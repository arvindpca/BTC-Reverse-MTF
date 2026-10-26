"""Causal feature library. Row t uses only bars whose CLOSE time is <= close time of bar t.

Index = bar OPEN time (UTC). A signal on row t is known at open_time[t] + tf, and is traded at the next bar's open.
Higher-timeframe values come from HTF bars that have fully closed by that moment (see `htf_onto`).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .clean import resample
from .data import TF_MIN


def ema(x, n):
    return x.ewm(span=n, adjust=False, min_periods=n).mean()


def rma(x, n):
    return x.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def rsi(c, n=14):
    d = c.diff()
    up, dn = rma(d.clip(lower=0), n), rma((-d).clip(lower=0), n)
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def atr(df, n=14):
    pc = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()], axis=1).max(axis=1)
    return rma(tr, n)


def adx(df, n=14):
    up, dn = df["high"].diff(), -df["low"].diff()
    pdm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), df.index)
    mdm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), df.index)
    a = atr(df, n)
    pdi, mdi = 100 * rma(pdm, n) / a, 100 * rma(mdm, n) / a
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return rma(dx, n)


def htf_onto(base: pd.DataFrame, tf: str, rule: str, minutes: int, fn) -> pd.DataFrame:
    """Resample base to `rule`, compute fn(htf_df) -> DataFrame, map to base rows by CLOSE time (no lookahead)."""
    h = resample(base, rule)
    vals = fn(h)
    vals.index = h.index + pd.Timedelta(minutes=minutes)            # HTF close time
    base_close = base.index + pd.Timedelta(minutes=TF_MIN[tf])
    out = vals.reindex(vals.index.union(base_close)).ffill().reindex(base_close)
    out.index = base.index
    return out


def _swings(h, l, k=2):
    """Fractal swing points confirmed k bars later. Returns last confirmed swing high/low levels (ffilled)."""
    n = len(h)
    sh = np.full(n, np.nan)
    sl = np.full(n, np.nan)
    for t in range(2 * k, n):
        c = t - k
        if h[c] == h[c - k:t + 1].max():
            sh[t] = h[c]
        if l[c] == l[c - k:t + 1].min():
            sl[t] = l[c]
    return pd.Series(sh).ffill().values, pd.Series(sl).ffill().values


def _order_blocks(o, c, h, l, bos_up, bos_dn, look=10, expiry=48):
    """Bullish OB: last down candle within `look` bars before a bullish BOS. Valid `expiry` bars. Mirror for bearish."""
    n = len(o)
    bhi = np.full(n, np.nan)
    blo = np.full(n, np.nan)
    shi = np.full(n, np.nan)
    slo = np.full(n, np.nan)
    cur_b = cur_s = None
    for t in range(n):
        if bos_up[t]:
            for j in range(t - 1, max(t - look, 0) - 1, -1):
                if c[j] < o[j]:
                    cur_b = (h[j], l[j], t)
                    break
        if bos_dn[t]:
            for j in range(t - 1, max(t - look, 0) - 1, -1):
                if c[j] > o[j]:
                    cur_s = (h[j], l[j], t)
                    break
        if cur_b and t - cur_b[2] <= expiry:
            bhi[t], blo[t] = cur_b[0], cur_b[1]
        if cur_s and t - cur_s[2] <= expiry:
            shi[t], slo[t] = cur_s[0], cur_s[1]
    return bhi, blo, shi, slo


def build(df: pd.DataFrame, tf: str) -> pd.DataFrame:
    f = df[["open", "high", "low", "close", "volume"]].copy()
    o, h, l, c, v = (f[k] for k in ("open", "high", "low", "close", "volume"))
    for n in (20, 50, 200):
        f[f"ema{n}"] = ema(c, n)
    f["atr"] = atr(f, 14)
    f["atrp"] = f["atr"] / c
    f["rsi"] = rsi(c, 14)
    m = ema(c, 12) - ema(c, 26)
    f["macd_h"] = m - ema(m, 9)
    f["roc"] = c.pct_change(12)
    ll, hh = l.rolling(14).min(), h.rolling(14).max()
    f["stoch"] = 100 * (c - ll) / (hh - ll).replace(0, np.nan)
    f["adx"] = adx(f, 14)
    f["vol_regime"] = f["atrp"] / f["atrp"].rolling(500, min_periods=100).median()
    f["atr_expand"] = f["atr"] / f["atr"].rolling(100, min_periods=50).mean()
    mid, sd = c.rolling(20).mean(), c.rolling(20).std()
    f["bb_up"], f["bb_lo"] = mid + 2 * sd, mid - 2 * sd
    f["bb_width"] = (4 * sd) / mid
    f["bb_squeeze"] = f["bb_width"] < f["bb_width"].rolling(200, min_periods=50).median()
    day = f.index.floor("D")
    tp = (h + l + c) / 3
    f["vwap"] = (tp * v).groupby(day).cumsum() / v.groupby(day).cumsum().replace(0, np.nan)
    f["vwap_dev"] = (c - f["vwap"]) / f["atr"]
    f["rvol"] = v / v.rolling(20).mean().shift(1).replace(0, np.nan)
    rng = (h - l).replace(0, np.nan)
    f["body"] = (c - o).abs() / rng
    f["close_loc"] = (c - l) / rng
    for n in (20, 48):
        f[f"don_hi{n}"] = h.rolling(n).max().shift(1)
        f[f"don_lo{n}"] = l.rolling(n).min().shift(1)
    sh, sl = _swings(h.values, l.values, 2)
    f["swing_hi"], f["swing_lo"] = sh, sl
    pc = c.shift(1)
    f["bos_up"] = (c > f["swing_hi"]) & (pc <= f["swing_hi"])
    f["bos_dn"] = (c < f["swing_lo"]) & (pc >= f["swing_lo"])
    last = pd.Series(np.where(f["bos_up"], 1, np.where(f["bos_dn"], -1, np.nan)), f.index).ffill()
    f["structure"] = last.fillna(0)
    f["fvg_up"] = l > h.shift(2)
    f["fvg_dn"] = h < l.shift(2)
    bhi, blo, shi, slo = _order_blocks(o.values, c.values, h.values, l.values,
                                       f["bos_up"].values, f["bos_dn"].values)
    f["ob_b_hi"], f["ob_b_lo"], f["ob_s_hi"], f["ob_s_lo"] = bhi, blo, shi, slo
    f["hour"] = f.index.hour
    f["dow"] = f.index.dayofweek

    def trend(x):
        return pd.DataFrame({"t": np.sign(ema(x["close"], 20) - ema(x["close"], 50))}, index=x.index)

    f["htf1h"] = htf_onto(df, tf, "1h", 60, trend)["t"]
    f["htf4h"] = htf_onto(df, tf, "4h", 240, trend)["t"]
    return f
