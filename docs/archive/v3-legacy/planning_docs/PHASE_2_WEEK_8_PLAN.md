# Phase 2 Week 8: CNN-LSTM Deep Learning (Layer 5) - PLAN

**Target Start:** December 16, 2025  
**Expected Duration:** 1 week  
**Priority:** HIGH

## Overview

Implement Layer 5: CNN-LSTM Deep Learning for sequence pattern recognition. This layer combines Convolutional Neural Networks (CNN) for spatial feature extraction with Long Short-Term Memory (LSTM) networks for temporal modeling of price sequences.

## Objectives

### Primary Goals
1. Implement CNN-LSTM hybrid architecture for candlestick pattern recognition
2. Process multi-timeframe sequences (5m, 15m, 1h, 4h)
3. Extract spatial features with CNN layers
4. Model temporal dependencies with LSTM layers
5. Generate probability-based predictions with confidence scores
6. Integrate with existing layer framework
7. Achieve 70-75% cumulative win rate (with all layers)

### Secondary Goals
- Model versioning and persistence
- Real-time inference (<100ms)
- Attention mechanism for interpretability
- Ensemble with XGBoost predictions
- Multi-horizon predictions (1, 3, 5, 10 bars ahead)

## Technical Specifications

### Architecture Design

**Input:**
- Sequence of candlesticks (e.g., last 60 bars)
- Shape: (batch_size, sequence_length, features)
- Features per candle: OHLCV + indicators (8-12 features)

**CNN Component:**
- 2-3 convolutional layers
- Extract spatial patterns from indicator relationships
- 1D convolutions along feature dimension
- Filters: 32, 64, 128
- Kernel sizes: 3, 5
- Activation: ReLU
- Max pooling between layers

**LSTM Component:**
- 2 LSTM layers (bidirectional optional)
- Hidden units: 64, 32
- Dropout: 0.2-0.3 for regularization
- Captures temporal dependencies

**Output:**
- Dense layers: 32, 16
- Output: Softmax (3 classes: down, neutral, up) OR Sigmoid (binary: down/up)
- Probability distribution over price directions

**Model Parameters:**
- Total parameters: ~500K-1M
- Trainable parameters: ~500K-1M
- Training time: 5-10 minutes (500 epochs)
- Inference time: <50ms

### Feature Engineering

**Sequence Features (per candle):**
1. OHLC normalized (log returns or z-score)
2. Volume normalized
3. Key indicators (5-7):
   - RSI
   - MACD
   - ATR normalized
   - EMA ratios
   - Volume MA ratio
   - Bollinger Band position

**Multi-Timeframe Approach:**
- Primary: 1h candles (main trading timeframe)
- Context: 4h candles (trend)
- Granular: 15m candles (entry timing)
- Option: Separate models per timeframe OR multi-input architecture

### Training Strategy

**Data Preparation:**
1. Create sequences (sliding window)
2. Label: Future price direction (N bars ahead)
3. Train/val/test split: 70/15/15 (chronological)
4. Data augmentation: Minor noise, time shifts

**Training Configuration:**
- Loss: Categorical crossentropy OR Binary crossentropy
- Optimizer: Adam (lr=0.001, decay)
- Batch size: 32-64
- Epochs: 300-500 with early stopping
- Validation patience: 20-30 epochs
- Learning rate schedule: Reduce on plateau

**Validation:**
- Walk-forward validation (3-5 folds)
- Time-series cross-validation
- Test on out-of-sample data (most recent 15%)
- Track accuracy, precision, recall, F1, AUC-ROC

**Target Metrics:**
- Validation accuracy: >60%
- Directional accuracy: >65%
- AUC-ROC: >0.65
- Sharpe ratio in backtest: >1.5
- Max drawdown: <15%

### Model Persistence

**Saved Artifacts:**
1. Model architecture (JSON/YAML)
2. Model weights (HDF5/SavedModel)
3. Preprocessing scaler (pickle)
4. Feature configuration (JSON)
5. Training history (CSV)
6. Performance metrics (JSON)

**Versioning:**
- Timestamp-based versions
- Semantic versioning (major.minor.patch)
- Model registry with metadata

## Implementation Plan

### Phase 8.1: Architecture Setup (Day 1)
- [ ] Create `src/layers/layer5_cnn_lstm.py`
- [ ] Define CNN-LSTM architecture class
- [ ] Implement sequence preprocessing
- [ ] Setup feature scaling
- [ ] Create sequence generator

**Deliverable:** Base layer5 class with architecture defined

### Phase 8.2: Training Pipeline (Day 2)
- [ ] Implement training function
- [ ] Add early stopping and callbacks
- [ ] Implement walk-forward validation
- [ ] Add learning rate scheduling
- [ ] Training history tracking

**Deliverable:** Complete training pipeline

### Phase 8.3: Prediction & Inference (Day 3)
- [ ] Real-time prediction function
- [ ] Batch prediction optimization
- [ ] Confidence score calculation
- [ ] Signal generation logic
- [ ] Ensemble with XGBoost (optional)

**Deliverable:** Prediction system ready

### Phase 8.4: Model Persistence (Day 4)
- [ ] Model save/load functions
- [ ] Version management
- [ ] Scaler persistence
- [ ] Configuration saving
- [ ] Model registry integration

**Deliverable:** Full persistence system

### Phase 8.5: Testing & Validation (Day 5)
- [ ] Create comprehensive test suite
- [ ] Unit tests for components
- [ ] Integration tests with framework
- [ ] Performance benchmarks
- [ ] Edge case testing

**Deliverable:** Test suite with >90% coverage

### Phase 8.6: Documentation (Day 6)
- [ ] Code documentation (docstrings)
- [ ] Architecture documentation
- [ ] Training guide
- [ ] Usage examples
- [ ] Performance report

**Deliverable:** Complete documentation

### Phase 8.7: Integration & Optimization (Day 7)
- [ ] Integrate with BaseLayer framework
- [ ] Optimize inference speed
- [ ] Memory optimization
- [ ] Multi-model ensemble
- [ ] Final validation

**Deliverable:** Production-ready Layer 5

## File Structure

```
src/layers/
  layer5_cnn_lstm.py          # Main implementation (~800 lines)
  
tests/
  test_layer5_cnn_lstm.py     # Comprehensive tests (~500 lines)
  
data/models/cnn_lstm/
  cnn_lstm_model.keras        # Saved model
  cnn_lstm_scaler.pkl         # Feature scaler
  config.pkl                  # Model configuration
  sequence_scaler.pkl         # Sequence normalization
  training_history.csv        # Training logs
  
docs/
  PHASE_2_WEEK_8_PLAN.md      # This file
  PHASE_2_WEEK_8_COMPLETE.md  # Completion report
```

## Dependencies

**Required (Already Installed):**
- tensorflow >= 2.15.0 ✅
- keras >= 2.15.0 ✅
- numpy >= 1.26.3 ✅
- pandas >= 2.1.4 ✅
- scikit-learn >= 1.3.2 ✅

**Additional (If Needed):**
- keras-tuner (hyperparameter optimization)
- tensorboard (visualization)
- mlflow (experiment tracking)

## Expected Outcomes

### Performance Targets

**Model Performance:**
- Training accuracy: 65-70%
- Validation accuracy: 60-65%
- Test accuracy: 60-65%
- AUC-ROC: >0.65
- Inference latency: <100ms

**Trading Performance (Backtest):**
- Win rate improvement: +3-5% (cumulative: 70-75%)
- Sharpe ratio: >1.5
- Max drawdown: <15%
- Profit factor: >1.8

### Deliverables Checklist

- [ ] Layer 5 implementation (~800 lines)
- [ ] Comprehensive test suite (~500 lines)
- [ ] Model training pipeline
- [ ] Walk-forward validation
- [ ] Model persistence system
- [ ] Real-time prediction (<100ms)
- [ ] Signal generation
- [ ] Performance documentation
- [ ] Integration with framework
- [ ] 100% test pass rate

## Risk Mitigation

### Technical Risks

**Risk 1: Overfitting**
- Mitigation: Dropout layers, L2 regularization, early stopping
- Validation: Walk-forward CV, out-of-sample testing

**Risk 2: Slow Inference**
- Mitigation: Model quantization, batch inference, GPU acceleration
- Target: <100ms per prediction

**Risk 3: Data Leakage**
- Mitigation: Strict chronological splits, no future data in features
- Validation: Manual code review, time-series CV

**Risk 4: Poor Generalization**
- Mitigation: Simpler architecture, more data, regularization
- Validation: Multiple test periods, walk-forward

### Performance Risks

**Risk 1: Lower Than Expected Accuracy**
- Mitigation: Hyperparameter tuning, feature engineering, ensemble
- Acceptable: >55% accuracy with good ROC-AUC

**Risk 2: High Latency**
- Mitigation: Model optimization, batch processing, caching
- Fallback: Reduce model complexity

**Risk 3: Memory Issues**
- Mitigation: Batch processing, model compression
- Monitoring: Track memory usage during inference

## Success Criteria

### Must Have
✅ Layer 5 implementation complete  
✅ All tests passing (100%)  
✅ Model training and validation working  
✅ Real-time prediction functional  
✅ Integration with BaseLayer framework  
✅ Documentation complete  

### Should Have
- Walk-forward validation >60% accuracy
- Inference latency <100ms
- Feature importance/attention visualization
- Model versioning system

### Nice to Have
- Multi-timeframe integration
- Ensemble with XGBoost
- Hyperparameter auto-tuning
- Real-time model monitoring

## Timeline

**Week 8 Schedule:**
- Day 1: Architecture & setup
- Day 2: Training pipeline
- Day 3: Prediction system
- Day 4: Persistence layer
- Day 5: Testing & validation
- Day 6: Documentation
- Day 7: Integration & optimization

**Milestones:**
- Day 3: First successful prediction ✓
- Day 5: All tests passing ✓
- Day 7: Production ready ✓

## Next Phase After Completion

**Phase 3: Strategy Composition (Weeks 9-10)**
- Integrate all 5 layers
- Implement strategy patterns
- Build layer compositor
- Portfolio optimization
- Multi-strategy testing

**Target:** 70-75% win rate with all layers active

---

**Prepared by:** Cline AI Assistant  
**Status:** Ready to begin Phase 2 Week 8  
**Prerequisites:** All previous phases complete ✅
