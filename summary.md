# PAXGUSDT: final candidate check

26280 1h bars, 2023-10-25 to 2026-10-24.

## 1. Walk-forward (variant chosen on earlier data only)

| fold | chosen on train (best PF, >= 30 trades) | chosen: test n | test net R | test PF | base: test net R | base PF |
|---|---|---|---|---|---|---|
| 2024-10 to 2025-10 | base | 48 | +25.7 | 2.26 | +25.7 | 2.26 |
| 2025-10 to 2026-10 | stop4 | 51 | +13.7 | 1.55 | +13.3 | 1.41 |

Walk-forward total +39.4 R versus always-base +39.1 R. Choosing on earlier data did not hurt, so the selection process is not obviously overfitting.

## 2. Candidate v2 vs base in money (start 300, risk 2% of equity per trade, compounding, fees included)

| variant | part | trades | win% | net R | end equity | return | max drawdown | longest loss streak |
|---|---|---|---|---|---|---|---|---|
| base | whole history | 136 | 59 | +56.9 | 875 | +192% | 21% | 8 |
| base | last 40% (test) | 71 | 54 | +24.7 | 474 | +58% | 21% | 8 |
| base | last 12 months | 57 | 49 | +13.3 | 380 | +27% | 21% | 8 |
| stop4+noEurope | whole history | 100 | 67 | +62.0 | 988 | +229% | 10% | 3 |
| stop4+noEurope | last 40% (test) | 52 | 67 | +35.6 | 594 | +98% | 10% | 3 |
| stop4+noEurope | last 12 months | 41 | 63 | +23.0 | 466 | +55% | 10% | 3 |

For comparison, v2 on the test part with the old fixed 9000 position: +3508 total. That needs a much bigger account than 300 to survive its drawdowns.

## 3. Cost stress for v2 (last 40%, 2% risk)

| fee+slippage per side | net R | end equity | return |
|---|---|---|---|
| 0.08% | +35.6 | 594 | +98% |
| 0.16% | +26.1 | 492 | +64% |
| 0.24% | +16.6 | 408 | +36% |

## 4. Stop sizes under v2 (must stay inside the 30x liquidation distance, about 2.8%)

median 1.23%, 90th percentile 1.92%, max 2.48%. At 2% risk the position is about 1.6x the account, far below 30x.
