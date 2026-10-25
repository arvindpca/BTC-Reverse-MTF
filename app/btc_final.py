"""Cross-asset check of 3 trend-breakout candidates found by the BTC zoo (frozen parameters, no tuning).

Candidates (4h, long only, ATR chandelier trailing stop = NOT a fixed stop):
  A 4h|donchian55|long|s4_delay   B 4h|keltner_break|long|s2_chand   C 4h|ema20/50|long|s3_chand
Ensemble = the three run as separate sub-accounts, each risking 1/3 of the per-trade risk.
Important: BTC years 2024+ were the 'sealed test' of the zoo and these three were picked after seeing that test, so BTC numbers are
NOT clean out-of-sample. ETH/BNB/SOL/XRP never entered the selection, so they are the fresh-data check. Research only.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from . import btc_study as b
from .reverse_eng import fetch_klines

CANDS = ["4h|donchian55|long|s4_delay", "4h|keltner_break|long|s2_chand", "4h|ema20/50|long|s3_chand"]
RISK = 0.02


def run_cfg(df1, cfg):
    tf, nm, dr, ex = cfg.split("|")
    df = b.resample(df1, tf)
    I = b.indicators(df)
    L, S = b.signals(I)[nm]
    tr = b.eval_cfg(df, I, L, S, dr, ex, tf, 210, len(df))
    return df, tr


def eq_curve(items, risk):
    """items: list of (entry_ts, exit_ts, net_r, weight). Compounds in exit-time order."""
    eq, peak, dd, pts = 1.0, 1.0, 0.0, []
    for _, xt, r, w in sorted(items, key=lambda x: x[1]):
        eq *= 1 + risk * w * r
        peak = max(peak, eq); dd = max(dd, 1 - eq / peak); pts.append((xt, eq))
    return eq, dd, pts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default="BTCUSDT ETHUSDT BNBUSDT SOLUSDT XRPUSDT")
    ap.add_argument("--days", type=int, default=3350)
    ap.add_argument("--out", default="btcf_out")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(exist_ok=True)
    L = ["# Trend-breakout candidates: cross-asset check (frozen, no tuning)", "",
         "A = 4h Donchian55 breakout, B = 4h Keltner breakout, C = 4h EMA20/50 cross; all long only, ATR chandelier trailing stop (not fixed). "
         "Ensemble = A+B+C each with 1/3 of the 2% risk.", ""]
    allrows = []
    for sym in a.symbols.split():
        try:
            df1 = fetch_klines(sym, "1h", a.days, 3_600_000)
        except Exception as e:  # noqa: BLE001
            L.append(f"{sym}: no data ({e})"); continue
        items, per = [], {}
        for cfg in CANDS:
            df, tr = run_cfg(df1, cfg)
            per[cfg] = (df, tr)
            for t in tr:
                items.append((df.index[t.entry_idx], df.index[t.exit_idx], t.net_r, 1 / 3))
        yrs = sorted({x[0].year for x in items})
        L += [f"## {sym}  ({df1.index[0]:%Y-%m-%d} to {df1.index[-1]:%Y-%m-%d}; buy&hold {(df1['close'].iloc[-1] / df1['close'].iloc[0] - 1) * 100:+.0f}%)", "",
              "| candidate | trades | win% | net R | PF | max DD R | " + " | ".join(str(y) for y in yrs) + " |",
              "|---|---|---|---|---|---|" + "---|" * len(yrs)]
        for cfg, (df, tr) in list(per.items()) + [("ENSEMBLE", (None, None))]:
            if cfg == "ENSEMBLE":
                net = np.array([x[2] * x[3] * 3 for x in items]); lab = "A+B+C (avg R)"
                ys = {y: sum(x[2] for x in items if x[0].year == y) / 3 for y in yrs}
                srt = sorted(items, key=lambda x: x[1]); cum = np.cumsum([x[2] / 3 for x in srt])
                dd = float((np.maximum.accumulate(np.maximum(cum, 0)) - cum).max()) if len(cum) else 0
                pf = (net[net > 0].sum() / -net[net < 0].sum()) if (net < 0).any() else 99
                n = len(net)
            else:
                s = b.pstat(tr); lab = cfg.split("|")[1] + " " + cfg.split("|")[3]
                ys = {y: sum(t.net_r for t in tr if df.index[t.entry_idx].year == y) for y in yrs}
                net = np.array([t.net_r for t in tr]); n, dd, pf = s["n"], s["dd"], s["pf"]
            L.append(f"| {lab} | {n} | {(net > 0).mean() * 100 if n else 0:.0f} | {net.sum() if cfg != 'ENSEMBLE' else net.sum() / 3:+.1f} | {pf:.2f} | {dd:.1f} | "
                     + " | ".join(f"{ys.get(y, 0):+.1f}" for y in yrs) + " |")
        eq, dd, pts = eq_curve(items, RISK)
        L += ["", f"Ensemble with 2% risk per trade (compounded): x{eq:.2f} total, max drawdown {dd * 100:.0f}%.", ""]
        allrows += [dict(symbol=sym, cfg=cfg, entry=str(df.index[t.entry_idx]), exit=str(df.index[t.exit_idx]), entry_px=t.entry, stop=t.stop,
                         risk_pct=t.risk_pct, net_r=t.net_r) for cfg, (df, tr) in per.items() for t in tr]
    pd.DataFrame(allrows).to_csv(out / "trades.csv", index=False)
    Path(out, "summary.md").write_text("\n".join(L)); print("\n".join(L))


if __name__ == "__main__":
    main()
