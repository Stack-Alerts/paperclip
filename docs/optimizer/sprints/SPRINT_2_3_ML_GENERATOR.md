# SPRINT 2.3: ML STRATEGY GENERATOR
**XGBoost Integration, Signal Filtering, Strategy Scoring**

**Duration**: 4 days  
**Tasks**: 15  
**Dependencies**: Sprint 2.2 complete  
**Status**: ☐ Not Started

**Design Reference**: `docs/v3/UI-UX/OPTIMIZER_V3_SIGNAL_INTELLIGENCE.md` → "ML Strategy Generator"

**Integration Documents**:
1. **[OPTIMIZER_V3_UI_STYLING_GUIDE.md](../OPTIMIZER_V3_UI_STYLING_GUIDE.md)**
   - Central stylesheet enforcement
   - Zero hardcoded styles
   - Style constants and helpers
   - Dark theme support
   - Style validation
   - Pre-commit hooks

---

## 📋 SPRINT OVERVIEW

**Purpose**: Build ML-driven strategy generator:
- User criteria input (trade frequency, R:R, capital)
- XGBoost for signal selection
- Filter signals (weight >=50, win rate >=0.4)
- Generate strategy combinations
- Score against user criteria
- Optimize parameters

**Design Reference Sections**:
- User Interface: "User Criteria Interface"
- Pipeline: "ML Strategy Generation Pipeline"
- Filtering: Signal filtering logic
- Scoring: Strategy scoring algorithm

---

## ✅ TASK CHECKLIST

- [ ] 2.3.1 StrategyBuildCriteria UI
- [ ] 2.3.2 User criteria form
- [ ] 2.3.3 ML training pipeline
- [ ] 2.3.4 XGBoost integration
- [ ] 2.3.5 Signal filtering (weight/win rate)
- [ ] 2.3.6 Combination generator
- [ ] 2.3.7 Strategy scoring algorithm
- [ ] 2.3.8 Parameter optimizer
- [ ] 2.3.9 Validation framework
- [ ] 2.3.10 Strategy builder UI
- [ ] 2.3.11 Generated strategy preview
- [ ] 2.3.12 Save to Database (DATABASE-FIRST)
- [ ] 2.3.13 Integration tests
- [ ] 2.3.14 Tests (95% coverage)
- [ ] 2.3.15 Sprint sign-off

---

## 📝 TASK DETAILS

### **Environment Configuration**
**Duration**: 1 hour  
**Dependencies**: Sprint 2.2 complete

**Implementation**:
```bash
# Add to .env file

# ML Training Configuration
ML_MAX_EPOCHS=100  # maximum training epochs
ML_BATCH_SIZE=32  # batch size for training
ML_LEARNING_RATE=0.001  # learning rate
ML_EARLY_STOP_PATIENCE=10  # epochs without improvement
ML_MIN_DELTA=0.001  # minimum improvement required
ML_VALIDATION_SPLIT=0.2  # validation data fraction
ML_TEST_SPLIT=0.1  # test data fraction

# XGBoost Configuration
XGB_MAX_DEPTH=6  # maximum tree depth
XGB_MIN_CHILD_WEIGHT=1  # minimum sum of instance weight
XGB_GAMMA=0  # minimum loss reduction
XGB_SUBSAMPLE=0.8  # subsample ratio of training instances
XGB_COLSAMPLE_BYTREE=0.8  # subsample ratio of columns
XGB_NUM_BOOST_ROUND=100  # number of boosting rounds
XGB_EARLY_STOPPING=10  # early stopping rounds

# Signal Selection Configuration
SIGNAL_MIN_WEIGHT=50  # minimum signal weight
SIGNAL_MIN_WIN_RATE=0.4  # minimum win rate
SIGNAL_MIN_PROFIT_FACTOR=1.5  # minimum profit factor
SIGNAL_MAX_CORRELATION=0.7  # maximum correlation between signals
SIGNAL_MIN_TRADES=30  # minimum trades for inclusion

# Strategy Generation Configuration
STRATEGY_MAX_SIGNALS=5  # maximum signals per strategy
STRATEGY_MIN_SIGNALS=2  # minimum signals per strategy
STRATEGY_MAX_COMBINATIONS=1000  # maximum combinations to test
STRATEGY_MIN_SCORE=70  # minimum strategy score (0-100)
STRATEGY_TIMEOUT=3600  # seconds before timeout

# Parameter Optimization
PARAM_MAX_TRIALS=100  # maximum optimization trials
PARAM_TIMEOUT=1800  # seconds before timeout
PARAM_MIN_IMPROVEMENT=0.001  # minimum improvement required
PARAM_MAX_RETRIES=3  # retries for failed optimizations
PARAM_PARALLEL_TRIALS=4  # parallel optimization trials

# Performance Requirements
PERF_MIN_SHARPE=1.5  # minimum Sharpe ratio
PERF_MIN_SORTINO=2.0  # minimum Sortino ratio
PERF_MAX_DRAWDOWN=0.10  # maximum drawdown
PERF_MIN_TRADES_MONTH=10  # minimum trades per month
PERF_MAX_TRADES_DAY=5  # maximum trades per day
PERF_MIN_WIN_RATE=0.55  # minimum win rate

# Risk Management
RISK_MAX_POSITION=1.0  # BTC
RISK_MIN_POSITION=0.001  # BTC
RISK_MAX_LEVERAGE=1.0  # no margin
RISK_DAILY_LIMIT=500  # USD daily loss limit
RISK_MAX_CORRELATED=3  # maximum correlated positions
RISK_MIN_RR_RATIO=2.0  # minimum risk/reward ratio

# Validation Configuration
VALIDATE_OUT_OF_SAMPLE=true  # out-of-sample validation
VALIDATE_TIMEFRAMES=["15m","1h","4h","1D"]  # validation timeframes
VALIDATE_MIN_DAYS=180  # minimum validation period
VALIDATE_SIGNIFICANCE=0.05  # statistical significance level
VALIDATE_MONTE_CARLO=1000  # Monte Carlo simulations

# Export Configuration
EXPORT_INCLUDE_METADATA=true  # include generation metadata
EXPORT_INCLUDE_ML_PARAMS=true  # include ML parameters
EXPORT_COMPRESSION=true  # compress exported files
EXPORT_BACKUP=true  # backup before overwrite
EXPORT_MAX_SIZE=10  # MB maximum file size

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
LOG_PATH=logs/ml_generator
LOG_ROTATION=5  # number of files to keep
LOG_MAX_SIZE=10  # MB per log file
```

**Configuration Loading**:
```python
from dotenv import load_dotenv
import os
from decimal import Decimal
from typing import Dict, Any
from nautilus_trader.model.objects import Quantity, Money

def get_ml_config() -> Dict[str, Any]:
    """Load ML generator configuration from environment"""
    load_dotenv()
    
    return {
        'training': {
            'max_epochs': int(os.getenv('ML_MAX_EPOCHS')),
            'batch_size': int(os.getenv('ML_BATCH_SIZE')),
            'learning_rate': float(os.getenv('ML_LEARNING_RATE')),
            'early_stop_patience': int(os.getenv('ML_EARLY_STOP_PATIENCE')),
            'min_delta': float(os.getenv('ML_MIN_DELTA')),
            'validation_split': float(os.getenv('ML_VALIDATION_SPLIT')),
            'test_split': float(os.getenv('ML_TEST_SPLIT'))
        },
        'xgboost': {
            'max_depth': int(os.getenv('XGB_MAX_DEPTH')),
            'min_child_weight': int(os.getenv('XGB_MIN_CHILD_WEIGHT')),
            'gamma': float(os.getenv('XGB_GAMMA')),
            'subsample': float(os.getenv('XGB_SUBSAMPLE')),
            'colsample_bytree': float(os.getenv('XGB_COLSAMPLE_BYTREE')),
            'num_boost_round': int(os.getenv('XGB_NUM_BOOST_ROUND')),
            'early_stopping': int(os.getenv('XGB_EARLY_STOPPING'))
        },
        'signal': {
            'min_weight': int(os.getenv('SIGNAL_MIN_WEIGHT')),
            'min_win_rate': float(os.getenv('SIGNAL_MIN_WIN_RATE')),
            'min_profit_factor': float(os.getenv('SIGNAL_MIN_PROFIT_FACTOR')),
            'max_correlation': float(os.getenv('SIGNAL_MAX_CORRELATION')),
            'min_trades': int(os.getenv('SIGNAL_MIN_TRADES'))
        },
        'strategy': {
            'max_signals': int(os.getenv('STRATEGY_MAX_SIGNALS')),
            'min_signals': int(os.getenv('STRATEGY_MIN_SIGNALS')),
            'max_combinations': int(os.getenv('STRATEGY_MAX_COMBINATIONS')),
            'min_score': int(os.getenv('STRATEGY_MIN_SCORE')),
            'timeout': int(os.getenv('STRATEGY_TIMEOUT'))
        },
        'optimization': {
            'max_trials': int(os.getenv('PARAM_MAX_TRIALS')),
            'timeout': int(os.getenv('PARAM_TIMEOUT')),
            'min_improvement': float(os.getenv('PARAM_MIN_IMPROVEMENT')),
            'max_retries': int(os.getenv('PARAM_MAX_RETRIES')),
            'parallel_trials': int(os.getenv('PARAM_PARALLEL_TRIALS'))
        },
        'performance': {
            'min_sharpe': float(os.getenv('PERF_MIN_SHARPE')),
            'min_sortino': float(os.getenv('PERF_MIN_SORTINO')),
            'max_drawdown': float(os.getenv('PERF_MAX_DRAWDOWN')),
            'min_trades_month': int(os.getenv('PERF_MIN_TRADES_MONTH')),
            'max_trades_day': int(os.getenv('PERF_MAX_TRADES_DAY')),
            'min_win_rate': float(os.getenv('PERF_MIN_WIN_RATE'))
        },
        'risk': {
            'max_position': Quantity(os.getenv('RISK_MAX_POSITION')),
            'min_position': Quantity(os.getenv('RISK_MIN_POSITION')),
            'max_leverage': Decimal(os.getenv('RISK_MAX_LEVERAGE')),
            'daily_limit': Money(os.getenv('RISK_DAILY_LIMIT'), 'USD'),
            'max_correlated': int(os.getenv('RISK_MAX_CORRELATED')),
            'min_rr_ratio': float(os.getenv('RISK_MIN_RR_RATIO'))
        },
        'validation': {
            'out_of_sample': os.getenv('VALIDATE_OUT_OF_SAMPLE').lower() == 'true',
            'timeframes': os.getenv('VALIDATE_TIMEFRAMES').strip('[]').split(','),
            'min_days': int(os.getenv('VALIDATE_MIN_DAYS')),
            'significance': float(os.getenv('VALIDATE_SIGNIFICANCE')),
            'monte_carlo': int(os.getenv('VALIDATE_MONTE_CARLO'))
        },
        'export': {
            'include_metadata': os.getenv('EXPORT_INCLUDE_METADATA').lower() == 'true',
            'include_ml_params': os.getenv('EXPORT_INCLUDE_ML_PARAMS').lower() == 'true',
            'compression': os.getenv('EXPORT_COMPRESSION').lower() == 'true',
            'backup': os.getenv('EXPORT_BACKUP').lower() == 'true',
            'max_size': int(os.getenv('EXPORT_MAX_SIZE'))
        },
        'logging': {
            'level': os.getenv('LOG_LEVEL'),
            'format': os.getenv('LOG_FORMAT'),
            'path': os.getenv('LOG_PATH'),
            'rotation': int(os.getenv('LOG_ROTATION')),
            'max_size': int(os.getenv('LOG_MAX_SIZE'))
        }
    }
```

### **Task 2.3.1: StrategyBuildCriteria UI**
**Duration**: 3 hours  
**Dependencies**: Sprint 2.2 complete

**Implementation**: See OPTIMIZER_V3_SIGNAL_INTELLIGENCE.md → "User Criteria Interface"

```python
from PyQt6.QtWidgets import QWidget, QFormLayout
from src.strategy_builder.ui.styles import (
    GROUPBOX_STYLE,
    INPUT_STYLE,
    SPACING_UNIT
)

class StrategyBuildCriteriaUI(QWidget):
    """User input for strategy criteria"""
    
    def setup_ui(self):
        layout = QFormLayout()
        layout.setSpacing(SPACING_UNIT)
        
        # All inputs styled from styles.py
        # Trade frequency, R:R, capital, etc.
```

**Acceptance Criteria**:
- [ ] Form captures all criteria from design
- [ ] Uses INPUT_STYLE from styles.py

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 2.3.2-2.3.4: ML Pipeline Setup**
**Duration**: 8 hours total

- 2.3.2: User criteria validation
- 2.3.3: ML training pipeline setup
- 2.3.4: XGBoost integration (load historical signal data)

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 2.3.5: Signal Filtering**
**Duration**: 3 hours  
**Dependencies**: 2.3.4

**Implementation**:
```python
def filter_signals(self, signals: List[dict]) -> List[dict]:
    """Filter by weight and win rate"""
    return [s for s in signals 
            if s['weight'] >= 50 and s['win_rate'] >= 0.4]
```

**Acceptance Criteria**:
- [ ] Filters correctly

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 2.3.6: Combination Generator**
**Duration**: 4 hours  
**Dependencies**: 2.3.5

**Implementation**: Generate valid signal combinations

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 2.3.7: NautilusTrader Strategy Scoring**
**Duration**: 6 hours  
**Dependencies**: 2.3.6

**Implementation**:
```python
from nautilus_trader.model.objects import Quantity, Price, Money
from nautilus_trader.model.identifiers import InstrumentId
from decimal import Decimal

class NautilusStrategyScorer:
    """Score strategies using NautilusTrader types"""
    
    def __init__(self, criteria: dict):
        # Convert criteria to NautilusTrader types
        self.target_position = Quantity(str(criteria['position_size']))
        self.min_profit = Money(str(criteria['min_profit']), 'USD')
        self.max_drawdown = Money(str(criteria['max_drawdown']), 'USD')
        self.min_win_rate = Decimal(str(criteria['min_win_rate']))
        self.min_profit_factor = Decimal(str(criteria['min_profit_factor']))
        self.max_trades_per_day = Decimal(str(criteria['max_trades_per_day']))
        
        # Risk parameters
        self.max_risk_per_trade = Money(str(criteria['max_risk_per_trade']), 'USD')
        self.daily_loss_limit = Money(str(criteria['daily_loss_limit']), 'USD')
        self.max_correlated_trades = int(criteria['max_correlated_trades'])
    
    def score_strategy(self, strategy: dict) -> dict:
        """Score strategy against criteria using NautilusTrader types"""
        try:
            # Convert strategy metrics to NautilusTrader types
            avg_position = Quantity(str(strategy['avg_position_size']))
            net_profit = Money(str(strategy['net_profit']), 'USD')
            max_drawdown = Money(str(strategy['max_drawdown']), 'USD')
            win_rate = Decimal(str(strategy['win_rate']))
            profit_factor = Decimal(str(strategy['profit_factor']))
            trades_per_day = Decimal(str(strategy['trades_per_day']))
            
            # Calculate component scores (0-100)
            position_score = self._score_position_match(avg_position)
            profit_score = self._score_profit(net_profit)
            risk_score = self._score_risk_metrics(max_drawdown)
            consistency_score = self._score_consistency(win_rate, profit_factor)
            frequency_score = self._score_trade_frequency(trades_per_day)
            
            # Calculate weighted total (weights from design doc)
            total_score = (
                position_score * Decimal('0.2') +
                profit_score * Decimal('0.3') +
                risk_score * Decimal('0.2') +
                consistency_score * Decimal('0.2') +
                frequency_score * Decimal('0.1')
            )
            
            # Check critical thresholds
            meets_criteria = (
                max_drawdown <= self.max_drawdown and
                win_rate >= self.min_win_rate and
                profit_factor >= self.min_profit_factor and
                trades_per_day <= self.max_trades_per_day
            )
            
            return {
                'total_score': total_score,
                'meets_criteria': meets_criteria,
                'component_scores': {
                    'position_size': position_score,
                    'profitability': profit_score,
                    'risk_metrics': risk_score,
                    'consistency': consistency_score,
                    'trade_frequency': frequency_score
                },
                'risk_metrics': {
                    'max_drawdown': max_drawdown.to_string(),
                    'avg_risk_per_trade': self._calculate_avg_risk(strategy).to_string(),
                    'daily_var_99': self._calculate_daily_var(strategy).to_string(),
                    'correlation_exposure': self._calculate_correlation_exposure(strategy)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Scoring failed: {str(e)}")
            return None
    
    def _score_position_match(self, avg_position: Quantity) -> Decimal:
        """Score how well position size matches target"""
        deviation = abs(avg_position.as_decimal() - self.target_position.as_decimal())
        max_deviation = self.target_position.as_decimal() * Decimal('0.2')  # 20% tolerance
        
        if deviation <= max_deviation:
            return Decimal('100')
        else:
            return max(Decimal('0'), 
                      Decimal('100') * (1 - deviation / max_deviation))
    
    def _score_profit(self, net_profit: Money) -> Decimal:
        """Score profitability against minimum target"""
        if net_profit >= self.min_profit:
            return Decimal('100')
        else:
            return max(Decimal('0'),
                      Decimal('100') * (net_profit.as_decimal() / self.min_profit.as_decimal()))
    
    def _score_risk_metrics(self, max_drawdown: Money) -> Decimal:
        """Score risk metrics"""
        if max_drawdown <= self.max_drawdown:
            return Decimal('100')
        else:
            return max(Decimal('0'),
                      Decimal('100') * (self.max_drawdown.as_decimal() / max_drawdown.as_decimal()))
    
    def _score_consistency(self, win_rate: Decimal, profit_factor: Decimal) -> Decimal:
        """Score trading consistency"""
        win_rate_score = (win_rate / self.min_win_rate) * Decimal('100')
        pf_score = (profit_factor / self.min_profit_factor) * Decimal('100')
        return min(Decimal('100'), (win_rate_score + pf_score) / Decimal('2'))
    
    def _score_trade_frequency(self, trades_per_day: Decimal) -> Decimal:
        """Score trade frequency match"""
        if trades_per_day <= self.max_trades_per_day:
            return Decimal('100')
        else:
            return max(Decimal('0'),
                      Decimal('100') * (self.max_trades_per_day / trades_per_day))
    
    def _calculate_avg_risk(self, strategy: dict) -> Money:
        """Calculate average risk per trade"""
        total_risk = Money('0', 'USD')
        for trade in strategy['trades']:
            risk = Money.from_string(trade['risk_amount'])
            total_risk += risk
        return total_risk / len(strategy['trades']) if strategy['trades'] else Money('0', 'USD')
    
    def _calculate_daily_var(self, strategy: dict) -> Money:
        """Calculate 99% Value at Risk"""
        daily_returns = []
        for day in strategy['daily_results']:
            pnl = Money.from_string(day['net_pnl'])
            daily_returns.append(pnl.as_decimal())
        
        if daily_returns:
            var_99 = np.percentile(daily_returns, 1)  # 99% VaR
            return Money(str(abs(var_99)), 'USD')
        return Money('0', 'USD')
    
    def _calculate_correlation_exposure(self, strategy: dict) -> Decimal:
        """Calculate correlation exposure risk"""
        correlated_signals = [s for s in strategy['signals'] 
                            if s['correlation'] > Decimal('0.7')]
        return Decimal(str(len(correlated_signals)))
```

**Testing**:
```python
def test_nautilus_strategy_scorer():
    """Test NautilusTrader type handling in scoring"""
    criteria = {
        'position_size': '1.0',
        'min_profit': '1000',
        'max_drawdown': '500',
        'min_win_rate': '0.6',
        'min_profit_factor': '2.0',
        'max_trades_per_day': '5',
        'max_risk_per_trade': '100',
        'daily_loss_limit': '500',
        'max_correlated_trades': 3
    }
    
    scorer = NautilusStrategyScorer(criteria)
    
    strategy = {
        'avg_position_size': '0.9',
        'net_profit': '1200',
        'max_drawdown': '400',
        'win_rate': '0.65',
        'profit_factor': '2.2',
        'trades_per_day': '4',
        'trades': [
            {'risk_amount': '90.00 USD'},
            {'risk_amount': '95.00 USD'}
        ],
        'daily_results': [
            {'net_pnl': '100.00 USD'},
            {'net_pnl': '-50.00 USD'}
        ],
        'signals': [
            {'correlation': Decimal('0.8')},
            {'correlation': Decimal('0.6')}
        ]
    }
    
    result = scorer.score_strategy(strategy)
    
    # Verify NautilusTrader types
    assert isinstance(scorer.target_position, Quantity)
    assert isinstance(scorer.min_profit, Money)
    assert isinstance(scorer.min_win_rate, Decimal)
    
    # Verify scoring
    assert isinstance(result['total_score'], Decimal)
    assert Decimal('0') <= result['total_score'] <= Decimal('100')
    assert isinstance(result['meets_criteria'], bool)
    
    # Verify risk metrics
    risk_metrics = result['risk_metrics']
    assert 'USD' in risk_metrics['max_drawdown']
    assert 'USD' in risk_metrics['avg_risk_per_trade']
    assert 'USD' in risk_metrics['daily_var_99']
```

**Acceptance Criteria**:
- [ ] Uses NautilusTrader types throughout
- [ ] Proper decimal arithmetic for all calculations
- [ ] Comprehensive scoring across all criteria
- [ ] Risk metrics with proper Money type
- [ ] Position sizing with Quantity type
- [ ] Win rate and ratios with Decimal type
- [ ] Component scores (0-100 scale)
- [ ] Risk exposure analysis
- [ ] 100% test coverage
- [ ] Zero floating point arithmetic

**Sign-off**: ☐ Developer ☐ Lead ☐ NautilusTrader Expert

---

### **Task 2.3.8: NautilusTrader Parameter Optimizer**
**Duration**: 5 hours  
**Dependencies**: 2.3.7

**Implementation**:
```python
from nautilus_trader.model.objects import Quantity, Price, Money
from nautilus_trader.model.identifiers import InstrumentId
from decimal import Decimal
import numpy as np

class NautilusParameterOptimizer:
    """Optimize strategy parameters using NautilusTrader types"""
    
    def __init__(self, strategy_id: str, scorer: NautilusStrategyScorer):
        self.strategy_id = strategy_id
        self.scorer = scorer
        self.logger = OptimizerLogger('parameter_optimizer')
        
        # Parameter ranges (using NautilusTrader types)
        self.param_ranges = {
            'position_size': {
                'min': Quantity('0.1'),
                'max': Quantity('1.0'),
                'step': Quantity('0.1')
            },
            'stop_loss_pct': {
                'min': Decimal('0.005'),  # 0.5%
                'max': Decimal('0.02'),   # 2%
                'step': Decimal('0.001')
            },
            'take_profit_pct': {
                'min': Decimal('0.01'),   # 1%
                'max': Decimal('0.04'),   # 4%
                'step': Decimal('0.002')
            },
            'recheck_delay': {
                'min': Decimal('5'),      # bars
                'max': Decimal('30'),
                'step': Decimal('5')
            }
        }
    
    def optimize(self, base_config: dict, n_trials: int = 100) -> dict:
        """Find optimal parameters using Bayesian optimization"""
        try:
            best_score = Decimal('0')
            best_params = None
            
            for trial in range(n_trials):
                # Generate parameter set
                params = self._generate_params()
                
                # Apply parameters to base config
                config = self._apply_params(base_config.copy(), params)
                
                # Run backtest with parameters
                result = self._run_backtest(config)
                
                # Score result
                score = self.scorer.score_strategy(result)
                
                if score['total_score'] > best_score and score['meets_criteria']:
                    best_score = score['total_score']
                    best_params = params
                    
                    self.logger.info(
                        f"New best parameters found (score: {best_score}): {best_params}"
                    )
            
            return {
                'optimal_params': best_params,
                'score': best_score,
                'risk_metrics': self._calculate_risk_metrics(best_params)
            }
            
        except Exception as e:
            self.logger.error(f"Parameter optimization failed: {str(e)}")
            raise
    
    def _generate_params(self) -> dict:
        """Generate parameter set using NautilusTrader types"""
        params = {}
        
        for name, range_info in self.param_ranges.items():
            min_val = range_info['min']
            max_val = range_info['max']
            step = range_info['step']
            
            if isinstance(min_val, Quantity):
                # Generate Quantity parameter
                steps = int((max_val.as_decimal() - min_val.as_decimal()) / 
                          step.as_decimal())
                random_step = np.random.randint(0, steps + 1)
                value = min_val.as_decimal() + (step.as_decimal() * random_step)
                params[name] = Quantity(str(value))
                
            else:
                # Generate Decimal parameter
                steps = int((max_val - min_val) / step)
                random_step = np.random.randint(0, steps + 1)
                value = min_val + (step * random_step)
                params[name] = Decimal(str(value))
        
        return params
    
    def _apply_params(self, config: dict, params: dict) -> dict:
        """Apply parameters to config using proper types"""
        # Position size
        config['position_size'] = params['position_size'].to_string()
        
        # Stop loss price
        entry_price = Price(str(config['entry_price']))
        stop_pct = params['stop_loss_pct']
        config['stop_loss_price'] = Price(
            str(entry_price.as_decimal() * (1 - stop_pct))
        ).to_string()
        
        # Take profit price
        take_profit_pct = params['take_profit_pct']
        config['take_profit_price'] = Price(
            str(entry_price.as_decimal() * (1 + take_profit_pct))
        ).to_string()
        
        # Recheck delay
        config['recheck_delay'] = int(params['recheck_delay'])
        
        return config
    
    def _calculate_risk_metrics(self, params: dict) -> dict:
        """Calculate risk metrics for parameter set"""
        entry_price = Price('50000')  # Example price for calculation
        position = params['position_size']
        stop_pct = params['stop_loss_pct']
        
        # Calculate risk amount
        stop_distance = entry_price.as_decimal() * stop_pct
        risk_per_trade = Money(
            str(position.as_decimal() * stop_distance),
            'USD'
        )
        
        # Calculate reward amount
        take_profit_pct = params['take_profit_pct']
        profit_distance = entry_price.as_decimal() * take_profit_pct
        reward_per_trade = Money(
            str(position.as_decimal() * profit_distance),
            'USD'
        )
        
        return {
            'risk_per_trade': risk_per_trade.to_string(),
            'reward_per_trade': reward_per_trade.to_string(),
            'risk_reward_ratio': reward_per_trade.as_decimal() / risk_per_trade.as_decimal(),
            'position_size': position.to_string(),
            'stop_loss_pct': str(stop_pct),
            'take_profit_pct': str(take_profit_pct)
        }
```

**Testing**:
```python
def test_nautilus_parameter_optimizer():
    """Test NautilusTrader type handling in parameter optimization"""
    # Setup scorer with criteria
    criteria = {
        'position_size': '1.0',
        'min_profit': '1000',
        'max_drawdown': '500',
        'min_win_rate': '0.6',
        'min_profit_factor': '2.0',
        'max_trades_per_day': '5'
    }
    scorer = NautilusStrategyScorer(criteria)
    
    # Create optimizer
    optimizer = NautilusParameterOptimizer('test_strategy', scorer)
    
    # Test parameter generation
    params = optimizer._generate_params()
    assert isinstance(params['position_size'], Quantity)
    assert isinstance(params['stop_loss_pct'], Decimal)
    assert isinstance(params['take_profit_pct'], Decimal)
    assert isinstance(params['recheck_delay'], Decimal)
    
    # Test parameter application
    config = {
        'entry_price': '50000',
        'strategy_id': 'test_strategy'
    }
    modified = optimizer._apply_params(config, params)
    assert 'USD' not in modified['position_size']  # Should be pure number
    assert float(modified['stop_loss_price']) < float(config['entry_price'])
    assert float(modified['take_profit_price']) > float(config['entry_price'])
    assert isinstance(modified['recheck_delay'], int)
    
    # Test risk metrics
    metrics = optimizer._calculate_risk_metrics(params)
    assert 'USD' in metrics['risk_per_trade']
    assert 'USD' in metrics['reward_per_trade']
    assert isinstance(Decimal(metrics['risk_reward_ratio']), Decimal)
```

**Acceptance Criteria**:
- [ ] Uses NautilusTrader types throughout
- [ ] Proper decimal arithmetic for all calculations
- [ ] Position sizing with Quantity type
- [ ] Price levels with Price type
- [ ] Risk amounts with Money type
- [ ] Parameter ranges with appropriate types
- [ ] Risk metrics calculation
- [ ] Bayesian optimization integration
- [ ] 100% test coverage
- [ ] Zero floating point arithmetic

**Sign-off**: ☐ Developer ☐ Lead ☐ NautilusTrader Expert

---

### **Task 2.3.9: Validation Framework**
**Duration**: 2 hours
**Dependencies**: 2.3.8

**Implementation**:
```python
def validate_generated_strategy(strategy: dict, criteria: dict) -> dict:
    """Validate strategy meets user criteria"""
    score_result = scorer.score_strategy(strategy)
    
    return {
        'valid': score_result['meets_criteria'],
        'score': score_result['total_score'],
        'issues': [],
        'warnings': []
    }
```

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 2.3.10: Strategy Preview UI**
**Duration**: 2 hours
**Dependencies**: 2.3.9

**Implementation**: Preview dialog before saving

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 2.3.11: MLGeneratedStrategyDialog**
**Duration**: 2 hours
**Dependencies**: 2.3.10

**Implementation**: Dialog with database save option

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 2.3.12: Save to Database (DATABASE-FIRST)**
**Duration**: 2 hours
**Dependencies**: 2.3.11

**CRITICAL**: Generated strategies MUST be saved to database, NOT JSON files!

**Implementation**:
```python
def save_generated_strategy(strategy: dict) -> tuple:
    """
    Save ML-generated strategy to database
    Returns (strategy_id, version_id)
    """
    db = get_db_manager()
    
    # Create strategy in database
    strategy_id = db.strategy_manager.create_strategy(
        name=strategy['name']
    )
    
    # Create initial version with generated configuration
    version_data = {
        'strategy_id': strategy_id,
        'name': strategy['name'],
        'description': strategy.get('description', 'ML-generated strategy'),
        'blocks': strategy['blocks'],
        'signals': strategy['signals'],
        'parameters': strategy['parameters'],
        'entry_conditions': strategy['entry_conditions'],
        'exit_conditions': strategy['exit_conditions'],
        'risk_management': strategy['risk_management'],
        'backtest_config': strategy.get('backtest_config', {}),
        'tags': strategy.get('tags', []) + ['ml-generated'],
        'notes': f"Generated by ML with score: {strategy['score']}"
    }
    
    # Add ML generation metadata
    version_data['ml_metadata'] = {
        'generation_date': datetime.now().isoformat(),
        'ml_score': strategy['score'],
        'training_period': strategy['training_period'],
        'selected_signals': strategy['signal_selection'],
        'optimization_trials': strategy['optimization_trials']
    }
    
    version_id = db.strategy_manager.create_strategy_version(version_data)
    
    # Optionally export JSON backup
    if os.getenv('EXPORT_JSON_BACKUP', 'false').lower() == 'true':
        export_json_backup(strategy, version_id)
    
    return strategy_id, version_id
```

**UI Integration**:
```python
class MLGeneratedStrategyDialog(QDialog):
    """Dialog showing generated strategy with database save option"""
    
    def __init__(self, generated_strategy: dict, parent=None):
        super().__init__(parent)
        self.strategy = generated_strategy
        self.setWindowTitle("ML-Generated Strategy")
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout()
        
        # Strategy preview
        preview = self._create_preview()
        layout.addWidget(preview)
        
        # Save options
        save_layout = QHBoxLayout()
        
        # Name input
        self.name_input = QLineEdit()
        self.name_input.setText(self.strategy['name'])
        save_layout.addWidget(QLabel("Strategy Name:"))
        save_layout.addWidget(self.name_input)
        
        # Save to database button (PRIMARY)
        self.save_db_btn = QPushButton("💾 Save to Database")
        self.save_db_btn.clicked.connect(self._save_to_database)
        save_layout.addWidget(self.save_db_btn)
        
        # Export JSON backup (OPTIONAL)
        self.export_json_btn = QPushButton("📄 Export JSON Backup")
        self.export_json_btn.clicked.connect(self._export_json_backup)
        save_layout.addWidget(self.export_json_btn)
        
        layout.addLayout(save_layout)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
    
    def _save_to_database(self):
        """Save strategy to database (DATABASE-FIRST)"""
        self.strategy['name'] = self.name_input.text()
        
        try:
            strategy_id, version_id = save_generated_strategy(self.strategy)
            
            QMessageBox.information(
                self,
                "Success",
                f"Strategy saved to database:\n"
                f"ID: {strategy_id}\n"
                f"Version: 1\n\n"
                f"You can now access it from the Strategy Browser."
            )
            
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save strategy:\n{str(e)}"
            )
    
    def _export_json_backup(self):
        """Export JSON backup (OPTIONAL - backup only)"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export JSON Backup",
            f"{self.strategy['name']}_backup.json",
            "JSON Files (*.json)"
        )
        
        if filename:
            with open(filename, 'w') as f:
                json.dump(self.strategy, f, indent=2)
            
            QMessageBox.information(
                self,
                "Success",
                f"JSON backup exported to:\n{filename}"
            )
```

**Testing**:
```python
def test_ml_generator_saves_to_database():
    """Test ML-generated strategy saves to database"""
    # Generate strategy
    generator = MLStrategyGenerator(criteria)
    strategy = generator.generate_best_strategy()
    
    # Save to database
    strategy_id, version_id = save_generated_strategy(strategy)
    
    # Verify in database
    db = get_db_manager()
    saved = db.strategy_manager.get_strategy_version(version_id)
    
    assert saved is not None
    assert saved['name'] == strategy['name']
    assert saved['blocks'] == strategy['blocks']
    assert 'ml-generated' in saved['tags']
    assert 'ml_metadata' in saved
    
    # Verify can be loaded through strategy browser
    browser = StrategyBrowserDialog(mode='open')
    strategies = browser._load_strategies()
    assert any(s['strategy_id'] == strategy_id for s in strategies)

def test_ml_strategy_accessible_after_save():
    """Test saved strategy is immediately accessible"""
    strategy = generate_test_strategy()
    strategy_id, version_id = save_generated_strategy(strategy)
    
    # Should appear in strategy browser
    db = get_db_manager()
    strategies = db.strategy_manager.get_all_strategies()
    assert any(s['strategy_id'] == strategy_id for s in strategies)
    
    # Should be loadable
    loaded = db.strategy_manager.get_strategy_version(version_id)
    assert loaded is not None
```

**Acceptance Criteria**:
- [ ] Saves to database as primary storage
- [ ] Returns strategy_id and version_id
- [ ] Adds ML metadata to version
- [ ] Tags as 'ml-generated'
- [ ] Immediately accessible in Strategy Browser
- [ ] JSON export optional (backup only)
- [ ] 100% test coverage
- [ ] No JSON file dependencies

**Sign-off**: ☐ Developer ☐ Lead ☐ Architect

---

### **Task 2.3.13-2.3.15: Testing & Sign-off**
**Duration**: 6 hours total

- 2.3.13: Integration tests (generate → validate → save)
- 2.3.14: Unit tests (95% coverage)
- 2.3.15: Sprint sign-off

**Sign-off**: ☐ Developer ☐ Lead ☐ Architect

---

## 🎯 SPRINT SIGN-OFF

**Complete When**:
- [ ] All 15 tasks done
- [ ] ML pipeline working
- [ ] Strategies generated
- [ ] 100% coverage

**Sign-off**: ☐ Developer ☐ Lead ☐ Architect

**Next Sprint**: `SPRINT_2_4_INTEGRATION.md`
