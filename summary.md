# PAXGUSDT detailed analysis

26280 1h bars, 2023-10-25 to 2026-10-24. Price 1963 -> 3997 (buy&hold +104% overall, train part +71%, test part +20%).

## A. Test part: each rule long, and its mirror short

| rule | side | trades | net R | win% | PF | avg hold h | avg win R | avg loss R | time in market | P/L (300x30) |
|---|---|---|---|---|---|---|---|---|---|---|
| er>.4 & 3 up bars | long | 71 | +24.7 | 54 | 1.66 | 44 | 1.64 | -1.14 | 30% | +2055 |
| er>.4 & 3 down bars | short | 80 | -25.0 | 32 | 0.61 | 35 | 1.52 | -1.20 | 27% | -1473 |
| dist>3 & 3 up bars | long | 67 | +26.0 | 55 | 1.75 | 36 | 1.63 | -1.15 | 23% | +1758 |
| dist<-3 & 3 down bars | short | 49 | -4.0 | 41 | 0.88 | 35 | 1.49 | -1.17 | 16% | -296 |
| dist>3 & range high>.9 | long | 76 | +26.2 | 58 | 1.69 | 37 | 1.45 | -1.18 | 27% | +1885 |
| dist<-3 & range low<.1 | short | 64 | -9.9 | 44 | 0.77 | 33 | 1.15 | -1.17 | 20% | -889 |
| rsi>70 & 3 up bars | long | 61 | +23.5 | 54 | 1.71 | 36 | 1.72 | -1.18 | 21% | +1748 |
| rsi<30 & 3 down bars | short | 57 | -15.8 | 33 | 0.65 | 33 | 1.53 | -1.18 | 18% | -1474 |
| er>.4 & dist>3 | long | 60 | +22.3 | 52 | 1.66 | 36 | 1.81 | -1.17 | 21% | +1762 |
| er>.4 & dist<-3 | short | 52 | -9.1 | 40 | 0.74 | 38 | 1.25 | -1.14 | 19% | -600 |

## B. Lead rule `er>.4 & 3 up bars` in six equal time blocks (whole history, long)

| period | buy&hold % | trades | net R | win% | PF | P/L (300x30) |
|---|---|---|---|---|---|---|
| 2023-11 to 2024-04 | +17 | 16 | +6.8 | 62 | 1.96 | +713 |
| 2024-04 to 2024-10 | +20 | 15 | +11.0 | 73 | 3.41 | +873 |
| 2024-10 to 2025-04 | +21 | 24 | +11.7 | 67 | 2.26 | +962 |
| 2025-04 to 2025-10 | +25 | 24 | +14.0 | 62 | 2.26 | +946 |
| 2025-10 to 2026-04 | +15 | 30 | +10.9 | 47 | 1.62 | +698 |
| 2026-04 to 2026-10 | -15 | 27 | +2.4 | 52 | 1.16 | +384 |

Profitable blocks: 6 of 6.

## C. Does the rule beat random long entries? (test part, same stop/trailing exit)

- Rule: net +24.7 R over 71 trades.
- 200 random long-entry runs: median +2.0 R, 90th percentile +16.1 R, best +29.6 R, positive in 57% of runs.
- The rule beats 98% of random long runs. Random longs also make money here, so a big part of the result is the gold uptrend itself.

## D. How the profit is made (lead rule, test part)

- Total +24.7 R; the best 5 trades alone = +18.1 R (73% of total).
- Without the best 5 trades: +6.6 R.
- Longest losing streak: 8 trades. Worst single trade -1.37 R.
- Exit reasons: TRAIL 39, SL 31, TIME 1
- Median stop distance 0.95% (liquidation at 30x is about 2.8%).

Month by month (net R): 2025-08 -1.0, 2025-09 +5.7, 2025-10 +5.6, 2025-11 +4.4, 2025-12 -1.2, 2026-01 +9.5, 2026-02 +6.5, 2026-03 -2.8, 2026-04 -5.6, 2026-05 +2.3, 2026-06 -0.5, 2026-07 -2.4, 2026-08 +4.9, 2026-09 -2.3, 2026-10 +1.5

## E. Cost stress (lead rule, test part)

| fee+slippage per side (x1 = real assumption, 0.16% round trip) | net R | P/L (300x30) |
|---|---|---|
| 0.08% | +24.7 | +2055 |
| 0.16% | +11.1 | +1032 |
| 0.24% | -2.6 | +10 |
