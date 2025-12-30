# Layer 0 & 0.5 Rebuild Plan - Validated Approach

**Date:** December 22, 2025  
**Status:** 🚧 IN PROGRESS  
**Objective:** Build generalizable trend detectors that predict ACTUAL price outcomes

---

## 🎯 Mission

Build Layer 0 (macro) and Layer 0.5 (micro) trend detectors that:
1. Predict actual price movement (>50% accuracy)
2. Generalize across ALL market conditions (2019-2025)
3. Combine ML precision with rule-based reliability
4. Pass rigorous outcome-based validation

---

## 📊 Current Status Assessment

### What We Have:
- ✅ Institutional orderbook features (66K snapshots, 2024-2025)
- ✅ Outcome-based validation framework
- ✅ 6 years of price data (2019-2025)

### What Failed:
- ❌ Current models: 15-23% accuracy on actual outcomes
- ❌ Overfitted to 2024-2025 data
- ❌ Features don't generalize across market regimes

### Validation Results:
```
Metric                  Current    Target
Training (2024-2025)    71%        N/A
Ground Truth Labels     39%        N/A
Actual Price Outcomes   15-23%     >50%
Random Baseline         33%        Baseline
```

---

## 🔧 Implementation Plan

### PHASE 1: Market-Invariant Feature Engineering
**Duration:** 1-2 days  
**Goal:** Create features that work in ANY market condition

#### 1.1 Normalize All Features
```python
# Instead of absolute values, use ratios/percentages
price_momentum = (close - close.shift(20)) / close.shift(20)  # Not absolute $
volume_ratio = volume / volume.rolling(50).mean()  # Not raw volume
rsi_change = rsi.diff()  # Rate of change, not level

# Market regime independent!
```

#### 1.2 Multi-Regime Feature Testing
```python
# Test each feature across:
- Bull markets (2019-2020, 2024)
- Bear markets (2022)
- Sideways (2023)
- High volatility (2020 COVID)
- Low volatility (2019)

# Keep only features that correlate >0.2 in ALL regimes
```

#### 1.3 Feature Categories
```
Traditional (Normalized):
- Price momentum ratios (multiple timeframes)
- Volume profile changes (not absolute)
- Volatility expansion/contraction
- Trend strength (not direction)

Institutional (If Available):
- Order flow imbalance ratios
- Whale activity changes (not levels)
- Depth profile shifts

Remove:
- Absolute price levels
- Absolute volume
- Market-specific patterns
```

**Deliverable:** 20-30 market-invariant features tested across all regimes

---

### PHASE 2: Proper Training Strategy
**Duration:** 2-3 days  
**Goal:** Train on diverse data, test on truly unseen periods

#### 2.1 Data Split Strategy
```
Training:   2019-2023 (5 years, multiple regimes)
Validation: H1 2024 (6 months, unseen)
Test:       H2 2024-2025 (recent unseen)

NOT: Train on 2024, test on 2025 (too similar!)
```

#### 2.2 Walk-Forward Validation
```python
# Train on expanding window
for year in [2020, 2021, 2022, 2023]:
    train_data = data[2019:year]
    test_data = data[year+1]
    
    model.fit(train_data)
    accuracy = validate_on_price_outcomes(model, test_data)
    
    if accuracy < 45%:
        print(f"Failed on {year+1} - features don't generalize")
        break

# Model must work on EVERY out-of-sample year
```

#### 2.3 Model Configuration
```python
# Prevent overfitting
XGBClassifier(
    max_depth=3,           # Shallow (was 6)
    min_child_weight=5,    # More samples per leaf
    subsample=0.8,         # Row sampling
    colsample_bytree=0.8,  # Feature sampling
    reg_alpha=1.0,         # L1 regularization
    reg_lambda=2.0,        # L2 regularization
    n_estimators=100,      # Fewer trees (was 200)
)

# Simpler = less overfitting
```

**Deliverable:** Models that achieve >45% on ALL out-of-sample years

---

### PHASE 3: Rule-Based Layer 0 (Macro)
**Duration:** 1 day  
**Goal:** Simple, robust macro trend detection

#### 3.1 Multi-Timeframe EMA System
```python
def layer0_macro_trend(df):
    """
    Simple but proven multi-TF trend detection.
    No ML - just robust price action rules.
    """
    # Multiple timeframe EMAs
    ema_4h = df['close'].ewm(span=16).mean()   # 4 hours
    ema_12h = df['close'].ewm(span=48).mean()  # 12 hours
    ema_1d = df['close'].ewm(span=96).mean()   # 1 day
    
    # Trend is UP if:
    # 1. Price > all EMAs
    # 2. EMAs stacked (4h > 12h > 1d)
    # 3. Slope positive
    
    if (df['close'] > ema_4h > ema_12h > ema_1d and
        ema_1d > ema_1d.shift(4)):
        return 'BULLISH'
    
    # Trend is DOWN if:
    elif (df['close'] < ema_4h < ema_12h < ema_1d and
          ema_1d < ema_1d.shift(4)):
        return 'BEARISH'
    
    else:
        return 'NEUTRAL'
```

#### 3.2 Validation Requirements
```
Must achieve on 2019-2025 data:
- >50% accuracy predicting 6h outcomes
- Works in ALL market conditions
- No parameter optimization (use standard EMAs)
```

**Deliverable:** Rule-based Layer 0 with >50% validated accuracy

---

### PHASE 4: ML Layer 0.5 (Micro) 
**Duration:** 2-3 days  
**Goal:** ML for tactical timing within macro trend

#### 4.1 Feature Set
```python
# Only use features that passed Phase 1 testing
# ~20 market-invariant features
# Plus: Layer 0 macro trend as input feature!

features = [
    # From Phase 1 (market-invariant only)
    'momentum_1h_ratio',
    'momentum_2h_ratio', 
    'volume_regime_change',
    'volatility_expansion',
    # ... 16 more validated features
    
    # Macro context
    'layer0_trend',  # From rule-based system
]
```

#### 4.2 Training Protocol
```python
# Train ONLY within macro trend context
# Don't predict macro - refine it

for row in training_data:
    if row['layer0_trend'] == 'BULLISH':
        # ML refines: strong bull, weak bull, or neutral
        label = get_micro_trend(row)
    elif row['layer0_trend'] == 'BEARISH':
        # ML refines: strong bear, weak bear, or neutral
        label = get_micro_trend(row)
    else:
        # Skip neutral macro periods
        continue

# ML adds precision to rule-based macro
```

#### 4.3 Validation
```python
# Must outperform Layer 0 macro by >5%
layer0_accuracy = validate_layer0(test_data)
layer05_accuracy = validate_layer05(test_data)

assert layer05_accuracy > layer0_accuracy + 5%, \
    "Layer 0.5 must add value, not noise"
```

**Deliverable:** ML Layer 0.5 with >55% accuracy (5%+ better than Layer 0)

---

### PHASE 5: Integration & Hybrid Logic
**Duration:** 1 day  
**Goal:** Combine rule-based macro + ML micro

#### 5.1 Decision Logic
```python
def get_trend_signal(timestamp):
    # Step 1: Rule-based macro (robust)
    macro_trend = layer0_macro_trend(data_up_to(timestamp))
    
    # Step 2: ML micro refinement (precise)
    if macro_trend in ['BULLISH', 'BEARISH']:
        # Only use ML when macro has direction
        micro_signal = layer05_ml_predict(data_up_to(timestamp))
        
        # Combine
        if macro_trend == 'BULLISH' and micro_signal == 'STRONG_BULLISH':
            return 'STRONG_LONG'
        elif macro_trend == 'BULLISH' and micro_signal == 'WEAK_BULLISH':
            return 'LONG_PULLBACK'
        # ... etc
    else:
        # Macro neutral - no ML needed
        return 'NEUTRAL'
```

#### 5.2 Confidence Filtering
```python
# Only trade high-confidence signals
if ml_confidence < 0.65:
    # Fall back to pure macro trend
    return macro_trend
else:
    # Use refined ML signal
    return combined_signal
```

**Deliverable:** Hybrid system that beats both components individually

---

### PHASE 6: Rigorous Validation
**Duration:** 1 day  
**Goal:** Prove system works on ALL unseen data

#### 6.1 Out-of-Sample Testing
```
Test Period 1: 2019-2020 (if trained on 2021-2025)
Test Period 2: 2024 H1 (validation set)
Test Period 3: 2024 H2-2025 (final test)

All three must be >50% accurate on actual price outcomes
```

#### 6.2 Market Regime Testing
```
Bull markets: >55% accuracy
Bear markets: >55% accuracy  
Sideways: >45% accuracy (harder)
High vol: >50% accuracy
Low vol: >50% accuracy

Must work in ALL conditions!
```

#### 6.3 Walk-Forward Validation
```python
# Simulate real-time deployment
results = []
for month in range(72):  # 6 years
    train_data = data[:month]
    test_data = data[month:month+1]
    
    model.fit(train_data)
    accuracy = test_on_actual_outcomes(model, test_data)
    results.append(accuracy)

assert np.mean(results) > 50%, "Must work consistently"
assert np.std(results) < 15%, "Must be stable"
```

**Deliverable:** Documented proof system works across all conditions

---

## 📋 Success Criteria

### Minimum Viable:
- [ ] Layer 0 (rule-based): >50% on actual price outcomes
- [ ] Layer 0.5 (ML): >55% on actual price outcomes  
- [ ] Combined: >57% on actual price outcomes
- [ ] Validated on 2019-2025 (all regimes)
- [ ] Walk-forward test >50% every period

### Production Ready:
- [ ] Layer 0: >55%
- [ ] Layer 0.5: >60%
- [ ] Combined: >62%
- [ ] High-confidence signals: >70%
- [ ] Stable across all market conditions

---

## 🛠️ Implementation Order

**Week 1:**
1. Phase 1: Engineer market-invariant features (2 days)
2. Phase 2: Implement proper training strategy (2 days)
3. Phase 3: Build rule-based Layer 0 (1 day)

**Week 2:**
4. Phase 4: Train ML Layer 0.5 (2 days)
5. Phase 5: Integrate hybrid system (1 day)
6. Phase 6: Rigorous validation (2 days)

**Total:** ~10 working days for bulletproof system

---

## 🎯 Key Principles

1. **Market-Invariant Features Only**
   - Test on ALL regimes before using
   - Ratios, not absolutes
   - Changes, not levels

2. **Proper Train/Test Splits**
   - Train on old data (2019-2023)
   - Test on new data (2024-2025)
   - Never mix similar time periods

3. **Validate on Actual Outcomes**
   - Not labels
   - Not training accuracy
   - Only real price movement matters

4. **Hybrid Approach**
   - Rules for reliability
   - ML for precision
   - Don't replace, enhance

5. **Iterative Improvement**
   - If <50%, fix features
   - Don't force outcomes
   - Let data guide you

---

## 📊 Tracking Progress

Current validation framework in place:
- ✅ `validate_nested_trends_by_price_outcome.py`
- ✅ Tests against actual price movement
- ✅ Multiple timeframe analysis
- ✅ Detailed per-class metrics

Use this for EVERY iteration:
```bash
# After each improvement
python3 scripts/validation/validate_nested_trends_by_price_outcome.py

# Must see improvement or change approach
```

---

## 🚀 Getting Started

**Next Steps:**
1. Review this plan
2. Start Phase 1: Market-invariant feature engineering
3. Test each feature across 2019-2025
4. Keep only features that work in ALL conditions
5. Proceed to Phase 2 only when features are proven

**Remember:**
- Don't force outcomes
- Validate on actual price movement
- Simple often beats complex
- Generalization > Training accuracy

---

**Status:** Ready to implement  
**Estimated Completion:** 2 weeks  
**Success Metric:** >50% accuracy on actual price outcomes across all market conditions
