"""Three more strategy families on the same 4h / 1h / 15m / 1m stack. All causal.

  donchian : 1h Donchian breakout (trend) - 4h trend filter, optional 15m EMA confirmation
  bollinger: 1h Bollinger-band fade (mean reversion) - optional 4h range regime
  ema_sar  : 1h EMA cross stop-and-reverse (flip on every opposite cross)

Entry is the close of the 1m bar on which a 1h bar finishes, so the signal only uses closed candles.
Stops are ATR(1h) multiples (wide enough that costs are a small part of 1R). `invert=True` mirrors the signal.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .mtf import ema, take
from .signals import ER_RANGE, Features, Signals


def _first_bar_mask(pos: np.ndarray) -> np.ndarray:
    """True on the first 1m bar after each new closed HTF bar (== the bar that closes it)."""
    prev = np.concatenate([[-2], pos[:-1]])
    return (pos != prev) & (pos >= 0)


def _htf_ok(f: Features, htf: str) -> tuple[np.ndarray, np.ndarray]:
    n = len(f.c)
    if htf == "with":
        with np.errstate(invalid="ignore"):
            return f.trend4h > 0, f.trend4h < 0
    if htf == "range":
        with np.errstate(invalid="ignore"):
            ok = f.er4h <= ER_RANGE
        return ok, ok
    if htf == "any":
        ones = np.ones(n, dtype=bool)
        return ones, ones
    raise ValueError("htf must be any|with|range")


def _confirm15(f: Features, on: bool) -> tuple[np.ndarray, np.ndarray]:
    n = len(f.c)
    if not on:
        ones = np.ones(n, dtype=bool)
        return ones, ones
    c15 = take(f.c15, f.pos15)
    e15 = take(ema(f.c15, 20), f.pos15)
    with np.errstate(invalid="ignore"):
        return c15 > e15, c15 < e15


def _hits(flag_per_1h: np.ndarray, pos60: np.ndarray) -> np.ndarray:
    """Map a per-1h-bar boolean onto the 1m grid (False where undefined)."""
    return take(flag_per_1h.astype(float), pos60) == 1.0


def _finish(f: Features, long_ok: np.ndarray, short_ok: np.ndarray, atr_mult: float, invert: bool) -> Signals:
    a = take(f.atr60, f.pos60)
    good = np.isfinite(a)
    long_ok, short_ok = long_ok & good, short_ok & good
    side = np.zeros(len(f.c), dtype=np.int8)
    side[long_ok] = 1
    side[short_ok & ~long_ok] = -1
    stop = np.where(side == 1, f.c - atr_mult * a, np.where(side == -1, f.c + atr_mult * a, np.nan))
    sid = np.where(side != 0, f.pos60, -1).astype(np.int64)
    if invert:
        active = side != 0
        stop = np.where(active, 2.0 * f.c - stop, np.nan)
        side = (-side).astype(np.int8)
    return Signals(side=side, stop=stop, setup_id=sid)


def donchian(f: Features, N: int = 20, atr_mult: float = 2.0, htf: str = "any", confirm15: bool = False,
             invert: bool = False) -> Signals:
    hi = pd.Series(f.h60).shift(1).rolling(N).max().to_numpy()
    lo = pd.Series(f.l60).shift(1).rolling(N).min().to_numpy()
    with np.errstate(invalid="ignore"):
        up, dn = f.c60 > hi, f.c60 < lo
    first = _first_bar_mask(f.pos60)
    hl, hs = _htf_ok(f, htf)
    cl, cs = _confirm15(f, confirm15)
    return _finish(f, first & _hits(up, f.pos60) & hl & cl, first & _hits(dn, f.pos60) & hs & cs, atr_mult, invert)


def bollinger(f: Features, k: float = 2.0, atr_mult: float = 2.0, htf: str = "any", invert: bool = False) -> Signals:
    s = pd.Series(f.c60)
    mid, sd = s.rolling(20).mean(), s.rolling(20).std(ddof=0)
    lower, upper = (mid - k * sd).to_numpy(), (mid + k * sd).to_numpy()
    with np.errstate(invalid="ignore"):
        below, above = f.c60 < lower, f.c60 > upper
    first = _first_bar_mask(f.pos60)
    hl, hs = _htf_ok(f, htf)
    return _finish(f, first & _hits(below, f.pos60) & hl, first & _hits(above, f.pos60) & hs, atr_mult, invert)


def ema_sar(f: Features, fast: int = 12, slow: int = 48, atr_mult: float = 2.0, htf: str = "any",
            invert: bool = False) -> Signals:
    ef, es = ema(f.c60, fast), ema(f.c60, slow)
    state = np.where(ef > es, 1, -1)
    state[: slow * 2] = 0  # warm-up
    cross_up = np.zeros(len(state), dtype=bool)
    cross_dn = np.zeros(len(state), dtype=bool)
    cross_up[1:] = (state[1:] == 1) & (state[:-1] == -1)
    cross_dn[1:] = (state[1:] == -1) & (state[:-1] == 1)
    first = _first_bar_mask(f.pos60)
    hl, hs = _htf_ok(f, htf)
    return _finish(f, first & _hits(cross_up, f.pos60) & hl, first & _hits(cross_dn, f.pos60) & hs, atr_mult, invert)
