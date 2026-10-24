# BTC-Reverse-MTF

Research harness for a **multi-timeframe stop-and-reverse** strategy on **BTC, PAXG and XAU**
(4h + 1h + 15m + 1m). Research only: it never places orders and holds no credentials.

## Status - read this first

| | |
|---|---|
| Engine, signals, data adapter | Built and unit-tested (no-lookahead, SL/TP/gap/reverse/fee maths, host fallback) |
| Controls | Random-walk data -> no edge found (gross ~0R/trade, costs ~-0.3R/trade). Data with built-in structure -> edge found. |
| **Real BTC / PAXG / XAU results** | **Not run yet.** The build sandbox had no market-data access. Run the `Research backtest` workflow. |
| Profitability | **Unproven.** Nothing here is a claim of profit. |

## The strategy (what is tested)

| TF | Role | Rule |
|---|---|---|
| 4h | regime / bias | EMA20 vs EMA50 trend; Kaufman efficiency ratio (<= 0.30 = range) |
| 1h | stretch | RSI(14) <= `rsi_lo` (long) or >= `100 - rsi_lo` (short), last *closed* 1h bar |
| 15m | setup | liquidity sweep: bar takes the prior K-bar extreme but closes back inside with a rejection body; valid for M bars |
| 1m | trigger | 1m close beyond the prior 5 one-minute extremes, candle in trade direction |

* **Reverse mechanism**: while in a trade, a valid opposite signal closes it at that bar's close and flips (same idea as the `REVERSAL_LIMIT_PAPER.md` spec in BTC-SMC-Live, but market-at-close here).
* `invert=True` mirrors every signal (same stop distance, opposite side) so the data decides whether *fading* or *following* the rejection pays.
* Stop beyond the sweep extreme (+0.1 ATR). Target `rr` x R. Optional break-even at 1R. 12h time stop. One entry per setup.
* Costs: 0.06% fee + 0.02% slippage **per side**. A trade with a 0.4% stop pays ~0.4R in costs, so stops under 0.25% are skipped.
* Every signal uses only candles closed by the signal bar (checked by truncating the data in tests).

## How the verdict works (anti self-deception)

432 configs are tried per asset. The best one *on the train part* will often look good by luck, so:

1. Data is split by time: first 60% = train, last 40% = test. Configs are ranked on **train only**.
2. The best train config must be **positive on the untouched test part**, with >= 30 trades, t-stat >= 2, and at least 60% of the top-10 train configs must also be positive on test.
3. Otherwise the report says `NO EDGE PROVEN`. Even `CANDIDATE` only means "worth forward/paper testing".

## Run it

GitHub Actions (recommended - the runner has internet): **Actions -> Research backtest -> Run workflow**.
Results appear in the job summary; per-config grids are in the `research-results` artifact.

Locally:

```bash
pip install -r requirements.txt
python -m pytest -q
python scripts/random_walk_check.py                       # null control, must show NO EDGE
python -m app.research --assets BTCUSDT PAXGUSDT --days 180
python -m app.research --assets XAUUSD --csv XAUUSD=xau_1m.csv --days 180
```

## Assets and data

* **BTCUSDT / PAXGUSDT**: public Binance 1m klines (hosts `data-api.binance.vision`, `api.binance.com`, `api.binance.us` tried in order). BTCUSDT is a proxy for CoinDCX `B-BTC_USDT`; check live spreads/fees before trusting costs.
* **PAXG** is a gold-backed token that trades 24/7; it tracks XAU but with its own spread and weekend behaviour.
* **XAU spot** has no free long 1m API: supply a CSV (`timestamp,open,high,low,close[,volume]`, UTC) via the `xau_csv_url` workflow input or `--csv`. Gold has weekend gaps; those are handled as missing bars.

## Next steps if a CANDIDATE appears

1. Re-run with a different, later window (fresh data the grid never saw).
2. Paper trade for weeks with real fills before any live money.
3. Only then think about order handling (exchange-side stops, restart recovery) - none of that exists here.
