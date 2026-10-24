"""Four-timeframe reversal (fade) signals, all causal.

  4h  regime / bias : EMA20-vs-EMA50 trend and Kaufman efficiency ratio (range vs trend)
  1h  stretch       : RSI(14) oversold / overbought on the last CLOSED 1h bar
  15m setup         : liquidity sweep - bar takes out the prior K-bar extreme but closes back
                      inside with a rejection body; setup stays valid for M 15m bars
  5m  confirm       : closed 5m structure break in the signal direction
  1m  trigger       : micro break - 1m close beyond the prior T 1m bars' extreme, with the candle

Stop = beyond the sweep extreme (+ small ATR buffer).  `invert=True` mirrors every signal
(trade the opposite side with the same stop distance) so the data can say whether fading or
following the rejection pays.  Signals depend only on candles closed by the signal bar.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .mtf import (atr, efficiency_ratio, ema, last_closed_pos, normalize_1m, resample, rsi,
                  take)

ER_RANGE = 0.30  # 4h efficiency ratio at/below this = range regime


@dataclass(frozen=True)
class SignalParams:
    rsi_lo: float = 35.0        # long needs 1h RSI <= rsi_lo, short needs >= 100 - rsi_lo
    sweep_lookback: int = 12    # 15m bars defining the prior extreme
    setup_valid: int = 4        # 15m bars a sweep stays tradable (incl. the sweep bar)
    htf: str = "any"            # any | with (trade only with 4h trend) | range (only when 4h ER is low)
    trig_lookback: int = 5      # 1m bars for the micro break
    stop_atr_buf: float = 0.1   # x ATR(15m) beyond the sweep extreme
    invert: bool = False
    setup_tf: int = 15          # 15 | 60  minutes: timeframe of the sweep setup (60 = bigger stops)
    stretch_tf: int = 60        # 60 | 240 minutes: timeframe of the RSI stretch
    confirm_5m: bool = True     # require a closed 5m structure-break confirmation
    confirm_lookback_5m: int = 3  # prior closed 5m bars used for confirmation


@dataclass
class Features:
    index: pd.DatetimeIndex
    o: np.ndarray
    h: np.ndarray
    l: np.ndarray
    c: np.ndarray
    trend4h: np.ndarray   # +1 / -1 aligned to 1m (closed 4h bars only)
    er4h: np.ndarray
    rsi1h: np.ndarray
    pos15: np.ndarray
    o15: np.ndarray
    h15: np.ndarray
    l15: np.ndarray
    c15: np.ndarray
    atr15: np.ndarray
    pos5: np.ndarray
    o5: np.ndarray
    h5: np.ndarray
    l5: np.ndarray
    c5: np.ndarray
    rsi4h: np.ndarray
    pos60: np.ndarray
    o60: np.ndarray
    h60: np.ndarray
    l60: np.ndarray
    c60: np.ndarray
    atr60: np.ndarray


@dataclass
class Signals:
    side: np.ndarray      # +1 long, -1 short, 0 none (int8)
    stop: np.ndarray      # initial stop price at signal bars
    setup_id: np.ndarray  # id of the 15m sweep bar behind the signal (int64, -1 none)


def compute_features(df1m: pd.DataFrame) -> Features:
    d = normalize_1m(df1m)
    r4, r1, r15, r5 = resample(d, 240), resample(d, 60), resample(d, 15), resample(d, 5)

    trend = np.where(ema(r4["close"], 20) > ema(r4["close"], 50), 1.0, -1.0)
    trend[:60] = np.nan
    er = efficiency_ratio(r4["close"], 20)
    rs = rsi(r1["close"], 14)
    rs[:42] = np.nan
    a15 = atr(r15["high"], r15["low"], r15["close"], 14)
    a15[:42] = np.nan
    a60 = atr(r1["high"], r1["low"], r1["close"], 14)
    a60[:42] = np.nan
    rs4 = rsi(r4["close"], 14)
    rs4[:42] = np.nan

    p4 = last_closed_pos(d.index, r4.index, 240)
    p1 = last_closed_pos(d.index, r1.index, 60)
    p15 = last_closed_pos(d.index, r15.index, 15)
    p5 = last_closed_pos(d.index, r5.index, 5)
    return Features(
        index=d.index,
        o=d["open"].to_numpy(), h=d["high"].to_numpy(), l=d["low"].to_numpy(), c=d["close"].to_numpy(),
        trend4h=take(trend, p4), er4h=take(er, p4), rsi1h=take(rs, p1),
        pos15=p15,
        o15=r15["open"].to_numpy(), h15=r15["high"].to_numpy(), l15=r15["low"].to_numpy(),
        c15=r15["close"].to_numpy(), atr15=a15,
        pos5=p5, o5=r5["open"].to_numpy(), h5=r5["high"].to_numpy(),
        l5=r5["low"].to_numpy(), c5=r5["close"].to_numpy(),
        rsi4h=take(rs4, p4), pos60=p1,
        o60=r1["open"].to_numpy(), h60=r1["high"].to_numpy(), l60=r1["low"].to_numpy(),
        c60=r1["close"].to_numpy(), atr60=a60,
    )


def _latch(sweep: np.ndarray, level: np.ndarray, valid: int) -> tuple[np.ndarray, np.ndarray]:
    """For each 15m bar: stop level + id of the most recent sweep still within `valid` bars."""
    n = len(sweep)
    lvl = np.full(n, np.nan)
    sid = np.full(n, -1.0)
    last = -10**9
    for j in range(n):
        if sweep[j]:
            last = j
        if j - last < valid:
            lvl[j] = level[last]
            sid[j] = last
    return lvl, sid


def build_signals(f: Features, p: SignalParams) -> Signals:
    if p.htf not in ("any", "with", "range"):
        raise ValueError("htf must be any|with|range")
    if p.setup_tf == 15:
        so, sh, sl, sc, sa, spos = f.o15, f.h15, f.l15, f.c15, f.atr15, f.pos15
    elif p.setup_tf == 60:
        so, sh, sl, sc, sa, spos = f.o60, f.h60, f.l60, f.c60, f.atr60, f.pos60
    else:
        raise ValueError("setup_tf must be 15 or 60")
    if p.stretch_tf == 60:
        rsi_arr = f.rsi1h
    elif p.stretch_tf == 240:
        rsi_arr = f.rsi4h
    else:
        raise ValueError("stretch_tf must be 60 or 240")
    k = p.sweep_lookback
    s_lo, s_hi = pd.Series(sl), pd.Series(sh)
    prior_min = s_lo.shift(1).rolling(k).min().to_numpy()
    prior_max = s_hi.shift(1).rolling(k).max().to_numpy()
    with np.errstate(invalid="ignore"):
        sweep_l = (sl < prior_min) & (sc > prior_min) & (sc > so)
        sweep_s = (sh > prior_max) & (sc < prior_max) & (sc < so)
    stop_l15 = sl - p.stop_atr_buf * sa
    stop_s15 = sh + p.stop_atr_buf * sa
    lvl_l15, id_l15 = _latch(sweep_l, stop_l15, p.setup_valid)
    lvl_s15, id_s15 = _latch(sweep_s, stop_s15, p.setup_valid)
    lvl_l, lvl_s = take(lvl_l15, spos), take(lvl_s15, spos)
    id_l = np.nan_to_num(take(id_l15, spos), nan=-1.0).astype(np.int64)
    id_s = np.nan_to_num(take(id_s15, spos), nan=-1.0).astype(np.int64)

    # Use only the most recent fully closed 5m candle available at this 1m close.
    k5 = p.confirm_lookback_5m
    prior_h5 = pd.Series(f.h5).shift(1).rolling(k5).max().to_numpy()
    prior_l5 = pd.Series(f.l5).shift(1).rolling(k5).min().to_numpy()
    c5 = take(f.c5, f.pos5)
    o5 = take(f.o5, f.pos5)
    h5 = take(prior_h5, f.pos5)
    l5 = take(prior_l5, f.pos5)
    confirm_l = (c5 > h5) & (c5 > o5)
    confirm_s = (c5 < l5) & (c5 < o5)
    if not p.confirm_5m:
        confirm_l = confirm_s = np.ones(len(f.c), dtype=bool)

    t = p.trig_lookback
    hh = pd.Series(f.h).shift(1).rolling(t).max().to_numpy()
    ll = pd.Series(f.l).shift(1).rolling(t).min().to_numpy()
    with np.errstate(invalid="ignore"):
        trig_l = (f.c > hh) & (f.c > f.o)
        trig_s = (f.c < ll) & (f.c < f.o)
        stretched_l = rsi_arr <= p.rsi_lo
        stretched_s = rsi_arr >= 100.0 - p.rsi_lo
        if p.htf == "with":
            htf_l, htf_s = f.trend4h > 0, f.trend4h < 0
        elif p.htf == "range":
            htf_l = htf_s = f.er4h <= ER_RANGE
        else:
            htf_l = htf_s = np.ones(len(f.c), dtype=bool)
        long_ok = (id_l >= 0) & (f.c > lvl_l) & stretched_l & trig_l & htf_l & confirm_l
        short_ok = (id_s >= 0) & (f.c < lvl_s) & stretched_s & trig_s & htf_s & confirm_s

    side = np.zeros(len(f.c), dtype=np.int8)
    side[long_ok] = 1
    side[short_ok & ~long_ok] = -1
    stop = np.where(side == 1, lvl_l, np.where(side == -1, lvl_s, np.nan))
    sid = np.where(side == 1, id_l, np.where(side == -1, id_s, -1)).astype(np.int64)

    if p.invert:
        active = side != 0
        stop = np.where(active, 2.0 * f.c - stop, np.nan)  # mirror the stop distance around the close
        side = (-side).astype(np.int8)
    return Signals(side=side, stop=stop, setup_id=sid)
