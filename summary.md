# Movement-first study: indicator status before profitable moves

Window 2026-04-27 17:20:00+00:00 -> 2026-10-24 17:19:00+00:00 (after 60d warm-up); train/test split 60/40. Trade = stop 1.5 ATR, target 2.0R, <= horizon bars, costs 0.16% round trip. One trade at a time per condition. R = initial risk.

## 1. Which timeframe can even pay for its costs?

Entering at EVERY bar (no indicator), average per trade after costs - this is the baseline any clue must beat.

| tf | dir | BTCUSDT cost/trade | BTCUSDT test net R/trade | PAXGUSDT cost/trade | PAXGUSDT test net R/trade |
|---|---|---|---|---|---|
| 15m | LONG | 0.58R | -0.56R | 2.43R | -2.53R |
| 15m | SHORT | 0.59R | -0.62R | 2.34R | -2.20R |
| 1h | LONG | 0.24R | -0.13R | 0.53R | -0.71R |
| 1h | SHORT | 0.24R | -0.32R | 0.54R | -0.33R |
| 4h | LONG | 0.10R | +0.15R | 0.17R | -0.29R |
| 4h | SHORT | 0.10R | -0.44R | 0.17R | +0.00R |
| 5m | LONG | 1.26R | -1.20R | 6.46R | -6.44R |
| 5m | SHORT | 1.28R | -1.26R | 6.29R | -6.19R |

## 2. Clues that were positive after costs on BOTH assets, in BOTH train and test

| tf | clues passed (1 indicator) | expected by luck | clues passed (2 indicators) | expected by luck |
|---|---|---|---|---|
| 5m | 0 | nan | 0 | nan |
| 15m | 0 | nan | 0 | 0.2 |
| 1h | 0 | nan | 0 | 5.1 |
| 4h | 1 | 0.9 | 5 | 5.2 |

A clue that passes is only interesting if the 'passed' count is clearly ABOVE the 'expected by luck' count.

### 4h - top passing clues (by the weaker asset's test result)

| dir | indicator status before entry | BTCUSDT train | BTCUSDT test | PAXGUSDT train | PAXGUSDT test |
|---|---|---|---|---|---|
| SHORT | dist_ema20=0.5..2 & er4h=range | 28t +0.09R | 16t +0.31R | 20t +0.11R | 13t +0.61R |
| SHORT | volatility=low & er4h=range | 35t +0.11R | 14t +0.16R | 30t +0.04R | 12t +0.54R |
| SHORT | break20=none & dist_ema20=0.5..2 | 29t +0.07R | 22t +0.06R | 26t +0.16R | 15t +0.37R |
| SHORT | dist_ema20=0.5..2 | 29t +0.07R | 22t +0.06R | 27t +0.11R | 15t +0.37R |
| SHORT | vol_spike=no & dist_ema20=0.5..2 | 28t +0.11R | 22t +0.06R | 26t +0.16R | 14t +0.27R |
| SHORT | dist_ema20=0.5..2 & day=weekday | 27t +0.37R | 20t +0.03R | 25t +0.22R | 14t +0.48R |

