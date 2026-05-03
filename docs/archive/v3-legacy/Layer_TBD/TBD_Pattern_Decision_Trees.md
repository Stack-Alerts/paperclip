# TBD Pattern Detection Decision Trees - Markdown Diagram

## Overview

This document provides detailed decision trees for all 7 TBD patterns with complete logic flow and calculations.

---

## Pattern 1: M-Pattern (Double Top) - BEARISH REVERSAL

### Detection Logic Flow

```
┌────────────────────────────────────────────┐
│  M-PATTERN DETECTION (DOUBLE TOP)          │
│  Bearish Reversal Pattern                  │
└────────────┬─────────────────────────────┘
             │
             ▼
    ┌─────────────────────────────┐
    │ STEP 1: FIND PEAKS          │
    │ • Lookback: 30-50 candles   │
    │ • Find local maxima         │
    │ • Need: ≥2 peaks            │
    └────────┬────────────────────┘
             │
             ├─NO PEAKS FOUND─→ [RETURN: None]
             │
             ▼
    ┌─────────────────────────────┐
    │ STEP 2: SYMMETRY CHECK      │
    │ |peak1 - peak2| / peak1     │
    │ < tolerance (±15%)?         │
    └────────┬────────────────────┘
             │
         ┌───┴───┐
        YES      NO
         │       │
         ▼       └──→ [RETURN: None]
    ┌─────────────────────────────┐
    │ STEP 3: NECKLINE            │
    │ Lowest point between peaks  │
    │ = Support level             │
    └────────┬────────────────────┘
             │
             ▼
    ┌─────────────────────────────┐
    │ STEP 4: BREAK CONFIRMATION  │
    │ Price < neckline - 0.3%?    │
    └────────┬────────────────────┘
             │
         ┌───┴───┐
        YES      NO
         │       │
         ▼       └──→ [RETURN: None]
    ┌─────────────────────────────┐
    │ STEP 5: VOLUME CONFIRMATION │
    │ (If enabled)                │
    │ Vol > avg × 1.3?            │
    └────────┬────────────────────┘
             │
         ┌───┴───┐
        YES      NO (if required)
         │       │
         ▼       └──→ [RETURN: None]
    ┌─────────────────────────────┐
    │ STEP 6: CALCULATE TARGETS   │
    │ Height = max(p1,p2) - neck  │
    │ TP1 = neck - (h × 0.5)      │
    │ TP2 = neck - (h × 1.0)      │
    │ TP3 = neck - (h × 1.5)      │
    └────────┬────────────────────┘
             │
             ▼
    ┌─────────────────────────────┐
    │ STEP 7: CALCULATE STOP      │
    │ Stop = max(p1,p2) + ATR×1.5 │
    │ (protects above peaks)      │
    └────────┬────────────────────┘
             │
             ▼
    ┌─────────────────────────────┐
    │ STEP 8: CONFIDENCE SCORE    │
    │ Symmetry×0.4 +              │
    │ Volume×0.3 +                │
    │ Clarity×0.3 = Confidence    │
    └────────┬────────────────────┘
             │
             ▼
    ┌─────────────────────────────┐
    │ [RETURN: PatternData]       │
    │ • Direction: SHORT          │
    │ • Entry: Current price      │
    │ • Stop: Calculated          │
    │ • TP1/2/3: Calculated       │
    │ • Confidence: Calculated    │
    └─────────────────────────────┘

EXPECTED: 58-62% win rate, 1-3 signals/month
TIMEFRAME: Best on 4H and Daily
TRADE TIME: 4-12 hours typical
```

### Key Parameters

```
Configuration Parameters:
├─ mw_peak_tolerance: 0.10-0.20 (default 0.15)
├─ mw_pattern_length_min: 10 candles
├─ mw_pattern_length_max: 50 candles
├─ mw_neckline_break_threshold: 0.003 (0.3%)
└─ mw_volume_multiplier: 1.3

Calculation Formulas:
├─ Peak Diff % = |peak1 - peak2| / peak1
├─ Pattern Height = max(peak1, peak2) - neckline
├─ TP1 = neckline - (height × 0.5)
├─ TP2 = neckline - (height × 1.0)
├─ TP3 = neckline - (height × 1.5)
└─ Stop = max(peak1, peak2) + (ATR × 1.5)
```

---

## Pattern 2: W-Pattern (Double Bottom) - BULLISH REVERSAL

### Detection Logic Flow

```
┌────────────────────────────────────────────┐
│  W-PATTERN DETECTION (DOUBLE BOTTOM)       │
│  Bullish Reversal Pattern                  │
│  (Mirror of M-Pattern logic)               │
└────────────┬─────────────────────────────┘
             │
             ▼
    ┌─────────────────────────────┐
    │ STEP 1: FIND TROUGHS        │
    │ • Lookback: 30-50 candles   │
    │ • Find local minima         │
    │ • Need: ≥2 troughs          │
    └────────┬────────────────────┘
             │
             ├─NO TROUGHS─→ [RETURN: None]
             │
             ▼
    ┌─────────────────────────────┐
    │ STEP 2: SYMMETRY CHECK      │
    │ |trough1 - trough2|/trough1 │
    │ < ±15%?                     │
    └────────┬────────────────────┘
             │
         ┌───┴───┐
        YES      NO
         │       │
         ▼       └──→ [RETURN: None]
    ┌─────────────────────────────┐
    │ STEP 3: NECKLINE            │
    │ Highest point between troughs│
    │ = Resistance level          │
    └────────┬────────────────────┘
             │
             ▼
    ┌─────────────────────────────┐
    │ STEP 4: BREAK CONFIRMATION  │
    │ Price > neckline + 0.3%?    │
    │ (ABOVE, opposite of M)      │
    └────────┬────────────────────┘
             │
         ┌───┴───┐
        YES      NO
         │       │
         ▼       └──→ [RETURN: None]
    ┌─────────────────────────────┐
    │ STEP 5: VOLUME CONFIRMATION │
    │ Vol > avg × 1.3?            │
    └────────┬────────────────────┘
             │
         ┌───┴───┐
        YES      NO
         │       │
         ▼       └──→ [RETURN: None]
    ┌─────────────────────────────┐
    │ STEP 6: CALCULATE TARGETS   │
    │ Height = neck - min(t1,t2)  │
    │ TP1 = neck + (h × 0.5)      │
    │ TP2 = neck + (h × 1.0)      │
    │ TP3 = neck + (h × 1.5)      │
    │ (ALL ABOVE, opposite M)     │
    └────────┬────────────────────┘
             │
             ▼
    ┌─────────────────────────────┐
    │ [RETURN: PatternData]       │
    │ • Direction: LONG           │
    │ • Entry: Current price      │
    │ • Stop: Below lower trough  │
    │ • TP1/2/3: Calculated       │
    │ • Confidence: Calculated    │
    └─────────────────────────────┘

EXPECTED: 58-62% win rate, 1-3 signals/month
TIMEFRAME: Best on 4H and Daily
TRADE TIME: 4-12 hours typical
```

---

## Pattern 3: Weekend Trap - REVERSAL SETUP

### Detection Logic Flow

```
┌─────────────────────────────────────────┐
│  WEEKEND TRAP DETECTION                 │
│  Monday Reversal Pattern                │
│  Catches retail trapped on wrong side   │
└────────────┬──────────────────────────┘
             │
             ▼
    ┌──────────────────────────────┐
    │ STEP 1: TIME CHECK           │
    │ Is it Monday (weekday = 0)?  │
    └────────┬──────────────────────┘
             │
         ┌───┴───┐
        YES      NO
         │       │
         ▼       └──→ [RETURN: None]
    ┌──────────────────────────────┐
    │ STEP 2: MORNING WINDOW       │
    │ Hours from open < 4?         │
    └────────┬──────────────────────┘
             │
         ┌───┴───┐
        YES      NO
         │       │
         ▼       └──→ [RETURN: None]
    ┌──────────────────────────────┐
    │ STEP 3: WEEKEND MOVE         │
    │ |price - friday_close| /     │
    │ friday_close > 2%?           │
    └────────┬──────────────────────┘
             │
         ┌───┴───┐
        YES      NO
         │       │
         ▼       └──→ [RETURN: None]
    ┌──────────────────────────────┐
    │ STEP 4: REVERSAL CHECK       │
    │ Is price reversing?          │
    │ Last 2 candles show counter? │
    └────────┬──────────────────────┘
             │
         ┌───┴───┐
        YES      NO
         │       │
         ▼       └──→ [RETURN: None]
    ┌──────────────────────────────┐
    │ STEP 5: DETERMINE DIRECTION  │
    │ If price moved UP from Fri:  │
    │   → Direction = SHORT        │
    │ If price moved DOWN from Fri:│
    │   → Direction = LONG         │
    └────────┬──────────────────────┘
             │
             ▼
    ┌──────────────────────────────┐
    │ STEP 6: SET TARGETS          │
    │ TP1 = friday_close           │
    │ TP2 = friday_close ± 1%      │
    │ TP3 = friday_close ± 2%      │
    │ (Mean reversion targets)     │
    └────────┬──────────────────────┘
             │
             ▼
    ┌──────────────────────────────┐
    │ [RETURN: PatternData]        │
    │ • Direction: Opposite move   │
    │ • Entry: Current price       │
    │ • Stop: Weekend extreme + ATR│
    │ • TP: Friday close levels    │
    │ • Confidence: 0.6-0.9        │
    └──────────────────────────────┘

EXPECTED: 65-75% win rate (HIGHEST!)
TIME WINDOW: Monday 00:00-04:00 UTC only
TRADE TIME: 30 min - 2 hours (QUICK)
FREQUENCY: 2-4 signals/month
```

---

## Pattern 4: Board Meeting - BREAKOUT PATTERN

### Detection Logic Flow

```
┌─────────────────────────────────────────┐
│  BOARD MEETING DETECTION                │
│  Tight Consolidation Before Breakout    │
│  Breakout from indecision               │
└────────────┬──────────────────────────┘
             │
             ▼
    ┌──────────────────────────────┐
    │ STEP 1: FIND CONSOLIDATION   │
    │ Last 24 candles              │
    │ Range = (H - L) / L          │
    │ Check: Range < 2%?           │
    └────────┬──────────────────────┘
             │
         ┌───┴───┐
        YES      NO
         │       │
         ▼       └──→ [RETURN: None]
    ┌──────────────────────────────┐
    │ STEP 2: DURATION CHECK       │
    │ Consolidation lasted         │
    │ 6-24 candles?                │
    └────────┬──────────────────────┘
             │
         ┌───┴───┐
        YES      NO
         │       │
         ▼       └──→ [RETURN: None]
    ┌──────────────────────────────┐
    │ STEP 3: QUALITY CHECK        │
    │ Early volume < late volume?  │
    │ (Institutions building)      │
    └────────┬──────────────────────┘
             │
         ┌───┴───┐
        YES      NO
         │       │
         ▼       (OK, continue)
    ┌──────────────────────────────┐
    │ STEP 4: BREAKOUT DETECTION   │
    │ Current price breaks above   │
    │ consolidation high OR below  │
    │ consolidation low?           │
    │ Break > 50% of range?        │
    └────────┬──────────────────────┘
             │
         ┌───┴───┐
        YES      NO
         │       │
         ▼       └──→ [RETURN: None]
    ┌──────────────────────────────┐
    │ STEP 5: VOLUME CONFIRMATION  │
    │ Breakout candle volume       │
    │ > avg volume × 1.5?          │
    └────────┬──────────────────────┘
             │
         ┌───┴───┐
        YES      NO
         │       │
         ▼       └──→ [RETURN: None]
    ┌──────────────────────────────┐
    │ STEP 6: DIRECTION            │
    │ If breakout upward: LONG     │
    │ If breakout downward: SHORT  │
    └────────┬──────────────────────┘
             │
             ▼
    ┌──────────────────────────────┐
    │ STEP 7: MEASURED MOVE        │
    │ Height = High - Low of consol│
    │ TP1 = High + (height × 1.0)  │
    │ TP2 = High + (height × 2.0)  │
    │ TP3 = High + (height × 3.0)  │
    └────────┬──────────────────────┘
             │
             ▼
    ┌──────────────────────────────┐
    │ [RETURN: PatternData]        │
    │ • Direction: Breakout dir    │
    │ • Entry: Current price       │
    │ • Stop: Opposite extreme + ATR
    │ • TP: Measured moves         │
    │ • Confidence: 0.5-0.8        │
    └──────────────────────────────┘

EXPECTED: 50-55% win rate
TIMEFRAME: 4H, Daily preferred
TRADE TIME: 4-24 hours
FREQUENCY: 1-3 signals/month
```

---

## Pattern 5: Three Hits Reversal - EXHAUSTION PATTERN

### Detection Logic Flow

```
┌─────────────────────────────────────────┐
│  THREE HITS REVERSAL DETECTION          │
│  Market Exhaustion After 3rd Touch      │
│  Trades weekly high/low rejections      │
└────────────┬──────────────────────────┘
             │
             ▼
    ┌──────────────────────────────┐
    │ STEP 1: TOUCH COUNT CHECK    │
    │ Is weekly_high_touches ≥ 3?  │
    │ OR weekly_low_touches ≥ 3?   │
    └────────┬──────────────────────┘
             │
         ┌───┴───┐
        YES      NO
         │       │
         ▼       └──→ [RETURN: None]
    ┌──────────────────────────────┐
    │ STEP 2: CURRENT POSITION     │
    │ Is current candle at the     │
    │ touched level now?           │
    │ Within ±0.5% of level?       │
    └────────┬──────────────────────┘
             │
         ┌───┴───┐
        YES      NO
         │       │
         ▼       └──→ [RETURN: None]
    ┌──────────────────────────────┐
    │ STEP 3: REJECTION CONFIRMATION
    │ Does candle have:            │
    │ • Wick touching level        │
    │ • Close on opposite side      │
    │ • Small body size (rejection) │
    └────────┬──────────────────────┘
             │
         ┌───┴───┐
        YES      NO
         │       │
         ▼       └──→ [RETURN: None]
    ┌──────────────────────────────┐
    │ STEP 4: DIRECTION            │
    │ At weekly high 3×:           │
    │   → Direction = SHORT        │
    │ At weekly low 3×:            │
    │   → Direction = LONG         │
    └────────┬──────────────────────┘
             │
             ▼
    ┌──────────────────────────────┐
    │ STEP 5: CALCULATE TARGETS    │
    │ Range = WH - WL              │
    │                              │
    │ If at high (SHORT):          │
    │ TP1 = WH - (range × 0.3)     │
    │ TP2 = WH - (range × 0.5)     │
    │ TP3 = WL (full range)        │
    │                              │
    │ If at low (LONG):            │
    │ TP1 = WL + (range × 0.3)     │
    │ TP2 = WL + (range × 0.5)     │
    │ TP3 = WH (full range)        │
    └────────┬──────────────────────┘
             │
             ▼
    ┌──────────────────────────────┐
    │ [RETURN: PatternData]        │
    │ • Direction: Opposite of 3×  │
    │ • Entry: Current price       │
    │ • Stop: Level + ATR×1.5      │
    │ • TP: Range-based            │
    │ • Confidence: 0.7-0.85       │
    └──────────────────────────────┘

EXPECTED: 65-75% win rate
FREQUENCY: 1-2 signals/month
TRADE TIME: 1-4 hours
```

---

## Pattern 6: Trapping Volume - FAKE BREAKOUT REVERSAL

### Detection Logic Flow

```
┌─────────────────────────────────────────┐
│  TRAPPING VOLUME DETECTION              │
│  Large Wicks Trap Traders               │
│  Quick counter-trend plays              │
└────────────┬──────────────────────────┘
             │
             ▼
    ┌──────────────────────────────┐
    │ STEP 1: DETECT WICKS         │
    │ Current candle analysis      │
    │ Upper wick = H - max(O,C)    │
    │ Lower wick = min(O,C) - L    │
    │ Range = H - L                │
    │                              │
    │ Wick ratios:                 │
    │ Upper = upper_wick / range   │
    │ Lower = lower_wick / range   │
    └────────┬──────────────────────┘
             │
         ┌───┴────┬─────────┐
        >50%      |        <50%
      (Upper)     |       
         │        |
    ┌────▼──┐    └──→ [CHECK LOWER]
    │Upper  │
    │ Wick  │
    │Trap   │
    │found  │
    └────┬──┘
         │
         ▼
    ┌──────────────────────────────┐
    │ STEP 2: BODY CHECK           │
    │ Body should be small         │
    │ Opposite side of wick        │
    │ (Confirms fake break)        │
    └────────┬──────────────────────┘
             │
         ┌───┴───┐
        YES      NO
         │       │
         ▼       └──→ [RETURN: None]
    ┌──────────────────────────────┐
    │ STEP 3: VOLUME CONFIRMATION  │
    │ Current volume               │
    │ > avg volume × 1.5?          │
    └────────┬──────────────────────┘
             │
         ┌───┴───┐
        YES      NO
         │       │
         ▼       └──→ [RETURN: None]
    ┌──────────────────────────────┐
    │ STEP 4: DIRECTION            │
    │ If upper wick > 50%:         │
    │   Direction = SHORT          │
    │   (Bullish trap caught)      │
    │                              │
    │ If lower wick > 50%:         │
    │   Direction = LONG           │
    │   (Bearish trap caught)      │
    └────────┬──────────────────────┘
             │
             ▼
    ┌──────────────────────────────┐
    │ STEP 5: QUICK TARGETS        │
    │ Opposite extreme of wick     │
    │ TP1 = Opp ± (range × 0.5)    │
    │ TP2 = Opp ± (range × 1.0)    │
    │ TP3 = Opp ± (range × 1.5)    │
    └────────┬──────────────────────┘
             │
             ▼
    ┌──────────────────────────────┐
    │ [RETURN: PatternData]        │
    │ • Direction: Opposite wick   │
    │ • Entry: Next candle         │
    │ • Stop: Wick extreme + ATR   │
    │ • TP: Quick scalp targets    │
    │ • Confidence: 0.5-0.75       │
    └──────────────────────────────┘

EXPECTED: 45-55% win rate (lower, but quick)
FREQUENCY: 2-4 signals/month
TRADE TIME: 15 min - 1 hour (SCALP)
PROFIT: Fast winners
```

---

## Pattern 7: One Formation - BIG BREAKOUT

### Detection Logic Flow

```
┌─────────────────────────────────────────┐
│  ONE FORMATION DETECTION                │
│  Single Decisive Breakout               │
│  Big move after consolidation           │
└────────────┬──────────────────────────┘
             │
             ▼
    ┌──────────────────────────────┐
    │ STEP 1: CONSOLIDATION        │
    │ Last 30 candles              │
    │ Range = (H - L) / L          │
    │ Check: Range < 3%?           │
    │ All candles within range?    │
    └────────┬──────────────────────┘
             │
         ┌───┴───┐
        YES      NO
         │       │
         ▼       └──→ [RETURN: None]
    ┌──────────────────────────────┐
    │ STEP 2: CANDLE SIZE          │
    │ Current candle range         │
    │ Avg range from lookback      │
    │ Check: Current > Avg × 2.0?  │
    │ (Double normal size)         │
    └────────┬──────────────────────┘
             │
         ┌───┴───┐
        YES      NO
         │       │
         ▼       └──→ [RETURN: None]
    ┌──────────────────────────────┐
    │ STEP 3: VOLUME SURGE         │
    │ Current volume               │
    │ > avg volume × 2.0?          │
    │ (Double volume)              │
    └────────┬──────────────────────┘
             │
         ┌───┴───┐
        YES      NO
         │       │
         ▼       └──→ [RETURN: None]
    ┌──────────────────────────────┐
    │ STEP 4: DECISIVE BREAK       │
    │ Candle closes:               │
    │ Above consolidation high     │
    │ OR below consolidation low   │
    │ (Not inside range)           │
    └────────┬──────────────────────┘
             │
         ┌───┴───┐
        YES      NO
         │       │
         ▼       └──→ [RETURN: None]
    ┌──────────────────────────────┐
    │ STEP 5: DIRECTION            │
    │ If breaks above: LONG        │
    │ If breaks below: SHORT       │
    └────────┬──────────────────────┘
             │
             ▼
    ┌──────────────────────────────┐
    │ STEP 6: MEASURED MOVE        │
    │ MM = High - Low of consol    │
    │ TP1 = H + (MM × 1.0)         │
    │ TP2 = H + (MM × 2.0)         │
    │ TP3 = H + (MM × 3.0)         │
    │ (Extended targets)           │
    └────────┬──────────────────────┘
             │
             ▼
    ┌──────────────────────────────┐
    │ [RETURN: PatternData]        │
    │ • Direction: Breakout dir    │
    │ • Entry: Current price       │
    │ • Stop: Consol extreme + ATR │
    │ • TP: Extended measured moves│
    │ • Confidence: 0.8-0.95       │
    └──────────────────────────────┘

EXPECTED: 70-80% win rate (BEST!)
TIMEFRAME: 1H, 4H, Daily
TRADE TIME: 2-24 hours
FREQUENCY: 1-2 signals/month
```

---

## Pattern Comparison Table

```
Pattern         │ Type      │ Win Rate │ Entry Cond    │ Hold Time │ Freq
─────────────────┼──────────┼──────────┼───────────────┼───────────┼─────
M-Pattern       │ Bearish  │ 58-62%   │Neckline break │ 4-12h     │1-3
W-Pattern       │ Bullish  │ 58-62%   │Neckline break │ 4-12h     │1-3
Weekend Trap    │ Reversal │ 65-75%   │Monday morning │ 30m-2h    │2-4
Board Meeting   │ Breakout │ 50-55%   │Range break    │ 4-24h     │1-3
Three Hits      │ Reversal │ 65-75%   │3rd rejection  │ 1-4h      │1-2
Trap Volume     │ Reversal │ 45-55%   │Next candle    │ 15m-1h    │2-4
One Formation   │ Breakout │ 70-80%   │Decisive break │ 2-24h     │1-2
─────────────────┴──────────┴──────────┴───────────────┴───────────┴─────

BEST PATTERNS by Win Rate:
1. One Formation: 70-80%
2. Three Hits: 65-75%
2. Weekend Trap: 65-75%
4. M-Pattern: 58-62%
4. W-Pattern: 58-62%
6. Board Meeting: 50-55%
7. Trapping Volume: 45-55%

MOST FREQUENT:
1. Trapping Volume: 2-4/month (scalps)
2. Weekend Trap: 2-4/month
2. M-Pattern: 1-3/month
2. W-Pattern: 1-3/month
2. Board Meeting: 1-3/month
6. Three Hits: 1-2/month
6. One Formation: 1-2/month
```

---

## Risk/Reward Expectations

```
Pattern         │ Typical R:R │ Stop Size    │ Target Distance
─────────────────┼─────────────┼──────────────┼─────────────────
M-Pattern       │ 2.0:1       │ ATR × 1.5    │ Pattern height
W-Pattern       │ 2.0:1       │ ATR × 1.5    │ Pattern height
Weekend Trap    │ 1.5:1       │ ATR × 1.5    │ % from Friday
Board Meeting   │ 2.5:1       │ ATR × 1.5    │ 3× range
Three Hits      │ 2.0:1       │ ATR × 1.5    │ Range-based
Trap Volume     │ 2.0:1       │ ATR × 0.5    │ Scalp distances
One Formation   │ 3.0:1       │ ATR × 1.5    │ 3× measured move
```

---

## Quick Reference: Which Pattern When?

```
Looking for BEST WIN RATE?
└─→ One Formation (70-80%) or Three Hits (65-75%)

Looking for MOST FREQUENT SIGNALS?
└─→ Trapping Volume (2-4/month) or Weekend Trap (2-4/month)

Looking for QUICKEST TRADES?
└─→ Weekend Trap (30m-2h) or Trapping Volume (15m-1h)

Looking for EXTENDED MOVES?
└─→ One Formation or Board Meeting (multiple targets)

Trading MAINLY MORNINGS?
└─→ Weekend Trap (Monday AM only)

Trading ALL DAY?
└─→ M-Pattern, W-Pattern, Board Meeting, Three Hits

Want SCALP PROFITS?
└─→ Trapping Volume (fast wins)

Want SWING TRADES?
└─→ One Formation, M-Pattern, W-Pattern (4-12 hours)
```

---

**This markdown diagram provides complete decision logic for all 7 TBD patterns with detailed calculations and thresholds.**
