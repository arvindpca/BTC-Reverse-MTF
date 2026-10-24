import numpy as np
import pandas as pd
import pytest

from app import events
from app.events import TFData, build_tf, label, replay
from app.mtf import normalize_1m
from app.synthetic import make_synthetic


def _tf(h, l, c, atr_val=1.0):
    n = len(c)
    return TFData("t", pd.date_range("2026-01-01", periods=n, freq="1h", tz="UTC"), np.array(c, float), np.array(h, float),
                  np.array(l, float), np.array(c, float), np.full(n, atr_val), {}, np.full(n, np.nan), np.full(n, np.nan))


def test_label_target_stop_and_costs():
    # entry 100, ATR 1 -> risk 1.5, tp 103 (2R), stop 98.5
    tf = _tf(h=[100, 101, 103.5, 100], l=[100, 99.5, 100.5, 100], c=[100, 100.5, 103, 100])
    R, ex, C = label(tf, +1, 3)
    cost = events.COST_PCT / (1.5 / 100 * 100)
    assert ex[0] == 2 and R[0] == pytest.approx(2.0 - cost) and C[0] == pytest.approx(cost)
    tf2 = _tf(h=[100, 100.5, 100.2, 100], l=[100, 98.0, 99.9, 100], c=[100, 99, 100, 100])
    R2, ex2, _ = label(tf2, +1, 3)
    assert ex2[0] == 1 and R2[0] < -1.0          # stop hit, loss = -1R minus costs
    R3, ex3, _ = label(tf2, -1, 3)               # short: price never reaches 101.5 stop; time exit at close
    assert ex3[0] == 3


def test_label_same_bar_stop_wins_and_tail_is_undefined():
    tf = _tf(h=[100, 104, 100, 100], l=[100, 98, 100, 100], c=[100, 100, 100, 100])
    R, ex, _ = label(tf, +1, 2)
    assert R[0] < -1.0 and ex[0] == 1            # both barriers in one bar -> stop first
    assert np.isnan(R[-1]) and np.isnan(R[-2])   # not enough future bars


def test_replay_is_one_trade_at_a_time():
    ex = np.array([3, 3, 3, 5, 6, 7, 8, 9])
    assert replay(np.array([0, 1, 2, 3, 4, 5]), ex) == [0, 4]
    assert replay(np.array([0, 1, 2]), ex) == [0]


def test_features_do_not_use_future_data():
    df = normalize_1m(make_synthetic(n=60 * 24 * 70, seed=4))
    n1 = 60 * 24 * 50 + 11
    a, b = build_tf(df.iloc[:n1], "1h", 60), build_tf(df, "1h", 60)
    m = len(a.c) - 1                              # last bar of the truncated frame is partial
    for name in a.feats:
        np.testing.assert_array_equal(a.feats[name][0][:m], b.feats[name][0][:m])
    np.testing.assert_array_equal(a.trend4[:m], b.trend4[:m])
    np.testing.assert_array_equal(a.trend30[:m], b.trend30[:m])


def test_directional_alignment_flips_with_direction():
    tf = build_tf(normalize_1m(make_synthetic(n=60 * 24 * 70, seed=4)), "1h", 60)
    long_codes, short_codes = tf.directional(1)["align4h"][0], tf.directional(-1)["align4h"][0]
    known = long_codes >= 0
    assert known.sum() > 100 and ((long_codes[known] + short_codes[known]) == 1).all()  # with<->against


def test_scan_smoke_and_pass_filter_on_synthetic():
    d = make_synthetic(n=60 * 24 * 40, seed=2)
    fr = [events.scan_asset("A", d, 10, tfs={"1h": 60}), events.scan_asset("B", make_synthetic(n=60 * 24 * 40, seed=3), 10, tfs={"1h": 60})]
    c = events.combine(fr)
    assert {"A:train_avg", "B:test_n"} <= set(c.columns) and (c.key == "ALL").sum() == 2
    assert events.passes(c, ["A", "B"]).dtype == bool
