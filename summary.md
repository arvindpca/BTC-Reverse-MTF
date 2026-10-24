# BTC + PAXG strategy search (4h / 1h / 15m / 1m)

Window 2026-04-27 16:49:00+00:00 -> 2026-10-24 16:48:00+00:00; train/test split 2026-08-13 16:49:00+00:00. Costs 0.06% fee + 0.02% slippage per side. 896 configs x 2 assets, ranked on TRAIN only.

## Verdict: NO EDGE PROVEN: the pooled train winner does not hold up on the untouched test part.

- configs profitable on pooled test (all): 18%
- top-10 pooled train configs profitable on test: 90%
- best config positive on every asset's test: False

## Top-10 by pooled TRAIN net R (test columns = untouched data)

| family | config | train n | train R | test n | test R | test R/trade | test t | test R @half cost | test per asset |
|---|---|---|---|---|---|---|---|---|---|
| donchian | `{"N": 20, "atr_mult": 2.5, "confirm15": true, "htf": "with", "invert": false, "rr": 50.0, "trail_r": 3.0}` | 53 | +11.6 | 45 | +11.5 | +0.256 | +0.50 | +15.3 | BTC +11.6R(27) / PAX -0.1R(18) |
| donchian | `{"N": 20, "atr_mult": 2.5, "confirm15": false, "htf": "with", "invert": false, "rr": 50.0, "trail_r": 3.0}` | 53 | +11.6 | 45 | +11.5 | +0.256 | +0.50 | +15.3 | BTC +11.6R(27) / PAX -0.1R(18) |
| donchian | `{"N": 40, "atr_mult": 2.5, "confirm15": false, "htf": "with", "invert": false, "rr": 50.0, "trail_r": 3.0}` | 41 | +10.5 | 39 | +2.0 | +0.051 | +0.09 | +5.4 | BTC +7.1R(23) / PAX -5.1R(16) |
| donchian | `{"N": 40, "atr_mult": 2.5, "confirm15": true, "htf": "with", "invert": false, "rr": 50.0, "trail_r": 3.0}` | 41 | +10.5 | 39 | +2.0 | +0.051 | +0.09 | +5.4 | BTC +7.1R(23) / PAX -5.1R(16) |
| donchian | `{"N": 80, "atr_mult": 1.5, "confirm15": false, "htf": "with", "invert": false, "rr": 50.0, "trail_r": 3.0}` | 43 | +9.5 | 31 | +4.8 | +0.156 | +0.33 | +8.4 | BTC +8.2R(19) / PAX -3.3R(12) |
| donchian | `{"N": 80, "atr_mult": 1.5, "confirm15": true, "htf": "with", "invert": false, "rr": 50.0, "trail_r": 3.0}` | 43 | +9.5 | 31 | +4.8 | +0.156 | +0.33 | +8.4 | BTC +8.2R(19) / PAX -3.3R(12) |
| ema_sar | `{"atr_mult": 2.5, "fast": 24, "htf": "any", "invert": false, "rr": 50.0, "slow": 96, "trail_r": 2.0}` | 60 | +8.8 | 48 | +2.3 | +0.048 | +0.14 | +6.3 | BTC +9.5R(28) / PAX -7.2R(20) |
| ema_sar | `{"atr_mult": 2.5, "fast": 12, "htf": "with", "invert": false, "rr": 50.0, "slow": 48, "trail_r": 2.0}` | 41 | +8.0 | 28 | -2.3 | -0.084 | -0.30 | -0.1 | BTC -6.2R(17) / PAX +3.9R(11) |
| donchian | `{"N": 20, "atr_mult": 1.5, "confirm15": true, "htf": "with", "invert": false, "rr": 50.0, "trail_r": 3.0}` | 60 | +7.6 | 46 | +0.0 | +0.000 | +0.00 | +5.4 | BTC +4.6R(31) / PAX -4.6R(15) |
| donchian | `{"N": 20, "atr_mult": 1.5, "confirm15": false, "htf": "with", "invert": false, "rr": 50.0, "trail_r": 3.0}` | 60 | +7.6 | 46 | +0.0 | +0.000 | +0.00 | +5.4 | BTC +4.6R(31) / PAX -4.6R(15) |

## By family (configs with enough test trades)

| family | configs | mean test R/trade | profitable on test |
|---|---|---|---|
| bollinger | 47 | -0.162 | 2% |
| donchian | 80 | -0.088 | 30% |
| ema_sar | 24 | -0.176 | 12% |
| sweep_big | 14 | -0.311 | 0% |
| sweep_small | 307 | -0.466 | 0% |
