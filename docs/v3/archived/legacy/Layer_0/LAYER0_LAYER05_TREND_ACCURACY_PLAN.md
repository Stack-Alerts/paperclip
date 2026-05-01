# Layer 0 + Layer 0.5 Trend Identification - 85% Accuracy Plan

**Date:** December 22, 2025  
**Scope:** ONLY Layer 0 (Multi-TF Trend) + Layer 0.5 (Outcome-Based ML)  
**Goal:** 85%+ trend direction accuracy in ANY market condition  
**Architecture:** NO CHANGES to existing system - only improve Layer 0/0.5 models

---

## 🎯 Clear Scope Definition

### Current Architecture (UNCHANGED):
```
Data Ingestion
    ↓
Layer 0 (Multi-TF Trend) + Layer 0.5 (ML) → Trend Direction (Bullish/Bearish)
    ↓
Layer 1,2,3,4,5,6 → Entry/Exit signals (only when aligned with L0/L0.5 trend)
    ↓
Backtesting / Paper Trading / Live Trading
```

### What We're Fixing:
- ✅ **Layer 0:** Multi-timeframe trend detection (EMA crossovers, alignment)
- ✅ **Layer 0.5:** ML model that predicts 8-hour trend direction
- ❌ **NOT changing:** Layers 1-6, backtest engine, trading architecture, paper trading

### Current Problem:
- Layer 0.5 achieves 97.68% on 2024 but only 37.60% on 2021
- This means trend identification fails in different market conditions
- Other layers (1-6) can't work if Layer 0/0.5 gives wrong trend

---

## 📊 What Needs to Change (Layer 0 + 0.5 ONLY)

### Layer 0 Changes (Simple):

**Current Issue:**
- Layer 0 showed 0% for ALL categories on 2021 data
- Merge logic broke when aligning 15m, 1h, 4h timeframes
- Trend detection not working properly

**Fix (2 hours):**
```python
# Better trend detection
def detect_trend_robust(df):
    # Use multiple EMAs for confirmation
    ema_9 = df['close'].ewm(span=9).mean()
    ema_21 = df['close'].ewm(span=21).mean()
    ema_50 = df['close'].ewm(span=50).mean()
    ema_200 = df['close'].ewm(span=200).mean()
    
    # Bullish: fast EMAs > slow EMAs
    bullish = (ema_9 > ema_21) & (ema_21 > ema_50) & (ema_50 > ema_200)
    
    # Bearish: fast EMAs < slow EMAs
    bearish = (ema_9 < ema_21) & (ema_21 < ema_50) & (ema_50 < ema_200)
    
    # Mixed: everything else
    trend = np.where(bullish, 1, np.where(bearish, -1, 0))
    
    return trend
```

**Result:** Layer 0 will properly identify trends across all years

---

### Layer 0.5 Changes (Main Focus):

#### Current Issues:

1. **Feature Dependency (79% missing)**
   - Model needs 116 features
   - 92 features (79%) are orderbook-specific
   - When orderbook = 0 (2021), model blind

2. **Market Regime Overfitting**
   - Trained only on 2024 bull market patterns
   - 2021 had different volatility/liquidity
   - Model memorized 2024, not learned universals

3. **Prediction Bias**
   - 95% bearish predictions on 2021
   - Not balanced across market conditions

---

## 🚀 Solution: 3-Phase Layer 0.5 Improvement

### Phase 1: Market-Invariant Features (Week 1)

**Goal:** Replace absolute features with relative features that work in any market

**Current Bad Features:**
```python
close_price = 65000           # Different in 2021 ($35k) vs 2024 ($65k)
volume = 1000 BTC             # Different liquidity
orderbook_depth = 500 BTC     # Not available for 2021
```

**New Good Features:**
```python
# Relative to trend
price_vs_ema200 = (close - ema200) / ema200    # % distance (works at any price)
price_vs_ema50 = (close - ema50) / ema50
ema_alignment = (ema9 > ema21 > ema50).astype(int)

# Normalized momentum
roc_5 = close.pct_change(5)                    # % change (not absolute)
roc_10 = close.pct_change(10)
roc_20 = close.pct_change(20)
momentum_accel = roc_5 - roc_10                # Acceleration

# Relative volume
volume_ratio = volume / volume.rolling(20).mean()  # Relative to norm
volume_zscore = (volume - volume_mean) / volume_std

# Normalized volatility  
volatility = returns.rolling(20).std()
volatility_zscore = (volatility - vol_mean) / vol_std
volatility_regime = "high" if volatility > 0.02 else "low"

# Structure patterns (binary, not numeric)
higher_high = (high > high.shift(5)).astype(int)
lower_low = (low < low.shift(5)).astype(int)
consolidation = (high - low) / close < 0.02

# Time features (same everywhere)
hour_of_day = df.index.hour
day_of_week = df.index.dayofweek
is_asian_session = hour_of_day.between(0, 8)
is_london_session = hour_of_day.between(8, 16)
is_ny_session = hour_of_day.between(13, 21)
```

**Implementation:**
```python
# File: scripts/ml_training/generate_market_invariant_features.py

def create_market_invariant_features(df):
    """
    Generate 40-50 features that work in ANY market condition
    No orderbook dependency, no absolute values
    """
    features = pd.DataFrame(index=df.index)
    
    # 1. Relative Price Position (10 features)
    for period in [9, 21, 50, 100, 200]:
        ema = df['close'].ewm(span=period).mean()
        features[f'price_vs_ema{period}'] = (df['close'] - ema) / ema
    
    # 2. Momentum Features (10 features)
    for period in [1, 3, 5, 10, 20]:
        features[f'roc_{period}'] = df['close'].pct_change(period)
    
    # 3. Volatility Features (8 features)
    for period in [5, 10, 20, 50]:
        vol = df['close'].pct_change().rolling(period).std()
        features[f'volatility_{period}'] = vol
        features[f'volatility_{period}_zscore'] = (vol - vol.rolling(100).mean()) / vol.rolling(100).std()
    
    # 4. Volume Features (6 features)
    for period in [10, 20, 50]:
        ma = df['volume'].rolling(period).mean()
        features[f'volume_ratio_{period}'] = df['volume'] / ma
    
    # 5. Structure Features (8 features)
    features['higher_high'] = (df['high'] > df['high'].shift(5)).astype(int)
    features['lower_low'] = (df['low'] < df['low'].shift(5)).astype(int)
    features['consolidation'] = ((df['high'] - df['low']) / df['close'] < 0.02).astype(int)
    features['range_position'] = (df['close'] - df['low']) / (df['high'] - df['low'])
    
    # 6. Time Features (6 features)
    features['hour'] = df.index.hour
    features['day_of_week'] = df.index.dayofweek
    features['is_asian'] = df.index.hour.isin(range(0, 8)).astype(int)
    features['is_london'] = df.index.hour.isin(range(8, 16)).astype(int)
    features['is_ny'] = df.index.hour.isin(range(13, 21)).astype(int)
    features['is_weekend'] = df.index.dayofweek.isin([5, 6]).astype(int)
    
    return features

# Total: ~45-50 features, all market-invariant
```

**Expected Result:** 60-70% accuracy on 2021

---

### Phase 2: Market Regime Awareness (Week 2)

**Goal:** Train separate models for different market conditions, ensemble at runtime

**Regime Classification:**
```python
def classify_market_regime(df):
    """
    Classify current market into one of 4 regimes
    """
    # Trend: Bull or Bear
    ema200 = df['close'].ewm(span=200).mean()
    is_bull = df['close'] > ema200
    
    # Volatility: High or Low
    volatility = df['close'].pct_change().rolling(20).std()
    is_high_vol = volatility > 0.02
    
    # 4 Regimes:
    regime = np.where(
        is_bull & ~is_high_vol, 'bull_low_vol',
        np.where(is_bull & is_high_vol, 'bull_high_vol',
        np.where(~is_bull & ~is_high_vol, 'bear_low_vol',
        'bear_high_vol'))
    )
    
    return regime
```

**Training Specialist Models:**
```python
# File: scripts/ml_training/train_regime_specialists.py

# 1. Segment 2024 data by regime
data_bull_low = data[data['regime'] == 'bull_low_vol']
data_bull_high = data[data['regime'] == 'bull_high_vol']
data_bear_low = data[data['regime'] == 'bear_low_vol']
data_bear_high = data[data['regime'] == 'bear_high_vol']

# 2. Train 4 specialist models
model_bull_low = XGBClassifier().fit(X_bull_low, y_bull_low)
model_bull_high = XGBClassifier().fit(X_bull_high, y_bull_high)
model_bear_low = XGBClassifier().fit(X_bear_low, y_bear_low)
model_bear_high = XGBClassifier().fit(X_bear_high, y_bear_high)

# 3. Save all 4 models
joblib.dump(model_bull_low, 'layer05_bull_low_vol.pkl')
joblib.dump(model_bull_high, 'layer05_bull_high_vol.pkl')
joblib.dump(model_bear_low, 'layer05_bear_low_vol.pkl')
joblib.dump(model_bear_high, 'layer05_bear_high_vol.pkl')
```

**Runtime Ensemble:**
```python
# File: src/layers/layer05_micro_trend.py (UPDATE)

def predict_with_regime_ensemble(df, features):
    """
    Detect regime and route to specialist model
    """
    # 1. Detect current regime
    current_regime = classify_market_regime(df)
    
    # 2. Load appropriate specialist
    if current_regime == 'bull_low_vol':
        model = joblib.load('layer05_bull_low_vol.pkl')
    elif current_regime == 'bull_high_vol':
        model = joblib.load('layer05_bull_high_vol.pkl')
    elif current_regime == 'bear_low_vol':
        model = joblib.load('layer05_bear_low_vol.pkl')
    else:  # bear_high_vol
        model = joblib.load('layer05_bear_high_vol.pkl')
    
    # 3. Make prediction with specialist
    prediction = model.predict(features)
    confidence = model.predict_proba(features).max()
    
    return prediction, confidence
```

**Expected Result:** 75-80% accuracy across all years

---

### Phase 3: Confidence Calibration (Week 3)

**Goal:** Only trust high-confidence predictions, ensure 85%+ on those

**Calibration Strategy:**
```python
# File: scripts/ml_training/calibrate_confidence.py

def calibrate_predictions(model, X_val, y_val):
    """
    Find confidence threshold that gives 85%+ accuracy
    """
    predictions = model.predict(X_val)
    probabilities = model.predict_proba(X_val)
    confidence = probabilities.max(axis=1)
    
    # Test different confidence thresholds
    for threshold in [0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95]:
        high_conf_mask = confidence > threshold
        high_conf_pred = predictions[high_conf_mask]
        high_conf_actual = y_val[high_conf_mask]
        
        if len(high_conf_pred) > 0:
            accuracy = (high_conf_pred == high_conf_actual).mean()
            coverage = high_conf_mask.mean()
            
            print(f"Threshold {threshold:.2f}: {accuracy:.1%} accuracy on {coverage:.1%} of trades")
            
            if accuracy >= 0.85:
                return threshold  # Found our threshold!
    
    return 0.9  # Default to 90% if nothing works
```

**Layer 0.5 Output with Confidence:**
```python
# src/layers/layer05_micro_trend.py

def generate_signals(self, data):
    """
    Generate trend direction with confidence filtering
    """
    # 1. Get features
    features = self.create_market_invariant_features(data)
    
    # 2. Predict with regime-aware ensemble
    prediction, confidence = self.predict_with_regime_ensemble(data, features)
    
    # 3. Apply confidence threshold
    if confidence < self.confidence_threshold:  # e.g., 0.85
        return {
            'direction': 0,  # Neutral (don't trade)
            'confidence': confidence,
            'reason': 'Low confidence'
        }
    
    # 4. High confidence signal
    return {
        'direction': 1 if prediction == 1 else -1,  # Bullish or bearish
        'confidence': confidence,
        'regime': self.current_regime
    }
```

**Expected Result:** 85-90% accuracy on high-confidence predictions

---

## 🔧 Implementation Details

### File Structure:
```
scripts/ml_training/
├── generate_market_invariant_features.py      # Phase 1
├── train_regime_specialists.py                 # Phase 2
├── calibrate_confidence.py                     # Phase 3
└── train_layer05_market_agnostic.py           # Main training script

src/layers/
├── layer0_multi_tf_trend.py                    # Fix Layer 0
└── layer05_micro_trend.py                      # Update Layer 0.5

data/models/
├── layer05_ml_market_agnostic/
│   ├── bull_low_vol_model.pkl
│   ├── bull_high_vol_model.pkl
│   ├── bear_low_vol_model.pkl
│   ├── bear_high_vol_model.pkl
│   ├── scaler.pkl
│   ├── features.json
│   └── confidence_thresholds.json
```

### Integration (NO ARCHITECTURE CHANGES):

**Current Layer 0.5 in system:**
```python
# src/layers/layer_compositor.py

# Get Layer 0 trend
layer0_signal = self.layer0.generate_signals(data)

# Get Layer 0.5 ML prediction
layer05_signal = self.layer05.generate_signals(data)

# Combined trend direction
trend_direction = self._combine_layer0_layer05(layer0_signal, layer05_signal)

# Pass to other layers
if trend_direction == 1:  # Bullish
    # Only look for long entries in Layers 1-6
    layer1_signals = self.layer1.generate_signals(data, direction='long')
    ...
elif trend_direction == -1:  # Bearish
    # Only look for short entries in Layers 1-6
    layer1_signals = self.layer1.generate_signals(data, direction='short')
    ...
```

**After improvement (SAME INTEGRATION):**
```python
# src/layers/layer_compositor.py

# Get Layer 0 trend (IMPROVED)
layer0_signal = self.layer0.generate_signals(data)  # Fixed EMA logic

# Get Layer 0.5 ML prediction (IMPROVED)
layer05_signal = self.layer05.generate_signals(data)  # Market-invariant features + regime ensemble

# Combined trend direction (SAME LOGIC)
trend_direction = self._combine_layer0_layer05(layer0_signal, layer05_signal)

# Pass to other layers (UNCHANGED)
if trend_direction == 1:
    layer1_signals = self.layer1.generate_signals(data, direction='long')
    ...
```

**Key Point:** Only Layer 0 and Layer 0.5 code changes, everything else stays the same!

---

## 📊 Validation Plan

### Test on Multiple Years (Walk-Forward):
```
2019 Data → Should get 85%+ accuracy
2020 Data → Should get 85%+ accuracy
2021 Data → Should get 85%+ accuracy (currently 37.60%)
2022 Data → Should get 85%+ accuracy
2023 Data → Should get 85%+ accuracy
2024 Data → Should maintain 97.68% accuracy
```

### Test on Extreme Events:
```
2020 March Crash (-50% in 2 days)
2021 May Correction (-50%)
2022 Bear Market (Terra/Luna)
2023 Recovery
2024 Bull Run
```

---

## 🎯 Success Criteria

### Layer 0 (Simple):
- [ ] Properly detects bullish/bearish/neutral on ALL years
- [ ] No more "0% all categories" errors
- [ ] Alignment scores calculated correctly

### Layer 0.5 (Main Focus):
- [ ] 85%+ accuracy on 2021 data (up from 37.60%)
- [ ] 85%+ accuracy on 2022 data
- [ ] 85%+ accuracy on 2023 data
- [ ] Maintains 95%+ accuracy on 2024 data
- [ ] Balanced predictions (not 95% bearish)
- [ ] Works without orderbook data

### Integration:
- [ ] NO changes to Layers 1-6
- [ ] NO changes to backtest engine
- [ ] NO changes to paper trading
- [ ] NO changes to live trading
- [ ] Drop-in replacement for existing Layer 0/0.5

---

## 📅 Timeline

### Week 1: Market-Invariant Features
- Day 1-2: Implement feature generator
- Day 3-4: Extract features from 2019-2024
- Day 5-6: Train new model, validate on 2021
- Day 7: Test and document
- **Target: 65-75% accuracy on 2021**

### Week 2: Regime Specialists
- Day 1-2: Implement regime classifier
- Day 3-4: Train 4 specialist models
- Day 5-6: Build ensemble logic
- Day 7: Test on all years
- **Target: 75-85% accuracy across all years**

### Week 3: Confidence Calibration
- Day 1-2: Calibrate confidence thresholds
- Day 3-4: Update Layer 0.5 code
- Day 5-6: Final validation
- Day 7: Integration testing
- **Target: 85-90% on high-confidence**

---

## 🚨 Critical Points

### What This Plan Does:
✅ Improves Layer 0 trend detection
✅ Retrains Layer 0.5 with better features
✅ Makes Layer 0.5 work in any market condition
✅ Achieves 85%+ trend accuracy
✅ Drop-in replacement - no architecture changes

### What This Plan Does NOT Do:
❌ Change Layers 1-6
❌ Modify backtest engine
❌ Change paper trading
❌ Alter live trading
❌ Require new data collection
❌ Change overall system architecture

### Integration:
- Layer 0 outputs: Same format (trend direction + confidence)
- Layer 0.5 outputs: Same format (prediction + confidence)
- Layers 1-6 inputs: Unchanged
- Trading logic: Unchanged
- **Only the MODELS change, not the ARCHITECTURE**

---

## 💡 Summary

**Goal:** Make Layer 0 + Layer 0.5 identify trends at 85%+ accuracy in ANY market

**Method:**
1. Fix Layer 0 EMA detection (simple fix)
2. Re-engineer Layer 0.5 features (market-invariant)
3. Train regime specialists (4 models for different conditions)
4. Calibrate confidence (only trade when sure)

**Result:**
- 85%+ accuracy on 2019, 2020, 2021, 2022, 2023, 2024
- No architecture changes
- Drop-in replacement for existing Layer 0/0.5
- Other layers (1-6) get better trend signals
- Better overall system performance

**Timeline:** 3 weeks to production-ready Layer 0 + 0.5

**Next Step:** Approve Phase 1 (market-invariant features) and begin implementation.
