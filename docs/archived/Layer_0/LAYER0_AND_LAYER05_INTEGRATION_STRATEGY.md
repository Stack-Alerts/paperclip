# Layer 0 & Layer 0.5 Integration Strategy with Complete Dataset

## System Overview

### Layer Hierarchy (Complete Picture)

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 0: Multi-TF Trend Foundation (4H/2H/1H)             │
│  Role: Macro trend direction - LONG_ONLY/SHORT_ONLY/NONE   │
│  Current: Rule-based with 44% accuracy on 6-24h trends     │
└────────────────────┬────────────────────────────────────────┘
                     │ Directional Bias
┌────────────────────▼────────────────────────────────────────┐
│  LAYER 0.5: Micro-Trend Detection (1H/30M/15M)             │
│  Role: Scalping opportunities (6-24 hour trends)            │
│  Current: Rule-based 53% accuracy                           │
│  Target: ML-enhanced 75-80% accuracy ← WE ARE HERE         │
└────────────────────┬────────────────────────────────────────┘
                     │ Trend-Aligned Opportunities
┌────────────────────▼────────────────────────────────────────┐
│  LAYERS 1-6: Signal Generation & Filtering                 │
│  - Layer 1: Traditional TA signals                          │
│  - Layer 2: Volume Delta                                    │
│  - Layer 3: Weis Wave                                       │
│  - Layer 4: XGBoost ML                                      │
│  - Layer 5: CNN-LSTM DL                                     │
│  - Layer 6: TradingView Alerts                             │
└────────────────────┬────────────────────────────────────────┘
                     │ High-Quality Signals
┌────────────────────▼────────────────────────────────────────┐
│  COMPOSITOR: Weighted Signal Aggregation                    │
└────────────────────┬────────────────────────────────────────┘
                     │ Final Decision
┌────────────────────▼────────────────────────────────────────┐
│  RISK MANAGER → ORDER EXECUTION                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Current Status

### What We Have

**Downloaded Dataset (41.9 GB):**
- ✅ 24 months order book data (33 GB)
  - ~400 million snapshots
  - 20 levels deep (bid/ask)
  - Jan 2024 - Dec 2025
  
- ✅ 24 months trade data (8.9 GB)
  - ~950 million individual trades
  - Side, price, quantity, timestamps
  - Jan 2024 - Dec 2025

**Existing Systems:**
- ✅ Layer 0: Multi-TF trend (4H/2H/1H) - 44% accuracy
- ✅ Layer 0.5: Micro-trend (1H/30M/15M) - 53% accuracy (rule-based)
- ✅ Layers 1-6: Signal generation layers
- ✅ 15m ground truth: 6,801 validated trends

### What We Need to Build

**Layer 0.5 ML Enhancement:**
- [ ] Feature engineering from orderbook + trades
- [ ] Train XGBoost model
- [ ] Achieve 75-80% accuracy
- [ ] Integrate with existing system

---

## Layer 0 vs Layer 0.5: Clear Distinction

### Layer 0: Macro Trend Foundation

**Purpose:** Establish overall market direction
**Timeframes:** 4H (primary), 2H, 1H
**Output:** LONG_ONLY | SHORT_ONLY | NONE
**Method:** Rule-based (EMA, structure, MACD, RSI)
**Accuracy:** 44% on 6-24h trends
**Role:** Blocks counter-trend signals from all layers

**Example:**
```
4H: Strong bullish (score +1.5)
2H: Bullish (score +0.8)
1H: Neutral (score +0.2)
→ Layer 0 Output: LONG_ONLY

Result: All layers (1-6) can ONLY generate LONG signals
```

### Layer 0.5: Micro-Trend Detection

**Purpose:** Find scalping opportunities within macro trend
**Timeframes:** 1H (primary), 30M, 15M
**Output:** LONG | SHORT | NEUTRAL + confidence
**Method:** ML-enhanced (orderbook + trades)
**Current Accuracy:** 53% rule-based
**Target Accuracy:** 75-80% with ML
**Role:** Generates trend-aligned scalp opportunities

**Example:**
```
Layer 0: LONG_ONLY (4H bullish)
Layer 0.5: Analyzes 1H/30M/15M
  - Finds pullback completing
  - Orderbook shows bid pressure
  - Trade flow aggressive buying
→ Layer 0.5 Output: LONG, confidence=0.85

Result: High-quality long entry signal for Layers 1-6 to confirm
```

### Integration Flow

```
1. Layer 0 (Macro): Determines allowed direction
   ↓
2. Layer 0.5 (Micro): Finds opportunities in that direction
   ↓
3. Layers 1-6: Confirm and filter opportunities
   ↓
4. Compositor: Aggregate all signals
   ↓
5. Trade Execution
```

---

## ML Training Strategy for Layer 0.5

### Objective

**Transform Layer 0.5 from 53% → 75-80% accuracy** by incorporating:
- Order book microstructure
- Trade flow analysis
- Machine learning pattern recognition

### Data Preparation

**Input Data:**
- 24 months of 15m OHLCV
- 24 months of order book snapshots
- 24 months of trade ticks

**Resampling:**
```python
# Current 15m data
df_15m = load_ohlcv('15m')

# Resample to 1H (primary timeframe for Layer 0.5)
df_1h = df_15m.resample('1H').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
})

# Resample to 30M
df_30m = df_15m.resample('30M').agg({...})
```

**Ground Truth:**
- Use existing 6,801 validated 15m trends
- Aggregate to 1H level
- Label: 1 = bullish, 0 = bearish, -1 = neutral

### Feature Engineering

#### Category 1: Traditional Technical Indicators (Baseline - 53%)

**From existing Layer 0.5:**
- Fast EMAs (5/13/34)
- Swing structure
- MACD + RSI momentum
- Volume trend

**Keep these as baseline features.**

#### Category 2: Order Book Microstructure (NEW +15-20%)

**Bid/Ask Imbalance:**
```python
def orderbook_imbalance(orderbook, levels=10):
    """
    Calculate bid/ask pressure.
    """
    bids = orderbook['bids'][:levels]
    asks = orderbook['asks'][:levels]
    
    bid_volume = sum([b['size'] for b in bids])
    ask_volume = sum([a['size'] for a in asks])
    
    imbalance = bid_volume / (bid_volume + ask_volume)
    # >0.6 = bullish, <0.4 = bearish
    
    return imbalance
```

**Weighted Mid-Price:**
```python
def weighted_mid(orderbook, levels=10):
    """
    Volume-weighted mid price.
    """
    bid_weighted = sum([b['price'] * b['size'] for b in orderbook['bids'][:levels]])
    ask_weighted = sum([a['price'] * a['size'] for a in orderbook['asks'][:levels]])
    
    bid_volume = sum([b['size'] for b in orderbook['bids'][:levels]])
    ask_volume = sum([a['size'] for a in orderbook['asks'][:levels]])
    
    return (bid_weighted / bid_volume + ask_weighted / ask_volume) / 2
```

**Spread Metrics:**
```python
def spread_analysis(orderbook):
    """
    Analyze bid-ask spread.
    """
    best_bid = orderbook['bids'][0]['price']
    best_ask = orderbook['asks'][0]['price']
    
    spread = best_ask - best_bid
    spread_pct = spread / best_bid
    
    # Also: spread at levels 5, 10
    
    return spread, spread_pct
```

**Order Book Depth:**
```python
def depth_metrics(orderbook, levels=[5, 10, 20]):
    """
    Liquidity at different levels.
    """
    features = {}
    
    for level in levels:
        bid_depth = sum([b['size'] for b in orderbook['bids'][:level]])
        ask_depth = sum([a['size'] for a in orderbook['asks'][:level]])
        
        features[f'bid_depth_{level}'] = bid_depth
        features[f'ask_depth_{level}'] = ask_depth
        features[f'depth_ratio_{level}'] = bid_depth / ask_depth
    
    return features
```

#### Category 3: Trade Flow Analysis (NEW +5-10%)

**Taker Buy/Sell Ratio:**
```python
def taker_flow(trades, window='1H'):
    """
    Aggressive buyer vs seller ratio.
    """
    # Aggregate trades in window
    buys = trades[trades['side'] == 'buy']
    sells = trades[trades['side'] == 'sell']
    
    buy_volume = buys['quantity'].sum()
    sell_volume = sells['quantity'].sum()
    
    ratio = buy_volume / sell_volume
    # >1.2 = bullish, <0.8 = bearish
    
    return ratio, buy_volume, sell_volume
```

**Trade Size Distribution:**
```python
def trade_size_analysis(trades):
    """
    Large vs small trade analysis.
    """
    # Separate retail (< $10k) vs whale (> $100k)
    retail = trades[trades['quantity'] * trades['price'] < 10000]
    whale = trades[trades['quantity'] * trades['price'] > 100000]
    
    retail_volume = retail['quantity'].sum()
    whale_volume = whale['quantity'].sum()
    
    # Whales buying = bullish signal
    whale_buys = whale[whale['side'] == 'buy']['quantity'].sum()
    whale_sells = whale[whale['side'] == 'sell']['quantity'].sum()
    
    return {
        'whale_ratio': whale_volume / retail_volume,
        'whale_buy_pressure': whale_buys / (whale_buys + whale_sells)
    }
```

**Trade Frequency:**
```python
def trade_frequency(trades, window='1H'):
    """
    Number of trades per minute.
    """
    trades_per_min = len(trades) / 60
    
    # Also: acceleration (change in frequency)
    
    return trades_per_min
```

**Cumulative Volume Delta (CVD):**
```python
def calculate_cvd(trades):
    """
    Net buying/selling pressure.
    """
    cvd = 0
    cvd_series = []
    
    for trade in trades:
        if trade['side'] == 'buy':
            cvd += trade['quantity']
        else:
            cvd -= trade['quantity']
        
        cvd_series.append(cvd)
    
    # Look for divergences with price
    price_trend = trades['price'].iloc[-1] > trades['price'].iloc[0]
    cvd_trend = cvd_series[-1] > cvd_series[0]
    
    divergence = (price_trend != cvd_trend)
    
    return cvd, divergence
```

### Complete Feature Set

**Total Features: ~40-50**

1. **Traditional (15 features):**
   - EMA 5/13/34 alignment
   - Swing structure
   - MACD, RSI
   - Volume metrics
   - Price action (returns, volatility)

2. **Order Book (15-20 features):**
   - Bid/ask imbalance (levels 5, 10, 20)
   - Weighted mid-price
   - Spread (absolute, %, at levels)
   - Depth ratios
   - Order book slope

3. **Trade Flow (10-15 features):**
   - Taker buy/sell ratio
   - Whale vs retail activity
   - Trade frequency
   - CVD and divergences
   - Large trade tracking

### Model Architecture

**XGBoost Gradient Boosting:**

```python
from xgboost import XGBClassifier

model = XGBClassifier(
    n_estimators=300,  # More trees for complex patterns
    max_depth=8,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    objective='multi:softmax',  # 3 classes: bullish, bearish, neutral
    num_class=3,
    eval_metric='mlogloss',
    use_label_encoder=False,
    random_state=42
)
```

**Why XGBoost:**
- ✅ Handles mixed feature types well
- ✅ Feature importance analysis
- ✅ Fast training and prediction
- ✅ Robust to outliers
- ✅ No need for GPU

### Training Process

**1. Data Split:**
```python
# Chronological split (important for time series!)
train_end = '2024-10-31'
val_start = '2024-11-01'
val_end = '2024-12-31'
test_start = '2025-01-01'

X_train, y_train = data[data['date'] <= train_end]
X_val, y_val = data[(data['date'] > val_start) & (data['date'] <= val_end)]
X_test, y_test = data[data['date'] > test_start]
```

**2. Feature Scaling:**
```python
from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_val_scaled = scaler.transform(X_val)
X_test_scaled = scaler.transform(X_test)
```

**3. Training:**
```python
model.fit(
    X_train_scaled, y_train,
    eval_set=[(X_val_scaled, y_val)],
    early_stopping_rounds=20,
    verbose=10
)
```

**4. Evaluation:**
```python
from sklearn.metrics import classification_report, confusion_matrix

y_pred = model.predict(X_test_scaled)
print(classification_report(y_test, y_pred))

# Feature importance
import matplotlib.pyplot as plt
from xgboost import plot_importance

plot_importance(model, max_num_features=20)
plt.show()
```

### Expected Results

**Baseline (current rule-based):** 53% accuracy

**With complete features:**
- Order book only: 68-72%
- Order book + trades: 75-80% ⭐
- Best case: 80-85%

**Improvement breakdown:**
- Traditional indicators: 53% (baseline)
- + Order book microstructure: +15-20%
- + Trade flow analysis: +5-10%
- **Total: 75-80%**

---

## Integration with Existing System

### Layer 0.5 Enhanced Architecture

```python
class Layer05MicroTrendML(Layer05MicroTrend):
    """
    Enhanced Layer 0.5 with ML.
    
    Combines rule-based analysis with ML predictions.
    """
    
    def __init__(self, config, model_path):
        super().__init__(config)
        self.ml_model = load_ml_model(model_path)
        self.scaler = load_scaler(model_path)
    
    def generate_signal(self, data, current_price, current_position=None):
        # 1. Generate rule-based signal (baseline)
        rule_signal = super().generate_signal(data, current_price)
        
        # 2. Extract ML features
        features = self._extract_ml_features(data)
        
        # 3. Get ML prediction
        ml_prediction, ml_confidence = self._predict_ml(features)
        
        # 4. Combine rule-based + ML
        final_signal = self._combine_signals(rule_signal, ml_prediction, ml_confidence)
        
        return final_signal
    
    def _extract_ml_features(self, data):
        """Extract all features: traditional + orderbook + trades."""
        features = {}
        
        # Traditional
        features.update(self._traditional_features(data))
        
        # Order book
        if self.orderbook_data:
            features.update(self._orderbook_features(data))
        
        # Trade flow
        if self.trade_data:
            features.update(self._trade_features(data))
        
        return features
    
    def _combine_signals(self, rule_signal, ml_prediction, ml_confidence):
        """
        Combine rule-based and ML signals.
        
        Strategy:
        - ML confidence > 0.7: Use ML (70% weight)
        - ML confidence 0.5-0.7: Average of both
        - ML confidence < 0.5: Use rules (70% weight)
        """
        if ml_confidence > 0.7:
            # Trust ML
            return LayerSignal(
                direction=ml_prediction,
                confidence=ml_confidence,
                strength=ml_confidence,
                metadata={'source': 'ml', 'ml_confidence': ml_confidence}
            )
        elif ml_confidence > 0.5:
            # Average
            if rule_signal.direction == ml_prediction:
                # Agreement
                combined_confidence = (rule_signal.confidence + ml_confidence) / 2
                return LayerSignal(
                    direction=ml_prediction,
                    confidence=combined_confidence,
                    strength=combined_confidence,
                    metadata={'source': 'combined', 'agreement': True}
                )
            else:
                # Conflict - reduce confidence
                return LayerSignal(
                    direction='neutral',
                    confidence=0.3,
                    strength=0.3,
                    metadata={'source': 'combined', 'conflict': True}
                )
        else:
            # Trust rules
            return rule_signal
```

### Fallback Strategy

**If orderbook/trade data unavailable:**
- Fall back to rule-based Layer 0.5
- System remains functional
- Graceful degradation

**If ML model fails:**
- Use rule-based baseline
- Log error
- Alert for investigation

---

## Implementation Plan

### Phase 1: Feature Engineering (1-2 days)

1. Create `feature_engineering.py`
   - Load orderbook data
   - Load trade data
   - Extract all features
   - Align with 15m/1H ground truth

2. Create feature extraction functions
   - Order book features
   - Trade flow features
   - Combine with traditional features

3. Save feature matrix
   - CSV or parquet format
   - Ready for training

### Phase 2: Model Training (1 day)

1. Create `train_layer05_ml.py`
   - Load feature matrix
   - Split train/val/test
   - Train XGBoost
   - Evaluate metrics
   - Save model

2. Feature importance analysis
   - Identify top features
   - Remove low-importance features
   - Retrain if needed

3. Model validation
   - Test on holdout set
   - Calculate accuracy, precision, recall
   - Confusion matrix analysis

### Phase 3: Integration (1 day)

1. Create `layer05_ml.py`
   - Extend existing Layer05MicroTrend
   - Add ML prediction
   - Combine signals

2. Update config
   - Add ML model path
   - Add feature configs

3. System testing
   - Run backtest with ML Layer 0.5
   - Compare vs rule-based
   - Verify improvement

### Phase 4: Production (1 day)

1. Production deployment
   - Save model artifacts
   - Update documentation
   - Create monitoring

2. Performance tracking
   - Log ML predictions
   - Track accuracy over time
   - Alert on degradation

---

## Success Metrics

### Target Metrics

**Accuracy:**
- Overall: 75-80%
- Bullish signals: 75%+
- Bearish signals: 75%+
- Neutral (avoid): 80%+

**Precision:**
- When model says LONG: 80%+ are profitable trends
- When model says SHORT: 80%+ are profitable trends

**Recall:**
- Catch 70%+ of actual bullish trends
- Catch 70%+ of actual bearish trends

**Integration Metrics:**
- System-wide win rate: Improve from 40% → 60%+
- Sharpe ratio: Improve by 50%+
- Drawdown: Reduce by 30%+

---

## Conclusion

**This strategy transforms Layer 0.5 from rule-based (53%) to ML-enhanced (75-80%) by leveraging:**

1. ✅ Complete institutional dataset (orderbook + trades)
2. ✅ Advanced feature engineering
3. ✅ Proven ML architecture (XGBoost)
4. ✅ Seamless integration with existing system
5. ✅ Fallback to rules if ML unavailable

**Result:** A production-ready Layer 0.5 that provides high-quality scalping opportunities aligned with Layer 0's macro trend direction.

**Next Step:** Implement Phase 1 (Feature Engineering)
