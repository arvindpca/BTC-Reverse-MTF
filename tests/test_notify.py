import os

from app.notify import build_events, send_telegram

OPEN = dict(signal_id="2026-10-25 03:00:00+00:00", entry=4000.0, initial_stop=3950.0, stop_pct=1.25, notional=1500.0,
            margin_at_30x=50.0, liquidation=3887.0)
CLOSED = dict(entry_time="2026-10-20 05:00:00+00:00", exit_time="2026-10-22 08:00:00+00:00", entry=3900.0, exit=3950.0,
              reason="TRAIL", net_r=1.2, pnl=7.0, equity=307.0)


def test_no_token_means_no_send_and_no_crash():
    os.environ.pop("TELEGRAM_BOT_TOKEN", None)
    assert send_telegram("x") is False


def test_first_run_does_not_flood_with_old_trades():
    st = {}
    assert build_events(dict(closed=[CLOSED], open=None), st, "PAXGUSDT") == []
    assert CLOSED["entry_time"] in st["notified_exits"]


def test_entry_and_exit_alerts_fire_once():
    st = {"notified_exits": [], "notified_entries": []}
    m1 = build_events(dict(closed=[], open=OPEN), st, "PAXGUSDT")
    assert len(m1) == 1 and "PAPER ENTRY" in m1[0] and "no real order" in m1[0]
    assert build_events(dict(closed=[], open=OPEN), st, "PAXGUSDT") == []          # same open position: silent
    closed = dict(CLOSED, entry_time=OPEN["signal_id"])
    m2 = build_events(dict(closed=[closed], open=None), st, "PAXGUSDT")
    assert len(m2) == 1 and "PAPER EXIT" in m2[0]
    assert build_events(dict(closed=[closed], open=None), st, "PAXGUSDT") == []
