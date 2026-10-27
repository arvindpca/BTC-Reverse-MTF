"""'Time Frame Combo' backtest (Velox FX idea): 4H direction -> 1H liquidity sweep -> 15m ChoCH -> 5m entry.

LONG (mirror for SHORT):
  4H  : bias = +1 after a 4H close above the last confirmed 4H swing high (BOS up), -1 after close below last swing low.
  1H  : liquidity pool = confirmed 1H swing low (optionally only EQUAL lows: 2 swing lows within tol). Pool must be < 7 days old.
  15m : a 15m candle trades below the pool = SWEEP. Within `win` 15m bars, a 15m CLOSE above the last confirmed 15m swing
        high (formed before the sweep) = ChoCH. Bias must still be +1.
  5m  : entry 'mkt' = next 5m open after the ChoCH candle closes; 'pb50' = limit at 50% of the sweep-low -> leg-high move,
        valid 2 hours. SL just below the sweep low. TP = fixed R multiple, or 'liq' = nearest unswept 1H swing high.
No look-ahead: every swing is used only after its right-side bars have closed; HTF values only after their candle closes.
Fills on 5m candles; if SL and TP fall in the same 5m candle, the LOSS is counted. Costs per side are configurable.
One position at a time. Time exit after 48h. Research only: no orders.
"""
from __future__ import annotations

import argparse
import itertools
from pathlib import Path

import numpy as np
import pandas as pd

from .reverse_eng import fetch_klines

M5 = 300_000


def resample(df, rule):
    return df.resample(rule, label="left", closed="left").agg(
        dict(open="first", high="max", low="min", close="last", volume="sum")).dropna()


def pivots(h, l, k):
    """Indexes of swing highs/lows with k bars each side. A pivot at i is known at bar i+k."""
    n = len(h)
    sh, sl = [], []
    for i in range(k, n - k):
        if h[i] == h[i - k:i + k + 1].max() and h[i] > h[i - k:i].max():
            sh.append(i)
        if l[i] == l[i - k:i + k + 1].min() and l[i] < l[i - k:i].min():
            sl.append(i)
    return np.array(sh, int), np.array(sl, int)


def htf_bias(df, k):
    """Bias per HTF bar, valid from that bar's CLOSE onward."""
    h, l, c = (df[x].to_numpy() for x in ("high", "low", "close"))
    sh, sl = pivots(h, l, k)
    conf_h = {i + k: h[i] for i in sh}
    conf_l = {i + k: l[i] for i in sl}
    bias = np.zeros(len(c))
    lh = ll = np.nan
    b = 0
    for i in range(len(c)):
        if i in conf_h:
            lh = conf_h[i]
        if i in conf_l:
            ll = conf_l[i]
        if not np.isnan(lh) and c[i] > lh:
            b = 1
        elif not np.isnan(ll) and c[i] < ll:
            b = -1
        bias[i] = b
    return bias


def build(m5, k4=3, k1=3, k15=2):
    m15, h1, h4 = resample(m5, "15min"), resample(m5, "1h"), resample(m5, "4h")
    t15_close = (m15.index + pd.Timedelta(minutes=15)).values
    # 4H bias known at 4H close
    b4 = htf_bias(h4, k4)
    t4_close = (h4.index + pd.Timedelta(hours=4)).values
    idx = np.searchsorted(t4_close, t15_close, side="right") - 1
    bias15 = np.where(idx >= 0, b4[np.clip(idx, 0, None)], 0)
    # 1H pools, known at close of pivot+k1 bar
    hh, hl = h1["high"].to_numpy(), h1["low"].to_numpy()
    sh, sl = pivots(hh, hl, k1)
    t1 = h1.index.values
    pools_lo = [(t1[i + k1] + np.timedelta64(1, "h"), t1[i], hl[i]) for i in sl if i + k1 < len(t1)]
    pools_hi = [(t1[i + k1] + np.timedelta64(1, "h"), t1[i], hh[i]) for i in sh if i + k1 < len(t1)]
    # 15m swings, known at close of pivot+k15 bar
    h15, l15 = m15["high"].to_numpy(), m15["low"].to_numpy()
    s15h, s15l = pivots(h15, l15, k15)
    return dict(m15=m15, t15_close=t15_close, bias=bias15, pools_lo=pools_lo, pools_hi=pools_hi,
                s15h=s15h, s15l=s15l, k15=k15)


def find_setups(D, use_bias=True, eql_only=False, win=16, tol=0.0010, max_age_days=7):
    """Walk 15m bars; return list of setups (dir, choch_bar, sweep_extreme, leg_extreme)."""
    m15 = D["m15"]
    o, h, l, c = (m15[x].to_numpy() for x in ("open", "high", "low", "close"))
    tc = D["t15_close"]
    n = len(c)
    k15 = D["k15"]
    # 15m confirmed swing arrays by confirm index
    conf_sh = np.full(n, np.nan); conf_sl = np.full(n, np.nan)
    for i in D["s15h"]:
        if i + k15 < n: conf_sh[i + k15] = h[i]
    for i in D["s15l"]:
        if i + k15 < n: conf_sl[i + k15] = l[i]
    last_sh = pd.Series(conf_sh).ffill().to_numpy()
    last_sl = pd.Series(conf_sl).ffill().to_numpy()

    age = np.timedelta64(max_age_days, "D")
    lo_q, hi_q = list(D["pools_lo"]), list(D["pools_hi"])
    act_lo, act_hi = [], []   # [level, pivot_time, is_eql]
    pend = []                 # pending sweeps: [dir, start_bar, extreme, struct_level]
    setups = []
    qi_lo = qi_hi = 0
    for i in range(n):
        T = tc[i]
        while qi_lo < len(lo_q) and lo_q[qi_lo][0] <= T:
            ct, pt, lv = lo_q[qi_lo]
            eq = any(abs(lv - a[0]) / lv <= tol for a in act_lo)
            act_lo.append([lv, pt, eq]); qi_lo += 1
        while qi_hi < len(hi_q) and hi_q[qi_hi][0] <= T:
            ct, pt, lv = hi_q[qi_hi]
            eq = any(abs(lv - a[0]) / lv <= tol for a in act_hi)
            act_hi.append([lv, pt, eq]); qi_hi += 1
        act_lo = [a for a in act_lo if T - a[1] <= age]
        act_hi = [a for a in act_hi if T - a[1] <= age]
        b = D["bias"][i]
        # progress pending setups
        keep = []
        for p in pend:
            d, s, ext, lvl = p
            if d == 1:
                p[2] = ext = min(ext, l[i])
                if c[i] > lvl and (not use_bias or b == 1):
                    setups.append(dict(dir=1, bar=i, sweep=ext, leg=h[s:i + 1].max()))
                    continue
            else:
                p[2] = ext = max(ext, h[i])
                if c[i] < lvl and (not use_bias or b == -1):
                    setups.append(dict(dir=-1, bar=i, sweep=ext, leg=l[s:i + 1].min()))
                    continue
            if i - s < win:
                keep.append(p)
        pend = keep
        # new sweeps (pool consumed whatever the bias)
        swept = [a for a in act_lo if l[i] < a[0]]
        if swept:
            act_lo = [a for a in act_lo if l[i] >= a[0]]
            if (not eql_only or any(a[2] for a in swept)) and (not use_bias or b == 1) and not np.isnan(last_sh[i]):
                pend = [p for p in pend if p[0] != 1]
                pend.append([1, i, l[i], last_sh[i]])
        swept = [a for a in act_hi if h[i] > a[0]]
        if swept:
            act_hi = [a for a in act_hi if h[i] <= a[0]]
            if (not eql_only or any(a[2] for a in swept)) and (not use_bias or b == -1) and not np.isnan(last_sl[i]):
                pend = [p for p in pend if p[0] != -1]
                pend.append([-1, i, h[i], last_sl[i]])
    return setups


def simulate(setups, m5, D, entry="mkt", tp="2", fee=0.0008, buf=0.0005, rmin=0.002, rmax=0.03,
             pb_valid=24, max_hold=576, window=None):
    """window: list of (start_min, end_min) in IST (UTC+5:30); a setup is taken only if its 15m signal closes inside."""
    t5 = m5.index.values
    o5, h5, l5, c5 = (m5[x].to_numpy() for x in ("open", "high", "low", "close"))
    hi_pools = np.array([[p[0].astype("datetime64[ns]").astype("int64"), p[2]] for p in D["pools_hi"]], float) if D["pools_hi"] else np.zeros((0, 2))
    lo_pools = np.array([[p[0].astype("datetime64[ns]").astype("int64"), p[2]] for p in D["pools_lo"]], float) if D["pools_lo"] else np.zeros((0, 2))
    trades = []
    busy_until = np.datetime64("1970-01-01")
    for s in setups:
        T = D["t15_close"][s["bar"]]
        if T < busy_until:
            continue
        if window:
            mi = int(((T.astype("datetime64[m]").astype("int64") + 330) % 1440))
            if not any((a <= mi < b) if a < b else (mi >= a or mi < b) for a, b in window):
                continue
        j = np.searchsorted(t5, T)
        if j >= len(t5) - 2:
            continue
        d = s["dir"]
        sl = s["sweep"] * (1 - buf) if d == 1 else s["sweep"] * (1 + buf)
        if entry == "mkt":
            ej, ep = j, o5[j]
        else:
            lvl = s["leg"] - 0.5 * (s["leg"] - s["sweep"])
            ej = None
            for q in range(j, min(j + pb_valid, len(t5))):
                if (d == 1 and l5[q] <= sl) or (d == -1 and h5[q] >= sl):
                    break  # invalidated before fill
                if (d == 1 and l5[q] <= lvl) or (d == -1 and h5[q] >= lvl):
                    ej, ep = q, (min(lvl, o5[q]) if d == 1 else max(lvl, o5[q])); break
            if ej is None:
                continue
        risk = (ep - sl) * d
        if risk <= 0 or not (rmin <= risk / ep <= rmax):
            continue
        if tp == "liq":
            Tn = t5[ej].astype("datetime64[ns]").astype("int64")
            if d == 1:
                cand = hi_pools[(hi_pools[:, 0] <= Tn) & (hi_pools[:, 1] > ep + 1.5 * risk)][:, 1] if len(hi_pools) else []
                if len(cand) == 0: continue
                tgt = cand.min()
            else:
                cand = lo_pools[(lo_pools[:, 0] <= Tn) & (lo_pools[:, 1] < ep - 1.5 * risk)][:, 1] if len(lo_pools) else []
                if len(cand) == 0: continue
                tgt = cand.max()
        else:
            tgt = ep + d * float(tp) * risk
        res, xj, xp = None, None, None
        for q in range(ej, min(ej + max_hold, len(t5))):
            hit_sl = (l5[q] <= sl) if d == 1 else (h5[q] >= sl)
            hit_tp = (h5[q] >= tgt) if d == 1 else (l5[q] <= tgt)
            if q == ej and entry != "mkt":
                hit_tp = hit_tp and ((c5[q] >= tgt) if d == 1 else (c5[q] <= tgt))  # same-bar fill: be strict
            if hit_sl:
                res, xj, xp = "SL", q, sl; break
            if hit_tp:
                res, xj, xp = "TP", q, tgt; break
        if res is None:
            xj = min(ej + max_hold, len(t5)) - 1
            res, xp = "TIME", c5[xj]
        gross = (xp - ep) * d / ep
        net = gross - 2 * fee
        trades.append(dict(time=pd.Timestamp(t5[ej]), dir="LONG" if d == 1 else "SHORT", entry=ep, sl=sl, tp=tgt,
                           exit=xp, exit_time=pd.Timestamp(t5[xj]), result=res, risk_pct=risk / ep * 100,
                           R=net * ep / risk, net_pct=net * 100))
        busy_until = t5[xj] + np.timedelta64(5, "m")
    return pd.DataFrame(trades)


def mdtable(df):
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(str(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join(lines)


def stats(t):
    if t is None or len(t) == 0:
        return dict(trades=0, win=0.0, avgR=0.0, totR=0.0, PF=0.0, maxDD_R=0.0, sum_pct=0.0)
    R = t["R"].to_numpy()
    eq = np.cumsum(R)
    dd = (np.maximum.accumulate(np.concatenate([[0], eq])) - np.concatenate([[0], eq])).max()
    pos, neg = R[R > 0].sum(), -R[R < 0].sum()
    return dict(trades=len(R), win=round((R > 0).mean() * 100, 1), avgR=round(R.mean(), 3), totR=round(R.sum(), 1),
                PF=round(pos / neg, 2) if neg > 0 else 99.0, maxDD_R=round(dd, 1), sum_pct=round(t["net_pct"].sum(), 1))


def compound(t, risk=0.01, start=1000.0):
    eq = start
    for r in t["R"]:
        eq *= 1 + risk * r
    return round(eq, 0)


WINDOWS = {"all": None, "LN": [(750, 1410)], "user": [(1110, 1410), (0, 120)], "noAsia": [(750, 330)]}
PICKS = ["4H|EqL|w8|mkt|tp3|user", "4H|anyL|w8|mkt|tp3|LN", "4H|anyL|w16|mkt|tp2|all"]


def yearly(t):
    if len(t) == 0:
        return "no trades"
    g = t.groupby(t["time"].dt.year)
    return ", ".join(f"{y}: {len(x)} tr {x.R.sum():+.1f}R" for y, x in g)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default="BTCUSDT")
    ap.add_argument("--days", type=int, default=1095)
    ap.add_argument("--fee", type=float, default=0.0008, help="cost per side incl. slippage")
    ap.add_argument("--out", default="tfcombo_out")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    md = ["# Time Frame Combo backtest (4H direction -> 1H liquidity -> 15m ChoCH -> 5m entry)", "",
          f"Cost per side {a.fee*100:.2f}% (fee+slippage). SL = beyond sweep extreme. Same-candle SL/TP = loss. "
          "Split: first 2/3 of data = IN-SAMPLE (pick), last 1/3 = OUT-OF-SAMPLE (honest check).", ""]
    for sym in a.symbols.split():
        m5 = fetch_klines(sym, "5m", a.days, M5)
        cut = m5.index[0] + (m5.index[-1] - m5.index[0]) * 2 / 3
        cut_n = cut.tz_localize(None)
        md += [f"## {sym}  ({m5.index[0]:%Y-%m-%d} -> {m5.index[-1]:%Y-%m-%d}, split {cut:%Y-%m-%d})", ""]
        D = build(m5)
        rows, picks = [], {}
        for use_bias, eql, win in itertools.product([True, False], [False, True], [8, 16]):
            S = find_setups(D, use_bias=use_bias, eql_only=eql, win=win)
            for entry, tp, wn in itertools.product(["mkt", "pb50"], ["1.5", "2", "3", "liq"], WINDOWS):
                t = simulate(S, m5, D, entry=entry, tp=tp, fee=a.fee, window=WINDOWS[wn])
                name = f"{'4H' if use_bias else 'no4H'}|{'EqL' if eql else 'anyL'}|w{win}|{entry}|tp{tp}|{wn}"
                ins = t[t["time"] < cut_n] if len(t) else t
                oos = t[t["time"] >= cut_n] if len(t) else t
                si, so = stats(ins), stats(oos)
                if name in PICKS:
                    picks[name] = t
                rows.append(dict(cfg=name, **{f"IS_{k}": v for k, v in si.items()}, **{f"OOS_{k}": v for k, v in so.items()},
                                 OOS_1k_at_1pct_risk=compound(oos) if len(oos) else 1000))
                if len(t):
                    t.to_csv(out / f"trades_{sym}_{name.replace('|', '_')}.csv", index=False)
        R = pd.DataFrame(rows).sort_values("IS_totR", ascending=False)
        R.to_csv(out / f"grid_{sym}.csv", index=False)
        cols = ["cfg", "IS_trades", "IS_win", "IS_avgR", "IS_totR", "IS_PF", "OOS_trades", "OOS_win", "OOS_avgR",
                "OOS_totR", "OOS_PF", "OOS_maxDD_R", "OOS_1k_at_1pct_risk"]
        md += ["Top 12 by IN-SAMPLE total R:", "", mdtable(R[cols].head(12)), "",
               "Baseline (exact image rules: 4H bias, any 1H low, w16, market entry, 2R):", "",
               mdtable(R[R.cfg == "4H|anyL|w16|mkt|tp2|all"][cols]), "",
               "Pre-chosen candidates (picked on the earlier 1-year run, before this test):", "",
               mdtable(R[R.cfg.isin(PICKS)][cols]), ""]
        for k, t in picks.items():
            md += [f"- {k}: full period {stats(t)} | per year: {yearly(t)} | 1 lakh @2% risk -> {(compound(t, 0.02, 100000) if len(t) else 100000):,.0f}"]
        md += ["", "Window effect (avg OOS totR over all rule combos): " + ", ".join(
               f"{w}: {R[R.cfg.str.endswith('|' + w)].OOS_totR.mean():+.1f}R" for w in WINDOWS), "",
               f"Configs profitable OOS: {(R.OOS_totR > 0).sum()} of {len(R)}", ""]
        print(sym, "done", len(m5))
    (out / "summary.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
