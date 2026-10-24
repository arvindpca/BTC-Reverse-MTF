import pytest

from app.paper import PaperBook, PaperConfig, client_order_id, size_position

CFG = PaperConfig(margin=100.0, leverage=30)


def test_full_size_numbers_at_30x():
    s, why = size_position(CFG, 100000.0, 98400.0)           # 1.6% stop
    assert why == "OK" and s["notional"] == pytest.approx(3000.0) and s["margin_used"] == pytest.approx(100.0)
    assert s["loss_at_stop"] == pytest.approx(48.0) and s["fee_round_trip"] == pytest.approx(4.8)


def test_risk_sizing_and_liquidation_guard():
    r = PaperConfig(margin=100.0, sizing="risk", risk_pct=2.0)
    s, _ = size_position(r, 100000.0, 98400.0)
    assert s["notional"] == pytest.approx(125.0) and s["loss_at_stop"] == pytest.approx(2.0)
    assert size_position(CFG, 100000.0, 97000.0)[1] == "STOP_BEYOND_LIQUIDATION_GUARD"   # 3% > 0.9 x 2.83%
    assert size_position(CFG, 100000.0, 98000.0)[1] == "OK"                              # 2% fits


def test_config_validation():
    for bad in (dict(leverage=31), dict(leverage=0), dict(margin=0), dict(sizing="x")):
        try:
            PaperConfig(**bad)
        except ValueError:
            continue
        raise AssertionError(f"accepted bad config {bad}")


def test_default_is_margin_300_leverage_30():
    d = PaperConfig()
    assert d.margin == 300.0 and d.leverage == 30
    s, _ = size_position(d, 100000.0, 98400.0)
    assert s["notional"] == pytest.approx(9000.0) and s["margin_used"] == pytest.approx(300.0)
    assert s["loss_at_stop"] == pytest.approx(144.0) and s["fee_round_trip"] == pytest.approx(14.4)


def test_duplicate_signal_and_same_side_are_rejected():
    b = PaperBook(CFG)
    a = b.on_signal("s1", +1, 100.0, 98.4)
    assert a["action"] == "OPEN" and a["order"]["client_order_id"] == client_order_id("s1")
    assert b.on_signal("s1", +1, 100.0, 98.4)["reason"] == "DUPLICATE_SIGNAL"
    assert b.on_signal("s2", +1, 100.5, 98.9)["reason"] == "SAME_SIDE_POSITION_OPEN"
    assert b.position["signal_id"] == "s1" and b.closed == []                        # still exactly one position


def test_opposite_signal_reverses_and_books_pnl():
    b = PaperBook(CFG)
    b.on_signal("s1", +1, 100.0, 98.4)
    r = b.on_signal("s2", -1, 101.0, 102.6)
    assert r["action"] == "FLIP" and b.position["side"] == -1 and len(b.closed) == 1
    c = b.closed[0]                                          # +1% on 3000 = +30 gross, minus 4.8 fees
    assert c["reason"] == "REVERSE" and c["pnl"] == pytest.approx(30.0 - 4.8, abs=0.01)


def test_stop_and_liquidation_exits_and_loss_capped_at_margin():
    b = PaperBook(CFG)
    b.on_signal("s1", +1, 100.0, 98.4)
    assert b.on_candle(high=101, low=99.0) is None
    c = b.on_candle(high=100, low=98.0)
    assert c["reason"] == "STOP" and c["pnl"] == pytest.approx(-48.0 - 4.8, abs=0.01)
    b2 = PaperBook(CFG)
    b2.on_signal("g", +1, 100.0, 98.4)
    b2.position["stop"] = 90.0                               # simulate a stop that never triggers before liquidation
    c2 = b2.on_candle(high=100, low=90.0)
    assert c2["reason"] == "LIQUIDATED" and c2["pnl"] == pytest.approx(-100.0 - 4.8, abs=0.01)


def test_state_survives_restart(tmp_path):
    f = tmp_path / "state.json"
    b = PaperBook(CFG, f)
    b.on_signal("s1", +1, 100.0, 98.4)
    again = PaperBook(CFG, f)                                # new process
    assert again.on_signal("s1", +1, 100.0, 98.4)["reason"] == "DUPLICATE_SIGNAL"
    assert again.position["signal_id"] == "s1"


def test_too_wide_stop_while_flipping_only_closes():
    b = PaperBook(CFG)
    b.on_signal("s1", +1, 100.0, 98.4)
    r = b.on_signal("s2", -1, 100.0, 104.0)                  # 4% stop: beyond guard
    assert r["action"] == "CLOSED_ONLY" and b.position is None and len(b.closed) == 1
