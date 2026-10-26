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
