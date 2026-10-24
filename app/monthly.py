"""Month-by-month table for candidate v2 (PAXG). Research only."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from .deep import WARM, base_trades
from .paper_run import RISK, START_EQ, v2_condition
from .reverse_eng import clue_masks, fetch_klines, make_null_1h


def report(df: pd.DataFrame, label: str) -> list[str]:
    masks, a = clue_masks(df)
    tr = base_trades(df, v2_condition(df, masks), a, WARM, len(df))
    eq, rows = START_EQ, []
    for t in tr:
        pnl = eq * RISK * t.net_r
        eq += pnl
        rows.append(dict(month=df.index[t.exit_idx].strftime("%Y-%m"), net_r=t.net_r, pnl=pnl, eq=eq, risk=t.risk_pct))
    d = pd.DataFrame(rows)
    cm = df["close"].resample("MS").last()
    bh = ((cm / cm.shift(1) - 1) * 100)
    g = d.groupby("month").agg(trades=("net_r", "size"), wins=("net_r", lambda x: int((x > 0).sum())), net_r=("net_r", "sum"),
                               pnl=("pnl", "sum"), eq=("eq", "last"))
    L = [f"# {label} v2 month by month (trades counted in the month they CLOSE)", "",
         f"Start equity {START_EQ:.0f}, risk {RISK*100:.0f}% of equity per trade, compounding, fees 0.16% round trip included. "
         "P/L is in the margin currency.", "",
         "| month | gold move % | trades | wins | win% | net R | P/L | equity at month end |", "|---|---|---|---|---|---|---|---|"]
    for m, r in g.iterrows():
        b = bh.get(pd.Timestamp(m + "-01", tz="UTC"), np.nan)
        L.append(f"| {m} | {b:+.1f} | {int(r['trades'])} | {int(r['wins'])} | {r['wins']/r['trades']*100:.0f} | {r['net_r']:+.1f} | {r['pnl']:+.1f} | {r['eq']:.0f} |")
    pos = int((g["net_r"] > 0).sum())
    L += ["", f"- Total trades: **{len(d)}** in {len(g)} months with at least one closed trade (avg {len(d)/len(g):.1f} per month, "
          f"about {len(d)/ (len(df)/24/365):.0f} per year).",
          f"- Profitable months: {pos} of {len(g)}. Losing months: {len(g)-pos}. Best {g['net_r'].idxmax()} ({g['net_r'].max():+.1f} R), "
          f"worst {g['net_r'].idxmin()} ({g['net_r'].min():+.1f} R).",
          f"- End equity {eq:.0f} (from {START_EQ:.0f}).", ""]
    for y in sorted({m[:4] for m in g.index}):
        gy = g[[m.startswith(y) for m in g.index]]
        L.append(f"- {y}: {int(gy['trades'].sum())} trades, win {gy['wins'].sum()/gy['trades'].sum()*100:.0f}%, net {gy['net_r'].sum():+.1f} R, P/L {gy['pnl'].sum():+.0f}")
    return L


def trades_csv(df: pd.DataFrame, eq0: float = 10000.0) -> pd.DataFrame:
    masks, a = clue_masks(df)
    tr = base_trades(df, v2_condition(df, masks), a, WARM, len(df))
    eq, rows = eq0, []
    for t in tr:
        risk_amt = eq * RISK
        pnl = risk_amt * t.net_r
        eq += pnl
        rows.append(dict(entry_time=df.index[t.entry_idx], exit_time=df.index[t.exit_idx], entry=round(t.entry, 2), stop=round(t.stop, 2),
                         exit=round(t.exit, 2), reason=t.reason, stop_pct=round(t.risk_pct, 2), risk_amount=round(risk_amt, 2),
                         notional=round(risk_amt / (t.risk_pct / 100), 0), net_r=round(t.net_r, 3), pnl=round(pnl, 2), equity=round(eq, 2)))
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="PAXGUSDT")
    ap.add_argument("--days", type=int, default=1095)
    ap.add_argument("--out", default="monthly_out")
    ap.add_argument("--synthetic", action="store_true")
    a = ap.parse_args()
    df = make_null_1h(24 * 900, 17) if a.synthetic else fetch_klines(a.symbol, "1h", a.days, 3_600_000)
    L = report(df, a.symbol)
    out = Path(a.out)
    out.mkdir(exist_ok=True)
    (out / "summary.md").write_text("\n".join(L))
    trades_csv(df).to_csv(out / "trades_10k.csv", index=False)
    print("\n".join(L))


if __name__ == "__main__":
    main()
