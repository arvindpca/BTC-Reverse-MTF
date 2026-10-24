import numpy as np
import pytest

from app.engine import EngineParams, run, summarize

COST = 2 * (0.06 + 0.02)  # round-trip % of notional


def mk(bars, signals):
    """bars: (open, high, low, close) per 1m bar. signals: {idx: (side, stop, setup_id)}."""
    a = np.array(bars, dtype=float)
    n = len(a)
    side = np.zeros(n, dtype=np.int8)
    stop = np.full(n, np.nan)
    sid = np.full(n, -1, dtype=np.int64)
    for k, (s, st, i) in signals.items():
        side[k], stop[k], sid[k] = s, st, i
    return a[:, 0], a[:, 1], a[:, 2], a[:, 3], side, stop, sid


def go(bars, signals, **kw):
    o, h, l, c, side, stop, sid = mk(bars, signals)
    return run(o, h, l, c, side, stop, sid, EngineParams(**kw))


def test_take_profit_net_of_costs():
    # long @100, stop 99 (1% risk) -> TP 102 = +2R gross, cost = 0.16%/1% = 0.16R
    t = go([(100, 100, 100, 100), (100, 101.5, 99.5, 101), (101, 102.5, 100.8, 102), (102, 102, 102, 102)],
           {0: (1, 99.0, 1)}, be_r=None)
    assert len(t) == 1 and t[0].reason == "TP"
    assert t[0].gross_r == pytest.approx(2.0) and t[0].net_r == pytest.approx(2.0 - COST / 1.0)


def test_stop_loss_and_stop_before_target_in_same_bar():
    t = go([(100, 100, 100, 100), (100, 102.5, 98.9, 100), (100, 100, 100, 100)], {0: (1, 99.0, 1)}, be_r=None)
    assert t[0].reason == "SL" and t[0].gross_r == pytest.approx(-1.0)  # both touched -> stop wins


def test_gap_through_stop_fills_at_open():
    t = go([(100, 100, 100, 100), (98, 98.5, 97.5, 98), (98, 98, 98, 98)], {0: (1, 99.0, 1)}, be_r=None)
    assert t[0].exit == 98 and t[0].gross_r == pytest.approx(-2.0)


def test_short_take_profit():
    t = go([(100, 100, 100, 100), (100, 100.5, 97.9, 98), (98, 98, 98, 98)], {0: (-1, 101.0, 1)}, be_r=None)
    assert t[0].reason == "TP" and t[0].gross_r == pytest.approx(2.0)


def test_break_even_moves_from_next_bar_only():
    # bar1 runs +1.2R (no exit) -> stop to entry for bar2; bar2 dips to 99.9 -> exit at entry (BE, 0R)
    t = go([(100, 100, 100, 100), (100, 101.2, 99.5, 101), (101, 101, 99.9, 100.5), (100, 100, 100, 100)],
           {0: (1, 99.0, 1)}, be_r=1.0)
    assert t[0].reason == "BE" and t[0].gross_r == pytest.approx(0.0)


def test_reverse_closes_at_signal_close_and_flips():
    bars = [(100, 100, 100, 100), (100, 100.4, 99.8, 100.2), (100.2, 100.6, 100.0, 100.5),
            (100.5, 100.5, 99.9, 100.0), (100, 100.1, 98.0, 98.5), (98.5, 98.5, 98.5, 98.5)]
    t = go(bars, {0: (1, 99.0, 1), 3: (-1, 101.0, 2)}, be_r=None, rr=2.0)
    assert [x.reason for x in t][0] == "REVERSE" and t[0].exit_idx == 3 and t[0].exit == 100.0
    assert t[1].side == -1 and t[1].entry_idx == 3
    assert t[1].reason == "TP"  # 100 -> 98 target (2R of 1R=1)


def test_reverse_disabled_ignores_opposite_signal():
    bars = [(100, 100, 100, 100)] + [(100, 100.3, 99.7, 100)] * 4 + [(100, 100, 98, 98.5)]
    t = go(bars, {0: (1, 99.0, 1), 3: (-1, 101.0, 2)}, be_r=None, reverse=False)
    assert len(t) == 1 and t[0].reason == "SL"


def test_one_entry_per_setup_and_no_overlap():
    bars = [(100, 100, 100, 100)] * 3 + [(100, 100.2, 99.8, 100)] * 5
    t = go(bars, {0: (1, 99.0, 7), 1: (1, 99.0, 7), 2: (1, 99.0, 8)}, be_r=None)
    assert len(t) == 1  # same-side signals while in a trade are ignored; setup 7 never re-enters


def test_tiny_and_huge_risk_are_skipped():
    bars = [(100, 100, 100, 100)] * 6
    assert go(bars, {0: (1, 99.9, 1)}) == []     # 0.1% < min_risk_pct
    assert go(bars, {0: (1, 90.0, 2)}) == []     # 10% > max_risk_pct


def test_time_stop():
    bars = [(100, 100, 100, 100)] + [(100, 100.1, 99.9, 100)] * 10
    t = go(bars, {0: (1, 99.0, 1)}, be_r=None, max_hold=4)
    assert t[0].reason == "TIME" and t[0].exit_idx == 4


def test_summarize_basics():
    bars = [(100, 100, 100, 100), (100, 102.5, 99.5, 102), (102, 102, 102, 102),
            (100, 100, 100, 100), (100, 100, 98.5, 98.8), (99, 99, 99, 99)]
    t = go(bars, {0: (1, 99.0, 1), 3: (1, 99.0, 2)}, be_r=None)
    s = summarize(t)
    assert s["n"] == 2 and s["win_rate"] == 0.5
    assert s["net_r"] == pytest.approx(s["gross_r"] - s["cost_r"])
    assert summarize([])["n"] == 0
