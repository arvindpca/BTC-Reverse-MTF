# Short-hold, cost-aware study (volatility events, stop floor 0.6% / 1.0%)

Hold <= 8h (15m) / 12h (1h). Pass rule: n>=40 train & >=25 validation, net R>0 and PF>1.15 in both. Test = 2025-07 onwards (sealed).

## BTCUSDT (172795 15m bars, 2021-11-20 to 2026-10-25)

Configs 64; positive net R: train 14%, validation 9%, test 12%. Average fee cost per trade 0.15 R. Passed train+validation: **0**.

| signal | configs | train avg R | validation avg R | test avg R |
|---|---|---|---|---|
| break_novol | 16 | -126.7 | -130.6 | -126.1 |
| break_vol | 16 | -70.2 | -96.2 | -92.5 |
| expand | 16 | -34.3 | -43.7 | -48.2 |
| fade | 16 | -7.0 | -5.0 | +0.8 |

Random-walk null (same bars): passers by pure luck = **0** of 48; positive on test 8%.

## ETHUSDT (172795 15m bars, 2021-11-20 to 2026-10-25)

Configs 64; positive net R: train 2%, validation 6%, test 30%. Average fee cost per trade 0.13 R. Passed train+validation: **0**.

| signal | configs | train avg R | validation avg R | test avg R |
|---|---|---|---|---|
| break_novol | 16 | -104.8 | -100.5 | -69.8 |
| break_vol | 16 | -72.2 | -60.5 | -45.9 |
| expand | 16 | -29.8 | -33.5 | -15.7 |
| fade | 16 | -13.4 | -6.9 | +1.6 |

## SOLUSDT (172795 15m bars, 2021-11-20 to 2026-10-25)

Configs 64; positive net R: train 23%, validation 0%, test 25%. Average fee cost per trade 0.09 R. Passed train+validation: **0**.

| signal | configs | train avg R | validation avg R | test avg R |
|---|---|---|---|---|
| break_novol | 16 | -98.2 | -126.9 | -99.8 |
| break_vol | 16 | -54.2 | -93.2 | -69.3 |
| expand | 16 | -26.3 | -37.2 | -31.2 |
| fade | 16 | -5.9 | -6.1 | +0.8 |
