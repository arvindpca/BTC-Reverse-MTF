"""Fresh-data (out-of-sample) check of the two candidates on history BEFORE the period they were designed on.

The v2 rule and the 15m 'scaled' variant were chosen on 2023-10-26 .. 2026-10-25. This script runs the SAME frozen rules on
older PAXG candles (everything before 2023-10-26) without changing any parameter. Research only; no orders.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from . import m5, reverse_eng as re_
from .engine import run
from .reverse_eng import fetch_klines

CUT = pd.Timestamp("2023-10-26", tz="UTC")


def frame(df, tr, tag):
    return pd.DataFrame([dict(strategy=tag, t=str(df.index[x.entry_idx]), exit=str(df.index[x.exit_idx]), entry=x.entry, stop=x.stop,
                              reason=x.reason, risk_pct=x.risk_pct, net_r=x.net_r) for x in tr])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="PAXGUSDT")
    ap.add_argument("--days", type=int, default=2700)
    ap.add_argument("--out", default="fresh_out")
    a = ap.parse_args()
    Path(a.out).mkdir(exist_ok=True)
    m5.BARS_H = 4
    m5.EP5 = m5.replace(re_.EP, max_hold=480 * 4)
    df15 = fetch_klines(a.symbol, "15m", a.days, 900_000)
    df1 = m5.to_1h(df15)
    hi15, hi1 = int(df15.index.searchsorted(CUT)), int(df1.index.searchsorted(CUT))
    a15 = m5.atr1h_on_5m(df15, df1)
    L = [f"# {a.symbol}: fresh-data check (frozen rules, data BEFORE {CUT:%Y-%m-%d})", "",
         f"15m data available: {df15.index[0]:%Y-%m-%d} to {df15.index[-1]:%Y-%m-%d}; fresh window = {df15.index[0]:%Y-%m-%d} to {CUT:%Y-%m-%d} ({hi15} 15m bars).", ""]
    res = {}
    # 1h v2
    e1, ar = m5.v2_1h(df1)
    c1 = df1["close"].to_numpy(float)
    st1 = np.where(e1, c1 - 4.0 * ar, np.nan)
    o, h, l, c = m5.arr(df1)
    res["1h v2"] = (df1, run(o, h, l, c, e1.astype(np.int8), st1, np.arange(len(c)), re_.EP, 700, hi1))
    # 15m scaled er>0.50, 3h up
    sd, st = m5.sig_scaled(df15, a15, 0.50, 3)
    o, h, l, c = m5.arr(df15)
    res["15m scaled er>0.50 3h"] = (df15, run(o, h, l, c, sd.astype(np.int8), st, np.arange(len(c)), m5.EP5, 3000, hi15))
    L += ["| strategy | trades | win% | net R | PF | max DD R | t-stat | net R by year |", "|---|---|---|---|---|---|---|---|"]
    for k, (d, tr) in res.items():
        s = m5.stats(tr, k)
        yr = pd.Series({str(d.index[t.entry_idx].year): 0.0 for t in tr}, dtype=float)
        for t in tr:
            yr[str(d.index[t.entry_idx].year)] += t.net_r
        L.append(f"| {k} | {s['n']} | {s['win']:.0f} | {s['net_r']:+.1f} | {s['pf']:.2f} | {s['dd_r']:.1f} | {s['t']:.1f} | "
                 + ", ".join(f"{y}: {v:+.1f}" for y, v in yr.items()) + " |")
        if tr:
            frame(d, tr, k).to_csv(Path(a.out, f"fresh_{'1h' if k.startswith('1h') else '15m'}.csv"), index=False)
    # buy-and-hold reference for the same window
    L += ["", f"Buy & hold PAXG over the fresh window: {(df15['close'].iloc[hi15 - 1] / df15['close'].iloc[0] - 1) * 100:+.1f}% "
          f"({df15['close'].iloc[0]:.0f} -> {df15['close'].iloc[hi15 - 1]:.0f}).", ""]
    Path(a.out, "summary.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
