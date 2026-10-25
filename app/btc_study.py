"""BTC study: data check + a wide zoo of common indicator strategies with NON-FIXED stops (ATR based, trailing).

Pre-registered, honest pipeline (research only, no orders):
  data  < 2022-01-01  TRAIN      (2017-08 .. 2021)
  data  2022 .. 2023  VALIDATION (rules/params are the frozen grid; nothing is fitted)
  data  >= 2024-01-01 SEALED TEST (never used for ranking; top-3 by the rule below are tested ONCE)
Selection rule: n>=30 train & n>=20 val trades, net R>0 and PF>1.2 in BOTH, score = min(PF_train, PF_val), top 3.
The same zoo is run on a random-walk series with BTC-like volatility to show how many 'winners' appear by pure luck.
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
from .reverse_eng import fetch_klines, make_null_1h

T_VAL, T_TEST = pd.Timestamp("2022-01-01", tz="UTC"), pd.Timestamp("2024-01-01", tz="UTC")
TFS = {"1h": 1, "4h": 4, "1d": 24}
HOLD = {"1h": 720, "4h": 180, "1d": 30}
MAXRISK = {"1h": 6.0, "4h": 12.0, "1d": 25.0}
# (stop ATR, trail start R, trail R, reverse-on-opposite)
EXITS = {"s2_chand": (2, 0.0, 1.0, False), "s3_chand": (3, 0.0, 1.0, False), "s4_chand": (4, 0.0, 1.0, False),
         "s3_delay": (3, 1.5, 1.0, False), "s4_delay": (4, 1.5, 1.0, False), "s3_chand_rev": (3, 0.0, 1.0, True)}


# ------------------------------------------------------------ data
def resample(df1, tf):
    if tf == "1h":
        return df1
    r = {"4h": "4h", "1d": "1D"}[tf]
    return df1.resample(r, label="left", closed="left").agg(dict(open="first", high="max", low="min", close="last", volume="sum")).dropna()


def data_check(df1):
    L = ["## 1. Data check", "", f"1h bars: {len(df1)}, {df1.index[0]:%Y-%m-%d} to {df1.index[-1]:%Y-%m-%d}."]
    exp = int((df1.index[-1] - df1.index[0]) / pd.Timedelta(hours=1)) + 1
    gaps = df1.index.to_series().diff().dropna()
    L += [f"Expected {exp} hourly bars, got {len(df1)} ({exp - len(df1)} missing); duplicates: {int(df1.index.duplicated().sum())}; "
          f"zero-volume bars: {int((df1['volume'] <= 0).sum())}; largest gap: {gaps.max()}.", "",
          "| year | open | close | return % | max DD % | daily vol % | 1d trending days % (ER20>0.4) | 1h trending % |", "|---|---|---|---|---|---|---|---|"]
    d1 = resample(df1, "1d")
    er_d = pd.Series(efficiency_ratio(d1["close"].to_numpy(), 20), index=d1.index)
    er_h = pd.Series(efficiency_ratio(df1["close"].to_numpy(), 20), index=df1.index)
    for y, g in df1.groupby(df1.index.year):
        c = g["close"]
        dd = ((c / c.cummax()) - 1).min() * 100
        dr = d1["close"][d1.index.year == y].pct_change().std() * 100
        L.append(f"| {y} | {c.iloc[0]:.0f} | {c.iloc[-1]:.0f} | {(c.iloc[-1] / c.iloc[0] - 1) * 100:+.0f} | {dd:.0f} | {dr:.2f} | "
                 f"{(er_d[er_d.index.year == y] > 0.4).mean() * 100:.0f} | {(er_h[er_h.index.year == y] > 0.4).mean() * 100:.0f} |")
    L += ["", f"Buy & hold whole period: {df1['close'].iloc[0]:.0f} -> {df1['close'].iloc[-1]:.0f} ({(df1['close'].iloc[-1] / df1['close'].iloc[0] - 1) * 100:+.0f}%).", ""]
    return L


# ------------------------------------------------------------ indicators and signals
def indicators(df):
    o, h, l, c, v = (df[k].to_numpy(float) for k in ("open", "high", "low", "close", "volume"))
    S = pd.Series
    I = dict(o=o, h=h, l=l, c=c, v=v, atr14=atr(h, l, c, 14), atr10=atr(h, l, c, 10))
    for n in (9, 20, 21, 50, 200):
        I[f"ema{n}"] = ema(c, n)
    I["rsi14"] = rsi(c, 14)
    m12 = ema(c, 12) - ema(c, 26); I["macd"], I["macds"] = m12, ema(m12, 9)
    m8 = ema(c, 8) - ema(c, 17); I["macd2"], I["macds2"] = m8, ema(m8, 9)
    ma, sd = S(c).rolling(20).mean().to_numpy(), S(c).rolling(20).std().to_numpy()
    I["bbu"], I["bbl"] = ma + 2 * sd, ma - 2 * sd
    for n in (20, 55):
        I[f"dh{n}"], I[f"dl{n}"] = S(h).rolling(n).max().shift(1).to_numpy(), S(l).rolling(n).min().shift(1).to_numpy()
    I["kcu"], I["kcl"] = ema(c, 20) + 2 * I["atr10"], ema(c, 20) - 2 * I["atr10"]
    up, dn = np.diff(h, prepend=h[0]), -np.diff(l, prepend=l[0])
    pdm, mdm = np.where((up > dn) & (up > 0), up, 0.0), np.where((dn > up) & (dn > 0), dn, 0.0)
    a = I["atr14"]
    with np.errstate(invalid="ignore", divide="ignore"):
        pdi, mdi = 100 * ema(pdm, 14) / a, 100 * ema(mdm, 14) / a
        dx = 100 * np.abs(pdi - mdi) / (pdi + mdi)
    I["pdi"], I["mdi"], I["adx"] = pdi, mdi, ema(np.nan_to_num(dx), 14)
    ll, hh = S(l).rolling(14).min().to_numpy(), S(h).rolling(14).max().to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        k = 100 * (c - ll) / (hh - ll)
    I["stk"] = S(k).rolling(3).mean().to_numpy()
    I["er20"] = efficiency_ratio(c, 20)
    I["volr"] = v / S(v).rolling(20).mean().to_numpy()
    # supertrend
    for per, mult, nm in ((10, 3.0, "st10"), (14, 3.0, "st14")):
        at = atr(h, l, c, per); hl2 = (h + l) / 2
        ub, lb = hl2 + mult * at, hl2 - mult * at
        dirn = np.ones(len(c)); fu, fl = ub.copy(), lb.copy()
        for i in range(1, len(c)):
            fu[i] = ub[i] if (ub[i] < fu[i - 1] or c[i - 1] > fu[i - 1]) else fu[i - 1]
            fl[i] = lb[i] if (lb[i] > fl[i - 1] or c[i - 1] < fl[i - 1]) else fl[i - 1]
            dirn[i] = 1 if c[i] > fu[i - 1] else (-1 if c[i] < fl[i - 1] else dirn[i - 1])
        I[nm] = dirn
    return I


def xup(a, b):
    pa, pb = np.roll(a, 1), np.roll(b, 1)
    r = (a > b) & (pa <= pb); r[0] = False; return r


def xdn(a, b):
    return xup(b, a)


def edge(x):
    return x & ~np.concatenate([[False], x[:-1]])


def signals(I):
    """name -> (long_edge, short_edge)"""
    c, o, S = I["c"], I["o"], {}
    for f, s in ((9, 21), (20, 50), (50, 200)):
        S[f"ema{f}/{s}"] = (xup(I[f"ema{f}"], I[f"ema{s}"]), xdn(I[f"ema{f}"], I[f"ema{s}"]))
    S["macd12-26"] = (xup(I["macd"], I["macds"]), xdn(I["macd"], I["macds"]))
    S["macd8-17"] = (xup(I["macd2"], I["macds2"]), xdn(I["macd2"], I["macds2"]))
    S["rsi_mr30/70"] = (xup(I["rsi14"], np.full_like(c, 30.0)), xdn(I["rsi14"], np.full_like(c, 70.0)))
    S["rsi_trend55/45"] = (xup(I["rsi14"], np.full_like(c, 55.0)), xdn(I["rsi14"], np.full_like(c, 45.0)))
    S["bb_break"] = (xup(c, I["bbu"]), xdn(c, I["bbl"]))
    S["bb_revert"] = (xup(c, I["bbl"]), xdn(c, I["bbu"]))
    for n in (20, 55):
        S[f"donchian{n}"] = (edge(c > I[f"dh{n}"]), edge(c < I[f"dl{n}"]))
    S["keltner_break"] = (xup(c, I["kcu"]), xdn(c, I["kcl"]))
    for nm in ("st10", "st14"):
        d = I[nm]; S[f"supertrend_{nm[2:]}"] = (edge(d > 0) & (np.roll(d, 1) < 0), edge(d < 0) & (np.roll(d, 1) > 0))
    S["adx_di25"] = (edge((I["pdi"] > I["mdi"]) & (I["adx"] > 25)), edge((I["mdi"] > I["pdi"]) & (I["adx"] > 25)))
    S["stoch_20/80"] = (xup(I["stk"], np.full_like(c, 20.0)), xdn(I["stk"], np.full_like(c, 80.0)))
    up3 = (c > o) & (np.roll(c, 1) > np.roll(o, 1)) & (np.roll(c, 2) > np.roll(o, 2))
    dn3 = (c < o) & (np.roll(c, 1) < np.roll(o, 1)) & (np.roll(c, 2) < np.roll(o, 2))
    S["er0.4_3bar"] = (edge((I["er20"] > 0.4) & up3), edge((I["er20"] > 0.4) & dn3))
    S["volspike_trend"] = (edge((I["volr"] > 2) & (c > o) & (c > I["ema50"])), edge((I["volr"] > 2) & (c < o) & (c < I["ema50"])))
    S["dip_in_uptrend"] = (edge((c > I["ema200"]) & (I["rsi14"] < 40)), edge((c < I["ema200"]) & (I["rsi14"] > 60)))
    for k, (a, b) in S.items():
        a[:210], b[:210] = False, False
    return S


# ------------------------------------------------------------ evaluation
def eval_cfg(df, I, L, Sh, direction, exit_name, tf, lo, hi):
    sa, ts, trr, rev = EXITS[exit_name]
    if rev and direction != "both":
        return None
    sd = np.zeros(len(df), np.int8)
    if direction in ("long", "both"):
        sd[L] = 1
    if direction in ("short", "both"):
        sd[Sh & (sd == 0)] = -1
    c = I["c"]
    stop = np.where(sd != 0, c - sd * sa * I["atr14"], np.nan)
    ep = replace(re_.EP, rr=50.0, be_r=None, max_hold=HOLD[tf], min_risk_pct=0.2, max_risk_pct=MAXRISK[tf], reverse=rev,
                 trail_r=trr, trail_start_r=ts)
    return run(I["o"], I["h"], I["l"], c, sd, stop, np.arange(len(c)), ep, lo, hi)


def pstat(tr):
    s = summarize(tr)
    return dict(n=s["n"], win=s["win_rate"], net_r=s["net_r"], pf=min(s["pf"], 99.0), dd=s["max_dd_r"])


def zoo(df1, lo_ts, hi_ts, label):
    rows = []
    for tf in TFS:
        df = resample(df1, tf)
        hi = int(df.index.searchsorted(hi_ts)) if hi_ts is not None else len(df)
        I = indicators(df)
        sig = signals(I)
        for (nm, (L, Sh)), dr, ex in itertools.product(sig.items(), ("long", "short", "both"), EXITS):
            tr = eval_cfg(df, I, L, Sh, dr, ex, tf, 210, hi)
            if tr is None:
                continue
            ent = df.index[[t.entry_idx for t in tr]].tz_localize(None).values if tr else np.array([], dtype="datetime64[ns]")
            tv, tt = np.datetime64(T_VAL.tz_localize(None)), np.datetime64(T_TEST.tz_localize(None))
            a = [t for t, e in zip(tr, ent) if e < tv]
            b = [t for t, e in zip(tr, ent) if tv <= e < tt]
            c_ = [t for t, e in zip(tr, ent) if e >= tt]
            sa_, sb_, sc_ = pstat(a), pstat(b), pstat(c_)
            rows.append(dict(cfg=f"{tf}|{nm}|{dr}|{ex}", tf=tf, **{f"tr_{k}": v for k, v in sa_.items()}, **{f"va_{k}": v for k, v in sb_.items()},
                             **{f"te_{k}": v for k, v in sc_.items()}))
    return pd.DataFrame(rows)


def passes(R):
    return (R.tr_n >= 30) & (R.va_n >= 20) & (R.tr_net_r > 0) & (R.va_net_r > 0) & (R.tr_pf > 1.2) & (R.va_pf > 1.2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--days", type=int, default=3350)
    ap.add_argument("--out", default="btc_out")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(exist_ok=True)
    df1 = fetch_klines(a.symbol, "1h", a.days, 3_600_000)
    L = [f"# {a.symbol}: data check + indicator-strategy zoo (non-fixed stops)", ""] + data_check(df1)

    # real data: scan uses ONLY data before T_TEST for ranking
    R = zoo(df1, None, None, "real")
    R["pass"] = passes(R)
    R["score"] = np.where(R["pass"], np.minimum(R.tr_pf, R.va_pf), 0.0)
    R.to_csv(out / "all_configs.csv", index=False)
    # null: random walk with BTC-like vol
    n1 = len(df1)
    nul = make_null_1h(n1, 7, base=float(df1["close"].iloc[0]))
    nul.index = df1.index
    N = zoo(nul, None, None, "null")
    N["pass"] = passes(N)

    L += ["## 2. Zoo overview (train 2017-21 | validation 2022-23)", "",
          f"Configs evaluated: {len(R)} (real) / {len(N)} (random-walk null). "
          f"Positive on TRAIN: real {(R.tr_net_r > 0).mean() * 100:.0f}%, null {(N.tr_net_r > 0).mean() * 100:.0f}%. "
          f"Positive on VALIDATION: real {(R.va_net_r > 0).mean() * 100:.0f}%, null {(N.va_net_r > 0).mean() * 100:.0f}%. "
          f"Positive on SEALED TEST: real {(R.te_net_r > 0).mean() * 100:.0f}%, null {(N.te_net_r > 0).mean() * 100:.0f}%.",
          f"Configs passing the selection filter (profitable & PF>1.2 in train AND validation, enough trades): real **{int(R['pass'].sum())}**, "
          f"null (luck only) **{int(N['pass'].sum())}**.",
          f"Rank correlation train net R vs validation net R across all real configs: {R.tr_net_r.rank().corr(R.va_net_r.rank()):+.2f}; "
          f"validation vs sealed test: {R.va_net_r.rank().corr(R.te_net_r.rank()):+.2f}  (near 0 = past winners do not stay winners).", ""]
    by = R.groupby(R.cfg.str.split("|").str[1]).agg(configs=("cfg", "size"), tr=("tr_net_r", "mean"), va=("va_net_r", "mean"), te=("te_net_r", "mean"))
    L += ["Average net R per config by indicator family (all stops/directions/timeframes):", "", "| family | configs | train avg R | validation avg R | sealed test avg R |", "|---|---|---|---|---|"]
    for k, r in by.sort_values("va", ascending=False).iterrows():
        L.append(f"| {k} | {int(r.configs)} | {r.tr:+.1f} | {r.va:+.1f} | {r.te:+.1f} |")
    bt = R.groupby("tf").agg(tr=("tr_net_r", "mean"), va=("va_net_r", "mean"), te=("te_net_r", "mean"))
    L += ["", "By timeframe (avg net R per config):", "", "| tf | train | validation | sealed test |", "|---|---|---|---|"]
    for k, r in bt.iterrows():
        L.append(f"| {k} | {r.tr:+.1f} | {r.va:+.1f} | {r.te:+.1f} |")

    top = R[R["pass"]].sort_values("score", ascending=False)
    L += ["", "## 3. Pre-registered finalists (top 3 by min(PF train, PF validation)) and SEALED TEST (2024-01 onwards, tested once)", "",
          "| config | train n / PF / net R | val n / PF / net R | TEST n | TEST win% | TEST net R | TEST PF | TEST max DD R |", "|---|---|---|---|---|---|---|---|"]
    for _, r in top.head(3).iterrows():
        L.append(f"| {r.cfg} | {r.tr_n:.0f} / {r.tr_pf:.2f} / {r.tr_net_r:+.1f} | {r.va_n:.0f} / {r.va_pf:.2f} / {r.va_net_r:+.1f} | "
                 f"{r.te_n:.0f} | {r.te_win * 100:.0f} | {r.te_net_r:+.1f} | {r.te_pf:.2f} | {r.te_dd:.1f} |")
    if top.empty:
        L.append("| (no config passed the filter) | | | | | | | |")
    L += ["", "Other passing configs (for completeness; NOT pre-selected, test shown only to measure how many survive):", "",
          "| config | score | TEST n | TEST net R | TEST PF |", "|---|---|---|---|---|"]
    for _, r in top.iloc[3:25].iterrows():
        L.append(f"| {r.cfg} | {r.score:.2f} | {r.te_n:.0f} | {r.te_net_r:+.1f} | {r.te_pf:.2f} |")
    if len(top):
        L += ["", f"Of {len(top)} configs that passed train+validation, {int((top.te_net_r > 0).sum())} are also profitable on the sealed test "
              f"({(top.te_net_r > 0).mean() * 100:.0f}%); with >=30 test trades and PF>1.2: {int(((top.te_n >= 30) & (top.te_pf > 1.2) & (top.te_net_r > 0)).sum())}."]
    Path(out, "summary.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
