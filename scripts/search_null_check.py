"""Null control for app.search: on random-walk data the pooled gate must (almost) never say ROBUST CANDIDATE.

    python scripts/search_null_check.py [trials]
"""
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.search import judge, pool, search_asset  # noqa: E402


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
    trials = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    robust = 0
    for t in range(trials):
        t0 = time.time()
        grids = [search_asset(f"RW{t}_{k}", random_walk(200 * 1440, 100 * t + k), 180, 0.6)[0] for k in range(2)]
        assets = [g.asset.iloc[0] for g in grids]
        pooled = pool(grids)
        v, top, info = judge(pooled, assets, 40)
        robust += v.startswith("ROBUST")
        extra = f" best-train pooled test R {info['best'].test_net_r:+.1f} (n={int(info['best'].test_n)})" if info else ""
        print(f"trial {t}: {v.split(':')[0]:22s} configs profitable on pooled test {(pooled.test_net_r > 0).mean():.0%}{extra}  [{time.time() - t0:.0f}s]")
    print(f"ROBUST on pure random data: {robust}/{trials}")
