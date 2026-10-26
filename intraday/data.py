"""CoinDCX futures market data (public, read-only, no keys).

* Instrument check: the pair must be in CoinDCX's active USDT futures list, otherwise we STOP (no silent substitute).
* Candles: public candlestick endpoint with pcode=f (futures). Pages are walked backwards; if the server returns
  fewer bars than asked, the cursor moves to the earliest bar it did return, so a per-call cap cannot create
  silent holes. Real holes are left as holes and reported by the quality check.
* Only COMPLETED candles are kept (the forming bar is excluded).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
import requests

CANDLES_URL = "https://public.coindcx.com/market_data/candlesticks"
ACTIVE_URL = "https://api.coindcx.com/exchange/v1/derivatives/futures/data/active_instruments"
DETAIL_URL = "https://api.coindcx.com/exchange/v1/derivatives/futures/data/instrument"
RESOLUTION = {"1m": "1", "5m": "5", "15m": "15", "1h": "60"}
TF_MIN = {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "4h": 240}


class DataError(RuntimeError):
    pass


def _get_json(session, url, params, *, tries=5, log=print):
    delay = 1.0
    for attempt in range(tries):
        try:
            r = session.get(url, params=params, timeout=25)
            if r.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"HTTP {r.status_code}")
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as exc:
            if attempt == tries - 1:
                raise DataError(f"{url} failed after {tries} tries: {exc}") from exc
            log(f"  retry {attempt + 1} for {url}: {exc}")
            time.sleep(delay)
            delay *= 2


def parse_candles(js) -> pd.DataFrame:
    """Accepts {'s':'ok','data':[{...}]} or a bare list of dicts / lists."""
    data = js.get("data", js) if isinstance(js, dict) else js
    if not data:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    if isinstance(data[0], dict):
        df = pd.DataFrame(data)
        tcol = next(c for c in ("time", "t", "timestamp", "open_time") if c in df.columns)
        ts = df[tcol].astype("int64")
    else:  # [time, open, high, low, close, volume]
        df = pd.DataFrame(data).iloc[:, :6]
        df.columns = ["time", "open", "high", "low", "close", "volume"]
        ts = df["time"].astype("int64")
    unit = "ms" if ts.iloc[0] > 1e11 else "s"
    out = df[["open", "high", "low", "close", "volume"]].astype(float)
    out.index = pd.to_datetime(ts.values, unit=unit, utc=True)
    out.index.name = "open_time"
    return out.sort_index()


def check_instrument(pair: str, *, session=None, out_dir: Path | None = None, log=print) -> dict:
    session = session or requests.Session()
    info: dict = {"pair": pair}
    active = _get_json(session, ACTIVE_URL, {"margin_currency_short_name[]": "USDT"}, log=log)
    pairs = active if isinstance(active, list) else active.get("data", active.get("instruments", []))
    pairs = [p if isinstance(p, str) else p.get("pair", "") for p in pairs]
    info["n_active_usdt_futures"] = len(pairs)
    info["listed"] = pair in pairs
    info["similar"] = [p for p in pairs if pair.split("-")[-1].split("_")[0] in p][:10]
    try:
        info["detail"] = _get_json(session, DETAIL_URL, {"pair": pair, "margin_currency_short_name": "USDT"}, log=log)
    except DataError as exc:
        info["detail_error"] = str(exc)
    if out_dir:
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        (Path(out_dir) / f"instrument_{pair}.json").write_text(json.dumps(info, indent=2, default=str))
    if not info["listed"]:
        raise DataError(f"{pair} is NOT in CoinDCX active USDT futures. Similar: {info['similar']}. Not substituting.")
    return info


def fetch_candles(pair: str, tf: str, days: int, *, session=None, now_s: int | None = None,
                  chunk_bars: int = 1000, pause: float = 0.3 if "PYTEST_FAST" not in __import__("os").environ else 0, log=print) -> tuple[pd.DataFrame, dict]:
    session = session or requests.Session()
    step = TF_MIN[tf] * 60
    now_s = int(time.time()) if now_s is None else now_s
    end = now_s // step * step            # open time of the FORMING bar -> excluded
    start = end - days * 86400
    frames, calls, empty, cur_end = [], 0, 0, end
    while cur_end > start:
        cur_start = max(start, cur_end - chunk_bars * step)
        js = _get_json(session, CANDLES_URL, {"pair": pair, "from": cur_start, "to": cur_end - 1,
                                              "resolution": RESOLUTION[tf], "pcode": "f"}, log=log)
        calls += 1
        df = parse_candles(js)
        df = df[(df.index >= pd.Timestamp(cur_start, unit="s", tz="UTC")) &
                (df.index < pd.Timestamp(cur_end, unit="s", tz="UTC"))]
        if len(df):
            frames.append(df)
            empty = 0
            earliest = int(df.index[0].timestamp())
            cur_end = earliest if earliest > cur_start else cur_start
        else:
            empty += 1
            cur_end = cur_start
            if empty >= 5:   # five empty pages in a row: history has ended
                log(f"  {pair} {tf}: history ends before {pd.Timestamp(cur_end, unit='s', tz='UTC')}")
                break
        time.sleep(pause)
    if not frames:
        raise DataError(f"no candles returned for {pair} {tf}")
    raw = pd.concat(frames).sort_index()
    meta = {"pair": pair, "tf": tf, "requested_days": days, "api_calls": calls, "source": CANDLES_URL,
            "pcode": "f", "fetched_at_utc": pd.Timestamp.now(tz="UTC").isoformat(),
            "rows_raw": int(len(raw)), "first": str(raw.index[0]), "last": str(raw.index[-1]),
            "forming_bar_excluded_from": str(pd.Timestamp(end, unit="s", tz="UTC"))}
    return raw, meta


def save_raw(raw: pd.DataFrame, meta: dict, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    f = out_dir / f"{meta['pair']}_{meta['tf']}_raw.csv.gz"
    raw.to_csv(f)
    (out_dir / f"{meta['pair']}_{meta['tf']}_raw_meta.json").write_text(json.dumps(meta, indent=2))
    return f


def load_csv(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path, index_col=0)
    df.index = pd.to_datetime(df.index, utc=True)
    df.index.name = "open_time"
    return df[["open", "high", "low", "close", "volume"]].astype(float)
