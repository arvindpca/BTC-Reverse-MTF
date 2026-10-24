"""1m candle loading: public Binance klines (BTCUSDT, PAXGUSDT) or any CSV (e.g. XAUUSD export).

Read-only public market data. Binance.com can refuse some regions, so several public hosts are tried
in order. XAU spot has no free long 1m API: pass a CSV (timestamp,open,high,low,close[,volume]).
"""
from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import requests

BINANCE_HOSTS = ("https://data-api.binance.vision", "https://api.binance.com", "https://api.binance.us")
MS_MIN = 60_000


class DataError(RuntimeError):
    pass


def fetch_binance_1m(symbol: str, days: int, *, session=None, hosts=BINANCE_HOSTS,
                     now_ms: int | None = None, pause: float = 0.08) -> pd.DataFrame:
    """Last `days` of COMPLETED 1m candles (the forming minute is excluded)."""
    session = session or requests.Session()
    now_ms = int(time.time() * 1000) if now_ms is None else now_ms
    end_ms = now_ms // MS_MIN * MS_MIN
    cursor = end_ms - days * 1440 * MS_MIN
    rows: list = []
    host_i, errors = 0, []
    while cursor < end_ms:
        while True:
            try:
                resp = session.get(
                    f"{hosts[host_i]}/api/v3/klines",
                    params=dict(symbol=symbol, interval="1m", startTime=cursor, endTime=end_ms - 1, limit=1000),
                    timeout=20,
                )
                resp.raise_for_status()
                chunk = resp.json()
                break
            except (requests.RequestException, ValueError) as exc:
                errors.append(f"{hosts[host_i]}: {exc}")
                host_i += 1
                if host_i >= len(hosts):
                    raise DataError(f"all hosts failed for {symbol}: {errors[-3:]}") from exc
        if not chunk:
            break
        rows.extend(chunk)
        last = int(chunk[-1][0])
        if last + MS_MIN <= cursor:
            break
        cursor = last + MS_MIN
        time.sleep(pause)
    if not rows:
        raise DataError(f"no candles returned for {symbol}")
    df = pd.DataFrame(rows).iloc[:, :6]
    df.columns = ["ts", "open", "high", "low", "close", "volume"]
    df.index = pd.to_datetime(df.pop("ts").astype("int64"), unit="ms", utc=True)
    return df.astype(float)


def load_csv(path: str | Path) -> pd.DataFrame:
    raw = pd.read_csv(path)
    raw.columns = [str(c).strip().lower() for c in raw.columns]
    tcol = next((c for c in ("timestamp", "time", "datetime", "date", "ts", "open_time") if c in raw.columns), None)
    if tcol is None:
        raise DataError("CSV needs a timestamp/time/datetime/date column")
    ts = raw.pop(tcol)
    if pd.api.types.is_numeric_dtype(ts):
        unit = "ms" if float(ts.iloc[0]) > 1e11 else "s"
        idx = pd.to_datetime(ts, unit=unit, utc=True)
    else:
        idx = pd.to_datetime(ts, utc=True)
    raw.index = idx
    for c in ("open", "high", "low", "close"):
        if c not in raw.columns:
            raise DataError(f"CSV missing column: {c}")
    return raw[[c for c in ("open", "high", "low", "close", "volume") if c in raw.columns]].astype(float)


def get_1m(symbol: str, days: int, *, cache_dir: str | Path = "data_cache",
           csv_map: dict[str, str] | None = None) -> pd.DataFrame:
    """CSV if one is mapped for this symbol, else cached Binance fetch."""
    if csv_map and symbol in csv_map:
        df = load_csv(csv_map[symbol])
        return df.loc[df.index.max() - pd.Timedelta(days=days):]
    cache = Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    f = cache / f"{symbol}_{days}d_1m.csv.gz"
    if f.exists() and time.time() - f.stat().st_mtime < 6 * 3600:
        return pd.read_csv(f, index_col=0, parse_dates=True)
    df = fetch_binance_1m(symbol, days)
    df.to_csv(f)
    return df
