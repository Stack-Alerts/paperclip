# M Pattern Reversal Strategy - Complete Flow Documentation

**Strategy File:** `src/strategies/strategy_01_reversal_m_pattern.py`  
**Strategy Number:** 01  
**Category:** REVERSAL  
**Direction:** SHORT (Bearish)  
**Date Created:** January 8, 2026  
**Last Updated:** January 9, 2026

---

## Strategy Overview

**Concept:** Classic M-pattern (double top) reversal strategy targeting bearish reversals at resistance levels with multiple confirmations.

**Market Conditions:** Works best in ranging to slightly uptrending markets where price makes equal highs before reversing.

**Expected Frequency:** 2-4 signals per month (60-120 trades per 180 days)

**Target Win Rate:** 65-75%

**Risk:Reward:** Minimum 1:3, Target 1:4-5

---

## Signal Generation Flow

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: DATA COLLECTION (Every 15-minute bar)              │
│                                                              │
│  • Collect OHLCV data                                        │
│  • Maintain rolling window (1000 bars)                       │
│  • Update all building blocks                                │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: BUILDING BLOCK ANALYSIS (6 blocks)                  │
│                                                              │
│  1. Double Top Pattern (35 points max)                       │
│     └─ Detect M-pattern formation                           │
│                                                              │
│  2. RSI Divergence (30 points max)                          │
│     └─ Confirm bearish momentum                             │
│                                                              │
│  3. HOD Level (15 points max)                               │
│     └─ Check rejection at high of day                        │
│                                                              │
│  4. Asia 50% (12 points max)                                │
│     └─ Verify price below equilibrium                        │
│                                                              │
│  5. Session Time (10 points max)                            │
│     └─ Check London/NY session timing                        │
│                                                              │
│  6. VWAP (10 points max)                                    │
│     └─ Confirm price below VWAP                             │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: CONFLUENCE CALCULATION                               │
│                                                              │
│  Total confluence = Sum of all block points                  │
│                                                              │
│  Example:                                                    │
│   • Double Top: PATTERN_FORMING (90% conf) → +32 points     │
│   • RSI Div: BEARISH_DIVERGENCE (85% conf) → +26 points     │
│   • HOD: REJECTION (80% conf) → +12 points                  │
│   • Asia 50%: BELOW_EQ (70% conf) → +8 points               │
│   • Session: LONDON_OPEN (100% conf) → +10 points           │
│   • VWAP: BELOW_VWAP (75% conf) → +8 points                │
│   ────────────────────────────────────────                  │
│   TOTAL: 96 points ✅ (Exceeds 70 minimum)                  │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: ENTRY VALIDATION                                     │
│                                                              │
│  Check 1: Confluence >= 70? ✅                              │
│  Check 2: No existing position? ✅                          │
│  Check 3: Calculate TP/SL levels                            │
│  Check 4: Verify R:R >= 2.0? ✅                             │
│                                                              │
│  If ALL checks pass → ENTER SHORT                           │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 5: POSITION ENTRY                                       │
│                                                              │
│  Entry Price: $95,000 (current market)                       │
│  Position Size: 0.263 BTC ($25,000 notional at 10x)        │
│  Direction: SHORT                                            │
│                                                              │
│  TP/SL Placement:                                            │
│   • SL: $98,500 (above M pattern peak + buffer)            │
│   • TP1: $89,750 (1.5R, 50% position)                       │
│   • TP2: $84,500 (3.0R, 30% position)                       │
│   • TP3: $77,500 (5.0R, 20% position)                       │
│                                                              │
│  Risk: $3,500 (3.7% of notional)                            │
│  Reward: $10,500 (TP2 target)                                │
│  R:R Ratio: 1:3.0 ✅                                        │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 6: POSITION MONITORING (Every bar)                     │
│                                                              │
│  For SHORT positions, monitor:                               │
│                                                              │
│  IF price drops to TP1 ($89,750):                           │
│   └─ Close 50% of position                                  │
│   └─ Move to breakeven or reduce risk                       │
│                                                              │
│  IF price drops to TP2 ($84,500):                           │
│   └─ Close 30% of position                                  │
│   └─ Trail stop on remaining 20%                            │
│                                                              │
│  IF price drops to TP3 ($77,500):                           │
│   └─ Close remaining 20%                                     │
│   └─ Trade complete (FULL TP HIT)                           │
│                                                              │
│  IF price rises to SL ($98,500):                            │
│   └─ Close 100% of position                                 │
│   └─ Trade complete (STOP LOSS HIT)                         │
│                                                              │
│  IF max hold time reached (7 days):                          │
│   └─ Close at market                                         │
│   └─ Trade complete (TIME EXIT)                             │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 7: PERFORMANCE TRACKING                                 │
│                                                              │
│  Record:                                                     │
│   • Entry/Exit prices                                        │
│   • Hold time                                                │
│   • Exit reason (TP1/TP2/TP3/SL/TIME)                       │
│   • PnL (gross and net)                                     │
│   • Fees paid                                                │
│   • Confluence score                                         │
│                                                              │
│  Update Statistics:                                          │
│   • Win rate                                                 │
│   • Average R:R achieved                                    │
│   • Average confluence for winners vs losers                 │
└──────────────────────────────────────────────────────────────┘
```

---

## Detailed Building Block Logic

### 1. Double Top Pattern (PRIMARY - 35 points)

**Detection Logic:**
```python
1. Scan last 100 bars for two peaks
2. Peaks must have:
   - Similar highs (within 0.2% tolerance)
   - Valley between them
   - Second peak slightly lower okay
3. Pattern confirmed when:
   - Price breaks below valley support
   - Or price rejected at second peak
```

**Signals:**
- `PATTERN_FORMING` (90-100% confidence): M forming, awaiting confirmation
- `BEARISH_BREAKDOWN` (80-95% confidence): Support broken, strong signal

**Confluence Contribution:**
- High confidence (90%+): 32-35 points
- Medium confidence (80-89%): 28-31 points
- Low confidence (70-79%): 25-27 points

### 2. RSI Divergence (CONFIRMATION - 30 points)

**Detection Logic:**
```python
1. Calculate 14-period RSI
2. Compare peaks:
   - Price makes higher high
   - RSI makes lower high
   = Bearish divergence
3. Strong if:
   - RSI > 70 at first peak
   - RSI 60-70 at second peak
```

**Signals:**
- `BEARISH_DIVERGENCE` (85-95% confidence): Classic divergence
- `OVERBOUGHT` (70-85% confidence): RSI > 70 alone

**Confluence Contribution:**
- Bearish divergence: 25-30 points
- Overbought only: 21-25 points

### 3. HOD Level (CONTEXT - 15 points)

**Detection Logic:**
```python
1. Identify high of current day
2. Check price position:
   - AT_HOD: Within 0.1% of HOD
   - REJECTION: Wick showing rejection
   - BELOW_HOD: Trading below HOD
```

**Signals:**
- `REJECTION` (80-100% confidence): Strong rejection wick
- `AT_HOD` (70-85% confidence): Near resistance
- `BELOW_HOD` (60-75% confidence): Below level

**Confluence Contribution:**
- Rejection: 12-15 points
- At HOD: 11-13 points
- Below HOD: 9-11 points

### 4. Asia Session 50% (EQUILIBRIUM - 12 points)

**Detection Logic:**
```python
1. Calculate Asia session range (00:00-08:00 UTC)
2. Find 50% equilibrium level
3. Check if price:
   - Below: Premium zone (bearish)
   - At: Equilibrium
   - Above: Discount zone (neutral for shorts)
```

**Signals:**
- `BELOW_EQUILIBRIUM` (70-90% confidence): In premium
- `AT_EQUILIBRIUM` (60-80% confidence): At midpoint

**Confluence Contribution:**
- Below equilibrium: 8-12 points
- At equilibrium: 7-9 points

### 5. Session Time (TIMING - 10 points)

**Detection Logic:**
```python
1. Check current time:
   - London Open: 08:00-12:00 UTC
   - NY AM: 13:00-17:00 UTC
   - NY PM: 17:00-21:00 UTC
2. Prefer high-volume sessions
```

**Signals:**
- `LONDON_OPEN` (100% confidence): Prime time
- `NY_AM` (100% confidence): Prime time
- `NY_PM` (80% confidence): Less volume

**Confluence Contribution:**
- London/NY AM: 10 points
- NY PM: 8 points

### 6. VWAP (INSTITUTIONAL - 10 points)

**Detection Logic:**
```python
1. Calculate volume-weighted average price
2. Check if price:
   - BELOW_VWAP: Bearish positioning
   - ABOVE_VWAP: Bullish (reduces confluence)
3. Distance from VWAP matters
```

**Signals:**
- `BELOW_VWAP` (70-90% confidence): Bearish context
- `AT_VWAP` (60-75% confidence): Neutral

**Confluence Contribution:**
- Below VWAP: 7-10 points
- At VWAP: 6-8 points

---

## TP/SL Calculation Detail

### Stop Loss Placement

```python
# For M Pattern SHORT:
1. Identify second peak of M pattern
2. Add buffer (0.5 * ATR)
3. SL = peak2_high + buffer

Example:
- Peak 2: $98,000
- ATR: $1,000
- Buffer: $500
- SL: $98,500 ✅

Risk: Entry to SL distance
```

### Take Profit Calculation

```python
# Based on Risk:Reward multiples
risk = sl_price - entry_price

tp1 = entry_price - (risk * 1.5)  # 1.5R
tp2 = entry_price - (risk * 3.0)  # 3.0R
tp3 = entry_price - (risk * 5.0)  # 5.0R

Example:
- Entry: $95,000
- SL: $98,500
- Risk: $3,500

TP Levels:
- TP1: $95,000 - ($3,500 * 1.5) = $89,750 (50% exit)
- TP2: $95,000 - ($3,500 * 3.0) = $84,500 (30% exit)
- TP3: $95,000 - ($3,500 * 5.0) = $77,500 (20% exit)
```

### Partial Exit Logic

```python
Position: 0.263 BTC total

TP1 Hit ($89,750):
- Close: 0.131 BTC (50%)
- Remaining: 0.132 BTC
- Move SL to breakeven

TP2 Hit ($84,500):
- Close: 0.079 BTC (30% of original)
- Remaining: 0.053 BTC (20%)
- Trail SL below entry

TP3 Hit ($77,500):
- Close: 0.053 BTC (remaining 20%)
- Position fully closed
```

---

## Expected Performance Metrics

### Per Trade Expectations

```
Win Scenario (TP2 hit - typical):
- Entry: $95,000
- Exit: $84,500 (TP2)
- Move: -$10,500 (-11.05%)
- With 10x leverage: -110.5% (but on 0.263 BTC)
- Gross Profit: $10,500 * 0.263 = $2,762
- Fees: ~$25
- Net Profit: $2,737 per winning trade ✅

Loss Scenario (SL hit):
- Entry: $95,000
- Exit: $98,500 (SL)
- Move: +$3,500 (+3.68%)
- With 10x leverage: +36.8%
- Gross Loss: $3,500 * 0.263 = $921
- Fees: ~$25
- Net Loss: $946 per losing trade ❌

R:R Analysis:
- Risk: $946
- Reward: $2,737
- Ratio: 1:2.9 ✅ (Target achieved)
```

### Monthly Expectations

```
Trades per month: 2-4 average
Win rate: 65-75%

Conservative Month (2 trades, 65% WR):
- 1.3 winners @ $2,737 = $3,558
- 0.7 losers @ $946 = $662
- Net: +$2,896 (+28.96% monthly) ✅

Average Month (3 trades, 70% WR):
- 2.1 winners @ $2,737 = $5,748
- 0.9 losers @ $946 = $851
- Net: +$4,897 (+48.97% monthly) ✅

Good Month (4 trades, 75% WR):
- 3 winners @ $2,737 = $8,211
- 1 loser @ $946 = $946
- Net: +$7,265 (+72.65% monthly) ✅
```

---

## Risk Management Rules

### Position Sizing
```
Account: $10,000
Risk per trade: 25% = $2,500 margin
Leverage: 10x
Notional: $25,000
Position: 0.263 BTC

Max concurrent positions: 1 (single strategy)
```

### Daily Limits
```
Max trades per day: 1
Max loss per day: $2,000
If daily loss hit: Stop trading for day
```

### Stop Loss Rules
```
NEVER trade without stop loss
SL must be above pattern invalidation
Max risk: 5% of account per trade
Typical risk: 3-4% of account
```

---

## Quality Control Checklist

Before entering ANY trade, verify:

- [ ] Double top pattern clearly visible
- [ ] Both peaks within 0.2% price tolerance
- [ ] RSI divergence confirmed
- [ ] Price rejected at/near HOD
- [ ] Price below Asia 50% equilibrium
- [ ] Session is London or NY
- [ ] Price below VWAP
- [ ] Total confluence >= 70 points
- [ ] R:R ratio >= 2.0
- [ ] SL placement logical
- [ ] TP levels realistic
- [ ] Position size calculated correctly
- [ ] No other active positions

---

## Common Failure Modes

### False M Patterns
- Second peak too far from first (>3 days)
- Peaks not at similar price levels
- No valley between peaks
- Weak rejection on second peak

**Prevention:** Strict pattern validation, 0.2% tolerance

### Premature Entry
- Entering before pattern confirmation
- Entering before valley support breaks
- Entering on first peak

**Prevention:** Wait for BEARISH_BREAKDOWN signal

### Poor R:R
- SL too wide (above pattern by too much)
- TP too conservative (< 2.0R)
- Market ranging (no room for TPs)

**Prevention:** Verify R:R >= 2.0 before entry

---

## Integration with ITM

When Intelligent Trade Manager is deployed:

### ITM Enhancements
1. **Dynamic TP/SL:** Adjust based on market volatility
2. **Position Scaling:** Add to winners on pullbacks
3. **Early Exit:** Cut losers faster if market changes
4. **DCA Logic:** Average in if setup gets stronger

### Signal Handoff
```python
# Strategy emits:
StrategySignal(
    strategy_id='01_M_PATTERN',
    signal_type='ENTRY_SHORT',
    confidence=96/100 = 0.96,
    entry_price=95000,
    tp1=89750,
    tp2=84500,
    tp3=77500,
    sl=98500,
    position_size=0.263,
    reasoning="M Pattern + RSI Div + HOD Rejection..."
)

# ITM receives and may:
- Validate signal quality
- Adjust position size based on portfolio
- Modify TP/SL based on market regime
- Decide final execution
```

---

## Conclusion

This M Pattern Reversal strategy provides:
- ✅ Clear entry criteria (6 building blocks)
- ✅ Defined confluence threshold (70+)
- ✅ Proper risk management (TP/SL ladder)
- ✅ Realistic expectations (2-4 signals/month)
- ✅ Strong R:R ratio (1:3 minimum)
- ✅ Institutional-grade logic

**Key Success Factors:**
1. Pattern quality over quantity
2. Multiple confirmation layers
3. Proper TP/SL placement
4. Patience for high-quality setups

**End of Strategy Flow Documentation**