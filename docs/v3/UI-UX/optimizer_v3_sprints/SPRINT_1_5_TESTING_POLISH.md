# SPRINT 1.5: TESTING & POLISH (PHASE 1 COMPLETE)
**Multi-Strategy Testing, Performance Profiling, Documentation**

**Duration**: 2 days  
**Tasks**: 7  
**Dependencies**: Sprint 1.4 complete  
**Status**: ☐ Not Started

---

## 📋 SPRINT OVERVIEW

**Purpose**: Complete Phase 1 with comprehensive testing:
- Test with 10+ different strategies
- Validate accuracy of all metrics
- Performance profiling and optimization
- Complete user documentation
- Phase 1 final sign-off

**Critical Success Factors**:
- All strategies tested successfully
- Performance meets targets (<5min for 20 configs)
- Documentation complete and reviewed
- All Phase 1 components integrated

---

## ✅ TASK CHECKLIST

- [ ] 1.5.1 Test with 10+ strategies
- [ ] 1.5.2 Validate accuracy
- [ ] 1.5.3 Performance profiling
- [ ] 1.5.4 Performance optimization
- [ ] 1.5.5 User documentation
- [ ] 1.5.6 Code review & refactoring
- [ ] 1.5.7 Phase 1 complete sign-off

---

## 📝 TASK DETAILS

### **Environment Configuration**
**Duration**: 1 hour  
**Dependencies**: Sprint 1.4 complete

**Implementation**:
```bash
# Add to .env file

# Test Configuration
TEST_PARALLEL_WORKERS=4  # number of parallel test workers
TEST_TIMEOUT=300  # seconds per test
TEST_COVERAGE_MIN=95  # minimum coverage percentage
TEST_COVERAGE_FAIL=true  # fail if coverage below minimum
TEST_VERBOSITY=2  # test output detail level

# Performance Testing
PERF_MAX_RUNTIME=300  # seconds for 20 configs
PERF_MAX_MEMORY=2048  # MB maximum memory usage
PERF_MIN_CPU_UTIL=80  # minimum CPU utilization percentage
PERF_SAMPLE_INTERVAL=1  # seconds between measurements
PERF_HISTORY_LENGTH=300  # number of samples to keep

# Load Testing
LOAD_TEST_CONFIGS=100  # number of configs for load test
LOAD_TEST_CONCURRENT=20  # concurrent optimizations
LOAD_TEST_DURATION=3600  # seconds to run load test
LOAD_TEST_RAMP_UP=300  # seconds to ramp up load
LOAD_TEST_MONITOR_INTERVAL=60  # seconds between status reports

# Integration Testing
INTEGRATION_TEST_TIMEOUT=600  # seconds per integration test
INTEGRATION_TEST_RETRIES=3  # retry failed tests
INTEGRATION_TEST_BACKOFF=30  # seconds between retries
INTEGRATION_TEST_CLEANUP=true  # clean up after tests

# Profiling Configuration
PROFILE_ENABLED=true  # enable profiling
PROFILE_OUTPUT_DIR=profiles  # directory for profile data
PROFILE_STATS_COUNT=20  # number of top functions to show
PROFILE_MIN_TIME=0.1  # minimum time (seconds) to include function
PROFILE_SORT_BY=cumtime  # sort stats by (cumtime, tottime, calls)

# Memory Profiling
MEMORY_PROFILE_ENABLED=true  # enable memory profiling
MEMORY_SAMPLE_INTERVAL=1  # seconds between memory samples
MEMORY_LEAK_THRESHOLD=100  # MB growth to trigger leak warning
MEMORY_MAX_SNAPSHOTS=10  # maximum memory snapshots to keep
MEMORY_DIFF_BASELINE=true  # compare to baseline snapshot

# Test Data Configuration
TEST_DATA_PATH=tests/data  # path to test data
TEST_STRATEGIES_PATH=tests/strategies  # path to test strategies
TEST_RESULTS_PATH=tests/results  # path to test results
TEST_CACHE_ENABLED=true  # enable test data caching
TEST_CACHE_TTL=3600  # cache time-to-live in seconds

# Validation Configuration
VALIDATE_TYPES=true  # validate NautilusTrader types
VALIDATE_RANGES=true  # validate parameter ranges
VALIDATE_DEPENDENCIES=true  # validate strategy dependencies
VALIDATE_RISK_LIMITS=true  # validate risk management rules
VALIDATE_PERFORMANCE=true  # validate performance requirements

# Documentation Testing
DOC_TEST_ENABLED=true  # run documentation tests
DOC_TEST_PATHS=docs,src  # paths to check for docstrings
DOC_COVERAGE_MIN=90  # minimum documentation coverage
DOC_STYLE_CHECK=true  # check docstring style
DOC_LINK_CHECK=true  # verify documentation links

# Logging Configuration
TEST_LOG_LEVEL=INFO
TEST_LOG_FORMAT="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
TEST_LOG_PATH=logs/testing
TEST_LOG_ROTATION=5  # number of log files to keep
TEST_LOG_MAX_SIZE=10  # MB per log file
```

**Configuration Loading**:
```python
from dotenv import load_dotenv
import os
from typing import Dict, Any

def get_test_config() -> Dict[str, Any]:
    """Load testing configuration from environment"""
    load_dotenv()
    
    return {
        'test': {
            'parallel_workers': int(os.getenv('TEST_PARALLEL_WORKERS')),
            'timeout': int(os.getenv('TEST_TIMEOUT')),
            'coverage': {
                'minimum': int(os.getenv('TEST_COVERAGE_MIN')),
                'fail_under': os.getenv('TEST_COVERAGE_FAIL').lower() == 'true'
            },
            'verbosity': int(os.getenv('TEST_VERBOSITY'))
        },
        'performance': {
            'max_runtime': int(os.getenv('PERF_MAX_RUNTIME')),
            'max_memory': int(os.getenv('PERF_MAX_MEMORY')),
            'min_cpu_util': int(os.getenv('PERF_MIN_CPU_UTIL')),
            'sample_interval': int(os.getenv('PERF_SAMPLE_INTERVAL')),
            'history_length': int(os.getenv('PERF_HISTORY_LENGTH'))
        },
        'load': {
            'configs': int(os.getenv('LOAD_TEST_CONFIGS')),
            'concurrent': int(os.getenv('LOAD_TEST_CONCURRENT')),
            'duration': int(os.getenv('LOAD_TEST_DURATION')),
            'ramp_up': int(os.getenv('LOAD_TEST_RAMP_UP')),
            'monitor_interval': int(os.getenv('LOAD_TEST_MONITOR_INTERVAL'))
        },
        'integration': {
            'timeout': int(os.getenv('INTEGRATION_TEST_TIMEOUT')),
            'retries': int(os.getenv('INTEGRATION_TEST_RETRIES')),
            'backoff': int(os.getenv('INTEGRATION_TEST_BACKOFF')),
            'cleanup': os.getenv('INTEGRATION_TEST_CLEANUP').lower() == 'true'
        },
        'profiling': {
            'enabled': os.getenv('PROFILE_ENABLED').lower() == 'true',
            'output_dir': os.getenv('PROFILE_OUTPUT_DIR'),
            'stats_count': int(os.getenv('PROFILE_STATS_COUNT')),
            'min_time': float(os.getenv('PROFILE_MIN_TIME')),
            'sort_by': os.getenv('PROFILE_SORT_BY')
        },
        'memory': {
            'enabled': os.getenv('MEMORY_PROFILE_ENABLED').lower() == 'true',
            'sample_interval': int(os.getenv('MEMORY_SAMPLE_INTERVAL')),
            'leak_threshold': int(os.getenv('MEMORY_LEAK_THRESHOLD')),
            'max_snapshots': int(os.getenv('MEMORY_MAX_SNAPSHOTS')),
            'diff_baseline': os.getenv('MEMORY_DIFF_BASELINE').lower() == 'true'
        },
        'data': {
            'test_path': os.getenv('TEST_DATA_PATH'),
            'strategies_path': os.getenv('TEST_STRATEGIES_PATH'),
            'results_path': os.getenv('TEST_RESULTS_PATH'),
            'cache': {
                'enabled': os.getenv('TEST_CACHE_ENABLED').lower() == 'true',
                'ttl': int(os.getenv('TEST_CACHE_TTL'))
            }
        },
        'validation': {
            'types': os.getenv('VALIDATE_TYPES').lower() == 'true',
            'ranges': os.getenv('VALIDATE_RANGES').lower() == 'true',
            'dependencies': os.getenv('VALIDATE_DEPENDENCIES').lower() == 'true',
            'risk_limits': os.getenv('VALIDATE_RISK_LIMITS').lower() == 'true',
            'performance': os.getenv('VALIDATE_PERFORMANCE').lower() == 'true'
        },
        'docs': {
            'enabled': os.getenv('DOC_TEST_ENABLED').lower() == 'true',
            'paths': os.getenv('DOC_TEST_PATHS').split(','),
            'coverage_min': int(os.getenv('DOC_COVERAGE_MIN')),
            'style_check': os.getenv('DOC_STYLE_CHECK').lower() == 'true',
            'link_check': os.getenv('DOC_LINK_CHECK').lower() == 'true'
        },
        'logging': {
            'level': os.getenv('TEST_LOG_LEVEL'),
            'format': os.getenv('TEST_LOG_FORMAT'),
            'path': os.getenv('TEST_LOG_PATH'),
            'rotation': int(os.getenv('TEST_LOG_ROTATION')),
            'max_size': int(os.getenv('TEST_LOG_MAX_SIZE'))
        }
    }
```

### **Task 1.5.1: Test with 10+ Strategies**
**Duration**: 4 hours  
**Dependencies**: Sprint 1.4 complete

**Implementation**:
```python
# tests/integration/test_multiple_strategies.py
import pytest

STRATEGIES = [
    'hod_rejection.json',
    'lod_rejection.json',
    'rsi_vwap_50_asia.json',
    'wyckoff_spring.json',
    'fibonacci_zones.json',
    'market_structure.json',
    'divergence_strategy.json',
    'liquidity_sweep.json',
    'breakout_retest.json',
    'reversal_m_pattern.json'
]

@pytest.mark.parametrize("strategy_file", STRATEGIES)
def test_strategy_optimization(strategy_file):
    """Test optimizer with each strategy"""
    from src.optimizer_v3.core.optimizer import OptimizerV3
    
    # Load strategy
    with open(f'user_strategies/{strategy_file}') as f:
        strategy = json.load(f)
    
    # Initialize optimizer
    optimizer = OptimizerV3(strategy)
    optimizer.set_max_configs(10)
    
    # Run optimization
    results = optimizer.optimize()
    
    # Verify results
    assert len(results) > 0
    assert all('sharpe_ratio' in r for r in results)
    assert all('win_rate' in r for r in results)
    assert all('max_drawdown' in r for r in results)
```

**Acceptance Criteria**:
- [ ] 10+ strategies tested
- [ ] All pass successfully
- [ ] Results logged

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 1.5.2: Validate Accuracy**
**Duration**: 3 hours  
**Dependencies**: 1.5.1

**Implementation**:
```python
def test_metric_accuracy():
    """Validate metrics against known results"""
    
    # Known good backtest result
    expected = {
        'sharpe_ratio': 2.15,
        'win_rate': 0.62,
        'max_drawdown': -0.12,
        'net_pnl': 5420.50
    }
    
    # Run optimizer
    results = optimizer.optimize()
    best = results[0]
    
    # Validate within tolerance
    assert abs(best['sharpe_ratio'] - expected['sharpe_ratio']) < 0.05
    assert abs(best['win_rate'] - expected['win_rate']) < 0.02
    assert abs(best['max_drawdown'] - expected['max_drawdown']) < 0.01
```

**Acceptance Criteria**:
- [ ] Metrics match ground truth
- [ ] Within tolerance

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 1.5.2A: NautilusTrader Integration Tests**
**Duration**: 4 hours  
**Dependencies**: 1.5.2

**Implementation**:
```python
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.objects import Quantity, Price, Money
from nautilus_trader.model.enums import OrderSide, PositionSide
import pytest

class TestNautilusIntegration:
    """Test NautilusTrader integration"""
    
    def test_type_conversion(self):
        """Test type conversion system"""
        from src.optimizer_v3.database.nautilus_types import NautilusTypeConverter
        
        # Test Quantity conversion
        quantity = NautilusTypeConverter.to_quantity('0.1')
        assert isinstance(quantity, Quantity)
        assert quantity.to_string() == '0.1'
        
        # Test Price conversion
        price = NautilusTypeConverter.to_price('50000')
        assert isinstance(price, Price)
        assert price.to_string() == '50000'
        
        # Test Money conversion
        money = NautilusTypeConverter.to_money('500')
        assert isinstance(money, Money)
        assert money.to_string() == '500 USD'
    
    def test_risk_management(self):
        """Test risk management system"""
        from src.optimizer_v3.core.risk_manager import NautilusRiskManager
        
        risk_manager = NautilusRiskManager()
        
        # Test position size limits
        with pytest.raises(ValueError, match="below minimum"):
            risk_manager.validate_new_position(
                quantity=Quantity('0.0001'),
                side=OrderSide.BUY,
                price=Money('50000', 'USD')
            )
        
        with pytest.raises(ValueError, match="exceeds maximum"):
            risk_manager.validate_new_position(
                quantity=Quantity('2.0'),
                side=OrderSide.BUY,
                price=Money('50000', 'USD')
            )
        
        # Test daily loss limit
        risk_manager.daily_loss = Money('-499', 'USD')
        with pytest.raises(ValueError, match="loss limit"):
            risk_manager.validate_new_position(
                quantity=Quantity('0.1'),
                side=OrderSide.BUY,
                price=Money('50000', 'USD')
            )
        
        # Test stop loss calculation
        entry_price = Money('50000', 'USD')
        long_stop = risk_manager.calculate_stop_loss(entry_price, OrderSide.BUY)
        assert long_stop == Money('49000', 'USD')  # 2% below
        
        short_stop = risk_manager.calculate_stop_loss(entry_price, OrderSide.SELL)
        assert short_stop == Money('51000', 'USD')  # 2% above
    
    def test_database_integration(self):
        """Test database integration with NautilusTrader types"""
        from src.optimizer_v3.database.models import NautilusTradeEvent
        
        # Create test event
        event = NautilusTradeEvent(
            instrument_id=InstrumentId('BTC-USD'),
            order_side=OrderSide.BUY,
            quantity=Quantity('0.1'),
            price=Price('50000'),
            money=Money('5000', 'USD')
        )
        
        # Save to database
        with db.session_scope() as session:
            session.add(event)
            session.commit()
            
            # Retrieve and verify
            saved = session.query(NautilusTradeEvent).first()
            assert isinstance(saved.instrument_id, InstrumentId)
            assert isinstance(saved.order_side, OrderSide)
            assert isinstance(NautilusTypeConverter.to_quantity(saved.quantity), Quantity)
            assert isinstance(NautilusTypeConverter.to_price(saved.price), Price)
            assert isinstance(NautilusTypeConverter.to_money(saved.money), Money)
    
    def test_performance_metrics(self):
        """Test performance metrics with NautilusTrader types"""
        from src.optimizer_v3.core.performance import NautilusPerformanceMetrics
        
        trades = [
            {'pnl': Money('100', 'USD'), 'quantity': Quantity('0.1')},
            {'pnl': Money('-50', 'USD'), 'quantity': Quantity('0.1')},
            {'pnl': Money('75', 'USD'), 'quantity': Quantity('0.1')}
        ]
        
        metrics = NautilusPerformanceMetrics.calculate(trades)
        
        assert isinstance(metrics['total_pnl'], Money)
        assert metrics['total_pnl'] == Money('125', 'USD')
        assert metrics['win_rate'] == 0.67  # 2 out of 3
        assert isinstance(metrics['avg_trade_size'], Quantity)
        assert metrics['avg_trade_size'] == Quantity('0.1')
    
    def test_optimization_results(self):
        """Test optimization results with NautilusTrader types"""
        from src.optimizer_v3.core.optimizer import OptimizerV3
        
        optimizer = OptimizerV3(strategy_config)
        results = optimizer.optimize()
        
        # Verify all monetary values use Money type
        for result in results:
            assert isinstance(result['total_pnl'], Money)
            assert isinstance(result['max_drawdown'], Money)
            assert isinstance(result['avg_win'], Money)
            assert isinstance(result['avg_loss'], Money)
        
        # Verify all quantities use Quantity type
        assert isinstance(results[0]['avg_position_size'], Quantity)
        assert isinstance(results[0]['max_position_size'], Quantity)
```

**Acceptance Criteria**:
- [ ] Type conversion tests pass
- [ ] Risk management tests pass
- [ ] Database integration tests pass
- [ ] Performance metrics tests pass
- [ ] Optimization results tests pass
- [ ] All NautilusTrader types used correctly
- [ ] 95%+ test coverage for NautilusTrader integration
- [ ] No floating-point arithmetic for financial calculations

**Sign-off**: ☐ Developer ☐ Lead ☐ Risk Manager

---

### **Task 1.5.3: Performance Profiling**
**Duration**: 3 hours  
**Dependencies**: 1.5.2

**Implementation**:
```python
import cProfile
import pstats

def profile_optimization():
    """Profile optimization performance"""
    
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Run optimization
    optimizer = OptimizerV3(strategy)
    optimizer.set_max_configs(20)
    results = optimizer.optimize()
    
    profiler.disable()
    
    # Analyze
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumtime')
    stats.print_stats(20)
    
    # Identify bottlenecks
    return stats
```

**Acceptance Criteria**:
- [ ] Bottlenecks identified
- [ ] Report generated

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 1.5.4: Performance Optimization**
**Duration**: 4 hours  
**Dependencies**: 1.5.3

**Implementation**: Based on profiling results, optimize:
- Database queries (add indexes)
- Memory usage (cleanup after each config)
- Parallel execution (tune worker count)

**Target**: <5 minutes for 20 configs

**Acceptance Criteria**:
- [ ] Meets performance target
- [ ] Memory stable

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 1.5.5: User Documentation**
**Duration**: 4 hours  
**Dependencies**: 1.5.4

**Deliverable**: `docs/v3/optimizer/USER_GUIDE.md`

**Contents**:
- Getting started
- How to run optimization
- Understanding results
- Best practices
- Troubleshooting

**Acceptance Criteria**:
- [ ] Complete guide written
- [ ] Screenshots included
- [ ] Reviewed by team

**Sign-off**: ☐ Developer ☐ Lead ☐ Tech Writer

---

### **Task 1.5.6: Code Review & Refactoring**
**Duration**: 3 hours  
**Dependencies**: 1.5.5

**Activities**:
- Code review all Phase 1 code
- Refactor duplicated code
- Add docstrings
- Improve error messages

**Acceptance Criteria**:
- [ ] All code reviewed
- [ ] Refactoring complete
- [ ] Documentation updated

**Sign-off**: ☐ Developer ☐ Lead ☐ Architect

---

### **Task 1.5.7: Phase 1 Complete Sign-off**
**Duration**: 1 hour  
**Dependencies**: 1.5.6

**Final Checklist**:
- [ ] All 76 Phase 1 tasks complete
- [ ] All tests passing (95%+ coverage)
- [ ] Performance targets met
- [ ] Documentation complete
- [ ] Code reviewed
- [ ] No critical bugs

**Sign-off**: ☐ Developer ☐ Lead ☐ Architect ☐ Product Owner

---

## 🎯 SPRINT SIGN-OFF

**Complete When**:
- [ ] All 7 tasks done
- [ ] Phase 1 fully tested
- [ ] Performance optimized
- [ ] Documentation complete

**Performance Targets**:
- 20 configs in <5 minutes
- Memory usage <2GB
- CPU utilization >80%

**Sign-off**: ☐ Developer ☐ Lead ☐ Architect

**Next Phase**: `SPRINT_2_1_AUTOMATED_TRAINER.md` (Phase 2 begins)
