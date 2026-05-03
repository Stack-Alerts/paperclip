# SPRINT 1.1: STRATEGY ANALYSIS ENGINE
**Parse Strategies, Extract Parameters, Generate Optimization Space**

**Duration**: 3 days  
**Dependencies**: Sprint 0 complete  
**Status**: ✅ COMPLETE (19/19 tasks, 100%)

## 📋 SPRINT OVERVIEW

**Purpose**: Build core strategy analysis engine to:
- Parse strategy JSON files
- Extract optimizable parameters (timing, recheck, risk)
- Build dependency graphs
- Generate optimization space
- Validate configurations

**Critical Success Factors**:
- 100% NautilusTrader type coverage
- 95%+ test coverage
- Handles all strategy types
- Dependency graph cycle detection
- Parameter range generation
- API design complete
- Zero hardcoded styles
- Dark theme compatible
- Visual consistency with Window 1 & 2

## 📚 INTEGRATION DOCUMENTS

This sprint integrates with the following detailed specifications:

1. **[OPTIMIZER_V3_UI_STYLING_GUIDE.md](../OPTIMIZER_V3_UI_STYLING_GUIDE.md)**
   - Central stylesheet enforcement
   - Zero hardcoded styles
   - Style constants and helpers
   - Dark theme support
   - Style validation
   - Pre-commit hooks

2. **[NAUTILUS_STRATEGY_STRUCTURE_INTEGRATION.md](../../strategy-builder/NAUTILUS_STRATEGY_STRUCTURE_INTEGRATION.md)**
   - Strategy structure handling
   - Building blocks management
   - Dependencies resolution
   - Timing constraints
   - Parameter validation

3. **[NAUTILUS_BACKTEST_CONFIG_INTEGRATION.md](../../strategy-builder/NAUTILUS_BACKTEST_CONFIG_INTEGRATION.md)**
   - Configuration transfer system
   - Validation system
   - Results comparison
   - Risk management handling

4. **[NAUTILUS_EXECUTION_MODES_INTEGRATION.md](../../strategy-builder/NAUTILUS_EXECUTION_MODES_INTEGRATION.md)**
   - Execution mode handling
   - State management
   - Progress tracking
   - Error recovery

5. **[NAUTILUS_WEIGHT_CALCULATION_SYSTEM.md](../../strategy-builder/NAUTILUS_WEIGHT_CALCULATION_SYSTEM.md)**
   - Parameter weight calculation
   - Optimization priority
   - Impact assessment
   - Range generation

6. **[OPTIMIZER_V3_TESTING_FRAMEWORK.md](../OPTIMIZER_V3_TESTING_FRAMEWORK.md)**
   - Test coverage requirements
   - Integration test patterns
   - Performance benchmarks
   - Validation suites

7. **[NAUTILUS_INTEGRATION_MASTER_INDEX.md](../../strategy-builder/NAUTILUS_INTEGRATION_MASTER_INDEX.md)**
   - Cross-reference guide
   - Component relationships
   - Integration points
   - Dependency map

8. **[OPTIMIZER_V3_FLOW_DIAGRAM.md](OPTIMIZER_V3_FLOW_DIAGRAM.md)**
   - System architecture
   - UI component flow
   - Data flow patterns
   - Configuration flow
   - Integration points

9. **[OPTIMIZER_V3_CONFIGURATION_SYSTEM.md](../OPTIMIZER_V3_CONFIGURATION_SYSTEM.md)**
   - Configuration hierarchy
   - Runtime behavior
   - Parameter validation
   - Storage management
   - UI integration patterns

## ✅ TASK CHECKLIST

### Core Infrastructure
- [x] 1.1.1 Create NautilusTrader project structure
- [x] 1.1.2 Implement NautilusTrader OptimizerLogger
- [x] 1.1.3 Backtest Progress & Results Panel
- [x] 1.1.4 Implement NautilusTrader DataValidator
- [x] 1.1.5 Create NautilusTrader DependencyGraph

### Parameter Extraction
- [x] 1.1.6 Extract NautilusTrader timing parameters
- [x] 1.1.7 Extract NautilusTrader recheck parameters
- [x] 1.1.8 Extract NautilusTrader risk parameters

### Optimization Space
- [x] 1.1.9 Generate NautilusTrader optimization space
- [x] 1.1.10 Validate NautilusTrader optimization space

### Testing & Documentation
- [x] 1.1.11 Integration tests with NautilusTrader types
- [x] 1.1.12 Unit tests with NautilusTrader types (95% coverage)
- [x] 1.1.13 Sprint 1.1 sign-off

### API Design
- [x] 1.1.14 Design OptimizerV3 API with NautilusTrader
- [x] 1.1.15 Design StrategyAnalyzer API with NautilusTrader
- [x] 1.1.16 Design ParallelExecutor API with NautilusTrader
- [x] 1.1.17 Design ResultsRanker API with NautilusTrader
- [x] 1.1.18 API documentation with NautilusTrader types
- [x] 1.1.19 API versioning strategy with NautilusTrader support

## 📝 TASK DETAILS

### **Environment Configuration**
**Duration**: 1 hour  
**Dependencies**: Sprint 0 complete

**Implementation**:
```bash
# Add to .env file

# Strategy Analysis Configuration
STRATEGY_ANALYSIS_LOG_LEVEL=DEBUG
STRATEGY_ANALYSIS_LOG_FORMAT="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
STRATEGY_ANALYSIS_LOG_PATH=logs/strategy_analysis

# Take Profit Configuration
TP_FIBONACCI_LEVELS=[1.618, 2.618, 3.618]
TP_FIBONACCI_ADJUSTMENT_THRESHOLD=0.01
TP_HYBRID_ATR_MULTIPLIER=2.0
TP_HYBRID_MIN_DISTANCE=0.005
TP_FIXED_DISTANCES=[0.01, 0.02, 0.03]

# Stop Loss Configuration
SL_ADAPTIVE_ATR_PERIOD=14
SL_ADAPTIVE_ATR_MULTIPLIER=2.0
SL_ADAPTIVE_MIN_DISTANCE=0.005
SL_STATIC_DISTANCE=0.01

# Risk Management
RISK_MIN_REWARD_RATIO=2.0
RISK_PERCENT=1.0
RISK_MAX_LEVERAGE=1.0
RISK_MIN_CONFLUENCE=2
RISK_MAX_BARS_HELD=20

# Emergency Stop Loss
EMERGENCY_SL_ENABLED=true
EMERGENCY_SL_THRESHOLD=3.0
EMERGENCY_SL_VOLATILITY_LOOKBACK=14
EMERGENCY_SL_VOLATILITY_MULTIPLIER=2.0

# Optimization Ranges
OPTIMIZATION_RISK_REWARD_MIN=1.5
OPTIMIZATION_RISK_REWARD_MAX=3.0
OPTIMIZATION_RISK_PERCENT_MIN=0.5
OPTIMIZATION_RISK_PERCENT_MAX=2.0
OPTIMIZATION_CONFLUENCE_MIN=1
OPTIMIZATION_CONFLUENCE_MAX=3
OPTIMIZATION_BARS_HELD_MIN=10
OPTIMIZATION_BARS_HELD_MAX=30
OPTIMIZATION_VOLATILITY_MULTIPLIER_MIN=1.5
OPTIMIZATION_VOLATILITY_MULTIPLIER_MAX=2.5
OPTIMIZATION_SL_DISTANCE_MIN=0.003
OPTIMIZATION_SL_DISTANCE_MAX=0.025

# System Resources
CPU_CORES_MIN=1
CPU_CORES_MAX=auto  # Uses all available cores
CPU_AFFINITY_MODE=automatic  # or manual
MEMORY_CHART_HISTORY=60  # seconds
UPDATE_INTERVAL=1000  # milliseconds

# UI Configuration
DARK_THEME_ENABLED=true
CHART_UPDATE_INTERVAL=1000  # milliseconds
PROGRESS_UPDATE_INTERVAL=500  # milliseconds
```

**Configuration Loading**:
```python
from dotenv import load_dotenv
import os
from decimal import Decimal
import json

def get_strategy_config():
    """Load strategy analysis configuration from environment"""
    load_dotenv()
    
    return {
        'logging': {
            'level': os.getenv('STRATEGY_ANALYSIS_LOG_LEVEL'),
            'format': os.getenv('STRATEGY_ANALYSIS_LOG_FORMAT'),
            'path': os.getenv('STRATEGY_ANALYSIS_LOG_PATH')
        },
        'take_profit': {
            'fibonacci': {
                'levels': json.loads(os.getenv('TP_FIBONACCI_LEVELS')),
                'adjustment_threshold': Decimal(os.getenv('TP_FIBONACCI_ADJUSTMENT_THRESHOLD'))
            },
            'hybrid': {
                'atr_multiplier': Decimal(os.getenv('TP_HYBRID_ATR_MULTIPLIER')),
                'min_distance': Decimal(os.getenv('TP_HYBRID_MIN_DISTANCE'))
            },
            'fixed': {
                'distances': json.loads(os.getenv('TP_FIXED_DISTANCES'))
            }
        },
        'stop_loss': {
            'adaptive': {
                'atr_period': int(os.getenv('SL_ADAPTIVE_ATR_PERIOD')),
                'atr_multiplier': Decimal(os.getenv('SL_ADAPTIVE_ATR_MULTIPLIER')),
                'min_distance': Decimal(os.getenv('SL_ADAPTIVE_MIN_DISTANCE'))
            },
            'static': {
                'distance': Decimal(os.getenv('SL_STATIC_DISTANCE'))
            }
        },
        'risk': {
            'min_reward_ratio': Decimal(os.getenv('RISK_MIN_REWARD_RATIO')),
            'risk_percent': Decimal(os.getenv('RISK_PERCENT')),
            'max_leverage': Decimal(os.getenv('RISK_MAX_LEVERAGE')),
            'min_confluence': int(os.getenv('RISK_MIN_CONFLUENCE')),
            'max_bars_held': int(os.getenv('RISK_MAX_BARS_HELD'))
        },
        'emergency_sl': {
            'enabled': os.getenv('EMERGENCY_SL_ENABLED').lower() == 'true',
            'threshold': Decimal(os.getenv('EMERGENCY_SL_THRESHOLD')),
            'volatility_lookback': int(os.getenv('EMERGENCY_SL_VOLATILITY_LOOKBACK')),
            'volatility_multiplier': Decimal(os.getenv('EMERGENCY_SL_VOLATILITY_MULTIPLIER'))
        },
        'optimization': {
            'risk_reward': {
                'min': Decimal(os.getenv('OPTIMIZATION_RISK_REWARD_MIN')),
                'max': Decimal(os.getenv('OPTIMIZATION_RISK_REWARD_MAX'))
            },
            'risk_percent': {
                'min': Decimal(os.getenv('OPTIMIZATION_RISK_PERCENT_MIN')),
                'max': Decimal(os.getenv('OPTIMIZATION_RISK_PERCENT_MAX'))
            },
            'confluence': {
                'min': int(os.getenv('OPTIMIZATION_CONFLUENCE_MIN')),
                'max': int(os.getenv('OPTIMIZATION_CONFLUENCE_MAX'))
            },
            'bars_held': {
                'min': int(os.getenv('OPTIMIZATION_BARS_HELD_MIN')),
                'max': int(os.getenv('OPTIMIZATION_BARS_HELD_MAX'))
            },
            'volatility_multiplier': {
                'min': Decimal(os.getenv('OPTIMIZATION_VOLATILITY_MULTIPLIER_MIN')),
                'max': Decimal(os.getenv('OPTIMIZATION_VOLATILITY_MULTIPLIER_MAX'))
            },
            'sl_distance': {
                'min': Decimal(os.getenv('OPTIMIZATION_SL_DISTANCE_MIN')),
                'max': Decimal(os.getenv('OPTIMIZATION_SL_DISTANCE_MAX'))
            }
        },
        'system': {
            'cpu_cores': {
                'min': int(os.getenv('CPU_CORES_MIN')),
                'max': os.getenv('CPU_CORES_MAX')
            },
            'cpu_affinity': os.getenv('CPU_AFFINITY_MODE'),
            'memory_history': int(os.getenv('MEMORY_CHART_HISTORY')),
            'update_interval': int(os.getenv('UPDATE_INTERVAL'))
        },
        'ui': {
            'dark_theme': os.getenv('DARK_THEME_ENABLED').lower() == 'true',
            'chart_update_interval': int(os.getenv('CHART_UPDATE_INTERVAL')),
            'progress_update_interval': int(os.getenv('PROGRESS_UPDATE_INTERVAL'))
        }
    }
```

### **Task 1.1.1: Create Project Structure**
**Duration**: 30 minutes  
**Dependencies**: Sprint 0 complete

**Implementation**:
```bash
mkdir -p src/optimizer_v3/{core,intelligence,training,testing,ml,ui}
touch src/optimizer_v3/__init__.py
touch src/optimizer_v3/core/__init__.py
touch src/optimizer_v3/intelligence/__init__.py
touch src/optimizer_v3/training/__init__.py
touch src/optimizer_v3/testing/__init__.py
touch src/optimizer_v3/ml/__init__.py
touch src/optimizer_v3/ui/__init__.py
```

**Acceptance Criteria**:
- [ ] All directories exist
- [ ] All `__init__.py` files present
- [ ] Package importable

**Testing**:
```python
def test_package_structure():
    import src.optimizer_v3
    import src.optimizer_v3.core
    assert True
```

**Sign-off**: ☐ Developer ☐ Lead

### **Task 1.1.2: Implement OptimizerLogger**
**Duration**: 2 hours  
**Dependencies**: 1.1.1

**Implementation**:
```python
import logging
import uuid
from datetime import datetime

class OptimizerLogger:
    """Multi-level structured logging"""
    
    def __init__(self, component: str):
        self.component = component
        self.session_id = uuid.uuid4()
        self.start_time = datetime.now()
        
        self.logger = logging.getLogger(f"optimizer_v3.{component}")
        self.logger.setLevel(logging.DEBUG)
        
        fh = logging.FileHandler(
            f'logs/optimizer_v3_{component}_{self.session_id}.log'
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(funcName)s | %(message)s'
        ))
        
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
    
    def debug(self, message: str, **kwargs):
        self.logger.debug(message, extra=kwargs)
    
    def info(self, message: str, **kwargs):
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        self.logger.error(message, extra=kwargs)
```

**Acceptance Criteria**:
- [ ] Logger creates files
- [ ] Session ID unique
- [ ] Console output works
- [ ] Uses STATUS_STYLE from styles.py
- [ ] Uses ERROR_STYLE from styles.py
- [ ] No hardcoded styles
- [ ] Dark theme compatible

**Testing**:
```python
def test_logger_creates_file():
    logger = OptimizerLogger('test')
    logger.info("Test message")
    log_files = [f for f in os.listdir('logs') if 'test' in f]
    assert len(log_files) > 0
```

**Sign-off**: ☐ Developer ☐ Lead

### **Task 1.1.3: Backtest Progress & Results Panel**
**Duration**: 4 hours  
**Dependencies**: 1.1.2

**Implementation**:
```python
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QProgressBar, QTableWidget
from src.strategy_builder.ui.styles import (
    WINDOW_STYLE,
    PANEL_STYLE,
    TABLE_STYLE,
    PROGRESSBAR_STYLE,
    SPACING_UNIT,
    create_font,
    PRIMARY_COLOR,
    SECONDARY_COLOR
)

class FibonacciTPStrategy:
    """Fibonacci-based take profit strategy"""
    
    def __init__(self, levels: List[float], adjustment_threshold: float):
        self.levels = [Decimal(str(level)) for level in levels]
        self.adjustment_threshold = Decimal(str(adjustment_threshold))
    
    def calculate_levels(self, entry_price: Price, position_size: Quantity) -> dict:
        """Calculate TP levels using Fibonacci ratios"""
        return {
            'tp1': Price(str(entry_price.as_decimal() * self.levels[0])),
            'tp2': Price(str(entry_price.as_decimal() * self.levels[1])),
            'tp3': Price(str(entry_price.as_decimal() * self.levels[2]))
        }
    
    def adjust_levels(self, current_price: Price, market_data: dict) -> dict:
        """Adjust TP levels based on market conditions"""
        volatility = Decimal(str(market_data['volatility']))
        if volatility > self.adjustment_threshold:
            return {
                'tp1': volatility * Decimal('0.5'),
                'tp2': volatility * Decimal('0.75'),
                'tp3': volatility
            }
        return {'tp1': Decimal('0'), 'tp2': Decimal('0'), 'tp3': Decimal('0')}

class HybridTPStrategy:
    """Hybrid take profit strategy combining multiple approaches"""
    
    def __init__(self, atr_multiplier: float = 2.0, min_distance: float = 0.005):
        self.atr_multiplier = Decimal(str(atr_multiplier))
        self.min_distance = Decimal(str(min_distance))
    
    def calculate_levels(self, entry_price: Price, position_size: Quantity) -> dict:
        """Calculate TP levels using hybrid approach"""
        base = entry_price.as_decimal()
        return {
            'tp1': Price(str(base * (Decimal('1') + self.min_distance * Decimal('2')))),
            'tp2': Price(str(base * (Decimal('1') + self.min_distance * Decimal('3')))),
            'tp3': Price(str(base * (Decimal('1') + self.min_distance * Decimal('4'))))
        }
    
    def adjust_levels(self, current_price: Price, market_data: dict) -> dict:
        """Adjust TP levels based on ATR and market conditions"""
        atr = Price(str(market_data['atr'])).as_decimal()
        return {
            'tp1': atr * self.atr_multiplier * Decimal('0.5'),
            'tp2': atr * self.atr_multiplier * Decimal('0.75'),
            'tp3': atr * self.atr_multiplier
        }

class FixedTPStrategy:
    """Fixed take profit strategy with static levels"""
    
    def __init__(self, tp1_distance: float, tp2_distance: float, tp3_distance: float):
        self.distances = {
            'tp1': Decimal(str(tp1_distance)),
            'tp2': Decimal(str(tp2_distance)),
            'tp3': Decimal(str(tp3_distance))
        }
    
    def calculate_levels(self, entry_price: Price, position_size: Quantity) -> dict:
        """Calculate TP levels using fixed distances"""
        base = entry_price.as_decimal()
        return {
            'tp1': Price(str(base * (Decimal('1') + self.distances['tp1']))),
            'tp2': Price(str(base * (Decimal('1') + self.distances['tp2']))),
            'tp3': Price(str(base * (Decimal('1') + self.distances['tp3'])))
        }
    
    def adjust_levels(self, current_price: Price, market_data: dict) -> dict:
        """Fixed strategy has no adjustments"""
        return {'tp1': Decimal('0'), 'tp2': Decimal('0'), 'tp3': Decimal('0')}

class AdaptiveSLStrategyV2:
    """Adaptive stop loss strategy v2.0 with dynamic adjustments"""
    
    def __init__(self, atr_period: int = 14, atr_multiplier: float = 2.0, min_distance: float = 0.005):
        self.atr_period = atr_period
        self.atr_multiplier = Decimal(str(atr_multiplier))
        self.min_distance = Decimal(str(min_distance))
    
    def calculate_level(self, entry_price: Price, position_size: Quantity) -> Price:
        """Calculate initial SL level"""
        return Price(str(entry_price.as_decimal() * (Decimal('1') - self.min_distance)))
    
    def adjust_level(self, current_price: Price, market_data: dict) -> Price:
        """Adjust SL level based on ATR and market conditions"""
        atr = Price(str(market_data['atr'])).as_decimal()
        volatility = Decimal(str(market_data['volatility']))
        
        # Dynamic adjustment based on both ATR and volatility
        adjustment = (atr * self.atr_multiplier + volatility) / Decimal('2')
        return Price(str(current_price.as_decimal() * (Decimal('1') - adjustment)))

class StaticSLStrategy:
    """Static stop loss strategy with fixed distance"""
    
    def __init__(self, distance: float):
        self.distance = Decimal(str(distance))
    
    def calculate_level(self, entry_price: Price, position_size: Quantity) -> Price:
        """Calculate SL level using fixed distance"""
        return Price(str(entry_price.as_decimal() * (Decimal('1') - self.distance)))
    
    def adjust_level(self, current_price: Price, market_data: dict) -> Price:
        """Static strategy has no adjustments"""
        return current_price

class TPSLConfigurationHandler:
    """Handle TP/SL configuration strategies"""
    
    def __init__(self):
        self.tp_strategy = None
        self.sl_strategy = None
        
    def configure_tp_strategy(self, strategy_type: str, params: dict):
        """Configure take profit strategy"""
        if strategy_type == 'fibonacci':
            self.tp_strategy = FibonacciTPStrategy(**params)
        elif strategy_type == 'hybrid':
            self.tp_strategy = HybridTPStrategy(**params)
        elif strategy_type == 'fixed':
            self.tp_strategy = FixedTPStrategy(**params)
        else:
            raise ValueError(f"Invalid TP strategy type: {strategy_type}")
    
    def configure_sl_strategy(self, strategy_type: str, params: dict):
        """Configure stop loss strategy"""
        if strategy_type == 'adaptive_v2':
            self.sl_strategy = AdaptiveSLStrategyV2(**params)
        elif strategy_type == 'static':
            self.sl_strategy = StaticSLStrategy(**params)
        else:
            raise ValueError(f"Invalid SL strategy type: {strategy_type}")
    
    def calculate_tp_levels(self, entry_price: Price, position_size: Quantity) -> dict:
        """Calculate take profit levels using configured strategy"""
        if not self.tp_strategy:
            raise RuntimeError("TP strategy not configured")
        return self.tp_strategy.calculate_levels(entry_price, position_size)
    
    def calculate_sl_level(self, entry_price: Price, position_size: Quantity) -> Price:
        """Calculate stop loss level using configured strategy"""
        if not self.sl_strategy:
            raise RuntimeError("SL strategy not configured")
        return self.sl_strategy.calculate_level(entry_price, position_size)
    
    def adjust_tp_levels(self, current_price: Price, market_data: dict) -> dict:
        """Adjust take profit levels based on market conditions"""
        if not self.tp_strategy:
            raise RuntimeError("TP strategy not configured")
        return self.tp_strategy.adjust_levels(current_price, market_data)
    
    def adjust_sl_level(self, current_price: Price, market_data: dict) -> Price:
        """Adjust stop loss level based on market conditions"""
        if not self.sl_strategy:
            raise RuntimeError("SL strategy not configured")
        return self.sl_strategy.adjust_level(current_price, market_data)

class SystemHealthTab(QWidget):
    """System health monitoring tab with real-time resource tracking"""
    
    def __init__(self, monitor: ProcessMonitor):
        super().__init__()
        self.monitor = monitor
        self.cpu_series = {}  # Per-core CPU utilization
        self.memory_series = QLineSeries()  # System memory usage
        self.disk_series = QLineSeries()  # Disk I/O
        self.network_series = QLineSeries()  # Network I/O
        self.update_interval = 1000  # 1 second updates
        self.history_points = 60  # 1 minute history
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(SPACING_UNIT)
        
        # CPU Configuration
        cpu_group = QGroupBox("CPU Configuration")
        cpu_group.setStyleSheet(GROUPBOX_STYLE)
        cpu_group.setFont(create_font())
        
        cpu_layout = QVBoxLayout()
        cpu_layout.setSpacing(SPACING_UNIT)
        
        # CPU cores selector
        cores_layout = QHBoxLayout()
        cores_label = QLabel("CPU Cores:")
        cores_label.setStyleSheet(LABEL_STYLE)
        cores_label.setFont(create_font())
        
        self.cores_spinbox = QSpinBox()
        self.cores_spinbox.setStyleSheet(SPINBOX_STYLE)
        self.cores_spinbox.setFont(create_font())
        self.cores_spinbox.setRange(1, mp.cpu_count())
        self.cores_spinbox.setValue(mp.cpu_count())
        self.cores_spinbox.valueChanged.connect(self._on_cores_changed)
        
        cores_layout.addWidget(cores_label)
        cores_layout.addWidget(self.cores_spinbox)
        cores_layout.addStretch()
        
        # CPU affinity
        affinity_layout = QHBoxLayout()
        affinity_label = QLabel("Core Affinity:")
        affinity_label.setStyleSheet(LABEL_STYLE)
        affinity_label.setFont(create_font())
        
        self.affinity_combo = QComboBox()
        self.affinity_combo.setStyleSheet(COMBOBOX_STYLE)
        self.affinity_combo.setFont(create_font())
        self.affinity_combo.addItems(['Automatic', 'Manual'])
        self.affinity_combo.currentTextChanged.connect(self._on_affinity_changed)
        
        affinity_layout.addWidget(affinity_label)
        affinity_layout.addWidget(self.affinity_combo)
        affinity_layout.addStretch()
        
        cpu_layout.addLayout(cores_layout)
        cpu_layout.addLayout(affinity_layout)
        cpu_group.setLayout(cpu_layout)
        layout.addWidget(cpu_group)
        
        # System Monitoring
        monitor_group = QGroupBox("System Monitoring")
        monitor_group.setStyleSheet(GROUPBOX_STYLE)
        monitor_group.setFont(create_font())
        
        monitor_layout = QVBoxLayout()
        monitor_layout.setSpacing(SPACING_UNIT)
        
        # CPU Utilization Chart
        cpu_chart = QChart()
        cpu_chart.setTitle("CPU Utilization per Core")
        cpu_chart.setTheme(QChart.ChartTheme.DarkTheme)
        
        for i in range(mp.cpu_count()):
            series = QLineSeries()
            series.setName(f"Core {i}")
            cpu_chart.addSeries(series)
            self.cpu_series[i] = series
        
        cpu_chart.createDefaultAxes()
        cpu_chart.axes(Qt.Orientation.YAxis)[0].setRange(0, 100)
        
        cpu_view = QChartView(cpu_chart)
        cpu_view.setStyleSheet(CHART_STYLE)
        monitor_layout.addWidget(cpu_view)
        
        # Memory Utilization Chart
        memory_chart = QChart()
        memory_chart.setTitle("Memory Utilization")
        memory_chart.setTheme(QChart.ChartTheme.DarkTheme)
        memory_chart.addSeries(self.memory_series)
        memory_chart.createDefaultAxes()
        memory_chart.axes(Qt.Orientation.YAxis)[0].setRange(0, 100)
        
        memory_view = QChartView(memory_chart)
        memory_view.setStyleSheet(CHART_STYLE)
        monitor_layout.addWidget(memory_view)
        
        # Disk & Network I/O Chart
        io_chart = QChart()
        io_chart.setTitle("I/O Activity")
        io_chart.setTheme(QChart.ChartTheme.DarkTheme)
        io_chart.addSeries(self.disk_series)
        io_chart.addSeries(self.network_series)
        io_chart.createDefaultAxes()
        
        io_view = QChartView(io_chart)
        io_view.setStyleSheet(CHART_STYLE)
        monitor_layout.addWidget(io_view)
        
        monitor_group.setLayout(monitor_layout)
        layout.addWidget(monitor_group)
        
        self.setLayout(layout)
        
        # Start update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_charts)
        self.update_timer.start(self.update_interval)
    
    def _on_cores_changed(self, value: int):
        """Handle CPU cores selection change"""
        if self.monitor:
            self.monitor.max_workers = value
            self.monitor.logger.info(f"Updated worker count to {value} cores")
    
    def _on_affinity_changed(self, mode: str):
        """Handle CPU affinity mode change"""
        if mode == 'Manual':
            # TODO: Add core selection dialog
            self.monitor.logger.info("Manual CPU affinity not yet implemented")
        else:
            # Reset to automatic affinity
            if self.monitor:
                self.monitor.reset_affinity()
    
    def _update_charts(self):
        """Update system health charts"""
        # Update CPU utilization
        cpu_percent = psutil.cpu_percent(percpu=True)
        for i, series in self.cpu_series.items():
            try:
                if series.count() > self.history_points:
                    series.remove(0)
                series.append(series.count(), cpu_percent[i])
            except IndexError:
                continue
        
        # Update memory utilization
        memory_percent = psutil.virtual_memory().percent
        if self.memory_series.count() > self.history_points:
            self.memory_series.remove(0)
        self.memory_series.append(self.memory_series.count(), memory_percent)
        
        # Update disk I/O
        disk_io = psutil.disk_io_counters()
        disk_activity = (disk_io.read_bytes + disk_io.write_bytes) / 1024 / 1024  # MB
        if self.disk_series.count() > self.history_points:
            self.disk_series.remove(0)
        self.disk_series.append(self.disk_series.count(), disk_activity)
        
        # Update network I/O
        net_io = psutil.net_io_counters()
        net_activity = (net_io.bytes_sent + net_io.bytes_recv) / 1024 / 1024  # MB
        if self.network_series.count() > self.history_points:
            self.network_series.remove(0)
        self.network_series.append(self.network_series.count(), net_activity)
    
    def closeEvent(self, event):
        """Clean up on tab close"""
        self.update_timer.stop()
        super().closeEvent(event)

class BacktestConfigurationPanel(QWidget):
    """Backtest configuration panel with complete parameter handling"""
    
    def __init__(self):
        super().__init__()
        # Initialize with default values
        self.starting_capital = Money('1000', 'USD')  # Default $1,000 USD
        self.capital_range = (
            Money('500', 'USD'),     # Minimum $500 considering leverage
            Money('5000000', 'USD')  # Maximum $5M considering leverage
        )
        self.capital_step = {
            'micro': Money('100', 'USD'),      # $100 steps up to $5K
            'small': Money('500', 'USD'),      # $500 steps up to $50K
            'medium': Money('1000', 'USD'),    # $1K steps up to $500K
            'large': Money('5000', 'USD')      # $5K steps above $500K
        }
        self.risk_params = {
            'min_risk_reward': Decimal('2.0'),
            'risk_percent': Decimal('1.0'),
            'leverage': Decimal('1.0'),
            'confluence_required': 2,
            'max_bars_held': 20
        }
        self.stop_loss_params = {
            'delay_bars': 3,
            'emergency_enabled': True,
            'emergency_threshold': Decimal('3.0'),
            'volatility_lookback': 14,
            'volatility_multiplier': Decimal('2.0'),
            'min_distance': Decimal('0.005'),
            'max_distance': Decimal('0.02')
        }
        self.optimizer_enabled = False
        self.setup_ui()
    
    def get_config_for_mode(self, is_optimizer_mode: bool = False) -> dict:
        """Get configuration based on mode"""
        config = {
            'capital': {
                'amount': self.starting_capital,
                'currency': 'USD'
            },
            'risk': {
                'min_risk_reward': self.risk_params['min_risk_reward'],
                'risk_percent': self.risk_params['risk_percent'],
                'leverage': self.risk_params['leverage'],
                'confluence_required': self.risk_params['confluence_required'],
                'max_bars_held': self.risk_params['max_bars_held']
            },
            'stop_loss': {
                'delay_bars': self.stop_loss_params['delay_bars'],
                'emergency_enabled': self.stop_loss_params['emergency_enabled'],
                'emergency_threshold': self.stop_loss_params['emergency_threshold'],
                'volatility_lookback': self.stop_loss_params['volatility_lookback'],
                'volatility_multiplier': self.stop_loss_params['volatility_multiplier'],
                'min_distance': self.stop_loss_params['min_distance'],
                'max_distance': self.stop_loss_params['max_distance']
            }
        }
        
        if is_optimizer_mode:
            # Add optimization ranges
            config['optimization_ranges'] = {
                'capital': {
                    'min': self.capital_range[0],
                    'max': self.capital_range[1],
                    'steps': {
                        (Money('500', 'USD'), Money('5000', 'USD')): self.capital_step['micro'],
                        (Money('5000', 'USD'), Money('50000', 'USD')): self.capital_step['small'],
                        (Money('50000', 'USD'), Money('500000', 'USD')): self.capital_step['medium'],
                        (Money('500000', 'USD'), Money('5000000', 'USD')): self.capital_step['large']
                    }
                },
                'risk_reward': (Decimal('1.5'), Decimal('3.0')),
                'risk_percent': (Decimal('0.5'), Decimal('2.0')),
                'confluence': (1, 3),
                'bars_held': (10, 30),
                'volatility_multiplier': (Decimal('1.5'), Decimal('2.5')),
                'stop_loss_distance': (Decimal('0.003'), Decimal('0.025'))
            }
        
        return config
    
    def set_starting_capital(self, amount: str):
        """Set starting capital amount"""
        try:
            self.starting_capital = Money(amount, 'USD')
        except ValueError as e:
            raise ValueError(f"Invalid starting capital: {str(e)}")
    
    def get_starting_capital(self) -> Money:
        """Get current starting capital"""
        return self.starting_capital
    
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(SPACING_UNIT)
        
        # Risk/Reward Configuration
        risk_reward_group = QGroupBox("Risk/Reward Configuration")
        risk_reward_group.setStyleSheet(GROUPBOX_STYLE)
        risk_reward_layout = QFormLayout()
        risk_reward_layout.setSpacing(SPACING_UNIT)
        
        # Min Risk/Reward
        self.min_rr_input = QDoubleSpinBox()
        self.min_rr_input.setStyleSheet(INPUT_STYLE)
        self.min_rr_input.setFont(create_font())
        self.min_rr_input.setRange(1.0, 5.0)
        self.min_rr_input.setValue(float(self.risk_params['min_risk_reward']))
        self.min_rr_input.valueChanged.connect(
            lambda v: self._update_risk_param('min_risk_reward', v)
        )
        risk_reward_layout.addRow("Min Risk/Reward:", self.min_rr_input)
        
        # Risk Percent
        self.risk_percent_input = QDoubleSpinBox()
        self.risk_percent_input.setStyleSheet(INPUT_STYLE)
        self.risk_percent_input.setFont(create_font())
        self.risk_percent_input.setRange(0.1, 5.0)
        self.risk_percent_input.setValue(float(self.risk_params['risk_percent']))
        self.risk_percent_input.valueChanged.connect(
            lambda v: self._update_risk_param('risk_percent', v)
        )
        risk_reward_layout.addRow("Risk %:", self.risk_percent_input)
        
        # Leverage
        self.leverage_input = QDoubleSpinBox()
        self.leverage_input.setStyleSheet(INPUT_STYLE)
        self.leverage_input.setFont(create_font())
        self.leverage_input.setRange(1.0, 10.0)
        self.leverage_input.setValue(float(self.risk_params['leverage']))
        self.leverage_input.valueChanged.connect(
            lambda v: self._update_risk_param('leverage', v)
        )
        risk_reward_layout.addRow("Leverage:", self.leverage_input)
        
        # Confluence Required
        self.confluence_input = QSpinBox()
        self.confluence_input.setStyleSheet(INPUT_STYLE)
        self.confluence_input.setFont(create_font())
        self.confluence_input.setRange(1, 5)
        self.confluence_input.setValue(self.risk_params['confluence_required'])
        self.confluence_input.valueChanged.connect(
            lambda v: self._update_risk_param('confluence_required', v)
        )
        risk_reward_layout.addRow("Confluence Required:", self.confluence_input)
        
        # Max Bars Held
        self.max_bars_input = QSpinBox()
        self.max_bars_input.setStyleSheet(INPUT_STYLE)
        self.max_bars_input.setFont(create_font())
        self.max_bars_input.setRange(5, 50)
        self.max_bars_input.setValue(self.risk_params['max_bars_held'])
        self.max_bars_input.valueChanged.connect(
            lambda v: self._update_risk_param('max_bars_held', v)
        )
        risk_reward_layout.addRow("Max Bars Held:", self.max_bars_input)
        
        risk_reward_group.setLayout(risk_reward_layout)
        layout.addWidget(risk_reward_group)
        
        # Stop Loss Configuration
        sl_group = QGroupBox("Stop Loss Configuration")
        sl_group.setStyleSheet(GROUPBOX_STYLE)
        sl_layout = QFormLayout()
        sl_layout.setSpacing(SPACING_UNIT)
        
        # Stop Loss Delay
        self.sl_delay_input = QSpinBox()
        self.sl_delay_input.setStyleSheet(INPUT_STYLE)
        self.sl_delay_input.setFont(create_font())
        self.sl_delay_input.setRange(0, 10)
        self.sl_delay_input.setValue(self.stop_loss_params['delay_bars'])
        self.sl_delay_input.valueChanged.connect(
            lambda v: self._update_sl_param('delay_bars', v)
        )
        sl_layout.addRow("Stop Loss Delay (bars):", self.sl_delay_input)
        
        # Emergency Stop Loss
        self.emergency_sl_check = QCheckBox()
        self.emergency_sl_check.setStyleSheet(CHECKBOX_STYLE)
        self.emergency_sl_check.setFont(create_font())
        self.emergency_sl_check.setChecked(self.stop_loss_params['emergency_enabled'])
        self.emergency_sl_check.stateChanged.connect(
            lambda v: self._update_sl_param('emergency_enabled', bool(v))
        )
        sl_layout.addRow("Emergency Stop Loss:", self.emergency_sl_check)
        
        # Emergency Threshold
        self.emergency_threshold_input = QDoubleSpinBox()
        self.emergency_threshold_input.setStyleSheet(INPUT_STYLE)
        self.emergency_threshold_input.setFont(create_font())
        self.emergency_threshold_input.setRange(1.0, 5.0)
        self.emergency_threshold_input.setValue(float(self.stop_loss_params['emergency_threshold']))
        self.emergency_threshold_input.valueChanged.connect(
            lambda v: self._update_sl_param('emergency_threshold', v)
        )
        sl_layout.addRow("Emergency Threshold:", self.emergency_threshold_input)
        
        # Volatility Settings
        self.vol_lookback_input = QSpinBox()
        self.vol_lookback_input.setStyleSheet(INPUT_STYLE)
        self.vol_lookback_input.setFont(create_font())
        self.vol_lookback_input.setRange(5, 30)
        self.vol_lookback_input.setValue(self.stop_loss_params['volatility_lookback'])
        self.vol_lookback_input.valueChanged.connect(
            lambda v: self._update_sl_param('volatility_lookback', v)
        )
        sl_layout.addRow("Volatility Lookback:", self.vol_lookback_input)
        
        self.vol_multiplier_input = QDoubleSpinBox()
        self.vol_multiplier_input.setStyleSheet(INPUT_STYLE)
        self.vol_multiplier_input.setFont(create_font())
        self.vol_multiplier_input.setRange(1.0, 4.0)
        self.vol_multiplier_input.setValue(float(self.stop_loss_params['volatility_multiplier']))
        self.vol_multiplier_input.valueChanged.connect(
            lambda v: self._update_sl_param('volatility_multiplier', v)
        )
        sl_layout.addRow("Volatility Multiplier:", self.vol_multiplier_input)
        
        # Stop Loss Distance Limits
        self.min_sl_input = QDoubleSpinBox()
        self.min_sl_input.setStyleSheet(INPUT_STYLE)
        self.min_sl_input.setFont(create_font())
        self.min_sl_input.setDecimals(4)
        self.min_sl_input.setRange(0.0001, 0.01)
        self.min_sl_input.setValue(float(self.stop_loss_params['min_distance']))
        self.min_sl_input.valueChanged.connect(
            lambda v: self._update_sl_param('min_distance', v)
        )
        sl_layout.addRow("Min Stop Loss Distance:", self.min_sl_input)
        
        self.max_sl_input = QDoubleSpinBox()
        self.max_sl_input.setStyleSheet(INPUT_STYLE)
        self.max_sl_input.setFont(create_font())
        self.max_sl_input.setDecimals(4)
        self.max_sl_input.setRange(0.001, 0.05)
        self.max_sl_input.setValue(float(self.stop_loss_params['max_distance']))
        self.max_sl_input.valueChanged.connect(
            lambda v: self._update_sl_param('max_distance', v)
        )
        sl_layout.addRow("Max Stop Loss Distance:", self.max_sl_input)
        
        sl_group.setLayout(sl_layout)
        layout.addWidget(sl_group)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: " + SECONDARY_COLOR)
        layout.addWidget(separator)
        
        # Starting Capital Group
        capital_group = QGroupBox("Starting Capital")
        capital_group.setStyleSheet(GROUPBOX_STYLE)
        capital_layout = QFormLayout()
        capital_layout.setSpacing(SPACING_UNIT)
        
        self.capital_input = QLineEdit()
        self.capital_input.setStyleSheet(INPUT_STYLE)
        self.capital_input.setFont(create_font())
        self.capital_input.setText(str(self.starting_capital.as_decimal()))
        self.capital_input.textChanged.connect(self._on_capital_changed)
        
        capital_layout.addRow("Amount (USD):", self.capital_input)
        capital_group.setLayout(capital_layout)
        layout.addWidget(capital_group)
        
        self.setLayout(layout)
    
    def _update_risk_param(self, param: str, value: float):
        """Update risk parameter"""
        self.risk_params[param] = Decimal(str(value))
    
    def _update_sl_param(self, param: str, value: Union[float, bool, int]):
        """Update stop loss parameter"""
        if isinstance(value, bool):
            self.stop_loss_params[param] = value
        else:
            self.stop_loss_params[param] = Decimal(str(value))
    
    def _on_capital_changed(self, text: str):
        """Handle starting capital input changes"""
        try:
            amount = Decimal(text)
            if amount < self.capital_range[0].as_decimal():
                raise ValueError(f"Capital must be at least {self.capital_range[0]}")
            if amount > self.capital_range[1].as_decimal():
                raise ValueError(f"Capital cannot exceed {self.capital_range[1]}")
            
            self.set_starting_capital(text)
            self.capital_input.setStyleSheet(INPUT_STYLE)
            
            # Update tooltip with valid range
            self.capital_input.setToolTip(
                f"Valid range: {self.capital_range[0]} - {self.capital_range[1]}"
            )
        except ValueError as e:
            self.capital_input.setStyleSheet(INPUT_ERROR_STYLE)
            self.capital_input.setToolTip(str(e))
    
    def set_optimizer_mode(self, enabled: bool):
        """Enable/disable optimizer mode"""
        self.optimizer_enabled = enabled
        # Update UI elements based on mode
        self.capital_input.setEnabled(not enabled)  # Lock capital input in optimizer mode
        self.min_rr_input.setEnabled(not enabled)
        self.risk_percent_input.setEnabled(not enabled)
        self.leverage_input.setEnabled(not enabled)
        self.confluence_input.setEnabled(not enabled)
        self.max_bars_input.setEnabled(not enabled)
        self.vol_multiplier_input.setEnabled(not enabled)
        self.min_sl_input.setEnabled(not enabled)
        self.max_sl_input.setEnabled(not enabled)

class BacktestProgressPanel(QWidget):
    """Real-time backtest progress tracking with TP/SL configuration handling"""
    
    # TP/SL Configuration Types
    TP_CONFIG_TYPES = {
        'FIBONACCI': 'fibonacci',
        'HYBRID': 'hybrid',
        'FIXED': 'fixed'
    }
    
    SL_CONFIG_TYPES = {
        'ADAPTIVE_V2': 'adaptive_v2',
        'STATIC': 'static'
    }
    
    def __init__(self, config_panel: BacktestConfigurationPanel):
        super().__init__()
        self.tp_config = self.TP_CONFIG_TYPES['FIBONACCI']  # Default
        self.sl_config = self.SL_CONFIG_TYPES['ADAPTIVE_V2']  # Default
        self.config_handler = TPSLConfigurationHandler()
        self.config_panel = config_panel
        self.setup_ui()
        
        # Configure default strategies
        self.config_handler.configure_tp_strategy('fibonacci', {
            'levels': [1.618, 2.618, 3.618],
            'adjustment_threshold': 0.01
        })
        self.config_handler.configure_sl_strategy('adaptive_v2', {
            'atr_period': 14,
            'atr_multiplier': 2.0,
            'min_distance': 0.005
        })
        
    def set_tp_config(self, config_type: str):
        """Set take profit configuration type"""
        if config_type not in self.TP_CONFIG_TYPES.values():
            raise ValueError(f"Invalid TP config type: {config_type}")
        self.tp_config = config_type
        
    def set_sl_config(self, config_type: str):
        """Set stop loss configuration type"""
        if config_type not in self.SL_CONFIG_TYPES.values():
            raise ValueError(f"Invalid SL config type: {config_type}")
        self.sl_config = config_type
    
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(SPACING_UNIT)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(PROGRESSBAR_STYLE)
        self.progress_bar.setFont(create_font())
        layout.addWidget(self.progress_bar)
        
        # Results panel
        self.results_table = QTableWidget()
        self.results_table.setStyleSheet(TABLE_STYLE)
        self.results_table.setFont(create_font())
        
        # Set up columns
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels([
            'Metric', 'Current', 'Best', 'Change'
        ])
        
        # Add rows for metrics
        metrics = [
            'Candles Processed',
            'Trades Executed',
            'Current TP1',
            'Current TP2',
            'Current TP3',
            'Current SL',
            'Win Rate',
            'Profit Factor'
        ]
        self.results_table.setRowCount(len(metrics))
        for i, metric in enumerate(metrics):
            self.results_table.setItem(i, 0, QTableWidgetItem(metric))
        
        layout.addWidget(self.results_table)
        self.setLayout(layout)
    
    def update_progress(self, current: int, total: int):
        """Update progress bar"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
    
    def update_results(self, results: dict):
        """Update results panel with latest metrics and TP/SL configurations"""
        # Update candles processed
        self._update_metric(0, str(results['candles_processed']))
        
        # Update trades executed
        self._update_metric(1, str(results['trades_executed']))
        
        # Update take profit levels with adjustments and configuration
        if 'tp_adjustments' in results:
            tp_adj = results['tp_adjustments']
            config_label = f"[{self.tp_config.upper()}]"
            self._update_metric(2, f"{config_label} TP1: {results['current_tp1']:.2f} ({tp_adj['tp1']:+.2f})")
            self._update_metric(3, f"{config_label} TP2: {results['current_tp2']:.2f} ({tp_adj['tp2']:+.2f})")
            self._update_metric(4, f"{config_label} TP3: {results['current_tp3']:.2f} ({tp_adj['tp3']:+.2f})")
        else:
            config_label = f"[{self.tp_config.upper()}]"
            self._update_metric(2, f"{config_label} TP1: {results['current_tp1']:.2f}")
            self._update_metric(3, f"{config_label} TP2: {results['current_tp2']:.2f}")
            self._update_metric(4, f"{config_label} TP3: {results['current_tp3']:.2f}")
        
        # Update stop loss with adjustment and configuration
        if 'sl_adjustment' in results:
            config_label = f"[{self.sl_config.upper()}]"
            self._update_metric(5, f"{config_label} SL: {results['current_sl']:.2f} ({results['sl_adjustment']:+.2f})")
        else:
            config_label = f"[{self.sl_config.upper()}]"
            self._update_metric(5, f"{config_label} SL: {results['current_sl']:.2f}")
        
        # Update performance metrics
        self._update_metric(6, f"{results['win_rate']:.2%}")
        self._update_metric(7, f"{results['profit_factor']:.2f}")
        
        # Color code adjustments
        if 'tp_adjustments' in results:
            for i, level in enumerate(['tp1', 'tp2', 'tp3']):
                if results['tp_adjustments'][level] > 0:
                    self._set_row_color(i + 2, PRIMARY_COLOR)
                elif results['tp_adjustments'][level] < 0:
                    self._set_row_color(i + 2, SECONDARY_COLOR)
        
        if 'sl_adjustment' in results:
            if results['sl_adjustment'] > 0:
                self._set_row_color(5, PRIMARY_COLOR)
            elif results['sl_adjustment'] < 0:
                self._set_row_color(5, SECONDARY_COLOR)
        
        # Update best values and changes
        for i in range(self.results_table.rowCount()):
            metric = self.results_table.item(i, 0).text()
            if metric in results['best']:
                self._update_metric(i, str(results['best'][metric]), column=2)
                
                # Calculate and show change
                current = float(self.results_table.item(i, 1).text())
                best = float(results['best'][metric])
                change = ((current - best) / best) * 100
                self._update_metric(i, f"{change:+.2f}%", column=3)
    
    def _update_metric(self, row: int, value: str, column: int = 1):
        """Update a specific metric in the results table"""
        item = QTableWidgetItem(value)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.results_table.setItem(row, column, item)
    
    def _set_row_color(self, row: int, color: str):
        """Set the background color for a row to indicate adjustment"""
        for col in range(self.results_table.columnCount()):
            item = self.results_table.item(row, col)
            if item:
                item.setBackground(QColor(color))
```

**Testing**:
```python
def test_tpsl_configuration_handler():
    """Test TP/SL configuration handler"""
    handler = TPSLConfigurationHandler()
    
    # Test TP strategy configuration
    handler.configure_tp_strategy('fibonacci', {
        'levels': [1.618, 2.618, 3.618],
        'adjustment_threshold': 0.01
    })
    
    # Test SL strategy configuration
    handler.configure_sl_strategy('adaptive_v2', {
        'atr_period': 14,
        'atr_multiplier': 2.0,
        'min_distance': 0.005
    })
    
    # Test invalid configurations
    with pytest.raises(ValueError):
        handler.configure_tp_strategy('invalid', {})
    with pytest.raises(ValueError):
        handler.configure_sl_strategy('invalid', {})
    
    # Test calculations
    entry_price = Price('50000')
    position_size = Quantity('1.0')
    market_data = {
        'atr': Price('500'),
        'volume': Quantity('100'),
        'volatility': Decimal('0.02')
    }
    
    # Test TP calculations
    tp_levels = handler.calculate_tp_levels(entry_price, position_size)
    assert len(tp_levels) == 3
    assert all(isinstance(level, Price) for level in tp_levels.values())
    
    # Test SL calculations
    sl_level = handler.calculate_sl_level(entry_price, position_size)
    assert isinstance(sl_level, Price)
    
    # Test adjustments
    current_price = Price('50100')
    tp_adjustments = handler.adjust_tp_levels(current_price, market_data)
    assert len(tp_adjustments) == 3
    
    sl_adjustment = handler.adjust_sl_level(current_price, market_data)
    assert isinstance(sl_adjustment, Price)

def test_system_health_tab():
    """Test system health tab functionality"""
    monitor = ProcessMonitor(OptimizerLogger('test'))
    tab = SystemHealthTab(monitor)
    
    # Test CPU cores configuration
    assert tab.cores_spinbox.minimum() == 1
    assert tab.cores_spinbox.maximum() == mp.cpu_count()
    assert tab.cores_spinbox.value() == mp.cpu_count()
    
    # Test CPU affinity
    assert tab.affinity_combo.currentText() == 'Automatic'
    tab.affinity_combo.setCurrentText('Manual')
    assert tab.affinity_combo.currentText() == 'Manual'
    
    # Test chart initialization
    assert len(tab.cpu_series) == mp.cpu_count()
    assert isinstance(tab.memory_series, QLineSeries)
    assert isinstance(tab.disk_series, QLineSeries)
    assert isinstance(tab.network_series, QLineSeries)
    
    # Test chart updates
    tab._update_charts()
    for series in tab.cpu_series.values():
        assert series.count() > 0
    assert tab.memory_series.count() > 0
    assert tab.disk_series.count() > 0
    assert tab.network_series.count() > 0
    
    # Test cleanup
    tab.close()
    assert not tab.update_timer.isActive()

def test_backtest_configuration_panel():
    """Test backtest configuration panel"""
    panel = BacktestConfigurationPanel()
    
    # Test starting capital
    panel.set_starting_capital('20000')
    assert panel.get_starting_capital() == Money('20000', 'USD')
    
    # Test capital range validation
    with pytest.raises(ValueError):
        panel.set_starting_capital('1000')  # Below min
    
    # Test large institutional positions
    panel.set_starting_capital('50000000')  # $50M should be valid
    assert panel.get_starting_capital() == Money('50000000', 'USD')
    
    # Test maximum capital
    with pytest.raises(ValueError):
        panel.set_starting_capital('200000000')  # Above $100M max
    
    # Test optimizer mode
    panel.set_optimizer_mode(True)
    config = panel.get_config_for_mode(is_optimizer_mode=True)
    assert 'capital' in config['optimization_ranges']
    assert config['optimization_ranges']['capital']['min'] == Money('5000', 'USD')
    assert config['optimization_ranges']['capital']['max'] == Money('100000000', 'USD')
    
    # Test step sizes for different ranges
    steps = config['optimization_ranges']['capital']['steps']
    assert steps[(Money('500', 'USD'), Money('5000', 'USD'))] == Money('100', 'USD')
    assert steps[(Money('5000', 'USD'), Money('50000', 'USD'))] == Money('500', 'USD')
    assert steps[(Money('50000', 'USD'), Money('500000', 'USD'))] == Money('1000', 'USD')
    assert steps[(Money('500000', 'USD'), Money('5000000', 'USD'))] == Money('5000', 'USD')
    
    # Test UI state in optimizer mode
    assert not panel.capital_input.isEnabled()
    
    # Test invalid capital
    with pytest.raises(ValueError):
        panel.set_starting_capital('invalid')
    
    # Test UI updates
    panel.capital_input.setText('30000')
    assert panel.get_starting_capital() == Money('30000', 'USD')
    
    # Test invalid UI input
    panel.capital_input.setText('invalid')
    assert panel.capital_input.styleSheet() == INPUT_ERROR_STYLE

def test_backtest_progress_panel():
    """Test progress panel functionality with TP/SL configurations"""
    config_panel = BacktestConfigurationPanel()
    panel = BacktestProgressPanel(config_panel)
    
    # Test progress updates
    panel.update_progress(50, 100)
    assert panel.progress_bar.value() == 50
    assert panel.progress_bar.maximum() == 100
    
    # Test TP/SL configuration
    panel.set_tp_config('fibonacci')
    panel.set_sl_config('adaptive_v2')
    
    # Test invalid configurations
    with pytest.raises(ValueError):
        panel.set_tp_config('invalid')
    with pytest.raises(ValueError):
        panel.set_sl_config('invalid')
    
    # Test results updates with configurations
    results = {
        'candles_processed': 1000,
        'trades_executed': 25,
        'current_tp1': 50100.0,
        'current_tp2': 50200.0,
        'current_tp3': 50300.0,
        'current_sl': 49800.0,
        'win_rate': 0.65,
        'profit_factor': 2.5,
        'best': {
            'win_rate': 0.70,
            'profit_factor': 2.8
        }
    }
    panel.update_results(results)
    
    # Verify table contents
    assert panel.results_table.item(0, 1).text() == '1000'
    assert panel.results_table.item(6, 1).text() == '65.00%'
    assert panel.results_table.item(6, 2).text() == '0.70'
    assert float(panel.results_table.item(6, 3).text().strip('%')) < 0
```

**Acceptance Criteria**:
- [ ] Progress bar updates in real-time
- [ ] Results panel shows all required metrics
- [ ] Take profit levels (TP1, TP2, TP3) displayed
- [ ] Stop loss level displayed
- [ ] Candles processed counter
- [ ] Trade execution counter
- [ ] Performance metrics updated live
- [ ] Best values tracked and displayed
- [ ] Changes calculated and shown
- [ ] Uses PROGRESSBAR_STYLE from styles.py
- [ ] Uses TABLE_STYLE from styles.py
- [ ] Proper spacing from SPACING_UNIT
- [ ] Consistent fonts using create_font
- [ ] Dark theme compatible
- [ ] No hardcoded styles
- [ ] Visual match with Window 1-4

**Sign-off**: ☐ Developer ☐ Lead ☐ UI Designer

### **Task 1.1.4: Implement DataValidator**
**Duration**: 2 hours  
**Dependencies**: 1.1.2

**Implementation**: See [NAUTILUS_STRATEGY_STRUCTURE_INTEGRATION.md](../../strategy-builder/NAUTILUS_STRATEGY_STRUCTURE_INTEGRATION.md) for complete implementation.

**Acceptance Criteria**:
- [ ] Detects missing fields
- [ ] Validates ranges
- [ ] Raises exceptions
- [ ] Validates NautilusTrader types
- [ ] Handles type conversion errors
- [ ] Validates trade events
- [ ] Validates positions
- [ ] Validates risk metrics

**Testing**:
```python
def test_validation_detects_missing():
    validator = DataValidator(OptimizerLogger('test'))
    invalid = {'timestamp': '2025-01-01'}
    with pytest.raises(ValidationError):
        validator.validate_training_event(invalid)
```

**Sign-off**: ☐ Developer ☐ Lead

### **Task 1.1.4: Create DependencyGraph**
**Duration**: 3 hours  
**Dependencies**: 1.1.2

**Implementation**: See [NAUTILUS_STRATEGY_STRUCTURE_INTEGRATION.md](../../strategy-builder/NAUTILUS_STRATEGY_STRUCTURE_INTEGRATION.md) for complete implementation.

**Acceptance Criteria**:
- [ ] Parses strategies
- [ ] Identifies anchors
- [ ] Detects cycles

**Testing**:
```python
def test_build_graph():
    strategy = {
        "name": "HOD Rejection",
        "blocks": [{
            "name": "hod",
            "signals": [{"name": "HOD_REJECTION"}]
        }]
    }
    graph = DependencyGraph(OptimizerLogger('test'))
    graph.build_from_strategy(strategy)
    assert len(graph.nodes) == 1
```

**Sign-off**: ☐ Developer ☐ Lead

### **Task 1.1.5: Extract Timing Parameters**
**Duration**: 2 hours  
**Dependencies**: 1.1.4

**Implementation**: See [NAUTILUS_STRATEGY_STRUCTURE_INTEGRATION.md](../../strategy-builder/NAUTILUS_STRATEGY_STRUCTURE_INTEGRATION.md) for complete implementation.

**Acceptance Criteria**:
- [ ] Extracts all timing constraints
- [ ] Generates ranges

**Testing**:
```python
def test_extract_timing():
    strategy = {"blocks": [{"name": "rsi", "signals": [
        {"name": "OVERBOUGHT", "timing_constraint": {"max_candles": 20}}
    ]}]}
    analyzer = StrategyAnalyzer()
    params = analyzer.extract_timing_parameters(strategy)
    assert len(params) == 1
    assert params[0]['min'] == 10
```

**Sign-off**: ☐ Developer ☐ Lead

### **Task 1.1.6: Extract Recheck Parameters**
**Duration**: 2 hours  
**Dependencies**: 1.1.5

**Implementation**: See [NAUTILUS_STRATEGY_STRUCTURE_INTEGRATION.md](../../strategy-builder/NAUTILUS_STRATEGY_STRUCTURE_INTEGRATION.md) for complete implementation.

**Acceptance Criteria**:
- [ ] Extracts recheck configs

**Testing**:
```python
def test_extract_recheck():
    strategy = {"blocks": [{"name": "test", "recheck": {"max_bars": 10}}]}
    params = StrategyAnalyzer().extract_recheck_parameters(strategy)
    assert len(params) == 1
```

**Sign-off**: ☐ Developer ☐ Lead

### **Task 1.1.7: Extract Risk Parameters**
**Duration**: 1.5 hours  
**Dependencies**: 1.1.6

**Implementation**: See [NAUTILUS_BACKTEST_CONFIG_INTEGRATION.md](../../strategy-builder/NAUTILUS_BACKTEST_CONFIG_INTEGRATION.md) for complete implementation.

**Acceptance Criteria**:
- [ ] Extracts risk parameters

**Sign-off**: ☐ Developer ☐ Lead

### **Task 1.1.8: Generate Optimization Space**
**Duration**: 3 hours  
**Dependencies**: 1.1.7

**Implementation**: See [NAUTILUS_BACKTEST_CONFIG_INTEGRATION.md](../../strategy-builder/NAUTILUS_BACKTEST_CONFIG_INTEGRATION.md) for complete implementation.

**Acceptance Criteria**:
- [ ] Generates configs
- [ ] Limits to max

**Sign-off**: ☐ Developer ☐ Lead

### **Task 1.1.9: Validate Optimization Space**
**Duration**: 2 hours  
**Dependencies**: 1.1.8

**Implementation**: See [NAUTILUS_BACKTEST_CONFIG_INTEGRATION.md](../../strategy-builder/NAUTILUS_BACKTEST_CONFIG_INTEGRATION.md) for complete implementation.

**Acceptance Criteria**:
- [ ] Detects invalid combos

**Sign-off**: ☐ Developer ☐ Lead

### **Task 1.1.10: Integration Tests**
**Duration**: 2 hours  
**Dependencies**: 1.1.9

**Testing**:
```python
def test_full_analysis():
    strategy = load_sample_strategy('hod_rejection.json')
    analyzer = StrategyAnalyzer(OptimizerLogger('test'))
    params = analyzer.extract_all_parameters(strategy)
    assert len(params) > 0
    configs = analyzer.generate_optimization_space(params)
    assert analyzer.validate_optimization_space(configs)
```

**Sign-off**: ☐ Developer ☐ Lead

### **Task 1.1.11: Unit Tests (95% Coverage)**
**Duration**: 3 hours  
**Dependencies**: 1.1.10

**Implementation**: Comprehensive test suite

**Acceptance Criteria**:
- [ ] 95%+ coverage

**Sign-off**: ☐ Developer ☐ Lead

### **Task 1.1.12: Sprint 1.1 Sign-off**
**Duration**: 1 hour  
**Dependencies**: 1.1.11

**Checklist**:
- [ ] All 18 tasks complete
- [ ] Tests passing

**Sign-off**: ☐ Developer ☐ Lead ☐ Architect

### **Task 1.1.13-1.1.18: API Design**
**Duration**: 12 hours total  
**Dependencies**: 1.1.12

**Tasks**:
- 1.1.13: OptimizerV3 API design
- 1.1.14: StrategyAnalyzer API
- 1.1.15: ParallelExecutor API
- 1.1.16: ResultsRanker API
- 1.1.17: API documentation
- 1.1.18: Versioning strategy

**Deliverables**:
- `docs/v3/optimizer/API_DESIGN.md`
- `docs/v3/optimizer/API_REFERENCE.md`
- `docs/v3/optimizer/api_versioning.md`

**Sign-off**: ☐ Developer ☐ Lead ☐ Architect

## 🎯 SPRINT SIGN-OFF

**Complete When**:
- [ ] All 18 tasks done
- [ ] 95%+ coverage
- [ ] API designed
- [ ] Documentation complete
- [ ] All integration documents referenced
- [ ] All NautilusTrader types validated

**Sign-off**: ☐ Developer ☐ Lead ☐ Architect

**Next Sprint**: `SPRINT_1_2_PARALLEL_EXECUTION.md`
