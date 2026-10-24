"""PAPER trading runner for the PAXG candidate (v2). No orders are ever sent anywhere.

Each run (hourly, from GitHub Actions) re-plays the exact backtest engine from a fixed start time on the latest closed 1h
candles. Because the whole result is recomputed from candle data, it is restart-safe and cannot create duplicate entries:
a signal is identified by its candle time, one position at a time, one entry per signal.

v2 rule: long when efficiency ratio(20) > 0.40 AND the last 3 hourly candles are green, first candle where this becomes true,
outside UTC 08-14, stop = 4 x ATR(14) below the close, trailing exit (starts at 1.5R, follows 1R), 2% of equity risked.
"""
from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd

from . import reverse_eng as re_
from .detail import cond_of
from .notify import build_events, send_telegram
from .paper import PaperConfig, client_order_id, size_position
from .refine import LEAD, trades_of
from .reverse_eng import clue_masks, fetch_klines

STOP_ATR, RISK, START_EQ, WARM = 4.0, 0.02, 300.0, 700
CFG = PaperConfig(margin=300.0, leverage=30)


def v2_condition(df, masks):
    h = df.index.hour
    return cond_of(masks, LEAD) & ~((h >= 8) & (h < 14))


def trailing_state(df, tr):
    """Current stop and best price of an open long, replaying the engine's own trailing rules up to the last bar."""
    o, hh, ll = df["open"].to_numpy(), df["high"].to_numpy(), df["low"].to_numpy()
    ep = re_.EP
    risk = tr.entry - tr.stop
    cur, best = tr.stop, tr.entry
    for t in range(tr.entry_idx + 1, len(df)):
        best = max(best, hh[t])
        run_r = best - tr.entry
        if run_r >= ep.trail_start_r * risk and best - ep.trail_r * risk > cur:
            cur = best - ep.trail_r * risk
    return cur, best


def evaluate(df: pd.DataFrame, start_ts: pd.Timestamp, risk: float = RISK, eq0: float = START_EQ) -> dict:
    n = len(df)
    masks, a = clue_masks(df)
    cond = v2_condition(df, masks)
    lo = max(WARM, int(df.index.searchsorted(start_ts)))
    trades = trades_of(df, cond, a, lo, n, None, STOP_ATR)
    max_hold = re_.EP.max_hold
    open_tr = None
    if trades:
        t = trades[-1]
        if t.exit_idx == n - 1 and t.reason == "TIME" and (t.exit_idx - t.entry_idx) < max_hold:
            open_tr, trades = t, trades[:-1]
    eq, rows = eq0, []
    for t in trades:
        pnl = eq * risk * t.net_r
        eq += pnl
        rows.append(dict(entry_time=str(df.index[t.entry_idx]), exit_time=str(df.index[t.exit_idx]), entry=t.entry,
                         stop=t.stop, exit=t.exit, reason=t.reason, net_r=round(t.net_r, 3), pnl=round(pnl, 2), equity=round(eq, 2)))
    out = dict(last_candle=str(df.index[-1]), last_close=float(df["close"].iloc[-1]), equity=eq, closed=rows, open=None, skipped=None)
    if open_tr:
        cur, best = trailing_state(df, open_tr)
        stop_pct = (open_tr.entry - open_tr.stop) / open_tr.entry * 100
        sized, why = size_position(CFG, open_tr.entry, open_tr.stop)
        notional = eq * risk / (stop_pct / 100)
        sig = str(df.index[open_tr.entry_idx])
        out["open"] = dict(signal_id=sig, client_order_id=client_order_id(sig), side="LONG", entry_time=sig, entry=open_tr.entry,
                           initial_stop=open_tr.stop, current_stop=cur, best_price=best, stop_pct=stop_pct,
                           notional=notional, qty=notional / open_tr.entry, margin_at_30x=notional / CFG.leverage,
                           liquidation=open_tr.entry * (1 - CFG.liq_dist_pct / 100), guard=why,
                           unrealized_pct=(float(df["close"].iloc[-1]) / open_tr.entry - 1) * 100,
                           unrealized_pnl=notional * (float(df["close"].iloc[-1]) / open_tr.entry - 1))
    return out


def report(res: dict, start_ts: pd.Timestamp, symbol: str) -> str:
    L = [f"# PAPER trading: {symbol} candidate v2", "",
         f"Started {start_ts:%Y-%m-%d %H:%M} UTC. Last closed candle: {res['last_candle']} (close {res['last_close']:.2f}). "
         f"Paper equity: **{res['equity']:.2f}** (start {START_EQ:.0f}, risk {RISK*100:.0f}% per trade, fees 0.16% round trip assumed). "
         "No orders are placed; this is a log only.", ""]
    o = res["open"]
    if o:
        L += ["## OPEN paper position", "",
              f"- LONG since {o['entry_time']} at {o['entry']:.2f} (signal id `{o['signal_id']}`, order id `{o['client_order_id']}`)",
              f"- initial stop {o['initial_stop']:.2f} ({o['stop_pct']:.2f}% away), **current stop {o['current_stop']:.2f}**, best price {o['best_price']:.2f}",
              f"- size: notional {o['notional']:.0f}, qty {o['qty']:.4f}, margin at 30x {o['margin_at_30x']:.1f}, "
              f"liquidation about {o['liquidation']:.2f}",
              f"- unrealized: {o['unrealized_pct']:+.2f}% = {o['unrealized_pnl']:+.2f}", ""]
    else:
        L += ["## No open position", "", "Waiting for a signal (efficiency ratio > 0.40 + 3 green candles, outside UTC 08-14).", ""]
    c = res["closed"]
    if c:
        w = sum(1 for r in c if r["net_r"] > 0)
        L += [f"## Closed trades: {len(c)} (wins {w}, net {sum(r['net_r'] for r in c):+.1f} R)", "",
              "| entry | exit | entry px | exit px | reason | R | P/L | equity |", "|---|---|---|---|---|---|---|---|"]
        for r in c[-30:]:
            L.append(f"| {r['entry_time'][:16]} | {r['exit_time'][:16]} | {r['entry']:.2f} | {r['exit']:.2f} | {r['reason']} | "
                     f"{r['net_r']:+.2f} | {r['pnl']:+.2f} | {r['equity']:.2f} |")
    else:
        L += ["## Closed trades: none yet", ""]
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="PAXGUSDT")
    ap.add_argument("--state", default="paper_out/state.json")
    ap.add_argument("--out", default="paper_out")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    sp = Path(a.state)
    now = pd.Timestamp.now(tz="UTC")
    state = json.loads(sp.read_text()) if sp.exists() else {}
    start = pd.Timestamp(state["start"]) if "start" in state else now.floor("1h")
    days = max(40, math.ceil((now - start).total_seconds() / 86400) + 40)
    df = fetch_klines(a.symbol, "1h", days, 3_600_000)
    df = df[df.index + pd.Timedelta(hours=1) <= now]            # drop the still-forming candle
    res = evaluate(df, start)
    for m in build_events(res, state, a.symbol):
        send_telegram(m)
    state.update(start=str(start), symbol=a.symbol, updated=str(now), last_candle=res["last_candle"])
    (out / "state.json").write_text(json.dumps(state, indent=1))
    (out / "result.json").write_text(json.dumps(res, indent=1, default=str))
    (out / "report.md").write_text(report(res, start, a.symbol))
    print((out / "report.md").read_text())


if __name__ == "__main__":
    main()
