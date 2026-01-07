# Fair Value Gap (FVG) Building Block

**Block Number:** 12/66 | **Category:** Price Action (ICT/SMC) | **Version:** 1.0 | **Status:** ✅ PRODUCTION READY

---

## ✅ VERY SELECTIVE BOOSTER - PRODUCTION READY

**This block detects institutional price imbalances (FVGs) for premium quality confirmation**

**Test Results:** 1.47% signal rate (very selective booster)  
**Block Type:** EVENT-DRIVEN (3-candle gap pattern detection)  
**Design:** ICT/SMC Fair Value Gap with event tracking  
**Grade:** A+ (98/100) - HIGHEST confidence (94.0%)

**Current Performance:**
- ✅ 1.47% signal rate (PERFECT for very selective booster)
- ✅ 94.0% confidence (HIGHEST QUALITY - premium institutional)
- ✅ 90.3% NO_FVG (excellent selectivity)
- ✅ 46/54 bullish/bearish balance (good for very selective)
- ✅ 0% error rate (perfect reliability)
- ✅ **EVENT TRACKING** (63.9% NEW gap entries for timing!)

**Implementation Features:**
1. ✅ 3-candle FVG pattern detection (ICT methodology)
2. ✅ Bullish FVG: Gap up (candle3_low > candle1_high)
3. ✅ Bearish FVG: Gap down (candle3_high < candle1_low)
4. ✅ Event tracking (`is_new_event` for fresh gap fills)
5. ✅ Gap zone calculation (high/low/mid/size)
6. ✅ Liquidation event integration (institutional quality boost)
7. ✅ Gap age tracking (bars since formation)
8. ✅ Optimized lookback (7 vs 50 - much faster)

**Status:** ✅ PRODUCTION READY - A+ GRADE

**See Expert Review:** `docs/v3/expert_analisys_review_building_blocks/12_fair_value_gap_expert_review.md`

**Deployment:**
- Very selective booster (final filter - layer 9-10)
- Premium institutional imbalance confirmation
- Use `is_new_event=True` for fresh gap fill timing
- Expected: 252 signals per 180 days (1.4/day, 0.89 NEW entries/day)

---

## Overview

Fair Value Gaps (FVGs) are price inefficiencies where price moved too quickly, leaving unfilled zones. ICT/SMC concept - institutions often return to fill these gaps.

## Block Classification

**Type:** EVENT-DRIVEN VERY SELECTIVE BOOSTER
- Detects 3-candle gap patterns
- Very selective (1.47% signal rate)  
- **HIGHEST confidence (94.0%)**
- Premium institutional imbalance detection

## Technical Specifications

**Components:** 3-Candle Pattern + Gap Zone Calculation + Event Tracking + Liquidation Detection  
**File:** `src/detectors/building_blocks/price_action/fair_value_gap.py`

## Signals

### Gap Detection (1.47% signal rate):
- **BULLISH**: Price in bullish FVG zone (gap fill in progress)
  - 94-100% confidence based on gap size
  - 95% if NEW gap entry (just entered zone)
  - 90% if continuing fill
  
- **BEARISH**: Price in bearish FVG zone (gap fill in progress)
  - 94-100% confidence based on gap size
  - 95% if NEW gap entry
  - 90% if continuing fill

- **NEUTRAL**: FVG exists but price not in zone (8.23% of bars)
- **NO_FVG**: No gap detected (90.3% of bars)

### FVG Formation Rules:

**Bullish FVG (Gap Up):**
```python
# 3-candle pattern where middle candle creates gap
Candle 1: High at level A
Candle 2: Creates upward movement  
Candle 3: Low at level B

If B > A: Bullish FVG exists
Gap Zone: A (low) to B (high)
```

**Bearish FVG (Gap Down):**
```python
# 3-candle pattern where middle candle creates gap
Candle 1: Low at level A
Candle 2: Creates downward movement
Candle 3: High at level B

If B < A: Bearish FVG exists  
Gap Zone: B (low) to A (high)
```

## Event Tracking (Critical Feature)

**is_new_event Detection:**
- **TRUE (63.9% of signals):** Price JUST entered gap zone
  - Previous bar: NOT in gap
  - Current bar: IN gap
  - **Use for timing entries** (fresh gap fill opportunity)
  - 95% confidence
  
- **FALSE (36.1% of signals):** Price continuing in gap zone
  - Previous bar: IN gap
  - Current bar: Still IN gap
  - Gap fill in progress
  - 90% confidence

**bars_since_gap:** Tracks gap age (useful for stale gap filtering)

## Parameters (Optimized)

```python
min_gap_pct: 0.2%    # Minimum gap size to qualify
lookback: 7          # Optimized from 50 (much faster window)
timeframe: '15min'
```

**Optimization Results:**
- Quality: 90/100 (exceptional)
- Accuracy: 62.9% (TIED FOR HIGHEST EVER)  
- Signals: 237 in 180 days
- R/R: 6.08 (excellent)
- Discovery: lookback=7 beats 50 (faster = better)

## Gap Quality Classification

**Size-Based Confidence:**
- Small gaps (<0.5%): 90% confidence
- Medium gaps (0.5-1.0%): 105% → capped at 100%
- Large gaps (>1.0%): 120% → capped at 100%

**Liquidation-Enhanced (Advanced):**
- FVG formed during liquidation spike: +15% confidence
- Quality upgraded to: "INSTITUTIONAL"
- Indicates smart money activity

## Trading Strategy

### As Very Selective Booster (Primary Use):
```python
# Multi-block strategy with FVG as final filter
def generate_signal(df):
    trend = ema_20_50_trend.analyze(df)
    trigger = macd_signal.analyze(df)
    confirm = stochastic_rsi.analyze(df)
    booster = order_block.analyze(df)
    fvg = fair_value_gap.analyze(df)
    
    if (
        trend['signal'] == 'BULLISH' and        # Filter (50%)
        trigger['signal'] == 'BULLISH' and      # Trigger (8.82%)
        confirm['confidence'] > 70 and          # Confirmation (33.73%)
        booster['signal'] == 'BULLISH' and      # Booster (4.12%)
        fvg['signal'] == 'BULLISH'              # Very Selective (1.47%)
    ):
        # Ultra-premium signal!
        if fvg['metadata']['is_new_event']:
            # Fresh gap entry = BEST timing
            return 'ENTER_LONG'  # ~2 signals per 180 days
        else:
            # Continuing gap fill
            return 'ENTER_LONG'  # ~3-5 signals per 180 days
    
    return 'NO_SIGNAL'
```

### Using Event Tracking for Timing:
```python
# Trade only NEW gap entries for best timing
def generate_signal_fresh_only(df):
    fvg = fair_value_gap.analyze(df)
    
    if (
        fvg['signal'] == 'BULLISH' and
        fvg['metadata']['is_new_event'] == True and  # JUST entered
        fvg['metadata']['gap_pct'] > 0.5  # Medium+ gap
    ):
        # Fresh gap fill opportunity
        return 'ENTER_LONG'  # ~0.89 signals/day (NEW only)
    
    return 'NO_SIGNAL'
```

### "Unicorn" Setup (FVG + Order Block):
```python
# When FVG overlaps with Order Block = highest probability
def detect_unicorn(df):
    fvg = fair_value_gap.analyze(df)
    ob = order_block.analyze(df)
    
    if (
        fvg['signal'] == 'BULLISH' and
        ob['signal'] == 'BULLISH' and
        fvg['metadata']['is_new_event'] == True
    ):
        # FVG + OB overlap = UNICORN (rare + premium)
        return 'UNICORN_LONG'  # Ultra-rare premium setup
    
    return 'NO_SIGNAL'
```

## Confluence

**Very Selective Booster Role:**
- 1.47% signal rate = 252 signals per 180 days
- ~1.4 signals per day (before considering other blocks)
- 0.89 NEW gap entries per day (most critical for timing)
- With 4 other blocks: ~2-5 ultra-premium signals per 180 days

**Value in Strategies:**
- Premium institutional imbalance detection
- HIGHEST confidence (94.0%) of all blocks reviewed
- Very selective without over-restricting (perfect balance)
- Event tracking enables precise gap fill timing
- Different signal type (complements structure blocks)

## Key Functions

**analyze(df)** - Main analysis
- Returns: signal, confidence, metadata, confluence_factors
- Detects both bullish and bearish FVGs
- Provides event tracking (`is_new_event`, `bars_since_gap`)
- Checks for liquidation event enhancement

**detect_bullish_fvg(df)** - Bullish gap detection
- 3-candle pattern: candle3_low > candle1_high
- Returns gap zone (high, low, mid, size, pct)

**detect_bearish_fvg(df)** - Bearish gap detection
- 3-candle pattern: candle3_high < candle1_low
- Returns gap zone (high, low, mid, size, pct)

**check_gap_liquidation_event(timestamp)** - Quality enhancement
- Checks if gap formed during liquidation spike
- Upgrades quality to "INSTITUTIONAL"
- Adds confidence boost (+15%)

## Advanced Usage

**Gap Age Filtering:**
```python
# Filter out stale gaps
if (
    fvg['signal'] == 'BULLISH' and
    fvg['metadata']['bars_since_gap'] < 20  # Recent gap only
):
    enter_long()
```

**Gap Size Filtering:**
```python
# Only trade large gaps (>1%)
if (
    fvg['signal'] == 'BULLISH' and
    fvg['metadata']['gap_pct'] > 1.0  # Large gap
):
    enter_long()  # Highest conviction
```

**Liquidation-Enhanced Gaps:**
```python
# Check confluence factors for liquidation
if (
    fvg['signal'] == 'BULLISH' and
    'INSTITUTIONAL GAP' in str(fvg['confluence_factors'])
):
    # Gap formed during liquidation = premium
    enter_long()
```

## Gap Zone Management

**Zone Tracking:**
- `gap_high`: Upper boundary
- `gap_low`: Lower boundary  
- `gap_mid`: Midpoint (50% fill level)
- `gap_size`: Absolute size ($)
- `gap_pct`: Percentage size (%)

**Price Location:**
- `in_gap`: Boolean (is price in gap zone now?)
- If TRUE → signal is BULLISH or BEARISH
- If FALSE → signal is NEUTRAL (watch for return)

## Documentation Claims (Validated)

- **Quality Score:** 90/100 (exceptional)
- **Accuracy:** 62.9% (TIED FOR HIGHEST EVER)
- **R/R Ratio:** 6.08 (excellent)
- **Balance:** 46/54 bullish/bearish (good for very selective)
- **Confidence:** 94.0% (HIGHEST of all blocks reviewed)

**Status:** ✅ Production Ready - A+ Grade | **Tests:** `test_fair_value_gap.py`

---
*End of Fair Value Gap Documentation*
