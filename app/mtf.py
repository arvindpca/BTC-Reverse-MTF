"""Causal multi-timeframe helpers.

1m candles are resampled to 15m / 1h / 4h.  A higher-timeframe bar becomes
usable only AFTER it has fully closed, so every 1m bar sees the last HTF bar
whose close time is <= the 1m bar's own close time.  Nothing here may peek at
future data; tests/test_signals.py checks that by truncating the data.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

OHLCV = ["open", "high", "low", "close", "volume"]


def normalize_1m(df: pd.DataFrame, max_bad_frac: float = 0.001) -> pd.DataFrame:
    """Validate/clean 1m candles. Index = UTC bar-OPEN time. Drops a few bad rows, raises if many."""
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("index must be a DatetimeIndex of bar-open times")
    if "volume" not in df.columns:
        df = df.assign(volume=0.0)
    missing = [c for c in OHLCV if c not in df.columns]
    if missing:
        raise ValueError(f"missing columns: {missing}")
    d = df[OHLCV].astype(float)
    d.index = d.index.tz_localize("UTC") if d.index.tz is None else d.index.tz_convert("UTC")
    d = d[~d.index.duplicated(keep="last")].sort_index()
    finite = np.isfinite(d.to_numpy()).all(axis=1)
    hi_ok = (d["high"] >= d[["open", "close", "low"]].max(axis=1)).to_numpy()
    lo_ok = (d["low"] <= d[["open", "close", "high"]].min(axis=1)).to_numpy()
    good = finite & hi_ok & lo_ok & (d["low"].to_numpy() > 0)
    bad = int((~good).sum())
    if bad > max_bad_frac * max(len(d), 1):
        raise ValueError(f"{bad} invalid OHLC rows out of {len(d)}")
    return d[good]


def resample(df: pd.DataFrame, minutes: int) -> pd.DataFrame:
    """OHLCV resample on the UTC grid (label = bar open). The first (possibly partial) bucket is dropped."""
    r = df.resample(f"{minutes}min", label="left", closed="left")
    out = pd.DataFrame(
        {
            "open": r["open"].first(),
            "high": r["high"].max(),
            "low": r["low"].min(),
            "close": r["close"].last(),
            "volume": r["volume"].sum(),
        }
    ).dropna(subset=["open"])
    return out.iloc[1:]


def last_closed_pos(index_1m: pd.DatetimeIndex, htf_index: pd.DatetimeIndex, minutes: int) -> np.ndarray:
    """For each 1m bar, position of the last HTF bar fully closed by that 1m bar's close (-1 = none yet)."""
    avail = (htf_index + pd.Timedelta(minutes=minutes)).values
    close_t = (index_1m + pd.Timedelta(minutes=1)).values
    return np.searchsorted(avail, close_t, side="right") - 1


def take(arr: np.ndarray, pos: np.ndarray) -> np.ndarray:
    """arr[pos] as float, NaN where pos < 0."""
    out = np.full(len(pos), np.nan)
    m = pos >= 0
    out[m] = np.asarray(arr, dtype=float)[pos[m]]
    return out


def ema(x, n: int) -> np.ndarray:
    return np.array(pd.Series(np.asarray(x, dtype=float)).ewm(span=n, adjust=False).mean(), dtype=float)


def rsi(close, n: int = 14) -> np.ndarray:
    s = pd.Series(np.asarray(close, dtype=float))
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    with np.errstate(divide="ignore", invalid="ignore"):
        out = 100 - 100 / (1 + up / dn)
    return np.array(out, dtype=float)


def atr(high, low, close, n: int = 14) -> np.ndarray:
    h, l, c = (pd.Series(np.asarray(x, dtype=float)) for x in (high, low, close))
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return np.array(tr.ewm(alpha=1 / n, adjust=False).mean(), dtype=float)


def efficiency_ratio(close, n: int = 20) -> np.ndarray:
    """Kaufman ER: |net change| / sum |bar changes| over n bars. ~0 = choppy/range, ~1 = clean trend."""
    s = pd.Series(np.asarray(close, dtype=float))
    change = (s - s.shift(n)).abs()
    path = s.diff().abs().rolling(n).sum()
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.array(change / path, dtype=float)
