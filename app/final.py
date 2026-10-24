"""Final PAXG candidate check: walk-forward variant choice + risk-based equity simulation.

Candidate v2 = lead rule (er>.4 & 3 up bars, long) + skip Europe session (UTC 08-14) + stop 4 x ATR.
Walk-forward: for each later third of history the variant is chosen using ONLY earlier data, then run on that third.
Equity: start 300, risk 2% of current equity per trade, compounding; P/L per trade = net_R x 2% x equity.
Research only; no orders.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from . import reverse_eng as re_
from .detail import cond_of
from .refine import LEAD, trades_of
from .reverse_eng import clue_masks, fetch_klines, make_null_1h
from .engine import summarize

VARIANTS = {"base": (False, 3.0), "stop4": (False, 4.0), "noEurope": (True, 3.0), "stop4+noEurope": (True, 4.0)}
RISK, START = 0.02, 300.0


def run_variant(df, masks, a, name, lo, hi, ep=None):
    skip, sa = VARIANTS[name]
    cond = cond_of(masks, LEAD)
    if skip:
        h = df.index.hour
        cond = cond & ~((h >= 8) & (h < 14))
    return trades_of(df, cond, a, lo, hi, ep, sa)


def equity(tr, risk=RISK, start=START):
    eq, peak, dd, curve = start, start, 0.0, []
    for t in tr:
        eq += eq * risk * t.net_r
        peak = max(peak, eq)
        dd = max(dd, (peak - eq) / peak)
        curve.append(eq)
    return eq, dd


def streak(tr) -> int:
    b = c = 0
    for t in tr:
        c = c + 1 if t.net_r < 0 else 0
        b = max(b, c)
    return b


def report(df: pd.DataFrame, label: str) -> list[str]:
    n = len(df)
    masks, a = clue_masks(df)
    L = [f"# {label}: final candidate check", "",
         f"{n} 1h bars, {df.index[0]:%Y-%m-%d} to {df.index[-1]:%Y-%m-%d}.", "",
         "## 1. Walk-forward (variant chosen on earlier data only)", "",
         "| fold | chosen on train (best PF, >= 30 trades) | chosen: test n | test net R | test PF | base: test net R | base PF |",
         "|---|---|---|---|---|---|---|"]
    folds = [(n // 3, 2 * n // 3), (2 * n // 3, n)]
    picked = []
    for lo, hi in folds:
        sc = {}
        for v in VARIANTS:
            s = summarize(run_variant(df, masks, a, v, 600, lo))
            if s["n"] >= 30 and s["net_r"] > 0:
                sc[v] = s["pf"]
        ch = max(sc, key=sc.get) if sc else "base"
        s1, s0 = summarize(run_variant(df, masks, a, ch, lo, hi)), summarize(run_variant(df, masks, a, "base", lo, hi))
        picked.append((ch, s1, s0))
        L.append(f"| {df.index[lo]:%Y-%m} to {df.index[hi-1]:%Y-%m} | {ch} | {s1['n']} | {s1['net_r']:+.1f} | {re_.fmt(s1['pf'])} | "
                 f"{s0['net_r']:+.1f} | {re_.fmt(s0['pf'])} |")
    wf = sum(p[1]["net_r"] for p in picked)
    bs = sum(p[2]["net_r"] for p in picked)
    L += ["", f"Walk-forward total {wf:+.1f} R versus always-base {bs:+.1f} R. "
          + ("Choosing on earlier data did not hurt, so the selection process is not obviously overfitting." if wf >= bs * 0.9 else
             "Choosing on earlier data did worse than just keeping the base rule, so do not trust the fancy variants."), ""]

    cut = int(n * 0.6)
    L += ["## 2. Candidate v2 vs base in money (start 300, risk 2% of equity per trade, compounding, fees included)", "",
          "| variant | part | trades | win% | net R | end equity | return | max drawdown | longest loss streak |",
          "|---|---|---|---|---|---|---|---|---|"]
    for v in ("base", "stop4+noEurope"):
        for part, lo, hi in (("whole history", 600, n), ("last 40% (test)", cut, n), ("last 12 months", n - 24 * 365, n)):
            tr = run_variant(df, masks, a, v, lo, hi)
            s = summarize(tr)
            e, dd = equity(tr)
            L.append(f"| {v} | {part} | {s['n']} | {s['win_rate']*100:.0f} | {s['net_r']:+.1f} | {e:.0f} | {(e/START-1)*100:+.0f}% | {dd*100:.0f}% | {streak(tr)} |")
    L.append("")
    # fixed 9000 for comparison
    tr = run_variant(df, masks, a, "stop4+noEurope", cut, n)
    fixed = sum(t.net_r * t.risk_pct / 100 * 9000 for t in tr)
    L += [f"For comparison, v2 on the test part with the old fixed 9000 position: {fixed:+.0f} total. "
          f"That needs a much bigger account than 300 to survive its drawdowns.", ""]
    # cost stress on v2
    L += ["## 3. Cost stress for v2 (last 40%, 2% risk)", "", "| fee+slippage per side | net R | end equity | return |", "|---|---|---|---|"]
    for m in (1, 2, 3):
        ep = replace(re_.EP, fee_pct=re_.EP.fee_pct * m, slip_pct=re_.EP.slip_pct * m)
        tr = run_variant(df, masks, a, "stop4+noEurope", cut, n, ep)
        e, _ = equity(tr)
        L.append(f"| {(re_.EP.fee_pct+re_.EP.slip_pct)*m:.2f}% | {summarize(tr)['net_r']:+.1f} | {e:.0f} | {(e/START-1)*100:+.0f}% |")
    L += ["", "## 4. Stop sizes under v2 (must stay inside the 30x liquidation distance, about 2.8%)", ""]
    tr = run_variant(df, masks, a, "stop4+noEurope", 600, n)
    rp = np.array([t.risk_pct for t in tr]) if tr else np.array([0.0])
    L.append(f"median {np.median(rp):.2f}%, 90th percentile {np.percentile(rp, 90):.2f}%, max {rp.max():.2f}%. "
             f"At 2% risk the position is about {RISK*100/np.median(rp):.1f}x the account, far below 30x.")
    L.append("")
    return L


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="PAXGUSDT")
    ap.add_argument("--days", type=int, default=1095)
    ap.add_argument("--out", default="final_out")
    ap.add_argument("--synthetic", action="store_true")
    a = ap.parse_args()
    df = make_null_1h(24 * 900, 13) if a.synthetic else fetch_klines(a.symbol, "1h", a.days, 3_600_000)
    L = report(df, a.symbol)
    out = Path(a.out)
    out.mkdir(exist_ok=True)
    (out / "summary.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
