"""v2 under CoinDCX-like fee scenarios, on PAXG and on BTC (same rule, no re-tuning). Research only."""
from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from . import reverse_eng as re_
from .deep import WARM
from .engine import summarize
from .final import equity, streak
from .paper_run import STOP_ATR, v2_condition
from .refine import trades_of
from .reverse_eng import clue_masks, fetch_klines, make_null_1h

# (label, fee % per side, slippage % per side)
SCENARIOS = [("assumed so far: 0.06 + 0.02 slip", 0.06, 0.02),
             ("INR futures taker 0.05 + 0.02 slip", 0.05, 0.02),
             ("USDT starting taker 0.075 + 0.02 slip", 0.075, 0.02),
             ("0.075 taker +18% GST on fee + 0.02 slip", 0.075 * 1.18, 0.02),
             ("harsh: 0.075 +GST + 0.05 slip", 0.075 * 1.18, 0.05)]


def report(df, label):
    n = len(df)
    masks, a = clue_masks(df)
    cond = v2_condition(df, masks)
    cut = int(n * 0.6)
    L = [f"## {label}", "", f"{df.index[0]:%Y-%m-%d} to {df.index[-1]:%Y-%m-%d}, {n} 1h bars. v2 unchanged. 2% risk, start 300.", "",
         "| fee scenario (per side) | round trip | part | trades | win% | net R | PF | 300 -> | max DD |", "|---|---|---|---|---|---|---|---|---|"]
    for nm, fee, slip in SCENARIOS:
        ep = replace(re_.EP, fee_pct=fee, slip_pct=slip)
        for part, lo, hi in (("whole", WARM, n), ("last 40%", cut, n)):
            tr = trades_of(df, cond, a, lo, hi, ep, STOP_ATR)
            s = summarize(tr)
            e, dd = equity(tr)
            L.append(f"| {nm} | {(fee+slip)*2:.2f}% | {part} | {s['n']} | {s['win_rate']*100:.0f} | {s['net_r']:+.1f} | {re_.fmt(s['pf'])} | {e:.0f} | {dd*100:.0f}% |")
    L.append("")
    return L


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", nargs="*", default=["PAXGUSDT", "BTCUSDT"])
    ap.add_argument("--days", type=int, default=1095)
    ap.add_argument("--out", default="fee_out")
    ap.add_argument("--synthetic", action="store_true")
    a = ap.parse_args()
    L = ["# v2 fee scenarios and BTC check", ""]
    for sym in a.assets:
        df = make_null_1h(24 * 900, 19) if a.synthetic else fetch_klines(sym, "1h", a.days, 3_600_000)
        L += report(df, sym)
    out = Path(a.out)
    out.mkdir(exist_ok=True)
    (out / "summary.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
