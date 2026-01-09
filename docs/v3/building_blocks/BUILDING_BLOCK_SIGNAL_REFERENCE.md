# BUILDING BLOCK SIGNAL REFERENCE
====================================================================================================

**Generated:** 2026-01-09 17:59:58
**Purpose:** Comprehensive reference of actual signals returned by each building block
**Usage:** Update ConfluenceCalculator.SIGNAL_TIERS to match these EXACT signal names

====================================================================================================


## PATTERNS
----------------------------------------------------------------------------------------------------

### double_top
**Class:** `DoubleTop`  
**Module:** `src.detectors.building_blocks.patterns.double_top`  

**Possible Signals:**
- ⚠️ NO SIGNALS DETECTED (may need specific conditions)

**Test Results:**
- neutral: ❌ ERROR - invalid syntax (double_top.py, line 19)
- bullish: ❌ ERROR - invalid syntax (double_top.py, line 19)
- bearish: ❌ ERROR - invalid syntax (double_top.py, line 19)

### double_bottom
**Class:** `DoubleBottom`  
**Module:** `src.detectors.building_blocks.patterns.double_bottom`  

**Possible Signals:**
- ⚠️ NO SIGNALS DETECTED (may need specific conditions)

**Test Results:**
- neutral: ❌ ERROR - module 'src.detectors.building_blocks.patterns.double_bottom' has no attribute 'DoubleBottom'
- bullish: ❌ ERROR - module 'src.detectors.building_blocks.patterns.double_bottom' has no attribute 'DoubleBottom'
- bearish: ❌ ERROR - module 'src.detectors.building_blocks.patterns.double_bottom' has no attribute 'DoubleBottom'

### triple_top
**Class:** `TripleTop`  
**Module:** `src.detectors.building_blocks.patterns.triple_top`  

**Possible Signals:**
- ⚠️ NO SIGNALS DETECTED (may need specific conditions)

**Test Results:**
- neutral: ❌ ERROR - module 'src.detectors.building_blocks.patterns.triple_top' has no attribute 'TripleTop'
- bullish: ❌ ERROR - module 'src.detectors.building_blocks.patterns.triple_top' has no attribute 'TripleTop'
- bearish: ❌ ERROR - module 'src.detectors.building_blocks.patterns.triple_top' has no attribute 'TripleTop'

### triple_bottom
**Class:** `TripleBottom`  
**Module:** `src.detectors.building_blocks.patterns.triple_bottom`  

**Possible Signals:**
- ⚠️ NO SIGNALS DETECTED (may need specific conditions)

**Test Results:**
- neutral: ❌ ERROR - module 'src.detectors.building_blocks.patterns.triple_bottom' has no attribute 'TripleBottom'
- bullish: ❌ ERROR - module 'src.detectors.building_blocks.patterns.triple_bottom' has no attribute 'TripleBottom'
- bearish: ❌ ERROR - module 'src.detectors.building_blocks.patterns.triple_bottom' has no attribute 'TripleBottom'

### head_and_shoulders
**Class:** `HeadAndShoulders`  
**Module:** `src.detectors.building_blocks.patterns.head_and_shoulders`  

**Possible Signals:**
- ⚠️ NO SIGNALS DETECTED (may need specific conditions)

**Test Results:**
- neutral: ❌ ERROR - module 'src.detectors.building_blocks.patterns.head_and_shoulders' has no attribute 'HeadAndShoulders'
- bullish: ❌ ERROR - module 'src.detectors.building_blocks.patterns.head_and_shoulders' has no attribute 'HeadAndShoulders'
- bearish: ❌ ERROR - module 'src.detectors.building_blocks.patterns.head_and_shoulders' has no attribute 'HeadAndShoulders'

### inverse_head_and_shoulders
**Class:** `InverseHeadAndShoulders`  
**Module:** `src.detectors.building_blocks.patterns.inverse_head_and_shoulders`  

**Possible Signals:**
- ⚠️ NO SIGNALS DETECTED (may need specific conditions)

**Test Results:**
- neutral: ❌ ERROR - module 'src.detectors.building_blocks.patterns.inverse_head_and_shoulders' has no attribute 'InverseHeadAndShoulders'
- bullish: ❌ ERROR - module 'src.detectors.building_blocks.patterns.inverse_head_and_shoulders' has no attribute 'InverseHeadAndShoulders'
- bearish: ❌ ERROR - module 'src.detectors.building_blocks.patterns.inverse_head_and_shoulders' has no attribute 'InverseHeadAndShoulders'


## OSCILLATORS
----------------------------------------------------------------------------------------------------

### rsi_divergence
**Class:** `RSIDivergence`  
**Module:** `src.detectors.building_blocks.oscillators.rsi_divergence`  

**Possible Signals:**
- ⚠️ NO SIGNALS DETECTED (may need specific conditions)

**Test Results:**
- neutral: ❌ ERROR - invalid syntax (rsi_divergence.py, line 20)
- bullish: ❌ ERROR - invalid syntax (rsi_divergence.py, line 20)
- bearish: ❌ ERROR - invalid syntax (rsi_divergence.py, line 20)

### macd_signal
**Class:** `MACDSignal`  
**Module:** `src.detectors.building_blocks.oscillators.macd_signal`  

**Possible Signals:**
- `BULLISH`
- `NEUTRAL`

**Test Results:**
- neutral: `NEUTRAL` @ 80.0%
- bullish: `BULLISH` @ 90.0%
- bearish: `BULLISH` @ 90.0%

### stochastic_rsi
**Class:** `StochasticRSI`  
**Module:** `src.detectors.building_blocks.oscillators.stochastic_rsi`  

**Possible Signals:**
- `NEUTRAL`

**Test Results:**
- neutral: `NEUTRAL` @ 70.0%
- bullish: `NEUTRAL` @ 70.0%
- bearish: `NEUTRAL` @ 80.0%


## PRICE_LEVELS
----------------------------------------------------------------------------------------------------

### hod
**Class:** `HOD`  
**Module:** `src.detectors.building_blocks.price_levels.hod`  

**Possible Signals:**
- ⚠️ NO SIGNALS DETECTED (may need specific conditions)

**Test Results:**
- neutral: ❌ ERROR - invalid syntax (hod.py, line 20)
- bullish: ❌ ERROR - invalid syntax (hod.py, line 20)
- bearish: ❌ ERROR - invalid syntax (hod.py, line 20)

### lod
**Class:** `LOD`  
**Module:** `src.detectors.building_blocks.price_levels.lod`  

**Possible Signals:**
- ⚠️ NO SIGNALS DETECTED (may need specific conditions)

**Test Results:**
- neutral: ❌ ERROR - invalid syntax (lod.py, line 20)
- bullish: ❌ ERROR - invalid syntax (lod.py, line 20)
- bearish: ❌ ERROR - invalid syntax (lod.py, line 20)

### asia_50
**Class:** `Asia50`  
**Module:** `src.detectors.building_blocks.price_levels.asia_50`  

**Possible Signals:**
- ⚠️ NO SIGNALS DETECTED (may need specific conditions)

**Test Results:**
- neutral: ❌ ERROR - No module named 'src.detectors.building_blocks.price_levels.asia_50'
- bullish: ❌ ERROR - No module named 'src.detectors.building_blocks.price_levels.asia_50'
- bearish: ❌ ERROR - No module named 'src.detectors.building_blocks.price_levels.asia_50'

### london_open
**Class:** `LondonOpen`  
**Module:** `src.detectors.building_blocks.price_levels.london_open`  

**Possible Signals:**
- ⚠️ NO SIGNALS DETECTED (may need specific conditions)

**Test Results:**
- neutral: ❌ ERROR - No module named 'src.detectors.building_blocks.price_levels.london_open'
- bullish: ❌ ERROR - No module named 'src.detectors.building_blocks.price_levels.london_open'
- bearish: ❌ ERROR - No module named 'src.detectors.building_blocks.price_levels.london_open'

### ny_open
**Class:** `NYOpen`  
**Module:** `src.detectors.building_blocks.price_levels.ny_open`  

**Possible Signals:**
- ⚠️ NO SIGNALS DETECTED (may need specific conditions)

**Test Results:**
- neutral: ❌ ERROR - No module named 'src.detectors.building_blocks.price_levels.ny_open'
- bullish: ❌ ERROR - No module named 'src.detectors.building_blocks.price_levels.ny_open'
- bearish: ❌ ERROR - No module named 'src.detectors.building_blocks.price_levels.ny_open'


## SESSIONS
----------------------------------------------------------------------------------------------------

### session_time
**Class:** `SessionTime`  
**Module:** `src.detectors.building_blocks.sessions.session_time`  

**Possible Signals:**
- ⚠️ NO SIGNALS DETECTED (may need specific conditions)

**Test Results:**
- neutral: ❌ ERROR - invalid syntax (session_time.py, line 27)
- bullish: ❌ ERROR - invalid syntax (session_time.py, line 27)
- bearish: ❌ ERROR - invalid syntax (session_time.py, line 27)

### kill_zones
**Class:** `KillZones`  
**Module:** `src.detectors.building_blocks.sessions.kill_zones`  

**Possible Signals:**
- ⚠️ NO SIGNALS DETECTED (may need specific conditions)

**Test Results:**
- neutral: ❌ ERROR - invalid syntax (kill_zones.py, line 27)
- bullish: ❌ ERROR - invalid syntax (kill_zones.py, line 27)
- bearish: ❌ ERROR - invalid syntax (kill_zones.py, line 27)


## MOVING_AVERAGES
----------------------------------------------------------------------------------------------------

### ema_20_50_trend
**Class:** `EMA2050Trend`  
**Module:** `src.detectors.building_blocks.moving_averages.ema_20_50_trend`  

**Possible Signals:**
- ⚠️ NO SIGNALS DETECTED (may need specific conditions)

**Test Results:**
- neutral: ❌ ERROR - invalid syntax (ema_20_50_trend.py, line 20)
- bullish: ❌ ERROR - invalid syntax (ema_20_50_trend.py, line 20)
- bearish: ❌ ERROR - invalid syntax (ema_20_50_trend.py, line 20)

### ema_20_50_cross
**Class:** `EMA2050Cross`  
**Module:** `src.detectors.building_blocks.moving_averages.ema_20_50_cross`  

**Possible Signals:**
- `NEUTRAL`

**Test Results:**
- neutral: `NEUTRAL` @ 70%
- bullish: `NEUTRAL` @ 70%
- bearish: `NEUTRAL` @ 70%

### ema_200_trend
**Class:** `EMA200Trend`  
**Module:** `src.detectors.building_blocks.moving_averages.ema_200_trend`  

**Possible Signals:**
- ⚠️ NO SIGNALS DETECTED (may need specific conditions)

**Test Results:**
- neutral: ❌ ERROR - invalid syntax (ema_200_trend.py, line 20)
- bullish: ❌ ERROR - invalid syntax (ema_200_trend.py, line 20)
- bearish: ❌ ERROR - invalid syntax (ema_200_trend.py, line 20)

### ema_50_vector
**Class:** `EMA50Vector`  
**Module:** `src.detectors.building_blocks.moving_averages.ema_50_vector`  

**Possible Signals:**
- `NEUTRAL`

**Test Results:**
- neutral: `NEUTRAL` @ 70%
- bullish: `NEUTRAL` @ 70%
- bearish: `NEUTRAL` @ 70%


## MARKET_STRUCTURE
----------------------------------------------------------------------------------------------------

### swing_points
**Class:** `SwingPoints`  
**Module:** `src.detectors.building_blocks.market_structure.swing_points`  

**Possible Signals:**
- `MINOR_SWING_LOW_DETECTED`
- `SWING_HIGH_DETECTED`

**Test Results:**
- neutral: `SWING_HIGH_DETECTED` @ 65%
- bullish: `MINOR_SWING_LOW_DETECTED` @ 55%
- bearish: `SWING_HIGH_DETECTED` @ 65%

### premium_discount_zones
**Class:** `PremiumDiscountZones`  
**Module:** `src.detectors.building_blocks.market_structure.premium_discount_zones`  

**Possible Signals:**
- ⚠️ NO SIGNALS DETECTED (may need specific conditions)

**Test Results:**
- neutral: ❌ ERROR - invalid syntax (premium_discount_zones.py, line 36)
- bullish: ❌ ERROR - invalid syntax (premium_discount_zones.py, line 36)
- bearish: ❌ ERROR - invalid syntax (premium_discount_zones.py, line 36)

### market_structure_shift
**Class:** `MarketStructureShift`  
**Module:** `src.detectors.building_blocks.market_structure.market_structure_shift`  

**Possible Signals:**
- ⚠️ NO SIGNALS DETECTED (may need specific conditions)

**Test Results:**
- neutral: ❌ ERROR - No module named 'src.detectors.building_blocks.market_structure.market_structure_shift'
- bullish: ❌ ERROR - No module named 'src.detectors.building_blocks.market_structure.market_structure_shift'
- bearish: ❌ ERROR - No module named 'src.detectors.building_blocks.market_structure.market_structure_shift'


## VOLATILITY
----------------------------------------------------------------------------------------------------

### atr
**Class:** `ATR`  
**Module:** `src.detectors.building_blocks.volatility.atr`  

**Possible Signals:**
- `STABLE`

**Test Results:**
- neutral: `STABLE` @ 70%
- bullish: `STABLE` @ 70%
- bearish: `STABLE` @ 70%

### adr
**Class:** `ADR`  
**Module:** `src.detectors.building_blocks.volatility.adr`  

**Possible Signals:**
- ⚠️ NO SIGNALS DETECTED (may need specific conditions)

**Test Results:**
- neutral: ❌ ERROR - invalid syntax (adr.py, line 20)
- bullish: ❌ ERROR - invalid syntax (adr.py, line 20)
- bearish: ❌ ERROR - invalid syntax (adr.py, line 20)

### bollinger_bands
**Class:** `BollingerBands`  
**Module:** `src.detectors.building_blocks.volatility.bollinger_bands`  

**Possible Signals:**
- `ABOVE_UPPER`
- `LOWER_HALF`
- `SQUEEZE_BREAKOUT_BULL`

**Test Results:**
- neutral: `SQUEEZE_BREAKOUT_BULL` @ 100%
- bullish: `ABOVE_UPPER` @ 90%
- bearish: `LOWER_HALF` @ 80%


## INSTITUTIONAL
----------------------------------------------------------------------------------------------------

### vwap
**Class:** `VWAP`  
**Module:** `src.detectors.building_blocks.institutional.vwap`  

**Possible Signals:**
- ⚠️ NO SIGNALS DETECTED (may need specific conditions)

**Test Results:**
- neutral: ❌ ERROR - invalid syntax (vwap.py, line 20)
- bullish: ❌ ERROR - invalid syntax (vwap.py, line 20)
- bearish: ❌ ERROR - invalid syntax (vwap.py, line 20)

### anchored_vwap
**Class:** `AnchoredVWAP`  
**Module:** `src.detectors.building_blocks.institutional.anchored_vwap`  

**Possible Signals:**
- `ABOVE_ANCHORED_VWAP`
- `BELOW_ANCHORED_VWAP`

**Test Results:**
- neutral: `ABOVE_ANCHORED_VWAP` @ 75%
- bullish: `ABOVE_ANCHORED_VWAP` @ 75%
- bearish: `BELOW_ANCHORED_VWAP` @ 75%

### volume_profile
**Class:** `VolumeProfile`  
**Module:** `src.detectors.building_blocks.institutional.volume_profile`  

**Possible Signals:**
- ⚠️ NO SIGNALS DETECTED (may need specific conditions)

**Test Results:**
- neutral: ❌ ERROR - No module named 'src.detectors.building_blocks.institutional.volume_profile'
- bullish: ❌ ERROR - No module named 'src.detectors.building_blocks.institutional.volume_profile'
- bearish: ❌ ERROR - No module named 'src.detectors.building_blocks.institutional.volume_profile'


## SMC_ICT
----------------------------------------------------------------------------------------------------

### order_block
**Class:** `OrderBlock`  
**Module:** `src.detectors.building_blocks.smc_ict.order_block`  

**Possible Signals:**
- ⚠️ NO SIGNALS DETECTED (may need specific conditions)

**Test Results:**
- neutral: ❌ ERROR - No module named 'src.detectors.building_blocks.smc_ict.order_block'
- bullish: ❌ ERROR - No module named 'src.detectors.building_blocks.smc_ict.order_block'
- bearish: ❌ ERROR - No module named 'src.detectors.building_blocks.smc_ict.order_block'

### fair_value_gap
**Class:** `FairValueGap`  
**Module:** `src.detectors.building_blocks.smc_ict.fair_value_gap`  

**Possible Signals:**
- ⚠️ NO SIGNALS DETECTED (may need specific conditions)

**Test Results:**
- neutral: ❌ ERROR - No module named 'src.detectors.building_blocks.smc_ict.fair_value_gap'
- bullish: ❌ ERROR - No module named 'src.detectors.building_blocks.smc_ict.fair_value_gap'
- bearish: ❌ ERROR - No module named 'src.detectors.building_blocks.smc_ict.fair_value_gap'

### liquidity_sweep
**Class:** `LiquiditySweep`  
**Module:** `src.detectors.building_blocks.smc_ict.liquidity_sweep`  

**Possible Signals:**
- ⚠️ NO SIGNALS DETECTED (may need specific conditions)

**Test Results:**
- neutral: ❌ ERROR - No module named 'src.detectors.building_blocks.smc_ict.liquidity_sweep'
- bullish: ❌ ERROR - No module named 'src.detectors.building_blocks.smc_ict.liquidity_sweep'
- bearish: ❌ ERROR - No module named 'src.detectors.building_blocks.smc_ict.liquidity_sweep'

### break_of_structure
**Class:** `BreakOfStructure`  
**Module:** `src.detectors.building_blocks.smc_ict.break_of_structure`  

**Possible Signals:**
- `BEARISH`
- `BULLISH`

**Test Results:**
- neutral: `BULLISH` @ 80%
- bullish: `BULLISH` @ 80%
- bearish: `BEARISH` @ 80%

### change_of_character
**Class:** `ChangeOfCharacter`  
**Module:** `src.detectors.building_blocks.smc_ict.change_of_character`  

**Possible Signals:**
- `NEUTRAL`

**Test Results:**
- neutral: `NEUTRAL` @ 0%
- bullish: `NEUTRAL` @ 0%
- bearish: `NEUTRAL` @ 0%
