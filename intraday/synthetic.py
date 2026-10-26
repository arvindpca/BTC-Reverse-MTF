"""Random-walk candles for offline smoke tests and the null control. Contains NO edge by construction."""
from __future__ import annotations

import numpy as np
import pandas as pd


def make(days: int, minutes: int, seed: int = 0, start_price: float = 4000.0, vol_per_bar: float = 0.0015,
         drop_frac: float = 0.0, end: str = "2026-10-26") -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = int(days * 1440 / minutes)
    idx = pd.date_range(end=pd.Timestamp(end, tz="UTC"), periods=n, freq=f"{minutes}min")
    regime = np.exp(np.cumsum(rng.normal(0, 0.02, n)) * 0.1)
    r = rng.normal(0, vol_per_bar, n) * np.clip(regime, 0.3, 3)
    c = start_price * np.exp(np.cumsum(r))
    o = np.concatenate([[start_price], c[:-1]])
    wick = np.abs(rng.normal(0, vol_per_bar / 2, (2, n))) * c
    h = np.maximum(o, c) + wick[0]
    l = np.minimum(o, c) - wick[1]
    v = rng.lognormal(3, 0.6, n)
    df = pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "volume": v}, index=idx)
    df.index.name = "open_time"
    if drop_frac:
        df = df.drop(df.sample(frac=drop_frac, random_state=seed).index)
    return df
