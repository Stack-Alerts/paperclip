# SPRINT 2.4: PHASE 2 INTEGRATION & TESTING
**End-to-End Testing, Performance Optimization, Documentation**

**Duration**: 2 days  
**Tasks**: 5  
**Dependencies**: Sprint 2.3 complete  
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

**Purpose**: Complete Phase 2 with full integration:
- Integrate all Phase 2 components
- End-to-end testing
- Performance optimization
- Complete documentation
- Phase 2 sign-off

---

## ✅ TASK CHECKLIST

- [ ] 2.4.1 Integrate all Phase 2 components
- [ ] 2.4.2 End-to-end testing
- [ ] 2.4.3 Performance optimization
- [ ] 2.4.4 User documentation
- [ ] 2.4.5 Phase 2 complete sign-off

---

## 📝 TASK DETAILS

### **Environment Configuration**
**Duration**: 1 hour  
**Dependencies**: Sprint 2.3 complete

**Implementation**:
```bash
# Add to .env file

# Integration Configuration
INTEGRATION_MAX_THREADS=4  # maximum integration threads
INTEGRATION_TIMEOUT=3600  # seconds before timeout
INTEGRATION_RETRY_ATTEMPTS=3  # retry failed operations
INTEGRATION_RETRY_DELAY=5  # seconds between retries
INTEGRATION_BATCH_SIZE=100  # batch size for operations

# Component Communication
COMPONENT_QUEUE_SIZE=1000  # maximum queue size
COMPONENT_TIMEOUT=30  # seconds before timeout
COMPONENT_HEARTBEAT=5  # seconds between heartbeats
COMPONENT_MAX_RETRIES=3  # retry failed communications
COMPONENT_BUFFER_SIZE=10000  # message buffer size

# Data Flow Configuration
FLOW_MAX_THROUGHPUT=1000  # messages per second
FLOW_BATCH_SIZE=100  # messages per batch
FLOW_COMPRESSION=true  # compress data flows
FLOW_VALIDATION=true  # validate data flows
FLOW_MAX_LATENCY=100  # milliseconds max latency

# Performance Monitoring
PERF_SAMPLE_INTERVAL=1  # seconds between samples
PERF_HISTORY_LENGTH=3600  # samples to keep
PERF_ALERT_THRESHOLD=90  # CPU/memory threshold
PERF_ALERT_WINDOW=60  # seconds for alert window
PERF_LOG_INTERVAL=300  # seconds between logs

# Resource Management
RESOURCE_CPU_LIMIT=90  # maximum CPU usage
RESOURCE_MEMORY_LIMIT=85  # maximum memory usage
RESOURCE_DISK_LIMIT=90  # maximum disk usage
RESOURCE_CHECK_INTERVAL=5  # seconds between checks
RESOURCE_CLEANUP_ENABLED=true  # auto cleanup

# Testing Configuration
TEST_PARALLEL_RUNS=4  # parallel test runs
TEST_TIMEOUT=600  # seconds per test
TEST_DATA_RETENTION=7  # days to keep test data
TEST_COVERAGE_MIN=95  # minimum coverage percent
TEST_PERFORMANCE_RUNS=10  # performance test runs

# Documentation Generation
DOC_AUTO_GENERATE=true  # auto-generate docs
DOC_OUTPUT_PATH=docs/v3/optimizer  # output directory
DOC_INCLUDE_DIAGRAMS=true  # include diagrams
DOC_INCLUDE_EXAMPLES=true  # include examples
DOC_STYLE_CHECK=true  # check doc style

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
LOG_PATH=logs/integration
LOG_ROTATION=5  # number of files to keep
LOG_MAX_SIZE=10  # MB per log file
```

**Configuration Loading**:
```python
from dotenv import load_dotenv
import os
from typing import Dict, Any

def get_integration_config() -> Dict[str, Any]:
    """Load integration configuration from environment"""
    load_dotenv()
    
    return {
        'integration': {
            'max_threads': int(os.getenv('INTEGRATION_MAX_THREADS')),
            'timeout': int(os.getenv('INTEGRATION_TIMEOUT')),
            'retry_attempts': int(os.getenv('INTEGRATION_RETRY_ATTEMPTS')),
            'retry_delay': int(os.getenv('INTEGRATION_RETRY_DELAY')),
            'batch_size': int(os.getenv('INTEGRATION_BATCH_SIZE'))
        },
        'components': {
            'queue_size': int(os.getenv('COMPONENT_QUEUE_SIZE')),
            'timeout': int(os.getenv('COMPONENT_TIMEOUT')),
            'heartbeat': int(os.getenv('COMPONENT_HEARTBEAT')),
            'max_retries': int(os.getenv('COMPONENT_MAX_RETRIES')),
            'buffer_size': int(os.getenv('COMPONENT_BUFFER_SIZE'))
        },
        'flow': {
            'max_throughput': int(os.getenv('FLOW_MAX_THROUGHPUT')),
            'batch_size': int(os.getenv('FLOW_BATCH_SIZE')),
            'compression': os.getenv('FLOW_COMPRESSION').lower() == 'true',
            'validation': os.getenv('FLOW_VALIDATION').lower() == 'true',
            'max_latency': int(os.getenv('FLOW_MAX_LATENCY'))
        },
        'performance': {
            'sample_interval': int(os.getenv('PERF_SAMPLE_INTERVAL')),
            'history_length': int(os.getenv('PERF_HISTORY_LENGTH')),
            'alert_threshold': int(os.getenv('PERF_ALERT_THRESHOLD')),
            'alert_window': int(os.getenv('PERF_ALERT_WINDOW')),
            'log_interval': int(os.getenv('PERF_LOG_INTERVAL'))
        },
        'resources': {
            'cpu_limit': int(os.getenv('RESOURCE_CPU_LIMIT')),
            'memory_limit': int(os.getenv('RESOURCE_MEMORY_LIMIT')),
            'disk_limit': int(os.getenv('RESOURCE_DISK_LIMIT')),
            'check_interval': int(os.getenv('RESOURCE_CHECK_INTERVAL')),
            'cleanup_enabled': os.getenv('RESOURCE_CLEANUP_ENABLED').lower() == 'true'
        },
        'testing': {
            'parallel_runs': int(os.getenv('TEST_PARALLEL_RUNS')),
            'timeout': int(os.getenv('TEST_TIMEOUT')),
            'data_retention': int(os.getenv('TEST_DATA_RETENTION')),
            'coverage_min': int(os.getenv('TEST_COVERAGE_MIN')),
            'performance_runs': int(os.getenv('TEST_PERFORMANCE_RUNS'))
        },
        'documentation': {
            'auto_generate': os.getenv('DOC_AUTO_GENERATE').lower() == 'true',
            'output_path': os.getenv('DOC_OUTPUT_PATH'),
            'include_diagrams': os.getenv('DOC_INCLUDE_DIAGRAMS').lower() == 'true',
            'include_examples': os.getenv('DOC_INCLUDE_EXAMPLES').lower() == 'true',
            'style_check': os.getenv('DOC_STYLE_CHECK').lower() == 'true'
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

### **Task 2.4.1: Integrate All Components**
**Duration**: 4 hours  
**Dependencies**: Sprint 2.3 complete

**Activities**:
- Connect Automated Trainer → Signal Intelligence
- Connect Signal Intelligence → ML Generator
- Verify data flows
- Test component interactions

**Acceptance Criteria**:
- [ ] All Phase 2 components integrated
- [ ] Data flows correctly

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 2.4.2: NautilusTrader End-to-End Testing**
**Duration**: 8 hours  
**Dependencies**: 2.4.1

**Implementation**:
```python
from nautilus_trader.model.objects import Quantity, Price, Money
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.enums import OrderSide, PositionSide
from decimal import Decimal

class NautilusPhase2Tester:
    """End-to-end testing with NautilusTrader types"""
    
    def __init__(self):
        self.logger = OptimizerLogger('phase2_tester')
        self.instrument_id = InstrumentId('BTC-USD')
        
        # Test criteria with NautilusTrader types
        self.criteria = {
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
    
    def test_automated_trainer(self) -> dict:
        """Test automated training system"""
        trainer = NautilusTrainingSystem(self.logger)
        
        metrics = trainer.train_building_block(
            block_name='hod_rejection',
            mode='entry',
            period=('2025-01-01', '2025-12-31'),
            timeframes=['15m'],
            instrument_id=self.instrument_id
        )
        
        # Verify metrics have proper types
        assert isinstance(metrics['avg_position_size'], Quantity)
        assert isinstance(metrics['avg_price_impact'], Money)
        assert isinstance(metrics['win_rate'], Decimal)
        assert isinstance(metrics['profit_factor'], Decimal)
        
        return metrics
    
    def test_signal_intelligence(self, training_metrics: dict) -> dict:
        """Test signal intelligence system"""
        intelligence = NautilusSignalIntelligence(self.logger)
        
        # Record signal event
        event = NautilusSignalEvent(
            signal_name='HOD_REJECTION',
            block_name='hod',
            timestamp=datetime.now(),
            instrument_id=self.instrument_id,
            price_at_signal=Price('50000'),
            fired=True,
            position_size=Quantity('0.1'),
            position_side=PositionSide.SHORT,
            stop_loss_price=Price('51000'),
            take_profit_price=Price('48000'),
            risk_amount=Money('100', 'USD'),
            potential_reward=Money('200', 'USD'),
            risk_reward_ratio=Decimal('2'),
            trade_pnl=Money('150', 'USD'),
            max_favorable_excursion=Money('250', 'USD'),
            max_adverse_excursion=Money('-50', 'USD'),
            trade_duration=12,
            volatility=Decimal('0.02'),
            volume_ratio=Decimal('1.2'),
            trend_strength=Decimal('25'),
            session='London',
            confluence_signals=['RSI_OVERBOUGHT'],
            recheck_delay=25,
            timing_window=20
        )
        
        intelligence.record_event(event)
        
        # Calculate signal weights
        weights = intelligence.calculate_weights('hod_rejection')
        assert isinstance(weights.win_rate, Decimal)
        assert isinstance(weights.avg_pnl_contribution, Money)
        assert isinstance(weights.weight, Decimal)
        
        return weights
    
    def test_ml_generator(self, signal_weights: dict) -> dict:
        """Test ML strategy generator"""
        generator = NautilusStrategyGenerator(self.logger)
        
        # Generate strategy with NautilusTrader types
        strategy = generator.generate_strategy(
            signal_weights=signal_weights,
            criteria={
                'target_position': Quantity('1.0'),
                'min_profit': Money('1000', 'USD'),
                'max_drawdown': Money('500', 'USD'),
                'min_win_rate': Decimal('0.6'),
                'min_profit_factor': Decimal('2.0'),
                'max_trades_per_day': Decimal('5')
            }
        )
        
        # Verify strategy metrics
        assert isinstance(strategy['avg_position'], Quantity)
        assert isinstance(strategy['net_profit'], Money)
        assert isinstance(strategy['max_drawdown'], Money)
        assert isinstance(strategy['win_rate'], Decimal)
        assert isinstance(strategy['profit_factor'], Decimal)
        
        return strategy
    
    def test_phase2_end_to_end(self) -> bool:
        """Complete Phase 2 workflow with NautilusTrader types"""
        try:
            # 1. Train building block
            self.logger.info("Testing automated trainer...")
            training_metrics = self.test_automated_trainer()
            
            # 2. Test signal intelligence
            self.logger.info("Testing signal intelligence...")
            signal_weights = self.test_signal_intelligence(training_metrics)
            
            # 3. Test ML generator
            self.logger.info("Testing ML generator...")
            strategy = self.test_ml_generator(signal_weights)
            
            # 4. Verify final strategy
            scorer = NautilusStrategyScorer(self.criteria)
            score = scorer.score_strategy(strategy)
            
            assert score['meets_criteria'], "Strategy does not meet criteria"
            assert score['total_score'] >= Decimal('70'), "Strategy score too low"
            
            self.logger.info(f"End-to-end test passed (score: {score['total_score']})")
            return True
            
        except Exception as e:
            self.logger.error(f"End-to-end test failed: {str(e)}")
            raise
```

**Testing**:
```python
def test_phase2_integration():
    """Test Phase 2 integration with NautilusTrader"""
    tester = NautilusPhase2Tester()
    
    # Run end-to-end test
    success = tester.test_phase2_end_to_end()
    assert success
    
    # Verify logs for performance
    logs = tester.logger.get_logs()
    training_time = parse_duration(logs['automated_trainer'])
    assert training_time < timedelta(hours=2), "Training too slow"
    
    intelligence_time = parse_duration(logs['signal_intelligence'])
    assert intelligence_time < timedelta(seconds=1), "Signal queries too slow"
    
    generation_time = parse_duration(logs['ml_generator'])
    assert generation_time < timedelta(seconds=30), "Strategy generation too slow"
```

**Performance Metrics**:
```python
def test_performance_metrics():
    """Test performance with NautilusTrader types"""
    metrics = {
        'training': {
            'block_count': 10,
            'total_time': timedelta(hours=1, minutes=45),
            'avg_time_per_block': timedelta(minutes=10.5),
            'memory_usage': '2.1 GB'
        },
        'signal_intelligence': {
            'query_count': 1000,
            'total_time': timedelta(seconds=45),
            'avg_time_per_query': timedelta(milliseconds=45),
            'peak_memory': '500 MB'
        },
        'ml_generation': {
            'strategies_generated': 100,
            'total_time': timedelta(seconds=25),
            'avg_time_per_strategy': timedelta(milliseconds=250),
            'memory_usage': '1.5 GB'
        }
    }
    
    # Verify all metrics meet targets
    assert metrics['training']['avg_time_per_block'] < timedelta(minutes=12)
    assert metrics['signal_intelligence']['avg_time_per_query'] < timedelta(milliseconds=50)
    assert metrics['ml_generation']['avg_time_per_strategy'] < timedelta(milliseconds=300)
```

**Acceptance Criteria**:
- [ ] End-to-end test passes with NautilusTrader types
- [ ] All workflows verified with proper type safety
- [ ] Performance metrics within targets
- [ ] Memory usage optimized
- [ ] Type conversion overhead minimized
- [ ] 100% test coverage
- [ ] Zero floating point arithmetic

**Sign-off**: ☐ Developer ☐ Lead ☐ NautilusTrader Expert

---

### **Task 2.4.3: Performance Optimization**
**Duration**: 4 hours  
**Dependencies**: 2.4.2

**Targets**:
- Training: <2 hours for 1 block, 1 year data
- Signal Intelligence: <1 second query response
- ML Generation: <30 seconds for strategy

**Acceptance Criteria**:
- [ ] Meets performance targets

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 2.4.4: User Documentation & UI Style Guide**
**Duration**: 4 hours  
**Dependencies**: 2.4.3

**Deliverables**: 
1. `docs/v3/optimizer/PHASE2_USER_GUIDE.md`
2. `docs/v3/optimizer/PHASE2_UI_STYLE_GUIDE.md`

**UI Style Requirements**:
- All components use styles.py
- Zero hardcoded styles
- Dark theme compatible
- Visual consistency with Window 1-4
- Proper spacing and alignment
- Responsive UI updates
- Memory efficient rendering

**Contents**:
- How to use Automated Trainer
- Understanding signal intelligence
- Generating strategies with ML
- Best practices

**Acceptance Criteria**:
- [ ] Complete guide
- [ ] Reviewed by team

**Sign-off**: ☐ Developer ☐ Lead ☐ Tech Writer

---

### **Task 2.4.5: Phase 2 Complete Sign-off**
**Duration**: 1 hour  
**Dependencies**: 2.4.4

**Final Checklist**:
- [ ] All 72 Phase 2 tasks complete
- [ ] All tests passing (100% coverage)
- [ ] Performance targets met
- [ ] Documentation complete
- [ ] No critical bugs

**Sign-off**: ☐ Developer ☐ Lead ☐ Architect ☐ Product Owner

---

## 🎯 SPRINT SIGN-OFF

**Complete When**:
- [ ] All 5 tasks done
- [ ] Phase 2 fully tested
- [ ] Performance optimized
- [ ] Documentation complete

**Sign-off**: ☐ Developer ☐ Lead ☐ Architect

**Next Phase**: `SPRINT_3_1_BLOCK_OPTIMIZATION.md` (Phase 3 begins)
