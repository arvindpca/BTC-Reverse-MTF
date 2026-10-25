"""Frozen cross-asset check of the rules found by rev2 (no tuning). BTC rules -> BTC, ETH, BNB, SOL, XRP; PAXG rules -> PAXG.
BTC rules: 4h long in a low-volatility regime: (A) breakout above 48-bar high, (B) close in top 10% of 48-bar range, (C) RSI>70; ATR chandelier exit.
PAXG rules: 4h long momentum: (D) ER>.4 and price 1-3 ATR above EMA50, (E) RSI 55-70 and ER .2-.4, (F) high-vol after 3 down bars (dip). Delayed-trail exit."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from .reverse_eng import clue_masks, fetch_klines
from .rev2 import to_tf, trades, st

BTC_RULES = [("A breakout48+lowvol", ["breakout up48", "vol low"], "chand"), ("B rangehigh+lowvol", ["range high>.9", "vol low"], "chand"), ("C rsi>70+lowvol", ["rsi>70", "vol low"], "chand")]
PAXG_RULES = [("D er>.4+dist1..3", ["er>.4", "dist1..3"], "delay"), ("E rsi55-70+er.2-.4", ["rsi55-70", "er.2-.4"], "delay"), ("F highvol+3down", ["vol high", "3 down bars"], "delay")]


def run_rules(df, rules):
    masks, a = clue_masks(df)
    out = {}
    for nm, parts, ex in rules:
        m = np.ones(len(df), bool)
        for p in parts: m &= masks[p]
        out[nm] = trades(df, m, a, 1, 250, len(df), "4h", ex)
    return out


def table(df, res, L):
    yrs = sorted({df.index[t.entry_idx].year for tr in res.values() for t in tr})
    L += ["| rule | trades | win% | net R | PF | max DD R | " + " | ".join(map(str, yrs)) + " |", "|---|---|---|---|---|---|" + "---|" * len(yrs)]
    allr = []
    for nm, tr in res.items():
        s = st(tr); ys = {y: sum(t.net_r for t in tr if df.index[t.entry_idx].year == y) for y in yrs}
        L.append(f"| {nm} | {s['n']} | {s['win'] * 100:.0f} | {s['net_r']:+.1f} | {s['pf']:.2f} | {s['dd']:.1f} | " + " | ".join(f"{ys[y]:+.1f}" for y in yrs) + " |")
        allr += [(df.index[t.entry_idx], t.net_r) for t in tr]
    if allr:
        v = np.array([r for _, r in allr]); ys = {y: sum(r for d, r in allr if d.year == y) / len(res) for y in yrs}
        pf = v[v > 0].sum() / -v[v < 0].sum() if (v < 0).any() else 99
        L.append(f"| **all rules (avg R)** | {len(v)} | {(v > 0).mean() * 100:.0f} | {v.sum() / len(res):+.1f} | {pf:.2f} | - | " + " | ".join(f"{ys[y]:+.1f}" for y in yrs) + " |")
    L.append("")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default="rev2c_out"); a = ap.parse_args()
    out = Path(a.out); out.mkdir(exist_ok=True)
    L = ["# Frozen cross-asset check of the reverse-engineering v2 rules (4h, long only, not-fixed exits)", "",
         "BTC and PAXG numbers below overlap with the period the rules were mined/validated/tested on (so not clean). ETH/BNB/SOL/XRP were never used: they are the fresh-data check.", ""]
    for sym, rules, days in (("BTCUSDT", BTC_RULES, 3350), ("ETHUSDT", BTC_RULES, 3350), ("BNBUSDT", BTC_RULES, 3350), ("SOLUSDT", BTC_RULES, 3350), ("XRPUSDT", BTC_RULES, 3350),
                             ("PAXGUSDT", PAXG_RULES, 2700)):
        try:
            d = to_tf(fetch_klines(sym, "1h", days, 3_600_000), "4h")
        except Exception as e:  # noqa: BLE001
            L.append(f"{sym}: no data ({e})"); continue
        res = run_rules(d, rules)
        L += [f"## {sym} ({d.index[0]:%Y-%m-%d} to {d.index[-1]:%Y-%m-%d}; buy&hold {(d['close'].iloc[-1] / d['close'].iloc[0] - 1) * 100:+.0f}%)", ""]
        table(d, res, L)
        pd.DataFrame([dict(rule=k, entry=str(d.index[t.entry_idx]), exit=str(d.index[t.exit_idx]), risk_pct=t.risk_pct, net_r=t.net_r) for k, tr in res.items() for t in tr]).to_csv(out / f"{sym}_trades.csv", index=False)
    Path(out, "summary.md").write_text("\n".join(L)); print("\n".join(L))


if __name__ == "__main__":
    main()
