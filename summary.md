# CoinDCX futures intraday research: BTC + PAXG (5m / 15m)

Source: **coindcx**. Run at 2026-10-26 19:28 UTC. Research only, no orders.

## Data quality

| asset | tf | first | last | days | bars | missing % | dupes | outliers | zero-vol | status |
|---|---|---|---|---|---|---|---|---|---|---|
| BTC | 5m | 2026-04-29 19:25 | 2026-10-26 19:20 | 180.0 | 51840 | 0.0 | 0 | 22 | 0 | WARN |
| BTC | 15m | 2026-04-29 19:15 | 2026-10-26 19:00 | 179.99 | 17280 | 0.0 | 0 | 7 | 0 | WARN |
| PAXG | 5m | 2026-04-29 19:25 | 2026-10-26 19:20 | 180.0 | 51840 | 0.0 | 0 | 33 | 0 | WARN |
| PAXG | 15m | 2026-04-29 19:15 | 2026-10-26 19:00 | 179.99 | 17280 | 0.0 | 0 | 11 | 0 | WARN |

## Results (TEST = last 25%, never used for selection)

## BTC 5m

51840 bars, 2026-04-29 19:25 to 2026-10-26 19:20 UTC. Costs 0.079% per side (+funding). 1608 configs searched.

| segment | from | to | buy & hold |
|---|---|---|---|
| dev | 2026-04-30 20:25 | 2026-07-28 19:20 | -16.59% |
| val | 2026-07-28 19:25 | 2026-09-11 19:20 | 21.17% |
| test | 2026-09-11 19:25 | 2026-10-26 19:20 | 3.63% |

Search vs luck: best DEV t-stat (no filters) = -1.34; it beats 100% of 20 random-entry searches of the same size.

| side | config | DEV n / exp R | VAL n / exp R | TEST n | TEST win% | TEST exp R | TEST PF | TEST sum R | TEST max DD | gross exp R | 1.5x cost exp R | WF OOS sum R (pos folds) | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | rsi_rev25 [htf1h] sl 3.0ATR rr 3.0 8h | 46 / 0.1233 | 28 / -0.1988 | 27 | 26 | -0.6762 | 0.281 | -18.26 | 16.89% | -0.2842 | -0.866 | -9.14 (60%) | **INCONCLUSIVE (too few test trades)** |
| LONG | vwap_rev2.5 [us_13_21+vol_high] sl 3.0ATR rr 3.0 8h | 77 / -0.1858 | 34 / -0.311 | 38 | 34 | -0.4264 | 0.459 | -16.2 | 17.05% | -0.1413 | -0.5644 | -11.88 (40%) | **NO EDGE PROVEN** |
| LONG | sweep_rev48 [-] sl 3.0ATR rr 3.0 8h | 254 / -0.3913 | 129 / -0.5887 | 140 | 27 | -0.6011 | 0.405 | -84.15 | 57.6% | -0.1564 | -0.8182 | -146.25 (0%) | **NO EDGE PROVEN** |
| SHORT | rsi_rev30 [weekday+htf1h] sl 3.0ATR rr 3.0 8h | 58 / -0.1392 | 35 / -0.0552 | 34 | 41 | 0.0764 | 1.108 | 2.6 | 6.04% | 0.4242 | -0.0936 | -5.14 (40%) | **NO EDGE PROVEN** |
| SHORT | candle_momo [weekday+europe_07_13] sl 3.0ATR rr 3.0 8h | 73 / -0.0488 | 38 / -0.2155 | 38 | 32 | -0.2094 | 0.78 | -7.96 | 16.69% | 0.1889 | -0.4047 | -29.26 (0%) | **NO EDGE PROVEN** |
| SHORT | rsi_rev25 [rvol_spike+atr_expand] sl 2.0ATR rr 3.0 8h | 46 / -0.219 | 21 / -0.2382 | 18 | 17 | -0.9773 | 0.304 | -17.59 | 16.41% | -0.3333 | -1.2976 | -33.62 (20%) | **INCONCLUSIVE (too few test trades)** |

Baseline (enter every bar, exit picked on DEV): LONG TEST n=302 exp R=-0.5242; SHORT TEST n=302 exp R=-0.5317

## BTC 15m

17280 bars, 2026-04-29 19:15 to 2026-10-26 19:00 UTC. Costs 0.079% per side (+funding). 1461 configs searched.

| segment | from | to | buy & hold |
|---|---|---|---|
| dev | 2026-05-02 22:15 | 2026-07-28 19:00 | -19.06% |
| val | 2026-07-28 19:15 | 2026-09-11 19:00 | 21.08% |
| test | 2026-09-11 19:15 | 2026-10-26 19:00 | 3.75% |

Search vs luck: best DEV t-stat (no filters) = 0.62; it beats 100% of 20 random-entry searches of the same size.

| side | config | DEV n / exp R | VAL n / exp R | TEST n | TEST win% | TEST exp R | TEST PF | TEST sum R | TEST max DD | gross exp R | 1.5x cost exp R | WF OOS sum R (pos folds) | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | rsi_rev30 [rvol_spike] sl 3.0ATR rr 3.0 8h | 42 / 0.0538 | 21 / 0.0974 | 22 | 36 | -0.1466 | 0.749 | -3.22 | 5.4% | 0.0733 | -0.2519 | -1.1 (60%) | **INCONCLUSIVE (too few test trades)** |
| LONG | sweep_rev48 [-] sl 3.0ATR rr 3.0 3h | 106 / -0.2251 | 52 / -0.1397 | 61 | 43 | -0.1976 | 0.557 | -12.06 | 11.92% | 0.041 | -0.3143 | -30.2 (20%) | **NO EDGE PROVEN** |
| LONG | ema_pullback [-] sl 3.0ATR rr 1.5 8h | 128 / -0.2337 | 74 / -0.261 | 63 | 41 | -0.3142 | 0.525 | -19.8 | 20.08% | -0.0151 | -0.4582 | -32.86 (20%) | **NO EDGE PROVEN** |
| SHORT | vwap_rev2.5 [close_loc] sl 3.0ATR rr 1.5 8h | 57 / 0.0234 | 37 / -0.0867 | 38 | 37 | -0.3477 | 0.503 | -13.21 | 13.9% | -0.0565 | -0.4888 | -21.49 (0%) | **NO EDGE PROVEN** |
| SHORT | ema_pullback [adx_range] sl 3.0ATR rr 2.0 8h | 67 / -0.0793 | 33 / -0.1052 | 40 | 25 | -0.4057 | 0.461 | -16.23 | 17.51% | -0.1188 | -0.5436 | -17.78 (0%) | **NO EDGE PROVEN** |
| SHORT | rsi_rev30 [-] sl 3.0ATR rr 2.0 8h | 71 / -0.1492 | 46 / -0.2088 | 39 | 31 | -0.4949 | 0.344 | -19.3 | 17.76% | -0.2308 | -0.6221 | -39.28 (0%) | **NO EDGE PROVEN** |

Baseline (enter every bar, exit picked on DEV): LONG TEST n=190 exp R=-0.2868; SHORT TEST n=188 exp R=-0.3054

## PAXG 5m

51840 bars, 2026-04-29 19:25 to 2026-10-26 19:20 UTC. Costs 0.079% per side (+funding). 1608 configs searched.

| segment | from | to | buy & hold |
|---|---|---|---|
| dev | 2026-04-30 20:25 | 2026-07-28 19:20 | -12.78% |
| val | 2026-07-28 19:25 | 2026-09-11 19:20 | 8.35% |
| test | 2026-09-11 19:25 | 2026-10-26 19:20 | -7.59% |

Search vs luck: best DEV t-stat (no filters) = -4.78; it beats 95% of 20 random-entry searches of the same size.

| side | config | DEV n / exp R | VAL n / exp R | TEST n | TEST win% | TEST exp R | TEST PF | TEST sum R | TEST max DD | gross exp R | 1.5x cost exp R | WF OOS sum R (pos folds) | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | rsi_rev25 [htf4h] sl 3.0ATR rr 1.0 3h | 46 / -4.8235 | 27 / -2.4179 | 17 | 6 | -10.8675 | 0.001 | -184.75 | 90.8% | 0.1984 | -16.3635 | -285.13 (0%) | **INCONCLUSIVE (too few test trades)** |
| LONG | rsi_rev30 [-] sl 3.0ATR rr 3.0 8h | 286 / -2.6605 | 129 / -2.1173 | 172 | 19 | -4.04 | 0.051 | -694.87 | 99.98% | 0.2222 | -6.1442 | -1081.92 (0%) | **NO EDGE PROVEN** |
| LONG | vwap_rev2.5 [-] sl 3.0ATR rr 3.0 3h | 424 / -3.1495 | 207 / -2.6107 | 251 | 15 | -4.8537 | 0.03 | -1218.28 | 100.0% | 0.1405 | -7.3209 | -1958.22 (0%) | **NO EDGE PROVEN** |
| SHORT | sweep_rev48 [vol_high+body_strong] sl 3.0ATR rr 3.0 8h | 42 / 0.0335 | 26 / -0.5581 | 20 | 35 | -0.7846 | 0.408 | -15.69 | 17.8% | 0.5966 | -1.4595 | -31.38 (20%) | **INCONCLUSIVE (too few test trades)** |
| SHORT | ema_pullback [htf1h+vol_high] sl 3.0ATR rr 3.0 8h | 84 / -0.3464 | 34 / -0.2567 | 63 | 27 | -1.247 | 0.25 | -78.56 | 56.01% | 0.1003 | -1.9073 | -84.18 (0%) | **NO EDGE PROVEN** |
| SHORT | donchian_bo48 [europe_07_13+htf1h] sl 3.0ATR rr 3.0 3h | 48 / -4.1639 | 22 / -2.4515 | 32 | 16 | -4.6966 | 0.027 | -150.29 | 79.89% | -0.0081 | -7.0264 | -348.1 (0%) | **NO EDGE PROVEN** |

Baseline (enter every bar, exit picked on DEV): LONG TEST n=668 exp R=-4.7854; SHORT TEST n=426 exp R=-4.5199

## PAXG 15m

17280 bars, 2026-04-29 19:15 to 2026-10-26 19:00 UTC. Costs 0.079% per side (+funding). 1510 configs searched.

| segment | from | to | buy & hold |
|---|---|---|---|
| dev | 2026-05-02 22:15 | 2026-07-28 19:00 | -12.48% |
| val | 2026-07-28 19:15 | 2026-09-11 19:00 | 8.3% |
| test | 2026-09-11 19:15 | 2026-10-26 19:00 | -7.65% |

Search vs luck: best DEV t-stat (no filters) = -3.94; it beats 0% of 20 random-entry searches of the same size.

| side | config | DEV n / exp R | VAL n / exp R | TEST n | TEST win% | TEST exp R | TEST PF | TEST sum R | TEST max DD | gross exp R | 1.5x cost exp R | WF OOS sum R (pos folds) | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | donchian_bo48 [weekday+rvol_spike] sl 3.0ATR rr 3.0 8h | 46 / -0.2007 | 37 / -0.173 | 26 | 12 | -0.9474 | 0.171 | -24.63 | 23.17% | -0.5559 | -1.1377 | -26.28 (0%) | **INCONCLUSIVE (too few test trades)** |
| LONG | sweep_rev48 [-] sl 3.0ATR rr 3.0 8h | 114 / -0.6777 | 45 / -0.7952 | 62 | 27 | -0.9437 | 0.181 | -58.51 | 45.39% | -0.1504 | -1.3287 | -107.74 (0%) | **NO EDGE PROVEN** |
| LONG | candle_momo [-] sl 3.0ATR rr 3.0 8h | 153 / -0.7814 | 88 / -0.8433 | 96 | 16 | -2.0539 | 0.061 | -197.17 | 86.78% | -0.2024 | -2.9507 | -220.76 (0%) | **NO EDGE PROVEN** |
| SHORT | ema_pullback [weekday+rvol_quiet] sl 3.0ATR rr 3.0 8h | 71 / -0.0422 | 30 / -0.0828 | 35 | 20 | -0.4842 | 0.306 | -16.95 | 15.78% | -0.1191 | -0.659 | -24.06 (20%) | **NO EDGE PROVEN** |
| SHORT | sweep_rev48 [atr_expand+close_loc] sl 3.0ATR rr 3.0 8h | 40 / -0.1637 | 20 / -0.2387 | 17 | 41 | 0.049 | 1.091 | 0.83 | 4.11% | 0.5805 | -0.2069 | -3.66 (20%) | **INCONCLUSIVE (too few test trades)** |
| SHORT | donchian_bo48 [weekday+ema_stack] sl 3.0ATR rr 3.0 8h | 56 / -0.1255 | 20 / -0.2241 | 31 | 29 | -0.3005 | 0.609 | -9.31 | 12.58% | 0.0923 | -0.4908 | -21.71 (0%) | **NO EDGE PROVEN** |

Baseline (enter every bar, exit picked on DEV): LONG TEST n=224 exp R=-1.8115; SHORT TEST n=211 exp R=-1.5389

## How to read

- R = net profit / planned stop loss. exp R 0.10 = average +0.1 of the risk per trade after costs.
- CANDIDATE needs: >= 30 test trades, test and val positive, PF >= 1.15, still positive at 1.5x costs, walk-forward positive in >= 50% of folds, neighbouring exits also positive, and the search beating >= 95% of random searches.
- Even a CANDIDATE is only a reason to paper trade. Nothing here promises profit.
