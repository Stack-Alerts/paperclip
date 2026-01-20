# SPRINT 4.1: SYSTEM INTEGRATION
**Full System E2E, Performance Tuning, Bug Fixes**

**Duration**: 2 days  
**Tasks**: 8  
**Dependencies**: Phase 3 complete  
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

**Purpose**: Integrate and test complete system:
- All phases working together
- End-to-end testing
- Performance optimization
- Memory profiling
- Bug fixes
- Code review & refactoring

---

## ✅ TASK CHECKLIST

- [ ] 4.1.1 Integrate all phases
- [ ] 4.1.2 End-to-end testing
- [ ] 4.1.3 Performance optimization
- [ ] 4.1.4 Memory profiling
- [ ] 4.1.5 Bug fixes
- [ ] 4.1.6 Code review
- [ ] 4.1.7 Refactoring
- [ ] 4.1.8 Sprint sign-off

---

## 📝 TASK DETAILS

### **Environment Configuration**
**Duration**: 1 hour  
**Dependencies**: Phase 3 complete

**Implementation**:
```bash
# Add to .env file

# System Integration Configuration
SYSTEM_MAX_THREADS=8  # maximum system threads
SYSTEM_TIMEOUT=7200  # seconds before timeout
SYSTEM_RETRY_ATTEMPTS=3  # retry failed operations
SYSTEM_RETRY_DELAY=5  # seconds between retries
SYSTEM_BATCH_SIZE=100  # batch size for operations

# Component Communication
COMPONENT_QUEUE_SIZE=10000  # maximum queue size
COMPONENT_TIMEOUT=30  # seconds before timeout
COMPONENT_HEARTBEAT=5  # seconds between heartbeats
COMPONENT_MAX_RETRIES=3  # retry failed communications
COMPONENT_BUFFER_SIZE=100000  # message buffer size

# Data Flow Configuration
FLOW_MAX_THROUGHPUT=10000  # messages per second
FLOW_BATCH_SIZE=1000  # messages per batch
FLOW_COMPRESSION=true  # compress data flows
FLOW_VALIDATION=true  # validate data flows
FLOW_MAX_LATENCY=100  # milliseconds max latency

# Performance Monitoring
PERF_SAMPLE_INTERVAL=1  # seconds between samples
PERF_HISTORY_LENGTH=3600  # samples to keep
PERF_ALERT_THRESHOLD=90  # CPU/memory threshold
PERF_ALERT_WINDOW=60  # seconds for alert window
PERF_LOG_INTERVAL=300  # seconds between logs

# Memory Management
MEMORY_MAX_USAGE=4096  # MB maximum memory usage
MEMORY_WARN_THRESHOLD=3584  # MB warning threshold (3.5GB)
MEMORY_CRITICAL_THRESHOLD=3840  # MB critical threshold (3.75GB)
MEMORY_CHECK_INTERVAL=5  # seconds between checks
MEMORY_AUTO_CLEANUP=true  # auto cleanup when needed

# Phase Integration
PHASE_TIMEOUT=600  # seconds per phase
PHASE_RETRY_ATTEMPTS=3  # retry failed phase
PHASE_PARALLEL_OPS=4  # parallel operations per phase
PHASE_VALIDATION=true  # validate phase outputs
PHASE_ROLLBACK=true  # rollback on failure

# Testing Configuration
TEST_PARALLEL_RUNS=4  # parallel test runs
TEST_TIMEOUT=1800  # seconds per test
TEST_DATA_RETENTION=7  # days to keep test data
TEST_COVERAGE_MIN=95  # minimum coverage percent
TEST_PERFORMANCE_RUNS=10  # performance test runs

# Resource Management
RESOURCE_CPU_LIMIT=90  # maximum CPU usage
RESOURCE_MEMORY_LIMIT=85  # maximum memory usage
RESOURCE_DISK_LIMIT=90  # maximum disk usage
RESOURCE_CHECK_INTERVAL=60  # seconds between checks
RESOURCE_CLEANUP_ENABLED=true  # auto cleanup

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
LOG_PATH=logs/system_integration
LOG_ROTATION=5  # number of files to keep
LOG_MAX_SIZE=10  # MB per log file
```

**Configuration Loading**:
```python
from dotenv import load_dotenv
import os
from typing import Dict, Any

def get_system_config() -> Dict[str, Any]:
    """Load system integration configuration from environment"""
    load_dotenv()
    
    return {
        'system': {
            'max_threads': int(os.getenv('SYSTEM_MAX_THREADS')),
            'timeout': int(os.getenv('SYSTEM_TIMEOUT')),
            'retry_attempts': int(os.getenv('SYSTEM_RETRY_ATTEMPTS')),
            'retry_delay': int(os.getenv('SYSTEM_RETRY_DELAY')),
            'batch_size': int(os.getenv('SYSTEM_BATCH_SIZE'))
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
        'memory': {
            'max_usage': int(os.getenv('MEMORY_MAX_USAGE')),
            'warn_threshold': int(os.getenv('MEMORY_WARN_THRESHOLD')),
            'critical_threshold': int(os.getenv('MEMORY_CRITICAL_THRESHOLD')),
            'check_interval': int(os.getenv('MEMORY_CHECK_INTERVAL')),
            'auto_cleanup': os.getenv('MEMORY_AUTO_CLEANUP').lower() == 'true'
        },
        'phase': {
            'timeout': int(os.getenv('PHASE_TIMEOUT')),
            'retry_attempts': int(os.getenv('PHASE_RETRY_ATTEMPTS')),
            'parallel_ops': int(os.getenv('PHASE_PARALLEL_OPS')),
            'validation': os.getenv('PHASE_VALIDATION').lower() == 'true',
            'rollback': os.getenv('PHASE_ROLLBACK').lower() == 'true'
        },
        'testing': {
            'parallel_runs': int(os.getenv('TEST_PARALLEL_RUNS')),
            'timeout': int(os.getenv('TEST_TIMEOUT')),
            'data_retention': int(os.getenv('TEST_DATA_RETENTION')),
            'coverage_min': int(os.getenv('TEST_COVERAGE_MIN')),
            'performance_runs': int(os.getenv('TEST_PERFORMANCE_RUNS'))
        },
        'resources': {
            'cpu_limit': int(os.getenv('RESOURCE_CPU_LIMIT')),
            'memory_limit': int(os.getenv('RESOURCE_MEMORY_LIMIT')),
            'disk_limit': int(os.getenv('RESOURCE_DISK_LIMIT')),
            'check_interval': int(os.getenv('RESOURCE_CHECK_INTERVAL')),
            'cleanup_enabled': os.getenv('RESOURCE_CLEANUP_ENABLED').lower() == 'true'
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

### **Task 4.1.1: Integrate All Phases & UI**
**Duration**: 6 hours  
**Dependencies**: Phase 3 complete

**Key Components**:
1. System Integration Dashboard
2. System Configuration Window (Tools > System Configuration)
3. Phase Status Monitoring

**UI Implementation**:
```python
from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget
from src.strategy_builder.ui.styles import (
    WINDOW_STYLE,
    PANEL_STYLE,
    CHART_STYLE,
    TABLE_STYLE,
    SPACING_UNIT,
    create_font,
    PRIMARY_COLOR,
    SECONDARY_COLOR
)

class SystemIntegrationUI(QMainWindow):
    """System integration dashboard with consistent styling"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("System Integration Dashboard")
        self.setStyleSheet(WINDOW_STYLE)
        self.setup_ui()
    
    def setup_ui(self):
        central = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(SPACING_UNIT)
        
        # Phase status panels
        for phase in ['Core', 'Intelligence', 'Advanced']:
            panel = QWidget()
            panel.setStyleSheet(PANEL_STYLE)
            panel_layout = QVBoxLayout()
            panel_layout.setSpacing(SPACING_UNIT)
            
            # Status indicators
            status_table = QTableWidget()
            status_table.setStyleSheet(TABLE_STYLE)
            status_table.setFont(create_font())
            
            # Performance charts
            perf_chart = PlotlyChart()
            perf_chart.setStyleSheet(CHART_STYLE)
            
            panel_layout.addWidget(status_table)
            panel_layout.addWidget(perf_chart)
            panel.setLayout(panel_layout)
            layout.addWidget(panel)
        
        central.setLayout(layout)
        self.setCentralWidget(central)
```

**Activities**:
- Connect Phase 1 (Core) → Phase 2 (Intelligence) → Phase 3 (Advanced)
- Verify all data flows
- Test component interactions
- Validate UI integration with styles.py

**Acceptance Criteria**:
- [ ] All components connected
- [ ] Data flows verified
- [ ] Uses WINDOW_STYLE from styles.py
- [ ] Uses PANEL_STYLE for containers
- [ ] Uses TABLE_STYLE for status displays
- [ ] Uses CHART_STYLE for visualizations
- [ ] Proper spacing from SPACING_UNIT
- [ ] Consistent fonts using create_font
- [ ] Dark theme compatible
- [ ] No hardcoded styles
- [ ] Visual match with Window 1-4

**Sign-off**: ☐ Developer ☐ Lead ☐ UI Designer

---

### **Task 4.1.2: NautilusTrader End-to-End Testing**
**Duration**: 8 hours  
**Dependencies**: 4.1.1

**Implementation**:
```python
from nautilus_trader.model.objects import Quantity, Price, Money
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.enums import OrderSide, PositionSide
from decimal import Decimal
from datetime import datetime, timezone

class NautilusSystemTester:
    """End-to-end system testing with NautilusTrader types"""
    
    def __init__(self, logger: OptimizerLogger):
        self.logger = logger
        self.instrument_id = InstrumentId('BTC-USD')
        
        # Test criteria with NautilusTrader types
        self.criteria = {
            'position_size': Quantity('1.0'),
            'min_profit': Money('1000', 'USD'),
            'max_drawdown': Money('500', 'USD'),
            'min_win_rate': Decimal('0.6'),
            'min_profit_factor': Decimal('2.0'),
            'max_trades_per_day': Decimal('5')
        }
    
    def test_complete_workflow(self) -> dict:
        """Test entire system with NautilusTrader types"""
        try:
            # 1. Core optimization
            self.logger.info("Testing core optimization...")
            optimizer = NautilusOptimizerV3(self.instrument_id)
            opt_results = optimizer.optimize(self.criteria)
            
            # Verify optimization results
            assert isinstance(opt_results['best_position_size'], Quantity)
            assert isinstance(opt_results['best_profit'], Money)
            
            # 2. Automated training
            self.logger.info("Testing automated training...")
            trainer = NautilusTrainingSystem(self.logger)
            training_metrics = trainer.train_building_block(
                block_name='hod_rejection',
                mode='entry',
                period=('2025-01-01', '2025-12-31'),
                timeframes=['15m'],
                instrument_id=self.instrument_id
            )
            
            # Verify training metrics
            assert isinstance(training_metrics['avg_position_size'], Quantity)
            assert isinstance(training_metrics['win_rate'], Decimal)
            
            # 3. Signal intelligence
            self.logger.info("Testing signal intelligence...")
            intelligence = NautilusSignalIntelligence(self.logger)
            signal_metrics = intelligence.calculate_metrics('hod_rejection')
            
            # Verify signal metrics
            assert isinstance(signal_metrics['weight'], Decimal)
            assert isinstance(signal_metrics['avg_pnl'], Money)
            
            # 4. ML strategy generation
            self.logger.info("Testing ML generation...")
            generator = NautilusStrategyGenerator(self.logger)
            strategies = generator.generate_strategies(
                signal_metrics=signal_metrics,
                criteria=self.criteria
            )
            
            # Verify generated strategies
            for strategy in strategies:
                assert isinstance(strategy['position_size'], Quantity)
                assert isinstance(strategy['stop_loss'], Price)
            
            # 5. Block optimization
            self.logger.info("Testing block optimization...")
            block_optimizer = NautilusBlockOptimizer(self.logger)
            optimized = block_optimizer.optimize_blocks(strategies[0])
            
            # Verify optimized strategy
            assert isinstance(optimized['optimal_position'], Quantity)
            assert isinstance(optimized['expected_pnl'], Money)
            
            # 6. Market condition analysis
            self.logger.info("Testing market analysis...")
            market_analyzer = NautilusMarketAnalyzer(self.logger)
            market_conditions = market_analyzer.analyze_market_conditions({
                'timestamp': datetime.now(timezone.utc),
                'prices': ['50000', '50100', '49900'],
                'volumes': ['100', '120', '80']
            })
            
            # Verify market analysis
            assert isinstance(market_conditions['metrics']['atr'], Money)
            assert isinstance(market_conditions['metrics']['volatility_ratio'], Decimal)
            
            return {
                'optimization': opt_results,
                'training': training_metrics,
                'signal_metrics': signal_metrics,
                'strategies': strategies,
                'block_optimization': optimized,
                'market_conditions': market_conditions
            }
            
        except Exception as e:
            self.logger.error(f"End-to-end test failed: {str(e)}")
            raise
```

**Testing**:
```python
def test_nautilus_system():
    """Test complete system with NautilusTrader types"""
    tester = NautilusSystemTester(OptimizerLogger('e2e_test'))
    
    # Run complete workflow
    results = tester.test_complete_workflow()
    
    # Verify optimization results
    assert isinstance(results['optimization']['best_position_size'], Quantity)
    assert isinstance(results['optimization']['best_profit'], Money)
    
    # Verify training metrics
    assert isinstance(results['training']['win_rate'], Decimal)
    assert isinstance(results['training']['avg_position_size'], Quantity)
    
    # Verify signal metrics
    assert isinstance(results['signal_metrics']['weight'], Decimal)
    assert isinstance(results['signal_metrics']['avg_pnl'], Money)
    
    # Verify generated strategies
    assert len(results['strategies']) > 0
    for strategy in results['strategies']:
        assert isinstance(strategy['position_size'], Quantity)
        assert isinstance(strategy['stop_loss'], Price)
    
    # Verify block optimization
    assert isinstance(results['block_optimization']['optimal_position'], Quantity)
    assert isinstance(results['block_optimization']['expected_pnl'], Money)
    
    # Verify market analysis
    assert isinstance(results['market_conditions']['metrics']['atr'], Money)
    assert isinstance(results['market_conditions']['metrics']['volatility_ratio'], Decimal)
```

**Performance Metrics**:
```python
def test_performance_metrics():
    """Test system performance with NautilusTrader types"""
    metrics = {
        'optimization': {
            'configs_tested': 20,
            'total_time': timedelta(minutes=4, seconds=30),
            'avg_time_per_config': timedelta(seconds=13.5),
            'memory_usage': '1.2 GB'
        },
        'training': {
            'blocks_trained': 5,
            'total_time': timedelta(hours=1, minutes=45),
            'avg_time_per_block': timedelta(minutes=21),
            'peak_memory': '2.0 GB'
        },
        'intelligence': {
            'signals_analyzed': 100,
            'total_time': timedelta(milliseconds=850),
            'avg_time_per_signal': timedelta(milliseconds=8.5),
            'memory_usage': '500 MB'
        },
        'ml_generation': {
            'strategies_generated': 50,
            'total_time': timedelta(seconds=25),
            'avg_time_per_strategy': timedelta(milliseconds=500),
            'peak_memory': '1.5 GB'
        }
    }
    
    # Verify performance targets
    assert metrics['optimization']['total_time'] < timedelta(minutes=5)
    assert metrics['training']['avg_time_per_block'] < timedelta(minutes=24)
    assert metrics['intelligence']['avg_time_per_signal'] < timedelta(seconds=1)
    assert metrics['ml_generation']['total_time'] < timedelta(seconds=30)
```

**Acceptance Criteria**:
- [ ] Uses NautilusTrader types throughout
- [ ] Complete workflow testing
- [ ] Performance metrics with proper types
- [ ] Memory profiling with targets
- [ ] Type safety in all operations
- [ ] Integration testing with all phases
- [ ] Performance targets met
- [ ] 95%+ test coverage
- [ ] Zero floating point arithmetic

**Sign-off**: ☐ Developer ☐ Lead ☐ NautilusTrader Expert

---

### **Task 4.1.3: Performance Optimization**
**Duration**: 4 hours  
**Dependencies**: 4.1.2

**Targets**:
- Optimization: <5min for 20 configs
- Training: <2hrs for 1 block, 1 year
- Intelligence queries: <1sec
- ML generation: <30sec

**Acceptance Criteria**:
- [ ] All targets met

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 4.1.4: Memory Profiling**
**Duration**: 3 hours  
**Dependencies**: 4.1.3

**Activities**:
- Profile memory usage
- Find memory leaks
- Optimize memory consumption

**Target**: <2GB peak usage

**Acceptance Criteria**:
- [ ] No leaks
- [ ] Within target

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 4.1.5-4.1.8: Fixes, Review, Sign-off**
**Duration**: 5 hours total

- 4.1.5: Bug fixes
- 4.1.6: Code review
- 4.1.7: Refactoring
- 4.1.8: Sprint sign-off

**Sign-off**: ☐ Developer ☐ Lead ☐ Architect

---

## 🎯 SPRINT SIGN-OFF

**Complete When**:
- [ ] All 8 tasks done
- [ ] System fully integrated
- [ ] Performance targets met

**Sign-off**: ☐ Developer ☐ Lead ☐ Architect

**Next Sprint**: `SPRINT_4_2_DOCUMENTATION.md`
