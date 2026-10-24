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


def test_plan_book_rules_and_month_end_withdrawal():
    from app.paper_run import PLAN, plan_book
    start = pd.Timestamp("2026-01-10", tz="UTC")
    now = pd.Timestamp("2026-03-05", tz="UTC")
    res = dict(closed=[dict(entry_time="2026-01-12 00:00:00+00:00", exit_time="2026-01-15 00:00:00+00:00", stop_pct=1.0, net_r=2.0),
                       dict(entry_time="2026-02-02 00:00:00+00:00", exit_time="2026-02-04 00:00:00+00:00", stop_pct=1.0, net_r=-1.0)], open=None)
    b = plan_book(res, start, now)
    # trade 1: position = min(3000*30, 100000)=90000, pnl = 90000*1%*2 = 1800 -> 4800; Jan end: withdraw 10% = 480 -> 4320
    assert b["trades"][0]["position"] == 90000 and abs(b["trades"][0]["pnl"] - 1800) < 0.01
    assert [m["month"] for m in b["months"]] == ["2026-01", "2026-02"]
    assert abs(b["months"][0]["withdrawn"] - 480) < 0.01 and abs(b["months"][0]["account"] - 4320) < 0.01
    # trade 2: position = min(4320*30,100000)=100000 (cap), pnl = -1000 -> 3320; Feb end: 332 withdrawn
    assert b["trades"][1]["position"] == 100000 and abs(b["trades"][1]["pnl"] + 1000) < 0.01
    assert abs(b["months"][1]["withdrawn"] - 332) < 0.01 and abs(b["account"] - 2988) < 0.01
    assert abs(b["withdrawn_total"] - 812) < 0.01 and PLAN["max_position"] == 100000
