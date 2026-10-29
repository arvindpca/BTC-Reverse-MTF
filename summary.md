# CoinDCX futures intraday research: BTC + PAXG (5m / 15m)

Round: **1h/4h study (fresh search on 1h and 4h bars; 5m/15m results were not used to pick anything here)**. Source: **coindcx**. Run at 2026-10-29 05:32 UTC. Research only, no orders.

## Data quality

| asset | tf | first | last | days | bars | missing % | dupes | outliers | zero-vol | status |
|---|---|---|---|---|---|---|---|---|---|---|
| BTC | 1h | 2023-10-30 05:00 | 2026-10-29 04:00 | 1094.96 | 26278 | 0.008 | 0 | 6 | 0 | WARN |
| BTC | 4h | 2023-10-30 04:00 | 2026-10-29 04:00 | 1095.0 | 6571 | 0.0 | 0 | 0 | 0 | OK |
| PAXG | 1h | 2025-03-27 11:00 | 2026-10-29 04:00 | 580.71 | 13938 | 0.0 | 0 | 10 | 0 | WARN |
| PAXG | 4h | 2025-03-27 08:00 | 2026-10-29 04:00 | 580.83 | 3486 | 0.0 | 0 | 2 | 0 | WARN |

## Results (TEST = last 25%, never used for selection)

## BTC 1h

26278 bars, 2023-10-30 05:00 to 2026-10-29 04:00 UTC. Costs 0.079% per side (+funding). 1579 configs searched. Min stop 0.25%.

| segment | from | to | buy & hold |
|---|---|---|---|
| dev | 2023-11-11 17:00 | 2025-04-29 17:00 | 156.22% |
| val | 2025-04-29 18:00 | 2026-01-28 10:00 | -6.12% |
| test | 2026-01-28 11:00 | 2026-10-29 04:00 | -10.24% |

Search vs luck: best DEV t-stat (no filters) = 2.1; it beats 100% of 20 random-entry searches of the same size.

| side | config | DEV n / exp R | VAL n / exp R | TEST n | TEST win% | TEST exp R | TEST PF | TEST sum R | TEST max DD | gross exp R | 1.5x cost exp R | WF OOS sum R (pos folds) | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | candle_momo [adx_trend+htf1h] sl 1.5ATR rr 3.0 48h | 66 / 0.4301 | 28 / 0.5843 | 27 | 37 | 0.2017 | 1.278 | 5.45 | 8.41% | 0.4265 | 0.0973 | 6.4 (67%) | **INCONCLUSIVE (too few test trades)** |
| LONG | ema_pullback [weekend] sl 4.0ATR rr 3.0 48h | 55 / 0.133 | 22 / 0.4584 | 25 | 36 | -0.1476 | 0.721 | -3.69 | 5.51% | -0.0256 | -0.1947 | -1.73 (47%) | **INCONCLUSIVE (too few test trades)** |
| LONG | donchian_bo20 [vol_low] sl 4.0ATR rr 3.0 48h | 57 / 0.1814 | 35 / 0.1818 | 33 | 36 | -0.1886 | 0.73 | -6.22 | 10.77% | -0.0417 | -0.2473 | -2.06 (53%) | **NO EDGE PROVEN** |
| SHORT | candle_momo [asia_00_07] sl 4.0ATR rr 3.0 12h | 46 / 0.1348 | 26 / 0.1113 | 26 | 46 | -0.1052 | 0.688 | -2.74 | 4.39% | -0.0181 | -0.1452 | 1.64 (54%) | **INCONCLUSIVE (too few test trades)** |
| SHORT | ema_pullback [weekend+bb_squeeze] sl 1.5ATR rr 2.0 48h | 51 / 0.1024 | 31 / 0.023 | 33 | 30 | -0.3724 | 0.583 | -12.29 | 15.37% | -0.0909 | -0.5029 | -13.89 (33%) | **NO EDGE PROVEN** |
| SHORT | donchian_bo20 [-] sl 2.5ATR rr 3.0 48h | 191 / -0.0211 | 99 / 0.0359 | 105 | 34 | -0.1651 | 0.755 | -17.34 | 26.59% | -0.0249 | -0.224 | -32.91 (33%) | **NO EDGE PROVEN** |

Baseline (enter every bar, exit picked on DEV): LONG TEST n=174 exp R=-0.0921; SHORT TEST n=200 exp R=-0.0732

## BTC 4h

6571 bars, 2023-10-30 04:00 to 2026-10-29 04:00 UTC. Costs 0.079% per side (+funding). 1395 configs searched. Min stop 0.25%.

| segment | from | to | buy & hold |
|---|---|---|---|
| dev | 2023-12-10 20:00 | 2025-04-29 12:00 | 116.32% |
| val | 2025-04-29 16:00 | 2026-01-28 08:00 | -5.01% |
| test | 2026-01-28 12:00 | 2026-10-29 04:00 | -10.9% |

Search vs luck: best DEV t-stat (no filters) = 2.19; it beats 55% of 20 random-entry searches of the same size.

| side | config | DEV n / exp R | VAL n / exp R | TEST n | TEST win% | TEST exp R | TEST PF | TEST sum R | TEST max DD | gross exp R | 1.5x cost exp R | WF OOS sum R (pos folds) | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | donchian_bo48 [-] sl 4.0ATR rr 1.0 24h | 60 / 0.0558 | 28 / 0.0768 | 29 | 45 | -0.0749 | 0.648 | -2.17 | 2.73% | -0.0373 | -0.0907 | -5.29 (14%) | **NO EDGE PROVEN** |
| LONG | fvg [-] sl 1.5ATR rr 1.5 24h | 155 / 0.0379 | 80 / 0.0596 | 79 | 47 | -0.0325 | 0.91 | -2.57 | 10.51% | 0.0729 | -0.0782 | -6.47 (29%) | **NO EDGE PROVEN** |
| LONG | donchian_bo20 [europe_07_13] sl 1.5ATR rr 1.5 96h | 48 / 0.1552 | 26 / 0.116 | 27 | 30 | -0.3761 | 0.52 | -10.15 | 10.79% | -0.2593 | -0.4222 | -9.16 (43%) | **NO EDGE PROVEN** |
| SHORT | bos [bb_squeeze+rvol_spike] sl 2.5ATR rr 3.0 96h | 36 / 0.1798 | 22 / 0.3101 | 24 | 38 | -0.2041 | 0.643 | -4.9 | 5.94% | -0.1103 | -0.234 | 0.98 (29%) | **NO EDGE PROVEN** |
| SHORT | rsi_rev30 [vwap_side] sl 2.5ATR rr 2.0 96h | 33 / 0.1422 | 15 / 0.2038 | 14 | 36 | -0.3826 | 0.327 | -5.36 | 5.47% | -0.3026 | -0.4092 | 0.25 (29%) | **INCONCLUSIVE (too few test trades)** |
| SHORT | sweep_rev48 [weekday] sl 1.5ATR rr 3.0 96h | 49 / 0.1265 | 22 / 0.1783 | 25 | 32 | -0.2612 | 0.636 | -6.53 | 10.77% | -0.1488 | -0.3016 | -0.68 (29%) | **NO EDGE PROVEN** |

Baseline (enter every bar, exit picked on DEV): LONG TEST n=81 exp R=-0.0897; SHORT TEST n=87 exp R=-0.0681

## PAXG 1h

13938 bars, 2025-03-27 11:00 to 2026-10-29 04:00 UTC. Costs 0.079% per side (+funding). 1551 configs searched. Min stop 0.25%.

| segment | from | to | buy & hold |
|---|---|---|---|
| dev | 2025-04-08 23:00 | 2026-01-11 19:00 | 50.04% |
| val | 2026-01-11 20:00 | 2026-06-05 23:00 | -4.23% |
| test | 2026-06-06 00:00 | 2026-10-29 04:00 | -6.49% |

Search vs luck: best DEV t-stat (no filters) = 1.91; it beats 45% of 20 random-entry searches of the same size.

| side | config | DEV n / exp R | VAL n / exp R | TEST n | TEST win% | TEST exp R | TEST PF | TEST sum R | TEST max DD | gross exp R | 1.5x cost exp R | WF OOS sum R (pos folds) | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | donchian_bo48 [htf1h+rvol_spike] sl 4.0ATR rr 3.0 48h | 67 / 0.4056 | 24 / 0.6292 | 24 | 38 | -0.3502 | 0.52 | -8.41 | 11.32% | -0.1167 | -0.4514 | 13.39 (50%) | **INCONCLUSIVE (too few test trades)** |
| LONG | donchian_bo20 [asia_00_07+ema200_side] sl 4.0ATR rr 1.5 48h | 60 / 0.3473 | 21 / 0.2457 | 19 | 53 | -0.2512 | 0.538 | -4.77 | 7.0% | -0.0223 | -0.3459 | 15.79 (83%) | **INCONCLUSIVE (too few test trades)** |
| LONG | candle_momo [ema200_side+roc_side] sl 4.0ATR rr 3.0 48h | 75 / 0.4504 | 24 / 0.2688 | 23 | 30 | -0.2931 | 0.604 | -6.74 | 7.64% | -0.0776 | -0.3841 | -1.38 (50%) | **INCONCLUSIVE (too few test trades)** |
| SHORT | ema_pullback [ema200_side+rvol_quiet] sl 4.0ATR rr 1.5 48h | 41 / -0.0282 | 23 / 0.334 | 35 | 40 | -0.1534 | 0.739 | -5.37 | 6.99% | 0.0447 | -0.2362 | 2.3 (67%) | **NO EDGE PROVEN** |
| SHORT | donchian_bo48 [htf1h+body_strong] sl 2.5ATR rr 3.0 48h | 44 / -0.1974 | 33 / -0.1994 | 33 | 27 | -0.3821 | 0.582 | -12.61 | 17.5% | -0.0928 | -0.5079 | -7.07 (50%) | **NO EDGE PROVEN** |
| SHORT | bos [-] sl 4.0ATR rr 3.0 48h | 112 / -0.3157 | 63 / 0.0976 | 63 | 40 | -0.0521 | 0.913 | -3.28 | 12.87% | 0.1717 | -0.1416 | -3.44 (50%) | **NO EDGE PROVEN** |

Baseline (enter every bar, exit picked on DEV): LONG TEST n=109 exp R=-0.3445; SHORT TEST n=97 exp R=-0.1062

## PAXG 4h

3486 bars, 2025-03-27 08:00 to 2026-10-29 04:00 UTC. Costs 0.079% per side (+funding). 1331 configs searched. Min stop 0.25%.

| segment | from | to | buy & hold |
|---|---|---|---|
| dev | 2025-05-08 00:00 | 2026-01-11 16:00 | 33.37% |
| val | 2026-01-11 20:00 | 2026-06-05 20:00 | -4.23% |
| test | 2026-06-06 00:00 | 2026-10-29 04:00 | -6.49% |

Search vs luck: best DEV t-stat (no filters) = 2.25; it beats 95% of 20 random-entry searches of the same size.

| side | config | DEV n / exp R | VAL n / exp R | TEST n | TEST win% | TEST exp R | TEST PF | TEST sum R | TEST max DD | gross exp R | 1.5x cost exp R | WF OOS sum R (pos folds) | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | fvg [structure+ema200_side] sl 4.0ATR rr 1.5 96h | 35 / 0.4115 | 15 / 0.3587 | 9 | 33 | -0.1915 | 0.603 | -1.72 | 2.97% | -0.0858 | -0.225 | -0.6 (0%) | **INCONCLUSIVE (too few test trades)** |
| LONG | donchian_bo20 [-] sl 4.0ATR rr 2.0 96h | 32 / 0.3463 | 18 / 0.2438 | 12 | 50 | 0.0477 | 1.1 | 0.57 | 2.49% | 0.1544 | 0.0131 | -4.03 (0%) | **INCONCLUSIVE (too few test trades)** |
| LONG | bos [-] sl 4.0ATR rr 1.5 96h | 43 / 0.2176 | 23 / 0.1255 | 21 | 38 | -0.2629 | 0.483 | -5.52 | 5.45% | -0.1556 | -0.2978 | -7.04 (0%) | **NO EDGE PROVEN** |
| SHORT | bos [body_strong+close_loc] sl 1.5ATR rr 2.0 96h | 31 / -0.1162 | 22 / 0.2139 | 22 | 45 | 0.1734 | 1.283 | 3.82 | 4.93% | 0.4132 | 0.0789 | 2.52 (100%) | **NO EDGE PROVEN** |
| SHORT | ema_pullback [-] sl 1.5ATR rr 3.0 24h | 35 / -0.2163 | 26 / 0.1408 | 33 | 27 | -0.1091 | 0.78 | -3.6 | 10.32% | 0.0995 | -0.1989 | -0.41 (0%) | **NO EDGE PROVEN** |
| SHORT | rsi_rev30 [-] sl 2.5ATR rr 1.0 24h | 37 / -0.1029 | 15 / -0.2438 | 7 | 14 | -0.5859 | 0.013 | -4.1 | 4.04% | -0.4686 | -0.636 | -0.24 (0%) | **INCONCLUSIVE (too few test trades)** |

Baseline (enter every bar, exit picked on DEV): LONG TEST n=41 exp R=-0.1513; SHORT TEST n=49 exp R=-0.0704

## How to read

- R = net profit / planned stop loss. exp R 0.10 = average +0.1 of the risk per trade after costs.
- CANDIDATE needs: >= 30 test trades, test and val positive, PF >= 1.15, still positive at 1.5x costs, walk-forward positive in >= 50% of folds, neighbouring exits also positive, and the search beating >= 95% of random searches.
- Even a CANDIDATE is only a reason to paper trade. Nothing here promises profit.
