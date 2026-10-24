import numpy as np
import pandas as pd

from app.mtf import last_closed_pos, normalize_1m, resample, take
from app.synthetic import make_synthetic


def test_resample_15m_ohlc():
    idx = pd.date_range("2026-01-01", periods=45, freq="1min", tz="UTC")
    close = np.arange(100.0, 145.0)
    df = pd.DataFrame({"open": close - 0.5, "high": close + 1, "low": close - 1, "close": close, "volume": 1.0}, index=idx)
    r = resample(df, 15)  # first bucket dropped -> buckets starting 00:15 and 00:30
    assert list(r.index.minute) == [15, 30]
    first = r.iloc[0]
    assert first["open"] == 114.5 and first["close"] == 129.0
    assert first["high"] == 130.0 and first["low"] == 114.0 and first["volume"] == 15.0


def test_alignment_uses_only_closed_htf_bars():
    d = normalize_1m(make_synthetic(n=60 * 24 * 3))
    r = resample(d, 60)
    pos = last_closed_pos(d.index, r.index, 60)
    avail = (r.index + pd.Timedelta(minutes=60)).values
    close_t = (d.index + pd.Timedelta(minutes=1)).values
    for k in np.random.default_rng(1).integers(0, len(d), 500):
        p = pos[k]
        if p >= 0:
            assert avail[p] <= close_t[k]
        if p + 1 < len(avail):
            assert avail[p + 1] > close_t[k]


def test_take_nan_for_missing():
    out = take(np.array([1.0, 2.0]), np.array([-1, 0, 1]))
    assert np.isnan(out[0]) and out[1] == 1.0 and out[2] == 2.0


def test_normalize_drops_few_bad_rows_and_rejects_many():
    df = make_synthetic(n=2000)
    df.iloc[5, df.columns.get_loc("high")] = df.iloc[5]["low"] * 0.5  # invalid high
    assert len(normalize_1m(df, max_bad_frac=0.01)) == 1999
    try:
        normalize_1m(df, max_bad_frac=0.0)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
