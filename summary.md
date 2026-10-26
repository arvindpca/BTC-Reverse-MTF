# CoinDCX futures intraday research: BTC + PAXG (5m / 15m)

Round: **2 (min stop 0.25%, wider exits; round-1 TEST was already viewed, so TEST here is not pristine)**. Source: **coindcx**. Run at 2026-10-26 19:34 UTC. Research only, no orders.

## Data quality

| asset | tf | first | last | days | bars | missing % | dupes | outliers | zero-vol | status |
|---|---|---|---|---|---|---|---|---|---|---|
| BTC | 5m | 2026-04-29 19:30 | 2026-10-26 19:25 | 180.0 | 51840 | 0.0 | 0 | 22 | 0 | WARN |
| BTC | 15m | 2026-04-29 19:30 | 2026-10-26 19:15 | 179.99 | 17280 | 0.0 | 0 | 7 | 0 | WARN |
| PAXG | 5m | 2026-04-29 19:30 | 2026-10-26 19:25 | 180.0 | 51840 | 0.0 | 0 | 33 | 0 | WARN |
| PAXG | 15m | 2026-04-29 19:30 | 2026-10-26 19:15 | 179.99 | 17280 | 0.0 | 0 | 11 | 0 | WARN |

## Results (TEST = last 25%, never used for selection)

## BTC 5m

51840 bars, 2026-04-29 19:30 to 2026-10-26 19:25 UTC. Costs 0.079% per side (+funding). 1560 configs searched. Min stop 0.25%.

| segment | from | to | buy & hold |
|---|---|---|---|
| dev | 2026-04-30 20:30 | 2026-07-28 19:25 | -16.62% |
| val | 2026-07-28 19:30 | 2026-09-11 19:25 | 21.13% |
| test | 2026-09-11 19:30 | 2026-10-26 19:25 | 3.55% |

Search vs luck: best DEV t-stat (no filters) = -0.27; it beats 75% of 20 random-entry searches of the same size.

| side | config | DEV n / exp R | VAL n / exp R | TEST n | TEST win% | TEST exp R | TEST PF | TEST sum R | TEST max DD | gross exp R | 1.5x cost exp R | WF OOS sum R (pos folds) | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | sweep_rev48 [adx_range] sl 5.0ATR rr 2.0 12h | 58 / 0.0491 | 31 / 0.0018 | 34 | 47 | -0.0949 | 0.85 | -3.23 | 12.94% | 0.1766 | -0.2259 | -2.02 (60%) | **NO EDGE PROVEN** |
| LONG | rsi_rev25 [htf4h] sl 5.0ATR rr 1.5 4h | 40 / -0.0778 | 24 / -0.0916 | 19 | 37 | -0.2277 | 0.406 | -4.33 | 4.28% | -0.011 | -0.3321 | -7.71 (20%) | **INCONCLUSIVE (too few test trades)** |
| LONG | vwap_rev2.5 [-] sl 5.0ATR rr 3.0 12h | 155 / -0.2248 | 70 / -0.2393 | 74 | 35 | -0.2077 | 0.69 | -15.37 | 15.07% | 0.0428 | -0.3268 | -30.23 (0%) | **NO EDGE PROVEN** |
| SHORT | bb_reentry [ema200_side] sl 2.0ATR rr 3.0 12h | 67 / 0.1733 | 25 / 0.0087 | 37 | 27 | -0.3674 | 0.647 | -13.59 | 16.22% | 0.1177 | -0.6054 | -3.68 (40%) | **NO EDGE PROVEN** |
| SHORT | rsi_rev25 [rvol_spike+close_loc] sl 5.0ATR rr 2.0 12h | 41 / -0.0543 | 22 / -0.0731 | 12 | 50 | 0.0061 | 1.011 | 0.07 | 2.4% | 0.2228 | -0.0986 | -15.27 (20%) | **INCONCLUSIVE (too few test trades)** |
| SHORT | rsi_rev30 [rvol_spike+body_strong] sl 5.0ATR rr 2.0 12h | 49 / 0.0268 | 36 / -0.2292 | 23 | 52 | 0.3238 | 1.616 | 7.45 | 4.73% | 0.5716 | 0.2058 | -13.99 (20%) | **INCONCLUSIVE (too few test trades)** |

Baseline (enter every bar, exit picked on DEV): LONG TEST n=141 exp R=-0.2915; SHORT TEST n=155 exp R=-0.3092

## BTC 15m

17280 bars, 2026-04-29 19:30 to 2026-10-26 19:15 UTC. Costs 0.079% per side (+funding). 1520 configs searched. Min stop 0.25%.

| segment | from | to | buy & hold |
|---|---|---|---|
| dev | 2026-05-02 22:30 | 2026-07-28 19:15 | -18.91% |
| val | 2026-07-28 19:30 | 2026-09-11 19:15 | 21.13% |
| test | 2026-09-11 19:30 | 2026-10-26 19:15 | 3.55% |

Search vs luck: best DEV t-stat (no filters) = 0.37; it beats 40% of 20 random-entry searches of the same size.

| side | config | DEV n / exp R | VAL n / exp R | TEST n | TEST win% | TEST exp R | TEST PF | TEST sum R | TEST max DD | gross exp R | 1.5x cost exp R | WF OOS sum R (pos folds) | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | rsi_rev30 [atr_expand] sl 5.0ATR rr 3.0 12h | 42 / 0.071 | 20 / 0.1144 | 23 | 48 | 0.0844 | 1.296 | 1.94 | 2.78% | 0.2112 | 0.0265 | 7.88 (60%) | **INCONCLUSIVE (too few test trades)** |
| LONG | ema_pullback [europe_07_13+vwap_side] sl 5.0ATR rr 2.0 12h | 41 / -0.0449 | 23 / -0.0561 | 25 | 48 | -0.06 | 0.886 | -1.5 | 6.22% | 0.1456 | -0.1568 | 4.91 (80%) | **INCONCLUSIVE (too few test trades)** |
| LONG | sweep_rev48 [-] sl 5.0ATR rr 1.0 12h | 77 / -0.1164 | 38 / -0.0301 | 48 | 48 | -0.1057 | 0.735 | -5.07 | 8.32% | 0.0447 | -0.1769 | -3.74 (40%) | **NO EDGE PROVEN** |
| SHORT | vwap_rev2.5 [stoch_room] sl 5.0ATR rr 1.5 12h | 58 / -0.0115 | 36 / 0.0129 | 32 | 44 | -0.2462 | 0.527 | -7.88 | 9.81% | -0.0699 | -0.3281 | -13.66 (0%) | **NO EDGE PROVEN** |
| SHORT | ema_pullback [adx_range] sl 3.0ATR rr 2.0 12h | 55 / -0.0312 | 25 / -0.072 | 35 | 26 | -0.3917 | 0.499 | -13.71 | 14.39% | -0.1255 | -0.5195 | -15.19 (20%) | **NO EDGE PROVEN** |
| SHORT | rsi_rev30 [-] sl 5.0ATR rr 2.0 12h | 55 / -0.0896 | 37 / -0.0027 | 31 | 42 | -0.256 | 0.469 | -7.93 | 8.69% | -0.0965 | -0.3302 | -19.33 (20%) | **NO EDGE PROVEN** |

Baseline (enter every bar, exit picked on DEV): LONG TEST n=117 exp R=-0.1317; SHORT TEST n=130 exp R=-0.1278

## PAXG 5m

51840 bars, 2026-04-29 19:30 to 2026-10-26 19:25 UTC. Costs 0.079% per side (+funding). 1455 configs searched. Min stop 0.25%.

| segment | from | to | buy & hold |
|---|---|---|---|
| dev | 2026-04-30 20:30 | 2026-07-28 19:25 | -12.76% |
| val | 2026-07-28 19:30 | 2026-09-11 19:25 | 8.26% |
| test | 2026-09-11 19:30 | 2026-10-26 19:25 | -7.51% |

Search vs luck: best DEV t-stat (no filters) = 0.08; it beats 30% of 20 random-entry searches of the same size.

| side | config | DEV n / exp R | VAL n / exp R | TEST n | TEST win% | TEST exp R | TEST PF | TEST sum R | TEST max DD | gross exp R | 1.5x cost exp R | WF OOS sum R (pos folds) | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | donchian_bo48 [rvol_spike+ema200_side] sl 5.0ATR rr 3.0 12h | 80 / -0.0711 | 53 / -0.0851 | 42 | 19 | -0.8087 | 0.2 | -33.97 | 29.48% | -0.4151 | -0.9979 | -8.87 (40%) | **NO EDGE PROVEN** |
| LONG | ema_pullback [asia_00_07] sl 5.0ATR rr 3.0 12h | 46 / -0.1921 | 29 / -0.0651 | 26 | 27 | -0.6908 | 0.288 | -17.96 | 18.43% | -0.2407 | -0.9069 | -21.77 (20%) | **INCONCLUSIVE (too few test trades)** |
| LONG | sweep_rev48 [rvol_spike+vol_high] sl 2.0ATR rr 1.5 12h | 48 / -0.3344 | 24 / -0.2687 | 17 | 29 | -0.6395 | 0.321 | -10.87 | 10.83% | -0.1427 | -0.8796 | -25.61 (20%) | **INCONCLUSIVE (too few test trades)** |
| SHORT | ob_retest [ema_stack+bb_squeeze] sl 5.0ATR rr 3.0 12h | 63 / 0.1474 | 28 / -0.0871 | 34 | 29 | -0.3289 | 0.578 | -11.18 | 16.97% | 0.0822 | -0.5234 | -14.09 (40%) | **NO EDGE PROVEN** |
| SHORT | sweep_rev48 [vol_high] sl 5.0ATR rr 2.0 12h | 79 / 0.1868 | 51 / -0.0565 | 33 | 42 | -0.1042 | 0.807 | -3.44 | 4.74% | 0.2494 | -0.271 | -4.67 (60%) | **NO EDGE PROVEN** |
| SHORT | vwap_rev1.5 [rvol_quiet+htf4h] sl 5.0ATR rr 3.0 12h | 75 / -0.0706 | 25 / -0.3232 | 48 | 40 | -0.2564 | 0.629 | -12.3 | 16.58% | 0.1286 | -0.4376 | -14.74 (25%) | **NO EDGE PROVEN** |

Baseline (enter every bar, exit picked on DEV): LONG TEST n=102 exp R=-0.5573; SHORT TEST n=103 exp R=-0.25

## PAXG 15m

17280 bars, 2026-04-29 19:30 to 2026-10-26 19:15 UTC. Costs 0.079% per side (+funding). 1483 configs searched. Min stop 0.25%.

| segment | from | to | buy & hold |
|---|---|---|---|
| dev | 2026-05-02 22:30 | 2026-07-28 19:15 | -12.51% |
| val | 2026-07-28 19:30 | 2026-09-11 19:15 | 8.26% |
| test | 2026-09-11 19:30 | 2026-10-26 19:15 | -7.51% |

Search vs luck: best DEV t-stat (no filters) = -0.04; it beats 0% of 20 random-entry searches of the same size.

| side | config | DEV n / exp R | VAL n / exp R | TEST n | TEST win% | TEST exp R | TEST PF | TEST sum R | TEST max DD | gross exp R | 1.5x cost exp R | WF OOS sum R (pos folds) | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | candle_momo [vwap_side+vol_high] sl 3.0ATR rr 3.0 12h | 40 / 0.0982 | 30 / -0.0285 | 18 | 28 | -0.6443 | 0.234 | -11.6 | 12.36% | -0.3141 | -0.7996 | -9.41 (20%) | **INCONCLUSIVE (too few test trades)** |
| LONG | donchian_bo48 [weekday] sl 5.0ATR rr 2.0 12h | 45 / -0.0442 | 32 / 0.0017 | 26 | 35 | -0.46 | 0.232 | -11.96 | 11.95% | -0.2262 | -0.5706 | -13.51 (20%) | **INCONCLUSIVE (too few test trades)** |
| LONG | donchian_bo20 [vol_high+ema200_side] sl 3.0ATR rr 3.0 12h | 42 / -0.1146 | 27 / 0.2694 | 18 | 33 | -0.6345 | 0.241 | -11.42 | 12.05% | -0.3182 | -0.7863 | -2.88 (20%) | **INCONCLUSIVE (too few test trades)** |
| SHORT | ema_pullback [weekday+body_strong] sl 5.0ATR rr 1.5 12h | 65 / 0.0528 | 26 / 0.0121 | 34 | 32 | -0.2609 | 0.511 | -8.87 | 9.84% | -0.0204 | -0.3723 | -10.11 (40%) | **NO EDGE PROVEN** |
| SHORT | sweep_rev48 [close_loc] sl 5.0ATR rr 3.0 12h | 50 / -0.0053 | 28 / -0.0082 | 28 | 46 | 0.0378 | 1.106 | 1.06 | 4.32% | 0.2758 | -0.0716 | -11.61 (20%) | **INCONCLUSIVE (too few test trades)** |
| SHORT | donchian_bo48 [rsi_momo] sl 5.0ATR rr 3.0 12h | 61 / -0.0056 | 29 / -0.0071 | 31 | 32 | -0.2433 | 0.562 | -7.54 | 7.43% | 0.0379 | -0.3739 | -7.41 (20%) | **NO EDGE PROVEN** |

Baseline (enter every bar, exit picked on DEV): LONG TEST n=91 exp R=-0.4591; SHORT TEST n=81 exp R=-0.1466

## How to read

- R = net profit / planned stop loss. exp R 0.10 = average +0.1 of the risk per trade after costs.
- CANDIDATE needs: >= 30 test trades, test and val positive, PF >= 1.15, still positive at 1.5x costs, walk-forward positive in >= 50% of folds, neighbouring exits also positive, and the search beating >= 95% of random searches.
- Even a CANDIDATE is only a reason to paper trade. Nothing here promises profit.
