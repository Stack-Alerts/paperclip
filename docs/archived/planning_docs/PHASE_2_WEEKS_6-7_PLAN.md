# Phase 2 Weeks 6-7: XGBoost Ensemble (Layer 4) - PLAN

**Start Date:** December 16, 2025  
**Target Completion:** 2-3 days  
**Status:** Planning

## Overview

Implement Layer 4: XGBoost Machine Learning Ensemble to predict price direction using features from Layers 1-3 and technical indicators. This layer provides ML-based probability estimates for bullish/bearish moves.

## Objectives

### Primary Goals
1. Comprehensive feature engineering (40+ features)
2. XGBoost classifier implementation
3. Walk-forward validation for robustness
4. Model persistence and versioning
5. Probability calibration
6. Feature importance tracking
7. Model retraining pipeline

### Expected Performance Impact
- **Win Rate:** +2-5% (cumulative: 65-70%)
- **Model Accuracy:** 55-65% on test data
- **Feature Importance Stability:** >80%
- **Prediction Latency:** <50ms

## Technical Specifications

### 1. Feature Engineering Strategy

**Price Action Features (10):**
- Returns: 1, 2, 5, 10, 20 periods
- Price position in range
- Distance from EMAs
- Volatility measures
- ATR normalized

**Technical Indicator Features (15):**
- RSI, MACD, ADX values
- Bollinger Band position
- EMA relationships (9/20, 20/50, 50/200)
- Volume ratios
- Momentum indicators

**Layer Signals (10):**
- Layer 1 score and confidence
- Layer 2 CVD and divergence signals
- Layer 3 accumulation/distribution confidence
- Wave exhaustion signals
- Composite scores

**Time Features (5):**
- Hour of day
- Day of week
- Market session (Asian/London/US)
- Weekend proximity
- Trading hour category

**Lag Features (10):**
- Lagged returns (1, 2, 3, 5, 10 periods)
- Lagged volume
- Lagged indicator values

**Target:**
- Binary: Will price be higher in N periods? (configurable)
- Multi-class option: Up, Down, Neutral

### 2. Layer 4 Architecture

```python
class Layer4XGBoost(BaseLayer):
    """
    XGBoost ML Ensemble Layer
    
    Uses gradient boosting to predict price direction
    based on comprehensive feature set.
    """
    
    def __init__(
        self,
        model_path: str = "data/models/xgboost/",
        n_estimators: int = 200,
        max_depth: int = 6,
        learning_rate: float = 0.05,
        prediction_horizon: int = 5  # bars ahead
    ):
        pass
    
    # Core Methods
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame
    def train_model(self, df: pd.DataFrame, validation_split: float = 0.2)
    def train_walk_forward(self, df: pd.DataFrame, n_splits: int = 5)
    def predict(self, df: pd.DataFrame) -> Dict
    def predict_proba(self, df: pd.DataFrame) -> np.ndarray
    
    # Utilities
    def save_model(self, version: str = None)
    def load_model(self, version: str = None)
    def get_feature_importance(self) -> pd.DataFrame
    def calibrate_probabilities(self, X_val, y_val)
    def evaluate_model(self, X_test, y_test) -> Dict
```

### 3. Walk-Forward Validation

**Purpose:** Ensure model generalizes to unseen data

**Process:**
1. Split data into N folds (time-ordered)
2. Train on fold 1-k, validate on fold k+1
3. Advance window and repeat
4. Select best model based on validation scores
5. Track performance across folds

**Metrics to Track:**
- Accuracy
- Precision/Recall
- F1 Score
- ROC-AUC
- Profit factor (if backtest integrated)
- Sharpe ratio of signals

### 4. Feature Importance Analysis

**Methods:**
- Built-in XGBoost importance (gain, weight, cover)
- SHAP values for interpretability
- Permutation importance
- Feature correlation analysis

**Monitoring:**
- Track importance changes over time
- Alert if top features shift dramatically
- Remove low-importance features
- Validate feature stability

## Implementation Plan

### Phase 1: Feature Engineering (~200 lines)

```python
def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
    """
    Create comprehensive feature set.
    
    Returns DataFrame with:
    - 40+ engineered features
    - Target variable
    - No NaN values (forward fill or drop)
    """
    features = pd.DataFrame(index=df.index)
    
    # 1. Price action features
    features['returns_1'] = df['close'].pct_change(1)
    features['returns_5'] = df['close'].pct_change(5)
    # ... more returns
    
    # 2. Technical indicators
    features['rsi'] = df['rsi']
    features['macd_diff'] = df['macd'] - df['macd_signal']
    # ... more indicators
    
    # 3. Layer signals (if available)
    # Integrate Layer 1, 2, 3 scores
    
    # 4. Time features
    features['hour'] = df.index.hour
    features['day_of_week'] = df.index.dayofweek
    
    # 5. Lag features
    for lag in [1, 2, 3, 5, 10]:
        features[f'returns_lag_{lag}'] = features['returns_1'].shift(lag)
    
    # 6. Target
    features['target'] = (
        df['close'].shift(-self.prediction_horizon) > df['close']
    ).astype(int)
    
    return features.dropna()
```

### Phase 2: Training Pipeline (~200 lines)

```python
def train_walk_forward(
    self,
    df: pd.DataFrame,
    n_splits: int = 5
) -> Dict:
    """
    Train using walk-forward validation.
    
    Returns:
        Dictionary with:
        - best_model
        - validation_scores
        - feature_importance
        - fold_results
    """
    from sklearn.model_selection import TimeSeriesSplit
    
    # Create features
    features = self.create_features(df)
    X = features.drop(['target'], axis=1)
    y = features['target']
    
    # Time series cross-validation
    tscv = TimeSeriesSplit(n_splits=n_splits)
    
    fold_results = []
    models = []
    
    for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_val_scaled = scaler.transform(X_val)
        
        # Train XGBoost
        model = xgb.XGBClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            random_state=42,
            eval_metric='logloss'
        )
        
        model.fit(
            X_train_scaled, y_train,
            eval_set=[(X_val_scaled, y_val)],
            early_stopping_rounds=20,
            verbose=False
        )
        
        # Evaluate
        y_pred = model.predict(X_val_scaled)
        y_proba = model.predict_proba(X_val_scaled)[:, 1]
        
        fold_score = {
            'fold': fold,
            'accuracy': accuracy_score(y_val, y_pred),
            'precision': precision_score(y_val, y_pred),
            'recall': recall_score(y_val, y_pred),
            'f1': f1_score(y_val, y_pred),
            'roc_auc': roc_auc_score(y_val, y_proba)
        }
        
        fold_results.append(fold_score)
        models.append((model, scaler, fold_score['accuracy']))
    
    # Select best model
    best_idx = max(range(len(models)), key=lambda i: models[i][2])
    self.model = models[best_idx][0]
    self.scaler = models[best_idx][1]
    
    return {
        'best_model': self.model,
        'best_scaler': self.scaler,
        'fold_results': fold_results,
        'avg_accuracy': np.mean([f['accuracy'] for f in fold_results]),
        'feature_importance': self.get_feature_importance()
    }
```

### Phase 3: Prediction & Signal Generation (~150 lines)

```python
def predict(self, df: pd.DataFrame) -> Dict:
    """
    Make prediction on latest data.
    
    Returns:
        Dictionary with:
        - probability: 0-1 (probability of up move)
        - prediction: 0 or 1
        - confidence: distance from 0.5
        - signal: -1, 0, or 1
    """
    if self.model is None:
        self.load_model()
    
    # Create features
    features = self.create_features(df)
    if len(features) == 0:
        return {
            'probability': 0.5,
            'prediction': 0,
            'confidence': 0.0,
            'signal': 0
        }
    
    # Get latest features
    X_latest = features.drop(['target'], axis=1).iloc[-1:]
    
    # Scale
    X_scaled = self.scaler.transform(X_latest)
    
    # Predict
    proba = self.model.predict_proba(X_scaled)[0]
    probability_up = proba[1]
    prediction = int(probability_up > 0.5)
    
    # Calculate confidence
    confidence = abs(probability_up - 0.5) * 2
    
    # Generate signal
    if probability_up > 0.65:
        signal = 1  # Strong bullish
    elif probability_up > 0.55:
        signal = 0.5  # Moderate bullish
    elif probability_up < 0.35:
        signal = -1  # Strong bearish
    elif probability_up < 0.45:
        signal = -0.5  # Moderate bearish
    else:
        signal = 0  # Neutral
    
    return {
        'probability': float(probability_up),
        'prediction': prediction,
        'confidence': float(confidence),
        'signal': float(signal),
        'probability_down': float(proba[0])
    }

def generate_signal(
    self,
    data: pd.DataFrame,
    current_price: float,
    current_position: Optional[str] = None
) -> LayerSignal:
    """Generate Layer 4 trading signal."""
    
    prediction = self.predict(data)
    
    # Determine direction
    if prediction['signal'] > 0.3:
        direction = 'long'
    elif prediction['signal'] < -0.3:
        direction = 'short'
    else:
        direction = 'neutral'
    
    # Use confidence as strength
    confidence = prediction['confidence']
    
    return LayerSignal(
        direction=direction,
        confidence=confidence,
        strength=confidence,
        metadata={
            'layer': self.name,
            'probability_up': prediction['probability'],
            'probability_down': prediction['probability_down'],
            'ml_signal': prediction['signal'],
            'prediction': prediction['prediction'],
            'feature_count': len(self.feature_columns) if hasattr(self, 'feature_columns') else 0
        }
    )
```

## Test Plan

### Test Coverage (~300 lines)

```python
def test_layer4_xgboost():
    """Comprehensive Layer 4 tests."""
    
    # Test 1: Initialization
    test_initialization()
    
    # Test 2: Feature Creation
    test_feature_creation()
    
    # Test 3: Feature Count
    test_feature_count()
    
    # Test 4: Model Training
    test_model_training()
    
    # Test 5: Walk-Forward Validation
    test_walk_forward()
    
    # Test 6: Prediction
    test_prediction()
    
    # Test 7: Probability Calibration
    test_probability_calibration()
    
    # Test 8: Feature Importance
    test_feature_importance()
    
    # Test 9: Model Persistence
    test_model_save_load()
    
    # Test 10: Signal Generation
    test_signal_generation()
    
    # Test 11: Performance Metrics
    test_performance_metrics()
    
    # Test 12: Edge Cases
    test_edge_cases()
```

## Development Checklist

### Core Implementation
- [ ] Create `src/layers/layer4_xgboost.py`
- [ ] Implement Layer4XGBoost class
- [ ] Implement feature engineering (40+ features)
- [ ] Implement price action features
- [ ] Implement technical indicator features
- [ ] Implement layer signal features
- [ ] Implement time features
- [ ] Implement lag features

### Training Pipeline
- [ ] Implement basic training method
- [ ] Implement walk-forward validation
- [ ] Implement early stopping
- [ ] Implement model evaluation
- [ ] Implement feature importance tracking
- [ ] Implement probability calibration

### Persistence
- [ ] Implement model save/load
- [ ] Implement scaler save/load
- [ ] Implement feature column tracking
- [ ] Implement model versioning

### Prediction
- [ ] Implement prediction method
- [ ] Implement probability prediction
- [ ] Implement signal generation
- [ ] Add confidence calculation

### Testing
- [ ] Create `tests/test_layer4_xgboost.py`
- [ ] Test feature engineering
- [ ] Test model training
- [ ] Test walk-forward validation
- [ ] Test predictions
- [ ] Test model persistence
- [ ] Test signal generation
- [ ] Test edge cases
- [ ] Run all tests (target: 100% pass)

### Documentation
- [ ] Add comprehensive docstrings
- [ ] Create training guide
- [ ] Document feature engineering
- [ ] Create `docs/PHASE_2_WEEKS_6-7_COMPLETE.md`

## Expected Deliverables

### Code Files
1. **`src/layers/layer4_xgboost.py`** (~600 lines)
   - Layer 4 implementation
   - Feature engineering
   - Training pipeline
   - Prediction methods

2. **`tests/test_layer4_xgboost.py`** (~300 lines)
   - Comprehensive test suite
   - 12 test cases
   - Performance validation

3. **`docs/PHASE_2_WEEKS_6-7_COMPLETE.md`**
   - Completion documentation
   - Training results
   - Feature importance analysis

### Performance Targets
- All tests passing (100%)
- Model accuracy: 55-65%
- Training time: <5 minutes
- Prediction latency: <50ms
- Feature importance stability: >80%

## Dependencies

**Required:**
- xgboost >= 2.0.3
- scikit-learn >= 1.3.2
- pandas >= 2.1.4
- numpy >= 1.26.3
- joblib >= 1.3.2 (for persistence)

**Optional:**
- shap (for explainability)
- optuna (for hyperparameter tuning)

## Integration Points

### Layer 1-3 Integration
```python
# Feature engineering from previous layers
def add_layer_features(self, df: pd.DataFrame, layer_signals: Dict) -> pd.DataFrame:
    """Add features from Layers 1-3."""
    
    features = df.copy()
    
    # Layer 1: Traditional
    if 'layer1' in layer_signals:
        features['layer1_score'] = layer_signals['layer1']['score']
        features['layer1_confidence'] = layer_signals['layer1']['confidence']
    
    # Layer 2: Volume Delta
    if 'layer2' in layer_signals:
        features['layer2_cvd'] = layer_signals['layer2']['cvd']
        features['layer2_divergence_count'] = layer_signals['layer2']['divergence_count']
    
    # Layer 3: Weis Wave
    if 'layer3' in layer_signals:
        features['layer3_accumulation'] = layer_signals['layer3']['accumulation_confidence']
        features['layer3_distribution'] = layer_signals['layer3']['distribution_confidence']
    
    return features
```

## Risk Considerations

### Overfitting
- **Issue:** Model learns training data too well
- **Mitigation:** Walk-forward validation, early stopping, regularization
- **Monitoring:** Track train vs validation performance gap

### Feature Drift
- **Issue:** Feature distributions change over time
- **Mitigation:** Regular retraining, feature importance monitoring
- **Schedule:** Retrain weekly or when accuracy drops >10%

### Look-Ahead Bias
- **Issue:** Using future information in features
- **Mitigation:** Careful feature engineering, strict time-ordering
- **Validation:** Manual review of all features

## Success Criteria

### Must Have (MVP)
- ✅ Feature engineering working (40+ features)
- ✅ Model training functional
- ✅ Walk-forward validation implemented
- ✅ Prediction working
- ✅ All tests passing

### Should Have
- ✅ Feature importance analysis
- ✅ Model persistence
- ✅ Probability calibration
- ✅ Performance metrics

### Nice to Have
- SHAP explainability
- Hyperparameter tuning (Optuna)
- Ensemble of multiple models
- Online learning updates

## Timeline

### Day 1 (December 16, 2025)
- Morning: Feature engineering implementation
- Afternoon: Training pipeline
- Evening: Testing framework

### Day 2 (December 17, 2025)
- Morning: Walk-forward validation
- Afternoon: Prediction & signal generation
- Evening: Model persistence

### Day 3 (December 18, 2025)
- Morning: Complete testing
- Afternoon: Documentation
- Evening: Integration validation

## Next Phase Preview

**Phase 2 Week 8: CNN-LSTM Deep Learning (Layer 5)**
- Sequence modeling with CNN-LSTM
- Pattern recognition in candle sequences
- Ensemble with XGBoost
- Target win rate: 70-75%

---

**Status:** Ready to Begin Implementation  
**Dependencies:** Layers 1-3 complete ✅  
**Estimated LOC:** ~900 lines (600 layer + 300 tests)
