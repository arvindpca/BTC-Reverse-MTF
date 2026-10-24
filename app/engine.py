"""Stop-and-reverse trade simulator on the 1m grid.

Rules (pessimistic where candle order is unknown):
  * entry at the signal bar's CLOSE; one position at a time; one entry per 15m setup id
  * stop is checked before target inside the same candle; gaps through the stop fill at the open
  * optional break-even: once price has run `be_r` x R the stop moves to entry from the NEXT bar
  * time stop after `max_hold` 1m bars
  * REVERSE: an opposite, valid signal while in a trade closes it at that bar's close and flips
  * costs: (fee + slippage) per side, charged in R as round_trip_pct / risk_pct
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class EngineParams:
    rr: float = 2.0
    be_r: float | None = 1.0
    max_hold: int = 720          # 1m bars (12h)
    fee_pct: float = 0.06        # per side, % of notional
    slip_pct: float = 0.02       # per side, % of notional
    min_risk_pct: float = 0.25   # skip stops so tight that costs eat the edge
    max_risk_pct: float = 2.5
    reverse: bool = True
    trail_r: float | None = None  # trailing stop distance in R, behind the best price
    trail_start_r: float = 1.0    # trailing arms once price has run this many R


@dataclass
class Trade:
    entry_idx: int
    exit_idx: int
    side: int
    entry: float
    stop: float
    exit: float
    reason: str
    risk_pct: float
    gross_r: float
    net_r: float


def _scan_exit(o, h, l, c, k, side, entry, stop, p: EngineParams, end: int):
    risk = abs(entry - stop)
    tp = entry + side * p.rr * risk
    cur, best, kind = stop, entry, "SL"
    for t in range(k + 1, end + 1):
        if side > 0:
            if l[t] <= cur:
                return t, min(cur, o[t]), kind
            if h[t] >= tp:
                return t, tp, "TP"
            best = max(best, h[t])
        else:
            if h[t] >= cur:
                return t, max(cur, o[t]), kind
            if l[t] <= tp:
                return t, tp, "TP"
            best = min(best, l[t])
        run_r = side * (best - entry)
        if p.be_r is not None and kind == "SL" and run_r >= p.be_r * risk:
            cur, kind = entry, "BE"
        if p.trail_r is not None and run_r >= p.trail_start_r * risk:
            t_stop = best - side * p.trail_r * risk
            if (side > 0 and t_stop > cur) or (side < 0 and t_stop < cur):
                cur, kind = t_stop, "TRAIL"
    return end, c[end], "TIME"


def run(o, h, l, c, side, stop, setup_id, p: EngineParams, lo: int = 0, hi: int | None = None) -> list[Trade]:
    n = len(c)
    hi = n if hi is None else min(hi, n)
    cand = (np.flatnonzero(side[lo:hi] != 0) + lo).tolist()
    ol, hl, ll, cl = (np.asarray(x, dtype=float).tolist() for x in (o, h, l, c))
    used: set[int] = set()
    trades: list[Trade] = []
    free, i = lo - 1, 0

    def ok(k: int) -> bool:
        if k >= hi - 1 or int(setup_id[k]) in used:
            return False
        e = cl[k]
        rp = abs(e - float(stop[k])) / e * 100.0
        return p.min_risk_pct <= rp <= p.max_risk_pct

    while i < len(cand):
        k = cand[i]
        if k <= free or not ok(k):
            i += 1
            continue
        s = int(side[k])
        entry, st = cl[k], float(stop[k])
        used.add(int(setup_id[k]))
        end = min(hi - 1, k + p.max_hold)
        e_idx, e_px, reason = _scan_exit(ol, hl, ll, cl, k, s, entry, st, p, end)

        flip = None
        if p.reverse:
            j = i + 1
            while j < len(cand) and cand[j] < e_idx:
                if int(side[cand[j]]) == -s and ok(cand[j]):
                    flip = j
                    break
                j += 1
        if flip is not None:
            e_idx, e_px, reason = cand[flip], cl[cand[flip]], "REVERSE"

        risk = abs(entry - st)
        rp = risk / entry * 100.0
        gross = s * (e_px - entry) / risk
        cost = 2.0 * (p.fee_pct + p.slip_pct) / rp
        trades.append(Trade(k, e_idx, s, entry, st, e_px, reason, rp, gross, gross - cost))
        if flip is not None:
            free, i = e_idx - 1, flip
        else:
            free, i = e_idx, i + 1
    return trades


def summarize(trades: list[Trade]) -> dict:
    n = len(trades)
    if n == 0:
        return dict(n=0, win_rate=0.0, net_r=0.0, avg_net_r=0.0, gross_r=0.0, cost_r=0.0,
                    pf=0.0, max_dd_r=0.0, t_stat=0.0, ss=0.0, net_half_r=0.0)
    net = np.array([t.net_r for t in trades])
    gross = np.array([t.gross_r for t in trades])
    wins, losses = net[net > 0].sum(), -net[net < 0].sum()
    eq = np.cumsum(net)
    dd = float((np.maximum.accumulate(np.maximum(eq, 0.0)) - eq).max())
    sd = net.std(ddof=1) if n > 1 else 0.0
    return dict(
        n=n, win_rate=float((net > 0).mean()), net_r=float(net.sum()), avg_net_r=float(net.mean()),
        gross_r=float(gross.sum()), cost_r=float(gross.sum() - net.sum()),
        pf=float(wins / losses) if losses > 0 else (float("inf") if wins > 0 else 0.0),
        max_dd_r=dd, t_stat=float(net.mean() / (sd / np.sqrt(n))) if sd > 0 else 0.0,
        ss=float((net ** 2).sum()),                       # for pooling t-stats across assets
        net_half_r=float(gross.sum() - 0.5 * (gross.sum() - net.sum())),  # net if costs were half
    )
