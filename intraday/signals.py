"""Entry families (setups) and filters. Every mask is evaluated on the CLOSED bar t; entry is next bar's open.

Family masks return (long, short). Filters return (long_ok, short_ok) so each side gets its own meaning
(e.g. 'htf1h' = trade with the 1h trend on both sides).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _b(x):
    return np.asarray(pd.Series(x).fillna(False).astype(bool))


def families(f: pd.DataFrame, seed: int = 7, null_seeds: int = 0) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    c, o, h, l = f["close"], f["open"], f["high"], f["low"]
    pc = c.shift(1)
    fam: dict = {}
    for n in (20, 48):
        fam[f"donchian_bo{n}"] = (c > f[f"don_hi{n}"], c < f[f"don_lo{n}"])
        fam[f"sweep_rev{n}"] = ((l < f[f"don_lo{n}"]) & (c > f[f"don_lo{n}"]) & (f["close_loc"] > 0.5),
                                (h > f[f"don_hi{n}"]) & (c < f[f"don_hi{n}"]) & (f["close_loc"] < 0.5))
    fam["ema_pullback"] = ((f["ema20"] > f["ema50"]) & (l <= f["ema20"]) & (c > f["ema20"]) & (c > o),
                           (f["ema20"] < f["ema50"]) & (h >= f["ema20"]) & (c < f["ema20"]) & (c < o))
    for th in (25, 30):
        r, pr = f["rsi"], f["rsi"].shift(1)
        fam[f"rsi_rev{th}"] = ((pr < th) & (r >= th), (pr > 100 - th) & (r <= 100 - th))
    fam["bb_reentry"] = ((pc < f["bb_lo"].shift(1)) & (c > f["bb_lo"]), (pc > f["bb_up"].shift(1)) & (c < f["bb_up"]))
    for k in (1.5, 2.5):
        fam[f"vwap_rev{k}"] = ((f["vwap_dev"] < -k) & (c > o), (f["vwap_dev"] > k) & (c < o))
    fam["bos"] = (f["bos_up"], f["bos_dn"])
    mh, pmh = f["macd_h"], f["macd_h"].shift(1)
    fam["macd_cross"] = ((pmh <= 0) & (mh > 0), (pmh >= 0) & (mh < 0))
    fam["fvg"] = (f["fvg_up"] & (c > o), f["fvg_dn"] & (c < o))
    fam["ob_retest"] = ((l <= f["ob_b_hi"]) & (c > f["ob_b_hi"]) & ~f["bos_up"],
                        (h >= f["ob_s_lo"]) & (c < f["ob_s_lo"]) & ~f["bos_dn"])
    fam["candle_momo"] = ((f["body"] > 0.7) & (c > o) & (f["rvol"] > 1.5), (f["body"] > 0.7) & (c < o) & (f["rvol"] > 1.5))
    # Baselines: "every bar" (no filter at all) and random entries (null control)
    ones = pd.Series(True, f.index)
    fam["BASE_every_bar"] = (ones, ones)
    rng = np.random.default_rng(seed)
    for s in range(null_seeds):
        p = 0.02
        fam[f"NULL_random{s:02d}"] = (rng.random(len(f)) < p, rng.random(len(f)) < p)
    return {k: (_b(a), _b(b)) for k, (a, b) in fam.items()}


def filters(f: pd.DataFrame) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    c = f["close"]
    hr = f["hour"]
    flt = {
        "htf1h": (f["htf1h"] > 0, f["htf1h"] < 0),
        "htf4h": (f["htf4h"] > 0, f["htf4h"] < 0),
        "ema200_side": (c > f["ema200"], c < f["ema200"]),
        "ema_stack": ((f["ema20"] > f["ema50"]) & (f["ema50"] > f["ema200"]), (f["ema20"] < f["ema50"]) & (f["ema50"] < f["ema200"])),
        "structure": (f["structure"] > 0, f["structure"] < 0),
        "adx_trend": (f["adx"] > 25,) * 2,
        "adx_range": (f["adx"] < 20,) * 2,
        "vol_high": (f["vol_regime"] > 1.2,) * 2,
        "vol_low": (f["vol_regime"] < 0.8,) * 2,
        "atr_expand": (f["atr_expand"] > 1.1,) * 2,
        "bb_squeeze": (f["bb_squeeze"],) * 2,
        "rvol_spike": (f["rvol"] > 1.5,) * 2,
        "rvol_quiet": (f["rvol"] < 0.8,) * 2,
        "rsi_room": (f["rsi"] < 60, f["rsi"] > 40),
        "rsi_momo": (f["rsi"] > 50, f["rsi"] < 50),
        "macd_side": (f["macd_h"] > 0, f["macd_h"] < 0),
        "stoch_room": (f["stoch"] < 80, f["stoch"] > 20),
        "roc_side": (f["roc"] > 0, f["roc"] < 0),
        "vwap_side": (c > f["vwap"], c < f["vwap"]),
        "body_strong": (f["body"] > 0.5,) * 2,
        "close_loc": (f["close_loc"] > 0.7, f["close_loc"] < 0.3),
        "asia_00_07": ((hr >= 0) & (hr < 7),) * 2,
        "europe_07_13": ((hr >= 7) & (hr < 13),) * 2,
        "us_13_21": ((hr >= 13) & (hr < 21),) * 2,
        "late_21_24": (hr >= 21,) * 2,
        "weekday": (f["dow"] < 5,) * 2,
        "weekend": (f["dow"] >= 5,) * 2,
    }
    return {k: (_b(a), _b(b)) for k, (a, b) in flt.items()}
