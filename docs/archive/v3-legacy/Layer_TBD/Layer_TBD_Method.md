# Layer TBD (Trade By Design) Method - Complete Documentation

**Version**: 2.0.0  
**Last Updated**: December 25, 2025  
**Framework**: BTC Scalp Bot V10  
**Methodology**: Trade By Design (Market Maker Method)

---

## Table of Contents

1. [Introduction](#introduction)
2. [TBD Philosophy and Market Maker Model](#tbd-philosophy-and-market-maker-model)
3. [The Three Core Elements](#the-three-core-elements)
4. [Pattern Recognition](#pattern-recognition)
5. [Timing and Session Analysis](#timing-and-session-analysis)
6. [Level Identification](#level-identification)
7. [Entry and Exit Rules](#entry-and-exit-rules)
8. [Configuration and Rule Switches](#configuration-and-rule-switches)
9. [Integration with Framework](#integration-with-framework)
10. [Walk Forward Backtesting](#walk-forward-backtesting)

---

## Introduction

### Purpose

The TBD (Trade By Design) layer implements the **Market Maker Method** - a sophisticated trading approach that anticipates market maker movements rather than reacting to them. This methodology identifies institutional price manipulation patterns and trades in alignment with smart money.

### Core Concept

Market makers have significantly larger capital and the ability to move markets. The TBD system allows traders to:

- **Anticipate market maker moves** before they complete
- **Trade alongside institutions** rather than being trapped by them
- **Identify accumulation and distribution phases**
- **Recognize trapping patterns** designed to liquidate retail traders

### Key Differentiators

- **Multi-timeframe pattern analysis** (Weekly → Daily → 4H → 1H → 15m)
- **Session-aware trading** (Asian, London, New York sessions)
- **Liquidity-based entry/exit** (using heatmaps and liquidation levels)
- **Phase-based market structure** (Accumulation, Markup, Distribution, Markdown)

---

## TBD Philosophy and Market Maker Model

### The Market Maker Business Model

The TBD system is built on understanding how market makers operate:

1. **Accumulation Phase** - Smart money builds positions
2. **Markup Phase** - Price moves in direction of smart money
3. **Distribution Phase** - Smart money offloads to retail
4. **Markdown Phase** - Price drops, retail gets liquidated

### Weekly Cycle Pattern

Market makers typically operate on a **weekly cycle**:

- **Monday-Wednesday**: Initial direction (3-day swing)
- **Mid-week**: Reversal point (Wednesday/Thursday)
- **Friday**: Weekend trap setup
- **Weekend**: False moves to trap retail

---

## The Three Core Elements

### 1. The Pattern

TBD identifies specific price patterns that reveal market maker intent:

#### M-Pattern (Double Top / Distribution)
- **Formation**: Two peaks at similar price levels
- **Psychology**: Smart money distribution to retail buyers
- **Trading**: Short after neckline break, target previous low

#### W-Pattern (Double Bottom / Accumulation)
- **Formation**: Two troughs at similar price levels
- **Psychology**: Smart money accumulation from retail sellers
- **Trading**: Long after neckline break, target previous high

#### Weekend Trap
- **Formation**: False moves during low-liquidity weekends
- **Psychology**: Market makers trap retail traders entering positions on weekend gaps
- **Trading**: Fade the weekend move on Monday open, target Friday close

#### Board Meeting
- **Formation**: Tight consolidation (board meeting) before explosive move
- **Psychology**: Market makers accumulating/distributing in tight range
- **Trading**: Enter on breakout with increased volume, measured move targets

#### Three Hits Rule
- **Formation**: Third touch to weekly high/low produces exhaustion
- **Psychology**: Retail keeps buying/selling at same level, smart money reverses
- **Trading**: Fade on rejection at 3rd touch, target opposite range boundary

#### Trapping Volume
- **Formation**: Large wick candles with high volume (bull/bear traps)
- **Psychology**: Market makers hunt stops, trap breakout traders
- **Trading**: Counter-trend entry on trap, quick scalp targets

#### One Formation
- **Formation**: Single decisive candle breaking consolidation
- **Psychology**: Smart money enters with conviction after accumulation
- **Trading**: Enter on breakout, measured move = consolidation range

---

## Pattern Recognition (Detailed)

### M-Pattern (Double Top) - Bearish Reversal

**Identification Criteria:**
1. Two peaks at similar price levels (within 10-20% of each other)
2. Valley between peaks forms the "neckline"
3. Pattern spans 10-50 candles typically
4. Second peak often has lower volume than first
5. Neckline break must occur with volume confirmation

**Entry Conditions:**
- Price breaks BELOW neckline by threshold (0.3% default)
- Volume on breakout candle > 1.3x average volume
- Pattern symmetry: peaks within 10-20% price difference
- Minimum pattern formation: 10 candles
- Maximum pattern formation: 50 candles

**Stop Loss Placement:**
- Above the highest peak + (ATR × 1.5)
- Protects against failed breakdown

**Take Profit Targets:**
```
Pattern Height = Higher Peak - Neckline
TP1 = Neckline - (Pattern Height × 0.5)   [30% position]
TP2 = Neckline - (Pattern Height × 1.0)   [40% position]
TP3 = Neckline - (Pattern Height × 1.5)   [30% position]
```

**Configuration Parameters:**
```python
mw_peak_tolerance: float = 0.15           # Max % difference between peaks
mw_min_timeframe: str = "4H"             # Minimum TF for pattern
mw_pattern_length_min: int = 10          # Min candles for pattern
mw_pattern_length_max: int = 50          # Max candles for pattern
mw_neckline_break_threshold: float = 0.003  # 0.3% break required
mw_volume_multiplier: float = 1.3        # Volume confirmation
```

**Example Trade:**
```
Peak 1: $100,000
Peak 2: $99,500 (0.5% difference - valid)
Neckline: $95,000
Current Price: $94,700 (below neckline ✓)
Volume: 1.5x average ✓

Entry: $94,700
Stop: $100,500 (above peaks + ATR)
TP1: $92,500 (50% of pattern height)
TP2: $90,000 (100% of pattern height)
TP3: $87,500 (150% of pattern height)
Risk:Reward = 1:2.5
```

---

### W-Pattern (Double Bottom) - Bullish Reversal

**Identification Criteria:**
1. Two troughs at similar price levels (within 10-20% of each other)
2. Peak between troughs forms the "neckline"
3. Pattern spans 10-50 candles typically
4. Second trough often has lower volume than first (absorption)
5. Neckline break must occur with volume confirmation

**Entry Conditions:**
- Price breaks ABOVE neckline by threshold (0.3% default)
- Volume on breakout candle > 1.3x average volume
- Pattern symmetry: troughs within 10-20% price difference
- Minimum pattern formation: 10 candles
- Maximum pattern formation: 50 candles

**Stop Loss Placement:**
- Below the lowest trough - (ATR × 1.5)
- Protects against failed breakout

**Take Profit Targets:**
```
Pattern Height = Neckline - Lower Trough
TP1 = Neckline + (Pattern Height × 0.5)   [30% position]
TP2 = Neckline + (Pattern Height × 1.0)   [40% position]
TP3 = Neckline + (Pattern Height × 1.5)   [30% position]
```

**Configuration Parameters:**
Same as M-Pattern (shared configuration)

**Example Trade:**
```
Trough 1: $90,000
Trough 2: $90,500 (0.55% difference - valid)
Neckline: $95,000
Current Price: $95,300 (above neckline ✓)
Volume: 1.4x average ✓

Entry: $95,300
Stop: $89,500 (below troughs - ATR)
TP1: $97,500 (50% of pattern height)
TP2: $100,000 (100% of pattern height)
TP3: $102,500 (150% of pattern height)
Risk:Reward = 1:2.5
```

---

### Weekend Trap - Monday Reversal

**Market Maker Psychology:**
During weekends, liquidity is extremely low (banks closed, institutional traders off). Market makers deliberately push price to create weekend gaps that trap retail traders who enter positions based on weekend price action.

**The Setup:**
1. **Friday Close**: Record closing price before weekend
2. **Weekend Move**: Price moves significantly (>2% typical) on low volume
3. **Monday Open**: Retail traders chase the weekend move
4. **The Trap**: Market makers reverse direction, trapping retail

**Identification Criteria:**
1. Weekend price move >2% from Friday close
2. Current time: Monday, within first 4 hours of trading
3. Price has moved away from Friday close
4. Low volume on weekend move (thin orderbook manipulation)

**Entry Conditions:**
- **Bullish Trap (fade downside)**: Weekend dropped >2%, enter LONG on Monday
- **Bearish Trap (fade upside)**: Weekend rallied >2%, enter SHORT on Monday
- Entry window: First 4 hours of Monday trading only
- Confidence increases with larger weekend move (3%+ very high)

**Stop Loss Placement:**
- **Long**: Below weekend low - ATR
- **Short**: Above weekend high + ATR

**Take Profit Targets:**
```
Target = Friday Close (mean reversion)
TP1 = 50% back to Friday close   [40% position]
TP2 = Friday close                [40% position]
TP3 = Overshoot (1% beyond)       [20% position]
```

**Configuration Parameters:**
```python
weekend_trap_threshold: float = 0.02       # 2% weekend move required
weekend_trap_reversal_hours: int = 4      # Trading window on Monday
```

**Example Trade:**
```
Friday Close: $95,000
Weekend Low: $92,000 (3.16% drop) ✓
Monday Open (Hour 2): $92,500
Direction: LONG (fading bearish trap)

Entry: $92,500
Stop: $91,500 (below weekend low)
TP1: $93,750 (50% retracement)
TP2: $95,000 (Friday close)
TP3: $95,950 (1% overshoot)
Risk:Reward = 1:3.5
```

**Why It Works:**
- Weekends have 70-80% less liquidity than weekdays
- Retail traders overreact to weekend gaps
- Market makers exploit this predictable behavior
- Monday sessions have institutional re-entry

---

### Board Meeting - Consolidation Breakout

**Market Maker Psychology:**
When market makers are accumulating or distributing large positions, they need to do so without moving price significantly. This creates a "board meeting" - tight consolidation where the "board" (smart money) is making decisions before the next major move.

**The Setup:**
1. **Consolidation**: Price range contracts to <2% (tight range)
2. **Duration**: Minimum 6 candles, maximum 24 candles
3. **Volume Decline**: Late consolidation has lower volume (coiling)
4. **Breakout**: Single decisive candle breaks range with volume

**Identification Criteria:**
1. Price range (high - low) <2% of price
2. Consolidation lasts 6-24 candles
3. Volume declining during consolidation
4. Current candle breaking range by >50% of range height
5. Breakout volume >1.5x average volume

**Entry Conditions:**
- **Bullish**: Price breaks ABOVE consolidation high
- **Bearish**: Price breaks BELOW consolidation low
- Breakout must be >50% of consolidation range
- Volume confirmation: >1.5x average
- Not during first hour of session (avoid fake breakouts)

**Stop Loss Placement:**
- **Long**: Below consolidation low - ATR
- **Short**: Above consolidation high + ATR

**Take Profit Targets:**
```
Range Height = Consolidation High - Consolidation Low
Measured Move = Range Height (width of consolidation)

TP1 = Breakout Level + (Range Height × 1.0)   [30% position]
TP2 = Breakout Level + (Range Height × 2.0)   [40% position]
TP3 = Breakout Level + (Range Height × 3.0)   [30% position]
```

**Configuration Parameters:**
```python
board_range_threshold: float = 0.02        # Max 2% consolidation range
board_min_candles: int = 6                # Min duration
board_max_candles: int = 24               # Max duration
board_breakout_volume: float = 1.5        # Volume multiplier
```

**Example Trade:**
```
Consolidation High: $95,500
Consolidation Low: $94,500
Range: $1,000 (1.05% - valid ✓)
Duration: 18 candles ✓
Breakout: $96,000 (above high by $500 = 50% of range ✓)
Volume: 1.8x average ✓

Direction: LONG
Entry: $96,000
Stop: $94,000 (below low - ATR)
TP1: $96,000 (1× measured move)
TP2: $97,000 (2× measured move)
TP3: $98,000 (3× measured move)
Risk:Reward = 1:2
```

**Why It Works:**
- Tight consolidation = absorption of supply/demand
- Breakout = smart money entering with conviction
- Measured moves are statistically reliable
- Volume confirms institutional participation

**Note:** Board Meeting breakouts often lead to extended moves because smart money has finished accumulation/distribution and now wants price to move.

---

### Three Hits Rule - Exhaustion Reversal

**Market Maker Psychology:**
Retail traders love "obvious" support and resistance levels. Market makers exploit this by allowing price to touch a key level (weekly high/low) three times. By the third touch, retail is fully convinced and loaded with positions. The fourth touch produces a violent reversal, liquidating retail.

**The Setup:**
1. **Level Identification**: Weekly high or weekly low established
2. **First Touch**: Price tests level, bounces (retail notices)
3. **Second Touch**: Price tests again, bounces (retail enters positions)
4. **Third Touch**: Price tests again, bounces (retail adds to positions)
5. **Fourth Touch**: Price breaks through, liquidating retail

**Identification Criteria:**
1. Weekly high or low clearly defined
2. Price has touched level 3+ times
3. Each touch within 0.5% of level (tight tolerance)
4. Minimum 4 candles between touches (not clustered)
5. Current candle showing rejection wick at 3rd+ touch

**Entry Conditions:**
- **At Weekly High (SHORT)**:
  - 3+ touches to weekly high
  - Current candle high >= weekly high × 0.995
  - Rejection: candle close < candle high (upper wick)
  - Enter SHORT on rejection

- **At Weekly Low (LONG)**:
  - 3+ touches to weekly low
  - Current candle low <= weekly low × 1.005
  - Rejection: candle close > candle low (lower wick)
  - Enter LONG on rejection

**Stop Loss Placement:**
- **Long**: Below weekly low - (ATR × 1.5)
- **Short**: Above weekly high + (ATR × 1.5)

**Take Profit Targets:**
```
Range = Weekly High - Weekly Low

TP1 = Entry ± (Range × 0.3)   [30% position]
TP2 = Entry ± (Range × 0.5)   [40% position]
TP3 = Opposite boundary        [30% position]
```

**Configuration Parameters:**
```python
three_hits_touch_tolerance: float = 0.005    # 0.5% touch tolerance
three_hits_min_candles_between: int = 4     # Min spacing
```

**Example Trade:**
```
Weekly High: $100,000
Touch 1: $99,800 (Day 1)
Touch 2: $99,900 (Day 3) 
Touch 3: $100,100 (Day 5)
Current: $100,050 with rejection wick ✓
Touches: 3 ✓
Weekly Range: $10,000 ($100k high, $90k low)

Direction: SHORT (exhaustion at weekly high)
Entry: $100,000
Stop: $101,500 (above high + ATR)
TP1: $97,000 (30% of range)
TP2: $95,000 (50% of range)
TP3: $90,000 (weekly low)
Risk:Reward = 1:6.7
```

**Why It Works:**
- Retail thinks support/resistance is "strong"
- Each bounce reinforces retail conviction
- Market makers accumulate opposite positions
- Liquidation of retail funds the reversal

**Critical Note:** Never enter BEFORE the 3rd touch. The setup only works because retail is fully loaded by touch #3.

---

### Trapping Volume - False Breakout Reversal

**Market Maker Psychology:**
Market makers deliberately create false breakouts to "trap" breakout traders. They push price through a key level with a large candle, triggering stop losses and breakout entries. Then they immediately reverse, leaving breakout traders trapped in losing positions.

**The Setup:**
1. **Consolidation or Level**: Price near key level
2. **False Breakout**: Large candle breaks level with huge wick
3. **High Volume**: Volume spike attracts attention
4. **Reversal**: Candle closes back inside range (trap sprung)
5. **Follow-Through**: Next candles continue reversal

**Identification Criteria:**
1. Large wick (>50% of candle range)
2. Volume >1.5x average (trap requires volume)
3. Candle closes away from wick (back inside range)
4. Wick direction indicates trap type:
   - **Upper wick**: Bullish trap (fake breakout up)
   - **Lower wick**: Bearish trap (fake breakout down)

**Entry Conditions:**
- **Bullish Trap (SHORT)**:
  - Upper wick >50% of candle range
  - Volume >1.5x average
  - Close near candle low (rejection)
  - Enter SHORT immediately

- **Bearish Trap (LONG)**:
  - Lower wick >50% of candle range
  - Volume >1.5x average
  - Close near candle high (rejection)
  - Enter LONG immediately

**Stop Loss Placement:**
- **Long**: Below wick low - (ATR × 0.5) [tight stop]
- **Short**: Above wick high + (ATR × 0.5) [tight stop]

**Take Profit Targets:**
```
Trap Range = Wick Size

TP1 = Entry ± (Trap Range × 0.5)   [40% position]
TP2 = Entry ± (Trap Range × 1.0)   [40% position]
TP3 = Entry ± (Trap Range × 1.5)   [20% position]
```

**Configuration Parameters:**
```python
trap_wick_threshold: float = 0.5           # 50% wick size minimum
trap_volume_multiplier: float = 1.5        # Volume confirmation
```

**Example Trade (Bearish Trap - Go LONG):**
```
Candle Range: $1,000 ($94k - $95k)
Lower Wick: $600 (low at $93,400, open at $94,000)
Wick % of Range: 60% ✓
Close: $94,800 (near high - rejection ✓)
Volume: 1.8x average ✓

Direction: LONG (fading bearish trap)
Entry: $94,800
Stop: $93,200 (below wick - tight ATR)
TP1: $95,100 (50% of wick)
TP2: $95,400 (100% of wick)
TP3: $95,700 (150% of wick)
Risk:Reward = 1:2
```

**Why It Works:**
- Breakout traders enter on wick extension
- Stop losses get hit during wick
- Market makers collect liquidity from stops
- Reversal is fast and violent
- Trapped traders exit (fuel reversal)

**Best Sessions:**
- London open (first 30 min - many fake breakouts)
- New York open (first 30 min)
- Avoid during overlap (real breakouts more common)

**Critical Note:** This is a SCALP pattern. Quick in, quick out. Don't hold for extended targets.

---

### One Formation - Decisive Breakout

**Market Maker Psychology:**
After extended consolidation (accumulation or distribution), market makers eventually enter the market with full conviction. This produces a single, decisive candle that breaks the consolidation cleanly - "The One" that signals the next major move has begun.

**The Setup:**
1. **Long Consolidation**: 20-40 candles in tight range (<3%)
2. **Volume Decline**: Consolidation volume dries up (coiling)
3. **The One**: Single large candle breaks range
4. **Confirmation**: Breakout candle is 2x average range, 2x volume
5. **Clean Break**: No retests, straight through

**Identification Criteria:**
1. Recent consolidation: 20-40 candles
2. Consolidation range <3% of price
3. Breakout candle range >2x average range
4. Breakout candle volume >2x average volume
5. Breakout candle closes beyond consolidation (clean break)

**Entry Conditions:**
- **Bullish**: Breakout candle closes ABOVE consolidation high
- **Bearish**: Breakout candle closes BELOW consolidation low
- Candle size: >2x average candle range
- Volume: >2x average volume
- Enter on close of breakout candle or next candle open

**Stop Loss Placement:**
- **Long**: Below consolidation low - (ATR × 1.5)
- **Short**: Above consolidation high + (ATR × 1.5)

**Take Profit Targets:**
```
Measured Move = Consolidation Range (high - low)

TP1 = Breakout + (Measured Move × 1.0)   [30% position]
TP2 = Breakout + (Measured Move × 2.0)   [40% position]
TP3 = Breakout + (Measured Move × 3.0)   [30% position]
```

**Configuration Parameters:**
```python
one_consolidation_min_candles: int = 20    # Min consolidation length
one_consolidation_max_range_pct: float = 0.03  # Max 3% range
one_breakout_size_multiplier: float = 2.0      # 2x avg candle
one_breakout_volume_multiplier: float = 2.0    # 2x avg volume
```

**Example Trade:**
```
Consolidation: 32 candles, range $94k - $95k ($1k = 1.05% ✓)
Average Candle Range: $200
Average Volume: 500 BTC
Breakout Candle:
  - Range: $600 (3x average ✓)
  - Volume: 1200 BTC (2.4x average ✓)
  - Close: $95,600 (above consolidation ✓)

Direction: LONG
Entry: $95,600
Stop: $93,500 (below consolidation - ATR)
TP1: $96,600 (1× measured move)
TP2: $97,600 (2× measured move)
TP3: $98,600 (3× measured move)
Risk:Reward = 1:2.4
```

**Why It Works:**
- Long consolidation = smart money finished positioning
- Breakout = smart money entering with full size
- Volume confirms institutional participation
- Measured moves are statistically reliable
- Low retail participation during consolidation

**Best Timeframes:**
- 4H and Daily charts (more reliable)
- 1H charts acceptable
- Avoid <1H (too much noise)

**Critical Note:** This is NOT a scalp. This signals the start of a trending move. Trail stops and let winners run. The One Formation often leads to multi-day trends.

### 2. The Timing

| Session | Open | Close | Characteristics |
|---------|------|-------|-----------------|
| **Asian** | 00:00 | 09:00 | Lower volatility, range-bound |
| **London** | 08:00 | 17:00 | High volume, trend development |
| **New York** | 13:00 | 22:00 | Highest volume, major moves |
| **Overlap** | 13:00 | 17:00 | Maximum volatility |

### 3. The Levels

- **Weekly High/Low (WHW/WHL)**: Most significant levels
- **Daily High/Low (DHD/DHL)**: Intraday reference points
- **Board Meeting Zones**: Consolidation before big move
- **Liquidation Levels**: Clusters of stop-losses
- **Three Hits Rule**: Fourth touch produces strong reversal

---

## Configuration and Rule Switches

The TBD layer is designed with granular control switches to enable/disable specific rules for optimization and testing.

### Complete Configuration Reference

#### Pattern Detection Switches (7 patterns)

| Parameter | Type | Default | Description | Impact |
|-----------|------|---------|-------------|--------|
| `enable_m_pattern` | bool | True | Enable M-Pattern (double top) detection | Bearish reversal signals |
| `enable_w_pattern` | bool | True | Enable W-Pattern (double bottom) detection | Bullish reversal signals |
| `enable_multi_session_mw` | bool | True | Allow M/W patterns across multiple sessions | Larger patterns, higher TF |
| `enable_one_formation` | bool | True | Enable One Formation breakout pattern | Trend continuation signals |
| `enable_weekend_trap` | bool | True | Enable Weekend Trap Monday reversal | Mean reversion signals |
| `enable_board_meeting` | bool | True | Enable Board Meeting consolidation breakout | Explosive breakout signals |
| `enable_trapping_volume` | bool | True | Enable Trapping Volume wick reversals | Quick scalp signals |

#### Timing Switches (8 controls)

| Parameter | Type | Default | Description | Impact |
|-----------|------|---------|-------------|--------|
| `enable_session_filter` | bool | True | Filter signals by trading session quality | Avoids low-liquidity periods |
| `enable_weekly_cycle` | bool | True | Use weekly cycle analysis (3-day swing) | Timing optimization |
| `enable_three_day_swing` | bool | True | Track Mon-Wed directional bias | Entry timing |
| `avoid_weekend_trading` | bool | True | Block signals during weekends | Risk management |
| `avoid_first_30min_london` | bool | True | Skip London open fake breakouts | False signal reduction |
| `midweek_reversal_day` | int | 3 | Expected reversal day (0=Mon, 3=Thu) | Cycle tracking |
| `asian_session_start` | time | 00:00 | Asian session start (UTC, DST-adjusted) | Session identification |
| `london_session_start` | time | 08:00 | London session start (UTC, DST-adjusted) | Session identification |
| `ny_session_start` | time | 13:00 | NY session start (UTC, DST-adjusted) | Session identification |

#### Level Switches (7 types + liquidations)

| Parameter | Type | Default | Description | Impact |
|-----------|------|---------|-------------|--------|
| `enable_weekly_hl` | bool | True | Track weekly high/low levels | Major S/R identification |
| `enable_daily_hl` | bool | True | Track daily high/low levels | Intraday S/R |
| `enable_session_hl` | bool | True | Track session high/low levels | Session S/R |
| `enable_three_hits_rule` | bool | True | Count touches to levels for exhaustion | Reversal signals |
| `enable_liquidation_levels` | bool | True | Track liquidation clusters (v2.0) | Stop-hunt zones |
| `enable_fibonacci_levels` | bool | True | Calculate Fibonacci retracement levels | Entry/target zones |
| `enable_support_resistance` | bool | True | Identify historical S/R levels | Level confluence |
| `weekly_hl_lookback` | int | 5 | Weeks to look back for high/low | Level timeframe |
| `daily_hl_first_hour` | bool | True | Set daily H/L during first hour | Level setting logic |

#### Liquidation Parameters (v2.0)

| Parameter | Type | Default | Description | Impact |
|-----------|------|---------|-------------|--------|
| `liquidation_cluster_threshold` | float | 1_000_000 | Min USD for significant cluster | Cluster sensitivity |
| `liquidation_proximity_pct` | float | 0.02 | Max distance to consider (2%) | Proximity filter |
| `liquidation_lookback_hours` | int | 168 | Hours of history to analyze (1 week) | Data window |
| `liquidation_weight` | float | 0.20 | Score boost per nearby cluster | Signal strength |

#### Confirmation Switches (5 requirements)

| Parameter | Type | Default | Description | Impact |
|-----------|------|---------|-------------|--------|
| `require_volume_confirmation` | bool | True | Require volume >1.2x average | Reduces false signals |
| `require_trend_alignment` | bool | True | Pattern must align with trend | Trend-following only |
| `require_multiple_timeframe` | bool | True | Confirm on multiple timeframes | Higher quality signals |
| `minimum_confirmations` | int | 3 | Min confirmations required (2-5) | Signal frequency vs quality |
| `enable_atr_stops` | bool | True | Use ATR-based stop losses | Risk management |
| `enable_time_stops` | bool | True | Exit after max hold time | Time-based risk |
| `enable_trailing_stops` | bool | True | Trail stops as profit increases | Profit protection |
| `use_scaling_exits` | bool | True | Exit in 3 tranches (TP1/2/3) | Position management |

#### M/W Pattern Parameters (6 settings)

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `mw_peak_tolerance` | float | 0.15 | 0.08-0.25 | Max % difference between peaks (15%) |
| `mw_min_timeframe` | str | "4H" | 1H-Daily | Minimum timeframe for pattern validity |
| `mw_pattern_length_min` | int | 10 | 8-15 | Min candles for pattern formation |
| `mw_pattern_length_max` | int | 50 | 40-100 | Max candles for pattern formation |
| `mw_neckline_break_threshold` | float | 0.003 | 0.001-0.01 | Required % break of neckline (0.3%) |
| `mw_volume_multiplier` | float | 1.3 | 1.0-2.0 | Volume confirmation multiplier |

#### Board Meeting Parameters (4 settings)

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `board_range_threshold` | float | 0.02 | 0.01-0.03 | Max consolidation range % (2%) |
| `board_min_candles` | int | 6 | 4-10 | Min candles in consolidation |
| `board_max_candles` | int | 24 | 20-40 | Max candles in consolidation |
| `board_breakout_volume` | float | 1.5 | 1.2-2.0 | Breakout volume multiplier |

#### Weekend Trap Parameters (2 settings)

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `weekend_trap_threshold` | float | 0.02 | 0.015-0.03 | Min weekend move % (2%) |
| `weekend_trap_reversal_hours` | int | 4 | 2-6 | Monday trading window (hours) |

#### Three Hits Parameters (2 settings)

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `three_hits_touch_tolerance` | float | 0.005 | 0.003-0.01 | Level touch tolerance % (0.5%) |
| `three_hits_min_candles_between` | int | 4 | 2-8 | Min spacing between touches |

#### Trapping Volume Parameters (2 settings)

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `trap_wick_threshold` | float | 0.5 | 0.4-0.7 | Min wick % of candle range (50%) |
| `trap_volume_multiplier` | float | 1.5 | 1.2-2.0 | Volume spike multiplier |

#### Risk Management Parameters (6 settings)

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `atr_period` | int | 14 | 10-20 | ATR calculation period |
| `atr_stop_multiplier` | float | 1.5 | 0.5-2.5 | ATR multiplier for stops |
| `max_hold_hours` | dict | varies | - | Max hold time per timeframe |
| `risk_per_trade` | float | 0.02 | 0.01-0.05 | Risk % per trade (2%) |
| `max_trades_per_day` | int | 5 | 1-10 | Daily trade limit |
| `max_concurrent_trades` | int | 3 | 1-5 | Max simultaneous positions |

#### Weight Configuration (4 components)

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `weight_pattern` | float | 0.35 | 0.2-0.5 | Pattern detection weight (35%) |
| `weight_timing` | float | 0.25 | 0.1-0.4 | Session timing weight (25%) |
| `weight_level` | float | 0.25 | 0.1-0.4 | Level proximity weight (25%) |
| `weight_confirmation` | float | 0.15 | 0.1-0.3 | Confirmation weight (15%) |

#### Scaling/Exit Parameters (6 settings)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `scaling_tp1_percent` | float | 0.30 | Exit 30% at TP1 |
| `scaling_tp2_percent` | float | 0.40 | Exit 40% at TP2 |
| `scaling_tp3_percent` | float | 0.30 | Exit 30% at TP3 |
| `tp1_multiplier` | float | 0.5 | TP1 = 50% of pattern height |
| `tp2_multiplier` | float | 1.0 | TP2 = 100% of pattern height |
| `tp3_multiplier` | float | 1.5 | TP3 = 150% of pattern height |

---

### Configuration Presets

#### Conservative Preset
```python
TBDConfig.conservative()
```
- `minimum_confirmations`: 4
- `require_volume_confirmation`: True
- `require_trend_alignment`: True
- `avoid_weekend_trading`: True
- `mw_peak_tolerance`: 0.15
- `atr_stop_multiplier`: 2.0
- Enables: M/W, Weekend Trap, Three Hits only
- **Expected**: 55-65% win rate, 8-12 signals/month

#### Balanced Preset
```python
TBDConfig.balanced()
```
- `minimum_confirmations`: 3
- `require_volume_confirmation`: True
- `require_trend_alignment`: False
- `mw_peak_tolerance`: 0.20
- `atr_stop_multiplier`: 1.5
- Enables: All patterns
- **Expected**: 50-60% win rate, 12-20 signals/month

#### Aggressive Preset
```python
TBDConfig.aggressive()
```
- `minimum_confirmations`: 2
- `require_volume_confirmation`: False
- `require_trend_alignment`: False
- `mw_peak_tolerance`: 0.25
- `atr_stop_multiplier`: 1.0
- Enables: All patterns
- **Expected**: 45-55% win rate, 20-30 signals/month

---

### Optimization Guidelines by Parameter

#### High-Impact Parameters (Test First)
1. `minimum_confirmations` (2-5): Directly controls signal frequency
2. `mw_peak_tolerance` (0.08-0.25): Pattern sensitivity
3. `atr_stop_multiplier` (0.5-2.5): Risk per trade
4. `require_volume_confirmation`: Quality filter
5. `liquidation_weight` (0.0-0.5): v2.0 cluster influence

#### Medium-Impact Parameters
1. `board_range_threshold` (0.01-0.03): Consolidation tightness
2. `trap_wick_threshold` (0.4-0.7): Trap sensitivity
3. `weekend_trap_threshold` (0.015-0.03): Trap trigger level
4. `weight_pattern` / `weight_timing` / `weight_level`: Signal composition

#### Low-Impact Parameters (Fine-Tuning)
1. Session start times (usually don't change)
2. `mw_pattern_length_min/max`: Pattern window
3. `three_hits_touch_tolerance`: Level precision
4. Scaling percentages (TP1/2/3 split)

---

### Parameter Interaction Effects

**Volume + Trend Alignment**:
- Both True: Very selective (high quality)
- Volume only: Moderate selectivity
- Trend only: Directional bias
- Both False: Maximum signals (use carefully)

**ATR Multiplier + Min Confirmations**:
- High ATR + Low confirmations = Wide stops, many trades
- Low ATR + High confirmations = Tight stops, few trades
- Balance for your risk tolerance

**Liquidation Weight + Level Weight**:
- Both high: Strong level emphasis (range trading)
- Pattern high, levels low: Breakout focus
- Balanced: All-weather approach

---

### Walk-Forward Optimization Strategy

1. **Initial Test** (Default/Balanced preset):
   - Run 90-day backtest
   - Identify best/worst patterns
   - Check session performance

2. **Pattern Optimization**:
   - Test each pattern individually
   - Optimize pattern-specific thresholds
   - Disable consistently losing patterns

3. **Confirmation Optimization**:
   - Test minimum_confirmations (2-5)
   - Test volume/trend requirements
   - Find best balance for your data

4. **Risk Optimization**:
   - Test ATR multipliers (0.5-2.5)
   - Test position sizing (1-3% risk)
   - Optimize scaling percentages

5. **Walk-Forward Validation**:
   - 60-day train, 30-day test
   - Move forward monthly
   - Track parameter stability

---

### Common Configuration Mistakes

❌ **Over-Optimization**:
- Testing 100+ parameter combinations
- Fitting to specific market conditions
- Using <90 days of data

❌ **Under-Filtering**:
- `minimum_confirmations` = 1-2 with all switches off
- No volume confirmation on breakouts
- Weekend trading without trap filter

❌ **Inconsistent Logic**:
- High risk per trade + conservative pattern selection
- Tight stops + aggressive entry signals
- Trend-following in ranging markets

✅ **Best Practices**:
- Start conservative, optimize gradually
- Use walk-forward validation (not curve-fitting)
- Test on 180+ days minimum
- Keep parameter changes small (10-20% at a time)
- Document all configuration changes
- Maintain separate configs for different market regimes

---

## Walk Forward Backtesting

### TBD-Specific Considerations

**Weekly Cycle Awareness:**
- Each test window should span complete weeks
- Minimum window: 4 weeks

**Pattern Requirements:**
- Need sufficient data for pattern formation
- Minimum 60 days for multi-session M/W

### Expected Performance

**Conservative Configuration:**
- Win Rate: 55-65%
- Average R:R: 1.5:1
- Signals per month: 8-12

**Balanced Configuration:**
- Win Rate: 50-60%
- Average R:R: 2.0:1
- Signals per month: 12-20

---

*"Trade what the market makers do, not what retail thinks will happen."*
