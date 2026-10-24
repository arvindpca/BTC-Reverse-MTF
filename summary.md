# v2 fee scenarios and BTC check

## PAXGUSDT

2023-10-25 to 2026-10-24, 26280 1h bars. v2 unchanged. 2% risk, start 300.

| fee scenario (per side) | round trip | part | trades | win% | net R | PF | 300 -> | max DD |
|---|---|---|---|---|---|---|---|---|
| assumed so far: 0.06 + 0.02 slip | 0.16% | whole | 100 | 67 | +60.7 | 2.77 | 965 | 10% |
| assumed so far: 0.06 + 0.02 slip | 0.16% | last 40% | 52 | 67 | +35.7 | 3.06 | 595 | 10% |
| INR futures taker 0.05 + 0.02 slip | 0.14% | whole | 100 | 67 | +62.7 | 2.87 | 1003 | 10% |
| INR futures taker 0.05 + 0.02 slip | 0.14% | last 40% | 52 | 67 | +36.8 | 3.18 | 609 | 10% |
| USDT starting taker 0.075 + 0.02 slip | 0.19% | whole | 100 | 67 | +57.8 | 2.64 | 910 | 11% |
| USDT starting taker 0.075 + 0.02 slip | 0.19% | last 40% | 52 | 67 | +33.9 | 2.89 | 575 | 11% |
| 0.075 taker +18% GST on fee + 0.02 slip | 0.22% | whole | 100 | 66 | +55.1 | 2.53 | 863 | 12% |
| 0.075 taker +18% GST on fee + 0.02 slip | 0.22% | last 40% | 52 | 65 | +32.3 | 2.74 | 557 | 12% |
| harsh: 0.075 +GST + 0.05 slip | 0.28% | whole | 100 | 66 | +49.1 | 2.29 | 767 | 14% |
| harsh: 0.075 +GST + 0.05 slip | 0.28% | last 40% | 52 | 65 | +28.7 | 2.44 | 519 | 14% |

## BTCUSDT

2023-10-25 to 2026-10-24, 26280 1h bars. v2 unchanged. 2% risk, start 300.

| fee scenario (per side) | round trip | part | trades | win% | net R | PF | 300 -> | max DD |
|---|---|---|---|---|---|---|---|---|
| assumed so far: 0.06 + 0.02 slip | 0.16% | whole | 76 | 46 | +14.4 | 1.32 | 384 | 20% |
| assumed so far: 0.06 + 0.02 slip | 0.16% | last 40% | 46 | 41 | -0.9 | 0.97 | 289 | 20% |
| INR futures taker 0.05 + 0.02 slip | 0.14% | whole | 76 | 46 | +15.2 | 1.34 | 391 | 19% |
| INR futures taker 0.05 + 0.02 slip | 0.14% | last 40% | 46 | 41 | -0.4 | 0.99 | 292 | 19% |
| USDT starting taker 0.075 + 0.02 slip | 0.19% | whole | 76 | 46 | +13.1 | 1.29 | 375 | 20% |
| USDT starting taker 0.075 + 0.02 slip | 0.19% | last 40% | 46 | 41 | -1.7 | 0.94 | 284 | 20% |
| 0.075 taker +18% GST on fee + 0.02 slip | 0.22% | whole | 76 | 46 | +12.0 | 1.26 | 367 | 20% |
| 0.075 taker +18% GST on fee + 0.02 slip | 0.22% | last 40% | 46 | 41 | -2.4 | 0.92 | 280 | 20% |
| harsh: 0.075 +GST + 0.05 slip | 0.28% | whole | 76 | 46 | +9.5 | 1.20 | 349 | 21% |
| harsh: 0.075 +GST + 0.05 slip | 0.28% | last 40% | 46 | 41 | -3.9 | 0.87 | 272 | 21% |
