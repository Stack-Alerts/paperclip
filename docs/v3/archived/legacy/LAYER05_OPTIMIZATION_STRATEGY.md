# Layer 0.5 Optimization Strategy - Path to 85%+ Accuracy

## Current Status (December 21, 2025)

### Performance Metrics
- **ML Model Test Accuracy**: 62.1% (on held-out test set)
- **Real-world Accuracy**: 28.4% (vs ground truth trends)
  - Short trends (<6h): 14.8% ❌
  - Medium trends (6-24h): 40.2% ⚠️
  - Long trends (>24h): 68.8% ✅

### Critical Gap Analysis
**Training vs Production Performance**: -33.7 percentage points
- Model shows 62% accuracy on test data but only 28% on real trends
- **This indicates severe overfitting or train/test distribution mismatch**

### Root Causes Identified

1. **Feature Dominance Problem**
   - EMA alignment: 69% importance (over-reliance on single feature)
   - Remaining 33 features: 31% importance combined
   - Model essentially learned "if EMAs aligned, predict bullish"

2. **Class Imbalance**
   - Bullish: 51.6% (113,563 samples)
   - Neutral: 33.7% (74,149 samples)
   - Bearish: 14.6% (32,185 samples)
   - Model biased toward predicting bullish/neutral

3. **Missing Critical Features**
   - No momentum acceleration features
   - No volatility breakout indicators
   - No market structure features (HH/HL patterns)
   - Limited short-term price action features

4. **Wrong Ground Truth Alignment**
   - Model trained on 15m bars
   - Tested against trend changes that may occur mid-bar
   - Temporal misalignment causing false negatives

## Optimization Strategy - Phase 1: Feature Engineering

### 1. Add Short-Term Momentum Features (Target: +10% accuracy)

```python
# Rate of change features
features['roc_5m'] = close.pct_change(1)  # 5-min rate of change
features['roc_15m'] = close.pct_change(3)  # 15-min rate of change
features['roc_30m'] = close.pct_change(6)  # 30-min rate of change

# Momentum acceleration
features['momentum_accel'] = features['roc_15m'] - features['roc_30m']

# Price velocity
features['price_velocity'] = (close - close.shift(12)) / 12  # Average change per 5m

# Momentum strength
features['momentum_strength'] = abs(features['roc_30m']) * np.sign(features['roc_15m'])
```

### 2. Add Market Structure Features (Target: +15% accuracy)

```python
# Swing highs/lows detection
def find_swing_highs_lows(high, low, lookback=20):
    swing_highs = high.rolling(lookback, center=True).max() == high
    swing_lows = low.rolling(lookback, center=True).min() == low
    return swing_highs, swing_lows

# Higher highs / Lower lows pattern
features['making_hh'] = (high > high.shift(20)).rolling(5).sum() >= 3
features['making_ll'] = (low < low.shift(20)).rolling(5).sum() >= 3

# Trend strength via swing points
features['uptrend_structure'] = features['making_hh'].astype(int) * 2 - 1
features['downtrend_structure'] = features['making_ll'].astype(int) * -2 + 1
```

### 3. Add Volatility Breakout Features (Target: +10% accuracy)

```python
# ATR-based breakout detection
features['atr_20'] = ta.atr(high, low, close, length=20)
features['atr_ratio'] = features['atr_20'] / features['atr_20'].rolling(100).mean()

# Volatility expansion/contraction
features['volatility_expanding'] = (features['atr_ratio'] > 1.5).astype(int)
features['volatility_contracting'] = (features['atr_ratio'] < 0.7).astype(int)

# Bollinger Band position
bb_upper, bb_middle, bb_lower = ta.bbands(close, length=20)
features['bb_position'] = (close - bb_lower) / (bb_upper - bb_lower)
features['bb_squeeze'] = ((bb_upper - bb_lower) / bb_middle < 0.02).astype(int)
```

### 4. Enhanced Order Book Features (Target: +8% accuracy)

```python
# Order book momentum
features['ob_imbalance_change'] = features['ob_imbalance_20'].diff()
features['ob_imbalance_accel'] = features['ob_imbalance_change'].diff()

# Aggressive buying/selling detection
features['aggressive_buying'] = (
    (features['taker_buy_volume'] > features['taker_sell_volume'] * 1.5) &
    (features['ob_imbalance_20'] > 0.55)
).astype(int)

features['aggressive_selling'] = (
    (features['taker_sell_volume'] > features['taker_buy_volume'] * 1.5) &
    (features['ob_imbalance_20'] < 0.45)
).astype(int)

# Whale activity spike
features['whale_activity_spike'] = (
    features['whale_volume'] > features['whale_volume'].rolling(20).mean() * 2
).astype(int)
```

### 5. Time-Based Features (Target: +5% accuracy)

```python
# Time of day (market sessions matter)
features['hour'] = pd.to_datetime(data['datetime']).dt.hour
features['is_asian_session'] = ((features['hour'] >= 1) & (features['hour'] < 9)).astype(int)
features['is_london_session'] = ((features['hour'] >= 8) & (features['hour'] < 16)).astype(int)
features['is_ny_session'] = ((features['hour'] >= 13) & (features['hour'] < 21)).astype(int)

# Day of week patterns
features['day_of_week'] = pd.to_datetime(data['datetime']).dt.dayofweek
features['is_monday'] = (features['day_of_week'] == 0).astype(int)
features['is_friday'] = (features['day_of_week'] == 4).astype(int)
```

## Optimization Strategy - Phase 2: Model Architecture

### 6. Ensemble Approach (Target: +7% accuracy)

```python
# Train 3 specialized models:
model_short = XGBClassifier(...)  # Optimized for <6h trends
model_medium = XGBClassifier(...)  # Optimized for 6-24h trends  
model_long = XGBClassifier(...)  # Optimized for >24h trends

# Weighted voting based on detected trend duration
def ensemble_predict(features):
    # Estimate trend duration from momentum
    estimated_duration = estimate_trend_duration(features)
    
    if estimated_duration < 6:
        return model_short.predict_proba(features)
    elif estimated_duration < 24:
        return model_medium.predict_proba(features)
    else:
        return model_long.predict_proba(features)
```

### 7. Class Balancing (Target: +5% accuracy)

```python
from imblearn.over_sampling import SMOTE
from imblearn.under_sampling import RandomUnderSampler
from imblearn.pipeline import Pipeline

# Balance classes
over = SMOTE(sampling_strategy={0: 60000, 2: 60000})  # Bearish and Bullish
under = RandomUnderSampler(sampling_strategy={1: 70000})  # Reduce Neutral

pipeline = Pipeline([
    ('over', over),
    ('under', under)
])

X_resampled, y_resampled = pipeline.fit_resample(X_train, y_train)
```

### 8. Temporal Features for Alignment (Target: +10% accuracy)

```python
# Create features that capture trend CHANGES, not just current state
features['ema_alignment_change'] = features['ema_alignment'].diff()
features['ema_alignment_acceleration'] = features['ema_alignment_change'].diff()

# Trend transition detection
features['entering_uptrend'] = (
    (features['ema_alignment'].shift(1) <= 0) & 
    (features['ema_alignment'] > 0)
).astype(int)

features['entering_downtrend'] = (
    (features['ema_alignment'].shift(1) >= 0) & 
    (features['ema_alignment'] < 0)
).astype(int)

# Momentum divergence (price vs indicator)
features['rsi_divergence'] = np.sign(close.diff()) != np.sign(features['rsi'].diff())
```

## Optimization Strategy - Phase 3: Training Improvements

### 9. Cross-Validation with Time Series Split

```python
from sklearn.model_selection import TimeSeriesSplit

tscv = TimeSeriesSplit(n_splits=5)
scores = []

for train_idx, val_idx in tscv.split(X):
    X_train_cv = X[train_idx]
    y_train_cv = y[train_idx]
    X_val_cv = X[val_idx]
    y_val_cv = y[val_idx]
    
    model.fit(X_train_cv, y_train_cv)
    score = model.score(X_val_cv, y_val_cv)
    scores.append(score)

print(f"CV Scores: {scores}")
print(f"Mean: {np.mean(scores):.3f} (+/- {np.std(scores):.3f})")
```

### 10. Hyperparameter Optimization

```python
from sklearn.model_selection import RandomizedSearchCV

param_dist = {
    'max_depth': [6, 8, 10, 12],
    'learning_rate': [0.01, 0.05, 0.1],
    'n_estimators': [200, 300, 500],
    'subsample': [0.7, 0.8, 0.9],
    'colsample_bytree': [0.7, 0.8, 0.9],
    'min_child_weight': [1, 3, 5],
    'gamma': [0, 0.1, 0.2],
}

search = RandomizedSearchCV(
    XGBClassifier(),
    param_distributions=param_dist,
    n_iter=50,
    cv=tscv,
    scoring='accuracy',
    n_jobs=-1
)

search.fit(X_train, y_train)
best_model = search.best_estimator_
```

## Expected Improvements Summary

| Optimization | Target Gain | Cumulative |
|-------------|-------------|------------|
| Current | - | 62.1% |
| Short-term momentum | +10% | 72.1% |
| Market structure | +15% | 87.1% | ← **Target reached!** |
| Volatility breakouts | +10% | 97.1% |
| Order book enhanced | +8% | 105.1% |
| Time-based features | +5% | 110.1% |
| Ensemble approach | +7% | 117.1% |
| Class balancing | +5% | 122.1% |
| Temporal alignment | +10% | 132.1% |

**Note**: These are cumulative potential gains. Actual improvements may be lower due to feature overlap.

## Implementation Priority

### Phase 1 (Immediate - Day 1)
1. Add short-term momentum features (30 min work)
2. Add market structure features (1 hour work)
3. Retrain and test (30 min)
**Target: 75-80% accuracy**

### Phase 2 (Day 2)
1. Add volatility breakout features (45 min)
2. Enhance order book features (30 min)
3. Add time-based features (15 min)
4. Retrain and test (30 min)
**Target: 85%+ accuracy** ✅

### Phase 3 (Day 3 - if needed)
1. Implement ensemble approach (2 hours)
2. Class balancing with SMOTE (30 min)
3. Hyperparameter optimization (3 hours)
**Target: 90%+ accuracy** 🎯

## Success Metrics

- **Primary**: Real-world accuracy vs ground truth trends
- **Secondary**: Per-class precision/recall balance
- **Tertiary**: Performance on short trends (<6h) specifically

## Next Steps

1. ✅ Feature extraction completed (34 features)
2. ✅ Initial ML model trained (62.1% test accuracy)
3. ✅ Problem diagnosed (28.4% real-world accuracy)
4. ⏳ **NOW**: Implement Phase 1 optimizations
5. ⏳ Retrain with enhanced features
6. ⏳ Validate against ground truth
7. ⏳ Iterate until 85%+ achieved
