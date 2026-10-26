# Intraday futures research: CoinDCX BTC + PAXG (5m / 15m)

Separate from everything else in this repo. It does **not** change the PAXG paper-trading job (`paper.yml`, `app/`).
Research only: public market data, no orders, no API keys.

## What it does

| Step | File | What |
|---|---|---|
| Data | `data.py` | Checks the pair is in CoinDCX's active USDT futures list (`B-BTC_USDT`, `B-PAXG_USDT`), pages the futures candle API (`pcode=f`), drops the still-forming bar, saves raw CSV + metadata. Never swaps in another pair. If direct 15m candles are unusable, 15m is built from the same pair's CoinDCX 5m candles (logged). |
| Quality | `clean.py` | Duplicates, off-grid timestamps, invalid OHLC, missing bars, gaps, extreme returns, zero volume -> `data_quality.json`. Missing bars are not filled. |
| Features | `features.py` | EMA 20/50/200, RSI, MACD, ROC, stochastic, ADX, ATR + volatility regime, Bollinger, daily VWAP, relative volume, candle body / close location, Donchian levels, swing highs/lows, BOS, structure, FVG, order blocks, hour/day, 1h + 4h trend from **closed** higher-timeframe bars only. |
| Setups + filters | `signals.py` | 15 entry families (breakout, sweep reversal, EMA pullback, RSI / Bollinger / VWAP reversion, BOS, MACD, FVG, OB retest, momentum candle) + 27 filters (trend, regime, volume, momentum, session, weekday). Baseline: enter every bar. Null: random entries. |
| Backtest | `engine.py` | Signal on closed bar, entry next bar open, ATR stop, R-multiple target, time stop, stop-first when both hit in one candle, gap fills at open, one position at a time, fee + 18% GST + slippage both sides, funding charged every 8h crossed. |
| Research | `research.py` | Per asset x timeframe x side: (A) every family x exit grid, (B) single filters on the 10 best, (C) filter pairs. Ranked on DEV + VAL only. TEST (last 25%) evaluated once for finalists. Plus walk-forward, cost stress, neighbour stability, monthly + regime splits, null-search comparison. |

## Verdict rules

A config is a **CANDIDATE (paper trade only)** only if all hold: >= 30 test trades, test and val net positive, test PF >= 1.15, still positive at 1.5x costs, walk-forward OOS positive with >= 50% positive folds, at least half of the neighbouring exit settings positive on dev and val, and the real search beats >= 95% of equally-sized random-entry searches. Otherwise `NO EDGE PROVEN` or `INCONCLUSIVE`.

## Run

GitHub: push to `research/coindcx-intraday-futures` or **Actions -> Intraday futures research -> Run workflow**. Results land on the `intraday-results` branch (`summary.md` first).

Locally:

```bash
pip install -r requirements.txt
python -m pytest -q tests/test_intraday.py        # or: python -m intraday.selftest
python -m intraday.research --out intraday_out                      # CoinDCX data, 180 days, BTC + PAXG, 5m + 15m
python -m intraday.research --out smoke --source synthetic          # offline pipeline check (random walk: must show no edge)
python -m intraday.research --out x --source csv --csv-dir intraday_out/data/raw   # re-run on saved raw data
```

Settings (costs, split, exit grid, thresholds) are in `config.py`; every run writes the exact settings to `config.json`.

## Output files (per `<ASSET>/<tf>/`)

`experiments.csv` (every config, dev/val metrics, stage), `ranked_top50.csv`, `result.json` (finalists with dev/val/test, cost stress, walk-forward folds, stability, regime, checks, verdict), `trades_<k>_<side>.csv` (trade log with equity + drawdown), `monthly_<k>_<side>.csv`, `baseline_every_bar.csv`. Top level: `summary.md`, `summary.json`, `data_quality.json`, `config.json`, `run_log.txt`, `data/raw`, `data/clean`.

## Known limits

* Funding history is not in the public API used here: a flat 0.01% per 8h is charged on every crossing (never credited).
* No gold (XAU) or basis features: no reliable free intraday XAU feed synchronized with CoinDCX.
* Fees default to 0.05% taker + 18% GST; check your CoinDCX fee tier and edit `config.py`.
* Trades are sized in R (risk units). Leverage does not change R; it only changes how big a loss can be.
