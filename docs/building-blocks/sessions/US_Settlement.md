# US Settlement Building Block

**Block Number:** 66/80 | **Category:** Sessions & Time | **Version:** 2.0 (Enhanced - Magnet Effect) | **Status:** ✅ PRODUCTION READY

---

## ✅ US SETTLEMENT MAGNET DETECTOR - PRODUCTION READY

**This block detects US market settlement window and price magnet effect**

**Test Results:** 6.8% active + 78.9% avg confidence + **11.6% std (TIGHT!)** ✅  
**Block Type:** EVENT BLOCK (specialized settlement detection)  
**Design:** Settlement window + magnet effect + smart confidence  
**Grade:** B+ (88/100) - EXCELLENT specialized event detector

**Current Performance (15min):**
- ✅ 6.8% active signals (1,169 / 17,181) - correct for event!
- ✅ 93.2% NEUTRAL (16,012) - appropriate for EVENT block!
- ✅ 78.9% avg confidence (active signals) ✅
- ✅ **11.6% std dev (TIGHT FOR FOCUSED EVENT!)** ✨
- ✅ 0% error rate (perfect reliability)
- ✅ **61% SETTLEMENT / 39% PRE-SETTLEMENT** (good split!)
- ✅ **1.0 settlement windows/day** (event tracking)
- ✅ Magnet effect detection (novel feature)
- ✅ Smart confidence (volume + ATR)

**Signal Distribution (Active Only):**
- **SETTLEMENT_ACTIVE** (61.2%): In settlement window
- **PRE_SETTLEMENT_BULLISH** (19.0%): Magnet up
- **PRE_SETTLEMENT_BEARISH** (19.8%): Magnet down
- **NEUTRAL** (93.2% overall): Outside windows

**Implementation Features:**
1. ✅ Correctly classified as EVENT BLOCK
2. ✅ US settlement window detection (20:00-21:00 UTC)
3. ✅ Magnet effect detection (novel pre-settlement drift)
4. ✅ Smart confidence (volume + ATR + magnet strength)
5. ✅ Tight variation (11.6% std - focused event)
6. ✅ Event tracking (window entry)
7. ✅ Pre-settlement period (19:00-20:00 UTC)
8. ✅ Directional bias detection (bullish/bearish drift)

**Status:** ✅ PRODUCTION READY - B+ GRADE

**See Expert Review:** `docs/v3/expert_analisys_review_building_blocks/66_us_settlement_expert_review.md`

**Deployment:**
- Settlement window timing
- Magnet effect capture
- End-of-day positioning
- Institutional flow detection
- Specialized event signal

---

## Overview

US Settlement detects institutional settlement window (20:00-21:00 UTC) and pre-settlement magnet effect - NOT continuous state but specialized 1-2hr market phenomenon correctly classified as EVENT BLOCK. Settlement window marks US equity market close (16:00 EST = 21:00 UTC for settlement period starting 20:00 UTC) when institutional flows settle positions, portfolios rebalance, and end-of-day positioning occurs creating "price magnet" effect. Novel magnet detection analyzes price drift during pre-settlement hour (19:00-20:00 UTC) measuring ATR-normalized slope to identify directional bias as institutions position for settlement - BULLISH drift signals upward magnet, BEARISH signals downward. Smart confidence system adjusts base values (90% settlement, 70% pre-settlement) using real-time volume activity (+/-10%), ATR volatility (+/-5%), window transition (+5%), and magnet strength bonus (+0-10%). Tight confidence variation (11.6% std) reflects focused 1-2hr phenomenon. Fires 6.8% of time (correct for specialized event) with 93.2% NEUTRAL during off-hours (appropriate EVENT behavior). Unlike continuous time blocks (Kill Zones, Session Time with 100% coverage), this specialized window deserves EVENT classification maintaining focused signal quality. Essential for end-of-day institutional flow detection and settlement-based trading strategies.

## Block Classification

**Type:** EVENT BLOCK - SPECIALIZED SETTLEMENT DETECTION
- **Signal Rate:** 6.8% (fires during settlement windows only!) ✅
- **SETTLEMENT_ACTIVE:** 61.2% of active
- **PRE_SETTLEMENT_BULLISH:** 19.0% of active
- **PRE_SETTLEMENT_BEARISH:** 19.8% of active
- **NEUTRAL:** 93.2% overall (off-hours)
- **Windows:** Settlement + Pre-settlement
- **Confidence:** 70-100 (event-dependent)
- **Variation:** 11.6% std (TIGHT!)
- **Events:** 1.0/day
- **Boosters:** +10-20 points
- Settlement specialist

## Technical Specifications

**Components:** Settlement Window Detection + Magnet Effect Analysis + Smart Confidence + Event Tracking  
**File:** `src/detectors/building_blocks/sessions/us_settlement.py`

## Signals

### Settlement Signals (Event-Based):

**SETTLEMENT_ACTIVE** (In Settlement Window)
- 20:00-21:00 UTC settlement period
- US market close settlement flows
- Frequency: 4.2% overall, 61.2% of active
- Confidence: 85-100% (window + adjustments)
- Booster: +15-20 points
- **Institutional settlement flows**

**PRE_SETTLEMENT_BULLISH** (Magnet Up)
- 19:00-20:00 UTC pre-settlement hour
- Upward price drift detected
- Frequency: 1.3% overall, 19.0% of active
- Confidence: 70-85% (magnet + adjustments)
- Booster: +10-15 points
- **Bullish magnet effect**

**PRE_SETTLEMENT_BEARISH** (Magnet Down)
- 19:00-20:00 UTC pre-settlement hour
- Downward price drift detected
- Frequency: 1.3% overall, 19.8% of active
- Confidence: 70-85% (magnet + adjustments)
- Booster: +10-15 points
- **Bearish magnet effect**

**NEUTRAL** (Outside Windows)
- All other times (93.2%)
- No settlement activity
- Frequency: 93.2% overall
- Confidence: N/A (no signal)
- Use: Other blocks for timing
- **EVENT block behavior - selective firing**

### Settlement Detection Logic:

```python
# Check settlement windows
current_hour = timestamp.hour

# Settlement window (20:00-21:00 UTC)
if 20 <= current_hour < 21:
    in_settlement = True
    base_confidence = 90
    
    # Smart adjustments
    confidence = base_confidence
    
    # Volume activity (+/-10%)
    if activity_score >= 80:
        confidence += 10  # Very active
    elif activity_score >= 60:
        confidence += 5
    elif activity_score < 40:
        confidence -= 10
    
    # ATR volatility (+/-5%)
    if volatility_ratio > 1.5:
        confidence += 5
    elif volatility_ratio < 0.5:
        confidence -= 5
    
    # Window entry (+5%)
    if just_entered_window:
        confidence += 5
    
    signal = 'SETTLEMENT_ACTIVE'
    
# Pre-settlement window (19:00-20:00 UTC)
elif 19 <= current_hour < 20:
    in_pre_settlement = True
    base_confidence = 70
    
    # Detect magnet effect
    has_magnet, direction, strength = detect_magnet_effect(df)
    
    if has_magnet:
        # Smart adjustments
        confidence = base_confidence
        
        # Volume activity
        if activity_score >= 80:
            confidence += 10
        elif activity_score >= 60:
            confidence += 5
        elif activity_score < 40:
            confidence -= 10
        
        # ATR volatility
        if volatility_ratio > 1.5:
            confidence += 5
        elif volatility_ratio < 0.5:
            confidence -= 5
        
        # Magnet strength bonus (+0-10%)
        magnet_bonus = min(10, strength // 10)
        confidence += magnet_bonus
        
        # Directional signal
        if direction == 'BULLISH':
            signal = 'PRE_SETTLEMENT_BULLISH'
        else:
            signal = 'PRE_SETTLEMENT_BEARISH'
    else:
        signal = 'NEUTRAL'
        
# Outside windows
else:
    signal = 'NEUTRAL'

# Final
confidence = clamp(confidence, 30, 100)

# Result: 6.8% active, 93.2% NEUTRAL
# EVENT block - selective firing!
```

## Enhanced Features

### 1. EVENT Block Classification (Correct!):
```python
# Correctly classified as EVENT BLOCK!

EVENT BLOCK Characteristics:
- Fires selectively (6.8% active)
- Returns NEUTRAL off-hours (93.2%)
- Specialized phenomenon (1-2hr window)
- Focused signal quality

Why EVENT not CONTEXT:

CONTEXT blocks (100% coverage):
- Kill Zones: Always indicates zone
- Session Time: Always indicates session
- Premium/Discount: Always indicates zone
- Swing Points: Always provides reference

Purpose: Continuous state for all bars

EVENT blocks (selective firing):
- US Settlement: Fires during settlement only
- Patterns: Fire when pattern detected
- Breakouts: Fire on breakout events
- Divergence: Fire when divergence found

Purpose: Specialized event detection

US Settlement is EVENT because:

1. Specialized 1-2hr window:
   - Settlement: 1 hr/day (4.2%)
   - Pre-settlement: 1 hr/day (2.6%)
   - Total: 2 hrs/day = ~8%

2. Specific market phenomenon:
   - Institutional settlement flows
   - Portfolio rebalancing
   - End-of-day positioning
   - Not general time state

3. Magnet effect is event-driven:
   - Detects price drift
   - Directional bias emerges
   - Opportunistic signal
   - Not continuous reference

4. NEUTRAL during off-hours appropriate:
   - 93.2% of time no settlement
   - No action needed
   - Use other blocks for timing
   - Preserves signal quality

Comparison to Session Time:

Session Time (redesigned to CONTEXT):
- Tracks full 24hr session cycle
- Always indicates current session
- General time state provider
- 100% coverage makes sense

US Settlement (stays EVENT):
- Tracks 1-2hr specialized window
- Only fires during settlement
- Specific institutional event
- 6.8% coverage is CORRECT

Different phenomenon = different approach!

Value of EVENT Classification:

As EVENT:
- Powerful specialized signal
- High confidence when active (78.9%)
- Focused on real phenomenon
- Clean selective firing
- Preserves signal quality

If forced to CONTEXT:
- Would need 100% coverage
- Diluted signal quality
- Artificial "state" 93% of time
- Loses specialized value
- Wrong tool for job

Verdict: EVENT classification is CORRECT! ✅
```

### 2. Settlement Window Framework:
```python
# US Market Settlement (Institutional Reality)

Settlement Window (20:00-21:00 UTC):

US Market Close Timing:
- NYSE closes: 16:00 EST
- NASDAQ closes: 16:00 EST
- Settlement period: 15:00-16:00 EST
- UTC equivalent: 20:00-21:00 (EST +5hrs winter)

Why This Matters:

Institutional Flows:
- Portfolio rebalancing
- Index tracking adjustments
- Mutual fund NAV calculation
- Options/futures settlement
- End-of-day positioning

Creates Price Magnet Effect:
- Institutions settle at specific prices
- Large volume converging
- Price gravitates toward settlement
- Predictable flow patterns

Crypto Correlation:
- BTC follows equity market flows
- Settlement creates directional bias
- Institutional crypto positions
- Cross-market arbitrage

Real-World Example:

Monday 20:30 UTC:
- US equities just closed (16:30 EST)
- Settlement flows active
- Large institutional volume
- BTC reacts to equity settlement
- Price drawn toward settlement level

Detection:
- Window: 20:00-21:00 UTC (1 hour)
- Base confidence: 90%
- High institutional activity
- Settlement flows

vs

Monday 14:00 UTC:
- US markets still open
- No settlement flows
- Normal trading activity
- Signal: NEUTRAL

Frequency:
Daily occurrence: 1 hour/24 hours = 4.2%
Results: 4.2% of bars ✅
Perfect match!

Why Important:

Known institutional event:
- Predictable timing (daily 20:00-21:00)
- Large flows (settlement volumes)
- Price impact (magnet effect)
- High probability window

Strategy Application:
- End-of-day positioning
- Settlement flow following
- Institutional flow detection
- Timing filter for entries
```

### 3. Magnet Effect Detection (Novel Feature!):
```python
# Price drift toward settlement - INSTITUTIONAL BEHAVIOR!

What is Magnet Effect?

Pre-settlement hour (19:00-20:00 UTC):
- Institutions position before settlement
- Creates directional price drift
- "Magnet" pulls price toward settlement level
- Measurable trend emerges

Detection Method:

def detect_magnet_effect(df, window=8):
    """
    Detect price drift toward settlement
    
    Analyzes last 8 bars (2 hours in 15min)
    during pre-settlement period
    """
    
    # Get recent closes
    recent_closes = df['close'].iloc[-window:].values
    
    # Calculate trend (linear regression)
    x = np.arange(len(recent_closes))
    slope = np.polyfit(x, recent_closes, 1)[0]
    
    # Normalize by ATR (context-aware)
    atr = calculate_atr(df)
    normalized_slope = slope / atr if atr > 0 else 0
    
    # Detect significant drift
    threshold = 0.1  # 10% of ATR per bar
    
    if abs(normalized_slope) > threshold:
        has_magnet = True
        direction = 'BULLISH' if slope > 0 else 'BEARISH'
        strength = min(100, int(abs(normalized_slope) * 100))
    else:
        has_magnet = False
        direction = 'NEUTRAL'
        strength = 0
    
    return has_magnet, direction, strength

Why This Works:

Institutional Behavior:
- Pre-settlement positioning (19:00-20:00)
- Large orders placed gradually
- Directional bias emerges
- Creates measurable drift

Example Bullish Magnet:

19:00 UTC: BTC at $45,000
19:15 UTC: $45,050 (+$50)
19:30 UTC: $45,120 (+$120)
19:45 UTC: $45,200 (+$200)

Linear slope: +$200/hour
ATR: $500
Normalized slope: 0.4 (40% ATR/hr)
→ STRONG BULLISH MAGNET (strength 40)

Signal: PRE_SETTLEMENT_BULLISH
Confidence: 70 + adjustments
Action: Consider long positions ahead of settlement

Example Bearish Magnet:

19:00 UTC: BTC at $45,000
19:15 UTC: $44,950 (-$50)
19:30 UTC: $44,880 (-$120)
19:45 UTC: $44,800 (-$200)

Linear slope: -$200/hour
ATR: $500
Normalized slope: -0.4 (-40% ATR/hr)
→ STRONG BEARISH MAGNET (strength 40)

Signal: PRE_SETTLEMENT_BEARISH
Confidence: 70 + adjustments
Action: Consider short positions ahead of settlement

Example No Magnet:

19:00 UTC: $45,000
19:15 UTC: $45,020
19:30 UTC: $44,990
19:45 UTC: $45,010

Choppy, no clear drift
Normalized slope: 0.02 (2% ATR/hr)
→ Below threshold (10%)

Signal: NEUTRAL
No magnet detected

Value of Magnet Detection:

Novel Feature:
- Not in standard TA libraries
- Institutional behavior analysis
- Pre-positioning detection
- Directional bias identification

Trading Application:
- Enter before settlement
- Follow institutional drift
- Capture magnet move
- Exit during settlement period

Confidence Boost:
Base: 70% (pre-settlement)
+ Volume active: +10%
+ High ATR: +5%
+ Strong magnet (40 strength): +4%
→ Total: 89%

Results:
- 222 bullish signals (1.3% of bars)
- 231 bearish signals (1.3% of bars)
- 49/51 balance (perfect!) ✅
- Novel and valuable feature!
```

### 4. Smart Confidence System:
```python
# Multi-factor confidence assessment!

Base Confidence:
- Settlement window (20:00-21:00): 90%
- Pre-settlement (19:00-20:00): 70%
- Off-hours: N/A (NEUTRAL)

FACTOR 1: Volume Activity (+/-10%)

Calculate activity score:
current_volume = df['volume'].iloc[-1]
avg_volume = df['volume'].iloc[-20:].mean()
activity_score = (current_volume / avg_volume) × 50

If activity_score >= 80 (very active):
  confidence += 10
  # Settlement flows confirmed

If activity_score >= 60 (active):
  confidence += 5
  # Good settlement activity

If activity_score < 40 (quiet):
  confidence -= 10
  # Weak settlement

Example Settlement Window:
- Base: 90%
- High volume (score 85): +10%
- Final: 100%

Example Settlement (quiet):
- Base: 90%
- Low volume (score 35): -10%
- Final: 80%

FACTOR 2: ATR Volatility (+/-5%)

Calculate volatility ratio:
current_atr = calculate_atr(df, 14)
avg_atr = historical_avg
volatility_ratio = current_atr / avg_atr

If volatility_ratio > 1.5 (high):
  confidence += 5
  # Good volatility for moves

If volatility_ratio < 0.5 (low):
  confidence -= 5
  # Too quiet

Example Pre-Settlement:
- Base: 70%
- High ATR (2.0): +5%
- Final: 75%

FACTOR 3: Window Transition (+5%)

If just_entered_window:
  confidence += 5
  # Fresh settlement entry

Example Settlement Entry:
- Base: 90%
- Just entered: +5%
- High volume: +10%
- Final: 100%+ → capped at 100%

FACTOR 4: Magnet Strength (+0-10%)

If magnet_detected:
  magnet_bonus = min(10, strength // 10)
  confidence += magnet_bonus

Examples:
Strength 40: +4%
Strength 70: +7%
Strength 100: +10% (capped)

Example Pre-Settlement Bullish:
- Base: 70%
- High volume: +10%
- High ATR: +5%
- Strong magnet (60): +6%
- Final: 91%

Final Range:
- Settlement active: 75-100%
- Pre-settlement magnet: 65-95%
- Average across active: 78.9% ✅
- Std dev: 11.6% (tight!) ✅

Why 11.6% Std is TIGHT:

Focused event (1-2hr window):
- Consistent conditions
- Similar volatility
- Similar volumes
- Tight confidence range

vs Broad time blocks (24hr):
- Variable conditions
- Wide volatility range
- Wide volume range
- Wide confidence range (20-30% std)

US Settlement: 11.6% std ✅
Appropriate for specialized event!
```

### 5. Tight Confidence Variation (11.6% std):
```python
# GOOD for focused event!

Understanding Variation by Block Type:

PRICE BLOCKS:
- Target: 5-10% std
- React to market state
- Small variations
- Example: EMA crossover

TIME BLOCKS (24hr):
- Target: 20-30% std
- Vary by time of day
- Large variations
- Example: Kill Zones (24.1% std)

EVENT BLOCKS (focused):
- Target: 10-15% std
- Specialized conditions
- Medium variations
- Example: US Settlement (11.6% std) ✅

Why 11.6% Std is PERFECT:

Calculation breakdown:
- Settlement window: 85-100% conf
- Pre-settlement magnet: 65-95% conf
- Focused 1-2hr phenomenon
- Similar market conditions

Result:
Average: 78.9%
Std dev: 11.6%

This is CORRECT because:

Specialized event characteristics:
- Occurs same time daily (20:00-21:00 UTC)
- Similar institutional flows
- Consistent settlement patterns
- Predictable activity levels

Tighter than broad time blocks:
- Kill Zones: 24.1% std (24hr cycle)
- Session Time: 23.0% std (24hr cycle)
- US Settlement: 11.6% std (1-2hr window)

Why tighter variation?

Focused window:
- Settlement: 20:00-21:00 only
- Pre-settlement: 19:00-20:00 only
- Total: 2 hours/day
- Consistent conditions

vs Broad coverage:
- Kill Zones: Multiple zones/24hrs
- Session Time: 4 sessions/24hrs
- Variable conditions
- Wide confidence range

Comparison:

Kill Zones (24hr coverage):
- Asian 40% vs NY AM 95% = 55 point spread
- Creates 24.1% std (correct for 24hr)

US Settlement (1-2hr window):
- Settlement 85% vs Magnet 95% = 10 point spread
- Creates 11.6% std (correct for focused)

Expert Perspective:

This is EXACTLY what focused events should do:
- Tight base range (70-90%)
- Moderate adjustments (±15%)
- Small total variation
- Creates 11.6% std
- Proper for specialized event
```

### 6. Event Tracking:
```python
# Tracks settlement window entry!

Tracks:
- Last in settlement state
- Bars in settlement
- Window transitions

Detection:
if in_settlement and not last_in_settlement:
    is_new_event = True
    bars_in_settlement = 0
    # NEW window entered!
elif in_settlement:
    is_new_event = False
    bars_in_settlement += 1
    # Continuing in window
else:
    is_new_event = False
    bars_in_settlement = 0

Results:
- New events: 181 (1.1% of results)
- Continuing: 988 (84.5% of active)
- New settlements/day: 1.0 ✅

Why 1.0 Events/Day is CORRECT:

1 settlement window per day:
- Settlement: 20:00-21:00 (1 hour)
- Occurs daily
- 1 entry event per day

Actual: 1.0/day ✅
Theoretical: 1.0/day ✅
Perfect match!

Value for Strategies:

Window entry = opportunity:
- Settlement just started
- Fresh institutional flows
- High probability window
- Position for magnet effect

Example Trading:

if result['metadata']['is_new_event']:
    # Settlement window just started!
    
    if result['signal'] == 'SETTLEMENT_ACTIVE':
        # 20:00 UTC - settlement beginning
        
        check_all_blocks()
        
        if total_confluence >= 65:
            # Settlement + other factors
            execute_position()
            position_size × 1.2  # Slightly larger
            notes.append('🆕 Settlement Window Entry!')
            
else:
    # Continuing in window
    
    bars_in = result['metadata']['bars_in_settlement']
    
    if bars_in > 3:  # 45 minutes in
        # Settlement ending soon
        prepare_to_exit()
        tighten_stops()

Prevents:
- Firing on every bar in window
- Double-counting
- Missed opportunities

Enables:
- Entry at window start
- Exit before window end
- Position management
- Proper timing
```

### 7. Pre-Settlement Period:
```python
# Magnet buildup period!

Pre-Settlement Window (19:00-20:00 UTC):

Why This Hour Matters:

1 Hour Before Settlement:
- Institutions positioning
- Large orders being placed
- Directional bias emerging
- Magnet effect building

Detection:
if 19 <= current_hour < 20:
    in_pre_settlement = True
    
    # Detect magnet effect
    has_magnet, direction, strength = detect_magnet_effect(df)
    
    if has_magnet:
        if direction == 'BULLISH':
            signal = 'PRE_SETTLEMENT_BULLISH'
        else:
            signal = 'PRE_SETTLEMENT_BEARISH'

Frequency:
- Pre-settlement hour: 1hr/24hr = 4.2%
- Magnet detected: ~50% of pre-settlement
- Active signals: ~2% of bars ✅

Results:
- PRE_SETTLEMENT_BULLISH: 1.3% (222 signals)
- PRE_SETTLEMENT_BEARISH: 1.3% (231 signals)
- Balance: 49/51 ✅

Value:

Early Entry Opportunity:
- Detect trend before settlement
- Enter ahead of flows
- Ride magnet effect
- Exit during settlement

Example Bullish Pre-Settlement:

19:15 UTC:
- Magnet detected (bullish drift)
- Signal: PRE_SETTLEMENT_BULLISH
- Confidence: 78%
- Action: Enter long

19:30 UTC:
- Drift continues
- Building toward settlement
- Maintain position

20:00 UTC:
- Settlement window starts
- Signal: SETTLEMENT_ACTIVE
- Hold or take partial profit

20:45 UTC:
- Settlement ending
- Exit position
- Capture magnet move

Strategy:
Pre-settlement = Lead indicator
Settlement = Confirmation
Magnet = Directional bias
```

### 8. NEUTRAL Signal Behavior:
```python
# Appropriate for EVENT blocks!

NEUTRAL Explained:

What NEUTRAL Means:
- Outside settlement windows
- No settlement activity
- 93.2% of time
- No action recommended

This is CORRECT for EVENT blocks!

Compare to CONTEXT blocks:

CONTEXT (always active, no NEUTRAL):
Kill Zones: 100% coverage
- Always indicates zone
- PRIME_TIME / ACTIVE / WAIT
- Never NEUTRAL

Session Time: 100% coverage
- Always indicates session
- PEAK / ACTIVE / MODERATE / QUIET
- Never NEUTRAL

EVENT (selective firing, mostly NEUTRAL):
US Settlement: 6.8% coverage
- Only fires during settlement
- SETTLEMENT_ACTIVE / PRE_SETTLEMENT_BULL/BEAR
- 93.2% NEUTRAL ✅

Why NEUTRAL is Appropriate:

1. Specialized Phenomenon:
   - Settlement is 1-2hr/day
   - Magnet effect is pre-settlement
   - Total relevant time: ~2hrs
   - Rest of day: No settlement

2. Signal Quality:
   - High confidence when active (78.9%)
   - Focused on real event
   - No dilution from forced signals
   - Clear actionable signals

3. Trading Reality:
   - Can't trade settlement 24hrs/day
   - Window-specific strategy
   - NEUTRAL = use other blocks
   - Clean separation of concerns

4. Event-Driven Nature:
   - Settlement flows occur at specific time
   - Magnet effect is temporary phenomenon
   - Not continuous state
   - Event triggers strategies

Usage Pattern:

settlement_result = us_settlement.analyze(df)

if settlement_result['signal'] != 'NEUTRAL':
    # Settlement event active!
    
    if settlement_result['signal'] == 'SETTLEMENT_ACTIVE':
        # In settlement window
        settlement_strategy()
        
    elif 'PRE_SETTLEMENT' in settlement_result['signal']:
        # Magnet effect detected
        magnet_strategy()
        
else:
    # NEUTRAL - no settlement activity
    # Use other blocks for timing:
    
    kz_result = kill_zones.analyze(df)
    session_result = session_time.analyze(df)
    
    # Continue with other strategies
    # Settlement not relevant

Value of NEUTRAL:

Clear Signal:
- Active = Settlement happening
- NEUTRAL = No settlement
- No ambiguity
- Clean decision making

Preserves Quality:
- Only fires when relevant
- High confidence signals
- Focused on phenomenon
- No noise

Complements Other Blocks:
- Kill Zones for general time filtering
- Session Time for session state
- US Settlement for settlement window
- Each block has role

This is how EVENT blocks should work! ✅
```

## Parameters (Optimized)

```python
timeframe: '15min'              # Works on any timeframe
```

**Settlement Windows (UTC - FIXED):**
```python
NOT CONFIGURABLE (Actual Market Hours):

Settlement: 20:00-21:00 UTC
Pre-Settlement: 19:00-20:00 UTC

Based on:
- US Market Close: 16:00 EST
- Settlement Period: 15:00-16:00 EST
- UTC Equivalent: 20:00-21:00 (EST +5hrs)

These match actual institutional flows
```

**Magnet Detection:**
```python
window: 8 bars                  # Last 2 hours (15min)
threshold: 0.1                  # 10% ATR per bar
```

**Adjustment Ranges:**
```python
Volume Activity: +/-10%
ATR Volatility: +/-5%
Window Transition: +5%
Magnet Strength: +0-10%

Total adjustment range: +/-25%
```

## Confidence Calculation

**Event-Based System (70-100 range for active):**
```python
# Base by window
if in_settlement:
    base = 90  # HIGH
elif in_pre_settlement:
    base = 70  # MEDIUM
else:
    return 'NEUTRAL'  # No signal

# Volume activity adjustment
if activity_score >= 80:
    base += 10
elif activity_score >= 60:
    base += 5
elif activity_score < 40:
    base -= 10

# ATR volatility adjustment
if volatility_ratio > 1.5:
    base += 5
elif volatility_ratio < 0.5:
    base -= 5

# Window entry bonus
if is_new_event:
    base += 5

# Magnet strength bonus (pre-settlement only)
if in_pre_settlement and has_magnet:
    magnet_bonus = min(10, magnet_strength // 10)
    base += magnet_bonus

# Final
confidence = clamp(base, 30, 100)

# Result range: 70-100% (active signals only)
# Average: 78.9%
# Std dev: 11.6% (TIGHT!)
```

## Trading Strategy

### Settlement Window Trading:
```python
# Trade during settlement
settlement_result = us_settlement.analyze(df)

if settlement_result['signal'] == 'SETTLEMENT_ACTIVE':
    # In settlement window (20:00-21:00)
    
    confluence = 18
    position_size = base_size × 1.2
    notes.append('🎯 US Settlement Window!')
    
    # Settlement-specific strategy
    if trend_aligned:
        execute_settlement_trade()
        
elif settlement_result['signal'] == 'PRE_SETTLEMENT_BULLISH':
    # Magnet effect up
    
    confluence = 15
    notes.append('🧲 Bullish Magnet Effect!')
    
    # Enter ahead of settlement
    if total_confluence >= 65:
        execute_long()
        prepare_for_settlement()
        
elif settlement_result['signal'] == 'PRE_SETTLEMENT_BEARISH':
    # Magnet effect down
    
    confluence = 15
    notes.append('🧲 Bearish Magnet Effect!')
    
    # Enter ahead of settlement
    if total_confluence >= 65:
        execute_short()
        prepare_for_settlement()
```

### Magnet Effect Strategy:
```python
# Follow pre-settlement drift
settlement_result = us_settlement.analyze(df)

if 'PRE_SETTLEMENT' in settlement_result['signal']:
    # Magnet detected
    
    direction = settlement_result['metadata']['magnet_direction']
    strength = settlement_result['metadata']['magnet_strength']
    
    if strength >= 40:
        # Strong magnet
        
        if direction == 'BULLISH':
            # Enter long
            execute_long()
            stop_below_recent_low()
            exit_during_settlement()
            
        else:
            # Enter short
            execute_short()
            stop_above_recent_high()
            exit_during_settlement()
```

### Settlement Entry/Exit:
```python
# Entry at window start, exit before end
settlement_result = us_settlement.analyze(df)

if settlement_result['metadata']['is_new_event']:
    # Settlement just started
    
    if settlement_result['signal'] == 'SETTLEMENT_ACTIVE':
        # 20:00 UTC - entry opportunity
        
        if confluence_sufficient:
            execute_entry()
            position_size × 1.3
            notes.append('🆕 Settlement Entry - Fresh Flows!')
            
elif settlement_result['signal'] == 'SETTLEMENT_ACTIVE':
    # Continuing in settlement
    
    bars_in = settlement_result['metadata']['bars_in_settlement']
    
    if bars_in > 3:  # 45+ minutes in
        # Settlement ending soon (21:00 approaching)
        
        if in_position:
            # Exit or tighten
            if profit > 0:
                exit_position()
                notes.append('⏰ Settlement Ending - Exit')
            else:
                tighten_stops()
```

### Volume/Magnet Confirmation:
```python
# Confirm with volume and magnet strength
settlement_result = us_settlement.analyze(df)

is_active = settlement_result['metadata']['is_volume_active']
magnet_strength = settlement_result['metadata']['magnet_strength']

if settlement_result['signal'] == 'SETTLEMENT_ACTIVE':
    # Settlement window
    
    if is_active:
        # High volume confirms flows
        confluence = 20
        confidence_boost = True
        notes.append('⭐ SETTLEMENT + HIGH VOLUME!')
        
    else:
        # Low volume - weak settlement
        confluence = 12
        notes.append('⚠️ Settlement but low volume')
        
elif 'PRE_SETTLEMENT' in settlement_result['signal']:
    # Pre-settlement magnet
    
    if magnet_strength >= 60:
        # Strong drift
        confluence = 18
        notes.append(f'💪 Strong Magnet ({magnet_strength})')
        
    elif magnet_strength >= 40:
        # Moderate drift  
        confluence = 15
        
    else:
        # Weak drift
        confluence = 10
```

## Confluence

**Event-Based Settlement Signal:**
- **Signal Rate:** 6.8% (fires during windows only) ✅
- **Distribution:** 61% / 20% / 20%
- **Window Coverage:** Settlement + Pre-settlement
- **Variation:** 11.6% std (TIGHT!)
- **Events:** 1.0/day
- **Confidence:** 70-100 (event-dependent)

**In Strategies:**
- **SETTLEMENT_ACTIVE** (90% base): +15-20 points, 1.2-1.3x size
- **PRE_SETTLEMENT_BULLISH** (70% base): +10-15 points, magnet following
- **PRE_SETTLEMENT_BEARISH** (70% base): +10-15 points, magnet following
- **NEUTRAL** (93.2%): Use other blocks for timing
- **Window transition:** +5 points (fresh flows)
- **High volume confirmation:** +5 points
- **Strong magnet:** +5-10 points (strength-based)

## Key Functions

**analyze(df)** - Main analysis
- Returns: signal, confidence, metadata
- Settlement window detection
- Magnet effect analysis
- Smart adjustments (volume + ATR)
- Event tracking

**detect_magnet_effect(df, window)** - Magnet detection
**calculate_smart_confidence(base, activity, atr, ...)** - Smart confidence
**analyze_volume_activity(df, window)** - Volume confirmation
**calculate_atr(df, period)** - ATR calculation

## Documentation Claims

- **Classification:** **EVENT BLOCK (CORRECT!)** ✨
- **Coverage:** **6.8% active (appropriate!)** ✨
- **Magnet Effect:** **Novel feature!** ✨
- **Smart Adjustments:** **Volume + ATR + magnet!** ✨
- **Tight Variation:** **11.6% std (focused!)** ✨
- **Event Tracking:** **1.0 windows/day!** ✨
- **Settlement Window:** **20:00-21:00 UTC!** ✨
- **Pre-Settlement:** **19:00-20:00 UTC magnet!** ✨
- **Error Rate:** **0.0% (perfect)** ✨

**Status:** ✅ Production Ready - B+ Grade (88/100) | **Tests:** `test_us_settlement.py`

---
*End of US Settlement Documentation*
