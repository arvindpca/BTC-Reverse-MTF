# Best trading time study: CoinDCX futures BTC + PAXG (5m / 15m)

Only one filter: the entry time window. Window chosen on DEV (first 50%), ranked on VAL (next 25%), TEST (last 25%) checked once. Costs as in the main study (0.079% per side + funding), min stop 0.25%.

## BTC 5m

Segments: dev 2026-04-30 20:30 to 2026-07-28 19:25, val 2026-07-28 19:30 to 2026-09-11 19:25, test 2026-09-11 19:30 to 2026-10-26 19:25

| side | setup | best window (chosen on DEV) | DEV n / exp R | VAL n / exp R | TEST n | TEST win% | TEST exp R | TEST PF | TEST sum R | beats luck | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | rsi_rev30 sl 5.0ATR rr 3.0 12h | 10:30-14:30 IST | 44 / -0.2349 | 20 / 0.4117 | 15 | 40 | -0.0741 | 0.904 | -1.11 | 40% | **INCONCLUSIVE (too few test trades)** |
| LONG | donchian_bo48 sl 2.0ATR rr 3.0 12h | 16:30-20:30 IST | 42 / -0.4223 | 25 / 0.3416 | 30 | 23 | -0.6145 | 0.452 | -18.44 | 30% | **NO EDGE PROVEN** |
| LONG | donchian_bo20 sl 3.0ATR rr 3.0 12h | 16:30-20:30 IST | 69 / -0.4143 | 36 / 0.2114 | 38 | 21 | -0.6875 | 0.371 | -26.12 | 10% | **NO EDGE PROVEN** |
| SHORT | candle_momo sl 3.0ATR rr 2.0 12h | 09:30-13:30 IST | 52 / 0.307 | 27 / 0.3506 | 30 | 37 | -0.3608 | 0.61 | -10.82 | 60% | **NO EDGE PROVEN** |
| SHORT | bos sl 5.0ATR rr 3.0 4h | 14:30-18:30 IST | 88 / -0.1205 | 40 / 0.0087 | 47 | 28 | -0.3661 | 0.457 | -17.21 | 0% | **NO EDGE PROVEN** |
| SHORT | macd_cross sl 3.0ATR rr 3.0 12h | 11:30-15:30 IST | 85 / 0.0212 | 34 / -0.022 | 42 | 26 | -0.4102 | 0.612 | -17.23 | 0% | **NO EDGE PROVEN** |

Hours whose average 1h move had the same direction in DEV, VAL and TEST: 16:30-17:30 IST (up, avg +0.029/+0.018/+0.054%), 19:30-20:30 IST (up, avg +0.017/+0.136/+0.016%), 21:30-22:30 IST (up, avg +0.001/+0.023/+0.028%), 22:30-23:30 IST (up, avg +0.038/+0.002/+0.006%), 23:30-00:30 IST (down, avg -0.069/-0.042/-0.017%), 01:30-02:30 IST (up, avg +0.075/+0.023/+0.033%)
Busiest hours (largest average 1h move): 18:30-19:30 IST 0.48%, 20:30-21:30 IST 0.39%, 19:30-20:30 IST 0.37%, 17:30-18:30 IST 0.33%

## BTC 15m

Segments: dev 2026-05-02 22:30 to 2026-07-28 19:15, val 2026-07-28 19:30 to 2026-09-11 19:15, test 2026-09-11 19:30 to 2026-10-26 19:15

| side | setup | best window (chosen on DEV) | DEV n / exp R | VAL n / exp R | TEST n | TEST win% | TEST exp R | TEST PF | TEST sum R | beats luck | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | donchian_bo20 sl 5.0ATR rr 3.0 4h | 13:30-19:30 IST | 49 / -0.1744 | 24 / 0.2263 | 26 | 35 | -0.0601 | 0.812 | -1.56 | 30% | **INCONCLUSIVE (too few test trades)** |
| LONG | bos sl 5.0ATR rr 1.0 12h | 13:30-17:30 IST | 50 / -0.087 | 26 / 0.1028 | 29 | 45 | -0.2381 | 0.578 | -6.91 | 0% | **INCONCLUSIVE (too few test trades)** |
| LONG | donchian_bo48 sl 3.0ATR rr 3.0 4h | 17:30-01:30 IST | 42 / -0.1626 | 26 / 0.1053 | 20 | 20 | -0.3993 | 0.384 | -7.99 | 0% | **INCONCLUSIVE (too few test trades)** |
| SHORT | fvg sl 2.0ATR rr 3.0 12h | 06:30-10:30 IST | 59 / 0.1115 | 24 / 0.1237 | 29 | 28 | -0.4588 | 0.521 | -13.31 | 0% | **INCONCLUSIVE (too few test trades)** |
| SHORT | macd_cross sl 3.0ATR rr 2.0 12h | 12:30-18:30 IST | 68 / 0.1179 | 28 / -0.0106 | 38 | 39 | -0.2265 | 0.707 | -8.61 | 0% | **NO EDGE PROVEN** |
| SHORT | vwap_rev1.5 sl 5.0ATR rr 1.5 12h | 08:30-16:30 IST | 40 / 0.1426 | 25 / -0.0242 | 25 | 36 | -0.4536 | 0.283 | -11.34 | 0% | **INCONCLUSIVE (too few test trades)** |

Hours whose average 1h move had the same direction in DEV, VAL and TEST: 16:30-17:30 IST (up, avg +0.029/+0.018/+0.054%), 19:30-20:30 IST (up, avg +0.017/+0.136/+0.016%), 21:30-22:30 IST (up, avg +0.001/+0.023/+0.028%), 22:30-23:30 IST (up, avg +0.038/+0.002/+0.006%), 23:30-00:30 IST (down, avg -0.069/-0.042/-0.017%), 01:30-02:30 IST (up, avg +0.075/+0.023/+0.033%)
Busiest hours (largest average 1h move): 18:30-19:30 IST 0.48%, 20:30-21:30 IST 0.39%, 19:30-20:30 IST 0.37%, 17:30-18:30 IST 0.33%

## PAXG 5m

Segments: dev 2026-04-30 20:30 to 2026-07-28 19:25, val 2026-07-28 19:30 to 2026-09-11 19:25, test 2026-09-11 19:30 to 2026-10-26 19:25

| side | setup | best window (chosen on DEV) | DEV n / exp R | VAL n / exp R | TEST n | TEST win% | TEST exp R | TEST PF | TEST sum R | beats luck | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | donchian_bo20 sl 5.0ATR rr 3.0 12h | 06:30-10:30 IST | 45 / -0.1175 | 23 / 0.3988 | 30 | 30 | -0.5328 | 0.398 | -15.98 | 90% | **NO EDGE PROVEN** |
| LONG | bb_reentry sl 5.0ATR rr 3.0 12h | 08:30-12:30 IST | 51 / -0.198 | 30 / 0.1877 | 27 | 22 | -0.6918 | 0.367 | -18.68 | 20% | **INCONCLUSIVE (too few test trades)** |
| LONG | ema_pullback sl 5.0ATR rr 3.0 12h | 08:30-16:30 IST | 48 / -0.0715 | 31 / 0.1048 | 24 | 33 | -0.6589 | 0.308 | -15.81 | 10% | **INCONCLUSIVE (too few test trades)** |
| SHORT | donchian_bo20 sl 3.0ATR rr 2.0 12h | 05:30-09:30 IST | 53 / 0.0334 | 23 / 0.0942 | 14 | 36 | -0.4549 | 0.535 | -6.37 | 10% | **INCONCLUSIVE (too few test trades)** |
| SHORT | ob_retest sl 5.0ATR rr 1.5 4h | 05:30-09:30 IST | 54 / -0.0916 | 28 / -0.0188 | 31 | 42 | -0.3767 | 0.423 | -11.68 | 0% | **NO EDGE PROVEN** |
| SHORT | macd_cross sl 3.0ATR rr 3.0 12h | 20:30-00:30 IST | 52 / 0.0425 | 28 / -0.0329 | 29 | 21 | -0.7017 | 0.333 | -20.35 | 0% | **INCONCLUSIVE (too few test trades)** |

Hours whose average 1h move had the same direction in DEV, VAL and TEST: 11:30-12:30 IST (up, avg +0.075/+0.039/+0.016%), 12:30-13:30 IST (down, avg -0.024/-0.001/-0.037%), 13:30-14:30 IST (down, avg -0.013/-0.031/-0.010%), 15:30-16:30 IST (up, avg +0.002/+0.013/+0.038%), 16:30-17:30 IST (up, avg +0.015/+0.064/+0.009%), 20:30-21:30 IST (down, avg -0.001/-0.020/-0.044%), 01:30-02:30 IST (down, avg -0.001/-0.022/-0.002%), 03:30-04:30 IST (down, avg -0.014/-0.008/-0.013%)
Busiest hours (largest average 1h move): 18:30-19:30 IST 0.27%, 17:30-18:30 IST 0.24%, 06:30-07:30 IST 0.21%, 20:30-21:30 IST 0.20%

## PAXG 15m

Segments: dev 2026-05-02 22:30 to 2026-07-28 19:15, val 2026-07-28 19:30 to 2026-09-11 19:15, test 2026-09-11 19:30 to 2026-10-26 19:15

| side | setup | best window (chosen on DEV) | DEV n / exp R | VAL n / exp R | TEST n | TEST win% | TEST exp R | TEST PF | TEST sum R | beats luck | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | bos sl 3.0ATR rr 2.0 12h | 06:30-12:30 IST | 44 / -0.1801 | 24 / 0.2883 | 26 | 35 | -0.2947 | 0.626 | -7.66 | 90% | **INCONCLUSIVE (too few test trades)** |
| LONG | fvg sl 3.0ATR rr 3.0 12h | 06:30-10:30 IST | 42 / -0.2064 | 27 / 0.2023 | 21 | 29 | -0.4402 | 0.43 | -9.24 | 50% | **INCONCLUSIVE (too few test trades)** |
| LONG | candle_momo sl 5.0ATR rr 3.0 12h | 05:30-13:30 IST | 41 / -0.1999 | 27 / 0.152 | 26 | 35 | -0.3752 | 0.39 | -9.76 | 50% | **INCONCLUSIVE (too few test trades)** |
| SHORT | ema_pullback sl 3.0ATR rr 1.0 4h | 17:30-23:30 IST | 45 / 0.0013 | 24 / 0.0844 | 23 | 39 | -0.2658 | 0.419 | -6.11 | 40% | **INCONCLUSIVE (too few test trades)** |
| SHORT | candle_momo sl 2.0ATR rr 3.0 12h | 06:30-14:30 IST | 40 / -0.0844 | 23 / 0.1769 | 22 | 27 | -0.6102 | 0.463 | -13.42 | 40% | **INCONCLUSIVE (too few test trades)** |
| SHORT | donchian_bo20 sl 2.0ATR rr 3.0 12h | 06:30-14:30 IST | 47 / -0.0093 | 22 / 0.0168 | 21 | 33 | -0.2688 | 0.741 | -5.64 | 20% | **INCONCLUSIVE (too few test trades)** |

Hours whose average 1h move had the same direction in DEV, VAL and TEST: 11:30-12:30 IST (up, avg +0.075/+0.039/+0.016%), 12:30-13:30 IST (down, avg -0.024/-0.001/-0.037%), 13:30-14:30 IST (down, avg -0.013/-0.031/-0.010%), 15:30-16:30 IST (up, avg +0.002/+0.013/+0.038%), 16:30-17:30 IST (up, avg +0.015/+0.064/+0.009%), 20:30-21:30 IST (down, avg -0.001/-0.020/-0.044%), 01:30-02:30 IST (down, avg -0.001/-0.022/-0.002%), 03:30-04:30 IST (down, avg -0.014/-0.008/-0.013%)
Busiest hours (largest average 1h move): 18:30-19:30 IST 0.27%, 17:30-18:30 IST 0.24%, 06:30-07:30 IST 0.21%, 20:30-21:30 IST 0.20%

