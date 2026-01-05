# Initial Balance Breakout - Building Block Documentation

**Block ID:** 68  
**Category:** PATTERNS  
**Type:** EVENT BLOCK  
**Mode:** SELECTIVE  
**Timeframe:** 15min (optimized for intraday)  
**Author:** Institutional Research  
**Date:** 2026-01-05  
**Status:** Testing  
**Grade:** TBD (pending walkforward validation)

---

## 📋 OVERVIEW

The Initial Balance (IB) Breakout detector identifies price breakouts from the opening range of each trading session. The Initial Balance represents the high and low formed during the first trading period - typically the first 1-2 hours.

This is a classic institutional concept:
- Institutions accumulate/distribute during the open
- The IB range sets the tone for the session
- Breakouts signal momentum continuation
- Rejections signal mean reversion opportunities

Based on **LuxAlgo Initial Balance** methodology, adapted for BTC/crypto 24/7 markets.

---

## ⚠️ BLOCK TYPE: CONTEXT PROVIDER

**This is a CONTEXT BLOCK, not a selective signal block.**

**What this means:**
- ✅ 100% active signal rate is **INTENTIONAL**
- ✅ Always provides IB-relative positioning (ABOVE_IB, BELOW_IB, INSIDE_IB)
- ✅ Moderate confidence (59.5% avg) is **APPROPRIATE** for context blocks
- ✅ Use for session structure + event boosting, **NOT** primary filtering

**How to use:**
1. **USE breakout events** (BULLISH_BREAKOUT, BEARISH_BREAKOUT) as confluence boosters when they occur
2. **USE context states** (ABOVE_IB, BELOW_IB) for ongoing momentum confirmation
3. **USE IB levels** for stop placement and target calculation
4. **DO NOT use** as primary signal filter (combine with selective blocks like EMA Cross)
5. **DO NOT expect** high base confidence (it provides structure, not conviction)

**Building Block Math:**
- Selective blocks (EMA Cross): 4.77% signal rate → Primary filtering
- Context blocks (IB Breakout): 100% active, 6.7% events → Structure + boosting
- Strategy = Selective blocks (filtering) + Context blocks (enhancement)

---

## 🎯 WHAT IT DETECTS

### Initial Balance Formation
- **Session Start:** Configurable (default: 00:00 UTC for crypto)
- **IB Duration:** Configurable (default: 2 hours = 120 minutes)
- **IB Range:** High and low during the IB period
- **Daily Reset:** New IB forms each calendar day

### Breakout Signals

**BULLISH_BREAKOUT:**
- Price closes above IB high
- Volume confirmation (optional)
- Distance-based strength assessment
- Provides target levels (25%, 50%, 100% extensions)

**BEARISH_BREAKOUT:**
- Price closes below IB low
- Volume confirmation (optional)
- Distance-based strength assessment  
- Provides target levels (25%, 50%, 100% extensions)

**IB_FORMED:**
- New IB session completed
- Provides IB high, low, midpoint, range

**INSIDE_IB:**
- Price currently inside IB range
- Position tracking (upper/mid/lower)

**NO_IB:**
- IB session not yet complete
- Waiting for formation

---

## 🔧 PARAMETERS

```python
InitialBalanceBreakout(
    timeframe='15min',            # Timeframe
    session_start_hour=0,         # Session start hour (UTC)
    session_start_min=0,          # Session start minute
    ib_duration_minutes=120,      # IB period duration (2 hours)
    volume_threshold=1.3,         # Volume multiplier for confirmation
    min_ib_range_atr=0.3,         # Min IB range (% of ATR)
)
```

### Parameter Details

**session_start_hour** (0-23)
- When the trading session begins
- Crypto: 0 (midnight UTC)
- US stocks: 9 (9:30 AM ET with session_start_min=30)
- Default: 0

**ib_duration_minutes** (positive integer)
- How long the IB period lasts
- Crypto: 120 minutes (2 hours, 8 bars @ 15min)
- Stocks: 60 minutes (first hour)
- Day trading: 5-30 minutes (ORB strategies)
- Default: 120

**volume_threshold** (>1.0)
- Volume multiplier for breakout confirmation
- 1.3 = requires 30% above average volume
- Higher = stricter confirmation
- Default: 1.3

**min_ib_range_atr** (0.0-1.0)
- Minimum IB range as % of ATR
- Prevents tight/invalid ranges
- 0.3 = IB must be at least 30% of ATR
- Default: 0.3

---

## 📊 SIGNAL STRUCTURE

### Example Signal: BULLISH_BREAKOUT

```python
{
    'signal': 'BULLISH_BREAKOUT',
    'confidence': 75,
    'metadata': {
        'ib_high': 45250.50,
        'ib_low': 45000.00,
        'ib_midpoint': 45125.25,
        'ib_range': 250.50,
        'breakout_price': 45300.00,
        'distance_from_ib': 49.50,
        'distance_pct': 19.8,
        'strength': 'WEAK',  # or 'MEDIUM', 'STRONG'
        'strength_score': 19.8,  # Fine-grained 0-100 scale
        'volume_confirmed': True,
        'is_new_event': True,
        'bars_since_ib': 12,  # Bars since IB formation
        'hours_since_ib': 3.0,  # Hours since IB formation
        'target_25': 45312.63,   # 25% extension
        'target_50': 45375.75,   # 50% extension  
        'target_100': 45501.00,  # 100% extension
    },
    'timestamp': '2025-12-16 10:30:00',
    'timeframe': '15min',
    'confluence_factors': [
        'BULLISH BREAKOUT at 45300.00',
        'IB: 45000.00 - 45250.50',
        'Strength: WEAK',
        'Volume: CONFIRMED',
        'Distance: 49.50 (19.8% of IB)',
    ]
}
```

### Signal Types & Confidence

| Signal | When | Confidence | is_new_event |
|--------|------|------------|--------------|
| BULLISH_BREAKOUT | First break above IB high | 55-85 | True |
| BEARISH_BREAKOUT | First break below IB low | 55-85 | True |
| IB_FORMED | New IB session complete | 60 | True |
| ABOVE_IB | Continuing above IB | 60 | False |
| BELOW_IB | Continuing below IB | 60 | False |
| INSIDE_IB | Price inside IB range | 50-55 | False |
| NO_IB | IB not formed yet | 50 | False |

**Confidence Calculation:**
- Base: 55 (weak), 65 (medium), 75 (strong)
- +10 if volume confirmed
- Strength based on distance from IB extreme:
  - Weak: <25% of IB range
  - Medium: 25-50% of IB range
  - Strong: >50% of IB range

---

## 📈 USAGE IN STRATEGIES

### As Primary Entry Signal

```python
# Configuration
detector = InitialBalanceBreakout(
    ib_duration_minutes=120,
    volume_threshold=1.5,  # Strict volume
)

# In strategy
result = detector.analyze(df)

if result['signal'] == 'BULLISH_BREAKOUT':
    if result['metadata']['volume_confirmed']:
        # Enter long
        entry = result['metadata']['breakout_price']
        stop = result['metadata']['ib_low']
        target = result['metadata']['target_50']  # 50% extension
```

### As Confluence Booster

```python
# Add to confluence score
if result['signal'] in ['BULLISH_BREAKOUT', 'BEARISH_BREAKOUT']:
    if result['metadata']['strength'] == 'STRONG':
        confluence_score += 25  # Strong breakout
    elif result['metadata']['strength'] == 'MEDIUM':
        confluence_score += 15  # Medium breakout
    else:
        confluence_score += 10  # Weak breakout
    
    # Extra boost for volume
    if result['metadata']['volume_confirmed']:
        confluence_score += 5
```

### Risk Management

```python
# Use IB for stop placement
if signal == 'BULLISH_BREAKOUT':
    stop_loss = ib_low  # IB low as invalidation
    risk = entry - stop_loss
    
    # Tiered targets
    target1 = metadata['target_25']  # Conservative
    target2 = metadata['target_50']  # Standard
    target3 = metadata['target_100']  # Aggressive
```

---

## 📚 TRADING CONCEPTS

### The Initial Balance

**Definition:**  
The high and low range formed during the first trading period of a session.

**Why It Matters:**
1. Institutional order flow establishes early direction
2. Sets support/resistance for the session
3. Breakouts signal continuation
4. Rejections signal reversals

**Classic Rules:**
- Price above IB = bullish session
- Price below IB = bearish session
- Extended breakouts = momentum
- Multiple IB tests = consolidation

### Session Types

**Crypto (24/7):**
- Session: 00:00 UTC
- IB Duration: 120 minutes (Asian open)
- Captures overnight positioning

**US Stocks:**
- Session: 9:30 AM ET
- IB Duration: 60 minutes (first hour)
- Captures institutional open

**ORB (Open Range Breakout):**
- Session: Market open
- IB Duration: 5-30 minutes (first minutes)
- Day trading strategy

### Extension Targets

**25% Extension:**
- Conservative profit target
- High probability
- Quick scalp

**50% Extension:**
- Standard breakout target
- Measured move
- Swing position

**100% Extension:**
- Aggressive target
- Extended move
- Full IB projection

---

## 🎨 VISUALIZATION CONCEPTS

### IB Range Box
```
Price  
  │
  ├─── IB High (45250.50) ────────────────
  │         ↑ BREAKOUT HERE
  │    [Initial Balance Range]
  │         (2-hour period)
  │
  ├─── IB Midpoint (45125.25)
  │
  │    [Initial Balance Range]
  │         (00:00-02:00 UTC)
  │         ↓ BREAKOUT HERE
  ├─── IB Low (45000.00) ─────────────────
  │
Time
```

### Extension Targets
```
100% Extension ──────────────────── 45500.00
               (Aggressive target)

 50% Extension ───────────────────── 45375.00
               (Standard target)

 25% Extension ───────────────────── 45312.50
               (Conservative)

     IB High ══════════════════════ 45250.00
              BREAKOUT ZONE

     IB Low ═══════════════════════ 45000.00
```

---

## ⚠️ LIMITATIONS

### False Breakouts
- **Issue:** Price briefly breaks IB then reverses
- **Mitigation:** Use volume confirmation, wait for close

### Tight Ranges
- **Issue:** Low volatility = small IB = trigger-happy signals
- **Mitigation:** min_ib_range_atr parameter validates minimum size

### 24/7 Markets
- **Issue:** Crypto trades continuously, no clear "open"
- **Mitigation:** Use consistent session time (00:00 UTC)

### Timeframe Dependency
- **Issue:** Designed for 15-min bars (8 bars = 2 hours)
- **Mitigation:** Adjust ib_duration_minutes for other timeframes

---

## 🔬 TESTING METHODOLOGY

### Walkforward Test

```python
# Test configuration
test = InitialBalanceBreakout(
    ib_duration_minutes=120,
    volume_threshold=1.3,
    min_ib_range_atr=0.3,
)

# Metrics to track:
# - Breakout frequency (per day)
# - Bullish vs bearish balance
# - Success rate to targets
# - False breakout rate
# - Volume confirmation accuracy
```

### Expected Results

**Ideal Performance:**
- BULLISH/BEARISH: 50/50 ± 10%
- Breakouts/Day: 0.5-2.0
- Strong breakouts: 10-20%
- Medium breakouts: 30-50%
- Weak breakouts: 30-60%
- Volume confirmed: 40-60%

---

## 📋 IMPLEMENTATION CHECKLIST

- [x] Core IB detection algorithm
- [x] Breakout signal generation
- [x] Volume confirmation
- [x] Strength classification
- [x] Extension targets (25/50/100%)
- [x] ATR-based validation
- [x] Daily session reset
- [x] State tracking (IB persistence)
- [ ] Walkforward testing
- [ ] Parameter optimization
- [ ] Expert Mode analysis
- [ ] Production deployment

---

## 📖 REFERENCES

**LuxAlgo Initial Balance:**
- Original concept and methodology
- Volume profile integration
- Session-based analysis

**Classic Trading:**
- J. Peter Steidlmayer (Market Profile)
- Toby Crabel (Opening Range Breakout)
- Linda Bradford Raschke (IB strategies)

**Related Blocks:**
- Range Liquidity (similar range concept)
- Volume Profile (institutional footprint)
- Session High/Low (intraday extremes)

---

## 🚀 NEXT STEPS

1. **Run Walkforward Test:**
   ```bash
   python scripts/walkforward_tests/68_test_initial_balance_breakout.py
   ```

2. **Review Results:**
   - Check BULLISH/BEARISH balance
   - Verify breakout frequency
   - Analyze strength distribution
   - Validate volume confirmation

3. **Expert Mode Analysis:**
   - Full institutional assessment
   - Compare to other event blocks
   - Determine optimal parameters
   - Assign final grade

4. **Production Deployment:**
   - If A/B grade: Deploy immediately
   - If C grade: Optimize or selective use
   - If D/F grade: Archive or redesign

---

**Status:** Ready for walkforward testing  
**Expected Grade:** B+ to A- (high-quality institutional concept)  
**Value:** Event-based intraday momentum detection  
**Use Case:** Confluence booster for breakout strategies
