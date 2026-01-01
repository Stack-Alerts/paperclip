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

## ✅ PRODUCTION READY BLOCKS (24/67)

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

### ICT/SMC (8/10 - 80%)

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

---

### INSTITUTIONAL (1/5 - 20%)

#### 24. VWAP
**File:** `institutional/vwap.py`  
**Function:** `analyze(df)`  
**Returns:**
- **Signals:** `BULLISH`, `BEARISH` (price above/below VWAP)
- **Metadata:** `vwap_value`, `current_price`, `distance_pct`
- **Optimization:** None (calculation based)
- **Quality:** 80/100, Accuracy: 56.9%
- **Note:** Bearish accuracy 62.0% (excellent for discount zone detection)

---

## 🔄 BLOCKS IDENTIFIED AS INCOMPATIBLE

### Volatility Blocks (Complex Signal Types)

#### Bollinger Bands
**File:** `volatility/bollinger_bands.py`  
**Function:** `analyze(df)`  
**Returns:**
- **Signals:** `SQUEEZE_BREAKOUT_BULL`, `SQUEEZE_BREAKOUT_BEAR`, `BULLISH_REVERSAL`, `BEARISH_REVERSAL`, `ABOVE_UPPER`, `NEAR_UPPER`, `UPPER_HALF`, `LOWER_HALF`, `NEAR_LOWER`, `BELOW_LOWER`
- **Metadata:** Complex - includes bands, squeeze detection, patterns, volatility regime
- **Status:** ❌ INCOMPATIBLE with simple directional validator
- **Reason:** Returns 10+ different signal types describing market state
- **Solution:** Needs specialized validator for volatility indicators

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

**2026-01-01:** Initial creation with 24 production-ready blocks  
- Documented all BULLISH/BEARISH blocks
- Identified Bollinger Bands incompatibility
- Established testing framework requirements

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
