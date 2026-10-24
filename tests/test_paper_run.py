import numpy as np
import pandas as pd

from app.paper_run import evaluate, v2_condition
from app.reverse_eng import clue_masks, make_null_1h


def _df():
    return make_null_1h(24 * 400, 21)


def test_replay_is_deterministic_and_prefix_stable():
    df = _df()
    start = df.index[800]
    full = evaluate(df, start)
    again = evaluate(df, start)
    assert full["closed"] == again["closed"]
    cut = 24 * 300
    part = evaluate(df.iloc[:cut], start)
    # trades that were already closed before the cut must be identical in the longer replay (no hindsight, no duplicates)
    done = [r for r in part["closed"] if r["exit_time"] < str(df.index[cut - 2])]
    assert len(done) > 3
    assert full["closed"][:len(done)] == done


def test_no_duplicate_entries_and_one_position():
    df = _df()
    res = evaluate(df, df.index[800])
    ents = [r["entry_time"] for r in res["closed"]]
    assert len(ents) == len(set(ents))
    spans = [(r["entry_time"], r["exit_time"]) for r in res["closed"]]
    assert all(spans[i][1] <= spans[i + 1][0] for i in range(len(spans) - 1))


def test_open_position_is_reported_with_sane_numbers():
    df = _df()
    found = 0
    for cut in range(24 * 200, 24 * 400, 7):
        res = evaluate(df.iloc[:cut], df.index[800])
        o = res["open"]
        if o:
            found += 1
            assert o["current_stop"] >= o["initial_stop"] and o["initial_stop"] < o["entry"]
            assert 0.3 <= o["stop_pct"] <= 2.5 and o["guard"] == "OK" and o["notional"] > 0
            assert o["liquidation"] < o["initial_stop"]
    assert found > 3


def test_condition_skips_europe_hours():
    df = _df()
    masks, _ = clue_masks(df)
    c = v2_condition(df, masks)
    h = df.index.hour
    assert not c[(h >= 8) & (h < 14)].any()
