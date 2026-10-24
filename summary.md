# Reverse engineering study (1h bars)

READ THIS FIRST: clues measured at a swing start look strong even on pure random data (a swing low is by definition after a drop, so 'oversold' always shows a big lift). Only the test table (rules chosen on train, run once on unseen data) and the luck baseline say anything about real edge.

Costs 0.16% round trip. ATR stop 3x, trailing exit, one trade at a time. Research only, no orders.

## BTCUSDT

26280 1h bars (~3.0 years) 2023-10-25 to 2026-10-24. Train = first 60% (until 2025-08-12), test = the rest.

### 1. Movement available in hindsight (swings >= 8 ATR)

- swings: 223 (74.3 per year), median move 8.1%, median length 93 hours
- hindsight profit if every swing were caught perfectly: 742% of price per year (an upper bound nobody can reach)

### 2. Clues at the start of UP swings (what looked like this before a rally) - train period

| clue | at swing start | on all bars | lift |
|---|---|---|---|
| range low<.1 | 58% | 6% | 9.68x |
| dist<-3 | 40% | 5% | 7.58x |
| breakout dn48 | 17% | 2% | 7.57x |
| rsi<30 | 28% | 4% | 7.20x |
| rsi30-45 | 65% | 25% | 2.65x |
| breakout up48 | 0% | 3% | 0.00x |
| range high>.9 | 0% | 10% | 0.00x |
| 3 up bars | 0% | 11% | 0.00x |

### 2. Clues at the start of DOWN swings - train period

| clue | at swing start | on all bars | lift |
|---|---|---|---|
| breakout up48 | 34% | 3% | 10.96x |
| range high>.9 | 59% | 10% | 5.65x |
| rsi>70 | 32% | 6% | 5.40x |
| dist>3 | 46% | 11% | 4.34x |
| er>.4 | 31% | 16% | 1.92x |
| breakout dn48 | 0% | 2% | 0.00x |
| range low<.1 | 0% | 6% | 0.00x |
| 3 down bars | 0% | 10% | 0.00x |

### 3-4. Rules built from clues: ranked on train, then run ONCE on test

| rule | side | train n | train net R | train t | test n | test net R | test win% | test PF | test max DD R |
|---|---|---|---|---|---|---|---|---|---|
| rsi>70 & dist>3 | long | 75 | 32.5 | 2.3 | 58 | -16.4 | 33 | 0.62 | 19.1 |
| range high>.9 & vol high | long | 41 | 21.2 | 2.3 | 37 | 0.5 | 41 | 1.02 | 8.3 |
| rsi>70 & breakout up48 | long | 76 | 31.2 | 2.2 | 55 | -4.0 | 40 | 0.89 | 12.6 |
| er.2-.4 & dist>3 | long | 65 | 29.6 | 2.1 | 49 | -17.7 | 33 | 0.52 | 18.3 |
| dist>3 & breakout up48 | long | 75 | 29.5 | 2.1 | 60 | -16.8 | 32 | 0.63 | 18.5 |
| rsi>70 | long | 85 | 28.9 | 2.0 | 68 | -14.7 | 37 | 0.69 | 17.0 |
| dist>3 & range high>.9 | long | 86 | 29.0 | 1.9 | 67 | -15.0 | 30 | 0.71 | 21.0 |
| breakout up48 & vol high | long | 29 | 13.9 | 1.9 | 29 | -0.6 | 41 | 0.97 | 6.4 |
| rsi>70 & range high>.9 | long | 84 | 27.1 | 1.9 | 64 | -7.1 | 38 | 0.84 | 17.1 |
| slope up & breakout up48 | long | 83 | 28.2 | 1.9 | 54 | -7.5 | 39 | 0.80 | 13.4 |

Top-10 train rules positive on test: 1 of 10.

Best-by-train rule `rsi>70 & dist>3` (long) on the unseen test part, margin 300 x 30x (notional 9000), costs included: **-2632** total, worst drawdown 2740, 58 trades.

## PAXGUSDT

26280 1h bars (~3.0 years) 2023-10-25 to 2026-10-24. Train = first 60% (until 2025-08-12), test = the rest.

### 1. Movement available in hindsight (swings >= 8 ATR)

- swings: 164 (54.7 per year), median move 4.4%, median length 102 hours
- hindsight profit if every swing were caught perfectly: 322% of price per year (an upper bound nobody can reach)

### 2. Clues at the start of UP swings (what looked like this before a rally) - train period

| clue | at swing start | on all bars | lift |
|---|---|---|---|
| dist<-3 | 40% | 2% | 16.09x |
| breakout dn48 | 23% | 1% | 15.27x |
| rsi<30 | 31% | 2% | 14.02x |
| range low<.1 | 57% | 6% | 9.32x |
| er>.4 | 40% | 11% | 3.50x |
| breakout up48 | 0% | 3% | 0.00x |
| range high>.9 | 0% | 10% | 0.00x |
| 3 up bars | 0% | 7% | 0.00x |

### 2. Clues at the start of DOWN swings - train period

| clue | at swing start | on all bars | lift |
|---|---|---|---|
| breakout up48 | 22% | 3% | 8.53x |
| dist>3 | 33% | 5% | 6.23x |
| range high>.9 | 61% | 10% | 5.96x |
| rsi>70 | 31% | 5% | 5.79x |
| er>.4 | 36% | 11% | 3.16x |
| dist-3..-1 | 0% | 17% | 0.00x |
| range low<.1 | 0% | 6% | 0.00x |
| breakout dn48 | 0% | 1% | 0.00x |

### 3-4. Rules built from clues: ranked on train, then run ONCE on test

| rule | side | train n | train net R | train t | test n | test net R | test win% | test PF | test max DD R |
|---|---|---|---|---|---|---|---|---|---|
| er>.4 & 3 up bars | long | 65 | 32.1 | 2.8 | 71 | 24.7 | 54 | 1.66 | 11.2 |
| dist>3 & 3 up bars | long | 51 | 26.5 | 2.6 | 67 | 26.0 | 55 | 1.75 | 6.9 |
| rsi>70 & 3 up bars | long | 64 | 29.5 | 2.5 | 61 | 23.5 | 54 | 1.71 | 13.6 |
| breakout up48 & 3 up bars | long | 66 | 27.5 | 2.2 | 67 | 15.0 | 46 | 1.36 | 14.4 |
| dist>3 & range high>.9 | long | 63 | 24.3 | 2.2 | 76 | 26.2 | 58 | 1.69 | 7.2 |
| er>.4 & dist>3 | long | 52 | 20.8 | 2.1 | 60 | 22.3 | 52 | 1.66 | 8.7 |
| rsi>70 & dist>3 | long | 59 | 21.3 | 2.0 | 68 | 14.6 | 53 | 1.38 | 10.4 |
| rsi55-70 & dist>3 | long | 36 | 14.6 | 1.9 | 58 | 16.5 | 59 | 1.59 | 5.7 |
| er>.4 & range high>.9 | long | 77 | 22.7 | 1.8 | 68 | 20.5 | 49 | 1.49 | 15.3 |
| dist1..3 & vol low | long | 89 | 25.5 | 1.8 | 61 | -4.1 | 38 | 0.91 | 25.3 |

Top-10 train rules positive on test: 9 of 10.

Best-by-train rule `er>.4 & 3 up bars` (long) on the unseen test part, margin 300 x 30x (notional 9000), costs included: **+2055** total, worst drawdown 1355, 71 trades.

## Verdict

- BTCUSDT: 0 of 10 top rules held up on test (net > 0, t > 1, >= 12 trades).
- PAXGUSDT: 9 of 10 top rules held up on test (net > 0, t > 1, >= 12 trades).
- Luck baseline (random walk, same procedure, 5 trials): on average 36% of the top rules were positive on test; best single test result 11.4 R.

- No rule held up on both assets. Treat every single-asset result above as unconfirmed.
