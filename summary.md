# Intraday study inside the user's time windows (IST 18:30-23:30 and 00:00-02:00)

Context: SMC proxy on 1h (BOS bias + order-block retest), POC of previous 24h, volume >= 1.5 x 20-day average. Triggers on 15m/5m: OB retest, POC bounce, VWAP cross + RSI/MACD, support/resistance bounce and breakout. Stops: ATR chandelier trailing (1.5 or 2.5 x ATR, floor 0.25%) or 1.5 ATR stop + 2R target. Costs 0.06%+0.02% per side. Split: train <2024, validation 2024-01..2025-06, SEALED TEST 2025-07+.

## BTCUSDT: 518384 5m bars, 2021-11-20 to 2026-10-25

Configs: 684. Positive net R: train 2%, validation 2%, sealed test 5%. Average cost per trade: 0.35 R (this is the fee+slippage eaten by each trade, in units of the stop).

Time window vs all day (avg net R per config):

| win | configs | train | validation | sealed test |
|---|---|---|---|---|
| all_day | 342 | -432.6 | -310.0 | -294.5 |
| window | 342 | -127.7 | -100.9 | -94.9 |

Timeframe (avg net R per config):

| tf | configs | train | validation | sealed test |
|---|---|---|---|---|
| 15m | 342 | -152.0 | -105.9 | -113.5 |
| 5m | 342 | -408.4 | -305.0 | -275.8 |

Strategy family (avg net R per config):

| fam | configs | train | validation | sealed test |
|---|---|---|---|---|
| poc_bounce | 108 | -197.1 | -149.9 | -140.0 |
| smc_ob | 108 | -88.2 | -62.8 | -48.3 |
| smc_ob+poc | 108 | -30.6 | -26.4 | -18.2 |
| sr_bounce | 72 | -442.5 | -317.2 | -359.4 |
| sr_breakout | 72 | -234.3 | -236.9 | -216.4 |
| vwap+macd | 72 | -478.0 | -340.6 | -305.4 |
| vwap+rsi | 72 | -580.4 | -390.1 | -369.5 |
| vwap+rsi+macd | 72 | -452.5 | -308.4 | -288.8 |

Passed filter (net>0 & PF>1.15 in train AND validation, n>=40/25): **0** of 684.

Random-walk null with the same bars and volatility: passers by pure luck = **0** of 684; positive on validation 2%, on sealed test 4%.

### BTCUSDT 1m 'instant trend' (exploratory, 525600 1m bars, 2025-10-25 to 2026-10-25)

| config | trades (window) | win% | net R | PF | cost per trade (R) | trades (all day) | net R (all day) | PF (all day) |
|---|---|---|---|---|---|---|---|---|
| insta1m|er>0.5|vol>=0.0|ch1.5 | 385 | 23 | -244.5 | 0.25 | 0.62 | 1317 | -831.6 | 0.24 |
| insta1m|er>0.5|vol>=0.0|sl1.5_tp2 | 369 | 30 | -258.4 | 0.37 | 0.62 | 1232 | -795.5 | 0.40 |
| insta1m|er>0.5|vol>=2.0|ch1.5 | 287 | 21 | -185.7 | 0.26 | 0.62 | 819 | -507.9 | 0.26 |
| insta1m|er>0.5|vol>=2.0|sl1.5_tp2 | 281 | 28 | -207.4 | 0.35 | 0.62 | 791 | -527.1 | 0.39 |
| insta1m|er>0.7|vol>=0.0|ch1.5 | 41 | 22 | -11.6 | 0.64 | 0.60 | 172 | -122.0 | 0.20 |
| insta1m|er>0.7|vol>=0.0|sl1.5_tp2 | 37 | 35 | -16.4 | 0.52 | 0.60 | 168 | -127.9 | 0.29 |
| insta1m|er>0.7|vol>=2.0|ch1.5 | 30 | 27 | -4.7 | 0.81 | 0.60 | 108 | -72.4 | 0.27 |
| insta1m|er>0.7|vol>=2.0|sl1.5_tp2 | 27 | 41 | -9.4 | 0.63 | 0.59 | 106 | -79.9 | 0.32 |

## PAXGUSDT: 518384 5m bars, 2021-11-20 to 2026-10-25

Configs: 684. Positive net R: train 0%, validation 0%, sealed test 0%. Average cost per trade: 0.57 R (this is the fee+slippage eaten by each trade, in units of the stop).

Time window vs all day (avg net R per config):

| win | configs | train | validation | sealed test |
|---|---|---|---|---|
| all_day | 342 | -842.7 | -670.4 | -286.1 |
| window | 342 | -320.6 | -234.5 | -102.3 |

Timeframe (avg net R per config):

| tf | configs | train | validation | sealed test |
|---|---|---|---|---|
| 15m | 342 | -431.3 | -315.9 | -143.9 |
| 5m | 342 | -732.0 | -588.9 | -244.5 |

Strategy family (avg net R per config):

| fam | configs | train | validation | sealed test |
|---|---|---|---|---|
| poc_bounce | 108 | -418.1 | -338.4 | -124.0 |
| smc_ob | 108 | -175.2 | -143.3 | -61.0 |
| smc_ob+poc | 108 | -109.7 | -93.8 | -29.0 |
| sr_bounce | 72 | -1040.3 | -794.9 | -382.4 |
| sr_breakout | 72 | -475.0 | -335.9 | -195.6 |
| vwap+macd | 72 | -931.8 | -720.9 | -302.6 |
| vwap+rsi | 72 | -1111.3 | -881.6 | -355.5 |
| vwap+rsi+macd | 72 | -912.8 | -701.5 | -287.8 |

Passed filter (net>0 & PF>1.15 in train AND validation, n>=40/25): **0** of 684.

### PAXGUSDT 1m 'instant trend' (exploratory, 525600 1m bars, 2025-10-25 to 2026-10-25)

| config | trades (window) | win% | net R | PF | cost per trade (R) | trades (all day) | net R (all day) | PF (all day) |
|---|---|---|---|---|---|---|---|---|
| insta1m|er>0.5|vol>=0.0|ch1.5 | 391 | 21 | -243.4 | 0.25 | 0.64 | 1291 | -811.6 | 0.24 |
| insta1m|er>0.5|vol>=0.0|sl1.5_tp2 | 373 | 31 | -213.9 | 0.39 | 0.64 | 1198 | -745.5 | 0.37 |
| insta1m|er>0.5|vol>=2.0|ch1.5 | 234 | 20 | -162.3 | 0.18 | 0.63 | 667 | -434.2 | 0.23 |
| insta1m|er>0.5|vol>=2.0|sl1.5_tp2 | 223 | 26 | -162.0 | 0.29 | 0.63 | 648 | -434.1 | 0.35 |
| insta1m|er>0.7|vol>=0.0|ch1.5 | 120 | 22 | -74.6 | 0.18 | 0.64 | 359 | -220.1 | 0.20 |
| insta1m|er>0.7|vol>=0.0|sl1.5_tp2 | 118 | 31 | -54.6 | 0.42 | 0.64 | 354 | -222.9 | 0.30 |
| insta1m|er>0.7|vol>=2.0|ch1.5 | 71 | 21 | -45.3 | 0.14 | 0.64 | 192 | -125.5 | 0.17 |
| insta1m|er>0.7|vol>=2.0|sl1.5_tp2 | 67 | 25 | -37.0 | 0.34 | 0.64 | 188 | -125.6 | 0.29 |
