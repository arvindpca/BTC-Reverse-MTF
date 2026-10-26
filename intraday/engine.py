"""Vectorised single-direction backtester.

Rules
  * signal on CLOSED bar i  ->  market entry at OPEN of bar i+1
  * stop = sl_atr x ATR(i), target = rr x stop, time stop after `hold` bars (exit at that bar's close)
  * stop and target touched in the same candle -> STOP is assumed first (pessimistic)
  * a gap through the stop fills at the bar open (worse than the stop); target fills at the target price
  * trades whose outcome is not known before the data ends are dropped (no peeking past the end)
  * one position at a time per config: a new signal is taken only if its bar is at/after the previous exit bar
  * costs: (fee x (1+GST) + slippage) per side, both sides; funding charged for every 00/08/16 UTC crossed
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

EIGHT_H_NS = 8 * 3600 * 10**9


@dataclass
class Bars:
    o: np.ndarray
    h: np.ndarray
    l: np.ndarray
    c: np.ndarray
    atr: np.ndarray
    t_open_ns: np.ndarray   # int64 bar open times
    step_ns: int

    @classmethod
    def from_frame(cls, f, step_minutes: int):
        t = np.asarray((f.index - f.index[0]) // np.timedelta64(1, "ns"), dtype="int64") + f.index[0].value
        return cls(f["open"].to_numpy(float), f["high"].to_numpy(float), f["low"].to_numpy(float),
                   f["close"].to_numpy(float), f["atr"].to_numpy(float), t, step_minutes * 60 * 10**9)


@dataclass
class Candidates:
    """Outcome of every signal as if it were taken (before the one-position rule)."""
    sig: np.ndarray        # signal bar index
    exit_bar: np.ndarray
    entry: np.ndarray
    exit: np.ndarray
    reason: np.ndarray     # 0=SL 1=TP 2=TIME
    risk_frac: np.ndarray  # stop distance / entry
    gross_ret: np.ndarray
    funding_n: np.ndarray
    side: int


def candidates(b: Bars, sig_mask: np.ndarray, side: int, sl_atr: float, rr: float, hold: int,
               warmup: int = 0) -> Candidates:
    n = len(b.o)
    sig = np.flatnonzero(sig_mask[: n - 1])
    sig = sig[(sig >= warmup) & np.isfinite(b.atr[sig]) & (b.atr[sig] > 0)]
    e = sig + 1
    entry = b.o[e]
    d = sl_atr * b.atr[sig]
    idx = e[:, None] + np.arange(hold)[None, :]
    valid = idx < n
    idx = np.minimum(idx, n - 1)
    lo, hi, op = b.l[idx], b.h[idx], b.o[idx]
    if side > 0:
        sl, tp = entry - d, entry + rr * d
        hit_sl, hit_tp = (lo <= sl[:, None]) & valid, (hi >= tp[:, None]) & valid
    else:
        sl, tp = entry + d, entry - rr * d
        hit_sl, hit_tp = (hi >= sl[:, None]) & valid, (lo <= tp[:, None]) & valid
    k_sl = np.where(hit_sl.any(1), hit_sl.argmax(1), hold)
    k_tp = np.where(hit_tp.any(1), hit_tp.argmax(1), hold)
    k = np.minimum(k_sl, k_tp)
    reason = np.where(k == hold, 2, np.where(k_sl <= k_tp, 0, 1))
    k_eff = np.where(reason == 2, hold - 1, k)
    complete = (reason != 2) | valid[:, -1]
    rows = np.arange(len(sig))
    o_k = op[rows, k_eff]
    c_k = b.c[idx[rows, k_eff]]
    sl_fill = np.minimum(o_k, sl) if side > 0 else np.maximum(o_k, sl)
    exit_px = np.where(reason == 0, sl_fill, np.where(reason == 1, tp, c_k))
    exit_bar = np.minimum(e + k_eff, n - 1)   # incomplete trades are dropped below
    t_in = b.t_open_ns[e]
    t_out = b.t_open_ns[exit_bar] + b.step_ns
    funding_n = t_out // EIGHT_H_NS - t_in // EIGHT_H_NS
    gross = side * (exit_px - entry) / entry
    m = complete
    return Candidates(sig[m], exit_bar[m], entry[m], exit_px[m], reason[m], (d / entry)[m], gross[m],
                      funding_n[m], side)


def select(cand: Candidates, keep: np.ndarray | None = None) -> np.ndarray:
    """Indices into cand that are actually traded under the one-position-at-a-time rule."""
    order = np.flatnonzero(keep) if keep is not None else np.arange(len(cand.sig))
    taken, busy_until = [], -1
    sig, xb = cand.sig, cand.exit_bar
    for j in order:
        if sig[j] >= busy_until:
            taken.append(j)
            busy_until = xb[j]
    return np.asarray(taken, dtype=int)


def net_returns(cand: Candidates, taken: np.ndarray, cost_side_pct: float, funding_pct: float):
    """Returns (net_ret, net_R, gross_R) for the taken trades. Percent inputs, fractional outputs."""
    g = cand.gross_ret[taken]
    net = g - 2 * cost_side_pct / 100 - cand.funding_n[taken] * funding_pct / 100
    rf = cand.risk_frac[taken]
    return net, net / rf, g / rf
