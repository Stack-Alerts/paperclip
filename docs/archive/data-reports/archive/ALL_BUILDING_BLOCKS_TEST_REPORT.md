# Building Blocks Comprehensive Test Report

**Generated:** 2026-01-15 19:42:38
**Test Period:** 180 days
**Duration:** 58.8 minutes (0.98 hours)

## Executive Summary

- **Total Blocks Tested:** 83
- **Successful:** 83 (100.0%)
- **Failed:** 0 (0.0%)
- **Total Signals Generated:** 1,415,032
- **Total Errors:** 10,991
- **Average Coverage:** 75.1%

## Coverage Leaderboard

| Rank | Block | Category | Coverage | Signals | Status |
|------|-------|----------|----------|---------|--------|
| 1 | wyckoff_accumulation | WYCKOFF | 90.0% | 17,181 | ⚠️ |
| 2 | bollinger_bands | VOLATILITY | 89.5% | 17,181 | ⚠️ |
| 3 | ema_255_vector | MOVING_AVERAGES | 88.9% | 17,181 | ⚠️ |
| 4 | ema_800_vector | MOVING_AVERAGES | 88.9% | 17,181 | ⚠️ |
| 5 | ema_crossover | INSTITUTIONAL | 88.9% | 17,181 | ⚠️ |
| 6 | ict_silver_bullet | SIGNALS | 88.9% | 17,181 | ⚠️ |
| 7 | pennant_pattern | PATTERNS | 88.9% | 17,181 | ⚠️ |
| 8 | power_hour_trends | MARKET_STRUCTURE | 88.9% | 17,181 | ⚠️ |
| 9 | fifty_pct_hod_lod | PRICE_LEVELS | 87.5% | 17,181 | ⚠️ |
| 10 | fifty_pct_intra_hod_lod | PRICE_LEVELS | 87.5% | 17,181 | ⚠️ |
| 11 | hod | PRICE_LEVELS | 87.5% | 17,181 | ⚠️ |
| 12 | lod | PRICE_LEVELS | 87.5% | 17,181 | ⚠️ |
| 13 | adr | VOLATILITY | 86.7% | 17,181 | ⚠️ |
| 14 | macd_price_forecasting | SIGNALS | 85.7% | 17,181 | ⚠️ |
| 15 | swing_breakout_sequence | PATTERNS | 85.7% | 17,181 | ⚠️ |
| 16 | swing_failure_pattern | SMC_ICT | 85.7% | 17,181 | ⚠️ |
| 17 | atr | VOLATILITY | 84.6% | 17,181 | ⚠️ |
| 18 | initial_balance_breakout | PATTERNS | 84.6% | 17,181 | ⚠️ |
| 19 | elliott_wave_count | ELLIOTT_WAVE | 83.3% | 17,181 | ⚠️ |
| 20 | elliott_wave_oscillator | ELLIOTT_WAVE | 83.3% | 17,181 | ⚠️ |
| 21 | kill_zones | SESSIONS | 83.3% | 17,181 | ⚠️ |
| 22 | liquidity | MARKET_STRUCTURE | 83.3% | 17,181 | ⚠️ |
| 23 | fibonacci_retracements | FIBONACCI | 81.8% | 17,181 | ⚠️ |
| 24 | macd_signal | OSCILLATORS | 81.8% | 17,181 | ⚠️ |
| 25 | asfx_a2_vwap | SIGNALS | 80.0% | 17,181 | ⚠️ |
| 26 | ema_200_trend | MOVING_AVERAGES | 80.0% | 17,042 | ⚠️ |
| 27 | stochastic_rsi | OSCILLATORS | 80.0% | 17,181 | ⚠️ |
| 28 | wyckoff_distribution | WYCKOFF | 80.0% | 17,181 | ⚠️ |
| 29 | adx | TREND | 78.6% | 17,181 | ⚠️ |
| 30 | adaptive_momentum_oscillator | SIGNALS | 77.8% | 17,181 | ⚠️ |
| 31 | anchored_vwap | INSTITUTIONAL | 77.8% | 17,181 | ⚠️ |
| 32 | ema_50_vector | MOVING_AVERAGES | 77.8% | 17,181 | ⚠️ |
| 33 | ema_55_vector | MOVING_AVERAGES | 77.8% | 17,181 | ⚠️ |
| 34 | flag_pattern | PATTERNS | 77.8% | 17,181 | ⚠️ |
| 35 | internal_pivot_pattern | PATTERNS | 77.8% | 17,181 | ⚠️ |
| 36 | symmetrical_triangle | PATTERNS | 77.8% | 17,181 | ⚠️ |
| 37 | wave_consolidation | MARKET_STRUCTURE | 77.8% | 17,181 | ⚠️ |
| 38 | wyckoff_reaccumulation | WYCKOFF | 77.8% | 17,181 | ⚠️ |
| 39 | asia_session_50_percent | PRICE_LEVELS | 75.0% | 17,181 | ⚠️ |
| 40 | balanced_price_range | SMC_ICT | 75.0% | 17,181 | ⚠️ |
| 41 | breaker_block | PRICE_ACTION | 75.0% | 17,181 | ⚠️ |
| 42 | fair_value_gap | PRICE_ACTION | 75.0% | 17,181 | ⚠️ |
| 43 | how | PRICE_LEVELS | 75.0% | 17,181 | ⚠️ |
| 44 | ichimoku_cloud | TREND | 75.0% | 17,181 | ⚠️ |
| 45 | ihod | PRICE_LEVELS | 75.0% | 17,181 | ⚠️ |
| 46 | ilod | PRICE_LEVELS | 75.0% | 17,181 | ⚠️ |
| 47 | liquidity_sweep | PRICE_ACTION | 75.0% | 17,181 | ⚠️ |
| 48 | market_depth | INSTITUTIONAL | 75.0% | 17,181 | ⚠️ |
| 49 | order_block | PRICE_ACTION | 75.0% | 17,181 | ⚠️ |
| 50 | order_flow_imbalance | INSTITUTIONAL | 75.0% | 17,181 | ⚠️ |
| 51 | premium_discount_zones | MARKET_STRUCTURE | 75.0% | 17,181 | ⚠️ |
| 52 | us_settlement | PRICE_LEVELS | 75.0% | 16,908 | ⚠️ |
| 53 | vwap | INSTITUTIONAL | 75.0% | 17,181 | ⚠️ |
| 54 | break_of_structure | SMC_ICT | 71.4% | 17,181 | ⚠️ |
| 55 | candle_2_close | PATTERNS | 71.4% | 17,181 | ⚠️ |
| 56 | change_of_character | SMC_ICT | 71.4% | 17,181 | ⚠️ |
| 57 | displacement | SMC_ICT | 71.4% | 17,181 | ⚠️ |
| 58 | ema_20_50_cross | MOVING_AVERAGES | 71.4% | 17,181 | ⚠️ |
| 59 | inducement | SMC_ICT | 71.4% | 17,181 | ⚠️ |
| 60 | mitigation_block | SMC_ICT | 71.4% | 17,181 | ⚠️ |
| 61 | optimal_trade_entry | SMC_ICT | 71.4% | 17,181 | ⚠️ |
| 62 | three_bar_reversal | PATTERNS | 71.4% | 17,181 | ⚠️ |
| 63 | cup_and_handle | PATTERNS | 66.7% | 17,181 | ⚠️ |
| 64 | ema_20_50_trend | MOVING_AVERAGES | 66.7% | 17,181 | ⚠️ |
| 65 | market_structure_shift | SMC_ICT | 66.7% | 17,181 | ⚠️ |
| 66 | swing_points | MARKET_STRUCTURE | 66.7% | 17,181 | ⚠️ |
| 67 | low | PRICE_LEVELS | 63.6% | 17,181 | ⚠️ |
| 68 | ascending_triangle | PATTERNS | 62.5% | 17,181 | ⚠️ |
| 69 | descending_triangle | PATTERNS | 62.5% | 17,181 | ⚠️ |
| 70 | double_bottom | PATTERNS | 62.5% | 17,181 | ⚠️ |
| 71 | double_top | PATTERNS | 62.5% | 17,181 | ⚠️ |
| 72 | falling_wedge | PATTERNS | 62.5% | 17,181 | ⚠️ |
| 73 | head_and_shoulders | PATTERNS | 62.5% | 6,602 | ⚠️ |
| 74 | inverse_head_and_shoulders | PATTERNS | 62.5% | 17,181 | ⚠️ |
| 75 | rising_wedge | PATTERNS | 62.5% | 17,181 | ⚠️ |
| 76 | rounding_bottom | PATTERNS | 62.5% | 17,181 | ⚠️ |
| 77 | rsi_divergence | OSCILLATORS | 62.5% | 17,181 | ⚠️ |
| 78 | triple_bottom | PATTERNS | 62.5% | 17,181 | ⚠️ |
| 79 | triple_top | PATTERNS | 62.5% | 17,181 | ⚠️ |
| 80 | supply_demand_zones | SUPPLY_DEMAND | 60.0% | 17,181 | ⚠️ |
| 81 | range_liquidity | MARKET_STRUCTURE | 57.1% | 17,181 | ⚠️ |
| 82 | session_time | SESSIONS | 50.0% | 17,181 | ⚠️ |
| 83 | trailing_stop | RISK_MANAGEMENT | 44.4% | 17,181 | ❌ |

## Test Performance

- **Total Test Time:** 58.8 min (0.98 hours)
- **Average per Block:** 42.5s (0.71 min)
- **Fastest Test:** 0.6s
- **Slowest Test:** 504.8s

## Failed/Crashed Blocks

✅ **All blocks passed!**

## Detailed Results by Category

### ELLIOTT_WAVE (2 blocks)

| Block | Coverage | Signals | Missing Signals |
|-------|----------|---------|-----------------|
| elliott_wave_count | 83.3% | 17,181 | 3 |
| elliott_wave_oscillator | 83.3% | 17,181 | 2 |

### FIBONACCI (1 blocks)

| Block | Coverage | Signals | Missing Signals |
|-------|----------|---------|-----------------|
| fibonacci_retracements | 81.8% | 17,181 | 2 |

### INSTITUTIONAL (5 blocks)

| Block | Coverage | Signals | Missing Signals |
|-------|----------|---------|-----------------|
| ema_crossover | 88.9% | 17,181 | 1 |
| anchored_vwap | 77.8% | 17,181 | 2 |
| market_depth | 75.0% | 17,181 | 2 |
| order_flow_imbalance | 75.0% | 17,181 | 2 |
| vwap | 75.0% | 17,181 | 2 |

### MARKET_STRUCTURE (6 blocks)

| Block | Coverage | Signals | Missing Signals |
|-------|----------|---------|-----------------|
| power_hour_trends | 88.9% | 17,181 | 2 |
| liquidity | 83.3% | 17,181 | 2 |
| wave_consolidation | 77.8% | 17,181 | 2 |
| premium_discount_zones | 75.0% | 17,181 | 2 |
| swing_points | 66.7% | 17,181 | 4 |
| range_liquidity | 57.1% | 17,181 | 3 |

### MOVING_AVERAGES (7 blocks)

| Block | Coverage | Signals | Missing Signals |
|-------|----------|---------|-----------------|
| ema_255_vector | 88.9% | 17,181 | 1 |
| ema_800_vector | 88.9% | 17,181 | 1 |
| ema_200_trend | 80.0% | 17,042 | 2 |
| ema_50_vector | 77.8% | 17,181 | 2 |
| ema_55_vector | 77.8% | 17,181 | 2 |
| ema_20_50_cross | 71.4% | 17,181 | 2 |
| ema_20_50_trend | 66.7% | 17,181 | 3 |

### OSCILLATORS (3 blocks)

| Block | Coverage | Signals | Missing Signals |
|-------|----------|---------|-----------------|
| macd_signal | 81.8% | 17,181 | 2 |
| stochastic_rsi | 80.0% | 17,181 | 2 |
| rsi_divergence | 62.5% | 17,181 | 3 |

### PATTERNS (20 blocks)

| Block | Coverage | Signals | Missing Signals |
|-------|----------|---------|-----------------|
| pennant_pattern | 88.9% | 17,181 | 2 |
| swing_breakout_sequence | 85.7% | 17,181 | 2 |
| initial_balance_breakout | 84.6% | 17,181 | 3 |
| flag_pattern | 77.8% | 17,181 | 2 |
| internal_pivot_pattern | 77.8% | 17,181 | 2 |
| symmetrical_triangle | 77.8% | 17,181 | 2 |
| candle_2_close | 71.4% | 17,181 | 2 |
| three_bar_reversal | 71.4% | 17,181 | 2 |
| cup_and_handle | 66.7% | 17,181 | 3 |
| ascending_triangle | 62.5% | 17,181 | 3 |
| descending_triangle | 62.5% | 17,181 | 3 |
| double_bottom | 62.5% | 17,181 | 3 |
| double_top | 62.5% | 17,181 | 3 |
| falling_wedge | 62.5% | 17,181 | 3 |
| head_and_shoulders | 62.5% | 6,602 | 3 |
| inverse_head_and_shoulders | 62.5% | 17,181 | 3 |
| rising_wedge | 62.5% | 17,181 | 4 |
| rounding_bottom | 62.5% | 17,181 | 4 |
| triple_bottom | 62.5% | 17,181 | 3 |
| triple_top | 62.5% | 17,181 | 4 |

### PRICE_ACTION (4 blocks)

| Block | Coverage | Signals | Missing Signals |
|-------|----------|---------|-----------------|
| breaker_block | 75.0% | 17,181 | 2 |
| fair_value_gap | 75.0% | 17,181 | 2 |
| liquidity_sweep | 75.0% | 17,181 | 2 |
| order_block | 75.0% | 17,181 | 2 |

### PRICE_LEVELS (10 blocks)

| Block | Coverage | Signals | Missing Signals |
|-------|----------|---------|-----------------|
| fifty_pct_hod_lod | 87.5% | 17,181 | 1 |
| fifty_pct_intra_hod_lod | 87.5% | 17,181 | 1 |
| hod | 87.5% | 17,181 | 1 |
| lod | 87.5% | 17,181 | 1 |
| asia_session_50_percent | 75.0% | 17,181 | 2 |
| how | 75.0% | 17,181 | 2 |
| ihod | 75.0% | 17,181 | 2 |
| ilod | 75.0% | 17,181 | 2 |
| us_settlement | 75.0% | 16,908 | 2 |
| low | 63.6% | 17,181 | 4 |

### RISK_MANAGEMENT (1 blocks)

| Block | Coverage | Signals | Missing Signals |
|-------|----------|---------|-----------------|
| trailing_stop | 44.4% | 17,181 | 5 |

### SESSIONS (2 blocks)

| Block | Coverage | Signals | Missing Signals |
|-------|----------|---------|-----------------|
| kill_zones | 83.3% | 17,181 | 2 |
| session_time | 50.0% | 17,181 | 6 |

### SIGNALS (4 blocks)

| Block | Coverage | Signals | Missing Signals |
|-------|----------|---------|-----------------|
| ict_silver_bullet | 88.9% | 17,181 | 2 |
| macd_price_forecasting | 85.7% | 17,181 | 2 |
| asfx_a2_vwap | 80.0% | 17,181 | 2 |
| adaptive_momentum_oscillator | 77.8% | 17,181 | 2 |

### SMC_ICT (9 blocks)

| Block | Coverage | Signals | Missing Signals |
|-------|----------|---------|-----------------|
| swing_failure_pattern | 85.7% | 17,181 | 2 |
| balanced_price_range | 75.0% | 17,181 | 2 |
| break_of_structure | 71.4% | 17,181 | 2 |
| change_of_character | 71.4% | 17,181 | 2 |
| displacement | 71.4% | 17,181 | 2 |
| inducement | 71.4% | 17,181 | 2 |
| mitigation_block | 71.4% | 17,181 | 2 |
| optimal_trade_entry | 71.4% | 17,181 | 2 |
| market_structure_shift | 66.7% | 17,181 | 3 |

### SUPPLY_DEMAND (1 blocks)

| Block | Coverage | Signals | Missing Signals |
|-------|----------|---------|-----------------|
| supply_demand_zones | 60.0% | 17,181 | 5 |

### TREND (2 blocks)

| Block | Coverage | Signals | Missing Signals |
|-------|----------|---------|-----------------|
| adx | 78.6% | 17,181 | 3 |
| ichimoku_cloud | 75.0% | 17,181 | 2 |

### VOLATILITY (3 blocks)

| Block | Coverage | Signals | Missing Signals |
|-------|----------|---------|-----------------|
| bollinger_bands | 89.5% | 17,181 | 2 |
| adr | 86.7% | 17,181 | 2 |
| atr | 84.6% | 17,181 | 2 |

### WYCKOFF (3 blocks)

| Block | Coverage | Signals | Missing Signals |
|-------|----------|---------|-----------------|
| wyckoff_accumulation | 90.0% | 17,181 | 1 |
| wyckoff_distribution | 80.0% | 17,181 | 2 |
| wyckoff_reaccumulation | 77.8% | 17,181 | 2 |

## Individual Block Details

### adaptive_momentum_oscillator

**Category:** SIGNALS
**Class:** AdaptiveMomentumOscillator
**Weight:** 20

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 7

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 9 signals
- **Found in test:** 7 signals
- **Coverage:** 77.8%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NEUTRAL:** 27,352 (159.2%)
- **[✓] BEARISH:** 1,763 (10.3%)
- **[✓] BULLISH:** 1,742 (10.1%)
- **[✓] BEARISH_CROSS:** 1,437 (8.4%)
- **[✓] BULLISH_CROSS:** 1,436 (8.4%)
- **[✓] BEARISH_DIVERGENCE:** 326 (1.9%)
- **[✓] BULLISH_DIVERGENCE:** 306 (1.8%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### adr

**Category:** VOLATILITY
**Class:** ADR
**Weight:** 8

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 13

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 15 signals
- **Found in test:** 13 signals
- **Coverage:** 86.7%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] BEARISH:** 8,052 (46.9%)
- **[✓] BULLISH:** 5,228 (30.4%)
- **[✓] BELOW_ADR:** 4,442 (25.9%)
- **[✓] NEUTRAL:** 3,901 (22.7%)
- **[✓] CALM:** 3,351 (19.5%)
- **[✓] NORMAL:** 2,975 (17.3%)
- **[✓] WITHIN_ADR:** 2,936 (17.1%)
- **[✓] ABOVE_ADR:** 2,037 (11.9%)
- **[✓] NEAR_ADR:** 732 (4.3%)
- **[✓] HIGH:** 238 (1.4%)
- **[✓] ELEVATED:** 192 (1.1%)
- **[✓] VOLATILE:** 161 (0.9%)
- **[✓] EXTREME:** 117 (0.7%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### adx

**Category:** TREND
**Class:** ADX
**Weight:** 16

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 11

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 14 signals
- **Found in test:** 11 signals
- **Coverage:** 78.6%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)
- **VERY_STRONG_UPTREND** - ❌ ERROR MISSING

#### 📈 Signal Distribution

- **[✓] NEUTRAL:** 8,831 (51.4%)
- **[✓] BEARISH:** 4,407 (25.7%)
- **[✓] WEAK_DOWNTREND:** 4,361 (25.4%)
- **[✓] WEAK_UPTREND:** 4,327 (25.2%)
- **[✓] BULLISH:** 3,943 (22.9%)
- **[✓] MODERATE_DOWNTREND:** 3,863 (22.5%)
- **[✓] MODERATE_UPTREND:** 3,543 (20.6%)
- **[✓] STRONG_DOWNTREND:** 531 (3.1%)
- **[✓] STRONG_UPTREND:** 400 (2.3%)
- **[✓] RANGING:** 143 (0.8%)
- **[✓] VERY_STRONG_DOWNTREND:** 13 (0.1%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### anchored_vwap

**Category:** INSTITUTIONAL
**Class:** AnchoredVWAP
**Weight:** 15

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 7

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 9 signals
- **Found in test:** 7 signals
- **Coverage:** 77.8%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NEUTRAL:** 15,514 (90.3%)
- **[✓] NEAR_VWAP:** 12,284 (71.5%)
- **[✓] AT_VWAP:** 3,230 (18.8%)
- **[✓] ABOVE_ANCHORED_VWAP:** 839 (4.9%)
- **[✓] BULLISH:** 839 (4.9%)
- **[✓] BELOW_ANCHORED_VWAP:** 828 (4.8%)
- **[✓] BEARISH:** 828 (4.8%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### ascending_triangle

**Category:** PATTERNS
**Class:** AscendingTrianglePattern
**Weight:** 30

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 5

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 8 signals
- **Found in test:** 5 signals
- **Coverage:** 62.5%

#### ⚠️ Missing Signals (not found in test)

- **BEARISH** - ❌ ERROR MISSING
- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NO_PATTERN:** 15,712 (91.4%)
- **[✓] NEUTRAL:** 15,712 (91.4%)
- **[✓] BULLISH:** 1,469 (8.6%)
- **[✓] PATTERN_FORMING:** 1,328 (7.7%)
- **[✓] BULLISH_BREAKOUT:** 141 (0.8%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### asfx_a2_vwap

**Category:** SIGNALS
**Class:** ASFXA2VWAP
**Weight:** 20

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 8

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 10 signals
- **Found in test:** 8 signals
- **Coverage:** 80.0%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] BEARISH:** 8,469 (49.3%)
- **[✓] BELOW_VWAP:** 8,468 (49.3%)
- **[✓] BULLISH:** 8,038 (46.8%)
- **[✓] ABOVE_VWAP:** 8,037 (46.8%)
- **[✓] AT_VWAP:** 674 (3.9%)
- **[✓] NEUTRAL:** 674 (3.9%)
- **[✓] VWAP_CROSS_UP:** 1 (0.0%)
- **[✓] VWAP_CROSS_DOWN:** 1 (0.0%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### asia_session_50_percent

**Category:** PRICE_LEVELS
**Class:** AsiaSession50Percent
**Weight:** 20

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 6

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 8 signals
- **Found in test:** 6 signals
- **Coverage:** 75.0%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NEUTRAL:** 14,708 (85.6%)
- **[✓] ABOVE_ASIA_50:** 6,285 (36.6%)
- **[✓] BELOW_ASIA_50:** 5,746 (33.4%)
- **[✓] AT_ASIA_50:** 5,150 (30.0%)
- **[✓] BULLISH:** 1,270 (7.4%)
- **[✓] BEARISH:** 1,203 (7.0%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### atr

**Category:** VOLATILITY
**Class:** ATR
**Weight:** 10

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 11

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 13 signals
- **Found in test:** 11 signals
- **Coverage:** 84.6%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NEUTRAL:** 10,278 (59.8%)
- **[✓] NORMAL:** 5,609 (32.6%)
- **[✓] BEARISH:** 3,834 (22.3%)
- **[✓] HIGH:** 3,363 (19.6%)
- **[✓] VERY_LOW:** 3,153 (18.4%)
- **[✓] BULLISH:** 3,069 (17.9%)
- **[✓] EXTREME_LOW:** 2,209 (12.9%)
- **[✓] EXTREME_HIGH:** 1,280 (7.5%)
- **[✓] CALM:** 1,200 (7.0%)
- **[✓] VERY_HIGH:** 337 (2.0%)
- **[✓] EXTREME:** 30 (0.2%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### balanced_price_range

**Category:** SMC_ICT
**Class:** BalancedPriceRange
**Weight:** 20

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 6

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 8 signals
- **Found in test:** 6 signals
- **Coverage:** 75.0%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NOT_IN_RANGE:** 15,304 (89.1%)
- **[✓] NEUTRAL:** 15,304 (89.1%)
- **[✓] IN_RANGE_HIGH:** 1,007 (5.9%)
- **[✓] BEARISH:** 1,007 (5.9%)
- **[✓] IN_RANGE_LOW:** 870 (5.1%)
- **[✓] BULLISH:** 870 (5.1%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### bollinger_bands

**Category:** VOLATILITY
**Class:** BollingerBands
**Weight:** 10

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 17

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 19 signals
- **Found in test:** 17 signals
- **Coverage:** 89.5%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - ❌ ERROR MISSING
- **INSUFFICIENT_DATA** - ❌ ERROR MISSING

#### 📈 Signal Distribution

- **[✓] BULLISH:** 9,885 (57.5%)
- **[✓] BEARISH:** 7,296 (42.5%)
- **[✓] MEDIUM_LOW:** 3,027 (17.6%)
- **[✓] LOWER_BAND_WALK:** 2,985 (17.4%)
- **[✓] UPPER_BAND_WALK:** 2,931 (17.1%)
- **[✓] MEDIUM_HIGH:** 2,344 (13.6%)
- **[✓] UPPER_HALF:** 1,260 (7.3%)
- **[✓] LOWER_HALF:** 1,134 (6.6%)
- **[✓] NEAR_LOWER:** 1,128 (6.6%)
- **[✓] BELOW_LOWER:** 509 (3.0%)
- **[✓] BULLISH_REVERSAL:** 450 (2.6%)
- **[✓] BEARISH_REVERSAL:** 428 (2.5%)
- **[✓] NEAR_UPPER:** 416 (2.4%)
- **[✓] SQUEEZE_BREAKOUT_BULL:** 186 (1.1%)
- **[✓] SQUEEZE_BREAKOUT_BEAR:** 172 (1.0%)
- **[✓] NEUTRAL:** 123 (0.7%)
- **[✓] ABOVE_UPPER:** 88 (0.5%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### break_of_structure

**Category:** SMC_ICT
**Class:** BreakOfStructure
**Weight:** 20

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 5

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 7 signals
- **Found in test:** 5 signals
- **Coverage:** 71.4%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] BULLISH_BOS:** 7,907 (46.0%)
- **[✓] BULLISH:** 7,907 (46.0%)
- **[✓] BEARISH_BOS:** 7,712 (44.9%)
- **[✓] BEARISH:** 7,712 (44.9%)
- **[✓] NEUTRAL:** 3,124 (18.2%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### breaker_block

**Category:** PRICE_ACTION
**Class:** BreakerBlock
**Weight:** 25

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 6

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 8 signals
- **Found in test:** 6 signals
- **Coverage:** 75.0%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] BULLISH_BREAKER:** 5,895 (34.3%)
- **[✓] BULLISH:** 5,895 (34.3%)
- **[✓] BEARISH_BREAKER:** 5,674 (33.0%)
- **[✓] BEARISH:** 5,674 (33.0%)
- **[✓] NO_BREAKER:** 5,612 (32.7%)
- **[✓] NEUTRAL:** 5,612 (32.7%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### candle_2_close

**Category:** PATTERNS
**Class:** Candle2Close
**Weight:** 30

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 5

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 7 signals
- **Found in test:** 5 signals
- **Coverage:** 71.4%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NEUTRAL:** 33,714 (196.2%)
- **[✓] BULLISH_C2_CLOSE:** 167 (1.0%)
- **[✓] BULLISH:** 167 (1.0%)
- **[✓] BEARISH_C2_CLOSE:** 157 (0.9%)
- **[✓] BEARISH:** 157 (0.9%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### change_of_character

**Category:** SMC_ICT
**Class:** ChangeOfCharacter
**Weight:** 20

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 5

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 7 signals
- **Found in test:** 5 signals
- **Coverage:** 71.4%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NEUTRAL:** 33,012 (192.1%)
- **[✓] BULLISH_CHOCH:** 360 (2.1%)
- **[✓] BULLISH:** 360 (2.1%)
- **[✓] BEARISH_CHOCH:** 315 (1.8%)
- **[✓] BEARISH:** 315 (1.8%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### cup_and_handle

**Category:** PATTERNS
**Class:** CupAndHandlePattern
**Weight:** 30

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 6

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 9 signals
- **Found in test:** 6 signals
- **Coverage:** 66.7%

#### ⚠️ Missing Signals (not found in test)

- **BEARISH** - Hidden from UI (points: 0)
- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NO_PATTERN:** 16,321 (95.0%)
- **[✓] NEUTRAL:** 16,321 (95.0%)
- **[✓] BULLISH:** 860 (5.0%)
- **[✓] CUP_FORMING:** 518 (3.0%)
- **[✓] PATTERN_FORMING:** 335 (1.9%)
- **[✓] BREAKOUT_CONFIRMED:** 7 (0.0%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### descending_triangle

**Category:** PATTERNS
**Class:** DescendingTrianglePattern
**Weight:** 30

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 5

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 8 signals
- **Found in test:** 5 signals
- **Coverage:** 62.5%

#### ⚠️ Missing Signals (not found in test)

- **BULLISH** - Hidden from UI (points: 0)
- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NO_PATTERN:** 16,310 (94.9%)
- **[✓] NEUTRAL:** 16,310 (94.9%)
- **[✓] BEARISH:** 871 (5.1%)
- **[✓] PATTERN_FORMING:** 653 (3.8%)
- **[✓] BEARISH_BREAKDOWN:** 218 (1.3%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### displacement

**Category:** SMC_ICT
**Class:** Displacement
**Weight:** 20

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 5

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 7 signals
- **Found in test:** 5 signals
- **Coverage:** 71.4%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NEUTRAL:** 32,246 (187.7%)
- **[✓] BEARISH_DISPLACEMENT:** 539 (3.1%)
- **[✓] BEARISH:** 539 (3.1%)
- **[✓] BULLISH_DISPLACEMENT:** 519 (3.0%)
- **[✓] BULLISH:** 519 (3.0%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### double_bottom

**Category:** PATTERNS
**Class:** DoubleBottomPattern
**Weight:** 30

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 5

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 8 signals
- **Found in test:** 5 signals
- **Coverage:** 62.5%

#### ⚠️ Missing Signals (not found in test)

- **BEARISH** - Hidden from UI (points: 0)
- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NO_PATTERN:** 15,951 (92.8%)
- **[✓] NEUTRAL:** 15,951 (92.8%)
- **[✓] BULLISH:** 1,230 (7.2%)
- **[✓] PATTERN_FORMING:** 989 (5.8%)
- **[✓] BULLISH_BREAKOUT:** 241 (1.4%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### double_top

**Category:** PATTERNS
**Class:** DoubleTopPattern
**Weight:** 30

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 5

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 8 signals
- **Found in test:** 5 signals
- **Coverage:** 62.5%

#### ⚠️ Missing Signals (not found in test)

- **BULLISH** - Hidden from UI (points: 0)
- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NO_PATTERN:** 15,418 (89.7%)
- **[✓] NEUTRAL:** 15,418 (89.7%)
- **[✓] BEARISH:** 1,763 (10.3%)
- **[✓] PATTERN_FORMING:** 1,119 (6.5%)
- **[✓] BEARISH_BREAKDOWN:** 644 (3.7%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### elliott_wave_count

**Category:** ELLIOTT_WAVE
**Class:** ElliottWaveCount
**Weight:** 22

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 15

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 18 signals
- **Found in test:** 15 signals
- **Coverage:** 83.3%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_PIVOTS** - Hidden from UI (points: 0)
- **NO_PATTERN** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] BULLISH:** 8,152 (47.4%)
- **[✓] BEARISH:** 6,760 (39.3%)
- **[✓] WAVE_1_BULLISH:** 5,377 (31.3%)
- **[✓] WAVE_1_BEARISH:** 3,721 (21.7%)
- **[✓] WAVE_3_BEARISH:** 2,719 (15.8%)
- **[✓] WAVE_3_BULLISH:** 2,326 (13.5%)
- **[✓] NEUTRAL:** 2,269 (13.2%)
- **[✓] INSUFFICIENT_DATA:** 1,869 (10.9%)
- **[✓] WAVE_UNCERTAIN:** 400 (2.3%)
- **[✓] WAVE_4_BULLISH:** 304 (1.8%)
- **[✓] WAVE_2_BEARISH:** 240 (1.4%)
- **[✓] WAVE_2_BULLISH:** 112 (0.7%)
- **[✓] WAVE_4_BEARISH:** 64 (0.4%)
- **[✓] WAVE_5_BULLISH:** 33 (0.2%)
- **[✓] WAVE_5_BEARISH:** 16 (0.1%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### elliott_wave_oscillator

**Category:** ELLIOTT_WAVE
**Class:** ElliottWaveOscillator
**Weight:** 22

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 10

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 12 signals
- **Found in test:** 10 signals
- **Coverage:** 83.3%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] BULLISH:** 8,619 (50.2%)
- **[✓] BEARISH:** 8,549 (49.8%)
- **[✓] BULLISH_MOMENTUM_INCREASING:** 3,578 (20.8%)
- **[✓] BEARISH_MOMENTUM_INCREASING:** 3,483 (20.3%)
- **[✓] BULLISH_MOMENTUM_WEAKENING:** 3,188 (18.6%)
- **[✓] BEARISH_MOMENTUM_WEAKENING:** 3,017 (17.6%)
- **[✓] BEARISH_DIVERGENCE:** 2,049 (11.9%)
- **[✓] BULLISH_DIVERGENCE:** 1,853 (10.8%)
- **[✓] NEUTRAL_MOMENTUM:** 13 (0.1%)
- **[✓] NEUTRAL:** 13 (0.1%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### ema_200_trend

**Category:** MOVING_AVERAGES
**Class:** EMA200Trend
**Weight:** 12

#### 📊 Signal Statistics

- **Total results:** 17,042
- **Errors:** 139 (0.8%)
- **Unique signals found:** 8

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 10 signals
- **Found in test:** 8 signals
- **Coverage:** 80.0%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NEUTRAL:** 16,468 (96.6%)
- **[✓] BELOW_200EMA:** 5,775 (33.9%)
- **[✓] ABOVE_200EMA:** 5,473 (32.1%)
- **[✓] AT_200EMA:** 5,220 (30.6%)
- **[✓] BULLISH_CROSS:** 294 (1.7%)
- **[✓] BULLISH:** 294 (1.7%)
- **[✓] BEARISH_CROSS:** 280 (1.6%)
- **[✓] BEARISH:** 280 (1.6%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 94.68
- **Candles per signal:** 1.0

### ema_20_50_cross

**Category:** MOVING_AVERAGES
**Class:** EMA2050Cross
**Weight:** 12

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 5

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 7 signals
- **Found in test:** 5 signals
- **Coverage:** 71.4%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NEUTRAL:** 32,722 (190.5%)
- **[✓] DEATH_CROSS:** 411 (2.4%)
- **[✓] BEARISH:** 411 (2.4%)
- **[✓] GOLDEN_CROSS:** 409 (2.4%)
- **[✓] BULLISH:** 409 (2.4%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### ema_20_50_trend

**Category:** MOVING_AVERAGES
**Class:** EMA2050Trend
**Weight:** 12

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 6

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 9 signals
- **Found in test:** 6 signals
- **Coverage:** 66.7%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)
- **NEUTRAL** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] BULLISH:** 8,759 (51.0%)
- **[✓] BEARISH:** 8,422 (49.0%)
- **[✓] STRONG_UPTREND:** 5,909 (34.4%)
- **[✓] STRONG_DOWNTREND:** 5,549 (32.3%)
- **[✓] EARLY_DOWNTREND:** 2,869 (16.7%)
- **[✓] EARLY_UPTREND:** 2,854 (16.6%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### ema_255_vector

**Category:** MOVING_AVERAGES
**Class:** EMA255VectorBreak
**Weight:** 12

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 8

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 9 signals
- **Found in test:** 8 signals
- **Coverage:** 88.9%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NEUTRAL:** 33,537 (195.2%)
- **[✓] BEARISH:** 181 (1.1%)
- **[✓] BULLISH:** 162 (0.9%)
- **[✓] INSUFFICIENT_DATA:** 139 (0.8%)
- **[✓] BEARISH_CLIMAX:** 122 (0.7%)
- **[✓] BULLISH_CLIMAX:** 101 (0.6%)
- **[✓] BULLISH_PSEUDO:** 61 (0.4%)
- **[✓] BEARISH_PSEUDO:** 59 (0.3%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### ema_50_vector

**Category:** MOVING_AVERAGES
**Class:** EMA50Vector
**Weight:** 12

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 7

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 9 signals
- **Found in test:** 7 signals
- **Coverage:** 77.8%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NEUTRAL:** 33,698 (196.1%)
- **[✓] BEARISH:** 181 (1.1%)
- **[✓] BEARISH_CLIMAX:** 176 (1.0%)
- **[✓] BULLISH:** 151 (0.9%)
- **[✓] BULLISH_CLIMAX:** 146 (0.8%)
- **[✓] BULLISH_PSEUDO:** 5 (0.0%)
- **[✓] BEARISH_PSEUDO:** 5 (0.0%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### ema_55_vector

**Category:** MOVING_AVERAGES
**Class:** EMA55VectorBreak
**Weight:** 12

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 7

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 9 signals
- **Found in test:** 7 signals
- **Coverage:** 77.8%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NEUTRAL:** 33,630 (195.7%)
- **[✓] BEARISH:** 204 (1.2%)
- **[✓] BEARISH_CLIMAX:** 200 (1.2%)
- **[✓] BULLISH:** 162 (0.9%)
- **[✓] BULLISH_CLIMAX:** 158 (0.9%)
- **[✓] BULLISH_PSEUDO:** 4 (0.0%)
- **[✓] BEARISH_PSEUDO:** 4 (0.0%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### ema_800_vector

**Category:** MOVING_AVERAGES
**Class:** EMA800VectorBreak
**Weight:** 12

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 8

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 9 signals
- **Found in test:** 8 signals
- **Coverage:** 88.9%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NEUTRAL:** 33,537 (195.2%)
- **[✓] INSUFFICIENT_DATA:** 609 (3.5%)
- **[✓] BEARISH:** 63 (0.4%)
- **[✓] BULLISH:** 45 (0.3%)
- **[✓] BEARISH_CLIMAX:** 37 (0.2%)
- **[✓] BULLISH_CLIMAX:** 35 (0.2%)
- **[✓] BEARISH_PSEUDO:** 26 (0.2%)
- **[✓] BULLISH_PSEUDO:** 10 (0.1%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### ema_crossover

**Category:** INSTITUTIONAL
**Class:** EMACrossover
**Weight:** 15

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 8

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 9 signals
- **Found in test:** 8 signals
- **Coverage:** 88.9%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] BEARISH:** 8,659 (50.4%)
- **[✓] BEARISH_ALIGNMENT:** 8,609 (50.1%)
- **[✓] BULLISH:** 8,423 (49.0%)
- **[✓] BULLISH_ALIGNMENT:** 8,373 (48.7%)
- **[✓] INSUFFICIENT_DATA:** 99 (0.6%)
- **[✓] NEUTRAL:** 99 (0.6%)
- **[✓] GOLDEN_CROSS:** 50 (0.3%)
- **[✓] DEATH_CROSS:** 50 (0.3%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### fair_value_gap

**Category:** PRICE_ACTION
**Class:** FairValueGap
**Weight:** 25

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 6

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 8 signals
- **Found in test:** 6 signals
- **Coverage:** 75.0%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NO_FVG:** 16,929 (98.5%)
- **[✓] NEUTRAL:** 16,929 (98.5%)
- **[✓] BEARISH_FVG:** 136 (0.8%)
- **[✓] BEARISH:** 136 (0.8%)
- **[✓] BULLISH_FVG:** 116 (0.7%)
- **[✓] BULLISH:** 116 (0.7%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### falling_wedge

**Category:** PATTERNS
**Class:** FallingWedgePattern
**Weight:** 30

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 5

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 8 signals
- **Found in test:** 5 signals
- **Coverage:** 62.5%

#### ⚠️ Missing Signals (not found in test)

- **BEARISH** - Hidden from UI (points: 0)
- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NO_PATTERN:** 15,931 (92.7%)
- **[✓] NEUTRAL:** 15,931 (92.7%)
- **[✓] BULLISH:** 1,250 (7.3%)
- **[✓] PATTERN_FORMING:** 1,107 (6.4%)
- **[✓] BULLISH_BREAKOUT:** 143 (0.8%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### fibonacci_retracements

**Category:** FIBONACCI
**Class:** FibonacciRetracements
**Weight:** 18

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 9

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 11 signals
- **Found in test:** 9 signals
- **Coverage:** 81.8%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] BETWEEN_LEVELS:** 9,954 (57.9%)
- **[✓] NEUTRAL:** 9,954 (57.9%)
- **[✓] BULLISH:** 3,759 (21.9%)
- **[✓] BEARISH:** 3,468 (20.2%)
- **[✓] AT_FIB_23:** 2,425 (14.1%)
- **[✓] AT_FIB_38:** 1,675 (9.7%)
- **[✓] AT_FIB_50:** 1,441 (8.4%)
- **[✓] AT_FIB_61:** 994 (5.8%)
- **[✓] AT_FIB_78:** 692 (4.0%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### fifty_pct_hod_lod

**Category:** PRICE_LEVELS
**Class:** FiftyPctHODLOD
**Weight:** 18

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 7

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 8 signals
- **Found in test:** 7 signals
- **Coverage:** 87.5%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NEUTRAL:** 8,172 (47.6%)
- **[✓] BULLISH:** 6,377 (37.1%)
- **[✓] ABOVE_EQUILIBRIUM:** 6,061 (35.3%)
- **[✓] BEARISH:** 5,818 (33.9%)
- **[✓] BELOW_EQUILIBRIUM:** 5,545 (32.3%)
- **[✓] AT_EQUILIBRIUM:** 1,800 (10.5%)
- **[✓] REJECTION_AT_EQ:** 589 (3.4%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### fifty_pct_intra_hod_lod

**Category:** PRICE_LEVELS
**Class:** FiftyPctIntraHODLOD
**Weight:** 18

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 7

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 8 signals
- **Found in test:** 7 signals
- **Coverage:** 87.5%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NEUTRAL:** 14,617 (85.1%)
- **[✓] AT_INTRA_EQ:** 4,287 (25.0%)
- **[✓] BULLISH:** 3,869 (22.5%)
- **[✓] BEARISH:** 3,860 (22.5%)
- **[✓] BELOW_INTRA_EQ:** 3,223 (18.8%)
- **[✓] ABOVE_INTRA_EQ:** 3,199 (18.6%)
- **[✓] REJECTION_AT_INTRA_EQ:** 1,307 (7.6%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### flag_pattern

**Category:** PATTERNS
**Class:** FlagPattern
**Weight:** 30

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 7

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 9 signals
- **Found in test:** 7 signals
- **Coverage:** 77.8%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NO_PATTERN:** 16,034 (93.3%)
- **[✓] NEUTRAL:** 16,034 (93.3%)
- **[✓] PATTERN_FORMING:** 662 (3.9%)
- **[✓] BEARISH:** 644 (3.7%)
- **[✓] BULLISH:** 503 (2.9%)
- **[✓] BEARISH_BREAKOUT:** 282 (1.6%)
- **[✓] BULLISH_BREAKOUT:** 203 (1.2%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### head_and_shoulders

**Category:** PATTERNS
**Class:** HeadAndShouldersPattern
**Weight:** 30

#### 📊 Signal Statistics

- **Total results:** 6,602
- **Errors:** 10579 (61.6%)
- **Unique signals found:** 5

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 8 signals
- **Found in test:** 5 signals
- **Coverage:** 62.5%

#### ⚠️ Missing Signals (not found in test)

- **BULLISH** - ❌ ERROR MISSING
- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NO_PATTERN:** 4,268 (64.6%)
- **[✓] NEUTRAL:** 4,268 (64.6%)
- **[✓] BEARISH:** 2,334 (35.4%)
- **[✓] PATTERN_FORMING:** 1,946 (29.5%)
- **[✓] PATTERN_CONFIRMED:** 388 (5.9%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 36.68
- **Candles per signal:** 2.6

### hod

**Category:** PRICE_LEVELS
**Class:** HOD
**Weight:** 20

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 7

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 8 signals
- **Found in test:** 7 signals
- **Coverage:** 87.5%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] BELOW_HOD:** 13,467 (78.4%)
- **[✓] NEUTRAL:** 8,737 (50.9%)
- **[✓] BEARISH:** 6,439 (37.5%)
- **[✓] ABOVE_HOD:** 2,145 (12.5%)
- **[✓] BULLISH:** 2,145 (12.5%)
- **[✓] AT_HOD:** 1,381 (8.0%)
- **[✓] HOD_REJECTION:** 48 (0.3%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### how

**Category:** PRICE_LEVELS
**Class:** HOW
**Weight:** 20

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 6

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 8 signals
- **Found in test:** 6 signals
- **Coverage:** 75.0%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] BELOW_HOW:** 16,963 (98.7%)
- **[✓] NEUTRAL:** 12,629 (73.5%)
- **[✓] BEARISH:** 4,426 (25.8%)
- **[✓] BREAKOUT_CONFIRMED:** 128 (0.7%)
- **[✓] BULLISH:** 128 (0.7%)
- **[✓] BREAKING_OUT:** 88 (0.5%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### ichimoku_cloud

**Category:** TREND
**Class:** IchimokuCloud
**Weight:** 16

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 6

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 8 signals
- **Found in test:** 6 signals
- **Coverage:** 75.0%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] BELOW_CLOUD:** 6,639 (38.6%)
- **[✓] BEARISH:** 6,639 (38.6%)
- **[✓] ABOVE_CLOUD:** 6,452 (37.6%)
- **[✓] BULLISH:** 6,452 (37.6%)
- **[✓] IN_CLOUD:** 4,090 (23.8%)
- **[✓] NEUTRAL:** 4,090 (23.8%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### ict_silver_bullet

**Category:** SIGNALS
**Class:** ICTSilverBullet
**Weight:** 20

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 8

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 9 signals
- **Found in test:** 8 signals
- **Coverage:** 88.9%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NEUTRAL:** 10,464 (60.9%)
- **[✗] UNKNOWN:** 10,464 (60.9%)
- **[✓] BULLISH:** 3,420 (19.9%)
- **[✓] BEARISH:** 3,297 (19.2%)
- **[✓] BULLISH_FVG_IN_ZONE:** 1,945 (11.3%)
- **[✓] BEARISH_FVG_IN_ZONE:** 1,772 (10.3%)
- **[✓] BEARISH_FVG_RETEST:** 1,525 (8.9%)
- **[✓] BULLISH_FVG_RETEST:** 1,475 (8.6%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### ihod

**Category:** PRICE_LEVELS
**Class:** IHOD
**Weight:** 20

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 6

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 8 signals
- **Found in test:** 6 signals
- **Coverage:** 75.0%

#### ⚠️ Missing Signals (not found in test)

- **AT_IHOD** - ❌ ERROR MISSING
- **ERROR** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NEUTRAL:** 19,576 (113.9%)
- **[✓] BELOW_IHOD:** 9,652 (56.2%)
- **[✓] BULLISH_BREAK:** 1,459 (8.5%)
- **[✓] BULLISH:** 1,459 (8.5%)
- **[✓] BEARISH_REJECTION:** 1,108 (6.4%)
- **[✓] BEARISH:** 1,108 (6.4%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### ilod

**Category:** PRICE_LEVELS
**Class:** ILOD
**Weight:** 20

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 6

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 8 signals
- **Found in test:** 6 signals
- **Coverage:** 75.0%

#### ⚠️ Missing Signals (not found in test)

- **AT_ILOD** - ❌ ERROR MISSING
- **ERROR** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NEUTRAL:** 19,014 (110.7%)
- **[✓] ABOVE_ILOD:** 10,572 (61.5%)
- **[✓] BEARISH_BREAK:** 1,518 (8.8%)
- **[✓] BEARISH:** 1,518 (8.8%)
- **[✓] BULLISH_BOUNCE:** 870 (5.1%)
- **[✓] BULLISH:** 870 (5.1%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### inducement

**Category:** SMC_ICT
**Class:** Inducement
**Weight:** 20

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 5

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 7 signals
- **Found in test:** 5 signals
- **Coverage:** 71.4%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NEUTRAL:** 31,964 (186.0%)
- **[✓] BULLISH_INDUCEMENT:** 646 (3.8%)
- **[✓] BULLISH:** 646 (3.8%)
- **[✓] BEARISH_INDUCEMENT:** 553 (3.2%)
- **[✓] BEARISH:** 553 (3.2%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### initial_balance_breakout

**Category:** PATTERNS
**Class:** InitialBalanceBreakout
**Weight:** 30

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 11

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 13 signals
- **Found in test:** 11 signals
- **Coverage:** 84.6%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)
- **NO_IB** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✗] UNKNOWN:** 14,018 (81.6%)
- **[✓] ABOVE_IB:** 7,352 (42.8%)
- **[✓] BELOW_IB:** 6,456 (37.6%)
- **[✓] INSIDE_IB:** 1,586 (9.2%)
- **[✓] NEUTRAL:** 1,586 (9.2%)
- **[✓] BEARISH:** 1,094 (6.4%)
- **[✓] LOWER_IB:** 628 (3.7%)
- **[✓] BULLISH_BREAKOUT:** 483 (2.8%)
- **[✓] BULLISH:** 483 (2.8%)
- **[✓] BEARISH_BREAKOUT:** 466 (2.7%)
- **[✓] IB_FORMED:** 210 (1.2%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### internal_pivot_pattern

**Category:** PATTERNS
**Class:** InternalPivotPattern
**Weight:** 30

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 7

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 9 signals
- **Found in test:** 7 signals
- **Coverage:** 77.8%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NEUTRAL:** 33,264 (193.6%)
- **[✓] BEARISH:** 285 (1.7%)
- **[✓] BEARISH_PIVOT_HIGH:** 279 (1.6%)
- **[✓] BULLISH:** 264 (1.5%)
- **[✓] BULLISH_PIVOT_LOW:** 260 (1.5%)
- **[✓] PIVOT_HIGH:** 6 (0.0%)
- **[✓] PIVOT_LOW:** 4 (0.0%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### inverse_head_and_shoulders

**Category:** PATTERNS
**Class:** InverseHeadAndShouldersPattern
**Weight:** 30

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 5

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 8 signals
- **Found in test:** 5 signals
- **Coverage:** 62.5%

#### ⚠️ Missing Signals (not found in test)

- **BEARISH** - ❌ ERROR MISSING
- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NO_PATTERN:** 16,176 (94.2%)
- **[✓] NEUTRAL:** 16,176 (94.2%)
- **[✓] BULLISH:** 1,005 (5.8%)
- **[✓] PATTERN_FORMING:** 764 (4.4%)
- **[✓] PATTERN_CONFIRMED:** 241 (1.4%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### kill_zones

**Category:** SESSIONS
**Class:** KillZones
**Weight:** 16

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 10

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 12 signals
- **Found in test:** 10 signals
- **Coverage:** 83.3%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **WAIT** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NO_KZ:** 7,160 (41.7%)
- **[✓] BEARISH:** 7,160 (41.7%)
- **[✓] NEUTRAL:** 5,728 (33.3%)
- **[✓] BULLISH:** 4,293 (25.0%)
- **[✓] NY_PM_KZ:** 2,148 (12.5%)
- **[✓] ASIAN_KZ:** 2,148 (12.5%)
- **[✓] NY_AM_KZ:** 1,966 (11.4%)
- **[✓] LONDON_KZ:** 1,961 (11.4%)
- **[✓] LONDON_OPEN_KZ:** 1,432 (8.3%)
- **[✓] PRIME_TIME:** 366 (2.1%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### liquidity

**Category:** MARKET_STRUCTURE
**Class:** Liquidity
**Weight:** 15

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 10

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 12 signals
- **Found in test:** 10 signals
- **Coverage:** 83.3%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NEUTRAL:** 6,687 (38.9%)
- **[✓] BULLISH:** 5,523 (32.1%)
- **[✓] BEARISH:** 5,478 (31.9%)
- **[✓] NEAR_BUYSIDE:** 4,503 (26.2%)
- **[✓] VOID_DETECTED:** 3,352 (19.5%)
- **[✓] BUYSIDE_ZONE_TOUCH:** 2,210 (12.9%)
- **[✓] BUYSIDE_BREACH:** 2,026 (11.8%)
- **[✓] SELLSIDE_BREACH:** 1,848 (10.8%)
- **[✓] SELLSIDE_ZONE_TOUCH:** 1,565 (9.1%)
- **[✓] NEAR_SELLSIDE:** 1,170 (6.8%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### liquidity_sweep

**Category:** PRICE_ACTION
**Class:** LiquiditySweep
**Weight:** 25

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 6

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 8 signals
- **Found in test:** 6 signals
- **Coverage:** 75.0%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NO_SWEEP:** 8,278 (48.2%)
- **[✓] NEUTRAL:** 8,278 (48.2%)
- **[✓] BULLISH_SWEEP:** 4,489 (26.1%)
- **[✓] BULLISH:** 4,489 (26.1%)
- **[✓] BEARISH_SWEEP:** 4,414 (25.7%)
- **[✓] BEARISH:** 4,414 (25.7%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### lod

**Category:** PRICE_LEVELS
**Class:** LOD
**Weight:** 20

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 7

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 8 signals
- **Found in test:** 7 signals
- **Coverage:** 87.5%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] ABOVE_LOD:** 14,267 (83.0%)
- **[✓] NEUTRAL:** 9,567 (55.7%)
- **[✓] BULLISH:** 6,408 (37.3%)
- **[✓] BELOW_LOD:** 1,653 (9.6%)
- **[✓] BEARISH:** 1,653 (9.6%)
- **[✓] AT_LOD:** 769 (4.5%)
- **[✓] LOD_BOUNCE:** 45 (0.3%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### low

**Category:** PRICE_LEVELS
**Class:** LOW
**Weight:** 20

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 7

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 11 signals
- **Found in test:** 7 signals
- **Coverage:** 63.6%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)
- **NO_LOW** - Hidden from UI (points: 0)
- **NO_LOW_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NEUTRAL:** 12,889 (75.0%)
- **[✓] ABOVE_LOW:** 12,795 (74.5%)
- **[✓] AT_LOW:** 4,148 (24.1%)
- **[✓] BULLISH:** 4,148 (24.1%)
- **[✓] BREAKDOWN_CONFIRMED:** 144 (0.8%)
- **[✓] BEARISH:** 144 (0.8%)
- **[✓] BREAKING_DOWN:** 94 (0.5%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### macd_price_forecasting

**Category:** SIGNALS
**Class:** MACDPriceForecasting
**Weight:** 20

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 6

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 7 signals
- **Found in test:** 6 signals
- **Coverage:** 85.7%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NEUTRAL:** 15,841 (92.2%)
- **[✗] UNKNOWN:** 15,841 (92.2%)
- **[✓] BEARISH_FORECAST:** 670 (3.9%)
- **[✓] BULLISH_FORECAST:** 670 (3.9%)
- **[✓] BEARISH:** 670 (3.9%)
- **[✓] BULLISH:** 670 (3.9%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### macd_signal

**Category:** OSCILLATORS
**Class:** MACDSignal
**Weight:** 25

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 9

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 11 signals
- **Found in test:** 9 signals
- **Coverage:** 81.8%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] BULLISH:** 8,948 (52.1%)
- **[✓] BULLISH_DIVERGENCE:** 8,766 (51.0%)
- **[✓] BEARISH:** 5,677 (33.0%)
- **[✓] BEARISH_DIVERGENCE:** 5,503 (32.0%)
- **[✓] NEUTRAL:** 5,112 (29.8%)
- **[✓] BULLISH_CROSS:** 142 (0.8%)
- **[✓] BEARISH_CROSS:** 139 (0.8%)
- **[✓] BULLISH_ZERO_CROSS:** 40 (0.2%)
- **[✓] BEARISH_ZERO_CROSS:** 35 (0.2%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### market_depth

**Category:** INSTITUTIONAL
**Class:** MarketDepth
**Weight:** 15

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 6

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 8 signals
- **Found in test:** 6 signals
- **Coverage:** 75.0%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NORMAL_LIQUIDITY:** 9,438 (54.9%)
- **[✓] NEUTRAL:** 9,438 (54.9%)
- **[✓] HIGH_LIQUIDITY:** 4,821 (28.1%)
- **[✓] BULLISH:** 4,821 (28.1%)
- **[✓] LOW_LIQUIDITY:** 2,922 (17.0%)
- **[✓] BEARISH:** 2,922 (17.0%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### market_structure_shift

**Category:** SMC_ICT
**Class:** MarketStructureShift
**Weight:** 20

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 6

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 9 signals
- **Found in test:** 6 signals
- **Coverage:** 66.7%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)
- **NEUTRAL** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] BULLISH:** 8,609 (50.1%)
- **[✓] BEARISH:** 8,572 (49.9%)
- **[✓] BEARISH_MSS:** 6,304 (36.7%)
- **[✓] BULLISH_MSS:** 6,076 (35.4%)
- **[✓] BULLISH_RETEST:** 2,533 (14.7%)
- **[✓] BEARISH_RETEST:** 2,268 (13.2%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### mitigation_block

**Category:** SMC_ICT
**Class:** MitigationBlock
**Weight:** 20

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 5

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 7 signals
- **Found in test:** 5 signals
- **Coverage:** 71.4%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NEUTRAL:** 11,186 (65.1%)
- **[✓] BULLISH_MITIGATION:** 5,926 (34.5%)
- **[✓] BULLISH:** 5,926 (34.5%)
- **[✓] BEARISH_MITIGATION:** 5,662 (33.0%)
- **[✓] BEARISH:** 5,662 (33.0%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### optimal_trade_entry

**Category:** SMC_ICT
**Class:** OptimalTradeEntry
**Weight:** 20

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 5

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 7 signals
- **Found in test:** 5 signals
- **Coverage:** 71.4%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NEUTRAL:** 29,236 (170.2%)
- **[✓] BEARISH_OTE:** 1,448 (8.4%)
- **[✓] BEARISH:** 1,448 (8.4%)
- **[✓] BULLISH_OTE:** 1,115 (6.5%)
- **[✓] BULLISH:** 1,115 (6.5%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### order_block

**Category:** PRICE_ACTION
**Class:** OrderBlock
**Weight:** 25

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 6

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 8 signals
- **Found in test:** 6 signals
- **Coverage:** 75.0%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NO_OB:** 16,474 (95.9%)
- **[✓] NEUTRAL:** 16,474 (95.9%)
- **[✓] BULLISH_OB:** 354 (2.1%)
- **[✓] BULLISH:** 354 (2.1%)
- **[✓] BEARISH_OB:** 353 (2.1%)
- **[✓] BEARISH:** 353 (2.1%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### order_flow_imbalance

**Category:** INSTITUTIONAL
**Class:** OrderFlowImbalance
**Weight:** 15

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 6

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 8 signals
- **Found in test:** 6 signals
- **Coverage:** 75.0%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] BALANCED:** 9,795 (57.0%)
- **[✓] NEUTRAL:** 9,795 (57.0%)
- **[✓] BUY_IMBALANCE:** 3,723 (21.7%)
- **[✓] BULLISH:** 3,723 (21.7%)
- **[✓] SELL_IMBALANCE:** 3,663 (21.3%)
- **[✓] BEARISH:** 3,663 (21.3%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### pennant_pattern

**Category:** PATTERNS
**Class:** PennantPattern
**Weight:** 30

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 8

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 9 signals
- **Found in test:** 8 signals
- **Coverage:** 88.9%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NO_PATTERN:** 16,088 (93.6%)
- **[✓] NEUTRAL:** 16,027 (93.3%)
- **[✓] PATTERN_FORMING:** 1,001 (5.8%)
- **[✓] BEARISH:** 587 (3.4%)
- **[✓] BULLISH:** 506 (2.9%)
- **[✓] BEARISH_BREAKOUT:** 61 (0.4%)
- **[✗] UNKNOWN:** 61 (0.4%)
- **[✓] BULLISH_BREAKOUT:** 31 (0.2%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### power_hour_trends

**Category:** MARKET_STRUCTURE
**Class:** PowerHourTrends
**Weight:** 15

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 16

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 18 signals
- **Found in test:** 16 signals
- **Coverage:** 88.9%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] BEARISH:** 6,975 (40.6%)
- **[✓] BULLISH:** 6,342 (36.9%)
- **[✓] NEUTRAL:** 3,864 (22.5%)
- **[✓] DOWNTREND_EXTREME:** 3,614 (21.0%)
- **[✓] UPTREND_HIGH:** 2,149 (12.5%)
- **[✓] UPTREND_EXTREME:** 2,136 (12.4%)
- **[✓] RANGING_LOW:** 1,542 (9.0%)
- **[✓] DOWNTREND_MODERATE:** 1,515 (8.8%)
- **[✓] UPTREND_MODERATE:** 1,167 (6.8%)
- **[✓] DOWNTREND_HIGH:** 1,157 (6.7%)
- **[✓] UPTREND_LOW:** 890 (5.2%)
- **[✓] RANGING_EXTREME:** 849 (4.9%)
- **[✓] DOWNTREND_LOW:** 689 (4.0%)
- **[✓] RANGING_HIGH:** 667 (3.9%)
- **[✓] RANGING_MODERATE:** 490 (2.9%)
- **[✓] INSUFFICIENT_POWER_HOURS:** 316 (1.8%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### premium_discount_zones

**Category:** MARKET_STRUCTURE
**Class:** PremiumDiscountZones
**Weight:** 14

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 6

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 8 signals
- **Found in test:** 6 signals
- **Coverage:** 75.0%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] PRICE_IN_PREMIUM:** 8,695 (50.6%)
- **[✓] BEARISH:** 8,695 (50.6%)
- **[✓] PRICE_IN_DISCOUNT:** 7,812 (45.5%)
- **[✓] BULLISH:** 7,812 (45.5%)
- **[✓] PRICE_AT_EQUILIBRIUM:** 674 (3.9%)
- **[✓] NEUTRAL:** 674 (3.9%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### range_liquidity

**Category:** MARKET_STRUCTURE
**Class:** RangeLiquidity
**Weight:** 15

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 4

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 7 signals
- **Found in test:** 4 signals
- **Coverage:** 57.1%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)
- **NEUTRAL** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NEAR_BUY_SIDE_LIQUIDITY:** 9,013 (52.5%)
- **[✓] BEARISH:** 9,013 (52.5%)
- **[✓] NEAR_SELL_SIDE_LIQUIDITY:** 8,168 (47.5%)
- **[✓] BULLISH:** 8,168 (47.5%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### rising_wedge

**Category:** PATTERNS
**Class:** RisingWedgePattern
**Weight:** 30

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 5

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 8 signals
- **Found in test:** 5 signals
- **Coverage:** 62.5%

#### ⚠️ Missing Signals (not found in test)

- **BULLISH** - Hidden from UI (points: 0)
- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)
- **NEUTRAL** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NO_PATTERN:** 14,031 (81.7%)
- **[✗] UNKNOWN:** 14,031 (81.7%)
- **[✓] BEARISH:** 3,150 (18.3%)
- **[✓] PATTERN_FORMING:** 3,121 (18.2%)
- **[✓] BEARISH_BREAKDOWN:** 29 (0.2%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### rounding_bottom

**Category:** PATTERNS
**Class:** RoundingBottomPattern
**Weight:** 30

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 5

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 8 signals
- **Found in test:** 5 signals
- **Coverage:** 62.5%

#### ⚠️ Missing Signals (not found in test)

- **BEARISH** - Hidden from UI (points: 0)
- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)
- **NEUTRAL** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NO_PATTERN:** 15,278 (88.9%)
- **[✗] UNKNOWN:** 15,278 (88.9%)
- **[✓] BULLISH:** 1,903 (11.1%)
- **[✓] BREAKOUT_CONFIRMED:** 1,884 (11.0%)
- **[✓] PATTERN_FORMING:** 19 (0.1%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### rsi_divergence

**Category:** OSCILLATORS
**Class:** RSIDivergence
**Weight:** 25

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 5

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 8 signals
- **Found in test:** 5 signals
- **Coverage:** 62.5%

#### ⚠️ Missing Signals (not found in test)

- **BEARISH_DIVERGENCE** - ❌ ERROR MISSING
- **BULLISH_DIVERGENCE** - ❌ ERROR MISSING
- **ERROR** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NEUTRAL:** 30,402 (177.0%)
- **[✓] OVERSOLD:** 1,029 (6.0%)
- **[✓] BULLISH:** 1,029 (6.0%)
- **[✓] OVERBOUGHT:** 951 (5.5%)
- **[✓] BEARISH:** 951 (5.5%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### session_time

**Category:** SESSIONS
**Class:** SessionTime
**Weight:** 15

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 6

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 12 signals
- **Found in test:** 6 signals
- **Coverage:** 50.0%

#### ⚠️ Missing Signals (not found in test)

- **BEARISH** - Hidden from UI (points: 0)
- **BULLISH** - Hidden from UI (points: 0)
- **ERROR** - Hidden from UI (points: 0)
- **NEUTRAL** - Hidden from UI (points: 0)
- **NO_SIGNAL** - Hidden from UI (points: 0)
- **OFF_SESSION** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] ACTIVE:** 15,033 (87.5%)
- **[✓] ACTIVE_SESSION:** 7,157 (41.7%)
- **[✓] MODERATE_SESSION:** 5,728 (33.3%)
- **[✓] PEAK_HOURS:** 2,148 (12.5%)
- **[✓] QUIET_SESSION:** 2,148 (12.5%)
- **[✓] INACTIVE:** 2,148 (12.5%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### stochastic_rsi

**Category:** OSCILLATORS
**Class:** StochasticRSI
**Weight:** 25

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 8

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 10 signals
- **Found in test:** 8 signals
- **Coverage:** 80.0%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] BEARISH:** 7,656 (44.6%)
- **[✓] BULLISH:** 7,616 (44.3%)
- **[✓] NEUTRAL_HIGH:** 5,576 (32.5%)
- **[✓] NEUTRAL_LOW:** 5,529 (32.2%)
- **[✓] BULLISH_CROSS:** 2,087 (12.1%)
- **[✓] BEARISH_CROSS:** 2,080 (12.1%)
- **[✓] NO_CROSS:** 1,909 (11.1%)
- **[✓] NEUTRAL:** 1,909 (11.1%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### supply_demand_zones

**Category:** SUPPLY_DEMAND
**Class:** SupplyDemandZones
**Weight:** 24

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 6

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 10 signals
- **Found in test:** 6 signals
- **Coverage:** 60.0%

#### ⚠️ Missing Signals (not found in test)

- **BEARISH** - ❌ ERROR MISSING
- **BULLISH** - ❌ ERROR MISSING
- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)
- **NEUTRAL** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✗] UNKNOWN:** 17,181 (100.0%)
- **[✓] NEAR_SUPPLY:** 10,209 (59.4%)
- **[✓] NEAR_DEMAND:** 5,049 (29.4%)
- **[✓] SUPPLY_ZONE:** 1,091 (6.4%)
- **[✓] DEMAND_ZONE:** 821 (4.8%)
- **[✓] NO_ZONE:** 11 (0.1%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### swing_breakout_sequence

**Category:** PATTERNS
**Class:** SwingBreakoutSequence
**Weight:** 30

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 6

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 7 signals
- **Found in test:** 6 signals
- **Coverage:** 85.7%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NEUTRAL:** 16,580 (96.5%)
- **[✗] UNKNOWN:** 16,580 (96.5%)
- **[✓] BEARISH_BREAKOUT_SEQUENCE:** 308 (1.8%)
- **[✓] BEARISH:** 308 (1.8%)
- **[✓] BULLISH_BREAKOUT_SEQUENCE:** 293 (1.7%)
- **[✓] BULLISH:** 293 (1.7%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### swing_failure_pattern

**Category:** SMC_ICT
**Class:** SwingFailurePattern
**Weight:** 20

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 6

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 7 signals
- **Found in test:** 6 signals
- **Coverage:** 85.7%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NEUTRAL:** 14,722 (85.7%)
- **[✗] UNKNOWN:** 14,722 (85.7%)
- **[✓] BULLISH_SFP:** 1,334 (7.8%)
- **[✓] BULLISH:** 1,334 (7.8%)
- **[✓] BEARISH_SFP:** 1,125 (6.5%)
- **[✓] BEARISH:** 1,125 (6.5%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### swing_points

**Category:** MARKET_STRUCTURE
**Class:** SwingPoints
**Weight:** 15

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 8

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 12 signals
- **Found in test:** 8 signals
- **Coverage:** 66.7%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)
- **NEUTRAL** - Hidden from UI (points: 0)
- **NO_SWINGS** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] BEARISH:** 8,866 (51.6%)
- **[✓] BULLISH:** 8,315 (48.4%)
- **[✓] SWING_HIGH_DETECTED:** 4,686 (27.3%)
- **[✓] MAJOR_SWING_LOW_DETECTED:** 4,395 (25.6%)
- **[✓] MAJOR_SWING_HIGH_DETECTED:** 4,164 (24.2%)
- **[✓] SWING_LOW_DETECTED:** 3,907 (22.7%)
- **[✓] MINOR_SWING_HIGH_DETECTED:** 16 (0.1%)
- **[✓] MINOR_SWING_LOW_DETECTED:** 13 (0.1%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### symmetrical_triangle

**Category:** PATTERNS
**Class:** SymmetricalTrianglePattern
**Weight:** 30

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 7

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 9 signals
- **Found in test:** 7 signals
- **Coverage:** 77.8%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NEUTRAL:** 17,129 (99.7%)
- **[✓] NO_PATTERN:** 11,296 (65.7%)
- **[✓] PATTERN_FORMING:** 5,833 (34.0%)
- **[✓] BULLISH_BREAKOUT:** 27 (0.2%)
- **[✓] BULLISH:** 27 (0.2%)
- **[✓] BEARISH_BREAKOUT:** 25 (0.1%)
- **[✓] BEARISH:** 25 (0.1%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### three_bar_reversal

**Category:** PATTERNS
**Class:** ThreeBarReversal
**Weight:** 30

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 5

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 7 signals
- **Found in test:** 5 signals
- **Coverage:** 71.4%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NEUTRAL:** 32,996 (192.0%)
- **[✓] BULLISH_3BAR:** 364 (2.1%)
- **[✓] BULLISH:** 364 (2.1%)
- **[✓] BEARISH_3BAR:** 319 (1.9%)
- **[✓] BEARISH:** 319 (1.9%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### trailing_stop

**Category:** RISK_MANAGEMENT
**Class:** TrailingStop
**Weight:** 8

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 4

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 9 signals
- **Found in test:** 4 signals
- **Coverage:** 44.4%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)
- **NEUTRAL** - Hidden from UI (points: 0)
- **NO_STOP** - Hidden from UI (points: 0)
- **STOP_UPDATED** - ❌ ERROR MISSING

#### 📈 Signal Distribution

- **[✓] BULLISH:** 14,083 (82.0%)
- **[✓] STOP_ACTIVE:** 10,609 (61.7%)
- **[✓] STOP_TRIGGERED:** 6,572 (38.3%)
- **[✓] BEARISH:** 3,098 (18.0%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### triple_bottom

**Category:** PATTERNS
**Class:** TripleBottomPattern
**Weight:** 30

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 5

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 8 signals
- **Found in test:** 5 signals
- **Coverage:** 62.5%

#### ⚠️ Missing Signals (not found in test)

- **BEARISH** - Hidden from UI (points: 0)
- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] BULLISH:** 8,666 (50.4%)
- **[✓] NO_PATTERN:** 8,515 (49.6%)
- **[✓] NEUTRAL:** 8,515 (49.6%)
- **[✓] PATTERN_FORMING:** 7,619 (44.3%)
- **[✓] BULLISH_BREAKOUT:** 1,047 (6.1%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### triple_top

**Category:** PATTERNS
**Class:** TripleTopPattern
**Weight:** 30

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 5

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 8 signals
- **Found in test:** 5 signals
- **Coverage:** 62.5%

#### ⚠️ Missing Signals (not found in test)

- **BULLISH** - Hidden from UI (points: 0)
- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)
- **NEUTRAL** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NO_PATTERN:** 14,817 (86.2%)
- **[✗] UNKNOWN:** 14,817 (86.2%)
- **[✓] BEARISH:** 2,364 (13.8%)
- **[✓] PATTERN_FORMING:** 2,212 (12.9%)
- **[✓] BEARISH_BREAKDOWN:** 152 (0.9%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### us_settlement

**Category:** PRICE_LEVELS
**Class:** USSettlement
**Weight:** 20

#### 📊 Signal Statistics

- **Total results:** 16,908
- **Errors:** 273 (1.6%)
- **Unique signals found:** 6

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 8 signals
- **Found in test:** 6 signals
- **Coverage:** 75.0%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NEUTRAL:** 7,459 (44.1%)
- **[✓] ABOVE_SETTLEMENT:** 7,078 (41.9%)
- **[✓] BELOW_SETTLEMENT:** 6,128 (36.2%)
- **[✓] BULLISH:** 5,164 (30.5%)
- **[✓] BEARISH:** 4,285 (25.3%)
- **[✓] AT_SETTLEMENT:** 3,702 (21.9%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 93.93
- **Candles per signal:** 1.0

### vwap

**Category:** INSTITUTIONAL
**Class:** VWAP
**Weight:** 15

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 6

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 8 signals
- **Found in test:** 6 signals
- **Coverage:** 75.0%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] BELOW_VWAP:** 8,775 (51.1%)
- **[✓] BEARISH:** 8,775 (51.1%)
- **[✓] ABOVE_VWAP:** 8,232 (47.9%)
- **[✓] BULLISH:** 8,232 (47.9%)
- **[✓] AT_VWAP:** 174 (1.0%)
- **[✓] NEUTRAL:** 174 (1.0%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### wave_consolidation

**Category:** MARKET_STRUCTURE
**Class:** WaveConsolidation
**Weight:** 15

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 7

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 9 signals
- **Found in test:** 7 signals
- **Coverage:** 77.8%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NEUTRAL:** 32,168 (187.2%)
- **[✓] BULLISH:** 579 (3.4%)
- **[✓] BEARISH:** 518 (3.0%)
- **[✓] BULLISH_ZONE_BREAK:** 453 (2.6%)
- **[✓] BEARISH_ZONE_BREAK:** 356 (2.1%)
- **[✓] BEARISH_ZONE_REJECTION:** 162 (0.9%)
- **[✓] BULLISH_ZONE_REJECTION:** 126 (0.7%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### wyckoff_accumulation

**Category:** WYCKOFF
**Class:** WyckoffAccumulation
**Weight:** 28

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 9

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 10 signals
- **Found in test:** 9 signals
- **Coverage:** 90.0%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NEUTRAL:** 15,030 (87.5%)
- **[✓] NO_ACCUMULATION:** 10,879 (63.3%)
- **[✓] ACCUMULATION_PHASE_B:** 5,135 (29.9%)
- **[✓] BEARISH:** 1,269 (7.4%)
- **[✓] BULLISH:** 882 (5.1%)
- **[✓] ACCUMULATION_PHASE_A:** 824 (4.8%)
- **[✓] INSUFFICIENT_DATA:** 285 (1.7%)
- **[✓] SOS_BREAKOUT:** 42 (0.2%)
- **[✓] SPRING_DETECTED:** 16 (0.1%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### wyckoff_distribution

**Category:** WYCKOFF
**Class:** WyckoffDistribution
**Weight:** 28

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 8

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 10 signals
- **Found in test:** 8 signals
- **Coverage:** 80.0%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **UTAD_DETECTED** - ❌ ERROR MISSING

#### 📈 Signal Distribution

- **[✓] NEUTRAL:** 15,207 (88.5%)
- **[✓] NO_DISTRIBUTION:** 10,863 (63.2%)
- **[✓] DISTRIBUTION_PHASE_B:** 4,943 (28.8%)
- **[✓] BEARISH:** 1,090 (6.3%)
- **[✓] DISTRIBUTION_PHASE_A:** 1,016 (5.9%)
- **[✓] BULLISH:** 884 (5.1%)
- **[✓] INSUFFICIENT_DATA:** 285 (1.7%)
- **[✓] SOW_BREAKDOWN:** 74 (0.4%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

### wyckoff_reaccumulation

**Category:** WYCKOFF
**Class:** WyckoffReaccumulation
**Weight:** 28

#### 📊 Signal Statistics

- **Total results:** 17,181
- **Errors:** 0 (0.0%)
- **Unique signals found:** 7

#### 🎯 Valid Signals Coverage

- **Expected (from registry):** 9 signals
- **Found in test:** 7 signals
- **Coverage:** 77.8%

#### ⚠️ Missing Signals (not found in test)

- **ERROR** - Hidden from UI (points: 0)
- **INSUFFICIENT_DATA** - Hidden from UI (points: 0)

#### 📈 Signal Distribution

- **[✓] NO_REACCUMULATION:** 15,096 (87.9%)
- **[✓] NEUTRAL:** 15,010 (87.4%)
- **[✓] BULLISH:** 2,085 (12.1%)
- **[✓] REACCUMULATION_DETECTED:** 1,968 (11.5%)
- **[✓] BEARISH:** 86 (0.5%)
- **[✓] BREAKOUT_CONTINUATION:** 60 (0.3%)
- **[✓] SPRING_DETECTED:** 57 (0.3%)

#### 📉 Density Metrics

- **Test period:** 180 days
- **Signals per day:** 95.45
- **Candles per signal:** 1.0

## Test Configuration

- Test Period: 180 days
- Timeframe: 15 minutes
- Method: Expanding window (candle-by-candle)
- Multicore: Enabled

---
*Report generated by BTC_Engine_v3 Building Block Test Suite*
*2026-01-15 19:42:38*