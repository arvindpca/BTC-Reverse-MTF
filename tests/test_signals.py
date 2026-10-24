import numpy as np

from app.signals import SignalParams, build_signals, compute_features
from app.synthetic import make_synthetic

LOOSE = SignalParams(rsi_lo=48.0, sweep_lookback=8, setup_valid=4, htf="any")


def _signals(df, p=LOOSE):
    return build_signals(compute_features(df), p)


def test_signals_exist_and_are_well_formed():
    df = make_synthetic(n=60 * 24 * 20, seed=3)
    f = compute_features(df)
    s = build_signals(f, LOOSE)
    act = s.side != 0
    assert act.sum() > 5, "test data must produce signals or the invariance test is vacuous"
    longs, shorts = s.side == 1, s.side == -1
    assert (s.stop[longs] < f.c[longs]).all() and (s.stop[shorts] > f.c[shorts]).all()
    assert (s.setup_id[act] >= 0).all()


def test_future_data_never_changes_past_signals():
    df = make_synthetic(n=60 * 24 * 20, seed=3)
    n1 = 60 * 24 * 14 + 37
    short = _signals(df.iloc[:n1])
    full = _signals(df)
    np.testing.assert_array_equal(short.side, full.side[:n1])
    np.testing.assert_array_equal(short.stop, full.stop[:n1])
    np.testing.assert_array_equal(short.setup_id, full.setup_id[:n1])


def test_future_invariance_for_every_htf_mode_and_invert():
    df = make_synthetic(n=60 * 24 * 12, seed=11)
    n1 = 60 * 24 * 8 + 13
    for htf in ("any", "with", "range"):
        for inv in (False, True):
            p = SignalParams(rsi_lo=48.0, sweep_lookback=8, setup_valid=4, htf=htf, invert=inv)
            a, b = _signals(df.iloc[:n1], p), _signals(df, p)
            np.testing.assert_array_equal(a.side, b.side[:n1])
            np.testing.assert_array_equal(a.stop, b.stop[:n1])


def test_invert_mirrors_side_and_stop_distance():
    df = make_synthetic(n=60 * 24 * 20, seed=3)
    f = compute_features(df)
    a = build_signals(f, LOOSE)
    b = build_signals(f, SignalParams(**{**LOOSE.__dict__, "invert": True}))
    act = a.side != 0
    np.testing.assert_array_equal(b.side, -a.side)
    np.testing.assert_allclose(np.abs(b.stop[act] - f.c[act]), np.abs(a.stop[act] - f.c[act]))
    assert (b.stop[b.side == 1] < f.c[b.side == 1]).all()
    assert (b.stop[b.side == -1] > f.c[b.side == -1]).all()
