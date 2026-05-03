# TBD Method Logic & Rule Evaluation System - Markdown Diagram

## Overview

This document details the rule evaluation logic and confirmation counting system for the TBD Method Layer.

---

## Level Tracking Rules

### Weekly High/Low Update

```
TRIGGER: Check if new week?

┌─────────────────────────────────┐
│  Is it a new week?              │
└────┬─────────────────┬──────────┘
     │                 │
  YES│                 │NO
     ▼                 ▼
┌──────────────┐  ┌──────────────┐
│ UPDATE       │  │ USE EXISTING │
│ WEEKLY H/L   │  │ WEEKLY H/L   │
└────┬─────────┘  └──────┬───────┘
     │                   │
     │ Lookback:         │
     │ 5 days (120 hrs)  │
     │                   │
     │ Set:              │
     │ • Weekly High =   │
     │   max(high)       │
     │ • Weekly Low =    │
     │   min(low)        │
     │                   │
     │ Reset:            │
     │ • Touch count = 0 │
     │                   │
     └────────┬──────────┘
              ▼
     ┌──────────────────┐
     │ Ready for 3-Hits │
     │ Rule Tracking    │
     └──────────────────┘

USED FOR: 3-Hits Rule, Level-based entries, Target calculation
UPDATED: Once per week
STORED: weekly_high, weekly_low, weekly_high_touches, weekly_low_touches
```

### Daily High/Low Identification

```
TRIGGER: Check if first hour London session?

┌────────────────────────────────────┐
│  Is it first hour London (08:00)?  │
└────┬───────────────────┬───────────┘
     │                   │
  YES│                   │NO
     ▼                   ▼
┌──────────────────┐ ┌──────────────────┐
│ SET DAILY H/L    │ │ UPDATE DAILY H/L │
│ FROM OPENING     │ │ WITH CURRENT     │
│ CANDLE           │ │ HIGH/LOW         │
└───┬──────────────┘ └────┬─────────────┘
    │                     │
    │ • Daily High =      │ • Daily High =
    │   candle_high       │   max(prev_high,
    │ • Daily Low =       │       current_high)
    │   candle_low        │ • Daily Low =
    │                     │   min(prev_low,
    │ • Mark as           │       current_low)
    │   "levels_set"      │
    │                     │
    └──────────┬──────────┘
               ▼
    ┌──────────────────────┐
    │ Continue throughout  │
    │ rest of trading day  │
    └──────────────────────┘

RATIONALE: London open sets tone for entire day
USED FOR: Intraday level-based entries, momentum confirmation
UPDATED: Continuously throughout trading day
STORED: daily_high, daily_low
```

### Three-Hits Rule Touch Tracking

```
FOR EACH NEW CANDLE:

┌──────────────────────────────────────┐
│  Check if near Weekly High?          │
└────┬───────────────────┬─────────────┘
     │                   │
  YES│                   │NO
     ▼                   ▼
┌──────────────────┐ ┌──────────────┐
│ Within ±0.5%?    │ │ Not near WH  │
└────┬─────────────┘ └──────────────┘
     │
     ▼
┌──────────────────────────┐
│ AND candle closes        │
│ below high (rejection)?  │
└────┬──────────┬──────────┘
     │          │
  YES│          │NO
     ▼          ▼
┌────────────┐  │
│INCREMENT   │  │
│touch_count │  │
└────┬───────┘  │
     │          │
     └────┬─────┘
          ▼
    ┌──────────────────┐
    │ Continue         │
    │ monitoring       │
    └──────────────────┘

TOLERANCE: ±0.5% (configurable)
INTERPRETATION:
├─ 1st touch: Level acknowledged
├─ 2nd touch: Level gaining strength
├─ 3rd touch: EXHAUSTION → Reversal setup
└─ 4+ touches: Pattern still valid

STORED: weekly_high_touches, weekly_low_touches
USED FOR: Three Hits Reversal pattern detection
```

### Weekend Trap Close Storage

```
TRIGGER: Check if Friday?

┌──────────────────────────────┐
│  Is it Friday PM (>22:00)?   │
└────┬──────────────┬──────────┘
     │              │
  YES│              │NO
     ▼              ▼
┌─────────────┐  ┌──────────────┐
│ STORE       │  │ USE EXISTING │
│ Friday      │  │ Friday Close │
│ Close Price │  │              │
└────┬────────┘  └──────┬───────┘
     │                  │
     │ Store Value:     │
     │ friday_close =   │
     │ current_close    │
     │                  │
     │ Use For:         │
     │ Weekend Trap     │
     │ Monday Detection │
     │                  │
     └────────┬─────────┘
              ▼
     ┌──────────────────┐
     │ Monday: Check    │
     │ if reversal      │
     │ happening        │
     └──────────────────┘

TIMING: Captured Friday PM
USED FOR: Weekend Trap detection on Monday morning
STORED: friday_close
```

---

## Timing Analysis Scoring

### Session Identification & Scoring

```
DETERMINE: What is current UTC hour?

┌──────────────────────────────────────────────────────┐
│  Current Hour in UTC Range?                          │
└────┬──────┬─────────┬──────┬───────────┬────────────┘
     │      │         │      │           │
    00-08  08-17    13-22   13-17    Sat-Sun
     │      │         │      │           │
     ▼      ▼         ▼      ▼           ▼

┌────────┐┌─────────┐┌──────┐┌────────┐┌────────┐
│ ASIAN  ││ LONDON  ││  NY  ││OVERLAP ││WEEKEND│
│ 00:00  ││ 08:00   ││13:00 ││13:00   ││ Sat   │
│ 09:00  ││ 17:00   ││22:00 ││17:00   ││ Sun   │
└────────┘└────┬────┘└──────┘└────────┘└────────┘
               │
          Check:
          First 30 min?
               │
    ┌──────────┴───────────┐
    │                      │
   YES                     NO
    │                      │
    ▼                      ▼
 0.2                     0.9
 AVOID                GOOD TIME

SCORING TABLE:

┌──────────────┬────────┬──────────────────┐
│   Session    │ Score  │   Time (UTC)     │
├──────────────┼────────┼──────────────────┤
│ ASIAN        │  0.3   │ 00:00-09:00      │
│ (Low Quality)│        │                  │
├──────────────┼────────┼──────────────────┤
│ LONDON EARLY │  0.2   │ 08:00-08:30      │
│ (Avoid)      │        │ (Volatile Entry) │
├──────────────┼────────┼──────────────────┤
│ LONDON       │  0.9   │ 08:30-17:00      │
│ (High)       │        │ (After 30min)    │
├──────────────┼────────┼──────────────────┤
│ NEW YORK     │  0.85  │ 13:00-22:00      │
│ (High)       │        │                  │
├──────────────┼────────┼──────────────────┤
│ OVERLAP      │  1.0   │ 13:00-17:00      │
│ (MAXIMUM)    │        │ (Both open)      │
├──────────────┼────────┼──────────────────┤
│ WEEKEND      │  0.1   │ Saturday-Sunday  │
│ (Very Low)   │        │ (Avoid except    │
│              │        │  Weekend Trap)   │
└──────────────┴────────┴──────────────────┘

WEEKLY CYCLE BONUS:
├─ Monday: +0.1 (Trap reversals)
├─ Tuesday: +0.1
├─ Wednesday: +0.1 (Mid-week action)
├─ Thursday: +0.1
├─ Friday: +0.1 (End of week)
└─ Weekend: Special handling

FINAL TIMING SCORE: 0.0 to 1.0
USED FOR: Confirmation filter (need > 0.6)
```

### Timing Score Interpretation

```
Score     Interpretation          Trading Recommendation
─────────────────────────────────────────────────────────
1.0       MAXIMUM QUALITY         Take it - Best time
0.85-0.9  VERY GOOD              Take it - Great time
0.7-0.8   GOOD                   Take it - OK time
0.6-0.7   ACCEPTABLE             Risky - Marginal time
0.3-0.6   LOWER QUALITY          Avoid - Poor time
<0.3      VERY LOW QUALITY       DO NOT TRADE
```

---

## Level Analysis Scoring

### Weekly Level Proximity

```
CALCULATE: Distance from current price to weekly levels

┌────────────────────────────────────────┐
│ Distance = |Price - Level| / Price     │
│                                        │
│ For both Weekly High AND Weekly Low    │
│ Take minimum distance                  │
└────────┬───────────────────────────────┘
         │
    ┌────┴────┬──────────┬──────┐
    │         │          │      │
   <1%      <2%        <5%     >5%
    │         │          │      │
    ▼         ▼          ▼      ▼
   +0.3     +0.2       +0.1    +0.0

INTERPRETATION:
├─ Within 1%: Price at critical level (+0.3)
├─ Within 2%: Approaching level (+0.2)
├─ Within 5%: Near level (+0.1)
└─ Far away: Not relevant (0.0)

REASON: Prices near key levels have higher reversal/breakout probability
```

### Daily Level Proximity

```
CALCULATE: Distance from current price to daily levels

┌────────────────────────────────────────┐
│ Same calculation as weekly but more    │
│ sensitive (tighter tolerance)          │
└────────┬───────────────────────────────┘
         │
    ┌────┴────┬──────┐
    │         │      │
  <0.5%     <1%    >1%
    │         │      │
    ▼         ▼      ▼
   +0.2     +0.1    +0.0

INTERPRETATION:
├─ Within 0.5%: Very close to daily level (+0.2)
├─ Within 1%: Close to daily level (+0.1)
└─ Far away: Not relevant (0.0)

REASON: Daily levels important intraday
```

### Combined Level Score

```
FINAL LEVEL SCORE = Weekly Points + Daily Points

Range: 0.0 (no levels) to 1.0 (multiple levels hit)

Typical Scenarios:
├─ At weekly + daily level: 0.5 (strong)
├─ Near weekly level only: 0.3 (moderate)
├─ Far from levels: 0.0 (weak)

USED FOR: Confirmation filter (need > 0.6)
```

---

## Confirmation Counting System

### Confirmation Type 1: Pattern Confirmation

```
IF pattern detected in Stage 5:
    ├─ Points = 1
    └─ CONFIRMED

ELSE:
    ├─ Points = 0
    └─ NOT CONFIRMED

REQUIREMENT: Minimum 2-5 confirmations needed
```

### Confirmation Type 2: Timing Confirmation

```
CHECK: Timing Score > 0.6?

┌──────────────────────┐
│ Timing Score > 0.6?  │
└────┬─────────────────┘
     │
  ┌──┴──┐
  │     │
 YES    NO
  │     │
  ▼     ▼
 +1    +0

REQUIREMENT: Needed for quality signal
IMPLICATION: Good trading hour window
```

### Confirmation Type 3: Level Confirmation

```
CHECK: Level Score > 0.6?

┌──────────────────────┐
│ Level Score > 0.6?   │
└────┬─────────────────┘
     │
  ┌──┴──┐
  │     │
 YES    NO
  │     │
  ▼     ▼
 +1    +0

REQUIREMENT: Needed for quality signal
IMPLICATION: Price near important level
```

### Confirmation Type 4: Volume Confirmation (Optional)

```
IF require_volume_confirmation = True:
    
    CHECK: Current Volume > Average Volume × Multiplier?
    
    Multiplier values:
    ├─ M/W Patterns: 1.3x
    ├─ Board Meeting: 1.5x
    ├─ One Formation: 2.0x
    └─ Trapping Volume: 1.5x
    
    ┌──────────────────────┐
    │ Volume > Avg × Mult? │
    └────┬─────────────────┘
         │
      ┌──┴──┐
      │     │
     YES    NO
      │     │
      ▼     ▼
     +1    +0

ELSE:
    ├─ Skip this confirmation
    └─ Points = not counted

REQUIREMENT: Improves signal quality
IMPLICATION: Institutional participation
```

### Confirmation Type 5: Trend Confirmation (Optional)

```
IF require_trend_alignment = True:
    
    DETERMINE: Current Trend
    
    ┌────────────────────────────┐
    │ Use SMA(50) for trend      │
    └────┬──────────────────┬────┘
         │                  │
    Price >             Price <
    SMA×1.02            SMA×0.98
         │                  │
         ▼                  ▼
    Trend = UP         Trend = DOWN
         │                  │
    CHECK: Pattern direction matches trend?
    
    ┌─────────────────────────────────┐
    │ LONG pattern + UP trend? → +1   │
    │ SHORT pattern + DOWN trend? → +1│
    │ Otherwise → 0                   │
    └─────────────────────────────────┘

ELSE:
    ├─ Skip this confirmation
    └─ Points = not counted

REQUIREMENT: Improves signal reliability
IMPLICATION: Pattern aligns with trend
```

### Confirmation Count Decision

```
TOTAL CONFIRMATIONS = Sum of all enabled confirmations

Range: 1/5 to 5/5 (depending on config)

CHECK: Does total meet minimum?

┌────────────────────────────────────┐
│ confirmations_met >= minimum?      │
└────┬──────────────┬────────────────┘
     │              │
    YES             NO
     │              │
     ▼              ▼
CONTINUE      NEUTRAL SIGNAL
Processing    (No setup)

MINIMUM BY CONFIGURATION:

┌────────────────┬─────────┬───────────┐
│ Configuration  │ Minimum │ Win Rate  │
├────────────────┼─────────┼───────────┤
│ CONSERVATIVE   │ ≥4/5    │ 55-65%    │
│ (Strict)       │         │           │
├────────────────┼─────────┼───────────┤
│ BALANCED       │ ≥3/5    │ 50-60%    │
│ (Moderate)     │         │           │
├────────────────┼─────────┼───────────┤
│ AGGRESSIVE     │ ≥2/5    │ 45-55%    │
│ (Loose)        │         │           │
└────────────────┴─────────┴───────────┘

TRADE-OFF:
├─ Higher minimum = Better quality, fewer signals
├─ Lower minimum = More signals, lower quality
└─ Choose based on your risk tolerance
```

---

## Configuration Impact Summary

### Pattern Enable/Disable Effects

```
Enabling/Disabling patterns affects:

┌──────────────────┬──────────┬───────────────┐
│ Action           │ Win Rate │ Signals/Month │
├──────────────────┼──────────┼───────────────┤
│ Enable All       │ ↓        │ ↑↑ (more)     │
│ (More patterns)  │ (lower)  │               │
├──────────────────┼──────────┼───────────────┤
│ Disable Weak     │ ↑        │ ↓ (fewer)     │
│ (Remove bad ones)│ (higher) │               │
├──────────────────┼──────────┼───────────────┤
│ Keep Best 2-3    │ ↑↑       │ ↓↓ (very few) │
│ (Ultra selective)│ (best)   │               │
└──────────────────┴──────────┴───────────────┘

RECOMMENDATION: Start with all, disable underperformers
```

### Session Filter Effects

```
┌──────────────────┬──────────┬───────────────┐
│ Filter Setting   │ Win Rate │ Signals/Month │
├──────────────────┼──────────┼───────────────┤
│ Enable (ON)      │ ↑        │ ↓ (fewer)     │
│ All sessions     │ (higher) │               │
├──────────────────┼──────────┼───────────────┤
│ Disable (OFF)    │ ↓        │ ↑ (more)      │
│ All hours        │ (lower)  │               │
├──────────────────┼──────────┼───────────────┤
│ London+NY only   │ ↑↑       │ ↓ (selective) │
│                  │ (best)   │               │
└──────────────────┴──────────┴───────────────┘

RECOMMENDATION: Keep session filter ON
```

### Confirmation Requirements Effects

```
┌──────────────────┬──────────┬───────────────┐
│ Minimum Confirm  │ Win Rate │ Signals/Month │
├──────────────────┼──────────┼───────────────┤
│ Need 2 (Loose)   │ ↓        │ ↑↑ (many)     │
│                  │ (lower)  │               │
├──────────────────┼──────────┼───────────────┤
│ Need 3 (Balance) │ ↑        │ ↑ (good)      │
│                  │ (better) │               │
├──────────────────┼──────────┼───────────────┤
│ Need 4 (Strict)  │ ↑↑       │ ↓ (selective) │
│                  │ (best)   │               │
├──────────────────┼──────────┼───────────────┤
│ Need 5 (Extreme) │ ↑↑↑      │ ↓↓ (rare)     │
│                  │ (perfect)│               │
└──────────────────┴──────────┴───────────────┘

RECOMMENDATION: Start with 3, adjust based on results
```

---

## Quick Reference Tables

### Timing Scores by Session

```
Session              Score   Quality    Trading Recommendation
────────────────────────────────────────────────────────────
Asian (00-09)       0.3     LOW         AVOID
London Early (08-08:30) 0.2 VERY LOW   AVOID
London (08:30-17)   0.9     HIGH        TAKE IT
New York (13-22)    0.85    HIGH        TAKE IT
Overlap (13-17)     1.0     EXCELLENT   BEST TIME
Weekend             0.1     TERRIBLE    AVOID
```

### Level Score by Proximity

```
Distance from Level     Weekly      Daily       Signal Quality
────────────────────────────────────────────────────────────
Within 0.5%            N/A         +0.2        Strong
Within 1%              +0.3        +0.1        Good
Within 2%              +0.2        N/A         Moderate
Within 5%              +0.1        N/A         Weak
Far away               0.0         0.0         No edge
```

### Confirmation Requirements

```
Config         Minimum    Best For           Expected Result
──────────────────────────────────────────────────────────
Conservative   ≥4/5       Risk-averse        55-65% win rate
                          Consistent traders  Few signals

Balanced       ≥3/5       Most traders       50-60% win rate
                          Moderate risk       Many signals

Aggressive     ≥2/5       Experienced        45-55% win rate
                          High risk tolerance Very many signals
```

---

## Complete System Logic Flow

```
START: Receive OHLCV Data
    │
    ├─→ UPDATE LEVELS (Stage 2)
    │   ├─ Weekly H/L (new week?)
    │   ├─ Daily H/L (first hour?)
    │   ├─ Touch counts (3-hits)
    │   └─ Friday close (trap)
    │
    ├─→ TIMING ANALYSIS (Stage 3)
    │   └─ Session Score (0.0-1.0)
    │
    ├─→ LEVEL ANALYSIS (Stage 4)
    │   └─ Level Score (0.0-1.0)
    │
    ├─→ PATTERN DETECTION (Stage 5)
    │   ├─ M-Pattern check
    │   ├─ W-Pattern check
    │   ├─ Weekend Trap check
    │   ├─ Board Meeting check
    │   ├─ Three Hits check
    │   ├─ Trap Volume check
    │   └─ One Formation check
    │
    ├─→ PATTERN FILTERING (Stage 6)
    │   └─ Select best or neutral
    │
    ├─→ CONFIRMATIONS (Stage 7)
    │   ├─ Pattern: +1 if found
    │   ├─ Timing: +1 if > 0.6
    │   ├─ Level: +1 if > 0.6
    │   ├─ Volume: +1 if enabled & confirmed
    │   ├─ Trend: +1 if enabled & matched
    │   └─ Check minimum met?
    │
    ├─→ CONFIDENCE (Stage 8)
    │   └─ Weighted sum of components
    │
    ├─→ SIGNAL (Stage 9)
    │   └─ Compose LayerSignal
    │
    └─→ RETURN Signal to Strategy
```

---

**This markdown diagram shows all the rule evaluation logic and confirmations used in the TBD Method Layer.**
