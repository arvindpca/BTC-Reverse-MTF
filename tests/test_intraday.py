"""QA for the intraday CoinDCX futures research package (intraday/). Runs with pytest or `python -m intraday.selftest`."""
from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from intraday import config as C
from intraday.clean import clean
from intraday.data import DataError, check_instrument, fetch_candles, parse_candles
from intraday.engine import Bars, candidates, net_returns, select
from intraday.features import build
from intraday.metrics import stats
from intraday.research import run_study
from intraday.synthetic import make


def _frame(rows, minutes=15, start="2026-01-01"):
    idx = pd.date_range(start, periods=len(rows), freq=f"{minutes}min", tz="UTC")
    df = pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx, dtype=float)
    df["volume"] = 1.0
    df["atr"] = 1.0
    return df


# ------------------------------------------------------------------ candles / data
def test_clean_dupes_invalid_gaps_utc():
    df = make(3, 15, seed=1)
    raw = pd.concat([df, df.iloc[[5, 6]]])                      # duplicates
    raw = raw.drop(raw.index[20:23])                            # 3 missing bars
    raw.iloc[30, raw.columns.get_loc("high")] = raw.iloc[30]["low"] - 1   # invalid OHLC
    out, rep = clean(raw, "15m")
    assert rep["duplicates"] == 2 and rep["invalid_ohlc_dropped"] == 1
    assert rep["missing_bars"] == 4
    assert out.index.is_monotonic_increasing and not out.index.duplicated().any()
    assert str(out.index.tz) == "UTC" and out["gap_before"].sum() == 2


def test_clean_rejects_naive_timestamps():
    df = make(1, 15).tz_localize(None)
    try:
        clean(df, "15m")
    except ValueError:
        return
    raise AssertionError("naive index accepted")


def test_parse_candles_formats():
    a = parse_candles({"s": "ok", "data": [{"open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 3, "time": 1760000400000}]})
    b = parse_candles([[1760000400, 1, 2, 0.5, 1.5, 3]])
    assert a.index[0] == b.index[0] == pd.Timestamp(1760000400, unit="s", tz="UTC")
    assert a.iloc[0].tolist() == b.iloc[0].tolist()


class FakeResp:
    def __init__(self, js):
        self.js, self.status_code = js, 200

    def raise_for_status(self):
        pass

    def json(self):
        return self.js


class FakeSession:
    """Serves 5m candles for every slot, but at most `cap` (newest first) per call: tests pagination."""
    def __init__(self, cap=300, listed=("B-PAXG_USDT",)):
        self.cap, self.listed, self.calls = cap, listed, 0

    def get(self, url, params=None, timeout=None):
        self.calls += 1
        if "active_instruments" in url:
            return FakeResp(list(self.listed))
        if "instrument" in url:
            return FakeResp({"instrument": {"pair": params["pair"]}})
        step = 300
        t0 = -(-params["from"] // step) * step
        ts = list(range(t0, params["to"] + 1, step))[-self.cap:]
        return FakeResp({"s": "ok", "data": [{"open": 1, "high": 1, "low": 1, "close": 1, "volume": 1, "time": t * 1000} for t in ts]})


def test_fetch_pagination_full_coverage_and_forming_bar_excluded():
    now = 1_760_000_000 + 123
    raw, meta = fetch_candles("B-PAXG_USDT", "5m", 2, session=FakeSession(cap=300), now_s=now, pause=0)
    out, rep = clean(raw, "5m")
    assert rep["missing_bars"] == 0 and len(out) == 2 * 288
    assert out.index[-1] < pd.Timestamp(now // 300 * 300, unit="s", tz="UTC")


def test_instrument_not_listed_is_a_blocker():
    try:
        check_instrument("B-XYZ_USDT", session=FakeSession(listed=("B-BTC_USDT",)))
    except DataError:
        return
    raise AssertionError("unlisted pair was accepted")


# ------------------------------------------------------------------ features / lookahead
def test_features_have_no_lookahead():
    df = make(20, 15, seed=3)
    full = build(df, "15m")
    for cut in (900, 1500, 1919):
        part = build(df.iloc[:cut], "15m")
        a = part.iloc[-1].astype(float)
        b = full.iloc[cut - 1].astype(float)
        assert np.allclose(a.values, b.values, equal_nan=True, rtol=1e-9), (a - b)[~np.isclose(a, b, equal_nan=True)]


def test_htf_value_uses_only_closed_bars():
    df = make(10, 15, seed=4)
    full = build(df, "15m")
    # 15m bar opening 10:30 closes 10:45 -> the 10:00 1h bar is NOT closed yet; 10:45 bar closes 11:00 -> it is.
    day = full.index[500].floor("D")
    t1030, t1045 = day + pd.Timedelta("10h30min"), day + pd.Timedelta("10h45min")
    trunc_1100 = build(df.loc[: day + pd.Timedelta("10h45min")], "15m")
    trunc_1045 = build(df.loc[: day + pd.Timedelta("10h30min")], "15m")
    assert full.loc[t1045, "htf1h"] == trunc_1100.loc[t1045, "htf1h"]
    assert full.loc[t1030, "htf1h"] == trunc_1045.loc[t1030, "htf1h"]


# ------------------------------------------------------------------ engine
def test_entry_is_next_bar_open_and_tp():
    f = _frame([[10, 10, 10, 10], [11, 11.5, 10.8, 11], [11, 13.5, 10.9, 13], [13, 13, 13, 13]])
    m = np.array([True, False, False, False])
    c = candidates(Bars.from_frame(f, 15), m, 1, 1.0, 2.0, 3)
    assert c.entry[0] == 11 and c.reason[0] == 1 and c.exit[0] == 13 and c.exit_bar[0] == 2


def test_same_candle_stop_and_target_means_stop():
    f = _frame([[10, 10, 10, 10], [10, 10.2, 9.9, 10], [10, 13, 8, 10], [10, 10, 10, 10]])
    c = candidates(Bars.from_frame(f, 15), np.array([1, 0, 0, 0], bool), 1, 1.0, 2.0, 3)
    assert c.reason[0] == 0 and c.exit[0] == 9


def test_gap_through_stop_fills_at_open():
    f = _frame([[10, 10, 10, 10], [10, 10.1, 9.95, 10], [8, 8.2, 7.9, 8], [8, 8, 8, 8]])
    c = candidates(Bars.from_frame(f, 15), np.array([1, 0, 0, 0], bool), 1, 1.0, 2.0, 3)
    assert c.reason[0] == 0 and c.exit[0] == 8


def test_short_side_and_time_exit():
    f = _frame([[10, 10, 10, 10], [10, 10.5, 9.6, 9.8], [9.8, 10.2, 9.5, 9.7], [9.7, 9.7, 9.7, 9.7]])
    c = candidates(Bars.from_frame(f, 15), np.array([1, 0, 0, 0], bool), -1, 1.0, 2.0, 2)
    assert c.reason[0] == 2 and c.exit[0] == 9.7 and c.exit_bar[0] == 2
    assert np.isclose(c.gross_ret[0], (10 - 9.7) / 10)


def test_incomplete_trade_at_end_is_dropped():
    f = _frame([[10, 10, 10, 10], [10, 10.1, 9.9, 10], [10, 10.1, 9.9, 10]])
    c = candidates(Bars.from_frame(f, 15), np.array([0, 1, 0], bool), 1, 1.0, 2.0, 5)
    assert len(c.sig) == 0


def test_costs_and_funding():
    rows = [[100, 100, 100, 100]] * 40
    f = _frame(rows, minutes=15, start="2026-01-01 07:00")
    f.iloc[1:, :4] = [[100, 100.2, 99.9, 100]] * 39
    c = candidates(Bars.from_frame(f, 15), np.eye(40, dtype=bool)[0], 1, 1.0, 50.0, 8)  # 2h hold crosses 08:00
    taken = select(c)
    net, R, gR = net_returns(c, taken, 0.079, 0.01)
    assert c.funding_n[0] == 1
    assert np.isclose(net[0], c.gross_ret[0] - 2 * 0.00079 - 0.0001)
    assert np.isclose(R[0], net[0] / 0.01)


def test_no_overlapping_positions():
    f = _frame([[10, 10.1, 9.95, 10]] * 30)
    m = np.zeros(30, bool)
    m[[2, 3, 4, 9, 10]] = True
    c = candidates(Bars.from_frame(f, 15), m, 1, 1.0, 2.0, 5)
    taken = select(c)
    sig, xb = c.sig[taken], c.exit_bar[taken]
    assert list(sig) == [2, 9]
    assert all(sig[i + 1] >= xb[i] for i in range(len(sig) - 1))


def test_cost_per_side_formula():
    cfg = C.load()
    assert np.isclose(C.cost_per_side_pct(cfg), 0.05 * 1.18 + 0.02)


# ------------------------------------------------------------------ metrics / reproducibility
def test_metrics():
    s = stats(np.array([1, -1, -1, 2, -1]), risk=0.1, start=100)
    assert s["n"] == 5 and s["win_rate"] == 0.4 and s["sum_R"] == 0 and s["pf"] == 1.0
    assert s["max_loss_streak"] == 2
    eq = 100 * np.cumprod([1.1, 0.9, 0.9, 1.2, 0.9])
    assert np.isclose(s["max_dd_pct"], round(100 * (1 - eq[2] / eq[0]), 2))


def test_reproducible_study():
    cfg = C.load(null_seeds=1, top_base_per_dir=2, pair_filters_per_base=2, finalists_per_dir=1)
    feats = build(make(40, 15, seed=9), "15m")
    hashes = []
    for _ in range(2):
        with tempfile.TemporaryDirectory() as d:
            run_study(feats, "15m", cfg, Path(d), lambda *a: None, "t")
            hashes.append(hashlib.md5((Path(d) / "experiments.csv").read_bytes()).hexdigest())
    assert hashes[0] == hashes[1]


def test_end_to_end_coindcx_path_with_fake_exchange():
    """Exchange path offline: instrument check, paging, 15m fallback to CoinDCX 5m, outputs written."""
    import json
    import intraday.data as D
    from intraday.research import main
    real = D.requests.Session
    D.requests.Session = lambda: FakeSession(cap=500, listed=("B-PAXG_USDT", "B-BTC_USDT"))
    try:
        with tempfile.TemporaryDirectory() as d:
            main(["--out", d, "--assets", "PAXG", "--days", "12", "--null-seeds", "1"])
            q = json.loads((Path(d) / "data_quality.json").read_text())
            assert [x["tf"] for x in q] == ["5m", "15m"] and q[1]["derived_from"] == "5m"
            assert (Path(d) / "data" / "raw" / "B-PAXG_USDT_5m_raw.csv.gz").exists()
            assert (Path(d) / "summary.md").exists() and (Path(d) / "config.json").exists()
    finally:
        D.requests.Session = real


def test_min_stop_filter_uses_signal_close():
    f = _frame([[100, 100, 100, 100]] * 10)          # atr 1 -> stop 1% at sl_atr 1
    m = np.zeros(10, bool)
    m[2] = True
    b = Bars.from_frame(f, 15)
    assert len(candidates(b, m, 1, 1.0, 2.0, 3, min_stop_pct=0.5).sig) == 1
    assert len(candidates(b, m, 1, 1.0, 2.0, 3, min_stop_pct=1.5).sig) == 0


def test_4h_built_from_smaller_candles_and_tf_overrides():
    import json
    import intraday.data as D
    from intraday.research import main
    cfg = C.for_tf(C.load(), "4h")
    assert cfg["max_hold_hours"] == [24, 96] and C.load()["max_hold_hours"] == [4, 12]
    real = D.requests.Session
    D.requests.Session = lambda: FakeSession(cap=500, listed=("B-PAXG_USDT", "B-BTC_USDT"))
    try:
        with tempfile.TemporaryDirectory() as d:
            main(["--out", d, "--assets", "BTC", "--days", "12", "--null-seeds", "1", "--timeframes", "5m", "4h"])
            q = json.loads((Path(d) / "data_quality.json").read_text())
            assert q[1]["tf"] == "4h" and q[1]["derived_from"] == "5m" and q[1]["missing_bars"] == 0
    finally:
        D.requests.Session = real


def test_parse_candles_rejects_or_empties_odd_responses():
    assert len(parse_candles({"s": "ok", "data": []})) == 0
    assert len(parse_candles({})) == 0
    for bad in ({"status": "error", "message": "invalid range"}, {"data": "oops"}, [{"open": 1}]):
        try:
            parse_candles(bad)
        except DataError:
            continue
        raise AssertionError(f"accepted {bad}")


class ErrorAfterSession(FakeSession):
    """Serves recent pages, then an error dict for older history (like a pair listed recently)."""
    def __init__(self, cutoff_s, **kw):
        super().__init__(**kw)
        self.cutoff = cutoff_s

    def get(self, url, params=None, timeout=None):
        if "candlesticks" in url and params["to"] < self.cutoff:
            return FakeResp({"status": "error", "message": "no data before listing"})
        return super().get(url, params, timeout)


def test_fetch_stops_cleanly_at_listing_date():
    now = 1_760_000_000
    raw, meta = fetch_candles("B-PAXG_USDT", "5m", 5, session=ErrorAfterSession(now - 2 * 86400, cap=300),
                              now_s=now, pause=0)
    assert len(raw) >= 2 * 288 - 300 and raw.index[0] > pd.Timestamp(now - 3 * 86400, unit="s", tz="UTC")


# ------------------------------------------------------------------ BTC 1h paper trader
def _paper_frame(rows, start="2026-01-31 20:00"):
    f = _frame(rows, minutes=60, start=start)
    f["atr"] = 1.0
    return f


def test_paper_entry_sl_tp_and_month_deposit():
    from intraday.paper_btc1h import new_state, step
    rows = [[100, 100.2, 99.9, 100]] * 3 + [[100, 101, 99.9, 100.5], [100.5, 105.5, 100.4, 105]] + [[105, 105, 105, 105]] * 3
    f = _paper_frame(rows)
    mask = np.zeros(len(f), bool)
    mask[2] = True                                  # signal on candle 2 -> entry at open of candle 3 = 100
    st = new_state(f.index[0], f.index[0].strftime("%Y-%m"))
    st, msgs = step(st, f, mask)
    assert len(st["trades"]) == 1
    t = st["trades"][0]
    assert t["entry"] == 100 and t["reason"] == "TP" and t["exit"] == 104.5      # 1.5 ATR stop, 3R target
    assert st["deposited"] == 4000 and st["month"] == "2026-02"                    # +1000 at the new month
    assert any("SIGNAL" in m for m in msgs) and any("EXIT" in m for m in msgs) and all("BTC 1H STRATEGY" in m for m in msgs)
    st2, msgs2 = step(st, f, mask)                                                  # idempotent
    assert msgs2 == [] and len(st2["trades"]) == 1


def test_paper_stop_first_and_sizing():
    from intraday.paper_btc1h import new_state, step
    rows = [[100, 100.1, 99.9, 100]] * 3 + [[100, 106, 97, 100]] + [[100, 100, 100, 100]] * 2
    f = _paper_frame(rows, start="2026-03-01 00:00")
    mask = np.zeros(len(f), bool)
    mask[2] = True
    st = new_state(f.index[0], "2026-03")
    st, _ = step(st, f, mask)
    t = st["trades"][0]
    assert t["reason"] == "SL" and t["exit"] == 98.5
    assert np.isclose(t["position"], 3000 * 0.02 / 0.015)                         # 2% risk / 1.5% stop
    assert t["pnl"] < -60 and st["equity"] < 3000


def test_paper_time_exit_after_48_candles():
    from intraday.paper_btc1h import new_state, step
    rows = [[100, 100.1, 99.9, 100]] * 3 + [[100, 100.5, 99.5, 100.2]] * 60
    f = _paper_frame(rows, start="2026-03-01 00:00")
    mask = np.zeros(len(f), bool)
    mask[2] = True
    st = new_state(f.index[0], "2026-03")
    st, _ = step(st, f, mask)
    t = st["trades"][0]
    assert t["reason"].startswith("TIME") and pd.Timestamp(t["exit_time"]) == f.index[3 + 47] + pd.Timedelta(hours=1)


# ------------------------------------------------------------------ BTC 1h LIVE-method paper trader
class FakeFeed:
    def __init__(self, hourly, minutes):
        self.h, self.m = hourly, minutes

    def hourly(self):
        return self.h

    def minutes(self, start, end):
        m = self.m
        return m[(m.index >= start.floor("min")) & (m.index <= end)]


def _live_setup(min_rows, sig=True, now_month="2026-03"):
    from intraday.live_btc1h import LiveTrader
    from intraday.paper_btc1h import new_state
    hourly = _paper_frame([[100, 100.1, 99.9, 100]] * 5, start="2026-03-01 00:00")
    hourly["atr"] = 1.0
    st = new_state(hourly.index[3], now_month)
    mi = pd.date_range("2026-03-01 05:00", periods=len(min_rows), freq="1min", tz="UTC")
    m = pd.DataFrame(min_rows, columns=["open", "high", "low", "close"], index=mi, dtype=float)
    sent = []
    tr = LiveTrader(st, FakeFeed(hourly, m), sent.append, None, lambda *a: None)
    import intraday.live_btc1h as L
    mask = np.zeros(len(hourly), bool)
    mask[4] = sig
    L.signal_mask = lambda f: mask
    return tr, st, sent, hourly, m


def test_live_entry_at_live_price_then_stop():
    rows = [[100, 100.2, 99.9, 100.1], [100.1, 100.3, 99.0, 99.2], [99.2, 99.5, 98.0, 98.2]]
    tr, st, sent, hourly, m = _live_setup(rows)
    now = pd.Timestamp("2026-03-01 05:00:20", tz="UTC")
    tr.on_hour(now)
    assert st["open"] and st["open"]["entry"] == 100.1 and np.isclose(st["open"]["stop"], 98.6)
    assert "BUY HO GAYA" in sent[-1]
    tr.monitor(pd.Timestamp("2026-03-01 05:02:30", tz="UTC"))
    t = st["trades"][-1]
    assert t["reason"] == "SL" and np.isclose(t["exit"], 98.6) and st["open"] is None and "STOP LOSS" in sent[-1]


def test_live_gap_through_stop_fills_at_open_and_target():
    rows = [[100, 100, 100, 100], [97, 97.5, 96.5, 97]]
    tr, st, sent, *_ = _live_setup(rows)
    tr.on_hour(pd.Timestamp("2026-03-01 05:00:10", tz="UTC"))
    tr.monitor(pd.Timestamp("2026-03-01 05:01:50", tz="UTC"))
    assert st["trades"][-1]["exit"] == 97
    rows = [[100, 100, 100, 100], [100, 103, 99.9, 102], [102, 106, 101, 105]]
    tr, st, sent, *_ = _live_setup(rows)
    tr.on_hour(pd.Timestamp("2026-03-01 05:00:10", tz="UTC"))
    tr.monitor(pd.Timestamp("2026-03-01 05:01:30", tz="UTC"))     # minute 05:01 still forming: high 103 < 104.5
    assert st["open"]
    tr.monitor(pd.Timestamp("2026-03-01 05:03:00", tz="UTC"))
    assert st["trades"][-1]["reason"] == "TP" and np.isclose(st["trades"][-1]["exit"], 104.5)


def test_live_stale_signal_is_skipped_and_restart_replays_gap():
    tr, st, sent, *_ = _live_setup([[100, 100, 100, 100]] * 3)
    tr.on_hour(pd.Timestamp("2026-03-01 05:40:00", tz="UTC"))         # 40 min late
    assert st["open"] is None and "CHHOOT" in sent[-1]
    rows = [[100, 100, 100, 100]] + [[100, 100.5, 99.5, 100]] * 30 + [[100, 100, 98.0, 98.5]] + [[98.5] * 4] * 5
    tr, st, sent, *_ = _live_setup(rows)
    tr.on_hour(pd.Timestamp("2026-03-01 05:00:05", tz="UTC"))
    tr.monitor(pd.Timestamp("2026-03-01 05:36:00", tz="UTC"))         # 'restart' after a 36 min gap
    t = st["trades"][-1]
    assert t["reason"] == "SL" and t["exit_time"].startswith("2026-03-01 05:32")


def test_live_time_exit_and_new_month_deposit():
    rows = [[100, 100, 100, 100]] + [[100, 100.5, 99.5, 100.2]] * (48 * 60 + 5)
    tr, st, sent, *_ = _live_setup(rows)
    tr.on_hour(pd.Timestamp("2026-03-01 05:00:05", tz="UTC"))
    tr.monitor(pd.Timestamp("2026-03-03 05:03:00", tz="UTC"))
    t = st["trades"][-1]
    assert t["reason"].startswith("TIME") and t["exit_time"].startswith("2026-03-03 05:01")
    tr.housekeeping(pd.Timestamp("2026-04-01 00:05", tz="UTC"))
    assert st["deposited"] == 4000 and st["month"] == "2026-04" and any("NAYA MAHINA" in x for x in sent)
