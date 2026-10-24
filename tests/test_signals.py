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


def test_big_profile_timeframes_are_causal_and_wider():
    df = make_synthetic(n=60 * 24 * 40, seed=5)
    n1 = 60 * 24 * 28 + 17
    p = SignalParams(rsi_lo=48.0, sweep_lookback=12, setup_valid=4, htf="any", setup_tf=60, stretch_tf=240, trig_lookback=5)
    a, b = _signals(df.iloc[:n1], p), _signals(df, p)
    np.testing.assert_array_equal(a.side, b.side[:n1])
    np.testing.assert_array_equal(a.stop, b.stop[:n1])
    f = compute_features(df)
    small = build_signals(f, SignalParams(rsi_lo=48.0, sweep_lookback=12, setup_valid=4, htf="any"))
    act_b, act_s = b.side != 0, small.side != 0
    assert act_b.sum() > 0, "big profile must produce signals on this data"
    risk_b = np.abs(b.stop[act_b] - f.c[act_b]) / f.c[act_b]
    risk_s = np.abs(small.stop[act_s] - f.c[act_s]) / f.c[act_s]
    assert np.median(risk_b) > np.median(risk_s)  # 1h sweeps give wider stops than 15m sweeps


def test_research_window_trades_only_after_warmup():
    from app.research import run_asset
    df = make_synthetic(n=60 * 24 * 40, seed=5)
    grid, meta = run_asset("S", df, 0.6, quick=True, trade_days=20)
    assert meta["bars"] == 20 * 1440
    assert pd_ts(meta["start"]) >= pd_ts(str(df.index[0])) + __import__("pandas").Timedelta(days=19)


def pd_ts(x):
    import pandas as pd
    return pd.Timestamp(x)


def test_new_families_are_causal_and_produce_signals():
    from app.families import bollinger, donchian, ema_sar
    df = make_synthetic(n=60 * 24 * 60, seed=9)
    n1 = 60 * 24 * 40 + 29
    cases = [(donchian, dict(N=20, htf="with", confirm15=True)), (donchian, dict(N=20, invert=True)),
             (bollinger, dict(k=1.5, htf="range")), (bollinger, dict(k=1.5, invert=True)),
             (ema_sar, dict(fast=12, slow=48, htf="with")), (ema_sar, dict(fast=12, slow=48, invert=True))]
    fa, fb = compute_features(df.iloc[:n1]), compute_features(df)
    for fn, kw in cases:
        a, b = fn(fa, **kw), fn(fb, **kw)
        np.testing.assert_array_equal(a.side, b.side[:n1])
        np.testing.assert_array_equal(a.stop, b.stop[:n1])
        assert (b.side != 0).sum() > 0, (fn.__name__, kw)
        act = b.side != 0
        longs, shorts = b.side == 1, b.side == -1
        assert (b.stop[longs] < fb.c[longs]).all() and (b.stop[shorts] > fb.c[shorts]).all()
        assert (np.abs(b.stop[act] - fb.c[act]) / fb.c[act] > 0.001).all()


def test_signal_only_on_bar_that_closes_the_hour():
    from app.families import donchian
    df = make_synthetic(n=60 * 24 * 30, seed=9)
    f = compute_features(df)
    s = donchian(f, N=10)
    idx = np.flatnonzero(s.side != 0)
    assert len(idx) > 3
    assert all(f.index[k].minute == 59 for k in idx)  # last minute of an hour = the 1h bar just closed
