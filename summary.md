# PAXGUSDT: deep analysis of candidate v2

26280 1h bars, 2023-10-25 to 2026-10-24. v2 over the whole history: 100 trades, win 67%, net +60.7 R, PF 2.77, 300 -> 964 at 2% risk, max drawdown 10%, longest loss streak 3.

## 1. How the trades behave

| result of a trade | trades | share | total R |
|---|---|---|---|
| worse than -1R | 29 | 29% | -33.3 |
| -1R to 0 | 4 | 4% | -0.9 |
| 0 to +1R | 28 | 28% | +16.9 |
| +1R to +2R | 24 | 24% | +34.9 |
| +2R to +4R | 13 | 13% | +33.4 |
| above +4R | 2 | 2% | +9.8 |

- Top 10% of trades (10) make +31.9 R of the total +60.7 R. Without them: +28.8 R.
- Winners: avg +1.42 R, avg hold 109 h. Losers: avg -1.04 R, avg hold 98 h.
- Exit reasons: SL 29 trades avg -1.15 R; TIME 4 trades avg -0.10 R; TRAIL 67 trades avg +1.41 R
- Losers: 27% had been at least +1R in profit before reversing, 48% at least +0.5R.
- Winners: median worst dip before winning 0.43 R; 43% dipped more than half a stop first.

## 2. Winners vs losers: what differs at entry? (whole history, v2 trades)

| feature | avg for winners | avg for losers | R/trade when feature is above its median | below its median |
|---|---|---|---|---|
| er20 | 0.512 | 0.507 | +0.57 (n=50) | +0.64 (n=50) |
| rsi14 | 70.4 | 61.4 | +0.61 (n=50) | +0.60 (n=50) |
| dist_ema50_atr | 3.19 | 1.37 | +0.87 (n=50) | +0.35 (n=50) |
| dist_ema200_pct | 1.37 | 0.449 | +0.68 (n=50) | +0.54 (n=50) |
| atr_pct | 0.301 | 0.333 | +0.43 (n=50) | +0.79 (n=50) |
| atr_rank500 | 0.485 | 0.605 | +0.47 (n=50) | +0.75 (n=50) |
| run3_atr | 2.22 | 1.54 | +0.95 (n=50) | +0.27 (n=50) |
| ret24h_pct | 1.2 | 0.554 | +0.66 (n=50) | +0.56 (n=50) |
| ret72h_pct | 1.31 | 0.35 | +0.66 (n=50) | +0.56 (n=50) |
| from_7d_high_pct | -0.946 | -1.87 | +0.87 (n=50) | +0.35 (n=50) |
| vol_ratio20 | 1.85 | 1.4 | +0.64 (n=50) | +0.58 (n=50) |
| last_body_atr | 0.866 | 0.683 | +0.69 (n=50) | +0.52 (n=50) |
| last_close_pos | 0.748 | 0.765 | +0.62 (n=50) | +0.60 (n=50) |
| er20_prev | 0.423 | 0.432 | +0.52 (n=50) | +0.69 (n=50) |

## 3. Filters, validated both ways

28 single filters tried in each direction. Direction A: learn on the first 60%, test on the last 40%. Direction B: learn on the last 60%, test on the first 40%. Base v2 PF: A learn 2.54 / test 3.05; B learn 2.82 / test 2.50.

A filter counts only if it beats the base PF on both learn and test parts AND stays profitable, in BOTH directions.

Passing in A: 3. Passing in B: 0. Passing in BOTH: 0. (With 28 tries per direction, a few passes by luck alone are expected.)

No single filter passed in both directions, so v2 stays as it is.
