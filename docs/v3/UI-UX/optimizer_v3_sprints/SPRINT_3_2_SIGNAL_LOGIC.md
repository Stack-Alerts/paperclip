# SPRINT 3.2: SIGNAL LOGIC OPTIMIZATION
**AND/OR Logic Testing, Logic Comparison, Recommendations**

**Duration**: 4 days  
**Tasks**: 12  
**Dependencies**: Sprint 3.1 complete  
**Status**: ☐ Not Started

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

**Purpose**: Optimize signal logic combinations:
- Test AND vs OR logic for signals
- Compare performance
- Generate logic recommendations
- UI controls for logic testing

---

## ✅ TASK CHECKLIST

- [ ] 3.2.1 AND/OR logic tester
- [ ] 3.2.2 Logic comparison engine
- [ ] 3.2.3 Recommendation system
- [ ] 3.2.4 UI controls
- [ ] 3.2.5 Integration tests
- [ ] 3.2.6 Write all tests
- [ ] 3.2.7 Documentation
- [ ] 3.2.8 Sprint sign-off
- [ ] 3.2.9-3.2.12 Advanced logic analysis (4 tasks)

---

## 📝 TASK DETAILS

### **Environment Configuration**
**Duration**: 1 hour  
**Dependencies**: Sprint 3.1 complete

**Implementation**:
```bash
# Add to .env file

# Logic Testing Configuration
LOGIC_MAX_COMBINATIONS=100  # maximum combinations to test
LOGIC_TEST_TIMEOUT=1800  # seconds before timeout
LOGIC_PARALLEL_TESTS=4  # parallel test processes
LOGIC_RETRY_ATTEMPTS=3  # retry failed tests
LOGIC_BATCH_SIZE=10  # combinations per batch

# Performance Requirements
PERF_MIN_IMPROVEMENT=0.05  # minimum improvement required
PERF_MAX_DRAWDOWN_INCREASE=0.02  # maximum drawdown increase
PERF_MIN_WIN_RATE=0.55  # minimum win rate required
PERF_MIN_PROFIT_FACTOR=1.5  # minimum profit factor
PERF_MAX_TRADES_DAY=5  # maximum trades per day

# Signal Analysis Configuration
SIGNAL_MIN_SAMPLES=50  # minimum samples for analysis
SIGNAL_CONFIDENCE=0.95  # statistical confidence level
SIGNAL_LOOKBACK=180  # days of historical data
SIGNAL_MIN_CORRELATION=0.7  # minimum correlation threshold
SIGNAL_MAX_P_VALUE=0.05  # maximum p-value for significance

# Logic Analysis Configuration
LOGIC_MIN_THRESHOLD=0.1  # minimum logic effect
LOGIC_MAX_SIGNALS=5  # maximum signals in combination
LOGIC_MIN_TRADES=30  # minimum trades for analysis
LOGIC_MAX_CORRELATION=0.7  # maximum correlation between signals
LOGIC_MIN_IMPACT=0.02  # minimum combined impact

# Hybrid Logic Configuration
HYBRID_MAX_GROUPS=3  # maximum AND/OR groups
HYBRID_MIN_GROUP_SIZE=2  # minimum signals per group
HYBRID_MAX_GROUP_SIZE=5  # maximum signals per group
HYBRID_MIN_IMPROVEMENT=0.1  # minimum improvement required
HYBRID_MAX_COMPLEXITY=10  # maximum logic complexity score

# Priority Analysis
PRIORITY_MIN_CONFIDENCE=0.95  # minimum confidence level
PRIORITY_MIN_SUPPORT=0.1  # minimum support level
PRIORITY_MAX_DISTANCE=3  # maximum priority distance
PRIORITY_MIN_LIFT=1.2  # minimum lift ratio
PRIORITY_UPDATE_INTERVAL=3600  # seconds between updates

# Conditional Logic
COND_MAX_CONDITIONS=3  # maximum conditions per rule
COND_MIN_OCCURRENCE=20  # minimum condition occurrences
COND_MIN_ACCURACY=0.8  # minimum condition accuracy
COND_MAX_COMPLEXITY=5  # maximum condition complexity
COND_MIN_IMPACT=0.05  # minimum condition impact

# Resource Management
RESOURCE_MAX_MEMORY=4096  # MB maximum memory usage
RESOURCE_MAX_CPU=90  # maximum CPU usage
RESOURCE_CHECK_INTERVAL=60  # seconds between checks
RESOURCE_CLEANUP_ENABLED=true  # auto cleanup
RESOURCE_BACKUP_ENABLED=true  # backup before changes

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
LOG_PATH=logs/signal_logic
LOG_ROTATION=5  # number of files to keep
LOG_MAX_SIZE=10  # MB per log file
```

**Configuration Loading**:
```python
from dotenv import load_dotenv
import os
from decimal import Decimal
from typing import Dict, Any

def get_logic_config() -> Dict[str, Any]:
    """Load signal logic configuration from environment"""
    load_dotenv()
    
    return {
        'testing': {
            'max_combinations': int(os.getenv('LOGIC_MAX_COMBINATIONS')),
            'timeout': int(os.getenv('LOGIC_TEST_TIMEOUT')),
            'parallel_tests': int(os.getenv('LOGIC_PARALLEL_TESTS')),
            'retry_attempts': int(os.getenv('LOGIC_RETRY_ATTEMPTS')),
            'batch_size': int(os.getenv('LOGIC_BATCH_SIZE'))
        },
        'performance': {
            'min_improvement': float(os.getenv('PERF_MIN_IMPROVEMENT')),
            'max_drawdown_increase': float(os.getenv('PERF_MAX_DRAWDOWN_INCREASE')),
            'min_win_rate': float(os.getenv('PERF_MIN_WIN_RATE')),
            'min_profit_factor': float(os.getenv('PERF_MIN_PROFIT_FACTOR')),
            'max_trades_day': int(os.getenv('PERF_MAX_TRADES_DAY'))
        },
        'signals': {
            'min_samples': int(os.getenv('SIGNAL_MIN_SAMPLES')),
            'confidence': float(os.getenv('SIGNAL_CONFIDENCE')),
            'lookback': int(os.getenv('SIGNAL_LOOKBACK')),
            'min_correlation': float(os.getenv('SIGNAL_MIN_CORRELATION')),
            'max_p_value': float(os.getenv('SIGNAL_MAX_P_VALUE'))
        },
        'logic': {
            'min_threshold': float(os.getenv('LOGIC_MIN_THRESHOLD')),
            'max_signals': int(os.getenv('LOGIC_MAX_SIGNALS')),
            'min_trades': int(os.getenv('LOGIC_MIN_TRADES')),
            'max_correlation': float(os.getenv('LOGIC_MAX_CORRELATION')),
            'min_impact': float(os.getenv('LOGIC_MIN_IMPACT'))
        },
        'hybrid': {
            'max_groups': int(os.getenv('HYBRID_MAX_GROUPS')),
            'min_group_size': int(os.getenv('HYBRID_MIN_GROUP_SIZE')),
            'max_group_size': int(os.getenv('HYBRID_MAX_GROUP_SIZE')),
            'min_improvement': float(os.getenv('HYBRID_MIN_IMPROVEMENT')),
            'max_complexity': int(os.getenv('HYBRID_MAX_COMPLEXITY'))
        },
        'priority': {
            'min_confidence': float(os.getenv('PRIORITY_MIN_CONFIDENCE')),
            'min_support': float(os.getenv('PRIORITY_MIN_SUPPORT')),
            'max_distance': int(os.getenv('PRIORITY_MAX_DISTANCE')),
            'min_lift': float(os.getenv('PRIORITY_MIN_LIFT')),
            'update_interval': int(os.getenv('PRIORITY_UPDATE_INTERVAL'))
        },
        'conditional': {
            'max_conditions': int(os.getenv('COND_MAX_CONDITIONS')),
            'min_occurrence': int(os.getenv('COND_MIN_OCCURRENCE')),
            'min_accuracy': float(os.getenv('COND_MIN_ACCURACY')),
            'max_complexity': int(os.getenv('COND_MAX_COMPLEXITY')),
            'min_impact': float(os.getenv('COND_MIN_IMPACT'))
        },
        'resources': {
            'max_memory': int(os.getenv('RESOURCE_MAX_MEMORY')),
            'max_cpu': int(os.getenv('RESOURCE_MAX_CPU')),
            'check_interval': int(os.getenv('RESOURCE_CHECK_INTERVAL')),
            'cleanup_enabled': os.getenv('RESOURCE_CLEANUP_ENABLED').lower() == 'true',
            'backup_enabled': os.getenv('RESOURCE_BACKUP_ENABLED').lower() == 'true'
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

### **Task 3.2.1: NautilusTrader Signal Logic Tester**
**Duration**: 6 hours  
**Dependencies**: Sprint 3.1 complete

**Implementation**:
```python
from nautilus_trader.model.objects import Quantity, Price, Money
from nautilus_trader.model.identifiers import InstrumentId
from decimal import Decimal

class NautilusSignalLogicTester:
    """Test signal logic combinations with NautilusTrader types"""
    
    def __init__(self, logger: OptimizerLogger):
        self.logger = logger
        self.instrument_id = InstrumentId('BTC-USD')
        self.scorer = NautilusStrategyScorer(self._get_criteria())
    
    def _get_criteria(self) -> dict:
        """Get test criteria with NautilusTrader types"""
        return {
            'position_size': '1.0',
            'min_profit': '1000',
            'max_drawdown': '500',
            'min_win_rate': '0.6',
            'min_profit_factor': '2.0',
            'max_trades_per_day': '5'
        }
    
    def test_logic_combination(self,
                             strategy: dict,
                             logic_type: str,
                             signal_groups: List[List[str]] = None) -> dict:
        """Test strategy with specified signal logic"""
        try:
            # Create modified strategy
            modified = strategy.copy()
            modified['logic_type'] = logic_type
            if signal_groups:
                modified['signal_groups'] = signal_groups
            
            # Run backtest with NautilusTrader types
            results = self._run_backtest_with_types(modified)
            
            # Calculate logic impact
            base_results = self._run_backtest_with_types(strategy)
            impact = self._calculate_logic_impact(base_results, results)
            
            return {
                'results': results,
                'impact': impact,
                'meets_criteria': self._validate_results(results),
                'signal_metrics': self._calculate_signal_metrics(results)
            }
            
        except Exception as e:
            self.logger.error(f"Logic test failed: {str(e)}")
            raise
    
    def _run_backtest_with_types(self, strategy: dict) -> dict:
        """Run backtest using NautilusTrader types"""
        config = {
            'position_size': Quantity(str(strategy['position_size'])),
            'stop_loss_price': Price(str(strategy['stop_loss'])),
            'take_profit_price': Price(str(strategy['take_profit'])),
            'instrument_id': self.instrument_id,
            'logic_type': strategy['logic_type']
        }
        
        results = run_backtest(config)
        
        return {
            'net_pnl': Money(str(results['net_pnl']), 'USD'),
            'max_drawdown': Money(str(results['max_drawdown']), 'USD'),
            'win_rate': Decimal(str(results['win_rate'])),
            'profit_factor': Decimal(str(results['profit_factor'])),
            'trades_per_day': Decimal(str(results['trades_per_day'])),
            'avg_trade_size': Quantity(str(results['avg_trade_size'])),
            'signal_fires': {
                name: Decimal(str(count))
                for name, count in results['signal_fires'].items()
            }
        }
    
    def _calculate_logic_impact(self,
                              base_results: dict,
                              modified_results: dict) -> dict:
        """Calculate impact of logic change using NautilusTrader types"""
        return {
            'pnl_impact': modified_results['net_pnl'] - base_results['net_pnl'],
            'drawdown_impact': (
                modified_results['max_drawdown'] - base_results['max_drawdown']
            ),
            'win_rate_impact': (
                modified_results['win_rate'] - base_results['win_rate']
            ),
            'trade_frequency_impact': (
                modified_results['trades_per_day'] - base_results['trades_per_day']
            ),
            'signal_fire_impact': {
                name: (
                    modified_results['signal_fires'][name] - 
                    base_results['signal_fires'][name]
                )
                for name in base_results['signal_fires']
            }
        }
    
    def _calculate_signal_metrics(self, results: dict) -> dict:
        """Calculate signal-specific metrics with NautilusTrader types"""
        return {
            'signal_contribution': {
                name: {
                    'fire_rate': count / Decimal('100'),
                    'avg_pnl_when_fired': Money(
                        str(results['signal_pnl'][name]),
                        'USD'
                    ),
                    'win_rate_when_fired': Decimal(
                        str(results['signal_win_rates'][name])
                    )
                }
                for name, count in results['signal_fires'].items()
            },
            'signal_correlations': {
                pair: Decimal(str(corr))
                for pair, corr in results['signal_correlations'].items()
            }
        }
    
    def _validate_results(self, results: dict) -> bool:
        """Validate results against criteria"""
        score = self.scorer.score_strategy(results)
        return score['meets_criteria']
    
    def analyze_hybrid_logic(self, strategy: dict) -> dict:
        """Test hybrid logic combinations (AND + OR groups)"""
        try:
            signals = strategy['signals']
            best_combination = None
            best_score = Decimal('0')
            
            # Test different signal groupings
            for groups in self._generate_signal_groups(signals):
                result = self.test_logic_combination(
                    strategy=strategy,
                    logic_type='HYBRID',
                    signal_groups=groups
                )
                
                score = self.scorer.score_strategy(result['results'])
                if score['total_score'] > best_score:
                    best_score = score['total_score']
                    best_combination = {
                        'groups': groups,
                        'results': result['results'],
                        'impact': result['impact'],
                        'score': score
                    }
            
            return best_combination
            
        except Exception as e:
            self.logger.error(f"Hybrid logic analysis failed: {str(e)}")
            raise
    
    def _generate_signal_groups(self, signals: List[str]) -> List[List[List[str]]]:
        """Generate possible signal groupings for hybrid logic"""
        # Implementation using itertools.combinations
        # Returns list of possible AND/OR groupings
        pass
```

**Testing**:
```python
def test_nautilus_logic_tester():
    """Test signal logic with NautilusTrader types"""
    tester = NautilusSignalLogicTester(OptimizerLogger('test'))
    
    # Test strategy
    strategy = {
        'position_size': '1.0',
        'stop_loss': '49000',
        'take_profit': '51000',
        'logic_type': 'OR',
        'signals': ['hod_rejection', 'rsi_overbought', 'vwap_cross']
    }
    
    # Test AND logic
    and_result = tester.test_logic_combination(strategy, 'AND')
    
    # Verify NautilusTrader types
    assert isinstance(and_result['results']['net_pnl'], Money)
    assert isinstance(and_result['results']['win_rate'], Decimal)
    assert isinstance(and_result['impact']['pnl_impact'], Money)
    
    # Test OR logic
    or_result = tester.test_logic_combination(strategy, 'OR')
    assert isinstance(or_result['results']['trades_per_day'], Decimal)
    
    # Test hybrid logic
    hybrid_result = tester.analyze_hybrid_logic(strategy)
    assert isinstance(hybrid_result['results']['net_pnl'], Money)
    assert isinstance(hybrid_result['score']['total_score'], Decimal)
    
    # Verify signal metrics
    metrics = and_result['signal_metrics']
    for signal in metrics['signal_contribution'].values():
        assert isinstance(signal['avg_pnl_when_fired'], Money)
        assert isinstance(signal['win_rate_when_fired'], Decimal)
```

**Acceptance Criteria**:
- [ ] Uses NautilusTrader types throughout
- [ ] Tests AND/OR/Hybrid logic combinations
- [ ] Proper decimal arithmetic for calculations
- [ ] Money type for PnL metrics
- [ ] Signal-specific metrics with proper types
- [ ] Impact analysis with NautilusTrader types
- [ ] Results validation against criteria
- [ ] Signal correlation analysis
- [ ] 100% test coverage
- [ ] Zero floating point arithmetic

**Sign-off**: ☐ Developer ☐ Lead ☐ NautilusTrader Expert

---

### **Task 3.2.2-3.2.8: NautilusTrader Logic Analysis & UI**
**Duration**: 24 hours total

**Critical UI Requirements**:
- All components use styles.py
- Zero hardcoded styles
- Dark theme compatible
- Visual consistency with Window 1-4
- Proper spacing and alignment
- Responsive UI updates
- Memory efficient rendering

**Implementation**:
```python
from nautilus_trader.model.objects import Quantity, Price, Money
from nautilus_trader.model.identifiers import InstrumentId
from decimal import Decimal

class NautilusLogicAnalyzer:
    """Advanced logic analysis with NautilusTrader types"""
    
    def __init__(self, logger: OptimizerLogger):
        self.logger = logger
        self.logic_tester = NautilusSignalLogicTester(logger)
    
    def compare_logic_performance(self,
                                strategy: dict,
                                logic_types: List[str]) -> dict:
        """Compare different logic types with NautilusTrader metrics"""
        try:
            results = {}
            best_logic = None
            best_score = Decimal('0')
            
            # Test each logic type
            for logic in logic_types:
                result = self.logic_tester.test_logic_combination(
                    strategy=strategy,
                    logic_type=logic
                )
                
                results[logic] = result
                score = result['results']['net_pnl'].as_decimal()
                if score > best_score:
                    best_score = score
                    best_logic = logic
            
            # Calculate comparative metrics
            comparisons = {}
            base_logic = logic_types[0]
            base_results = results[base_logic]['results']
            
            for logic in logic_types[1:]:
                curr_results = results[logic]['results']
                comparisons[f"{base_logic}_vs_{logic}"] = {
                    'pnl_diff': curr_results['net_pnl'] - base_results['net_pnl'],
                    'win_rate_diff': (
                        curr_results['win_rate'] - base_results['win_rate']
                    ),
                    'trade_reduction': (
                        (base_results['trades_per_day'] - 
                         curr_results['trades_per_day']) /
                        base_results['trades_per_day']
                    )
                }
            
            return {
                'results': results,
                'comparisons': comparisons,
                'best_logic': best_logic,
                'best_score': Money(str(best_score), 'USD')
            }
            
        except Exception as e:
            self.logger.error(f"Logic comparison failed: {str(e)}")
            raise
    
    def generate_logic_recommendations(self, strategy: dict) -> List[dict]:
        """Generate logic recommendations using NautilusTrader metrics"""
        try:
            recommendations = []
            
            # Test basic logic types
            basic_comparison = self.compare_logic_performance(
                strategy=strategy,
                logic_types=['AND', 'OR']
            )
            
            # Test hybrid logic
            hybrid_result = self.logic_tester.analyze_hybrid_logic(strategy)
            
            # Generate recommendations
            if hybrid_result['score']['total_score'] > Decimal('80'):
                recommendations.append({
                    'type': 'hybrid',
                    'groups': hybrid_result['groups'],
                    'reason': 'Superior performance',
                    'expected_impact': {
                        'pnl': hybrid_result['results']['net_pnl'].to_string(),
                        'win_rate': str(hybrid_result['results']['win_rate'])
                    }
                })
            
            elif basic_comparison['best_logic'] == 'AND':
                recommendations.append({
                    'type': 'AND',
                    'reason': 'Better risk management',
                    'expected_impact': {
                        'trade_reduction': str(
                            basic_comparison['comparisons']['AND_vs_OR']['trade_reduction']
                        ),
                        'win_rate_increase': str(
                            basic_comparison['comparisons']['AND_vs_OR']['win_rate_diff']
                        )
                    }
                })
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Recommendation generation failed: {str(e)}")
            raise
```

**UI Integration**:
```python
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QComboBox, QPushButton
from src.strategy_builder.ui.styles import (
    COMBOBOX_STYLE,
    BUTTON_STYLE,
    create_font,
    FONT_SIZE_BASE
)

class LogicControlsUI(QWidget):
    """UI controls for logic testing with NautilusTrader types"""
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Logic type selector
        self.logic_combo = QComboBox()
        self.logic_combo.setStyleSheet(COMBOBOX_STYLE)
        self.logic_combo.setFont(create_font(FONT_SIZE_BASE))
        self.logic_combo.addItems(['AND', 'OR', 'HYBRID'])
        
        # Test button
        self.test_btn = QPushButton("Test Logic")
        self.test_btn.setStyleSheet(BUTTON_STYLE)
        self.test_btn.setFont(create_font(FONT_SIZE_BASE, bold=True))
        
        layout.addWidget(self.logic_combo)
        layout.addWidget(self.test_btn)
        self.setLayout(layout)
    
    def on_test_clicked(self):
        """Run logic test with NautilusTrader types"""
        logic_type = self.logic_combo.currentText()
        strategy = self.get_current_strategy()
        
        analyzer = NautilusLogicAnalyzer(self.logger)
        result = analyzer.compare_logic_performance(
            strategy=strategy,
            logic_types=[logic_type]
        )
        
        self.display_results(result)
```

**Testing**:
```python
def test_nautilus_logic_analyzer():
    """Test logic analysis with NautilusTrader types"""
    analyzer = NautilusLogicAnalyzer(OptimizerLogger('test'))
    
    # Test strategy
    strategy = {
        'position_size': '1.0',
        'stop_loss': '49000',
        'take_profit': '51000',
        'logic_type': 'OR',
        'signals': ['hod_rejection', 'rsi_overbought', 'vwap_cross']
    }
    
    # Test logic comparison
    comparison = analyzer.compare_logic_performance(
        strategy=strategy,
        logic_types=['AND', 'OR', 'HYBRID']
    )
    
    # Verify NautilusTrader types
    assert isinstance(comparison['best_score'], Money)
    for logic, result in comparison['results'].items():
        assert isinstance(result['results']['net_pnl'], Money)
        assert isinstance(result['results']['win_rate'], Decimal)
    
    # Test recommendations
    recommendations = analyzer.generate_logic_recommendations(strategy)
    assert isinstance(recommendations, list)
    for rec in recommendations:
        if 'expected_impact' in rec:
            assert 'USD' in rec['expected_impact']['pnl']
```

**Acceptance Criteria**:
- [ ] Uses NautilusTrader types throughout
- [ ] Comprehensive logic comparison
- [ ] Performance metrics with proper types
- [ ] Impact analysis with Money/Decimal types
- [ ] Recommendations with metrics
- [ ] UI controls with proper styling
- [ ] Results display with type formatting
- [ ] Integration tests with NautilusTrader
- [ ] 100% test coverage
- [ ] Zero floating point arithmetic

**Sign-off**: ☐ Developer ☐ Lead ☐ UI Designer ☐ NautilusTrader Expert

---

### **Task 3.2.9-3.2.12: Advanced Logic**
**Duration**: 8 hours total

- Hybrid logic testing (AND + OR)
- Signal priority analysis
- Conditional logic recommendations
- Documentation

**Sign-off**: ☐ Developer ☐ Lead

---

## 🎯 SPRINT SIGN-OFF

**Complete When**:
- [ ] All 12 tasks done
- [ ] Logic optimization working

**Sign-off**: ☐ Developer ☐ Lead ☐ Architect

**Next Sprint**: `SPRINT_3_3_MARKET_CONDITIONS.md`
