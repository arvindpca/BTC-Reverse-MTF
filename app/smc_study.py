"""Intraday study for BTC and PAXG inside the user's time windows (IST 18:30-23:30 and 00:00-02:00).

Context from 1h: SMC proxy (BOS bias + order-block retest), POC of the previous 24h (volume profile), volume >= 1.5 x 20-day average.
Triggers on 15m / 5m: order-block retest, POC bounce, VWAP cross with RSI/MACD, support/resistance bounce and breakout confirmation.
1m: 'instant trend' bursts. Stops are NOT fixed: ATR chandelier trailing (or ATR stop + 2R target). Costs 0.06% + 0.02% per side.
Chronological split: TRAIN <2024-01-01, VALIDATION 2024-01..2025-06, SEALED TEST >=2025-07. Each config is also run WITHOUT the time window,
to see whether the window itself helps. A random-walk null shows how many 'winners' appear by luck. Research only; no orders.
"""
from __future__ import annotations

import argparse
import itertools
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from . import reverse_eng as re_
from .engine import run, summarize
from .mtf import atr, efficiency_ratio, ema, rsi
from .reverse_eng import fetch_klines

T_VAL, T_TEST = np.datetime64("2024-01-01"), np.datetime64("2025-07-01")
MIN = {"1m": 1, "5m": 5, "15m": 15}
HOLD = {"1m": 360, "5m": 288, "15m": 96}
EXITS = {"ch1.5": (1.5, True, 50.0), "ch2.5": (2.5, True, 50.0), "sl1.5_tp2": (1.5, False, 2.0)}


def resample(df, tf):
    r = {"5m": "5min", "15m": "15min", "1h": "1h"}[tf]
    return df.resample(r, label="left", closed="left").agg(dict(open="first", high="max", low="min", close="last", volume="sum")).dropna()


def xup(a, b):
    pa, pb = np.roll(a, 1), np.roll(b, 1)
    r = (a > b) & (pa <= pb); r[0] = False; return r


def edge(x):
    return x & ~np.concatenate([[False], x[:-1]])


# ------------------------------------------------------------ 1h context (all values known only after the 1h bar closes)
def smc_1h(h1):
    o, h, l, c = (h1[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    n = len(c)
    bias = np.zeros(n); obl = np.full((n, 2), np.nan); obs = np.full((n, 2), np.nan)
    ph = pl = np.nan; ph_used = pl_used = np.nan; b = 0; zl = zs = None
    for i in range(n):
        j = i - 5
        if j >= 5:
            if h[j] >= h[j - 5:i + 1].max(): ph = h[j]
            if l[j] <= l[j - 5:i + 1].min(): pl = l[j]
        if b <= 0 and ph == ph and c[i] > ph and ph != ph_used:
            b, ph_used = 1, ph
            idx = [k for k in range(max(0, i - 8), i) if c[k] < o[k]]
            zl = (l[idx[int(np.argmin(l[idx]))]], h[idx[int(np.argmin(l[idx]))]]) if idx else None
        elif b >= 0 and pl == pl and c[i] < pl and pl != pl_used:
            b, pl_used = -1, pl
            idx = [k for k in range(max(0, i - 8), i) if c[k] > o[k]]
            zs = (l[idx[int(np.argmax(h[idx]))]], h[idx[int(np.argmax(h[idx]))]]) if idx else None
        if zl and c[i] < zl[0]: zl = None
        if zs and c[i] > zs[1]: zs = None
        bias[i] = b
        if zl: obl[i] = zl
        if zs: obs[i] = zs
    # support / resistance: last confirmed pivot lows/highs
    sup, res = np.full(n, np.nan), np.full(n, np.nan)
    s = r = np.nan
    for i in range(n):
        j = i - 5
        if j >= 5:
            if l[j] <= l[j - 5:i + 1].min(): s = l[j]
            if h[j] >= h[j - 5:i + 1].max(): r = h[j]
        sup[i], res[i] = s, r
    volr = h1["volume"] / h1["volume"].rolling(480).mean().shift(1)
    day = h1.resample("1D").agg(dict(high="max", low="min"))
    pdh = day["high"].shift(1).reindex(h1.index, method="ffill").to_numpy(); pdl = day["low"].shift(1).reindex(h1.index, method="ffill").to_numpy()
    out = pd.DataFrame(dict(bias=bias, obl_lo=obl[:, 0], obl_hi=obl[:, 1], obs_lo=obs[:, 0], obs_hi=obs[:, 1], sup=sup, res=res,
                            volr=volr.to_numpy(), pdh=pdh, pdl=pdl), index=h1.index)
    out.index = out.index + pd.Timedelta(hours=1)          # known from the close of the hour
    return out


def poc_24h(df5):
    """POC of the previous 24h (volume profile on 5m closes), refreshed each hour, known at the hour start."""
    c, v = df5["close"].to_numpy(float), df5["volume"].to_numpy(float)
    hours = df5.index.floor("1h")
    first = np.flatnonzero(np.r_[True, hours[1:] != hours[:-1]])
    vals = np.full(len(first), np.nan)
    for k, s in enumerate(first):
        if s < 288: continue
        cc, vv = c[s - 288:s], v[s - 288:s]
        hist, edges = np.histogram(cc, bins=40, weights=vv)
        m = int(np.argmax(hist)); vals[k] = (edges[m] + edges[m + 1]) / 2
    return pd.Series(vals, index=df5.index[first])


def vwap_daily(df):
    tp = (df["high"] + df["low"] + df["close"]) / 3
    d = df.index.floor("1D")
    return ((tp * df["volume"]).groupby(d).cumsum() / df["volume"].groupby(d).cumsum()).to_numpy()


def macd_hist(c):
    m = ema(c, 12) - ema(c, 26)
    return m - ema(m, 9)


def build(df, tf, ctx, poc, h1_atr):
    """All arrays on the entry timeframe df."""
    o, h, l, c, v = (df[k].to_numpy(float) for k in ("open", "high", "low", "close", "volume"))
    A = {}
    cx = ctx.reindex(df.index, method="ffill")
    for k in cx.columns:
        A[k] = cx[k].to_numpy(float)
    A["poc"] = poc.reindex(df.index, method="ffill").to_numpy(float)
    per_day = 1440 // MIN[tf]
    A["barvolr"] = (v / pd.Series(v).rolling(20 * per_day).mean().shift(1).to_numpy())
    A["rsi"] = rsi(c, 14); A["mh"] = macd_hist(c); A["vwap"] = vwap_daily(df)
    A["atr"] = atr(h, l, c, 14)
    A.update(o=o, h=h, l=l, c=c, v=v)
    return A


def signals(A, tf):
    c, o, h, l = A["c"], A["o"], A["h"], A["l"]
    S = {}
    green, red = c > o, c < o
    vm = {"none": np.ones(len(c), bool), "1h": A["volr"] >= 1.5, "bar": A["barvolr"] >= 1.5}
    with np.errstate(invalid="ignore"):
        bu, bd = A["bias"] == 1, A["bias"] == -1
        ol = (A["obl_hi"] == A["obl_hi"]) & (l <= A["obl_hi"]) & (c > A["obl_lo"]) & green & bu
        os_ = (A["obs_lo"] == A["obs_lo"]) & (h >= A["obs_lo"]) & (c < A["obs_hi"]) & red & bd
        pocl = (A["poc"] == A["poc"]) & (l <= A["poc"]) & (c > A["poc"]) & green & bu
        pocs = (A["poc"] == A["poc"]) & (h >= A["poc"]) & (c < A["poc"]) & red & bd
        for vn, vmask in vm.items():
            S[f"smc_ob|vol={vn}"] = (edge(ol & vmask), edge(os_ & vmask))
            S[f"smc_ob+poc|vol={vn}"] = (edge(ol & vmask & (c > A["poc"])), edge(os_ & vmask & (c < A["poc"])))
            S[f"poc_bounce|vol={vn}"] = (edge(pocl & vmask), edge(pocs & vmask))
        up, dn = xup(c, A["vwap"]), xup(A["vwap"], c)
        for nm, lc, sc in (("rsi", A["rsi"] > 50, A["rsi"] < 50), ("macd", A["mh"] > 0, A["mh"] < 0), ("rsi+macd", (A["rsi"] > 50) & (A["mh"] > 0), (A["rsi"] < 50) & (A["mh"] < 0))):
            S[f"vwap+{nm}"] = (up & lc, dn & sc)
            S[f"vwap+{nm}|smc_bias"] = (up & lc & bu, dn & sc & bd)
        # support / resistance bounce confirmed by the candle close (looks back 6 bars for the touch)
        def touched_low(level):
            return pd.Series(l <= level * 1.001).rolling(6, min_periods=1).max().to_numpy().astype(bool)
        def touched_high(level):
            return pd.Series(h >= level * 0.999).rolling(6, min_periods=1).max().to_numpy().astype(bool)
        sl = (touched_low(A["sup"]) & (c > A["sup"] * 1.0005) & green) | (touched_low(A["pdl"]) & (c > A["pdl"] * 1.0005) & green)
        sh = (touched_high(A["res"]) & (c < A["res"] * 0.9995) & red) | (touched_high(A["pdh"]) & (c < A["pdh"] * 0.9995) & red)
        for vn in ("none", "bar"):
            S[f"sr_bounce|vol={vn}"] = (edge(sl & vm[vn]), edge(sh & vm[vn]))
            S[f"sr_breakout|vol={vn}"] = (edge((c > A["pdh"] * 1.0005) & vm[vn]) , edge((c < A["pdl"] * 0.9995) & vm[vn]))
    for k, (a, b) in S.items():
        a[:3000], b[:3000] = False, False
    return S


def insta_1m(df):
    o, h, l, c, v = (df[k].to_numpy(float) for k in ("open", "high", "low", "close", "volume"))
    er = efficiency_ratio(c, 30)
    volr = v / pd.Series(v).rolling(1440).mean().shift(1).to_numpy()
    g4 = (c > o) & (np.roll(c, 1) > np.roll(o, 1)) & (np.roll(c, 2) > np.roll(o, 2)) & (np.roll(c, 3) > np.roll(o, 3))
    r4 = (c < o) & (np.roll(c, 1) < np.roll(o, 1)) & (np.roll(c, 2) < np.roll(o, 2)) & (np.roll(c, 3) < np.roll(o, 3))
    S = {}
    with np.errstate(invalid="ignore"):
        for t in (0.5, 0.7):
            for vt in (0.0, 2.0):
                S[f"insta1m|er>{t}|vol>={vt}"] = (edge((er > t) & g4 & (volr >= vt)), edge((er > t) & r4 & (volr >= vt)))
    for a, b in S.values():
        a[:3000], b[:3000] = False, False
    return S, dict(o=o, h=h, l=l, c=c, atr=atr(h, l, c, 14))


# ------------------------------------------------------------ windows, evaluation
def window_masks(index, tf):
    t = index + pd.Timedelta(minutes=MIN[tf]) + pd.Timedelta(hours=5, minutes=30)     # close time in IST
    m = (t.hour * 60 + t.minute).to_numpy()
    wa = (m >= 18 * 60 + 30) & (m <= 23 * 60 + 30)
    wb = (m >= 0) & (m <= 2 * 60)
    return {"window": wa | wb, "all_day": np.ones(len(m), bool)}


def eval_cfg(A, L, Sh, direction, ex, tf, wmask):
    k, trail, rr = EXITS[ex]
    c = A["c"]
    sd = np.zeros(len(c), np.int8)
    if direction in ("long", "both"): sd[L & wmask] = 1
    if direction in ("short", "both"): sd[Sh & wmask & (sd == 0)] = -1
    dist = np.maximum(k * A["atr"], 0.0025 * c)
    stop = np.where(sd != 0, c - sd * dist, np.nan)
    ep = replace(re_.EP, rr=rr, be_r=None, max_hold=HOLD[tf], min_risk_pct=0.2, max_risk_pct=5.0, reverse=False,
                 trail_r=1.0 if trail else None, trail_start_r=0.0)
    return run(A["o"], A["h"], A["l"], c, sd, stop, np.arange(len(c)), ep, 3000, len(c))


def pstat(tr):
    s = summarize(tr)
    return dict(n=s["n"], win=s["win_rate"], net_r=s["net_r"], pf=min(s["pf"], 99.0), dd=s["max_dd_r"], cost=s["cost_r"] / max(s["n"], 1))


def zoo(df, A_by_tf, S_by_tf, tag, split=True):
    rows = []
    for tf, (A, S, idx) in A_by_tf.items():
        wm = window_masks(idx, tf)
        ent = idx.tz_localize(None).values if idx.tz is not None else idx.values
        for (nm, (L, Sh)), dr, ex, wn in itertools.product(S.items(), ("long", "short", "both"), EXITS, wm):
            tr = eval_cfg(A, L, Sh, dr, ex, tf, wm[wn])
            if not tr: continue
            et = ent[[t.entry_idx for t in tr]]
            parts = [[t for t, e in zip(tr, et) if e < T_VAL], [t for t, e in zip(tr, et) if T_VAL <= e < T_TEST], [t for t, e in zip(tr, et) if e >= T_TEST]]
            r = dict(cfg=f"{tf}|{nm}|{dr}|{ex}|{wn}", tf=tf, fam=nm.split("|")[0], win=wn)
            for p, t in zip(("tr", "va", "te"), parts):
                r.update({f"{p}_{k}": v for k, v in pstat(t).items()})
            rows.append(r)
    return pd.DataFrame(rows)


def passes(R):
    return (R.tr_n >= 40) & (R.va_n >= 25) & (R.tr_net_r > 0) & (R.va_net_r > 0) & (R.tr_pf > 1.15) & (R.va_pf > 1.15)


def make_ctx(df5):
    h1 = resample(df5, "1h")
    ctx = smc_1h(h1)
    return ctx, poc_24h(df5)


def prep_tf(df5, tf, ctx, poc):
    d = df5 if tf == "5m" else resample(df5, tf)
    A = build(d, tf, ctx, poc, None)
    return A, signals(A, tf), d.index


def null5(n, seed, base, index):
    rng = np.random.default_rng(seed)
    vol = np.repeat(rng.choice([0.0006, 0.001, 0.0016], size=n // 2000 + 1), 2000)[:n]
    c = base * np.exp(np.cumsum(rng.normal(0, vol)))
    o = np.r_[base, c[:-1]]
    h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, vol * .5))); l = np.minimum(o, c) * (1 - np.abs(rng.normal(0, vol * .5)))
    return pd.DataFrame(dict(open=o, high=h, low=l, close=c, volume=rng.lognormal(0, .6, n)), index=index)


def report(sym, df5, df1m, null=False):
    ctx, poc = make_ctx(df5)
    pack = {tf: prep_tf(df5, tf, ctx, poc) for tf in ("5m", "15m")}
    R = zoo(df5, {tf: (a, s, i) for tf, (a, s, i) in pack.items()}, None, sym)
    R["pass"] = passes(R); R["score"] = np.where(R["pass"], np.minimum(R.tr_pf, R.va_pf), 0.0)
    return R, pack


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default="BTCUSDT PAXGUSDT")
    ap.add_argument("--days", type=int, default=1800)
    ap.add_argument("--days1m", type=int, default=365)
    ap.add_argument("--out", default="smc_out")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(exist_ok=True)
    L = ["# Intraday study inside the user's time windows (IST 18:30-23:30 and 00:00-02:00)", "",
         "Context: SMC proxy on 1h (BOS bias + order-block retest), POC of previous 24h, volume >= 1.5 x 20-day average. "
         "Triggers on 15m/5m: OB retest, POC bounce, VWAP cross + RSI/MACD, support/resistance bounce and breakout. Stops: ATR chandelier trailing "
         "(1.5 or 2.5 x ATR, floor 0.25%) or 1.5 ATR stop + 2R target. Costs 0.06%+0.02% per side. Split: train <2024, validation 2024-01..2025-06, SEALED TEST 2025-07+.", ""]
    for sym in a.symbols.split():
        df5 = fetch_klines(sym, "5m", a.days, 300_000)
        R, pack = report(sym, df5, None)
        R.to_csv(out / f"{sym}_all_configs.csv", index=False)
        L += [f"## {sym}: {len(df5)} 5m bars, {df5.index[0]:%Y-%m-%d} to {df5.index[-1]:%Y-%m-%d}", "",
              f"Configs: {len(R)}. Positive net R: train {(R.tr_net_r > 0).mean() * 100:.0f}%, validation {(R.va_net_r > 0).mean() * 100:.0f}%, sealed test {(R.te_net_r > 0).mean() * 100:.0f}%. "
              f"Average cost per trade: {R.tr_cost.mean():.2f} R (this is the fee+slippage eaten by each trade, in units of the stop).", ""]
        for key, lab in (("win", "Time window vs all day"), ("tf", "Timeframe"), ("fam", "Strategy family")):
            g = R.groupby(key).agg(configs=("cfg", "size"), tr=("tr_net_r", "mean"), va=("va_net_r", "mean"), te=("te_net_r", "mean"), avgR=("te_n", "mean"))
            L += [f"{lab} (avg net R per config):", "", f"| {key} | configs | train | validation | sealed test |", "|---|---|---|---|---|"]
            for k, r in g.iterrows():
                L.append(f"| {k} | {int(r.configs)} | {r.tr:+.1f} | {r.va:+.1f} | {r.te:+.1f} |")
            L.append("")
        top = R[R["pass"]].sort_values("score", ascending=False)
        L += [f"Passed filter (net>0 & PF>1.15 in train AND validation, n>=40/25): **{len(top)}** of {len(R)}.", ""]
        if len(top):
            L += ["Top 5 (pre-registered, tested once on sealed test):", "", "| config | train n/PF/R | val n/PF/R | TEST n | TEST win% | TEST net R | TEST PF |", "|---|---|---|---|---|---|---|"]
            for _, r in top.head(5).iterrows():
                L.append(f"| {r.cfg} | {r.tr_n:.0f}/{r.tr_pf:.2f}/{r.tr_net_r:+.1f} | {r.va_n:.0f}/{r.va_pf:.2f}/{r.va_net_r:+.1f} | {r.te_n:.0f} | {r.te_win * 100:.0f} | {r.te_net_r:+.1f} | {r.te_pf:.2f} |")
            L += ["", f"Of the {len(top)} passers, {int((top.te_net_r > 0).sum())} are profitable on the sealed test; with n>=25 and PF>1.15: {int(((top.te_n >= 25) & (top.te_pf > 1.15) & (top.te_net_r > 0)).sum())}.", ""]
        if sym == a.symbols.split()[0]:
            nd = null5(len(df5), 11, float(df5['close'].iloc[0]), df5.index)
            N, _ = report("null", nd, None)
            L += [f"Random-walk null with the same bars and volatility: passers by pure luck = **{int(N['pass'].sum())}** of {len(N)}; positive on validation {(N.va_net_r > 0).mean() * 100:.0f}%, "
                  f"on sealed test {(N.te_net_r > 0).mean() * 100:.0f}%.", ""]
        # 1m instant trend (exploratory, last year only)
        try:
            d1 = fetch_klines(sym, "1m", a.days1m, 60_000)
            S1, A1 = insta_1m(d1)
            A1["c"], A1["o"] = A1["c"], d1["open"].to_numpy(float)
            L += [f"### {sym} 1m 'instant trend' (exploratory, {len(d1)} 1m bars, {d1.index[0]:%Y-%m-%d} to {d1.index[-1]:%Y-%m-%d})", "",
                  "| config | trades (window) | win% | net R | PF | cost per trade (R) | trades (all day) | net R (all day) | PF (all day) |", "|---|---|---|---|---|---|---|---|---|"]
            wm = window_masks(d1.index, "1m")
            for nm, (Lg, Sh) in S1.items():
                for ex in ("ch1.5", "sl1.5_tp2"):
                    rr = {}
                    for wn in ("window", "all_day"):
                        tr = eval_cfg(A1, Lg, Sh, "both", ex, "1m", wm[wn]); rr[wn] = pstat(tr)
                    w, al = rr["window"], rr["all_day"]
                    L.append(f"| {nm}|{ex} | {w['n']} | {w['win'] * 100:.0f} | {w['net_r']:+.1f} | {w['pf']:.2f} | {w['cost']:.2f} | {al['n']} | {al['net_r']:+.1f} | {al['pf']:.2f} |")
            L.append("")
        except Exception as e:  # noqa: BLE001
            L.append(f"1m data failed: {e}")
    Path(out, "summary.md").write_text("\n".join(L)); print("\n".join(L))


if __name__ == "__main__":
    main()
