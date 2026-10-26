"""Candle validation + cleaning. Nothing is invented: missing bars stay missing (no forward fill)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .data import TF_MIN


def clean(raw: pd.DataFrame, tf: str) -> tuple[pd.DataFrame, dict]:
    rep: dict = {"tf": tf, "rows_raw": int(len(raw))}
    df = raw.copy()
    if df.index.tz is None:
        raise ValueError("index must be timezone-aware UTC")
    df.index = df.index.tz_convert("UTC")
    step = pd.Timedelta(minutes=TF_MIN[tf])

    rep["duplicates"] = int(df.index.duplicated().sum())
    df = df[~df.index.duplicated(keep="last")].sort_index()

    secs = np.asarray((df.index - pd.Timestamp(0, tz="UTC")) // pd.Timedelta(seconds=1), dtype="int64")
    off_grid = secs % int(step.total_seconds()) != 0
    rep["off_grid_timestamps"] = int(off_grid.sum())
    df = df[~off_grid]

    bad = (df[["open", "high", "low", "close"]] <= 0).any(axis=1) | df[["open", "high", "low", "close"]].isna().any(axis=1)
    bad |= df["high"] < df[["open", "close"]].max(axis=1) - 1e-12
    bad |= df["low"] > df[["open", "close"]].min(axis=1) + 1e-12
    rep["invalid_ohlc_dropped"] = int(bad.sum())
    df = df[~bad]

    rep["zero_volume_bars"] = int((df["volume"].fillna(0) <= 0).sum())
    lr = np.log(df["close"]).diff()
    mad = (lr - lr.median()).abs().median() or 1e-12
    z = (lr - lr.median()).abs() / (1.4826 * mad)
    rep["outlier_bars_robust_z_gt_15"] = int((z > 15).sum())
    rep["largest_abs_bar_return_pct"] = round(float(lr.abs().max() * 100), 3) if len(lr) > 1 else None

    full = pd.date_range(df.index[0], df.index[-1], freq=step, tz="UTC")
    missing = full.difference(df.index)
    rep["first_bar"] = str(df.index[0])
    rep["last_bar"] = str(df.index[-1])
    rep["coverage_days"] = round((df.index[-1] - df.index[0]) / pd.Timedelta(days=1), 2)
    rep["expected_bars"] = int(len(full))
    rep["rows_clean"] = int(len(df))
    rep["missing_bars"] = int(len(missing))
    rep["missing_pct"] = round(100 * len(missing) / max(len(full), 1), 3)
    gaps = df.index.to_series().diff()
    big = gaps[gaps > step].sort_values(ascending=False).head(10)
    rep["largest_gaps"] = [{"ends_at": str(i), "length": str(g)} for i, g in big.items()]
    df["gap_before"] = gaps.fillna(step) > step
    return df, rep


def quality_verdict(rep: dict, min_days: float) -> tuple[str, list[str]]:
    issues = []
    if rep["coverage_days"] < min_days * 0.9:
        issues.append(f"coverage {rep['coverage_days']}d is below the {min_days}d target")
    if rep["missing_pct"] > 2:
        issues.append(f"{rep['missing_pct']}% bars missing")
    if rep["outlier_bars_robust_z_gt_15"] > 0:
        issues.append(f"{rep['outlier_bars_robust_z_gt_15']} extreme-return bars (kept, flagged)")
    if rep["zero_volume_bars"] > 0.05 * rep["rows_clean"]:
        issues.append(f"{rep['zero_volume_bars']} zero-volume bars (volume features less reliable)")
    status = "OK" if not issues else ("WARN" if rep["coverage_days"] >= 60 and rep["missing_pct"] <= 5 else "POOR")
    return status, issues


def resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """OHLCV bars indexed by OPEN time (label=left)."""
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    out = df[list(agg)].resample(rule, label="left", closed="left").agg(agg)
    return out.dropna(subset=["open"])
