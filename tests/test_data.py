import requests

from app.data import DataError, MS_MIN, fetch_binance_1m, load_csv

NOW = 1_800_000_000_000 // MS_MIN * MS_MIN + 25_000  # 25s into a minute: forming candle must be excluded


class FakeResp:
    def __init__(self, status, payload=None):
        self.status, self.payload = status, payload

    def raise_for_status(self):
        if self.status >= 400:
            raise requests.HTTPError(f"{self.status}")

    def json(self):
        return self.payload


class FakeSession:
    """Serves 1m klines for [startTime, endTime]; hosts listed in `bad` answer 451."""

    def __init__(self, bad=()):
        self.bad, self.calls = set(bad), []

    def get(self, url, params=None, timeout=None):
        host = url.split("/api/")[0]
        self.calls.append((host, params["startTime"]))
        if host in self.bad:
            return FakeResp(451)
        rows, t = [], params["startTime"]
        while t <= params["endTime"] and len(rows) < params["limit"]:
            rows.append([t, "100", "101", "99", "100.5", "1", t + MS_MIN - 1, "0", 1, "0", "0", "0"])
            t += MS_MIN
        return FakeResp(200, rows)


def test_paginates_and_excludes_forming_candle():
    s = FakeSession()
    df = fetch_binance_1m("BTCUSDT", 1, session=s, now_ms=NOW, pause=0)
    assert len(df) == 1440 and len(s.calls) == 2          # 1000 + 440
    end_ms = NOW // MS_MIN * MS_MIN
    assert int(df.index[-1].timestamp() * 1000) == end_ms - MS_MIN   # last completed minute only
    assert df.index.is_monotonic_increasing and not df.index.duplicated().any()


def test_falls_back_to_next_host_on_451():
    s = FakeSession(bad={"https://data-api.binance.vision"})
    df = fetch_binance_1m("PAXGUSDT", 1, session=s, now_ms=NOW, pause=0)
    assert len(df) == 1440
    assert {h for h, _ in s.calls} == {"https://data-api.binance.vision", "https://api.binance.com"}


def test_all_hosts_failing_raises_data_error():
    s = FakeSession(bad={"https://data-api.binance.vision", "https://api.binance.com", "https://api.binance.us"})
    try:
        fetch_binance_1m("BTCUSDT", 1, session=s, now_ms=NOW, pause=0)
        raise AssertionError("expected DataError")
    except DataError:
        pass


def test_load_csv_ms_and_iso(tmp_path):
    a = tmp_path / "a.csv"
    a.write_text("timestamp,open,high,low,close,volume\n1800000000000,1,2,0.5,1.5,3\n1800000060000,1.5,2,1,1.2,4\n")
    b = tmp_path / "b.csv"
    b.write_text("Date,Open,High,Low,Close\n2026-01-01 00:00:00,1,2,0.5,1.5\n2026-01-01 00:01:00,1.5,2,1,1.2\n")
    da, db = load_csv(a), load_csv(b)
    assert len(da) == 2 and da.index.tz is not None and da["volume"].iloc[1] == 4
    assert len(db) == 2 and "volume" not in db.columns
