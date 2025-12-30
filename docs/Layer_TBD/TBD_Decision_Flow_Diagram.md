# TBD Layer Complete Decision Flow - Markdown Diagram

## Overview

This document represents the complete end-to-end decision flow of the TBD Layer from data input to final signal output. Follow from top to bottom to understand the complete signal generation process.

---

## Stage 1: Data Input & Initialization

```
┌─────────────────────────────────────┐
│       RECEIVE OHLCV DATA            │
│   + Indicators + Timestamps         │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│   VALIDATE DATA QUALITY             │
│   • Min 100 bars required           │
│   • Check timestamps                │
│   • Verify no gaps                  │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  INITIALIZE LAYER STATE             │
│  • Load configuration               │
│  • Set tracking variables           │
│  • Prepare analysis structures      │
└────────────┬────────────────────────┘
             │
             ▼
       [Continue to Stage 2]
```

---

## Stage 2: Update Tracking Levels

```
┌─────────────────────────────────────┐
│  CHECK: NEW WEEK?                   │
└────────────┬──────────────┬─────────┘
             │              │
          YES│              │NO
             ▼              ▼
    ┌──────────────┐   ┌──────────────┐
    │ Update       │   │ Use existing │
    │ Weekly H/L   │   │ Weekly H/L   │
    │ (5-day      │   │              │
    │  lookback)  │   │              │
    └──────┬───────┘   └──────┬───────┘
           │                  │
           └────────┬─────────┘
                    ▼
         ┌─────────────────────────────┐
         │  CHECK: FIRST HOUR LONDON?  │
         └────────┬──────────┬─────────┘
                  │          │
               YES│          │NO
                  ▼          ▼
         ┌──────────────┐ ┌──────────────┐
         │ Set Daily    │ │ Update Daily │
         │ H/L from     │ │ H/L with     │
         │ opening      │ │ current      │
         │ candle       │ │ high/low     │
         └──────┬───────┘ └──────┬───────┘
                │                │
                └────────┬───────┘
                         ▼
            ┌──────────────────────────┐
            │ TOUCH COUNT TRACKING     │
            │ • Check if near Weekly   │
            │   H/L (±0.5% tolerance) │
            │ • Increment touch count  │
            │   if conditions met      │
            └────────┬─────────────────┘
                     │
                     ▼
            ┌──────────────────────────┐
            │ WEEKEND TRACKING         │
            │ • Check if Friday?       │
            │ • Store Friday close     │
            │   for Monday detection   │
            └────────┬─────────────────┘
                     │
                     ▼
                [Continue to Stage 3]
```

---

## Stage 2.5: Liquidation Level Loading (v2.0 Enhancement)

```
┌────────────────────────────────────────┐
│  CHECK: LIQUIDATION TRACKING ENABLED?  │
└────────────┬──────────────┬────────────┘
             │              │
          YES│              │NO
             ▼              ▼
    ┌──────────────┐   ┌──────────────┐
    │ LAZY LOAD    │   │ Skip         │
    │ Liquidation  │   │ liquidation  │
    │ Data         │   │ analysis     │
    │ (24 months)  │   │              │
    └──────┬───────┘   └──────┬───────┘
           │                  │
           ▼                  │
┌─────────────────────────┐  │
│ CLUSTER DETECTION       │  │
│ • Group by price bins   │  │
│   (1% ranges)           │  │
│ • Filter >$1M clusters  │  │
│ • Calculate proximity   │  │
│   to current price      │  │
└─────────┬───────────────┘  │
          │                  │
          └────────┬─────────┘
                   ▼
         ┌─────────────────────────────┐
         │  LIQUIDATION CONTEXT READY  │
         │  • Clusters identified      │
         │  • Proximity scores cached  │
         │  • Available for Stage 4    │
         └────────┬────────────────────┘
                  │
                  ▼
            [Continue to Stage 3]
```

**v2.0 Enhancement Notes**:
- Liquidation data lazy-loaded on first use
- 24 months of historical data (~18MB)
- Clustering algorithm: 1% price bins
- Significant threshold: >$1M USD
- Proximity scoring: Within 2% of price
- Data source: Crypto-Lake API monthly files

---

## Stage 3: Timing Analysis (DST-Aware v2.0)

```
┌─────────────────────────────────────┐
│   DETECT DST STATUS (v2.0)          │
│   • Check UK DST (Last Sun Mar/Oct) │
│   • Check US DST (2nd Sun Mar/     │
│     1st Sun Nov)                    │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│   IDENTIFY CURRENT SESSION          │
│   Based on UTC hour + DST adjust    │
└────────────┬────────────────────────┘
             │
    ┌────────┴─────────┬──────────┬─────────┬────────────┐
    │                  │          │         │            │
    ▼                  ▼          ▼         ▼            ▼
┌─────────┐      ┌─────────┐  ┌─────┐  ┌──────┐    ┌─────────┐
│ ASIAN   │      │ LONDON  │  │ NY  │  │OVERLAP│  │WEEKEND  │
│ 23-08   │      │ Winter: │  │Winter│ │Winter:│  │Sat-Sun  │
│ (No DST)│      │ 08-17   │  │13-22 │ │13-17  │  │ (Any    │
│ Score:  │      │ Summer: │  │Summer│ │Summer:│  │  time)  │
│  0.3    │      │ 07-16   │  │12-21 │ │12-16  │  │ Score:  │
│         │      │ (BST)   │  │(EDT) │ │       │  │  0.1    │
│         │      │ Score:  │  │Score │ │Score: │  │         │
│         │      │ 0.2-0.9 │  │0.85  │ │ 1.0   │  │         │
└─────────┘      └────┬────┘  └─────┘  └──────┘    └─────────┘
                      │
                Check 1st 30min?
                      │
         ┌────────────┴────────────┐
         │                         │
      YES│                         │NO
         ▼                         ▼
    ┌────────┐              ┌────────┐
    │Score:  │              │Score:  │
    │ 0.2    │              │ 0.9    │
    └────────┘              └────────┘
         │                      │
         └───────────┬──────────┘
                     │
                     ▼
        ┌──────────────────────────┐
        │ ADD WEEKLY CYCLE BONUS   │
        │ • Mon/Wed/Thu: +0.1      │
        │ • Tue/Fri: +0.1          │
        │ • Sat/Sun: Special       │
        └────────┬─────────────────┘
                 │
                 ▼
        ┌──────────────────────────┐
        │  TIMING SCORE (0.0-1.0)  │
        │  Result: Used in         │
        │  confirmations & weighting
        └────────┬─────────────────┘
                 │
                 ▼
            [Continue to Stage 4]
```

**DST Transition Details (v2.0)**:
```
UK (BST/GMT):
├─ DST Start: Last Sunday in March at 01:00 UTC
├─ DST End: Last Sunday in October at 01:00 UTC
├─ Winter (GMT): 08:00-17:00 UTC
└─ Summer (BST): 07:00-16:00 UTC (-1 hour shift)

US (EDT/EST):
├─ DST Start: 2nd Sunday in March at 02:00 UTC
├─ DST End: 1st Sunday in November at 02:00 UTC
├─ Winter (EST): 13:00-22:00 UTC
└─ Summer (EDT): 12:00-21:00 UTC (-1 hour shift)

Implementation: _is_uk_dst() and _is_us_dst() methods
Auto-detects transitions and adjusts session times
```

---

## Stage 4: Level Analysis (Enhanced with Liquidations v2.0)

```
┌──────────────────────────────────────┐
│  CALCULATE WEEKLY LEVEL PROXIMITY    │
│  Distance to H/L from current price  │
└────────────┬─────────────────────────┘
             │
    ┌────────┴────────┬──────────┐
    │                 │          │
    ▼                 ▼          ▼
┌────────────┐ ┌────────────┐ ┌────────┐
│ <1%?       │ │ <2%?       │ │ <5%?   │
│ +0.3 points│ │ +0.2 points│ │+0.1 pts│
└────────────┘ └────────────┘ └────────┘
    │                 │          │
    └────────┬────────┴──────────┘
             │
             ▼
┌──────────────────────────────────────┐
│  CALCULATE DAILY LEVEL PROXIMITY     │
│  Distance to H/L from current price  │
└────────────┬─────────────────────────┘
             │
    ┌────────┴────────┬──────────┐
    │                 │          │
    ▼                 ▼          ▼
┌────────────┐ ┌────────────┐ ┌──────┐
│ <0.5%?     │ │ <1%?       │ │Other │
│ +0.2 points│ │ +0.1 points│ │ 0pts │
└────────────┘ └────────────┘ └──────┘
    │                 │          │
    └────────┬────────┴──────────┘
             │
             ▼
┌──────────────────────────────────────┐
│  LIQUIDATION CLUSTER PROXIMITY (v2.0)│
│  Check nearby liquidation zones      │
└────────────┬─────────────────────────┘
             │
    ┌────────┴────────┬──────────┐
    │                 │          │
    ▼                 ▼          ▼
┌────────────┐ ┌────────────┐ ┌──────┐
│ <1%?       │ │ <2%?       │ │ >2%? │
│ Score: +0.3│ │ Score: +0.2│ │ +0.0 │
│ (Very      │ │ (Near      │ │ (Far)│
│  close)    │ │  cluster)  │ │      │
└────────────┘ └────────────┘ └──────┘
    │                 │          │
    └────────┬────────┴──────────┘
             │
             ▼
        ┌─────────────────────────┐
        │  LEVEL SCORE (0.0-1.0)  │
        │  Result: Used in        │
        │  confirmations & weighting│
        │  (Now includes liq boost)│
        └────────┬────────────────┘
                 │
                 ▼
            [Continue to Stage 5]
```

**Liquidation Cluster Scoring (v2.0)**:
```
┌──────────────────────────────────────┐
│  GET NEARBY CLUSTERS                 │
│  LiquidationLevelTracker.             │
│  get_nearby_clusters(price, 2%)      │
└────────────┬─────────────────────────┘
             │
             ▼
┌──────────────────────────────────────┐
│  FILTER SIGNIFICANT CLUSTERS         │
│  • Must be >$1M USD                  │
│  • Must be within 2% of price        │
│  • Calculate proximity score         │
└────────────┬─────────────────────────┘
             │
             ▼
┌──────────────────────────────────────┐
│  APPLY CLUSTER BOOST                 │
│  • <1% distance: +0.3                │
│  • <2% distance: +0.2                │
│  • Max total boost: 0.3              │
│  • Multiple clusters: Additive       │
└────────────┬─────────────────────────┘
             │
             ▼
        [Add to level_score]

INTERPRETATION:
├─ Liquidation clusters = price magnets
├─ Long liquidations = bearish pressure
├─ Short liquidations = bullish pressure
└─ Proximity increases reversal/breakout probability
```

---

## Stage 5: Pattern Detection (7 Parallel Branches)

```
┌──────────────────────────────────┐
│  BEGIN PATTERN DETECTION         │
│  Check all 7 enabled patterns    │
└────────────┬─────────────────────┘
             │
    ┌────────┴────────┬──────────┬──────────┬─────────┬──────────┬────────┐
    │                 │          │          │         │          │        │
    ▼                 ▼          ▼          ▼         ▼          ▼        ▼
┌────────────┐  ┌────────┐  ┌────────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌────────┐
│ M-PATTERN  │  │W-PATTERN│ │WEEKEND │  │BOARD │  │THREE │  │TRAP  │  │ONE     │
│(Double Top)│  │(Double  │ │TRAP    │  │MEET  │  │HITS  │  │VOL   │  │FORM    │
│ BEARISH   │  │Bottom)  │ │REVERSAL│  │BREAK │  │REV   │  │REVERS│  │BREAK   │
│           │  │BULLISH  │ │        │  │OUT   │  │      │  │      │  │        │
└─┬──────────┘  └────┬───┘  └───┬────┘  └──┬───┘  └──┬──┘  └──┬───┘  └───┬────┘
  │                 │          │          │       │       │        │
  │ Check:          │ Check:   │ Check:   │Check: │Check: │ Check: │ Check:
  │ • 2 peaks       │ • 2      │ • Monday │ • <2% │ • ≥3  │ • Wick │ • Tight
  │ • ±15% sym      │  troughs │   morning│ range │ touches│ ratio>│ consol
  │ • Neckline      │ • ±15%   │ • <4h    │ • 6-24│ • Wick │ 50%   │ • 2x
  │ • Break down    │   sym    │   from   │ candles│ reject │ • Vol │  candle
  │ • Volume        │ • Break  │   open   │ • >50%│       │ • Vol │  size
  │                 │   up     │ • >2%    │  break│       │       │ • Vol
  │                 │ • Volume │   move   │ • Vol │       │       │ • Break
  │                 │          │          │       │       │       │
  ▼                 ▼          ▼          ▼       ▼       ▼       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│   COLLECT RESULTS:                                                       │
│   patterns_found = [list of PatternData with confidence scores]         │
└────────────┬─────────────────────────────────────────────────────────────┘
             │
             ▼
            [Continue to Stage 6]
```

### Pattern Detail: M-Pattern (Double Top)
```
1. Find Peaks
   └─ Lookback 30-50 candles
      └─ Identify local maxima
         └─ Need ≥2 peaks

2. Symmetry Check
   └─ |peak1 - peak2| / peak1 < 15%?
      ├─ YES: Continue
      └─ NO: Return None

3. Neckline
   └─ Lowest point between peaks
      └─ This is support level

4. Break Confirmation
   └─ Is price < neckline - 0.3%?
      ├─ YES: Valid breakout
      └─ NO: Not triggered

5. Volume Confirmation
   └─ Current vol > avg vol × 1.3?
      ├─ YES: Confirmed
      └─ NO: Weak

6. Calculate Targets
   ├─ Height = peak - neckline
   ├─ TP1 = neckline - (height × 0.5)
   ├─ TP2 = neckline - (height × 1.0)
   └─ TP3 = neckline - (height × 1.5)

7. Calculate Stop
   └─ Stop = max(peak1, peak2) + (ATR × 1.5)
```

### Pattern Detail: W-Pattern (Double Bottom)
```
Mirror of M-Pattern for bullish reversal
├─ Find 2 troughs instead of peaks
├─ Check ±15% symmetry
├─ Neckline = highest point between
├─ Break above neckline (upward)
├─ TP above neckline
└─ Stop below lower trough
```

### Pattern Detail: Weekend Trap
```
1. Check: Is it Monday?
   └─ YES: Continue
   └─ NO: Can't be trap

2. Time Window: <4 hours from open?
   └─ YES: Continue
   └─ NO: Too late

3. Weekend Move: |price - friday_close| / friday_close > 2%?
   └─ YES: Significant move
   └─ NO: Not big enough

4. Reversal: Is price reversing?
   └─ YES: Pattern found
   └─ NO: Not yet

5. Direction: Opposite of weekend move
   ├─ If up: Entry SHORT
   └─ If down: Entry LONG

6. Target: Friday close (mean reversion)
```

### Pattern Detail: Board Meeting
```
1. Find Consolidation
   └─ Range < 2% over 24 candles?
      └─ YES: Consolidation found
      └─ NO: Not tight enough

2. Duration: 6-24 candles?
   └─ YES: Valid duration
   └─ NO: Too long or short

3. Breakout: >50% of consolidation range?
   └─ YES: Valid breakout
   └─ NO: Not decisive

4. Volume: Current × avg vol > 1.5?
   └─ YES: Confirmed breakout
   └─ NO: Weak

5. Direction: Of breakout
   ├─ Up: LONG
   └─ Down: SHORT

6. Targets: Measured move (height × 1, 2, 3)
```

### Pattern Detail: Three Hits Reversal
```
1. Touch Count: ≥3 to weekly H/L?
   └─ YES: Potential exhaustion
   └─ NO: Not yet

2. At Level Now?
   └─ Current candle within ±0.5%?
      └─ YES: Continue
      └─ NO: Not setup

3. Rejection: Wick + close opposite side?
   └─ YES: Clear rejection
   └─ NO: Not exhaustion

4. Direction: Opposite of level
   ├─ At high 3×: SHORT
   └─ At low 3×: LONG

5. Target: Range-based from level
```

### Pattern Detail: Trapping Volume
```
1. Detect Wick: >50% of candle range?
   ├─ Upper wick: Bullish trap
   ├─ Lower wick: Bearish trap
   └─ NO: No trap

2. Body Check: Small body opposite of wick?
   └─ YES: Confirms trap
   └─ NO: Not a trap

3. Volume: Current × avg vol > 1.5?
   └─ YES: Interest confirmed
   └─ NO: Weak

4. Direction: Opposite of wick
   ├─ Large upper wick: SHORT
   └─ Large lower wick: LONG

5. Target: Opposite extreme
```

### Pattern Detail: One Formation
```
1. Consolidation: <3% range?
   └─ Last 30 candles tight?
      └─ YES: Valid consolidation
      └─ NO: Not tight

2. Current Candle: >2× average size?
   └─ YES: Big breakout candle
   └─ NO: Not decisive

3. Volume: Current × avg vol > 2.0?
   └─ YES: Strong confirmation
   └─ NO: Weak

4. Outside Range: Closes outside consolidation?
   └─ YES: Valid breakout
   └─ NO: Not breakout

5. Direction: Of breakout
   ├─ Up: LONG
   └─ Down: SHORT

6. Target: Measured move (big)
```

---

## Stage 6: Pattern Filtering & Selection

```
┌──────────────────────────────────────┐
│  ANALYZE PATTERNS FOUND              │
└────────────┬─────────────────────────┘
             │
             ▼
    ┌────────────────────┐
    │ Patterns_Found     │
    │ list is empty?     │
    └────────┬──────┬───┘
             │      │
          YES│      │NO
             ▼      ▼
        [NEUTRAL] ┌─────────────────────┐
        [SIGNAL]  │ SELECT BEST PATTERN │
                  │ = max(confidence)   │
                  └────────┬────────────┘
                           │
                           ▼
                [Continue to Stage 7]
```

---

## Stage 7: Confirmation Checking (5 Types)

```
┌──────────────────────────────────────┐
│  CONFIRMATION SYSTEM                 │
│  Count all confirmations             │
└────────────┬─────────────────────────┘
             │
    ┌────────┴────────┬────────┬──────────┬──────────┐
    │                 │        │          │          │
    ▼                 ▼        ▼          ▼          ▼
┌──────────┐     ┌──────────┐ ┌────────┐ ┌────────┐ ┌──────────┐
│PATTERN   │     │TIMING    │ │LEVEL   │ │VOLUME  │ │TREND     │
│CONFIRM   │     │CONFIRM   │ │CONFIRM │ │CONFIRM │ │CONFIRM   │
│          │     │          │ │        │ │        │ │          │
│Pattern   │     │Timing    │ │Level   │ │Vol >   │ │Pattern   │
│Found?    │     │Score     │ │Score   │ │avg ×   │ │matches   │
│          │     │> 0.6?    │ │> 0.6?  │ │mult?   │ │trend?    │
│          │     │          │ │        │ │        │ │          │
│YES = +1  │     │YES = +1  │ │YES=+1  │ │YES=+1  │ │YES = +1  │
│NO  = 0   │     │NO = 0    │ │NO = 0  │ │NO = 0  │ │NO = 0    │
└──────────┘     └──────────┘ └────────┘ └────────┘ └──────────┘
    │                 │        │          │          │
    └─────────────────┴────────┴──────────┴──────────┘
                     │
                     ▼
        ┌──────────────────────────────┐
        │  TOTAL CONFIRMATIONS = SUM   │
        │  Range: 1/5 to 5/5           │
        └────────┬─────────────────────┘
                 │
                 ▼
        ┌──────────────────────────────┐
        │  CHECK MINIMUM REQUIRED      │
        └────────┬────────────┬────────┘
                 │            │
    CONFIG=?    │            │
    ┌──────────┬┴─┬──────────┬┴────┐
    │          │  │          │     │
  CONS      BAL  AGG        ≥Min   <Min
   ≥4        ≥3  ≥2         │      │
    │        │   │          ▼      ▼
    └────────┴───┴────┬─────────────┐
                      │             │
                      ▼             ▼
                [CONTINUE]    [NEUTRAL SIGNAL]
```

---

## Stage 8: Confidence Calculation

```
┌────────────────────────────────────────┐
│  CALCULATE WEIGHTED CONFIDENCE         │
└────────────┬─────────────────────────────┘
             │
     ┌───────┴────────┬──────────┬─────────┬──────────┐
     │                │          │         │          │
     ▼                ▼          ▼         ▼          ▼
┌──────────┐    ┌────────┐  ┌──────┐  ┌──────┐  ┌──────────┐
│PATTERN   │    │TIMING  │  │LEVEL │  │CONF  │  │WEIGHTS   │
│CONFID    │    │SCORE   │  │SCORE │  │COUNT │  │          │
│× 0.35    │    │× 0.25  │  │× 0.25│  │× 0.15│  │Sum = 1.0 │
└─────┬────┘    └───┬────┘  └──┬───┘  └──┬───┘  └──────────┘
      │             │         │         │
      └─────────────┴─────────┴─────────┘
                     │
                     ▼
            ┌─────────────────────────┐
            │  FINAL CONFIDENCE =     │
            │  Sum of weighted parts  │
            │  Range: 0.3 to 1.0      │
            └────────┬────────────────┘
                     │
            Confidence Level:
            0.9-1.0: Excellent (rare)
            0.8-0.9: Very good
            0.7-0.8: Good
            0.6-0.7: Acceptable
            <0.6: Should not pass
```

---

## Stage 9: Signal Composition

```
┌──────────────────────────────────────────┐
│  COMPOSE FINAL LAYERSIGNAL               │
│  All required information for strategy   │
└────────────┬─────────────────────────────┘
             │
             ▼
    ┌─────────────────────────────────┐
    │  LayerSignal OUTPUT:            │
    │                                 │
    │  direction: 'long'/'short'/     │
    │             'neutral'           │
    │                                 │
    │  confidence: 0.0-1.0            │
    │                                 │
    │  strength: pattern_confidence   │
    │                                 │
    │  metadata: {                    │
    │    'pattern_type': str,         │
    │    'entry_price': float,        │
    │    'stop_loss': float,          │
    │    'take_profit_1': float,      │
    │    'take_profit_2': float,      │
    │    'take_profit_3': float,      │
    │    'risk_reward_1': float,      │
    │    'risk_reward_2': float,      │
    │    'risk_reward_3': float,      │
    │    'confirmations_met': int,    │
    │    'confirmations_required':    │
    │         int,                    │
    │    'timing_score': float,       │
    │    'level_score': float,        │
    │    'session': str,              │
    │    'day_of_week': str,          │
    │    'pattern_metadata': dict     │
    │  }                              │
    └────────┬──────────────────────┘
             │
             ▼
        ┌──────────────────┐
        │  END OF FLOW     │
        │  RETURN SIGNAL   │
        └──────────────────┘
```

---

## Complete Signal Flow Summary

```
┌─────────────────────────────────┐
│  1. DATA INPUT & INIT           │
└────────────┬────────────────────┘
             ▼
┌─────────────────────────────────┐
│  2. UPDATE LEVELS               │
│  (Weekly H/L, Daily H/L, Touches)
└────────────┬────────────────────┘
             ▼
┌─────────────────────────────────┐
│  3. TIMING ANALYSIS             │
│  (Session Score)                │
└────────────┬────────────────────┘
             ▼
┌─────────────────────────────────┐
│  4. LEVEL ANALYSIS              │
│  (Proximity Score)              │
└────────────┬────────────────────┘
             ▼
┌─────────────────────────────────┐
│  5. PATTERN DETECTION (7 types) │
│  (Find all matching patterns)   │
└────────────┬────────────────────┘
             ▼
┌─────────────────────────────────┐
│  6. PATTERN FILTERING           │
│  (Select best by confidence)    │
└────────────┬────────────────────┘
             ▼
┌─────────────────────────────────┐
│  7. CONFIRMATION CHECKING       │
│  (Count 5 types, verify minimum)│
└────────────┬────────────────────┘
             ▼
┌─────────────────────────────────┐
│  8. CONFIDENCE CALCULATION      │
│  (Weighted sum of components)   │
└────────────┬────────────────────┘
             ▼
┌─────────────────────────────────┐
│  9. SIGNAL COMPOSITION          │
│  (Package all metadata)         │
└────────────┬────────────────────┘
             ▼
    ┌───────────────────────┐
    │ RETURN LAYERSIGNAL    │
    │ Ready for strategy    │
    └───────────────────────┘
```

---

## Key Definitions

### Timing Score
- **Purpose**: Filter trades by session quality
- **Range**: 0.0 (weekend) to 1.0 (overlap)
- **Use**: Confirmation filter (need > 0.6)
- **Calculation**: Based on current UTC hour

### Level Score
- **Purpose**: Filter trades near key support/resistance
- **Range**: 0.0 (far away) to 1.0 (at level)
- **Use**: Confirmation filter (need > 0.6)
- **Calculation**: Proximity to weekly/daily H/L

### Pattern Confidence
- **Purpose**: Measure quality of detected pattern
- **Range**: 0.3 (poor) to 1.0 (perfect)
- **Use**: Select best pattern when multiple found
- **Calculation**: Pattern-specific metrics

### Final Confidence
- **Purpose**: Overall signal quality
- **Range**: 0.3 to 1.0
- **Use**: Strength indicator for strategy
- **Formula**: `(pattern×0.35) + (timing×0.25) + (level×0.25) + (conf/5×0.15)`

---

## Configuration Parameters Reference

```
PATTERN SWITCHES (Enable/Disable each)
├─ enable_m_pattern
├─ enable_w_pattern
├─ enable_weekend_trap
├─ enable_board_meeting
├─ enable_three_hits_rule
├─ enable_trapping_volume
└─ enable_one_formation

TIMING SWITCHES
├─ enable_session_filter
├─ avoid_first_30min_london
└─ avoid_weekend_trading

CONFIRMATION SWITCHES
├─ require_volume_confirmation
├─ require_trend_alignment
└─ minimum_confirmations (2/3/4/5)

RISK PARAMETERS
├─ atr_stop_multiplier (0.5-2.5)
├─ mw_peak_tolerance (0.08-0.20)
├─ board_range_threshold (0.015-0.030)
└─ weekend_trap_threshold (0.015-0.030)
```

---

## Next Steps

1. Review this complete flow diagram
2. Match your implementation to each stage
3. Verify threshold values match your code
4. Test pattern detection logic
5. Validate confirmation system
6. Run backtests and optimize

---

**This markdown represents the complete TBD Layer decision flow in text format for easy reference and documentation.**
