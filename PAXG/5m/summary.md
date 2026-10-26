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
