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
