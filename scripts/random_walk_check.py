"""Null control: on pure random-walk data (no edge by construction) the harness must NOT find one.

Expected: gross R/trade ~ 0, net R/trade clearly negative (costs), few configs profitable on test,
verdict "NO EDGE PROVEN". If this ever prints a CANDIDATE on random data, something leaks.

    python scripts/random_walk_check.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.research import run_asset, verdict  # noqa: E402


def random_walk(n: int, seed: int, base: float = 60000.0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    vol = np.repeat(rng.choice([0.0004, 0.0008, 0.0016], size=n // 720 + 1), 720)[:n]
    close = base * np.exp(np.cumsum(rng.normal(0, vol)))
    open_ = np.concatenate([[base], close[:-1]])
    high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, vol * 0.6)))
    low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, vol * 0.6)))
    idx = pd.date_range("2026-01-01", periods=n, freq="1min", tz="UTC")
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": 1.0}, index=idx)


if __name__ == "__main__":
    for seed in range(3):
        grid, _ = run_asset(f"RW{seed}", random_walk(180 * 1440, seed), 0.6, quick=False)
        v, _ = verdict(grid)
        g = grid[grid.test_n >= 30]
        print(f"seed {seed}: {v.split(':')[0]:16s} gross R/trade {g.test_gross_r.sum() / g.test_n.sum():+.3f} | "
              f"net R/trade {g.test_avg_net_r.mean():+.3f} | configs profitable on test {(grid.test_net_r > 0).mean():.0%}")
