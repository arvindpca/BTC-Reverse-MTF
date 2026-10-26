"""All research settings in one place. Saved next to every run (config.json) so results are reproducible."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

DEFAULTS: dict = {
    "exchange": "CoinDCX",
    "market": "USDT-margined perpetual futures (pcode=f)",
    # Asset label -> CoinDCX futures pair. Verified against the live instrument list at run time; never substituted.
    "symbols": {"BTC": "B-BTC_USDT", "PAXG": "B-PAXG_USDT"},
    "timeframes": ["5m", "15m"],
    "days": 180,
    # Costs (per side, % of notional). CoinDCX futures taker fee is configurable; GST (18%) is charged on the fee.
    "fee_per_side_pct": 0.05,
    "gst_on_fee": 0.18,
    "slippage_per_side_pct": 0.02,   # includes half-spread
    # Funding: real per-interval history is not available from the public API used here, so a flat
    # conservative rate is CHARGED (never credited) for every funding time crossed (00/08/16 UTC).
    "funding_pct_per_8h": 0.01,
    "cost_multipliers": [0.0, 0.5, 1.0, 1.5, 2.0],
    # Chronological split of bars: development / validation / untouched test.
    "split": [0.50, 0.25, 0.25],
    "warmup_bars": 300,
    # Exit grid (ATR based stop, reward multiple, time stop in hours)
    "sl_atr": [1.0, 2.0, 3.0],
    "rr": [1.0, 1.5, 2.0, 3.0],
    "max_hold_hours": [3, 8],
    # Selection
    "min_trades_dev": 40,
    "min_trades_val": 20,
    "min_trades_test": 30,
    "top_base_per_dir": 10,
    "pair_filters_per_base": 6,
    "finalists_per_dir": 3,
    "null_seeds": 20,
    # Walk-forward (days)
    "wf_train_days": 60,
    "wf_test_days": 20,
    # Money view (fixed-fractional, compounding)
    "start_equity": 1000.0,
    "risk_per_trade": 0.01,
    "leverage_cap": 30,
    # Verdict thresholds
    "verdict": {"test_pf_min": 1.15, "wf_pos_folds_min": 0.5, "null_pct_min": 0.95},
    "seed": 7,
}


def load(path: str | Path | None = None, **overrides) -> dict:
    cfg = deepcopy(DEFAULTS)
    if path:
        cfg.update(json.loads(Path(path).read_text()))
    for k, v in overrides.items():
        if v is not None:
            cfg[k] = v
    return cfg


def cost_per_side_pct(cfg: dict, mult: float = 1.0) -> float:
    return mult * (cfg["fee_per_side_pct"] * (1 + cfg["gst_on_fee"]) + cfg["slippage_per_side_pct"])


def save(cfg: dict, path: str | Path) -> None:
    Path(path).write_text(json.dumps(cfg, indent=2))
