"""Trade statistics. R = net return / initial stop distance (1R = the planned loss)."""
from __future__ import annotations

import numpy as np


def stats(R: np.ndarray, ret: np.ndarray | None = None, *, bars_in_trade: int = 0, total_bars: int = 0,
          risk: float = 0.01, start: float = 1000.0) -> dict:
    R = np.asarray(R, float)
    n = len(R)
    if n == 0:
        return {"n": 0}
    wins, losses = R[R > 0], R[R <= 0]
    gp, gl = wins.sum(), -losses.sum()
    sd = R.std(ddof=1) if n > 1 else np.nan
    eq = start * np.cumprod(1 + risk * R)
    peak = np.maximum.accumulate(np.concatenate([[start], eq]))[1:]
    dd = (peak - eq) / peak
    streak = best = 0
    for r in R:
        streak = streak + 1 if r <= 0 else 0
        best = max(best, streak)
    out = {
        "n": n,
        "win_rate": round(float(len(wins) / n), 4),
        "exp_R": round(float(R.mean()), 4),
        "sum_R": round(float(R.sum()), 2),
        "pf": round(float(gp / gl), 3) if gl > 0 else (np.inf if gp > 0 else np.nan),
        "avg_win_R": round(float(wins.mean()), 3) if len(wins) else 0.0,
        "avg_loss_R": round(float(losses.mean()), 3) if len(losses) else 0.0,
        "t_stat": round(float(R.mean() / sd * np.sqrt(n)), 3) if n > 1 and sd > 0 else 0.0,
        "max_dd_pct": round(float(dd.max() * 100), 2),
        "max_loss_streak": int(best),
        "end_equity": round(float(eq[-1]), 2),
    }
    if ret is not None:
        out["exp_ret_pct"] = round(float(np.mean(ret) * 100), 4)
    if total_bars:
        out["exposure_pct"] = round(100 * bars_in_trade / total_bars, 2)
    return out


def equity_curve(R: np.ndarray, risk: float = 0.01, start: float = 1000.0):
    eq = start * np.cumprod(1 + risk * np.asarray(R, float))
    peak = np.maximum.accumulate(np.concatenate([[start], eq]))[1:]
    return eq, (peak - eq) / peak
