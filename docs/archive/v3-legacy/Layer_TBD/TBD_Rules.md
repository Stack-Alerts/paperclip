# TBD Rules - Complete Entry, Management, and Exit Conditions

**Version**: 2.0.0  
**Last Updated**: December 25, 2025  
**Purpose**: Comprehensive rule checklist for TBD layer implementation

---

## Entry Conditions

### Universal Entry Requirements

**Before ANY trade entry, ALL of the following must be TRUE:**

- [ ] **R1**: Account has sufficient capital for position
- [ ] **R2**: No conflicting position currently open
- [ ] **R3**: Daily loss limit not exceeded
- [ ] **R4**: Maximum open positions limit not reached
- [ ] **R5**: Spread < 0.1% (reasonable execution cost)

### Session Timing Rules (DST Auto-Adjusting)

**The system automatically adjusts for Daylight Saving Time. Session times below reflect UTC offsets that change based on DST status.**

**Winter Sessions (November - March):**
- [ ] **ST1-W**: Asian Session (23:00-08:00 UTC) - LOW priority
  - Japan has no DST, times constant year-round
  - Use for position monitoring only
  - Avoid new entries unless high-confidence setup
  
- [ ] **ST2-W**: London Session (08:00-17:00 UTC) - HIGH priority (GMT)
  - Skip first 30 minutes (08:00-08:30) - low liquidity
  - Best entry window: 08:30-12:00 UTC
  - Major European liquidity
  
- [ ] **ST3-W**: New York Session (13:00-22:00 UTC) - HIGH priority (EST)
  - Highest volatility period
  - Best entry window: 13:00-18:00 UTC
  - US market hours
  
- [ ] **ST4-W**: UK/US Overlap (13:00-17:00 UTC) - MAXIMUM priority
  - Peak global liquidity
  - Tightest spreads
  - Most reliable pattern execution

**Summer Sessions (March - November):**
- [ ] **ST1-S**: Asian Session (23:00-08:00 UTC) - LOW priority (unchanged)
  
- [ ] **ST2-S**: London Session (07:00-16:00 UTC) - HIGH priority (BST)
  - **1 hour earlier than winter** (BST = GMT-1)
  - Skip first 30 minutes (07:00-07:30)
  - Best entry window: 07:30-11:00 UTC
  - Auto-adjusts after last Sunday in March
  
- [ ] **ST3-S**: New York Session (12:00-21:00 UTC) - HIGH priority (EDT)
  - **1 hour earlier than winter** (EDT = EST-1)
  - Best entry window: 12:00-17:00 UTC
  - Auto-adjusts after 2nd Sunday in March
  
- [ ] **ST4-S**: UK/US Overlap (12:00-16:00 UTC) - MAXIMUM priority
  - **1 hour earlier than winter**
  - Peak global liquidity maintained

**DST Transition Rules:**
- [ ] **ST5**: UK transitions on last Sunday in March (spring forward)
- [ ] **ST6**: UK transitions on last Sunday in October (fall back)
- [ ] **ST7**: US transitions on 2nd Sunday in March (spring forward)
- [ ] **ST8**: US transitions on 1st Sunday in November (fall back)
- [ ] **ST9**: System automatically detects and adjusts - no manual intervention required

**Session Priority Multipliers:**
- Asian only: 0.3x confidence multiplier (reduce position size or skip)
- London/NY: 1.0x confidence multiplier (standard trading)
- UK/US Overlap: 1.5x confidence multiplier (preferred entry window)
- Weekend: 0.5x confidence multiplier (optional - can disable weekend trading)

**Weekly Timing Preferences:**
- [ ] **ST10**: Monday 00:00-08:00 UTC: Weekend Trap detection period
- [ ] **ST11**: Tuesday-Thursday: Primary trading days (highest consistency)
- [ ] **ST12**: Friday after 16:00 UTC: Reduce activity (weekend positioning)
- [ ] **ST13**: Saturday-Sunday: Optional (enable via `avoid_weekend_trading=False`)

### Pattern Confirmation Requirements

**Minimum confirmations required (configurable: 2-5):**

- [ ] **P1**: Valid pattern identified (M, W, One Formation, etc.)
- [ ] **P2**: Pattern at key level (weekly/daily high/low, S/R)
- [ ] **P3**: Volume confirmation (> 1.2x average on signal)
- [ ] **P4**: Timeframe alignment (consistent across 2+ timeframes)
- [ ] **P5**: Trend alignment (direction matches higher TF trend)

---

## Entry Conditions by Pattern Type

### M-Pattern Entry Conditions

**Formation Requirements:**
- [ ] **M1**: Two peaks identified
- [ ] **M2**: Peaks within 15% price range of each other
- [ ] **M3**: Valley between peaks > 5% depth from neckline
- [ ] **M4**: Timeframe >= 4H (configurable)
- [ ] **M5**: Pattern completion time: 10-50 candles

**Entry Trigger:**
- [ ] **M6**: Price breaks BELOW neckline
- [ ] **M7**: Breakdown candle is bearish (close < open)
- [ ] **M8**: Volume on breakdown > 1.3x average
- [ ] **M9**: Close is at least 0.3% below neckline

**Entry Execution:**
- **Aggressive**: Market order on breakdown candle close
- **Conservative**: Limit order at neckline retest
- **Stop Loss**: Above second peak + (1.5 * ATR)
- **Take Profit 1**: Neckline - 0.5x pattern height
- **Take Profit 2**: Neckline - 1.0x pattern height
- **Take Profit 3**: Neckline - 1.5x pattern height

### W-Pattern Entry Conditions

**Formation Requirements:**
- [ ] **W1**: Two troughs identified
- [ ] **W2**: Troughs within 15% price range of each other
- [ ] **W3**: Peak between troughs > 5% height above neckline
- [ ] **W4**: Timeframe >= 4H (configurable)
- [ ] **W5**: Pattern completion time: 10-50 candles

**Entry Trigger:**
- [ ] **W6**: Price breaks ABOVE neckline
- [ ] **W7**: Breakout candle is bullish (close > open)
- [ ] **W8**: Volume on breakout > 1.3x average
- [ ] **W9**: Close is at least 0.3% above neckline

**Entry Execution:**
- **Aggressive**: Market order on breakout candle close
- **Conservative**: Limit order at neckline retest
- **Stop Loss**: Below second trough - (1.5 * ATR)

### Weekend Trap Entry Conditions

**Friday Analysis:**
- [ ] **WT1**: Friday close price identified
- [ ] **WT2**: Friday closing candle direction noted
- [ ] **WT3**: End-of-week sentiment assessed

**Monday Entry Trigger:**
- [ ] **WT7**: Monday 1st-4th hour shows reversal
- [ ] **WT8**: Price reverses back toward Friday close
- [ ] **WT9**: Reversal candle closes past Friday close level
- [ ] **WT10**: Volume increases on reversal candle

### Board Meeting Breakout Entry Conditions

**Consolidation Identification:**
- [ ] **BM1**: Price range < 2% for at least 6 candles
- [ ] **BM2**: Volume declining through consolidation
- [ ] **BM3**: Duration: 6-24 candles (timeframe dependent)
- [ ] **BM4**: Consolidation at key level

**Breakout Trigger:**
- [ ] **BM5**: Price breaks consolidation range (> 0.5% outside)
- [ ] **BM6**: Breakout candle closes outside range
- [ ] **BM7**: Volume on breakout > 1.5x average

### Three Hits Reversal Entry Conditions

**Hit Counting:**
- [ ] **TH1**: Weekly or Daily high/low identified
- [ ] **TH2**: Price has touched level 3 times
- [ ] **TH3**: Each touch shows rejection (wick extends past level)
- [ ] **TH4**: Touch defined as: Price within 0.5% of level

**Reversal Trigger:**
- [ ] **TH6**: Third touch produces strong rejection candle
- [ ] **TH7**: Rejection candle closes away from level (> 0.5%)
- [ ] **TH8**: Volume on rejection > 1.2x average

---

## Position Management

### Position Sizing Rules

**Base Position Size:**
```python
risk_per_trade = 0.02  # 2%
risk_amount = account_balance * risk_per_trade
position_size = risk_amount / (entry_price - stop_loss)
```

**Adjustments Based on Confidence:**
- [ ] **PS1**: High confidence (> 0.8): Use full calculated size
- [ ] **PS2**: Medium confidence (0.6-0.8): Use 75% of size
- [ ] **PS3**: Low confidence (< 0.6): Use 50% of size or avoid

### Trailing Stop Management

**Breakeven Stop:**
- [ ] **TS1**: Move stop to breakeven when position reaches 1:1 R:R
- [ ] **TS2**: Add small buffer (0.1%) to avoid premature stop

**Progressive Trailing:**
- [ ] **TS3**: At 1.5:1 R:R → Trail stop to 0.5:1 lock-in
- [ ] **TS4**: At 2:1 R:R → Trail stop to 1:1 lock-in
- [ ] **TS5**: At 3:1 R:R → Trail stop to 2:1 lock-in

---

## Exit Conditions

### Take Profit Exits (Partial)

**Target 1 (30% of position):**
- [ ] **TP1**: Price reaches first target (0.5-1.0x pattern height)

**Target 2 (40% of position):**
- [ ] **TP4**: Price reaches second target (1.0-1.5x pattern height)

**Target 3 (30% runner):**
- [ ] **TP7**: Use trailing stop

### Stop Loss Exits (Full Position)

**Hard Stop Triggered:**
- [ ] **SL1**: Price touches stop loss level
- [ ] **SL2**: Exit immediately, no hesitation
- [ ] **SL3**: Market order for immediate execution

### Time-Based Exits

**Maximum Hold Time:**
- [ ] **TE1**: Pattern hasn't played out in expected time
- [ ] **TE2**: Timeframe-dependent: 
  - 15m patterns: 4 hours max
  - 1H patterns: 24 hours max
  - 4H patterns: 3 days max

---

## Risk Management Rules

### Account-Level Rules

- [ ] **RM1**: Maximum risk per trade: 2% of account
- [ ] **RM2**: Maximum daily loss: 6% of account
- [ ] **RM3**: Maximum weekly loss: 10% of account
- [ ] **RM4**: Maximum open positions: 5 (configurable)

### Position-Level Rules

- [ ] **RM6**: Stop loss always set before entry
- [ ] **RM7**: Position size calculated from stop distance
- [ ] **RM8**: Never move stop loss against position
- [ ] **RM9**: Never remove stop loss

---

## Configuration Templates

### Conservative Template

```python
{
    "minimum_confirmations": 4,
    "require_volume_confirmation": True,
    "require_trend_alignment": True,
    "risk_per_trade": 0.01,  # 1%
}
```

**Expected**: 55-65% win rate, 8-12 signals/month

### Balanced Template

```python
{
    "minimum_confirmations": 3,
    "require_volume_confirmation": True,
    "require_trend_alignment": False,
    "risk_per_trade": 0.02,  # 2%
}
```

**Expected**: 50-60% win rate, 12-20 signals/month

---

*"Rules are the edge. Discipline is the profit."*
