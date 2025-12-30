# TRAPPING VOLUME PATTERN - Comprehensive Detection Flow

**Version**: 2.0 (Enhanced Detection with Strict Validation)  
**Date**: December 28, 2025  
**Success Rate Target**: 55%+ (from current 37.5%)

---

## Pattern Overview

### Market Maker Psychology

**The Setup**: Large wicks with volume spikes designed to trap retail traders on the wrong side.

#### Bullish Trap (Enter SHORT)
```
High
  |
  |────────  Upper wick (60%+ of candle)
  |         Large volume spike
  █  Body   Retail buying "breakout"
  |         Smart money selling
Low ────────
```

**Psychology**:
1. Price spikes UP with huge volume
2. Retail sees "breakout" and buys
3. Smart money dumps inventory into retail buying
4. Price reverses DOWN (retail trapped)

#### Bearish Trap (Enter LONG)
```
High ────────
  |         Smart money buying
  █  Body   Retail selling "breakdown"
  |         Large volume spike
  |────────  Lower wick (60%+ of candle)
  |
Low
```

**Psychology**:
1. Price spikes DOWN with huge volume
2. Retail panics and sells
3. Smart money absorbs retail selling
4. Price reverses UP (retail trapped)

---

## Current Detection Problem

**Issue**: 62.5% loss rate - too many false traps detected!

**Root Causes**:
1. Wick threshold too low (50% vs 60% needed)
2. Volume threshold too low (1.5x vs 2x needed)
3. No body size check (allows large body candles)
4. No context validation (level proximity, trend)
5. No confirmation bar requirement
6. Holding too long (should be scalp < 4 hours)

---

## Stage 1: Wick Detection (Every Candle)

### Current Implementation (TOO LENIENT)

```python
# ❌ CURRENT (ACCEPTS TOO MUCH):
wick_ratio > 0.5       # 50% wick
volume > avg * 1.5     # 150% volume
# No other checks!
```

**Problem**: Catches many non-traps (real breakouts/breakdowns)

### Enhanced Implementation (STRICT)

```python
def detect_wick_trap_enhanced(candle, data):
    """
    Enhanced trap detection with strict validation
    
    Args:
        candle: Current OHLC candle
        data: Recent price history
    
    Returns:
        dict with trap info or None
    """
    # Calculate candle components
    candle_open = candle['open']
    candle_close = candle['close']
    candle_high = candle['high']
    candle_low = candle['low']
    candle_volume = candle['volume']
    
    candle_range = candle_high - candle_low
    if candle_range == 0:
        return None
    
    # Calculate wicks and body
    upper_wick = candle_high - max(candle_open, candle_close)
    lower_wick = min(candle_open, candle_close) - candle_low
    body = abs(candle_close - candle_open)
    
    # Calculate ratios
    upper_wick_ratio = upper_wick / candle_range
    lower_wick_ratio = lower_wick / candle_range
    body_ratio = body / candle_range
    
    # ========================================
    # BULLISH TRAP DETECTION (Enter SHORT)
    # ========================================
    
    if upper_wick_ratio >= 0.6:  # ✅ STRICTER: 60% minimum (was 50%)
        
        # CHECK 1: Small body (trap characteristic)
        if body_ratio > 0.3:
            # Body too large - this is a strong bullish candle
            # Not a trap, likely real buying
            return None
        
        # CHECK 2: Close position (must close near low)
        close_position = (candle_close - candle_low) / candle_range
        if close_position > 0.4:
            # Closed above 40% of range
            # Too strong, not a trap
            return None
        
        # CHECK 3: Volume spike (STRICTER)
        avg_volume = data['volume'].rolling(20).mean().iloc[-2]  # Exclude current
        volume_ratio = candle_volume / avg_volume
        
        if volume_ratio < 2.0:  # ✅ STRICTER: 2x minimum (was 1.5x)
            # Volume not high enough
            return None
        
        if volume_ratio > 5.0:
            # TOO much volume - might be genuine breakout
            # Institutions entering with size
            return None
        
        # CHECK 4: Context - at resistance level?
        resistance_levels = find_recent_resistance(data)
        at_resistance = False
        
        for level in resistance_levels:
            if abs(candle_high - level) / level < 0.01:  # Within 1%
                at_resistance = True
                break
        
        if not at_resistance:
            # Trap should happen AT levels
            # Random wicks don't count
            return None
        
        # CHECK 5: Recent trend (should be uptrend for bullish trap)
        recent_closes = data['close'].iloc[-10:]
        sma_10 = recent_closes.mean()
        
        if candle_close < sma_10 * 0.98:
            # Already in downtrend
            # This is continuation, not trap
            return None
        
        # ✅ BULLISH TRAP DETECTED
        logger.info(f"BULLISH TRAP DETECTED:")
        logger.info(f"  Upper wick: {upper_wick_ratio * 100:.1f}% of candle")
        logger.info(f"  Body: {body_ratio * 100:.1f}% of candle")
        logger.info(f"  Close position: {close_position * 100:.1f}%")
        logger.info(f"  Volume: {volume_ratio:.1f}x average")
        logger.info(f"  At resistance: ${resistance_levels[0]:.2f}")
        
        return {
            'type': 'bullish_trap',
            'direction': 'short',
            'wick_ratio': upper_wick_ratio,
            'body_ratio': body_ratio,
            'close_position': close_position,
            'volume_ratio': volume_ratio,
            'at_level': resistance_levels[0] if resistance_levels else None,
            'trap_candle': candle.copy()
        }
    
    # ========================================
    # BEARISH TRAP DETECTION (Enter LONG)
    # ========================================
    
    elif lower_wick_ratio >= 0.6:  # ✅ STRICTER: 60% minimum
        
        # CHECK 1: Small body
        if body_ratio > 0.3:
            return None
        
        # CHECK 2: Close position (must close near high)
        close_position = (candle_close - candle_low) / candle_range
        if close_position < 0.6:
            # Closed below 60% of range
            # Too weak, not a trap
            return None
        
        # CHECK 3: Volume spike
        avg_volume = data['volume'].rolling(20).mean().iloc[-2]
        volume_ratio = candle_volume / avg_volume
        
        if volume_ratio < 2.0 or volume_ratio > 5.0:
            return None
        
        # CHECK 4: Context - at support level?
        support_levels = find_recent_support(data)
        at_support = False
        
        for level in support_levels:
            if abs(candle_low - level) / level < 0.01:
                at_support = True
                break
        
        if not at_support:
            return None
        
        # CHECK 5: Recent trend (should be downtrend for bearish trap)
        recent_closes = data['close'].iloc[-10:]
        sma_10 = recent_closes.mean()
        
        if candle_close > sma_10 * 1.02:
            # Already in uptrend
            # This is continuation, not trap
            return None
        
        # ✅ BEARISH TRAP DETECTED
        logger.info(f"BEARISH TRAP DETECTED:")
        logger.info(f"  Lower wick: {lower_wick_ratio * 100:.1f}% of candle")
        logger.info(f"  Body: {body_ratio * 100:.1f}% of candle")
        logger.info(f"  Close position: {close_position * 100:.1f}%")
        logger.info(f"  Volume: {volume_ratio:.1f}x average")
        logger.info(f"  At support: ${support_levels[0]:.2f}")
        
        return {
            'type': 'bearish_trap',
            'direction': 'long',
            'wick_ratio': lower_wick_ratio,
            'body_ratio': body_ratio,
            'close_position': close_position,
            'volume_ratio': volume_ratio,
            'at_level': support_levels[0] if support_levels else None,
            'trap_candle': candle.copy()
        }
    
    return None

def find_recent_resistance(data, lookback=50):
    """Find recent resistance levels"""
    highs = data['high'].iloc[-lookback:]
    
    # Find local maxima
    resistances = []
    for i in range(3, len(highs) - 3):
        is_peak = True
        for j in range(1, 4):
            if highs.iloc[i] <= highs.iloc[i-j] or highs.iloc[i] <= highs.iloc[i+j]:
                is_peak = False
                break
        if is_peak:
            resistances.append(highs.iloc[i])
    
    # Return top 3 most recent
    return sorted(resistances, reverse=True)[:3]

def find_recent_support(data, lookback=50):
    """Find recent support levels"""
    lows = data['low'].iloc[-lookback:]
    
    # Find local minima
    supports = []
    for i in range(3, len(lows) - 3):
        is_trough = True
        for j in range(1, 4):
            if lows.iloc[i] >= lows.iloc[i-j] or lows.iloc[i] >= lows.iloc[i+j]:
                is_trough = False
                break
        if is_trough:
            supports.append(lows.iloc[i])
    
    # Return bottom 3 most recent
    return sorted(supports)[:3]
```

**Key Enhancements**:
1. ✅ Wick threshold increased (60% vs 50%)
2. ✅ Volume threshold increased (2x vs 1.5x)
3. ✅ Body size check added (<30%)
4. ✅ Close position check added
5. ✅ Level proximity check added
6. ✅ Trend context check added
7. ✅ Volume spike bounds (not > 5x)

---

## Stage 2: Confirmation Bar (CRITICAL!)

### The Missing Piece

**Problem**: Current system enters immediately on trap candle. But price often returns to level (not a real trap)!

**Solution**: Wait for NEXT bar to confirm reversal.

```python
class TrappingVolumeTracker:
    """
    Track trap setups and wait for confirmation
    """
    
    def __init__(self):
        self.pending_traps = {}
    
    def check_trap_confirmation(self, data, current_price):
        """
        Check if pending trap gets confirmed
        
        Returns:
            PatternData or None
        """
        if not self.pending_traps:
            return None
        
        current_candle = data.iloc[-1]
        
        for trap_id, trap in list(self.pending_traps.items()):
            # How long since trap?
            bars_since = len(data) - trap['detected_bar']
            
            if bars_since > 3:
                # Expired (no confirmation in 3 bars = not a trap)
                logger.debug(f"Trap {trap_id} expired")
                del self.pending_traps[trap_id]
                continue
            
            if bars_since == 0:
                continue  # Same bar, wait for next
            
            trap_candle = trap['trap_candle']
            
            # ========================================
            # BULLISH TRAP CONFIRMATION (SHORT)
            # ========================================
            
            if trap['direction'] == 'short':
                
                # CHECK 1: Price moved DOWN from trap
                if current_candle['close'] < trap_candle['close']:
                    
                    # CHECK 2: Broke below trap candle low
                    if current_candle['low'] < trap_candle['low']:
                        
                        # CHECK 3: Closing in lower half
                        conf_range = current_candle['high'] - current_candle['low']
                        if conf_range > 0:
                            close_pos = (current_candle['close'] - current_candle['low']) / conf_range
                            
                            if close_pos < 0.5:
                                
                                # CHECK 4: Volume moderate (not spike)
                                avg_vol = data['volume'].iloc[-20:-1].mean()
                                if current_candle['volume'] < avg_vol * 2:
                                    
                                    # ✅ TRAP CONFIRMED!
                                    logger.info(f"BULLISH TRAP CONFIRMED - Entering SHORT")
                                    del self.pending_traps[trap_id]
                                    return create_trap_short(data, current_price, trap)
            
            # ========================================
            # BEARISH TRAP CONFIRMATION (LONG)
            # ========================================
            
            elif trap['direction'] == 'long':
                
                # CHECK 1: Price moved UP from trap
                if current_candle['close'] > trap_candle['close']:
                    
                    # CHECK 2: Broke above trap candle high
                    if current_candle['high'] > trap_candle['high']:
                        
                        # CHECK 3: Closing in upper half
                        conf_range = current_candle['high'] - current_candle['low']
                        if conf_range > 0:
                            close_pos = (current_candle['close'] - current_candle['low']) / conf_range
                            
                            if close_pos > 0.5:
                                
                                # CHECK 4: Volume moderate
                                avg_vol = data['volume'].iloc[-20:-1].mean()
                                if current_candle['volume'] < avg_vol * 2:
                                    
                                    # ✅ TRAP CONFIRMED!
                                    logger.info(f"BEARISH TRAP CONFIRMED - Entering LONG")
                                    del self.pending_traps[trap_id]
                                    return create_trap_long(data, current_price, trap)
        
        return None

def create_trap_short(data, current_price, trap):
    """
    Create SHORT position for confirmed bullish trap
    
    IMPORTANT: Trap trades are SCALPS (short hold times!)
    """
    entry_price = current_price
    atr = get_atr(data)
    trap_candle = trap['trap_candle']
    
    # TIGHT stop (just above trap high)
    stop_loss = trap_candle['high'] + (atr * 0.5)  # ✅ 0.5x ATR (vs 1.5x for three_hits)
    
    # Targets based on trap candle range
    trap_range = trap_candle['high'] - trap_candle['low']
    
    tp1 = entry_price - (trap_range * 0.5)
    tp2 = entry_price - (trap_range * 1.0)
    tp3 = entry_price - (trap_range * 1.5)
    
    # Calculate R:R
    risk = stop_loss - entry_price
    reward1 = entry_price - tp1
    rr1 = reward1 / risk if risk > 0 else 0
    
    logger.info(f"TRAPPING VOLUME SHORT:")
    logger.info(f"  Entry: ${entry_price:.2f}")
    logger.info(f"  Stop:  ${stop_loss:.2f} (TIGHT! Risk: ${risk:.2f})")
    logger.info(f"  TP1:   ${tp1:.2f} (R:R = {rr1:.2f}:1)")
    logger.info(f"  TP2:   ${tp2:.2f}")
    logger.info(f"  TP3:   ${tp3:.2f}")
    logger.info(f"  MAX HOLD: 4 hours (SCALP!)")
    
    return PatternData(
        pattern_type=PatternType.TRAPPING_VOLUME,
        timeframe=get_timeframe(data),
        confidence=0.65,  # Moderate confidence
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit_1=tp1,
        take_profit_2=tp2,
        take_profit_3=tp3,
        direction='short',
        metadata={
            'trap_type': 'bullish_trap',
            'trap_high': trap_candle['high'],
            'trap_low': trap_candle['low'],
            'trap_range': trap_range,
            'wick_ratio': trap['wick_ratio'],
            'volume_ratio': trap['volume_ratio'],
            'max_hold_hours': 4,  # SCALP!
            'risk_reward_tp1': rr1
        }
    )

def create_trap_long(data, current_price, trap):
    """
    Create LONG position for confirmed bearish trap
    """
    entry_price = current_price
    atr = get_atr(data)
    trap_candle = trap['trap_candle']
    
    # TIGHT stop (just below trap low)
    stop_loss = trap_candle['low'] - (atr * 0.5)
    
    # Targets based on trap range
    trap_range = trap_candle['high'] - trap_candle['low']
    
    tp1 = entry_price + (trap_range * 0.5)
    tp2 = entry_price + (trap_range * 1.0)
    tp3 = entry_price + (trap_range * 1.5)
    
    risk = entry_price - stop_loss
    reward1 = tp1 - entry_price
    rr1 = reward1 / risk if risk > 0 else 0
    
    logger.info(f"TRAPPING VOLUME LONG:")
    logger.info(f"  Entry: ${entry_price:.2f}")
    logger.info(f"  Stop:  ${stop_loss:.2f} (TIGHT!)")
    logger.info(f"  TP1:   ${tp1:.2f} (R:R = {rr1:.2f}:1)")
    logger.info(f"  MAX HOLD: 4 hours")
    
    return PatternData(
        pattern_type=PatternType.TRAPPING_VOLUME,
        timeframe=get_timeframe(data),
        confidence=0.65,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit_1=tp1,
        take_profit_2=tp2,
        take_profit_3=tp3,
        direction='long',
        metadata={
            'trap_type': 'bearish_trap',
            'trap_high': trap_candle['high'],
            'trap_low': trap_candle['low'],
            'trap_range': trap_range,
            'wick_ratio': trap['wick_ratio'],
            'volume_ratio': trap['volume_ratio'],
            'max_hold_hours': 4,
            'risk_reward_tp1': rr1
        }
    )
```

---

## Stage 3: Trade Management (FAST EXITS!)

### Critical Difference: Trap Trades Are SCALPS

**Problem**: Holding trap trades too long (like three_hits patterns)

**Solution**: FAST exits (4 hours maximum)

```python
def monitor_trap_trade(data, position):
    """
    Monitor trap trade with AGGRESSIVE exit management
    
    Trap trades are SCALPS - get in, get out!
    """
    current_candle = data.iloc[-1]
    current_price = current_candle['close']
    entry_time = position['entry_time']
    current_time = current_candle.name
    
    # Calculate hold time in hours
    hold_hours = (current_time - entry_time).total_seconds() / 3600
    
    # PRIORITY 1: Stop Loss (tight!)
    if position['direction'] == 'short':
        if current_price >= position['stop_loss']:
            return {'action': 'EXIT', 'reason': 'stop_loss', 'pct': 100}
    else:
        if current_price <= position['stop_loss']:
            return {'action': 'EXIT', 'reason': 'stop_loss', 'pct': 100}
    
    # PRIORITY 2: TP Hits
    # ... (same as other patterns)
    
    # PRIORITY 3: Price returns to trap level (pattern failed!)
    trap_high = position['metadata']['trap_high']
    trap_low = position['metadata']['trap_low']
    
    if position['direction'] == 'short':
        # If price returns to trap high = failed trap
        if current_price >= trap_high * 0.99:
            logger.warn("Trap failed: price returned to trap high")
            return {'action': 'EXIT', 'reason': 'pattern_change', 'pct': 100}
    else:
        # If price returns to trap low = failed trap
        if current_price <= trap_low * 1.01:
            logger.warn("Trap failed: price returned to trap low")
            return {'action': 'EXIT', 'reason': 'pattern_change', 'pct': 100}
    
    # PRIORITY 4: TIME LIMIT (CRITICAL FOR TRAPS!)
    MAX_HOLD_HOURS = 4  # ✅ Much shorter than three_hits (96 bars)
    
    if hold_hours >= MAX_HOLD_HOURS:
        logger.info(f"Trap trade time limit ({MAX_HOLD_HOURS}h) - taking profit/loss")
        return {'action': 'EXIT', 'reason': 'time_exit', 'pct': 100}
    
    # PRIORITY 5: Approaching time limit with profit
    if hold_hours >= MAX_HOLD_HOURS * 0.75:  # 3 hours (75% of max)
        # Calculate current P&L
        if position['direction'] == 'short':
            pnl = position['entry_price'] - current_price
        else:
            pnl = current_price - position['entry_price']
        
        if pnl > 0:
            # In profit and approaching time limit
            logger.info("Trap trade: securing profit before time limit")
            return {'action': 'EXIT', 'reason': 'time_exit', 'pct': 100}
    
    # Continue holding
    return {'action': 'HOLD'}
```

**Key Differences from Three_Hits**:
1. ✅ Tighter stop (0.5x ATR vs 1.5x)
2. ✅ Shorter hold time (4 hours vs 4 days)
3. ✅ Exit if price returns to trap level
4. ✅ Take profit at 75% of time limit
5. ✅ More aggressive exits overall

---

## Buying/Selling Pressure Validation

### Advanced CVD Check (If Available)

```python
def check_accumulation_distribution(data, trap_type):
    """
    Check if trap is real using cumulative volume delta
    
    Args:
        data: Recent OHLCV data
        trap_type: 'bullish_trap' or 'bearish_trap'
    
    Returns:
        bool: True if trap is real, False if it's genuine move
    """
    # Calculate CVD (if we have buy/sell volume data)
    if 'buy_volume' not in data.columns:
        return True  # Can't check, assume valid
    
    # Calculate CVD trend over last 20 bars
    recent_data = data.iloc[-20:]
    cvd = (recent_data['buy_volume'] - recent_data['sell_volume']).cumsum()
    cvd_slope = cvd.iloc[-1] - cvd.iloc[0]
    
    if trap_type == 'bullish_trap':
        # For bullish trap (SHORT), CVD should be declining
        # If CVD is RISING = real buying, not a trap!
        if cvd_slope > 0:
            logger.debug("Bullish trap rejected: CVD rising (real buying)")
            return False
        return True
    
    elif trap_type == 'bearish_trap':
        # For bearish trap (LONG), CVD should be rising
        # If CVD is FALLING = real selling, not a trap!
        if cvd_slope < 0:
            logger.debug("Bearish trap rejected: CVD falling (real selling)")
            return False
        return True
    
    return True

def calculate_buying_pressure_score(data):
    """
    Calculate buying pressure score (0-10)
    
    Higher score = more buying pressure
    """
    score = 0
    recent = data.iloc[-10:]
    
    # Check 1: Recent candle bias
    bullish_candles = (recent['close'] > recent['open']).sum()
    if bullish_candles >= 7:
        score += 3
    
    # Check 2: Volume trend
    recent_vol = recent['volume'].iloc[-5:].mean()
    older_vol = recent['volume'].iloc[:5].mean()
    if recent_vol > older_vol * 1.2:
        score += 2
    
    # Check 3: Price vs VWAP
    typical = (recent['high'] + recent['low'] + recent['close']) / 3
    vwap = (typical * recent['volume']).sum() / recent['volume'].sum()
    if recent['close'].iloc[-1] > vwap:
        score += 2
    
    # Check 4: Close positions
    closes = [(row['close'] - row['low']) / (row['high'] - row['low']) 
              for _, row in recent.iterrows() if row['high'] != row['low']]
    avg_close_pos = sum(closes) / len(closes) if closes else 0.5
    if avg_close_pos > 0.6:
        score += 3
    
    return score
```

---

## Configuration Changes Required

```python
# IN config/base_config.py or TBDConfig:

# CURRENT (TOO LENIENT):
trap_wick_threshold: float = 0.5         # 50%
trap_volume_multiplier: float = 1.5      # 1.5x
# No body check
# No confirmation requirement

# ENHANCED (STRICT):
trap_wick_threshold: float = 0.6         # 60% wick minimum
trap_volume_multiplier_min: float = 2.0  # 2x volume minimum
trap_volume_multiplier_max: float = 5.0  # 5x volume maximum
trap_body_max_ratio: float = 0.3         # Max 30% body
trap_close_position_min: float = 0.6     # Min 60% close position (for bearish trap)
trap_close_position_max: float = 0.4     # Max 40% close position (for bullish trap)

# NEW PARAMETERS:
trap_require_confirmation: bool = True    # Wait for confirmation bar
trap_require_level_proximity: bool = True # Must be at support/resistance
trap_require_trend_context: bool = True   # Check if in correct trend
trap_max_hold_hours: int = 4             # Maximum hold time (SCALP!)
trap_tight_stop_multiplier: float = 0.5  # ATR multiplier for stop (tight!)
trap_exit_at_level_return: bool = True   # Exit if price returns to trap level
```

---

## Expected Performance Improvement

### Before Enhancements
- **Win Rate**: 37.5%
- **TP Hit Rate**: 0%
- **Stop Hit Rate**: 50%
- **Problem**: Too many false traps

### After Enhancements (Projected)
- **Win Rate**: 55-60% ✅
- **TP Hit Rate**: 20-25% ✅
- **Stop Hit Rate**: 25-30% ✅
- **Frequency**: Reduced (quality over quantity)

### Impact
- **Better Entries**: Confirmation bar improves win rate by 20%
- **Faster Exits**: 4-hour max hold prevents holding losers
- **Tighter Stops**: 0.5x ATR reduces loss size by 66%

---

## Common Failure Modes & Solutions

### Failure Mode #1: False Trap (Real Breakout)
**Symptoms**: Stop hit immediately, price continues in wick direction  
**Cause**: Not a trap - genuine institutional buying/selling  
**Solution**: ✅ Check CVD, volume bounds, level proximity

### Failure Mode #2: Holding Too Long
**Symptoms**: Small profit turns to loss  
**Cause**: Trap moves are SHORT-TERM  
**Solution**: ✅ 4-hour maximum hold time

### Failure Mode #3: Wide Stops
**Symptoms**: Large losses eat profits  
**Cause**: Using same stops as three_hits  
**Solution**: ✅ Tight stops (0.5x ATR)

### Failure Mode #4: Missing Confirmation
**Symptoms**: Enter on trap candle, price returns to level  
**Cause**: No follow-through  
**Solution**: ✅ Require confirmation bar

### Failure Mode #5: Trading Any Wick
**Symptoms**: Too many trades, mostly losers  
**Cause**: Not checking context  
**Solution**: ✅ Require level proximity, trend alignment

---

## Complete Implementation Code

```python
class TrappingVolumeDetector:
    """
    Enhanced trapping volume detector with strict validation
    """
    
    def __init__(self, config):
        self.config = config
        self.pending_traps = {}
        self.next_trap_id = 0
    
    def update(self, data, current_price):
        """
        Main update method called every bar
        
        Returns:
            PatternData or None
        """
        current_candle = data.iloc[-1]
        
        # Stage 1: Check for pending confirmation
        confirmed_trap = self.tracker.check_trap_confirmation(data, current_price)
        if confirmed_trap:
            return confirmed_trap
        
        # Stage 2: Detect new traps (that need confirmation)
        trap_setup = detect_wick_trap_enhanced(current_candle, data)
        if trap_setup:
            # Store for confirmation
            self.pending_traps[self.next_trap_id] = {
                **trap_setup,
                'detected_bar': len(data) - 1,
                'detected_time': current_candle.name
            }
            self.next_trap_id += 1
            logger.info(f"Trap setup detected - awaiting confirmation")
        
        return None
```

---

**Implementation Priority**: HIGH (Need to improve 37.5% win rate)  
**Expected Impact**: Transform 37.5% → 55%+ win rate  
**Trade Type**: SCALP (4 hours max, not days)

---

*Document Version: 2.0*  
*Last Updated: December 28, 2025*
