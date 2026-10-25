# Reverse engineering v2: BTC and PAXG on 4h and 1d (train 50% / validation 25% / sealed test 25%)

## BTCUSDT 4h: 20084 bars, train 2017-08 to 2022-03, validation to 2024-07, test to 2026-10

Candidate rules tried: 1168. Profitable on train (PF>1.15, enough trades): 479. Also pass validation: **317**.

  - UP-moves (long entries in hindsight), 54 swings on train; clues most common at the start: breakout dn48 (x12.5), range low<.1 (x11.4), rsi<30 (x9.2), dist<-3 (x8.3)
  - DOWN-moves, 54 swings on train; clues most common at the start: breakout up48 (x8.4), range high>.9 (x5.4), rsi>70 (x4.9), dist>3 (x3.2)

Luck check, 8 random-walk series of the same length (no edge by construction): rules passing train+validation per series: 14, 16, 67, 71, 55, 30, 238, 22. In **8 of 8** series the process still produced at least one top-5 rule that looks profitable on the test (n>=10, PF>1.15). So a profitable-looking test result is only meaningful if it beats this luck rate.

| rule | side | exit | train n/PF/R | val n/PF/R | TEST n | TEST win% | TEST net R | TEST PF | TEST max DD R |
|---|---|---|---|---|---|---|---|---|---|
| breakout up48 & vol low | long | chand | 48/2.99/+27.4 | 18/2.84/+8.8 | 26 | 46 | +3.0 | 1.31 | 4.7 |
| rsi>70 & vol low | long | chand | 46/3.84/+32.2 | 25/2.54/+10.1 | 22 | 50 | +8.6 | 2.20 | 3.2 |
| range high>.9 & vol high | long | delay | 37/2.43/+21.9 | 23/2.53/+14.7 | 18 | 39 | +0.7 | 1.07 | 4.7 |
| range high>.9 & vol low | long | chand | 68/2.40/+29.9 | 33/2.32/+15.1 | 34 | 44 | +7.7 | 1.86 | 4.6 |
| breakout up48 & vol low | long | delay | 42/2.35/+26.6 | 16/2.14/+9.5 | 20 | 55 | +6.9 | 1.72 | 3.2 |

## BTCUSDT 1d: 3351 bars, train 2017-08 to 2022-03, validation to 2024-07, test to 2026-10

Candidate rules tried: 1168. Profitable on train (PF>1.15, enough trades): 228. Also pass validation: **156**.

  - UP-moves (long entries in hindsight), 8 swings on train; clues most common at the start: dist<-3 (x9.5), range low<.1 (x8.7), breakout dn48 (x8.1), rsi<30 (x5.0)
  - DOWN-moves, 8 swings on train; clues most common at the start: breakout up48 (x4.9), range high>.9 (x3.2), rsi55-70 (x2.7), dist>3 (x2.3)

Luck check, 8 random-walk series of the same length (no edge by construction): rules passing train+validation per series: 10, 22, 69, 60, 33, 60, 169, 18. In **7 of 8** series the process still produced at least one top-5 rule that looks profitable on the test (n>=10, PF>1.15). So a profitable-looking test result is only meaningful if it beats this luck rate.

| rule | side | exit | train n/PF/R | val n/PF/R | TEST n | TEST win% | TEST net R | TEST PF | TEST max DD R |
|---|---|---|---|---|---|---|---|---|---|
| rsi>70 & range high>.9 | long | delay | 15/6.52/+16.8 | 9/5.22/+6.7 | 8 | 62 | +3.8 | 2.59 | 2.4 |
| dist>3 & range high>.9 | long | delay | 15/6.68/+17.0 | 8/4.68/+6.5 | 8 | 50 | +2.7 | 2.03 | 2.6 |
| rsi>70 | long | chand | 17/6.34/+11.7 | 9/4.43/+7.5 | 9 | 33 | +1.2 | 1.37 | 2.0 |
| er.2-.4 & vol high | long | delay | 15/3.74/+11.1 | 8/4.08/+4.6 | 9 | 33 | -3.2 | 0.26 | 3.2 |
| dist1..3 & slope up | long | chand | 20/3.86/+16.0 | 12/3.58/+8.3 | 16 | 31 | +1.3 | 1.30 | 1.8 |

## PAXGUSDT 4h: 13496 bars, train 2020-08 to 2023-09, validation to 2025-04, test to 2026-10

Candidate rules tried: 1168. Profitable on train (PF>1.15, enough trades): 6. Also pass validation: **4**.

  - UP-moves (long entries in hindsight), 31 swings on train; clues most common at the start: breakout dn48 (x14.8), range low<.1 (x7.2), dist<-3 (x6.7), rsi<30 (x6.6)
  - DOWN-moves, 32 swings on train; clues most common at the start: breakout up48 (x9.8), dist>3 (x8.6), rsi>70 (x5.8), range high>.9 (x4.7)

Luck check, 8 random-walk series of the same length (no edge by construction): rules passing train+validation per series: 24, 49, 37, 85, 38, 54, 71, 29. In **7 of 8** series the process still produced at least one top-5 rule that looks profitable on the test (n>=10, PF>1.15). So a profitable-looking test result is only meaningful if it beats this luck rate.

| rule | side | exit | train n/PF/R | val n/PF/R | TEST n | TEST win% | TEST net R | TEST PF | TEST max DD R |
|---|---|---|---|---|---|---|---|---|---|
| er>.4 & dist1..3 | long | delay | 37/1.57/+6.9 | 27/2.99/+16.1 | 27 | 48 | +8.9 | 1.59 | 7.3 |
| rsi55-70 & er.2-.4 | long | delay | 53/1.24/+6.1 | 36/2.41/+19.0 | 51 | 51 | +17.8 | 1.66 | 9.8 |
| rsi55-70 & er>.4 | long | delay | 35/1.21/+2.9 | 29/2.88/+16.4 | 37 | 49 | +10.4 | 1.50 | 7.8 |
| vol high & 3 down bars | long | delay | 43/1.18/+3.6 | 23/1.71/+7.2 | 32 | 53 | +10.7 | 1.68 | 3.6 |

## PAXGUSDT 1d: 2250 bars, train 2020-08 to 2023-09, validation to 2025-04, test to 2026-10

Candidate rules tried: 1168. Profitable on train (PF>1.15, enough trades): 14. Also pass validation: **3**.

  - UP-moves (long entries in hindsight), 4 swings on train; clues most common at the start: breakout dn48 (x46.9), dist<-3 (x19.9), rsi<30 (x19.9), range low<.1 (x11.5)
  - DOWN-moves, 5 swings on train; clues most common at the start: rsi>70 (x9.2), breakout up48 (x9.2), range high>.9 (x6.2), dist>3 (x4.6)

Luck check, 8 random-walk series of the same length (no edge by construction): rules passing train+validation per series: 15, 17, 13, 17, 17, 40, 49, 13. In **5 of 8** series the process still produced at least one top-5 rule that looks profitable on the test (n>=10, PF>1.15). So a profitable-looking test result is only meaningful if it beats this luck rate.

| rule | side | exit | train n/PF/R | val n/PF/R | TEST n | TEST win% | TEST net R | TEST PF | TEST max DD R |
|---|---|---|---|---|---|---|---|---|---|
| er<.2 | long | delay | 19/1.29/+1.8 | 11/99.00/+9.6 | 12 | 42 | +6.2 | 2.07 | 3.4 |
| rsi45-55 & er<.2 | long | delay | 19/1.20/+1.3 | 11/99.00/+10.2 | 12 | 50 | +6.0 | 2.26 | 3.7 |
| rsi45-55 | long | delay | 19/1.18/+1.2 | 12/99.00/+11.5 | 12 | 50 | +6.1 | 2.29 | 3.6 |
