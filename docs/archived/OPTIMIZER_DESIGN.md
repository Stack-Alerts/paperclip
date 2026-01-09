# Backtest Configuration Optimizer - Design Document

**Version**: 1.0  
**Last Updated**: December 16, 2025  
**Status**: Design Phase  

---

## Table of Contents

1. [Overview](#overview)
2. [Optimization Goals](#optimization-goals)
3. [Parameter Space](#parameter-space)
4. [Optimization Algorithms](#optimization-algorithms)
5. [Evaluation Metrics](#evaluation-metrics)
6. [Implementation Plan](#implementation-plan)
7. [Usage Examples](#usage-examples)

---

## Overview

### Purpose

The **Backtest Configuration Optimizer** is an automated tool that:
- Runs systematic backtests with different configurations
- Analyzes performance metrics
- Iteratively improves parameters
- Finds optimal configuration for current market conditions
- Adapts to changing market dynamics

### Key Features

1. **Multi-Objective Optimization**: Balance return, risk, and stability
2. **Intelligent Search**: Uses advanced algorithms (Bayesian, Genetic, Grid)
3. **Layer-Aware**: Optimizes parameters across all 5 analysis layers
4. **Adaptive**: Learns from each iteration
5. **Robust**: Validates against overfitting
6. **Efficient**: Parallel execution support
7. **Configurable**: Flexible optimization targets

---

## Optimization Goals

### Primary Objectives

1. **Maximize Sharpe Ratio** (risk-adjusted returns)
2. **Minimize Maximum Drawdown** (capital protection)
3. **Maximize Total Return** (profit)
4. **Optimize Win Rate** (consistency)
5. **Maximize Profit Factor** (efficiency)

### Constraints

1. **Maximum Drawdown**: < 20%
2. **Minimum Trades**: > 30 (statistical significance)
3. **Win Rate**: > 45%
4. **Profit Factor**: > 1.2

---

## Parameter Space

### 1. Global Parameters

```python
GLOBAL_PARAMS = {
    # Backtest Configuration
    'days': [30, 60, 90, 180, 365],
    'capital': [1000, 5000, 10000, 50000],
    'timeframe': ['15m', '1h', '4h'],
    
    # Risk Management
    'risk_per_trade': [0.01, 0.015, 0.02, 0.025, 0.03],
    'max_position_size': [0.05, 0.10, 0.15, 0.20],
    'stop_loss_atr_multiplier': [1.5, 2.0, 2.5, 3.0],
    'take_profit_risk_reward': [1.5, 2.0, 2.5, 3.0],
    
    # Entry/Exit Thresholds
    'confidence_threshold': [0.5, 0.6, 0.7, 0.8],
    'min_layers_agreement': [2, 3, 4, 5],
}
```

### 2. Layer 1: Traditional TA Parameters

```python
LAYER1_PARAMS = {
    # EMA Configuration
    'ema_fast_period': [8, 10, 12, 15, 20],
    'ema_slow_period': [20, 26, 30, 50],
    'ema_trend_period': [50, 100, 200],
    'ema_weight': [0.3, 0.4, 0.5],
    
    # RSI Configuration
    'rsi_period': [7, 10, 14, 21],
    'rsi_overbought': [65, 70, 75, 80],
    'rsi_oversold': [20, 25, 30, 35],
    'rsi_weight': [0.3, 0.4, 0.5],
    
    # MACD Configuration
    'macd_fast': [8, 12, 15],
    'macd_slow': [21, 26, 30],
    'macd_signal': [7, 9, 11],
    'macd_weight': [0.2, 0.3, 0.4],
    
    # Bollinger Bands
    'bb_period': [15, 20, 25, 30],
    'bb_std': [1.5, 2.0, 2.5, 3.0],
    'bb_weight': [0.2, 0.3, 0.4],
    
    # Layer Weight in Compositor
    'layer1_weight': [0.15, 0.20, 0.25, 0.30],
}
```

### 3. Layer 2: Volume Delta Parameters

```python
LAYER2_PARAMS = {
    # CVD Configuration
    'cvd_period': [10, 20, 30, 50],
    'cvd_threshold': [0.5, 0.6, 0.7, 0.8],
    'cvd_divergence_lookback': [10, 20, 30],
    
    # Volume Analysis
    'volume_ma_period': [10, 20, 30, 50],
    'volume_spike_threshold': [1.5, 2.0, 2.5, 3.0],
    
    # Layer Weight
    'layer2_weight': [0.10, 0.15, 0.20],
}
```

### 4. Layer 3: Weis Wave Parameters

```python
LAYER3_PARAMS = {
    # Wave Configuration
    'wave_threshold': [0.5, 1.0, 1.5, 2.0],
    'climax_volume_multiplier': [2.0, 2.5, 3.0, 3.5],
    'trend_wave_count': [3, 5, 7, 10],
    
    # Layer Weight
    'layer3_weight': [0.05, 0.10, 0.15],
}
```

### 5. Layer 4: XGBoost Parameters

```python
LAYER4_PARAMS = {
    # Model Configuration
    'n_estimators': [100, 150, 200, 250],
    'max_depth': [3, 5, 7, 10],
    'learning_rate': [0.01, 0.05, 0.1, 0.2],
    'subsample': [0.6, 0.8, 1.0],
    
    # Feature Engineering
    'feature_window': [10, 20, 30, 50],
    'n_features': [20, 30, 40, 50],
    
    # Prediction Threshold
    'prediction_threshold': [0.5, 0.6, 0.7],
    
    # Layer Weight
    'layer4_weight': [0.20, 0.25, 0.30],
}
```

### 6. Layer 5: CNN-LSTM Parameters

```python
LAYER5_PARAMS = {
    # Sequence Configuration
    'sequence_length': [30, 60, 90, 120],
    'n_features': [6, 8, 10, 12],
    
    # CNN Configuration
    'cnn_filters_1': [16, 32, 48, 64],
    'cnn_filters_2': [32, 64, 96, 128],
    'cnn_kernel_size': [3, 5, 7],
    
    # LSTM Configuration
    'lstm_units_1': [32, 64, 96, 128],
    'lstm_units_2': [16, 32, 48, 64],
    
    # Training Configuration
    'epochs': [20, 30, 50, 100],
    'batch_size': [16, 32, 64],
    
    # Prediction Threshold
    'prediction_threshold': [0.5, 0.6, 0.7],
    
    # Layer Weight
    'layer5_weight': [0.20, 0.25, 0.30],
}
```

### 7. Multi-Timeframe Parameters

```python
MULTI_TF_PARAMS = {
    # Timeframe Configuration
    'timeframes': [
        ['15m', '1h', '4h'],
        ['5m', '15m', '1h'],
        ['1h', '4h', '1d'],
    ],
    
    # Alignment Configuration
    'alignment_threshold': [0.5, 0.6, 0.7, 0.8],
    'higher_tf_weight': [0.5, 0.6, 0.7],
}
```

---

## Optimization Algorithms

### 1. Bayesian Optimization (Recommended)

**Best for**: Expensive function evaluations (backtests)

**Advantages**:
- Efficient exploration of parameter space
- Learns from previous evaluations
- Handles noisy objectives
- Good for 10-100 parameters

**Implementation**: Using `scikit-optimize` or `optuna`

```python
from skopt import BayesSearchCV
from skopt.space import Real, Integer, Categorical

# Define search space
search_space = {
    'confidence_threshold': Real(0.5, 0.8),
    'risk_per_trade': Real(0.01, 0.03),
    'layer1_weight': Real(0.15, 0.30),
    # ... more parameters
}

# Run optimization
optimizer = BayesSearchCV(
    estimator=backtest_wrapper,
    search_spaces=search_space,
    n_iter=100,
    scoring=sharpe_ratio_scorer,
    n_jobs=-1,
    verbose=1
)
```

### 2. Genetic Algorithm

**Best for**: Complex, multi-modal optimization

**Advantages**:
- Global optimization
- Handles multiple objectives
- Can escape local optima
- Parallelizable

**Implementation**: Using `DEAP` or custom GA

```python
# Chromosome: Vector of all parameters
# Fitness: Multi-objective (Sharpe, Drawdown, Return)
# Selection: Tournament or Roulette
# Crossover: Uniform or blend
# Mutation: Gaussian or uniform
```

### 3. Grid Search (Baseline)

**Best for**: Small parameter spaces, baseline comparison

**Advantages**:
- Simple and exhaustive
- Easy to parallelize
- Reproducible

**Disadvantages**:
- Exponential complexity
- Not efficient for large spaces

### 4. Random Search

**Best for**: Initial exploration

**Advantages**:
- Simple
- Often better than grid search
- Easy to parallelize

---

## Evaluation Metrics

### Composite Fitness Function

```python
def calculate_fitness(backtest_results):
    """
    Multi-objective fitness calculation
    
    Weights can be adjusted based on optimization goals
    """
    
    # Extract metrics
    sharpe = backtest_results['sharpe_ratio']
    total_return = backtest_results['total_return']
    max_drawdown = backtest_results['max_drawdown']
    win_rate = backtest_results['win_rate']
    profit_factor = backtest_results['profit_factor']
    n_trades = backtest_results['n_trades']
    
    # Constraint penalties
    penalty = 0
    
    if max_drawdown > 0.20:  # Max DD > 20%
        penalty += (max_drawdown - 0.20) * 10
    
    if n_trades < 30:  # Too few trades
        penalty += (30 - n_trades) * 0.1
    
    if win_rate < 0.45:  # Win rate too low
        penalty += (0.45 - win_rate) * 5
    
    # Composite score
    fitness = (
        sharpe * 0.40 +           # Risk-adjusted return (40%)
        total_return * 0.30 +     # Absolute return (30%)
        (1 - max_drawdown) * 0.15 +  # Drawdown protection (15%)
        profit_factor * 0.10 +    # Efficiency (10%)
        win_rate * 0.05           # Consistency (5%)
    ) - penalty
    
    return fitness
```

### Validation Strategy

**Walk-Forward Validation**:
```
Train Period: Days 1-60
Test Period: Days 61-90

Then roll forward:
Train Period: Days 31-90
Test Period: Days 91-120

Repeat...
```

This prevents overfitting to specific market conditions.

---

## Implementation Plan

### Phase 1: Core Infrastructure

```python
# File: src/optimization/optimizer.py

class ConfigurationOptimizer:
    """Main optimizer class"""
    
    def __init__(self, algorithm='bayesian'):
        self.algorithm = algorithm
        self.search_space = self._define_search_space()
        self.best_config = None
        self.optimization_history = []
    
    def optimize(
        self,
        days=90,
        capital=10000,
        timeframe='1h',
        max_iterations=100,
        n_jobs=-1
    ):
        """Run optimization"""
        pass
    
    def _run_backtest(self, config):
        """Run single backtest with config"""
        pass
    
    def _evaluate_fitness(self, results):
        """Calculate fitness score"""
        pass
    
    def _save_results(self):
        """Save optimization results"""
        pass
```

### Phase 2: Search Space Definition

```python
# File: src/optimization/search_space.py

class SearchSpace:
    """Define parameter search spaces"""
    
    @staticmethod
    def get_global_space():
        """Global parameters"""
        pass
    
    @staticmethod
    def get_layer_space(layer_num):
        """Layer-specific parameters"""
        pass
    
    @staticmethod
    def get_full_space():
        """Complete search space"""
        pass
```

### Phase 3: Evaluation Engine

```python
# File: src/optimization/evaluator.py

class PerformanceEvaluator:
    """Evaluate backtest performance"""
    
    def calculate_fitness(self, results):
        """Multi-objective fitness"""
        pass
    
    def check_constraints(self, results):
        """Validate constraints"""
        pass
    
    def validate_stability(self, configs):
        """Walk-forward validation"""
        pass
```

### Phase 4: CLI Integration

```bash
# New command: optimize
python scripts/bot.py optimize \
  --days 90 \
  --capital 10000 \
  --timeframe 1h \
  --algorithm bayesian \
  --max-iterations 100 \
  --objective sharpe \
  --output optimized_config.yaml
```

---

## Usage Examples

### Example 1: Basic Optimization

```bash
python scripts/bot.py optimize \
  --days 90 \
  --capital 10000 \
  --max-iterations 50
```

### Example 2: Multi-Objective Optimization

```bash
python scripts/bot.py optimize \
  --days 180 \
  --capital 50000 \
  --objectives sharpe,return,drawdown \
  --weights 0.5,0.3,0.2 \
  --algorithm genetic \
  --max-iterations 200
```

### Example 3: Layer-Specific Optimization

```bash
python scripts/bot.py optimize \
  --days 90 \
  --layers layer1,layer4,layer5 \
  --fix-other-params \
  --max-iterations 100
```

### Example 4: Walk-Forward Optimization

```bash
python scripts/bot.py optimize \
  --days 365 \
  --walk-forward \
  --train-window 60 \
  --test-window 30 \
  --algorithm bayesian
```

---

## Expected Output

```yaml
# optimized_config_20251216.yaml

optimization_metadata:
  date: 2025-12-16
  algorithm: bayesian
  iterations: 100
  best_fitness: 2.45
  validation_sharpe: 1.85

global_params:
  risk_per_trade: 0.022
  confidence_threshold: 0.68
  max_position_size: 0.12
  stop_loss_atr_multiplier: 2.3

layer1_params:
  ema_fast_period: 12
  ema_slow_period: 26
  rsi_period: 14
  layer1_weight: 0.24

layer2_params:
  cvd_period: 25
  layer2_weight: 0.15

# ... more layers

performance_metrics:
  sharpe_ratio: 1.85
  total_return: 0.285
  max_drawdown: 0.145
  win_rate: 0.562
  profit_factor: 1.95
  n_trades: 147
```

---

## Next Steps

1. ✅ Review and approve design
2. [ ] Implement core optimizer class
3. [ ] Implement search space definitions
4. [ ] Implement evaluation engine
5. [ ] Add Bayesian optimization
6. [ ] Add genetic algorithm
7. [ ] Integrate with CLI
8. [ ] Add parallel execution
9. [ ] Add progress reporting
10. [ ] Test and validate
11. [ ] Document usage

---

**Status**: Design complete, ready for implementation approval

*Last Updated: December 16, 2025*
