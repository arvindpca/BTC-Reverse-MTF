"""Indicator filters on top of the final Time Frame Combo setup (BTC, 4H|anyL|w8|mkt|tp3, IST 12:30-23:30).

Each filter is evaluated at the 15m signal candle CLOSE (1h values from the last CLOSED 1h candle). No look-ahead.
TRAIN = first 2 years, TEST = last year. A filter is only trusted if it improves TRAIN *and* TEST.
Research only: no orders.
"""
from __future__ import annotations

import argparse
import itertools
from pathlib import Path

import numpy as np
import pandas as pd

from .reverse_eng import fetch_klines
from .tfcombo import M5, build, find_setups, simulate, stats, compound, mdtable, resample

WIN = [(750, 1410)]


def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()


def rsi(c, n=14):
    d = np.diff(c, prepend=c[0])
    up = pd.Series(np.clip(d, 0, None)).ewm(alpha=1 / n, adjust=False).mean()
    dn = pd.Series(np.clip(-d, 0, None)).ewm(alpha=1 / n, adjust=False).mean()
    return (100 - 100 / (1 + up / dn.replace(0, np.nan))).fillna(50).to_numpy()


def atr(h, l, c, n=14):
    pc = np.concatenate([[c[0]], c[:-1]])
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    return pd.Series(tr).ewm(alpha=1 / n, adjust=False).mean().to_numpy()


def adx(h, l, c, n=14):
    up, dn = np.diff(h, prepend=h[0]), -np.diff(l, prepend=l[0])
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    ndm = np.where((dn > up) & (dn > 0), dn, 0.0)
    a = atr(h, l, c, n)
    pdi = 100 * pd.Series(pdm).ewm(alpha=1 / n, adjust=False).mean().to_numpy() / a
    ndi = 100 * pd.Series(ndm).ewm(alpha=1 / n, adjust=False).mean().to_numpy() / a
    dx = 100 * abs(pdi - ndi) / np.maximum(pdi + ndi, 1e-9)
    return pd.Series(dx).ewm(alpha=1 / n, adjust=False).mean().to_numpy()


def supertrend(h, l, c, n=10, m=3.0):
    a = atr(h, l, c, n); mid = (h + l) / 2
    ub, lb = mid + m * a, mid - m * a
    d = np.ones(len(c)); fu, fl = ub.copy(), lb.copy()
    for i in range(1, len(c)):
        fu[i] = ub[i] if (ub[i] < fu[i - 1] or c[i - 1] > fu[i - 1]) else fu[i - 1]
        fl[i] = lb[i] if (lb[i] > fl[i - 1] or c[i - 1] < fl[i - 1]) else fl[i - 1]
        d[i] = 1 if c[i] > fu[i - 1] else (-1 if c[i] < fl[i - 1] else d[i - 1])
    return d


def htf_map(D, df, hours, cols):
    tc = (df.index + pd.Timedelta(hours=hours)).values
    k = np.searchsorted(tc, D["t15_close"], side="right") - 1
    return {n: np.where(k >= 0, v[np.clip(k, 0, None)], np.nan) for n, v in cols.items()}


def features(m5, D):
    m15 = D["m15"]
    o, h, l, c, v = (m15[x].to_numpy() for x in ("open", "high", "low", "close", "volume"))
    F = pd.DataFrame(index=range(len(c)))
    F["rsi"] = rsi(c)
    F["macdh"] = (ema(c, 12) - ema(c, 26)) - ema(ema(c, 12) - ema(c, 26), 9)
    F["ema50_15"] = ema(c, 50)
    F["close"] = c
    F["vol_ratio"] = v / pd.Series(v).rolling(20).mean().shift(1).to_numpy()
    a15 = atr(h, l, c)
    F["body_atr"] = abs(c - o) / a15
    # session VWAP (UTC day)
    day = m15.index.floor("D")
    tp = (h + l + c) / 3
    pv = pd.Series(tp * v).groupby(day).cumsum().to_numpy()
    vv = pd.Series(v).groupby(day).cumsum().to_numpy()
    F["vwap"] = pv / np.maximum(vv, 1e-9)
    # 1h features from last CLOSED 1h bar
    h1 = resample(m5, "1h")
    H, L, C = (h1[x].to_numpy() for x in ("high", "low", "close"))
    a1 = atr(H, L, C)
    f1 = pd.DataFrame(dict(ema200=ema(C, 200), ema50=ema(C, 50), adx=adx(H, L, C), atrp=a1 / C, close1=C))
    f1["atrp_rank"] = f1["atrp"].rolling(500, min_periods=100).rank(pct=True)
    t1c = (h1.index + pd.Timedelta(hours=1)).values
    k = np.searchsorted(t1c, D["t15_close"], side="right") - 1
    for col in f1.columns:
        F[col] = np.where(k >= 0, f1[col].to_numpy()[np.clip(k, 0, None)], np.nan)
    F["st_1h"] = htf_map(D, h1, 1, {"x": supertrend(H, L, C)})["x"]
    h4 = resample(m5, "4h")
    H4, L4, C4 = (h4[x].to_numpy() for x in ("high", "low", "close"))
    for n, v in htf_map(D, h4, 4, {"st_4h": supertrend(H4, L4, C4), "ema50_4h": ema(C4, 50), "ema200_4h": ema(C4, 200)}).items():
        F[n] = v
    d1 = resample(m5, "1D")
    Hd, Ld, Cd = (d1[x].to_numpy() for x in ("high", "low", "close"))
    from .tfcombo import htf_bias
    for n, v in htf_map(D, d1, 24, {"ema20_d": ema(Cd, 20), "ema50_d": ema(Cd, 50), "ema200_d": ema(Cd, 200),
                                     "st_d": supertrend(Hd, Ld, Cd), "bias_d": htf_bias(d1, 2)}).items():
        F[n] = v
    return F


def filt(name, F, s):
    r = F.iloc[s["bar"]]
    d = s["dir"]
    if name == "none": return True
    if name == "rsi>50": return (r.rsi - 50) * d > 0
    if name == "rsi_not_extreme": return (r.rsi < 70) if d == 1 else (r.rsi > 30)
    if name == "macd_hist": return r.macdh * d > 0
    if name == "ema50_15m": return (r.close - r.ema50_15) * d > 0
    if name == "vwap": return (r.close - r.vwap) * d > 0
    if name == "ema200_1h": return (r.close - r.ema200) * d > 0
    if name == "ema50>200_1h": return (r.ema50 - r.ema200) * d > 0
    if name == "adx>20": return r.adx > 20
    if name == "adx>25": return r.adx > 25
    if name == "volume1.5x": return r.vol_ratio >= 1.5
    if name == "strong_candle": return r.body_atr >= 1.0
    if name == "atr_high": return r.atrp_rank >= 0.5
    if name == "atr_low": return r.atrp_rank < 0.5
    if name == "supertrend_1h": return r.st_1h == d
    if name == "supertrend_4h": return r.st_4h == d
    if name == "supertrend_D": return r.st_d == d
    if name == "ema50_4h": return (r.close - r.ema50_4h) * d > 0
    if name == "ema200_4h": return (r.close - r.ema200_4h) * d > 0
    if name == "ema20_D": return (r.close - r.ema20_d) * d > 0
    if name == "ema50_D": return (r.close - r.ema50_d) * d > 0
    if name == "ema200_D": return (r.close - r.ema200_d) * d > 0
    if name == "daily_structure": return r.bias_d == d
    raise ValueError(name)


TREND = ["supertrend_1h", "supertrend_4h", "supertrend_D", "ema50_4h", "ema200_4h", "ema20_D", "ema50_D",
         "ema200_D", "daily_structure", "ema200_1h", "ema50>200_1h"]


FILTERS = ["none", "rsi>50", "rsi_not_extreme", "macd_hist", "ema50_15m", "vwap", "ema200_1h", "ema50>200_1h",
           "adx>20", "adx>25", "volume1.5x", "strong_candle", "atr_high", "atr_low"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--days", type=int, default=1095)
    ap.add_argument("--fee", type=float, default=0.0008)
    ap.add_argument("--out", default="tfind_out")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    m5 = fetch_klines(a.symbol, "5m", a.days, M5)
    cut = (m5.index[-1] - pd.Timedelta(days=365)).tz_localize(None)
    D = build(m5)
    S = find_setups(D, use_bias=True, eql_only=False, win=8)
    F = features(m5, D)

    def run(names):
        ss = [s for s in S if all(filt(n, F, s) for n in names)]
        t = simulate(ss, m5, D, entry="mkt", tp="3", fee=a.fee, window=WIN)
        tr = t[t.time < cut] if len(t) else t
        te = t[t.time >= cut] if len(t) else t
        return t, stats(tr), stats(te)

    rows = []
    for n in FILTERS:
        t, s1, s2 = run([n])
        rows.append(dict(filter=n, TR_trades=s1["trades"], TR_win=s1["win"], TR_avgR=s1["avgR"], TR_totR=s1["totR"],
                         TE_trades=s2["trades"], TE_win=s2["win"], TE_avgR=s2["avgR"], TE_totR=s2["totR"],
                         TE_maxDD_R=s2["maxDD_R"],
                         lakh_3y_2pct=compound(t, 0.02, 100000) if len(t) else 100000,
                         lakh_1y_2pct=compound(t[t.time >= cut], 0.02, 100000) if len(t) else 100000))
        if len(t): t.to_csv(out / f"trades_{n.replace('>', 'gt')}.csv", index=False)
    R = pd.DataFrame(rows)
    base = R[R["filter"] == "none"].iloc[0]
    good = [r["filter"] for _, r in R.iterrows() if r["filter"] != "none" and r.TR_avgR > base.TR_avgR
            and r.TR_trades >= 30]
    combo = []
    for x, y in itertools.combinations(good, 2):
        t, s1, s2 = run([x, y])
        combo.append(dict(filter=f"{x} + {y}", TR_trades=s1["trades"], TR_win=s1["win"], TR_avgR=s1["avgR"],
                          TR_totR=s1["totR"], TE_trades=s2["trades"], TE_win=s2["win"], TE_avgR=s2["avgR"],
                          TE_totR=s2["totR"], TE_maxDD_R=s2["maxDD_R"],
                          lakh_3y_2pct=compound(t, 0.02, 100000) if len(t) else 100000,
                          lakh_1y_2pct=compound(t[t.time >= cut], 0.02, 100000) if len(t) else 100000))
    C = pd.DataFrame(combo).sort_values("TR_avgR", ascending=False) if combo else pd.DataFrame()
    trows = []
    for base in (["none"], ["volume1.5x"]):
        for n in ["none"] + TREND:
            names = [x for x in base + [n] if x != "none"]
            t, s1, s2 = run(names)
            trows.append(dict(filter=" + ".join(names) or "none", TR_trades=s1["trades"], TR_win=s1["win"],
                              TR_avgR=s1["avgR"], TR_totR=s1["totR"], TE_trades=s2["trades"], TE_win=s2["win"],
                              TE_avgR=s2["avgR"], TE_totR=s2["totR"], TE_maxDD_R=s2["maxDD_R"],
                              lakh_3y_2pct=compound(t, 0.02, 100000) if len(t) else 100000,
                              lakh_1y_2pct=compound(t[t.time >= cut], 0.02, 100000) if len(t) else 100000))
    T = pd.DataFrame(trows)
    T.to_csv(out / "trend.csv", index=False)
    R.to_csv(out / "single.csv", index=False)
    if len(C): C.to_csv(out / "pairs.csv", index=False)
    md = [f"# Indicator filters on final setup ({a.symbol}, 4H|anyL|w8|mkt|tp3, IST 12:30-23:30)", "",
          f"TRAIN < {cut:%Y-%m-%d} <= TEST (last 365 days). Filters chosen on TRAIN only (avgR better than none, >=30 trades).", "",
          "## Single filters", "", mdtable(R), "",
          f"Filters that helped on TRAIN: {', '.join(good) or 'none'}", "",
          "## Pairs of TRAIN-helpful filters (sorted by TRAIN avgR)", "", mdtable(C.head(15)) if len(C) else "none", "",
          "## Trend filters (alone, and on top of volume1.5x)", "", mdtable(T), ""]
    (out / "summary.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
