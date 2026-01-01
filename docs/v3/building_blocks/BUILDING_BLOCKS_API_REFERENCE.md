# Building Blocks API Reference

**Purpose:** Complete reference for all building block return signatures and expected outputs  
**Status:** Active - Update as blocks are completed  
**Created:** 2026-01-01  
**Last Updated:** 2026-01-01  

---

## Overview

This document catalogs the **exact return signatures** of all building blocks. Use this as the **authoritative reference** when:
- Testing blocks
- Building validation frameworks
- Understanding signal types
- Integrating blocks into strategies

**CRITICAL RULE:** Blocks define their own signal types. Validators must adapt to blocks, NOT the other way around.

---

## Block Categorization System
docs/v3/building_blocks/BLOCK_CATEGORIZATION.md
### THREE BLOCK TYPES

**📊 SIGNAL BLOCKS** - Predictive Trading Signals (27 confirmed)
- **Purpose:** Generate predictions about future price movement
- **Returns:** Directional signals (BULLISH/BEARISH or pattern-specific)
- **Testing:** Walk-forward validation (did prediction work?)
- **Validator:** `DirectionalSignalValidator` or `VolatilitySignalValidator`
- **Examples:** MA crossovers, Order Blocks, BOS, pattern completions

**📏 METADATA BLOCKS** - Context/Measurements (Identified: ATR, ADX, price levels)
- **Purpose:** Provide current measurements, not predictions
- **Returns:** Descriptive data (ATR value, trend strength, price levels)
- **Testing:** Data quality validation (is measurement accurate?)
- **Validator:** `MetadataBlockValidator`
- **Examples:** ATR (stop-loss distance), ADX (trend strength 0-100), HOD (price level)
- **Usage:** Context for signal blocks, risk management, filtering

**🔀 HYBRID BLOCKS** - Both Signals & Metadata (Confirmed: ADR, Bollinger Bands)
- **Purpose:** Generate signals AND provide measurements
- **Returns:** Both directional signals and metadata
- **Testing:** Dual validation (both tests)
- **Validators:** Both signal validator AND metadata validator
- **Examples:** ADR (volatility levels + targets), Bollinger Bands (bands + squeeze signals)

### Categorization Status

**Confirmed (29/67):**
- ✅ Signal Blocks: 27 (production-ready)
- ✅ Metadata Blocks: 1 (ATR)
- ✅ Hybrid Blocks: 1 (ADR)

**Remaining (38/67):** Under categorization review

---

## Signal Type Categories

### Directional Signals (Trading Actions)
**Used by:** Most trading pattern blocks  
**Returns:** `BULLISH` or `BEARISH`  
**Meaning:** Actionable trading direction

### Descriptive Signals (Market State)
**Used by:** Volatility, trend strength, position indicators  
**Returns:** Various descriptive states  
**Meaning:** Market condition description (not direct trade signal)

### Neutral/Error Signals (Non-actionable)
**Common across all blocks:**
- `NEUTRAL` - No clear signal
- `INSUFFICIENT_DATA` - Need more bars
- `ERROR` - Data validation failed
- `NO_BREAK` - Pattern not detected (SMC/ICT specific)

---

## ✅ PRODUCTION READY BLOCKS (26/67)

### MOVING AVERAGES (6/6 - 100%)

#### 1. EMA 50 Vector
**File:** `moving_averages/ema_50_vector.py`  
**Function:** `analyze(df)`  
**Returns:**
- **Signals:** `BULLISH`, `BEARISH`, `NEUTRAL`
- **Metadata:** `ema_value`, `price`, `distance_pct`, `slope`, `slope_category`, `slope_strength`
- **Optimization:** period=50, slope_threshold=0.001
- **Quality:** 80/100, Accuracy: 58.6%

#### 2. EMA 55 Vector
**File:** `moving_averages/ema_55_vector.py`  
**Function:** `analyze(df)`  
**Returns:**
- **Signals:** `BULLISH`, `BEARISH`, `NEUTRAL`
- **Metadata:** `ema_value`, `price`, `distance_pct`, `slope`, `slope_category`
- **Optimization:** period=55, slope_threshold=0.001
- **Quality:** 80/100, Accuracy: 58.2%

#### 3. EMA 200 Trend
**File:** `moving_averages/ema_200_trend.py`  
**Function:** `analyze(df)`  
**Returns:**
- **Signals:** `BULLISH`, `BEARISH`, `NEUTRAL`
- **Metadata:** `ema_value`, `price`, `distance_pct`, `direction`, `strength`
- **Optimization:** period=200, slope_threshold=0.001
- **Quality:** 80/100, Accuracy: 55.1%

#### 4. EMA 255 Vector
**File:** `moving_averages/ema_255_vector.py`  
**Function:** `analyze(df)`  
**Returns:**
- **Signals:** `BULLISH`, `BEARISH`, `NEUTRAL`
- **Metadata:** `ema_value`, `price`, `distance_pct`, `slope`
- **Optimization:** period=255, slope_threshold=0.0005
- **Quality:** 80/100, Accuracy: 60.3%

#### 5. EMA 800 Vector
**File:** `moving_averages/ema_800_vector.py`  
**Function:** `analyze(df)`  
**Returns:**
- **Signals:** `BULLISH`, `BEARISH`, `NEUTRAL`
- **Metadata:** `ema_value`, `price`, `distance_pct`, `slope`
- **Optimization:** period=800, slope_threshold=0.0001
- **Quality:** 80/100, Accuracy: 57.2%

#### 6. EMA 20/50 Cross
**File:** `moving_averages/ema_20_50_cross.py`  
**Function:** `analyze(df)`  
**Returns:**
- **Signals:** `BULLISH_CROSS`, `BEARISH_CROSS`, `NEUTRAL`
- **Metadata:** `ema_fast`, `ema_slow`, `distance_pct`, `cross_detected`
- **Optimization:** fast=20, slow=50
- **Quality:** 80/100, Accuracy: 60.9%

---

### OSCILLATORS (3/3 - 100%)

#### 7. MACD Signal
**File:** `oscillators/macd_signal.py`  
**Function:** `analyze(df)`  
**Returns:**
- **Signals:** `BULLISH`, `BEARISH`, `NEUTRAL`
- **Metadata:** `macd`, `signal`, `histogram`, `cross_type`
- **Optimization:** fast=12, slow=26, signal=9
- **Quality:** 80/100, Accuracy: 55.1%

#### 8. RSI Divergence
**File:** `oscillators/rsi_divergence.py`  
**Function:** `analyze(df)`  
**Returns:**
- **Signals:** `BULLISH_DIVERGENCE`, `BEARISH_DIVERGENCE`, `NEUTRAL`
- **Metadata:** `rsi_value`, `divergence_type`, `divergence_strength`
- **Optimization:** period=14, divergence_lookback=3
- **Quality:** 80/100, Accuracy: 58.6%

#### 9. Stochastic RSI
**File:** `oscillators/stochastic_rsi.py`  
**Function:** `analyze(df)`  
**Returns:**
- **Signals:** `BULLISH`, `BEARISH`, `NEUTRAL`
- **Metadata:** `k_value`, `d_value`, `zone`, `cross_detected`
- **Optimization:** period=14, smooth_k=3, smooth_d=3
- **Quality:** 80/100, Accuracy: 58.2%

---

### PRICE ACTION (4/4 - 100%)

#### 10. Order Block
**File:** `price_action/order_block.py`  
**Function:** `analyze(df)`  
**Returns:**
- **Signals:** `BULLISH_OB`, `BEARISH_OB`, `NEUTRAL`
- **Metadata:** `ob_type`, `ob_price`, `ob_timestamp`, `strength`
- **Optimization:** lookback=20, min_volume_multiplier=1.5
- **Quality:** 100/100, Accuracy: 69.3% ⭐⭐ RECORD

#### 11. Fair Value Gap
**File:** `price_action/fair_value_gap.py`  
**Function:** `analyze(df)`  
**Returns:**
- **Signals:** `BULLISH_FVG`, `BEARISH_FVG`, `NEUTRAL`
- **Metadata:** `fvg_type`, `gap_size`, `gap_high`, `gap_low`
- **Optimization:** min_gap_pct=0.1
- **Quality:** 90/100, Accuracy: 62.9% ⭐⭐

#### 12. Liquidity Sweep
**File:** `price_action/liquidity_sweep.py`  
**Function:** `analyze(df)`  
**Returns:**
- **Signals:** `BULLISH_SWEEP`, `BEARISH_SWEEP`, `NEUTRAL`
- **Metadata:** `sweep_type`, `swept_level`, `rejection_strength`
- **Optimization:** lookback=20, min_sweep_pct=0.05
- **Quality:** 90/100, Accuracy: 62.6% ⭐⭐

#### 13. Breaker Block
**File:** `price_action/breaker_block.py`  
**Function:** `analyze(df)`  
**Returns:**
- **Signals:** `BULLISH_BREAKER`, `BEARISH_BREAKER`, `NEUTRAL`
- **Metadata:** `breaker_type`, `original_ob`, `break_price`, `retest_detected`
- **Optimization:** lookback=20
- **Quality:** 80/100, Accuracy: 58.2%

---

### TREND (2/2 - 100%)

#### 14. Ichimoku Cloud
**File:** `trend/ichimoku_cloud.py`  
**Function:** `analyze(df)`  
**Returns:**
- **Signals:** `BULLISH`, `BEARISH`, `NEUTRAL`
- **Metadata:** `tenkan`, `kijun`, `senkou_a`, `senkou_b`, `cloud_color`, `price_vs_cloud`
- **Optimization:** tenkan=9, kijun=26, senkou=52
- **Quality:** 80/100, Accuracy: 55.0%

#### 15. ADX (Average Directional Index)
**File:** `trend/adx.py`  
**Function:** `analyze(df)`  
**Returns:**
- **Signals:** `BULLISH`, `BEARISH`, `RANGING` (CRITICAL: Uses RANGING, not NEUTRAL)
- **Metadata:** `adx_value`, `plus_di`, `minus_di`, `trend_strength`, `direction`
- **Trend Strength:** `WEAK`, `MODERATE`, `STRONG`, `VERY_STRONG`
- **Optimization:** period=14
- **Quality:** 80/100, Accuracy: 57.6%
- **NOTE:** Special case - ADX can return RANGING signal type

---

### ICT/SMC (10/10 - 100%) 🎉 COMPLETE!

#### 16. Break of Structure (BOS)
**File:** `smc_ict/break_of_structure.py`  
**Function:** `analyze(df)`  
**Returns:**
- **Signals:** `BULLISH_BOS`, `BEARISH_BOS`, `NEUTRAL`
- **Metadata:** `bos_type`, `previous_high`, `previous_low`, `break_price`
- **Optimization:** swing_lookback=3
- **Quality:** 90/100, Accuracy: 61.3%

#### 17. Market Structure Shift (MSS)
**File:** `smc_ict/market_structure_shift.py`  
**Function:** `analyze(df)`  
**Returns:**
- **Signals:** `BULLISH_MSS`, `BEARISH_MSS`, `NEUTRAL`
- **Metadata:** `mss_type`, `broken_structure`, `shift_strength`
- **Optimization:** swing_lookback=3
- **Quality:** 90/100, Accuracy: 62.0%

#### 18. Displacement
**File:** `smc_ict/displacement.py`  
**Function:** `analyze(df)`  
**Returns:**
- **Signals:** `BULLISH_DISPLACEMENT`, `BEARISH_DISPLACEMENT`, `NEUTRAL`
- **Metadata:** `displacement_size`, `candle_count`, `displacement_pct`
- **Optimization:** min_displacement_pct=0.5, max_candles=3
- **Quality:** 90/100, Accuracy: 59.4%

#### 19. Inducement
**File:** `smc_ict/inducement.py`  
**Function:** `analyze(df)`  
**Returns:**
- **Signals:** `BULLISH_INDUCEMENT`, `BEARISH_INDUCEMENT`, `NEUTRAL`
- **Metadata:** `inducement_type`, `liquidity_grabbed`, `reversal_detected`
- **Optimization:** lookback=3
- **Quality:** 90/100, Accuracy: 62.6% ⭐⭐

#### 20. Optimal Trade Entry (OTE)
**File:** `smc_ict/optimal_trade_entry.py`  
**Function:** `analyze(df)`  
**Returns:**
- **Signals:** `BULLISH_OTE`, `BEARISH_OTE`, `NEUTRAL`
- **Metadata:** `retracement_level`, `fib_zone`, `ote_quality`
- **Optimization:** None (uses standard 0.618-0.786 Fib zone)
- **Quality:** 80/100, Accuracy: 55.1%

#### 21. Swing Failure Pattern (SFP)
**File:** `smc_ict/swing_failure_pattern.py`  
**Function:** `analyze(df)`  
**Returns:**
- **Signals:** `BULLISH_SFP`, `BEARISH_SFP`, `NEUTRAL`
- **Metadata:** `sfp_type`, `failed_level`, `reversal_candle`
- **Optimization:** lookback=3
- **Quality:** 90/100, Accuracy: 62.3% ⭐

#### 22. Premium/Discount Zones
**File:** `smc_ict/premium_discount.py`  
**Function:** `analyze(df)`  
**Returns:**
- **Signals:** `PREMIUM`, `DISCOUNT`, `EQUILIBRIUM`
- **Metadata:** `zone_type`, `range_high`, `range_low`, `current_pct`
- **Optimization:** range_lookback=20
- **Quality:** 80/100, Accuracy: 56.6%
- **NOTE:** Special case - returns zone types, not directional signals

#### 23. Change of Character (CHOCH)
**File:** `smc_ict/change_of_character.py`  
**Function:** `analyze(df)`  
**Returns:**
- **Signals:** `BULLISH`, `BEARISH`, `NEUTRAL`
- **Metadata:** `choch_type`, `swing_point_broken`, `break_pct`
- **Optimization:** swing_lookback=3, lookback_window=50
- **Quality:** 80/100, Accuracy: 55.8%
- **NOTE:** Fixed 3 critical bugs - swing detection, pattern logic, lookback window

#### 24. Mitigation Block
**File:** `smc_ict/mitigation_block.py`  
**Function:** `analyze(df)`  
**Returns:**
- **Signals:** `BULLISH`, `BEARISH`, `NEUTRAL`
- **Metadata:** `mitigation_type`, `mitigation_high`, `mitigation_low`, `gap_size`, `gap_pct`, `distance_pct`
- **Optimization:** lookback=20
- **Quality:** 90/100, Accuracy: 60.2% ⭐
- **Signals:** 11,088 in 180 days (61.6/day)
- **R/R:** 7.89 (excellent)
- **NOTE:** Bitcoin-adapted - detects impulse candles approaching mitigation zones (not traditional gaps)

#### 25. Balanced Price Range
**File:** `smc_ict/balanced_price_range.py`  
**Function:** `analyze(df)`  
**Returns:**
- **Signals:** `BULLISH`, `BEARISH` (based on position in range)
- **Metadata:** `range_type`, `range_high`, `range_low`, `range_mid`, `range_size`, `position_in_range`, `avg_deviation`, `is_compressing`
- **Optimization:** lookback=20, balance_threshold=15.0
- **Quality:** 80/100, Accuracy: 56.3%
- **Signals:** 1,749 in 180 days (9.7/day)
- **R/R:** 7.25 (excellent)
- **NOTE:** Bitcoin-adapted - 15% threshold vs traditional 5% (volatility adjustment), always directional signal

---

### INSTITUTIONAL (1/5 - 20%)

#### 26. VWAP
**File:** `institutional/vwap.py`  
**Function:** `analyze(df)`  
**Returns:**
- **Signals:** `BULLISH`, `BEARISH` (price above/below VWAP)
- **Metadata:** `vwap_value`, `current_price`, `distance_pct`
- **Optimization:** None (calculation based)
- **Quality:** 80/100, Accuracy: 56.9%
- **Note:** Bearish accuracy 62.0% (excellent for discount zone detection)

---

## 🔄 METADATA & HYBRID BLOCKS

### Metadata Blocks (Context/Measurements)

#### ATR (Average True Range) - METADATA BLOCK
**File:** `volatility/atr.py`  
**Function:** `analyze(df)`  
**Block Type:** **METADATA** (not signal generator)
**Purpose:** Risk management tool - stop-loss placement, position sizing
**Returns:**
- **Signal:** `EXPANDING`, `CONTRACTING`, `STABLE`, `NEUTRAL` (volatility trend - NOT predictive)
- **Metadata (PRIMARY FUNCTION):**
  - `atr_value`: Current ATR in price units
  - `atr_percent`: ATR as % of price (BTC typically 0.1-10%)
  - `stop_suggestions`: Dict with conservative/standard/aggressive stops
    * `distance`: Stop distance in price units
    * `multiplier`: ATR multiplier used (1.5x, 2.0x, 2.5x)
    * `long_stop`: Entry - (ATR × multiplier)
    * `short_stop`: Entry + (ATR × multiplier)
  - `position_sizing_factor`: Inverse volatility scaling (higher ATR = smaller position)
  - `volatility_level`: Classification (CALM, NORMAL, HIGH, VERY_HIGH, EXTREME)
  - `atr_trend`: Trend direction (RISING, FALLING, STABLE)
  - `current_price`: Reference price
- **Status:** ✅ METADATA BLOCK - Test with MetadataBlockValidator
- **Quality:** 90/100 (as metadata tool) - Validates ATR calculations, stop suggestions
- **Usage:** Reference ATR value for stop placement; multiply ATR by 1.5-2.5 for stop distance
- **Note:** Signals (EXPANDING/CONTRACTING) are NOT predictive - describes current state only

#### ADX (Average Directional Index) - METADATA BLOCK
**File:** `trend_momentum/adx.py`  
**Function:** `analyze(df)`  
**Block Type:** **METADATA** (trend strength filter)
**Purpose:** Measure trend strength (not direction)
**Returns:**
- **Signal:** `STRONG_TREND`, `WEAK_TREND`, `RANGING` (descriptive - NOT predictive)
- **Metadata (PRIMARY FUNCTION):**
  - `adx_value`: 0-100 scale
    * 0-25: Weak/no trend (ranging)
    * 25-50: Strong trend
    * 50-75: Very strong trend
    * 75-100: Extreme trend
  - `trend_classification`: Strength category
  - `plus_di`: Positive Direction Indicator
  - `minus_di`: Negative Direction Indicator
- **Status:** ⚠️ METADATA BLOCK - Test with MetadataBlockValidator
- **Quality:** TBD (pending metadata validation)
- **Usage:** Filter - only trade trend strategies when ADX >25; range strategies when <20
- **Note:** ADX does NOT indicate direction, only strength

#### HOD/HOW/LOD/LOW - METADATA BLOCKS (Price Levels)
**Files:** `price_levels/hod.py`, etc.  
**Block Type:** **METADATA** (reference price levels)
**Purpose:** Provide intraday resistance/support references
**Returns:**
- **Metadata (PRIMARY FUNCTION):**
  - `hod`/`lod`: Price level
  - `current_price`: Current price
  - `distance_pct`: Distance to level as %
  - `test_count`: Number of times tested
- **Status:** ⚠️ NEEDS REDESIGN - Self-referencing logic bug (HOD updates realtime)
- **Fix Needed:** Use yesterday's HOD as fixed reference
- **Usage:** Reference levels for other strategies

### Hybrid Blocks (Both Signals & Metadata)

#### ADR (Average Daily Range) - HYBRID BLOCK
**File:** `volatility/adr.py`  
**Function:** `analyze(df)`  
**Block Type:** **HYBRID** (volatility levels + targets)
**Returns:**
- **Signals (for validation):** `CALM`, `NORMAL`, `ELEVATED`, `HIGH`, `EXTREME`
- **Metadata (for usage):**
  - `adr_value`: Average daily range in price units
  - `adr_percent`: ADR as % of price
  - `current_range`: Today's range
  - `range_classification`: Volatility level
  - `targets`: Profit target suggestions at 0.5x, 1.0x, 1.5x, 2.0x ADR
  - `position_sizing_factor`: Volatility-based sizing
- **Status:** ✅ PRODUCTION READY (70/100, 60.1% accuracy)
- **Quality:** CALM predictions 95.3% accurate
- **Usage:** Both signal (volatility level) and metadata (targets, position sizing)

### Volatility Blocks (Complex Signal Types)

#### Bollinger Bands ✅ EXPANDED
**File:** `volatility/bollinger_bands.py`  
**Function:** `analyze(df)`  
**Returns:**
- **Signal (original):** `SQUEEZE_BREAKOUT_BULL`, `SQUEEZE_BREAKOUT_BEAR`, `BULLISH_REVERSAL`, `BEARISH_REVERSAL`, `ABOVE_UPPER`, `NEAR_UPPER`, `UPPER_HALF`, `LOWER_HALF`, `NEAR_LOWER`, `BELOW_LOWER`
- **Metadata:** Complex - includes bands, squeeze detection, patterns, volatility regime
  - **EXPANSION:** `simple_signal` field added with `BULLISH`, `BEARISH`, or `NEUTRAL`
  - **EXPANSION:** `original_signal` field preserves complex signal
- **Status:** ✅ EXPANDED - Now validator compatible while preserving all original functionality
- **Backward Compatible:** YES - All original functionality intact
- **Usage:**
  - **Existing code:** Uses `result['signal']` (unchanged - complex signals)
  - **Validators:** Can use `result['metadata']['simple_signal']` (new - directional)
  - **Best of both:** Full complexity + validator compatibility

#### ATR (Average True Range)
**File:** `volatility/atr.py`  
**Function:** `analyze(df)`  
**Expected Returns:**
- **Signals:** Likely volatility state descriptions (not directional)
- **Metadata:** ATR value, volatility regime
- **Status:** ⚠️ UNTESTED - Likely incompatible with directional validator
- **Solution:** Needs volatility-specific testing framework

#### ADR (Average Daily Range)
**File:** `volatility/adr.py`  
**Function:** `analyze(df)`  
**Expected Returns:**
- **Signals:** Likely range descriptions (not directional)
- **Status:** ⚠️ UNTESTED - Likely incompatible

---

## Testing Framework Requirements

### Directional Signal Validator
**File:** `scripts/validate_walkforward_signals.py`  
**Accepts:** `BULLISH`, `BEARISH`, and variants ending with these (e.g., `BULLISH_CROSS`, `BULLISH_OB`)  
**Filters out:** `NEUTRAL`, `INSUFFICIENT_DATA`, `ERROR`, `NO_BREAK`  
**Use for:** Trading pattern blocks (most blocks)

### Descriptive Signal Validator
**Status:** ❌ NOT YET CREATED  
**Needed for:** Volatility indicators, market regime classifiers  
**Should accept:** Block-specific signal types  
**Examples:**
- Bollinger Bands: All 10+ signal types
- ADX: `RANGING` signal type
- Premium/Discount: `PREMIUM`, `DISCOUNT`, `EQUILIBRIUM`

---

## Signal Type Mapping Guide

### When to use BULLISH/BEARISH
✅ **Use directional signals when:**
- Block indicates a trade direction
- Pattern suggests entry opportunity
- Trend direction is clear
- Example: Order Block detected = direction to trade

### When to use Descriptive Signals
✅ **Use descriptive signals when:**
- Block describes market state (not action)
- Multiple states possible beyond bull/bear
- Used for confluence, not standalone trade
- Example: Bollinger position = context for other signals

### Special Cases
- **ADX:** Returns `RANGING` when trend is weak (ADX < 25)
- **Premium/Discount:** Returns zone types for confluence
- **Bollinger Bands:** Returns 10+ states for market context

---

## Block Development Standards

### Standard Return Format
All blocks MUST return dictionary with:
```python
{
    'signal': str,  # Block-specific signal type
    'confidence': float,  # 0-100
    'metadata': dict,  # Block-specific data
    'timestamp': datetime,
    'timeframe': str,
    'confluence_factors': list
}
```

### Signal Type Requirements
1. **Be descriptive:** Signal should describe what was detected
2. **Be consistent:** Use same signal types across similar detections
3. **Be clear:** Avoid ambiguous signal names
4. **Document:** List all possible signals in this doc

### Testing Requirements
1. **Match validator to block type:** Don't force directional validator on descriptive blocks
2. **Test with correct framework:** Use appropriate validator for signal type
3. **Document incompatibilities:** Update this doc when incompatible

---

## Revision History

**2026-01-01 (Initial):** Created with 24 production-ready blocks  
- Documented all BULLISH/BEARISH blocks
- Identified Bollinger Bands incompatibility
- Established testing framework requirements

**2026-01-01 (Update):** Added 2 ICT blocks - ICT category 100% complete!  
- Added Mitigation Block (90/100, 60.2%)
- Added Balanced Price Range (80/100, 56.3%)
- ICT/SMC category now 10/10 (100%) ✅
- Total blocks: 26/67 (38.8%)

---

## Future Additions

As blocks are completed, add to this document:
- Block name and file path
- analyze() function signature
- All possible signal return types
- Metadata structure
- Optimization parameters
- Quality scores
- Special notes/incompatibilities

---

*This document is the authoritative reference for building block APIs. Update whenever blocks are added or modified.*
