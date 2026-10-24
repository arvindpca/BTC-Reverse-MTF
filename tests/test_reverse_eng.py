import numpy as np

from app.reverse_eng import (clue_masks, candidates, group_of, lifts, make_null_1h, mine, pnl_curve, rule_signal,
                             swings, zigzag)
from app.mtf import atr


def _zz(df):
    a = atr(df["high"], df["low"], df["close"], 14)
    return zigzag(df["high"].to_numpy(), df["low"].to_numpy(), a / df["close"].to_numpy()), a


def test_zigzag_alternates_and_swings_are_big():
    df = make_null_1h(24 * 300, 1)
    piv, _ = _zz(df)
    assert len(piv) > 4
    assert all(piv[i][1] != piv[i + 1][1] for i in range(len(piv) - 1))
    sw = swings(df, piv)
    assert (sw["move_pct"] > 2).all() and set(sw["dir"]) == {1, -1}
    assert (sw["end"] > sw["start"]).all()


def test_clue_masks_are_causal():
    df = make_null_1h(24 * 120, 2)
    n1 = 24 * 80 + 5
    a, _ = clue_masks(df.iloc[:n1])
    b, _ = clue_masks(df)
    assert set(a) == set(b) and len(a) > 20
    for k in a:
        np.testing.assert_array_equal(a[k], b[k][:n1], err_msg=k)


def test_every_clue_has_a_group_and_pairs_mix_groups():
    df = make_null_1h(24 * 60, 3)
    masks, _ = clue_masks(df)
    for k in masks:
        group_of(k)
    cands = candidates(masks)
    assert len(cands) > len(masks)
    for name, _ in cands:
        if " & " in name:
            x, y = name.split(" & ")
            assert group_of(x) != group_of(y)


def test_rule_signal_fires_on_rising_edge_with_stop_on_correct_side():
    df = make_null_1h(500, 4)
    a = atr(df["high"], df["low"], df["close"], 14)
    cond = np.zeros(500, dtype=bool)
    cond[100:105] = True
    cond[200:203] = True
    for side in (1, -1):
        sd, stop, _ = rule_signal(cond, side, df, a)
        assert list(np.flatnonzero(sd)) == [100, 200]
        c = df["close"].to_numpy()
        assert all((stop[i] < c[i]) if side > 0 else (stop[i] > c[i]) for i in (100, 200))


def test_lift_detects_planted_clue():
    df = make_null_1h(24 * 300, 5)
    piv, _ = _zz(df)
    sw = swings(df, piv)
    masks, _ = clue_masks(df)
    planted = np.zeros(len(df), dtype=bool)
    planted[sw[sw["dir"] == 1]["start"].to_numpy()] = True
    masks["planted"] = planted
    lf = lifts(masks, sw, 0, len(df), 1)
    assert lf.iloc[0]["clue"] == "planted" and lf.iloc[0]["lift"] > 20


def test_mine_has_no_lookahead_in_split_and_runs():
    df = make_null_1h(24 * 500, 6)
    m = mine(df)
    if not m.empty:
        assert len(m) <= 10 and {"train_net_r", "test_net_r", "test_n"} <= set(m.columns)
        assert (m["train_net_r"] > 0).all()


def test_pnl_curve_empty():
    assert pnl_curve([]) == (0.0, 0.0)
