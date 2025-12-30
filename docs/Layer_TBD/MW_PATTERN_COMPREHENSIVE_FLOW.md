# M/W PATTERN - Comprehensive Detection Flow

**Version**: 2.0 (Enhanced for Better Detection)  
**Date**: December 28, 2025  
**Success Rate Target**: 65%+ (from current 66.7% - maintain and increase frequency)

---

## Pattern Overview

### Market Maker Psychology

#### M-Pattern (Double Top - Distribution)

**The Setup**: Smart money distribution pattern where institutions offload positions to retail buyers.

```
Formation:
    Peak1      Peak2
      /\        /\      ← Smart money selling
     /  \      /  \
    /    \    /    \    ← Retail buying the "resistance"
   /      \  /      \
  /        \/        \  ← Neckline (support)
           ↓
     Breakdown ← Retail trapped, smart money profits
```

**Psychology**:
1. **Peak 1**: Initial selling climax
2. **Valley**: Temporary support (smart money pauses)
3. **Peak 2**: Final distribution (less volume = exhaustion)
4. **Neckline Break**: Retail capitulates, smart money completes distribution

#### W-Pattern (Double Bottom - Accumulation)

**The Setup**: Smart money accumulation pattern where institutions build positions from retail sellers.

```
Formation:
           ↑
     Breakout ← Smart money enters with size
  /        /\        \  ← Neckline (resistance)
 /      /    \      /  
/    /        \    /    ← Retail selling the "support"
Trough1      Trough2    ← Smart money accumulating
```

**Psychology**:
1. **Trough 1**: Initial buying (panic selling absorbed)
2. **Peak**: Temporary resistance (smart money pauses)
3. **Trough 2**: Final accumulation (less volume = exhaustion)
4. **Neckline Break**: Retail buys high, smart money profits

---

## Current Detection Problem

**Issue**: Only detecting 13.3% of trades as M/W patterns, should be ~30%

**Root Causes**:
1. Pattern length too restrictive (10-50 bars)
2. Peak tolerance too strict (15%)
3. Not scanning multiple timeframes
4. Missing patterns due to volume requirement

---

## Stage 1: Peak/Trough Detection

### Current Implementation (MISSING PATTERNS)

```python
# ❌ CURRENT (TOO STRICT):
min_len = 10  # Misses 8-9 bar patterns
max_len = 50  # Misses 51-80 bar patterns
peak_tolerance = 0.15  # Misses 16-25% differences
```

### Enhanced Implementation (DETECTS MORE)

```python
def find_peaks_enhanced(data, lookback=80):
    """
    Enhanced peak detection with wider parameters
    
    Args:
        data: OHLCV DataFrame
        lookback: Maximum bars to look back
    
    Returns:
        List of (index, price) tuples for peaks
    """
    highs = data['high'].values
    peaks = []
    
    # Use variable order based on timeframe
    if len(data) < 100:
        order = 2  # Shorter lookback for small datasets
    else:
        order = 3  # Standard lookback
    
    for i in range(order, len(highs) - order):
        # Check if this is a local maximum
        is_peak = True
        
        # Check left side
        for j in range(1, order + 1):
            if highs[i] <= highs[i - j]:
                is_peak = False
                break
        
        # Check right side
        if is_peak:
            for j in range(1, order + 1):
                if highs[i] <= highs[i + j]:
                    is_peak = False
                    break
        
        if is_peak:
            peaks.append((i, highs[i]))
    
    return peaks

def find_troughs_enhanced(data, lookback=80):
    """
    Enhanced trough detection (inverse of peaks)
    """
    lows = data['low'].values
    troughs = []
    
    if len(data) < 100:
        order = 2
    else:
        order = 3
    
    for i in range(order, len(lows) - order):
        is_trough = True
        
        for j in range(1, order + 1):
            if lows[i] >= lows[i - j]:
                is_trough = False
                break
        
        if is_trough:
            for j in range(1, order + 1):
                if lows[i] >= lows[i + j]:
                    is_trough = False
                    break
        
        if is_trough:
            troughs.append((i, lows[i]))
    
    return troughs
```

---

## Stage 2: Peak/Trough Pairing

### Enhanced M-Pattern Detection

```python
def detect_m_pattern_enhanced(data, current_price):
    """
    Enhanced M-pattern detection with wider parameters
    
    Returns:
        PatternData or None
    """
    # ENHANCED PARAMETERS
    MIN_PATTERN_LENGTH = 8   # Down from 10
    MAX_PATTERN_LENGTH = 80  # Up from 50
    PEAK_TOLERANCE = 0.25    # Up from 0.15 (for BTC volatility)
    
    if len(data) < MAX_PATTERN_LENGTH:
        return None
    
    lookback = min(MAX_PATTERN_LENGTH, len(data))
    recent = data.iloc[-lookback:]
    
    # Find all peaks
    peaks = find_peaks_enhanced(recent)
    
    if len(peaks) < 2:
        return None
    
    # Try different peak pairs (most recent first)
    for i in range(len(peaks) - 1, 0, -1):
        peak2_idx, peak2_price = peaks[i]
        peak1_idx, peak1_price = peaks[i - 1]
        
        # ========================================
        # VALIDATION CHECKS
        # ========================================
        
        # CHECK 1: Pattern Length
        pattern_length = peak2_idx - peak1_idx
        
        if pattern_length < MIN_PATTERN_LENGTH:
            continue  # Too short
        
        if pattern_length > MAX_PATTERN_LENGTH:
            continue  # Too long
        
        # CHECK 2: Peak Symmetry (WIDENED)
        price_diff = abs(peak1_price - peak2_price)
        diff_pct = price_diff / max(peak1_price, peak2_price)
        
        if diff_pct > PEAK_TOLERANCE:
            continue  # Peaks too different
        
        # CHECK 3: Valley Depth
        valley_data = recent.iloc[peak1_idx:peak2_idx + 1]
        neckline = valley_data['low'].min()
        
        pattern_height = max(peak1_price, peak2_price) - neckline
        depth_pct = pattern_height / max(peak1_price, peak2_price)
        
        if depth_pct < 0.03:  # Minimum 3% depth
            continue  # Pattern too shallow
        
        if depth_pct > 0.25:  # Maximum 25% depth
            continue  # Pattern too deep (different pattern)
        
        # CHECK 4: Volume Profile (CRITICAL!)
        peak1_vol = recent.iloc[peak1_idx]['volume']
        peak2_vol = recent.iloc[peak2_idx]['volume']
        
        if peak2_vol > peak1_vol * 1.2:
            # Volume INCREASING = accumulation, not distribution!
            logger.debug(f"M-pattern rejected: volume increasing ({peak2_vol:.0f} > {peak1_vol * 1.2:.0f})")
            continue
        
        # CHECK 5: Neckline Break
        break_threshold = 0.003  # 0.3%
        
        if current_price >= neckline * (1 - break_threshold):
            continue  # Hasn't broken neckline yet
        
        # CHECK 6: Breakout Candle Properties
        current_candle = data.iloc[-1]
        
        # Must close below neckline
        if current_candle['close'] >= neckline:
            continue
        
        # CHECK 7: Volume on Breakout (ENHANCED)
        avg_volume = recent['volume'].mean()
        breakout_vol = current_candle['volume']
        
        # Not too high (fake breakout) and not too low (weak break)
        if breakout_vol > avg_volume * 3:
            logger.debug(f"M-pattern: breakout volume too high ({breakout_vol:.0f} > {avg_volume * 3:.0f})")
            continue
        
        if breakout_vol < avg_volume * 0.8:
            logger.debug(f"M-pattern: breakout volume too low ({breakout_vol:.0f} < {avg_volume * 0.8:.0f})")
            continue
        
        # CHECK 8: Trend Context
        if len(data) >= 50:
            sma_50 = data['close'].rolling(50).mean().iloc[-1]
            
            if current_price > sma_50 * 1.05:
                # Strong uptrend - risky counter-trend short
                logger.debug(f"M-pattern: strong uptrend (price={current_price:.2f}, sma50={sma_50:.2f})")
                confidence_adjustment = 0.5
            else:
                confidence_adjustment = 1.0
        else:
            confidence_adjustment = 1.0
        
        # ✅ PATTERN VALIDATED!
        logger.info(f"M-PATTERN DETECTED:")
        logger.info(f"  Peak1: ${peak1_price:.2f} (idx={peak1_idx})")
        logger.info(f"  Peak2: ${peak2_price:.2f} (idx={peak2_idx})")
        logger.info(f"  Neckline: ${neckline:.2f}")
        logger.info(f"  Pattern length: {pattern_length} bars")
        logger.info(f"  Peak difference: {diff_pct * 100:.1f}%")
        
        # Don't enter immediately - wait for retest or confirmation
        return store_pending_m_pattern(
            peak1_idx, peak1_price, peak1_vol,
            peak2_idx, peak2_price, peak2_vol,
            neckline, pattern_height,
            confidence_adjustment
        )
    
    return None
```

### Enhanced W-Pattern Detection

```python
def detect_w_pattern_enhanced(data, current_price):
    """
    Enhanced W-pattern detection (mirror of M-pattern)
    
    Returns:
        PatternData or None
    """
    MIN_PATTERN_LENGTH = 8
    MAX_PATTERN_LENGTH = 80
    TROUGH_TOLERANCE = 0.25
    
    if len(data) < MAX_PATTERN_LENGTH:
        return None
    
    lookback = min(MAX_PATTERN_LENGTH, len(data))
    recent = data.iloc[-lookback:]
    
    # Find all troughs
    troughs = find_troughs_enhanced(recent)
    
    if len(troughs) < 2:
        return None
    
    # Try different trough pairs
    for i in range(len(troughs) - 1, 0, -1):
        trough2_idx, trough2_price = troughs[i]
        trough1_idx, trough1_price = troughs[i - 1]
        
        # CHECK 1: Pattern Length
        pattern_length = trough2_idx - trough1_idx
        
        if pattern_length < MIN_PATTERN_LENGTH or pattern_length > MAX_PATTERN_LENGTH:
            continue
        
        # CHECK 2: Trough Symmetry
        price_diff = abs(trough1_price - trough2_price)
        diff_pct = price_diff / min(trough1_price, trough2_price)
        
        if diff_pct > TROUGH_TOLERANCE:
            continue
        
        # CHECK 3: Peak Between Troughs (Neckline)
        peak_data = recent.iloc[trough1_idx:trough2_idx + 1]
        neckline = peak_data['high'].max()
        
        pattern_height = neckline - min(trough1_price, trough2_price)
        depth_pct = pattern_height / neckline
        
        if depth_pct < 0.03 or depth_pct > 0.25:
            continue
        
        # CHECK 4: Volume Profile (accumulation check)
        trough1_vol = recent.iloc[trough1_idx]['volume']
        trough2_vol = recent.iloc[trough2_idx]['volume']
        
        # For accumulation, volume should DECLINE at trough2
        if trough2_vol > trough1_vol * 1.2:
            logger.debug(f"W-pattern rejected: volume increasing at trough2")
            continue
        
        # CHECK 5: Neckline Break
        break_threshold = 0.003
        
        if current_price <= neckline * (1 + break_threshold):
            continue  # Hasn't broken neckline yet
        
        # CHECK 6: Breakout Properties
        current_candle = data.iloc[-1]
        
        if current_candle['close'] <= neckline:
            continue
        
        # CHECK 7: Volume on Breakout
        avg_volume = recent['volume'].mean()
        breakout_vol = current_candle['volume']
        
        if breakout_vol > avg_volume * 3 or breakout_vol < avg_volume * 0.8:
            continue
        
        # CHECK 8: Trend Context
        if len(data) >= 50:
            sma_50 = data['close'].rolling(50).mean().iloc[-1]
            
            if current_price < sma_50 * 0.95:
                # Strong downtrend - risky counter-trend long
                confidence_adjustment = 0.5
            else:
                confidence_adjustment = 1.0
        else:
            confidence_adjustment = 1.0
        
        # ✅ PATTERN VALIDATED!
        logger.info(f"W-PATTERN DETECTED:")
        logger.info(f"  Trough1: ${trough1_price:.2f}")
        logger.info(f"  Trough2: ${trough2_price:.2f}")
        logger.info(f"  Neckline: ${neckline:.2f}")
        logger.info(f"  Pattern length: {pattern_length} bars")
        
        return store_pending_w_pattern(
            trough1_idx, trough1_price, trough1_vol,
            trough2_idx, trough2_price, trough2_vol,
            neckline, pattern_height,
            confidence_adjustment
        )
    
    return None
```

---

## Stage 3: Retest Handling (CRITICAL!)

### The Retest Phenomenon

**Statistical Fact**: 60-70% of M/W patterns retest the neckline before continuing!

**Current Problem**: Entering on initial break, then stopping out on retest.

### Enhanced Entry Logic with Retest

```python
class MWPatternTracker:
    """
    Track M/W patterns and handle retests
    """
    
    def __init__(self):
        self.pending_patterns = []
        self.retest_windows = {}
    
    def check_for_retest_entry(self, data, current_price):
        """
        Check if any pending patterns are getting retested
        
        This provides BETTER entry than initial break!
        """
        if not self.pending_patterns:
            return None
        
        current_candle = data.iloc[-1]
        
        for pattern in self.pending_patterns:
            if pattern['type'] == 'M':
                # M-pattern retest logic
                neckline = pattern['neckline']
                
                # Has it retested?
                if neckline * 0.99 <= current_price <= neckline * 1.01:
                    # At neckline ±1%
                    
                    # Check for rejection
                    candle_range = current_candle['high'] - current_candle['low']
                    if candle_range == 0:
                        continue
                    
                    # For SHORT: need upper wick rejection
                    upper_wick = current_candle['high'] - current_candle['close']
                    wick_ratio = upper_wick / candle_range
                    
                    if wick_ratio > 0.5:  # 50%+ rejection wick
                        if current_candle['close'] < neckline:
                            # ✅ RETEST REJECTION! Best entry!
                            logger.info(f"M-PATTERN RETEST ENTRY at ${current_price:.2f}")
                            return create_m_pattern_position(
                                data, current_price, pattern,
                                entry_type='retest'  # Better entry
                            )
            
            elif pattern['type'] == 'W':
                # W-pattern retest logic
                neckline = pattern['neckline']
                
                if neckline * 0.99 <= current_price <= neckline * 1.01:
                    candle_range = current_candle['high'] - current_candle['low']
                    if candle_range == 0:
                        continue
                    
                    # For LONG: need lower wick rejection
                    lower_wick = current_candle['close'] - current_candle['low']
                    wick_ratio = lower_wick / candle_range
                    
                    if wick_ratio > 0.5:
                        if current_candle['close'] > neckline:
                            # ✅ RETEST REJECTION!
                            logger.info(f"W-PATTERN RETEST ENTRY at ${current_price:.2f}")
                            return create_w_pattern_position(
                                data, current_price, pattern,
                                entry_type='retest'
                            )
        
        # Check if any patterns have strong continuation (no retest)
        return self.check_for_strong_continuation(data, current_price)
    
    def check_for_strong_continuation(self, data, current_price):
        """
        If no retest after 10 bars and strong move, enter on continuation
        """
        for pattern in self.pending_patterns:
            bars_since_break = len(data) - pattern['break_bar']
            
            if bars_since_break < 10:
                continue  # Too early, still waiting for retest
            
            if bars_since_break > 20:
                # Pattern expired
                self.pending_patterns.remove(pattern)
                continue
            
            # Check if strong move (no retest = strong pattern)
            if pattern['type'] == 'M':
                neckline = pattern['neckline']
                
                if current_price < neckline * 0.995:  # 0.5% below
                    # Strong bearish continuation
                    logger.info(f"M-PATTERN STRONG CONTINUATION at ${current_price:.2f}")
                    return create_m_pattern_position(
                        data, current_price, pattern,
                        entry_type='continuation'
                    )
            
            elif pattern['type'] == 'W':
                neckline = pattern['neckline']
                
                if current_price > neckline * 1.005:
                    logger.info(f"W-PATTERN STRONG CONTINUATION at ${current_price:.2f}")
                    return create_w_pattern_position(
                        data, current_price, pattern,
                        entry_type='continuation'
                    )
        
        return None

def create_m_pattern_position(data, current_price, pattern, entry_type='initial'):
    """
    Create M-pattern SHORT position
    
    Args:
        entry_type: 'initial', 'retest', or 'continuation'
    """
    entry_price = current_price
    atr = get_atr(data)
    
    pattern_height = pattern['pattern_height']
    neckline = pattern['neckline']
    peak_high = max(pattern['peak1_price'], pattern['peak2_price'])
    
    # Stop placement depends on entry type
    if entry_type == 'retest':
        # Tighter stop (below neckline instead of above peaks)
        stop_loss = neckline + (atr * 1.0)
    else:
        # Wider stop (above peaks)
        stop_loss = peak_high + (atr * 1.5)
    
    # Targets based on pattern height
    tp1 = neckline - (pattern_height * 0.5)
    tp2 = neckline - (pattern_height * 1.0)
    tp3 = neckline - (pattern_height * 1.5)
    
    # Calculate R:R
    risk = stop_loss - entry_price
    reward1 = entry_price - tp1
    rr1 = reward1 / risk if risk > 0 else 0
    
    logger.info(f"M-PATTERN SHORT ({entry_type.upper()}):")
    logger.info(f"  Entry: ${entry_price:.2f}")
    logger.info(f"  Stop:  ${stop_loss:.2f} (Risk: ${risk:.2f})")
    logger.info(f"  TP1:   ${tp1:.2f} (R:R = {rr1:.2f}:1)")
    logger.info(f"  TP2:   ${tp2:.2f}")
    logger.info(f"  TP3:   ${tp3:.2f}")
    
    confidence = pattern['base_confidence'] * pattern['trend_adjustment']
    if entry_type == 'retest':
        confidence *= 1.2  # Boost for retest entry (better)
    
    return PatternData(
        pattern_type=PatternType.M_PATTERN,
        timeframe=get_timeframe(data),
        confidence=confidence,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit_1=tp1,
        take_profit_2=tp2,
        take_profit_3=tp3,
        direction='short',
        neckline=neckline,
        peak1=pattern['peak1_price'],
        peak2=pattern['peak2_price'],
        pattern_height=pattern_height,
        metadata={
            'entry_type': entry_type,
            'pattern_length': pattern['pattern_length'],
            'peak_symmetry': pattern['peak_diff_pct'],
            'risk_reward_tp1': rr1
        }
    )

def create_w_pattern_position(data, current_price, pattern, entry_type='initial'):
    """
    Create W-pattern LONG position (mirror of M-pattern)
    """
    entry_price = current_price
    atr = get_atr(data)
    
    pattern_height = pattern['pattern_height']
    neckline = pattern['neckline']
    trough_low = min(pattern['trough1_price'], pattern['trough2_price'])
    
    # Stop placement
    if entry_type == 'retest':
        stop_loss = neckline - (atr * 1.0)  # Tighter
    else:
        stop_loss = trough_low - (atr * 1.5)  # Wider
    
    # Targets
    tp1 = neckline + (pattern_height * 0.5)
    tp2 = neckline + (pattern_height * 1.0)
    tp3 = neckline + (pattern_height * 1.5)
    
    risk = entry_price - stop_loss
    reward1 = tp1 - entry_price
    rr1 = reward1 / risk if risk > 0 else 0
    
    logger.info(f"W-PATTERN LONG ({entry_type.upper()}):")
    logger.info(f"  Entry: ${entry_price:.2f}")
    logger.info(f"  Stop:  ${stop_loss:.2f}")
    logger.info(f"  TP1:   ${tp1:.2f} (R:R = {rr1:.2f}:1)")
    
    confidence = pattern['base_confidence'] * pattern['trend_adjustment']
    if entry_type == 'retest':
        confidence *= 1.2
    
    return PatternData(
        pattern_type=PatternType.W_PATTERN,
        timeframe=get_timeframe(data),
        confidence=confidence,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit_1=tp1,
        take_profit_2=tp2,
        take_profit_3=tp3,
        direction='long',
        neckline=neckline,
        peak1=pattern['trough1_price'],
        peak2=pattern['trough2_price'],
        pattern_height=pattern_height,
        metadata={
            'entry_type': entry_type,
            'pattern_length': pattern['pattern_length'],
            'risk_reward_tp1': rr1
        }
    )
```

---

## Stage 4: Multi-Timeframe Scanning

### Why Multi-TF Matters

**Problem**: Only scanning current timeframe misses higher-TF patterns

**Solution**: Scan 15m, 1H, and 4H simultaneously

```python
def scan_multiple_timeframes(symbol, current_time):
    """
    Scan multiple timeframes for M/W patterns
    
    Priority: 4H > 1H > 15m (higher TF = more reliable)
    """
    timeframes = ['4H', '1H', '15m']
    patterns_found = []
    
    for tf in timeframes:
        data = load_data(symbol, tf, lookback=100)
        current_price = data.iloc[-1]['close']
        
        # Check M-pattern
        m_pattern = detect_m_pattern_enhanced(data, current_price)
        if m_pattern:
            m_pattern.metadata['scan_timeframe'] = tf
            m_pattern.confidence *= get_timeframe_multiplier(tf)
            patterns_found.append(m_pattern)
        
        # Check W-pattern
        w_pattern = detect_w_pattern_enhanced(data, current_price)
        if w_pattern:
            w_pattern.metadata['scan_timeframe'] = tf
            w_pattern.confidence *= get_timeframe_multiplier(tf)
            patterns_found.append(w_pattern)
    
    # Return highest confidence pattern
    if patterns_found:
        best_pattern = max(patterns_found, key=lambda p: p.confidence)
        logger.info(f"Best M/W pattern found on {best_pattern.metadata['scan_timeframe']} TF")
        return best_pattern
    
    return None

def get_timeframe_multiplier(tf):
    """
    Confidence multiplier based on timeframe
    
    Higher timeframes = more reliable patterns
    """
    multipliers = {
        '4H': 1.3,   # 30% boost
        '1H': 1.15,  # 15% boost
        '15m': 1.0   # No boost
    }
    return multipliers.get(tf, 1.0)
```

---

## Stage 5: Trade Management

### Pattern Invalidation for M/W

```python
def monitor_mw_pattern_trade(data, position):
    """
    Monitor M/W pattern trade with pattern-specific rules
    """
    current_candle = data.iloc[-1]
    current_price = current_candle['close']
    
    # Standard checks (stop, TPs) same as three_hits
    # ...
    
    # M/W SPECIFIC: Re-entry above/below neckline
    neckline = position['neckline']
    entry_price = position['entry_price']
    
    if position['pattern_type'] == 'M_PATTERN':
        # SHORT position
        
        # If price breaks back ABOVE neckline = pattern failed
        if current_price > neckline * 1.01:
            logger.warn("M-pattern invalidated: price back above neckline")
            return {'action': 'EXIT', 'reason': 'pattern_change', 'pct': 100}
        
        # If new higher high forms = trend changed
        if current_candle['high'] > max(position['peak1'], position['peak2']):
            logger.warn("M-pattern invalidated: new higher high")
            return {'action': 'EXIT', 'reason': 'pattern_change', 'pct': 100}
    
    elif position['pattern_type'] == 'W_PATTERN':
        # LONG position
        
        # If price breaks back BELOW neckline = pattern failed
        if current_price < neckline * 0.99:
            logger.warn("W-pattern invalidated: price back below neckline")
            return {'action': 'EXIT', 'reason': 'pattern_change', 'pct': 100}
        
        # If new lower low forms = trend changed
        if current_candle['low'] < min(position['trough1'], position['trough2']):
            logger.warn("W-pattern invalidated: new lower low")
            return {'action': 'EXIT', 'reason': 'pattern_change', 'pct': 100}
    
    # Continue holding
    return {'action': 'HOLD'}
```

---

## Configuration Changes Required

```python
# IN config/base_config.py or TBDConfig:

# CURRENT (TOO STRICT):
mw_pattern_length_min: int = 10
mw_pattern_length_max: int = 50
mw_peak_tolerance: float = 0.15

# ENHANCED (DETECTS MORE):
mw_pattern_length_min: int = 8     # Allow faster formations
mw_pattern_length_max: int = 80    # Allow slower formations
mw_peak_tolerance: float = 0.25    # Allow wider symmetry (BTC volatility)

# NEW PARAMETERS:
mw_enable_retest_entry: bool = True      # Better entry timing
mw_retest_window_bars: int = 20          # Max bars to wait for retest
mw_enable_multi_tf_scan: bool = True     # Scan 15m/1H/4H
mw_min_pattern_depth: float = 0.03       # Min 3% pattern height
mw_max_pattern_depth: float = 0.25       # Max 25% pattern height
mw_volume_breakout_min: float = 0.8      # Min breakout volume (vs avg)
mw_volume_breakout_max: float = 3.0      # Max breakout volume (vs avg)
```

---

## Expected Performance Improvement

### Before Enhancements
- **Frequency**: 13.3% of trades
- **Win Rate**: 66.7% (already good!)
- **Problem**: Missing patterns (low frequency)

### After Enhancements (Projected)
- **Frequency**: 30-35% of trades ✅ (2.5x increase!)
- **Win Rate**: 65-70% ✅ (maintain quality)
- **R:R**: 1.5:1 to 2.5:1

### Impact
- **More Trades**: 2-3 good M/W setups per week (from 0-1)
- **Better Entries**: Retest entries improve R:R by 30%
- **Higher Confidence**: 4H patterns more reliable than 15m

---

## Common Failure Modes & Solutions

### Failure Mode #1: Entering Too Early (Before Retest)
**Solution**: ✅ Wait for retest or strong continuation

### Failure Mode #2: Missing Patterns (Too Strict)
**Solution**: ✅ Widen length (8-80) and tolerance (25%)

### Failure Mode #3: False M-Patterns (Actually Accumulation)
**Solution**: ✅ Check volume profile (peak2 < peak1)

### Failure Mode #4: Counter-Trend Risk
**Solution**: ✅ Check SMA-50, reduce confidence if against trend

### Failure Mode #5: Missing Higher-TF Patterns
**Solution**: ✅ Multi-timeframe scanning

---

**Implementation Priority**: HIGH (Need to increase M/W frequency)  
**Expected Impact**: 2.5x more M/W patterns detected  
**Maintain Quality**: 65-70% win rate target

---

*Document Version: 2.0*  
*Last Updated: December 28, 2025*
