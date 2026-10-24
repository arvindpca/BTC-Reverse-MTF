# PAXGUSDT: lead rule conditions, timing and refinements

## 1. Exact conditions of the +2055 rule

All three must be true on a finished 1h candle, and the signal fires only on the first candle where they become true:

1. **Trend is clean:** Kaufman efficiency ratio over the last 20 hourly candles is above 0.40 (price moved mostly in one direction instead of zig-zagging).
2. **Momentum:** the last 3 hourly candles are all green (close above open).
3. **Side:** long only.

- Entry: at the close of that candle. Stop: 3 x ATR(14, 1h) below entry; trades with a stop under 0.3% or over 2.5% are skipped (the upper limit keeps the stop inside the 30x liquidation distance).
- Exit: trailing stop that starts after price has run 1.5 x risk and then follows 1 x risk behind the best price; or the stop; or a time exit after 480 hours. No reversing, no re-entry on the same signal, one trade at a time.
- Costs: fee 0.06% + slippage 0.02% per side (0.16% round trip). Size: margin 300 x 30 = 9000 notional.

## 2. When does it work?

Train = first 60% of history, test = last 40%. If a bucket is good in BOTH, it is a real pattern; if it flips, it is noise.

### By session (train)

| bucket | trades | net R | win% | avg R/trade |
|---|---|---|---|---|
| Asia   (UTC 00-08 = IST 05:30-13:30) | 18 | +16.5 | 72 | +0.92 |
| Europe (UTC 08-14 = IST 13:30-19:30) | 17 | +2.9 | 59 | +0.17 |
| US     (UTC 14-21 = IST 19:30-02:30) | 21 | +8.4 | 67 | +0.40 |
| Late   (UTC 21-24 = IST 02:30-05:30) | 9 | +4.3 | 56 | +0.48 |

### By session (test)

| bucket | trades | net R | win% | avg R/trade |
|---|---|---|---|---|
| Asia   (UTC 00-08 = IST 05:30-13:30) | 20 | +11.7 | 60 | +0.58 |
| Europe (UTC 08-14 = IST 13:30-19:30) | 13 | -13.1 | 8 | -1.00 |
| US     (UTC 14-21 = IST 19:30-02:30) | 26 | +25.4 | 73 | +0.98 |
| Late   (UTC 21-24 = IST 02:30-05:30) | 12 | +0.7 | 50 | +0.06 |

### By weekday (train)

| bucket | trades | net R | win% | avg R/trade |
|---|---|---|---|---|
| Mon | 16 | +12.9 | 75 | +0.80 |
| Tue | 13 | -0.8 | 54 | -0.06 |
| Wed | 9 | +7.3 | 78 | +0.81 |
| Thu | 6 | +0.7 | 50 | +0.11 |
| Fri | 14 | +9.4 | 71 | +0.67 |
| Sat+Sun | 7 | +2.8 | 43 | +0.40 |

### By weekday (test)

| bucket | trades | net R | win% | avg R/trade |
|---|---|---|---|---|
| Mon | 13 | +18.9 | 85 | +1.46 |
| Tue | 11 | +0.9 | 45 | +0.08 |
| Wed | 13 | +9.1 | 62 | +0.70 |
| Thu | 11 | -1.7 | 45 | -0.16 |
| Fri | 15 | +2.5 | 47 | +0.17 |
| Sat+Sun | 8 | -5.0 | 25 | -0.62 |

### Month by month (whole history)

| month | buy&hold % | trades | net R | P/L (300x30) |
|---|---|---|---|---|
| 2023-11 | +2.9 | 1 | +1.3 | +114 |
| 2023-12 | +0.2 | 4 | +0.3 | -45 |
| 2024-01 | -0.2 | 3 | -0.7 | -98 |
| 2024-02 | -1.4 | 2 | -0.8 | -75 |
| 2024-03 | +11.4 | 3 | +4.5 | +463 |
| 2024-04 | +3.6 | 3 | +2.1 | +353 |
| 2024-05 | +1.3 | 2 | +2.6 | +272 |
| 2024-06 | -0.9 | 3 | +0.7 | +57 |
| 2024-07 | +5.3 | 3 | +1.0 | +59 |
| 2024-08 | +2.5 | 3 | +0.4 | +48 |
| 2024-09 | +5.6 | 2 | +3.9 | +312 |
| 2024-10 | +4.5 | 3 | +1.2 | +38 |
| 2024-11 | -4.2 | 1 | +3.9 | +397 |
| 2024-12 | -0.2 | 2 | -0.6 | -145 |
| 2025-01 | +6.5 | 4 | +1.5 | +151 |
| 2025-02 | +2.0 | 5 | -1.6 | -204 |
| 2025-03 | +10.1 | 7 | +1.1 | +29 |
| 2025-04 | +4.2 | 4 | +8.6 | +821 |
| 2025-05 | +0.4 | 3 | +3.0 | +265 |
| 2025-06 | +0.7 | 3 | +1.5 | -134 |
| 2025-07 | -0.8 | 3 | -0.6 | -68 |
| 2025-08 | +5.0 | 6 | -0.0 | +4 |
| 2025-09 * | +12.0 | 5 | +3.5 | +250 |
| 2025-10 * | +3.2 | 5 | +5.6 | +473 |
| 2025-11 * | +6.0 | 5 | +5.2 | +242 |
| 2025-12 * | +2.3 | 6 | -1.9 | -71 |
| 2026-01 * | +11.6 | 6 | +9.5 | +986 |
| 2026-02 * | +10.9 | 4 | +6.5 | +713 |
| 2026-03 * | -12.7 | 5 | -3.9 | -581 |
| 2026-04 * | -1.5 | 5 | -5.6 | -676 |
| 2026-05 * | -1.8 | 5 | +3.5 | +316 |
| 2026-06 * | -11.7 | 2 | -0.5 | +22 |
| 2026-07 * | +1.1 | 6 | -2.4 | -261 |
| 2026-08 * | +10.0 | 4 | +4.9 | +529 |
| 2026-09 * | -6.4 | 5 | -2.3 | -129 |
| 2026-10 * | -4.0 | 3 | +1.5 | +149 |

Profitable months: 24 of 36 (rows marked * are in the test part). Months with a falling gold price (negative buy&hold) show how the rule behaves in a down move.

## 3. Can it be improved? (variants judged on train first)

12 variants tried (including the base). Choosing among many variants can pick luck, so a variant is only accepted if it also helps in the unseen test part.

| variant | train n | train net R | train PF | test n | test net R | test PF | test P/L (300x30) | test max DD |
|---|---|---|---|---|---|---|---|---|
| base | 65 | +32.1 | 2.20 | 71 | +24.7 | 1.66 | +2055 | 1355 |
| no weekend | 61 | +33.7 | 2.52 | 64 | +28.3 | 1.89 | +2359 | 1211 |
| ema50>ema200 | 55 | +9.1 | 1.33 | 47 | +20.5 | 1.81 | +1713 | 1182 |
| slope up (ema200 rising) | 62 | +4.9 | 1.14 | 50 | +17.4 | 1.61 | +1559 | 1422 |
| not vol low | 52 | +14.1 | 1.61 | 57 | +28.1 | 2.08 | +2253 | 1269 |
| skip worst train session: Europe | 58 | +27.0 | 2.16 | 59 | +36.6 | 2.51 | +3076 | 1012 |
| stop 2 ATR | 89 | -16.6 | 0.71 | 96 | -3.8 | 0.94 | -618 | 1589 |
| stop 4 ATR | 50 | +29.9 | 2.81 | 62 | +26.3 | 1.96 | +2264 | 1059 |
| trail 0.75R after 1.5R | 69 | +23.6 | 1.81 | 80 | +10.3 | 1.24 | +993 | 1220 |
| trail 1.5R after 1.5R | 58 | +33.8 | 2.44 | 69 | +18.6 | 1.49 | +1024 | 1599 |
| trail 1R after 1R | 73 | +22.2 | 1.89 | 77 | +16.1 | 1.42 | +1302 | 1398 |
| trail 1R after 2R | 57 | +40.6 | 2.82 | 71 | +19.7 | 1.45 | +901 | 2249 |

Best on TRAIN (more profit factor than base, >= 40 trades): **trail 1R after 2R**. On test it gives +19.7 R / PF 1.45 versus base +24.7 R / PF 1.66: it does NOT improve the unseen part, so keep the base rule.
