"""Synthetic 1m candles for tests and pipeline smoke runs ONLY. Results on this data mean nothing."""
from __future__ import annotations

import numpy as np
import pandas as pd


def make_synthetic(n: int = 60 * 24 * 30, seed: int = 7, start: str = "2026-01-01", base: float = 60000.0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    vol = np.repeat(rng.choice([0.0004, 0.0008, 0.0016], size=n // 720 + 1), 720)[:n]
    ret = rng.normal(0.0, vol)
    slow = 0.0
    for i in range(n):  # weak mean-reverting wobble so sweeps/rejections occur
        slow = 0.995 * slow + ret[i]
        ret[i] -= 0.02 * slow
    close = base * np.exp(np.cumsum(ret))
    open_ = np.concatenate([[base], close[:-1]])
    wick = np.abs(rng.normal(0.0, vol * 0.6))
    high = np.maximum(open_, close) * (1 + wick)
    low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0.0, vol * 0.6)))
    idx = pd.date_range(start, periods=n, freq="1min", tz="UTC")
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close,
                         "volume": rng.uniform(1, 10, n)}, index=idx)


def make_random_walk(n: int, seed: int = 0, base: float = 60000.0) -> pd.DataFrame:
    """Pure iid random walk (no edge by construction) - the null control for every study."""
    rng = np.random.default_rng(seed)
    vol = np.repeat(rng.choice([0.0004, 0.0008, 0.0016], size=n // 720 + 1), 720)[:n]
    close = base * np.exp(np.cumsum(rng.normal(0.0, vol)))
    open_ = np.concatenate([[base], close[:-1]])
    high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0.0, vol * 0.6)))
    low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0.0, vol * 0.6)))
    idx = pd.date_range("2026-01-01", periods=n, freq="1min", tz="UTC")
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": rng.uniform(1, 10, n)}, index=idx)
