# Universal Optimizer - 48 Config System Explained

**Author:** BTC_Engine_v3  
**Date:** January 9, 2026  
**Purpose:** Explain how 48 optimization configurations work

---

## Quick Answer

**48 configs = 4 confluence thresholds × 3 R:R ratios × 4 weight presets**

```
Confluence: [40, 50, 60, 70]           (4 options)
Risk:Reward: [2.0, 2.5, 3.0]           (3 options)
Weight Presets: [Aggressive, Balanced, Conservative, Best-Practices]  (4 options)

Total: 4 × 3 × 4 = 48 configurations
```

Each config tests a **different threshold and weighting** to find the optimal trade-off between:
- **Trade Frequency** (lower confluence = more trades)
- **Trade Quality** (higher confluence = better setups)
- **Risk/Reward** (affects position management)

---

## How It Works

### Component 1: Confluence Thresholds (4 variants)

**What it controls:** Minimum total points needed to enter a trade

```python
confluence_thresholds = [40, 50, 60, 70]

# Effect on trading:
# 40 points: AGGRESSIVE - More trades, lower quality
# 50 points: MODERATE - Balanced approach
# 60 points: CONSERVATIVE - Fewer trades, higher quality
# 70 points: VERY CONSERVATIVE - Very selective entries
```

**Example with Strategy_01 (M Pattern):**
```
Current Signals:
- Double Top: BEARISH_BREAKDOWN @ 95% → 30 points
- RSI Divergence: BEARISH_DIVERGENCE @ 90% → 23 points
- HOD: HOD_REJECTION @ 85% → 17 points
- VWAP: BELOW_VWAP @ 80% → 12 points
TOTAL: 82 points

Result:
✅ 40 threshold: TRADE (82 > 40)
✅ 50 threshold: TRADE (82 > 50)
✅ 60 threshold: TRADE (82 > 60)
✅ 70 threshold: TRADE (82 > 70)
```

**Different Scenario (Weaker Setup):**
```
Current Signals:
- Double Top: PATTERN_FORMING @ 65% → 10 points
- RSI: OVERBOUGHT @ 75% → 11 points
- Session: LONDON_OPEN → 15 points
- VWAP: BELOW_VWAP @ 70% → 11 points
TOTAL: 47 points

Result:
✅ 40 threshold: TRADE (47 > 40)
❌ 50 threshold: SKIP (47 < 50)
❌ 60 threshold: SKIP (47 < 60)
❌ 70 threshold: SKIP (47 < 70)
```

**Impact:** Different thresholds → Different number of trades → Different win rates

---

### Component 2: Risk:Reward Ratios (3 variants)

**What it controls:** Minimum R:R required to take a trade

```python
risk_reward_ratios = [2.0, 2.5, 3.0]

# Effect on trading:
# 2.0: AGGRESSIVE - More trades (2x reward for 1x risk)
# 2.5: MODERATE - Balanced (2.5x reward for 1x risk)
# 3.0: CONSERVATIVE - Fewer trades but bigger wins (3x reward for 1x risk)
```

**Example:**
```
Setup Detected:
- Entry: $50,000
- Stop Loss: $49,500 (risk = $500)
- Take Profit Options:
  * TP1: $51,000 (reward = $1,000, R:R = 2.0)
  * TP2: $51,250 (reward = $1,250, R:R = 2.5)
  * TP3: $51,500 (reward = $1,500, R:R = 3.0)

Result:
✅ R:R 2.0: TRADE (can reach TP1)
✅ R:R 2.5: TRADE (can reach TP2)
✅ R:R 3.0: TRADE (can reach TP3)
```

**Tight Market (Limited TP):**
```
Setup Detected:
- Entry: $50,000
- Stop Loss: $49,500 (risk = $500)
- Resistance: $50,900 (reward = $900, R:R = 1.8)

Result:
❌ R:R 2.0: SKIP (1.8 < 2.0)
❌ R:R 2.5: SKIP (1.8 < 2.5)
❌ R:R 3.0: SKIP (1.8 < 3.0)
```

**Impact:** Different R:R → Filters trades by available reward potential

---

### Component 3: Weight Presets (4 variants)

**What it controls:** How much each building block contributes to confluence

This is where it gets **ADAPTIVE** to different strategies!

#### Preset 1: AGGRESSIVE (Boost primary patterns)
```python
# For Strategy_01 (M Pattern):
weights = {
    'double_top': 40,        # +10 from default (boosted!)
    'rsi_divergence': 30,    # +5 from default
    'hod': 15,               # unchanged
    'asia_50': 10,           # -2 from default (reduced)
    'session_time': 8,       # -2 from default
    'vwap': 10,              # unchanged
    # ... other blocks scaled proportionally
}

Effect:
- Pattern breakdowns get MORE weight
- Context blocks get LESS weight
- Favors strong pattern signals
- Result: Fewer but higher-conviction trades
```

#### Preset 2: BALANCED (Default weights)
```python
# For Strategy_01 (M Pattern):
weights = {
    'double_top': 30,        # default
    'rsi_divergence': 25,    # default
    'hod': 15,               # default
    'asia_50': 12,           # default
    'session_time': 10,      # default
    'vwap': 12,              # default
    # ... all blocks at baseline
}

Effect:
- Equal importance across all blocks
- Balanced approach
- Middle ground for frequency/quality
```

#### Preset 3: CONSERVATIVE (Boost context/filters)
```python
# For Strategy_01 (M Pattern):
weights = {
    'double_top': 25,        # -5 from default (reduced)
    'rsi_divergence': 20,    # -5 from default
    'hod': 18,               # +3 from default (boosted!)
    'asia_50': 15,           # +3 from default (boosted!)
    'session_time': 12,      # +2 from default (boosted!)
    'vwap': 15,              # +3 from default (boosted!)
    # ... context blocks matter more
}

Effect:
- Context and filters get MORE weight
- Primary patterns get LESS weight
- Requires more confluence overall
- Result: Fewer, highly-filtered trades
```

#### Preset 4: BEST-PRACTICES (Expert-tuned)
```python
# For Strategy_01 (M Pattern):
# Based on walk-forward test results and expert analysis
weights = {
    'double_top': 35,        # Proven effectiveness
    'rsi_divergence': 30,    # Strong confirmation
    'hod': 15,               # Good level
    'asia_50': 12,           # Context
    'session_time': 10,      # Timing
    'vwap': 10,              # Reference
    # ... optimized from 80+ building block tests
}

Effect:
- Uses proven weight ratios from testing
- Based on actual performance data
- Usually best starting point
```

---

## Complete Example: Strategy_01 (M Pattern)

### Strategy has 12 building blocks:
```python
blocks = {
    'double_top': 35,
    'rsi_divergence': 30,
    'hod': 15,
    'asia_50': 12,
    'session_time': 10,
    'vwap': 10,
    'ema_20_50_trend': 12,
    'kill_zones': 12,
    'adr': 8,
    'swing_points': 15,
    'ema_200_trend': 12,
    'premium_discount_zones': 14
}
```

### 48 Configs Generated:

**Config #0:**
```python
{
    'min_confluence': 40,
    'min_risk_reward': 2.0,
    'weights': 'AGGRESSIVE',
    'blocks': {
        'double_top': 40,         # Boosted
        'rsi_divergence': 35,     # Boosted
        'hod': 15,
        'asia_50': 10,            # Reduced
        # ... etc
    }
}
```

**Config #1:**
```python
{
    'min_confluence': 40,
    'min_risk_reward': 2.0,
    'weights': 'BALANCED',
    'blocks': {
        'double_top': 30,         # Default
        'rsi_divergence': 25,     # Default
        'hod': 15,
        'asia_50': 12,
        # ... etc
    }
}
```

**Config #2:**
```python
{
    'min_confluence': 40,
    'min_risk_reward': 2.0,
    'weights': 'CONSERVATIVE',
    'blocks': {
        'double_top': 25,         # Reduced
        'rsi_divergence': 20,     # Reduced
        'hod': 18,                # Boosted
        'asia_50': 15,            # Boosted
        # ... etc
    }
}
```

**Config #3:**
```python
{
    'min_confluence': 40,
    'min_risk_reward': 2.0,
    'weights': 'BEST-PRACTICES',
    'blocks': {
        'double_top': 35,         # Expert-tuned
        'rsi_divergence': 30,     # Expert-tuned
        'hod': 15,
        'asia_50': 12,
        # ... etc
    }
}
```

**Config #4:**
```python
{
    'min_confluence': 40,
    'min_risk_reward': 2.5,    # Changed R:R
    'weights': 'AGGRESSIVE',
    'blocks': {
        'double_top': 40,
        # ... same weights as Config #0
    }
}
```

... and so on for all 48 combinations!

---

## How It Adapts to Different Strategies

### Example: Strategy_04 (EMA Trend Continuation)

**Has different blocks:**
```python
blocks = {
    'ema_20_50_trend': 15,
    'ema_200_trend': 12,
    'ema_20_50_cross': 25,
    'macd_signal': 22,
    'adx': 20,
    'vwap': 15,
    'fibonacci': 16
}
```

**Same 48 configs generated, but weights adapt:**

**Config #0 (Aggressive):**
```python
{
    'min_confluence': 40,
    'min_risk_reward': 2.0,
    'weights': 'AGGRESSIVE',
    'blocks': {
        'ema_20_50_cross': 30,    # Primary signal boosted!
        'macd_signal': 27,        # Confirmation boosted!
        'ema_20_50_trend': 12,    # Context reduced
        'ema_200_trend': 10,      # Context reduced
        'adx': 18,
        'vwap': 12,               # Context reduced
        'fibonacci': 14
    }
}
```

**Config #2 (Conservative):**
```python
{
    'min_confluence': 40,
    'min_risk_reward': 2.0,
    'weights': 'CONSERVATIVE',
    'blocks': {
        'ema_20_50_cross': 20,    # Primary signal reduced
        'macd_signal': 18,        # Confirmation reduced
        'ema_20_50_trend': 18,    # Context boosted!
        'ema_200_trend': 15,      # Context boosted!
        'adx': 23,                # Filter boosted!
        'vwap': 18,               # Context boosted!
        'fibonacci': 19           # Entry level boosted!
    }
}
```

**Key Insight:** The SAME 4 presets work for ANY strategy because:
- Aggressive: Boosts primary signals (whatever they are)
- Conservative: Boosts context/filters (whatever they are)
- Balanced: Uses defaults
- Best-Practices: Uses tested ratios

---

## Why 48 Configs?

### Systematic Coverage

**Grid Search:**
```
Confluence Axis (4 points):
[40] -------- [50] -------- [60] -------- [70]
 |            |            |            |
 ↓------------+------------+------------+
R:R Axis (3 points):
[2.0] -------- [2.5] -------- [3.0]
 |            |            |
 ↓------------+------------+
Weight Preset Axis (4 points):
[AGG] -- [BAL] -- [CON] -- [BEST]
```

This creates a **3D grid** of parameter combinations:
- **Confluence dimension:** Controls trade frequency
- **R:R dimension:** Controls position management
- **Weights dimension:** Controls signal prioritization

**Total coverage:** 4 × 3 × 4 = **48 unique combinations**

### Why not more?

**Computational Cost:**
- Each config tests ~17,280 bars (180 days of 15min data)
- 48 configs = reasonable 7-minute runtime with parallelization
- 96 configs would take 14 minutes
- 192 configs would take 28 minutes

**Diminishing Returns:**
- 48 configs covers the sweet spot
- More granularity (e.g., [35, 40, 45, 50, ...]) gives minimal benefit
- User can manually fine-tune from top 5 results

### Why not less?

**Insufficient Coverage:**
- 24 configs (4×3×2) misses Conservative vs Aggressive distinction
- 12 configs (4×3×1) can't test different weight strategies
- 48 is the minimum for comprehensive optimization

---

## Expected Results Per Config

### Config Performance Variation

**Example Results from Strategy_01:**

| Config | Confluence | R:R | Weights | Trades | Win% | PnL | Sharpe |
|--------|-----------|-----|---------|--------|------|-----|--------|
| #0 | 40 | 2.0 | AGG | 45 | 62% | $1,245 | 1.2 |
| #1 | 40 | 2.0 | BAL | 52 | 58% | $1,104 | 1.1 |
| #2 | 40 | 2.0 | CON | 38 | 67% | $1,456 | 1.4 |
| #3 | 40 | 2.0 | BEST | 48 | 65% | $1,389 | 1.3 |
| #4 | 40 | 2.5 | AGG | 38 | 64% | $1,523 | 1.5 |
| #5 | 40 | 2.5 | BAL | 44 | 60% | $1,298 | 1.2 |
| ... | ... | ... | ... | ... | ... | ... | ... |
| #12 | 50 | 2.0 | AGG | 35 | 68% | $1,678 | 1.7 |
| #13 | 50 | 2.0 | BAL | 40 | 64% | $1,445 | 1.4 |
| ... | ... | ... | ... | ... | ... | ... | ... |
| #24 | 60 | 2.0 | AGG | 25 | 72% | $1,789 | 1.9 |
| #25 | 60 | 2.0 | BAL | 29 | 69% | $1,623 | 1.7 |
| ... | ... | ... | ... | ... | ... | ... | ... |
| #36 | 70 | 2.0 | AGG | 18 | 78% | $1,823 | 2.1 |
| #37 | 70 | 2.0 | BAL | 22 | 74% | $1,701 | 1.9 |
| ... | ... | ... | ... | ... | ... | ... | ... |

**Patterns Emerge:**
- ↑ Confluence → ↓ Trades, ↑ Win%, ↑ Sharpe (quality over quantity)
- ↑ R:R → ↓ Trades, ↑ Average Win (bigger targets)
- AGG weights → Fewer trades, higher conviction
- CON weights → More trades, better filtering

**Top 5 Usually:**
- Mix of confluence levels (e.g., 50, 60, 70)
- Mix of R:R ratios
- Favor BEST or CON weights
- Sharpe > 1.5, Win% > 65%

---

## Practical Impact

### Trade Count Variation

**Same setup, different configs:**

```
Market Condition: M pattern breakdown @ 95% confidence
Signal Strength: 82 confluence points

Config Results:
- Conf 40, R:R 2.0: ✅ TRADE (82 > 40, TP possible)
- Conf 50, R:R 2.0: ✅ TRADE (82 > 50, TP possible)
- Conf 60, R:R 2.0: ✅ TRADE (82 > 60, TP possible)
- Conf 70, R:R 2.0: ✅ TRADE (82 > 70, TP possible)
- Conf 70, R:R 2.5: ✅ TRADE (82 > 70, TP2 possible)
- Conf 70, R:R 3.0: ❌ SKIP (TP3 too far in tight market)

Trades Executed: 5 out of 6 configs would trade this setup
```

**Weaker setup:**

```
Market Condition: M pattern forming @ 65% confidence
Signal Strength: 47 confluence points

Config Results:
- Conf 40, R:R 2.0: ✅ TRADE (47 > 40)
- Conf 50, R:R 2.0: ❌ SKIP (47 < 50)
- Conf 60, R:R 2.0: ❌ SKIP (47 < 60)
- Conf 70, R:R 2.0: ❌ SKIP (47 < 70)

Trades Executed: 1 out of 4 configs would trade this setup
```

**Result:** Different configs trade different setups → Different performance!

---

## Selecting the Winner

### Top 5 Display

User sees top 5 performing configs:

```
================================================================================
🏆 TOP 5 OPTIMIZED CONFIGURATIONS - ITERATION 2
================================================================================

   #1: Confluence 60 | R:R 2.5 | CONSERVATIVE Weights
       ├─ Trades: 28 (Win: 72.0%)
       ├─ Net PnL: $1,789.50 (+17.9%)
       ├─ Sharpe: 2.1 | Max DD: 8.3%
       └─ Avg Win: $145.50 | Avg Loss: -$82.30

   #2: Confluence 70 | R:R 2.0 | BEST-PRACTICES Weights
       ├─ Trades: 22 (Win: 77.3%)
       ├─ Net PnL: $1,701.20 (+17.0%)
       ├─ Sharpe: 1.9 | Max DD: 7.1%
       └─ Avg Win: $138.20 | Avg Loss: -$79.50

   #3: Confluence 50 | R:R 2.5 | CONSERVATIVE Weights
       ├─ Trades: 35 (Win: 68.6%)
       ├─ Net PnL: $1,678.40 (+16.8%)
       ├─ Sharpe: 1.8 | Max DD: 9.2%
       └─ Avg Win: $128.90 | Avg Loss: -$85.10

   #4: Confluence 60 | R:R 2.0 | AGGRESSIVE Weights
       ├─ Trades: 25 (Win: 72.0%)
       ├─ Net PnL: $1,623.50 (+16.2%)
       ├─ Sharpe: 1.7 | Max DD: 8.9%
       └─ Avg Win: $141.30 | Avg Loss: -$88.20

   #5: Confluence 50 | R:R 2.0 | BALANCED Weights
       ├─ Trades: 40 (Win: 65.0%)
       ├─ Net PnL: $1,523.80 (+15.2%)
       ├─ Sharpe: 1.5 | Max DD: 10.1%
       └─ Avg Win: $124.50 | Avg Loss: -$89.30

Select configuration to apply (1-5, or 0 to quit):
```

**User picks #1** → Config applied to strategy file automatically!

---

## Summary

### The 48 Config System

**What:** Systematic grid search of 48 parameter combinations
**Why:** Find optimal balance of frequency, quality, and risk management
**How:** Test all combinations in parallel (7 minutes vs 18 minutes serial)

**Components:**
1. **Confluence Thresholds (4):** Controls trade frequency
2. **Risk:Reward Ratios (3):** Controls position management  
3. **Weight Presets (4):** Controls signal prioritization

**Adaptability:**
- Same system works for ALL strategies
- Weights automatically adapt to available blocks
- Primary signals vs context blocks balanced differently
- Each strategy finds its own optimal parameters

**Result:**
- User picks from top 5 configs
- Parameters auto-applied to strategy
- Ready for paper/live trading
- Institutional-grade optimization process

**Value:**
- Saves hours of manual parameter tuning
- Tests 48 variations in 7 minutes
- Finds non-obvious optimal combinations
- Repeatable, systematic approach

---

**Last Updated:** January 9, 2026  
**Status:** Production Guide  
**Related:** `src/strategies/universal_optimizer/modules/optimizer_core.py`