# SPRINT 2.1: AUTOMATED TRAINER (New Tab (Automated Trainer))
**Forward-Looking Analysis, Training Database, Optimal Parameters**

> **Superseded by BTCAAAAA-338:** The "⚙️ Calibrate" tab introduced in this
> sprint has been **removed** from `BacktestConfigDialog`. Calibration is now
> automatic — it runs when the user clicks "▶️ Run Test" (see
> `BacktestConfigPanel._run_auto_calibration()`). `TrainingPanelUI` is
> preserved in `src/optimizer_v3/ui/training_panel.py` but is no longer
> embedded in the main backtest dialog. This document is a historical record.

**Duration**: 12 days  
**Tasks**: 25  
**Dependencies**: Phase 1 complete  
**Status**: ☐ Not Started

**Design Reference**: `docs/v3/UI-UX/OPTIMIZER_V3_AUTOMATED_TRAINER.md` (COMPLETE DOCUMENT)

**Integration Documents**:
1. **[OPTIMIZER_V3_UI_STYLING_GUIDE.md](../OPTIMIZER_V3_UI_STYLING_GUIDE.md)**
   - Central stylesheet enforcement
   - Zero hardcoded styles
   - Style constants and helpers
   - Dark theme support
   - Style validation
   - Pre-commit hooks

2. **[OPTIMIZER_V3_CONFIGURATION_SYSTEM.md](../OPTIMIZER_V3_CONFIGURATION_SYSTEM.md)**
   - Configuration hierarchy
   - Runtime behavior
   - Parameter validation
   - Storage management
   - UI integration patterns

3. **[OPTIMIZER_V3_FLOW_DIAGRAM.md](OPTIMIZER_V3_FLOW_DIAGRAM.md)**
   - System architecture
   - UI component flow
   - Data flow patterns
   - Configuration flow
   - Integration points

---

## 📋 SPRINT OVERVIEW

**Purpose**: Build automated training system (NEW Tab after AI Recommendation):
- Forward-looking signal analysis
- Training database for historical signals
- Optimal parameter calculator
- Standalone training UI

**Critical Success Factors**:
- 100% NautilusTrader type coverage
- Zero hardcoded styles
- Dark theme compatible using styles.py
- Visual consistency with Window 1-3 and Config, Live Output, Trades, Metrics, AI Recommendations tabs
- All styles from styles.py
- Proper spacing and alignment
- Responsive UI updates
- Memory efficient
- Log file based on existing Debug Log and Log Viewer system

**Design Reference Sections**:
- UI Design: Section "New Tab: Training Panel UI"
- Implementation: Section "Implementation"
- Database: Section "Training Database Schema"
- Calculator: Section "Optimal Parameter Calculator"

---

## ✅ TASK CHECKLIST

- [x] 2.1.0 Environment Configuration (.env setup)
- [x] 2.1.1 Create TrainingPanelUI (New Tab)
- [x] 2.1.2 Block selection with BlockRegistry
- [x] 2.1.3 Mode selection (Testing/Production)
- [x] 2.1.4 Period selection dropdown
- [x] 2.1.5 Timeframe checkboxes
- [x] 2.1.6 Resource estimator & monitoring
- [x] 2.1.7 Confirmation dialog
- [x] 2.1.8 NautilusTrainingSystem class
- [x] 2.1.9 Forward behavior analyzer
- [x] 2.1.10 Signal recurrence detector
- [x] 2.1.11 Price movement tracker
- [x] 2.1.12 Dependent signal finder
- [x] 2.1.13 Trade outcome analyzer
- [x] 2.1.14 TrainingEvent ORM model
- [x] 2.1.15 Database migration & indexes
- [ ] 2.1.16 Data loading pipeline
- [ ] 2.1.17 Data caching system
- [x] 2.1.18 OptimalParameterCalculator
- [x] 2.1.19 Statistical validation
- [x] 2.1.20 TrainingThread worker
- [x] 2.1.21 Progress tracking UI
- [x] 2.1.22 Results display table
- [x] 2.1.23 Export functionality
- [x] 2.1.24 Complete test suite (100% coverage)
- [x] 2.1.25 Sprint sign-off

---

## 🔄 CODE REUSE OPPORTUNITIES

**CRITICAL DISCOVERY**: Existing `TradesPanel` (`src/optimizer_v3/ui/trades_panel.py`) provides institutional-grade patterns that can be directly adapted for Training Results display.

### **Reusable Components from TradesPanel**

#### **1. Table Infrastructure**
**Source**: `TradesPanel._create_trades_table()`
**Target**: `TrainingResultsTable._init_ui()`

**Reusable Elements**:
- ✅ `QTableWidget` setup with styling
- ✅ `get_table_stylesheet()` for consistent dark theme
- ✅ Alternating row colors
- ✅ Multi-select support (`ExtendedSelection`)
- ✅ Sortable columns
- ✅ Column width configuration
- ✅ Header styling

**Code Similarity**: ~85%

---

#### **2. Numeric Sorting**
**Source**: `NumericTableWidgetItem` class
**Target**: Training results delay/sample size columns

**Reusable Elements**:
- ✅ Custom `__lt__` method for proper numeric comparison
- ✅ Prevents string-based sorting (1, 10, 11, 2, 20... → 1, 2, 10, 11, 20...)
- ✅ Fallback to string comparison for non-numeric

**Code Similarity**: 100% (exact copy)

---

#### **3. Color-Coded Data**
**Source**: `TradesPanel._update_table()` P&L color coding
**Target**: Training confidence score color coding

**Reusable Pattern**:
```python
# TradesPanel pattern (P&L):
if float(pnl) > 0:
    item.setForeground(QColor(get_color('success')))  # Green
elif float(pnl) < 0:
    item.setForeground(QColor(get_color('error')))    # Red

# Training adaptation (Confidence):
if confidence >= 0.8:
    item.setForeground(QColor(get_color('success')))  # Green: High
elif confidence >= 0.5:
    item.setForeground(QColor(get_color('warning')))  # Yellow: Medium
else:
    item.setForeground(QColor(get_color('error')))    # Red: Low
```

**Code Similarity**: ~90% (same logic, different thresholds)

---

#### **4. Real-Time Data Updates**
**Source**: `TradesPanel.add_trade()` and `update_trade()`
**Target**: `TrainingResultsTable.add_result()`

**Reusable Pattern**:
- ✅ Duplicate detection before adding
- ✅ Update existing entry if duplicate found
- ✅ Append new entry if unique
- ✅ Immediate table refresh after update
- ✅ `List[Dict]` data storage

**Code Similarity**: ~95%

---

#### **5. Export Functionality**
**Source**: `TradesPanel._export_trades()`, `_copy_trades()`, `_copy_selection()`
**Target**: `TrainingResultsTable` export methods

**Reusable Elements**:
- ✅ Timestamp-based filename generation
- ✅ CSV format with headers
- ✅ Tab-separated clipboard format (Excel-compatible)
- ✅ Multi-select copy support
- ✅ Try/catch error handling
- ✅ Success/error print messages
- ✅ `QApplication.clipboard()` integration

**Code Similarity**: ~90%

---

#### **6. Performance Summary Panel**
**Source**: `TradesPanel._create_performance_summary()`
**Target**: Training results summary (optional)

**Reusable Elements**:
- ✅ `QGroupBox` with header styling
- ✅ Horizontal layout with labels
- ✅ Real-time metric updates
- ✅ Color-coded metrics
- ✅ Fixed height panel

**Code Similarity**: ~80%

---

#### **7. Logger Integration**
**Source**: `TradesPanel` institutional-grade logging
**Target**: Training system logging

**Reusable Pattern**:
```python
# TradesPanel pattern:
from src.debugger_logger.config_debugger import ConfigDebugger, DebugLevel

log_file = Path("logs/training") / f"training_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
self.logger = ConfigDebugger(
    name="TrainingPanel",
    level=DebugLevel.HIGH,
    log_file=log_file,
    console_output=True
)
```

**Code Similarity**: 100% (exact pattern)

---

#### **8. ORM Integration Pattern**
**Source**: `TradesPanel` data storage (`List[Dict]`)
**Target**: Training results storage

**Reusable Pattern**:
- ✅ Store results in `List[Dict]` for UI display
- ✅ Database-backed via ORM (`TrainingEvent` model)
- ✅ Query results → populate list → update table
- ✅ Duplicate detection by composite key

**Code Similarity**: ~85%

---

### **Implementation Strategy**

**Phase 1: Direct Copy** (Tasks 2.1.22-2.1.23)
1. Copy `NumericTableWidgetItem` class (exact copy)
2. Copy table setup code from `_create_trades_table()`
3. Copy export methods from TradesPanel
4. Adapt column headers and data fields

**Phase 2: Adaptation** (Task 2.1.22)
1. Change P&L color logic → Confidence color logic
2. Change trade columns → training result columns
3. Change duplicate detection key (ID → signal_name + timeframe)
4. Update CSV headers for training data

**Phase 3: Integration** (Tasks 2.1.20-2.1.21)
1. Connect to `TrainingThread` worker
2. Add progress tracking (new functionality)
3. Connect to `OptimalParameterCalculator` output
4. Database query → table population

---

### **Time Savings Estimate**

| Component | From Scratch | With Reuse | Savings |
|-----------|-------------|-----------|---------|
| Table Infrastructure | 4 hours | 1 hour | 75% |
| Export Functionality | 3 hours | 1 hour | 67% |
| Color-Coded Display | 2 hours | 0.5 hours | 75% |
| Logger Integration | 1 hour | 0.25 hours | 75% |
| **Total** | **10 hours** | **2.75 hours** | **~72%** |

**Net Benefit**: ~7.25 hours saved by reusing TradesPanel patterns

---

## 🔧 CONFIGURATION UI REUSE OPPORTUNITIES

**CRITICAL DISCOVERY**: Existing `BacktestConfigurationPanel` (`src/optimizer_v3/ui/backtest_panels.py`) provides configuration widget patterns that can be directly adapted for Training configuration UI.

### **Reusable Components from BacktestConfigurationPanel**

#### **1. QGroupBox with FormLayout Pattern**
**Source**: `BacktestConfigurationPanel.setup_ui()`
**Target**: Training configuration sections (Tasks 2.1.2-2.1.7)

**Reusable Pattern**:
```python
# BacktestConfigurationPanel pattern:
risk_reward_group = QGroupBox("Risk/Reward Configuration")
risk_reward_group.setStyleSheet(GROUPBOX_STYLE)
risk_reward_layout = QFormLayout()
risk_reward_layout.setSpacing(SPACING_UNIT)

# Add inputs
self.min_rr_input = QDoubleSpinBox()
self.min_rr_input.setStyleSheet(INPUT_STYLE)
risk_reward_layout.addRow("Min Risk/Reward:", self.min_rr_input)

risk_reward_group.setLayout(risk_reward_layout)

# Training adaptation:
block_selection_group = QGroupBox("Block Selection")
block_selection_group.setStyleSheet(GROUPBOX_STYLE)
block_layout = QFormLayout()
block_layout.setSpacing(SPACING_UNIT)

# Add checkboxes
self.hod_checkbox = QCheckBox("HOD Rejection")
self.hod_checkbox.setStyleSheet(CHECKBOX_STYLE)
block_layout.addRow("Entry Blocks:", self.hod_checkbox)

block_selection_group.setLayout(block_layout)
```

**Code Similarity**: ~90%

---

#### **2. QSpinBox/QDoubleSpinBox Inputs**
**Source**: `BacktestConfigurationPanel` numeric inputs
**Target**: Period selection, delay bars configuration

**Reusable Elements**:
- ✅ Range validation (`setRange(min, max)`)
- ✅ Default value (`setValue(default)`)
- ✅ Uniform styling (`INPUT_STYLE`)
- ✅ Decimal precision for doubles
- ✅ Step increments

**Reusable Pattern**:
```python
# BacktestConfigurationPanel pattern:
self.min_rr_input = QDoubleSpinBox()
self.min_rr_input.setStyleSheet(INPUT_STYLE)
self.min_rr_input.setRange(1.0, 5.0)
self.min_rr_input.setValue(2.0)

# Training adaptation:
self.period_spin = QSpinBox()  
self.period_spin.setStyleSheet(INPUT_STYLE)
self.period_spin.setRange(7, 365)
self.period_spin.setValue(180)
```

**Code Similarity**: 100% (exact pattern)

---

#### **3. QCheckBox Configuration**
**Source**: `BacktestConfigurationPanel` boolean options
**Target**: Timeframe selection, mode selection

**Reusable Elements**:
- ✅ `CHECKBOX_STYLE` styling
- ✅ State tracking (`isChecked()`)
- ✅ Signal connections
- ✅ Group organization

**Reusable Pattern**:
```python
# Training timeframe checkboxes (adapted from Config):
timeframe_group = QGroupBox("Timeframes")
timeframe_group.setStyleSheet(GROUPBOX_STYLE)
timeframe_layout = QVBoxLayout()

self.tf_5m = QCheckBox("5 minutes")
self.tf_5m.setStyleSheet(CHECKBOX_STYLE)
self.tf_5m.setChecked(True)
timeframe_layout.addWidget(self.tf_5m)

self.tf_15m = QCheckBox("15 minutes")
self.tf_15m.setStyleSheet(CHECKBOX_STYLE)
self.tf_15m.setChecked(True)
timeframe_layout.addWidget(self.tf_15m)

timeframe_group.setLayout(timeframe_layout)
```

**Code Similarity**: ~95%

---

#### **4. Configuration Data Structure**
**Source**: `BacktestConfigurationPanel` config storage
**Target**: Training configuration storage

**Reusable Pattern**:
```python
# BacktestConfigurationPanel pattern:
class BacktestConfigurationPanel(QWidget):
    def __init__(self):
        self.risk_params = {
            'min_risk_reward': Decimal('2.0'),
            'risk_percent': Decimal('1.0'),
            'leverage': Decimal('1.0')
        }
    
    def get_config_for_mode(self, is_optimizer_mode: bool = False) -> dict:
        return {
            'risk': self.risk_params.copy(),
            'capital': {'amount': self.starting_capital}
        }

# Training adaptation:
class TrainingConfigPanel(QWidget):
    def __init__(self):
        self.training_params = {
            'max_lookback': 180,
            'min_signals': 50,
            'parallel_blocks': 4,
            'batch_size': 1000
        }
    
    def get_training_config(self) -> dict:
        return {
            'training': self.training_params.copy(),
            'signal': self.signal_params.copy(),
            'selected_blocks': self._get_selected_blocks(),
            'selected_timeframes': self._get_selected_timeframes()
        }
```

**Code Similarity**: ~85%

---

#### **5. Styled Input Widgets**
**Source**: All input styles from `backtest_panels.py`
**Target**: All Training configuration inputs

**Reusable Styles**:
```python
# Direct reuse from backtest_panels.py:
GROUPBOX_STYLE = """..."""  # GroupBox with colored title
INPUT_STYLE = """..."""      # TextInputs with focus states
CHECKBOX_STYLE = """..."""   # Checkboxes with custom indicators
COMBOBOX_STYLE = """..."""   # Dropdowns with hover effects
SPACING_UNIT = 8             # Consistent spacing
```

**Code Similarity**: 100% (exact copy)

---

#### **6. QComboBox Dropdown Pattern**
**Source**: `BacktestConfigurationPanel` selection widgets
**Target**: Mode selection, period selection

**Reusable Pattern**:
```python
# Add ComboBox (from Config panel pattern):
self.mode_combo = QComboBox()
self.mode_combo.setStyleSheet(COMBOBOX_STYLE)
self.mode_combo.addItems(['Testing Mode', 'Production Mode'])
self.mode_combo.setCurrentIndex(0)
```

**Code Similarity**: 100%

---

#### **7. Validation & State Management**
**Source**: `BacktestConfigurationPanel.set_optimizer_mode()`
**Target**: Training panel enable/disable based on running state

**Reusable Pattern**:
```python
# BacktestConfigurationPanel pattern:
def set_optimizer_mode(self, enabled: bool):
    """Enable/disable optimizer mode"""
    self.optimizer_enabled = enabled
    self.capital_input.setEnabled(not enabled)

# Training adaptation:
def set_training_running(self, is_running: bool):
    """Enable/disable inputs during training"""
    self.training_running = is_running
    for checkbox in self.block_checkboxes:
        checkbox.setEnabled(not is_running)
    self.period_spin.setEnabled(not is_running)
    self.start_button.setEnabled(not is_running)
```

**Code Similarity**: ~90%

---

### **Implementation Strategy for Tasks 2.1.2-2.1.7**

**Phase 1: Copy Base Patterns** (1 hour)
1. Copy `GROUPBOX_STYLE`, `INPUT_STYLE`, `CHECKBOX_STYLE`, `COMBOBOX_STYLE`
2. Copy `QFormLayout` setup pattern
3. Copy `QSpinBox/QDoubleSpinBox` configuration

**Phase 2: Adapt for Training** (2 hours)
1. Create block selection checkboxes (adapt from risk params)
2. Create mode ComboBox (adapt from similar patterns)
3. Create period SpinBox (exact pattern)
4. Create timeframe checkboxes (adapt from boolean options)
5. Add resource estimator label
6. Add confirmation dialog

**Phase 3: Integration** (1 hour)
1. Connect to `get_training_config()` method
2. Add validation rules
3. Connect to TrainingThread start
4. Add state management during training

---

### **Configuration UI Time Savings**

| Component | From Scratch | With Reuse | Savings |
|-----------|-------------|-----------|---------|
| GroupBox Layout | 2 hours | 0.5 hours | 75% |
| Styled Inputs | 3 hours | 0.5 hours | 83% |
| CheckBox Groups | 2 hours | 0.5 hours | 75% |
| ComboBox Dropdowns | 1 hour | 0.25 hours | 75% |
| Config Storage | 2 hours | 0.5 hours | 75% |
| State Management | 2 hours | 0.5 hours | 75% |
| **Total** | **12 hours** | **2.75 hours** | **~77%** |

**Net Benefit**: ~9.25 hours saved by reusing BacktestConfigurationPanel patterns

---

### **Combined Time Savings (TradesPanel + ConfigPanel)**

| Category | From Scratch | With Reuse | Savings |
|----------|-------------|-----------|---------|
| **Results Display** (Trades) | 10 hours | 2.75 hours | 72% |
| **Configuration UI** (Config) | 12 hours | 2.75 hours | 77% |
| **Total Sprint Savings** | **22 hours** | **5.5 hours** | **~75%** |

**Total Net Benefit**: **~16.5 hours saved** through institutional code reuse

---

## 📝 TASK DETAILS

### **Environment Configuration**
**Duration**: 1 hour  
**Dependencies**: Phase 1 complete

**Implementation**:
```bash
# Add to .env file

# Training System Configuration
TRAINING_MAX_LOOKBACK=180  # days of historical data
TRAINING_MIN_SIGNALS=50  # minimum signals for analysis
TRAINING_MAX_TIMEFRAMES=5  # maximum concurrent timeframes
TRAINING_BATCH_SIZE=1000  # signals per batch
TRAINING_PARALLEL_BLOCKS=4  # blocks to analyze in parallel

# Signal Analysis Configuration
SIGNAL_FORWARD_BARS=10  # bars to analyze after signal
SIGNAL_MIN_OCCURRENCE=5  # minimum occurrences for pattern
SIGNAL_MIN_CONFIDENCE=0.95  # minimum confidence level
SIGNAL_MAX_CORRELATION=0.7  # maximum correlation between signals
SIGNAL_MIN_IMPACT=0.001  # minimum price impact

# Price Movement Analysis
PRICE_VOLATILITY_WINDOW=20  # bars for volatility calculation
PRICE_IMPACT_THRESHOLD=0.002  # significant price movement
PRICE_NOISE_FILTER=0.0005  # filter out noise
PRICE_TREND_STRENGTH=0.6  # minimum trend strength
PRICE_REVERSAL_THRESHOLD=0.8  # reversal detection threshold

# Position Sizing Configuration
POSITION_MAX_SIZE=1.0  # BTC
POSITION_MIN_SIZE=0.001  # BTC
POSITION_SIZE_INCREMENT=0.001  # BTC
POSITION_RISK_LIMIT=500  # USD per trade
POSITION_MAX_NOTIONAL=50000  # USD

# Risk Management Configuration
RISK_MAX_DRAWDOWN=0.02  # maximum drawdown per trade
RISK_MIN_WIN_RATE=0.55  # minimum required win rate
RISK_MIN_PROFIT_FACTOR=1.5  # minimum profit factor
RISK_MAX_CORRELATION=0.7  # maximum correlation between trades
RISK_MAX_EXPOSURE=0.1  # maximum portfolio exposure

# Training Database Configuration
DB_MAX_SIGNALS=1000000  # maximum signals to store
DB_CLEANUP_INTERVAL=86400  # cleanup every 24 hours
DB_MIN_KEEP_DAYS=30  # minimum days to keep data
DB_COMPRESSION=true  # compress old data
DB_BACKUP_ENABLED=true  # backup training database

# Performance Requirements
PERF_MAX_MEMORY=4096  # MB maximum memory usage
PERF_MAX_CPU=90  # maximum CPU usage percentage
PERF_MAX_DISK=90  # maximum disk usage percentage
PERF_MIN_SIGNALS_PER_SEC=100  # processing performance

# Resource Management
RESOURCE_CHECK_INTERVAL=60  # seconds between checks
RESOURCE_WARNING_THRESHOLD=80  # percentage for warnings
RESOURCE_CRITICAL_THRESHOLD=90  # percentage for critical
RESOURCE_AUTO_CLEANUP=true  # auto cleanup when needed
RESOURCE_HISTORY_LENGTH=1440  # 24 hours of metrics

# UI Configuration
UI_UPDATE_INTERVAL=1000  # milliseconds
UI_CHART_POINTS=1000  # maximum points in charts
UI_TABLE_ROWS=1000  # maximum visible table rows
UI_AUTO_REFRESH=true  # auto refresh results
UI_CACHE_TIMEOUT=300  # seconds to cache results

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
LOG_PATH=logs/training
LOG_ROTATION=5  # number of files to keep
LOG_MAX_SIZE=10  # MB per log file
```

**Configuration Loading**:
```python
from dotenv import load_dotenv
import os
from decimal import Decimal
from typing import Dict, Any

def get_training_config() -> Dict[str, Any]:
    """Load training configuration from environment"""
    load_dotenv()
    
    return {
        'training': {
            'max_lookback': int(os.getenv('TRAINING_MAX_LOOKBACK')),
            'min_signals': int(os.getenv('TRAINING_MIN_SIGNALS')),
            'max_timeframes': int(os.getenv('TRAINING_MAX_TIMEFRAMES')),
            'batch_size': int(os.getenv('TRAINING_BATCH_SIZE')),
            'parallel_blocks': int(os.getenv('TRAINING_PARALLEL_BLOCKS'))
        },
        'signal': {
            'forward_bars': int(os.getenv('SIGNAL_FORWARD_BARS')),
            'min_occurrence': int(os.getenv('SIGNAL_MIN_OCCURRENCE')),
            'min_confidence': float(os.getenv('SIGNAL_MIN_CONFIDENCE')),
            'max_correlation': float(os.getenv('SIGNAL_MAX_CORRELATION')),
            'min_impact': float(os.getenv('SIGNAL_MIN_IMPACT'))
        },
        'price': {
            'volatility_window': int(os.getenv('PRICE_VOLATILITY_WINDOW')),
            'impact_threshold': float(os.getenv('PRICE_IMPACT_THRESHOLD')),
            'noise_filter': float(os.getenv('PRICE_NOISE_FILTER')),
            'trend_strength': float(os.getenv('PRICE_TREND_STRENGTH')),
            'reversal_threshold': float(os.getenv('PRICE_REVERSAL_THRESHOLD'))
        },
        'position': {
            'max_size': Decimal(os.getenv('POSITION_MAX_SIZE')),
            'min_size': Decimal(os.getenv('POSITION_MIN_SIZE')),
            'size_increment': Decimal(os.getenv('POSITION_SIZE_INCREMENT')),
            'risk_limit': int(os.getenv('POSITION_RISK_LIMIT')),
            'max_notional': int(os.getenv('POSITION_MAX_NOTIONAL'))
        },
        'risk': {
            'max_drawdown': float(os.getenv('RISK_MAX_DRAWDOWN')),
            'min_win_rate': float(os.getenv('RISK_MIN_WIN_RATE')),
            'min_profit_factor': float(os.getenv('RISK_MIN_PROFIT_FACTOR')),
            'max_correlation': float(os.getenv('RISK_MAX_CORRELATION')),
            'max_exposure': float(os.getenv('RISK_MAX_EXPOSURE'))
        },
        'database': {
            'max_signals': int(os.getenv('DB_MAX_SIGNALS')),
            'cleanup_interval': int(os.getenv('DB_CLEANUP_INTERVAL')),
            'min_keep_days': int(os.getenv('DB_MIN_KEEP_DAYS')),
            'compression': os.getenv('DB_COMPRESSION').lower() == 'true',
            'backup_enabled': os.getenv('DB_BACKUP_ENABLED').lower() == 'true'
        },
        'performance': {
            'max_memory': int(os.getenv('PERF_MAX_MEMORY')),
            'max_cpu': int(os.getenv('PERF_MAX_CPU')),
            'max_disk': int(os.getenv('PERF_MAX_DISK')),
            'min_signals_per_sec': int(os.getenv('PERF_MIN_SIGNALS_PER_SEC'))
        },
        'resources': {
            'check_interval': int(os.getenv('RESOURCE_CHECK_INTERVAL')),
            'warning_threshold': int(os.getenv('RESOURCE_WARNING_THRESHOLD')),
            'critical_threshold': int(os.getenv('RESOURCE_CRITICAL_THRESHOLD')),
            'auto_cleanup': os.getenv('RESOURCE_AUTO_CLEANUP').lower() == 'true',
            'history_length': int(os.getenv('RESOURCE_HISTORY_LENGTH'))
        },
        'ui': {
            'update_interval': int(os.getenv('UI_UPDATE_INTERVAL')),
            'chart_points': int(os.getenv('UI_CHART_POINTS')),
            'table_rows': int(os.getenv('UI_TABLE_ROWS')),
            'auto_refresh': os.getenv('UI_AUTO_REFRESH').lower() == 'true',
            'cache_timeout': int(os.getenv('UI_CACHE_TIMEOUT'))
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

### **Task 2.1.1: Create TrainingPanelUI (New Tab (Automated Trainer))**
**Duration**: 4 hours  
**Dependencies**: Phase 1 complete

**Implementation**: See OPTIMIZER_V3_AUTOMATED_TRAINER.md → "New Tab (Automated Trainer): Training Panel UI"

```python
# src/optimizer_v3/ui/training_panel.py
from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget
from src.strategy_builder.ui.styles import (
    WINDOW_STYLE,
    PANEL_TITLE_STYLE,
    SPACING_UNIT
)

class TrainingPanelUI(QMainWindow):
    """New Tab (Automated Trainer): Standalone training panel"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Optimizer v3 - Training Panel")
        self.setStyleSheet(WINDOW_STYLE)  # From styles.py
        self.setup_ui()
    
    def setup_ui(self):
        central = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(SPACING_UNIT)
        
        # Add components (all styled from styles.py)
        # ...
        
        central.setLayout(layout)
        self.setCentralWidget(central)
```

**Acceptance Criteria**:
- [ ] New Tab (Automated Trainer) created
- [ ] Uses WINDOW_STYLE from styles.py
- [ ] Matches Window 1 & 2 visual style

**Sign-off**: ☐ Developer ☐ Lead ☐ UI Designer

---

### **Task 2.1.2-2.1.7: UI Components**
See OPTIMIZER_V3_AUTOMATED_TRAINER.md for complete specifications

**Tasks**:
- 2.1.2: Block selection checkboxes (CHECKBOX_STYLE)
- 2.1.3: Mode selection ComboBox (COMBOBOX_STYLE)
- 2.1.4: Period selection dropdown (COMBOBOX_STYLE)
- 2.1.5: Timeframe checkboxes (CHECKBOX_STYLE)
- 2.1.6: Resource estimator label (create_font)
- 2.1.7: Confirmation dialog (DIALOG_STYLE)

**Sign-off**: ☐ Developer ☐ Lead ☐ UI Designer

---

### **Task 2.1.8: NautilusTrader Training System**
**Duration**: 8 hours  
**Dependencies**: 2.1.7

**Implementation**:
```python
from nautilus_trader.model.objects import Quantity, Price, Money
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.enums import OrderSide, PositionSide
from decimal import Decimal

class NautilusTrainingSystem:
    """Core training system with NautilusTrader integration"""
    
    def __init__(self, logger: OptimizerLogger):
        self.logger = logger
        self.type_converter = NautilusTypeConverter()
    
    def train_building_block(self,
                           block_name: str,
                           mode: str,
                           period: tuple,
                           timeframes: List[str],
                           instrument_id: InstrumentId):
        """Execute training with NautilusTrader types"""
        self.logger.info(f"Training block {block_name} on {instrument_id}")
        
        # Initialize metrics storage
        metrics = {
            'total_signals': 0,
            'valid_signals': 0,
            'avg_price_impact': Money('0', 'USD'),
            'avg_position_size': Quantity('0'),
            'win_rate': Decimal('0'),
            'profit_factor': Decimal('0')
        }
        
        # Analyze forward behavior with NautilusTrader types
        for timeframe in timeframes:
            signals = self._analyze_forward_behavior(
                block_name=block_name,
                timeframe=timeframe,
                period=period,
                instrument_id=instrument_id
            )
            
            # Update metrics with proper types
            metrics['total_signals'] += len(signals)
            metrics['valid_signals'] += len([s for s in signals if s.is_valid])
            
            # Calculate price impact (Money type)
            price_impacts = [s.price_impact for s in signals if s.is_valid]
            if price_impacts:
                total_impact = sum(price_impacts, Money('0', 'USD'))
                metrics['avg_price_impact'] = total_impact / len(price_impacts)
            
            # Calculate position sizes (Quantity type)
            position_sizes = [s.position_size for s in signals if s.is_valid]
            if position_sizes:
                total_size = sum(position_sizes, Quantity('0'))
                metrics['avg_position_size'] = total_size / len(position_sizes)
            
            # Calculate win rate and profit factor (Decimal)
            winning_trades = len([s for s in signals if s.pnl > Money('0', 'USD')])
            if signals:
                metrics['win_rate'] = Decimal(str(winning_trades / len(signals)))
            
            gross_profit = sum([s.pnl for s in signals if s.pnl > Money('0', 'USD')], Money('0', 'USD'))
            gross_loss = abs(sum([s.pnl for s in signals if s.pnl < Money('0', 'USD')], Money('0', 'USD')))
            if gross_loss > Money('0', 'USD'):
                metrics['profit_factor'] = Decimal(str(gross_profit.as_decimal() / gross_loss.as_decimal()))
        
        return metrics
    
    def _analyze_forward_behavior(self,
                                block_name: str,
                                timeframe: str,
                                period: tuple,
                                instrument_id: InstrumentId) -> List[SignalEvent]:
        """Analyze forward price behavior after signal"""
        signals = []
        
        # Get historical data with NautilusTrader types
        data = self._get_historical_data(
            instrument_id=instrument_id,
            timeframe=timeframe,
            start=period[0],
            end=period[1]
        )
        
        for bar in data:
            if self._check_signal_condition(block_name, bar):
                # Record signal with proper types
                signal = SignalEvent(
                    block_name=block_name,
                    timestamp=bar.timestamp,
                    price=Price(str(bar.close)),
                    instrument_id=instrument_id
                )
                
                # Analyze forward movement
                forward_bars = self._get_forward_bars(bar, data, bars=10)
                
                # Calculate metrics with NautilusTrader types
                max_move = self._calculate_max_move(forward_bars)
                signal.price_impact = Money(str(max_move), 'USD')
                
                # Calculate optimal position size
                signal.position_size = self._calculate_position_size(
                    price=signal.price,
                    volatility=self._calculate_volatility(forward_bars)
                )
                
                signals.append(signal)
        
        return signals
    
    def _calculate_position_size(self,
                               price: Price,
                               volatility: Decimal) -> Quantity:
        """Calculate optimal position size based on volatility"""
        # Risk-based sizing using NautilusTrader types
        risk_amount = Money('500', 'USD')  # $500 risk per trade
        stop_distance = price.as_decimal() * volatility  # 1x ATR
        
        # Convert to Quantity
        size = risk_amount.as_decimal() / stop_distance
        return Quantity(str(round(size, 8)))
    
    def _calculate_volatility(self, bars: List[Bar]) -> Decimal:
        """Calculate volatility (ATR) from bars"""
        # Proper decimal arithmetic
        ranges = [
            Decimal(str(max(
                bar.high - bar.low,
                abs(bar.high - bar.close_previous),
                abs(bar.low - bar.close_previous)
            )))
            for bar in bars
        ]
        return sum(ranges) / len(ranges)
```

**Testing**:
```python
def test_nautilus_training_system():
    """Test NautilusTrader integration in training"""
    system = NautilusTrainingSystem(OptimizerLogger('test'))
    
    # Test with BTC-USD instrument
    instrument_id = InstrumentId('BTC-USD')
    
    metrics = system.train_building_block(
        block_name='hod_rejection',
        mode='entry',
        period=('2025-01-01', '2025-12-31'),
        timeframes=['15m'],
        instrument_id=instrument_id
    )
    
    # Verify NautilusTrader types
    assert isinstance(metrics['avg_price_impact'], Money)
    assert isinstance(metrics['avg_position_size'], Quantity)
    assert isinstance(metrics['win_rate'], Decimal)
    assert isinstance(metrics['profit_factor'], Decimal)
    
    # Verify calculations
    assert metrics['avg_position_size'] <= Quantity('1.0')  # Max position
    assert metrics['win_rate'] <= Decimal('1.0')  # Max 100%
```

**Acceptance Criteria**:
- [ ] Uses NautilusTrader types throughout
- [ ] Proper decimal arithmetic for financial calculations
- [ ] Risk-based position sizing
- [ ] Volatility-based analysis
- [ ] Type safety in all calculations
- [ ] Comprehensive metrics with proper types
- [ ] 100% test coverage
- [ ] Zero floating point arithmetic

**Sign-off**: ☐ Developer ☐ Lead ☐ NautilusTrader Expert

---

### **Task 2.1.9-2.1.13: Analysis Methods**
See OPTIMIZER_V3_AUTOMATED_TRAINER.md → "Implementation" section

**Tasks**:
- 2.1.9: _analyze_forward_behavior
- 2.1.10: _find_signal_recurrence
- 2.1.11: _analyze_price_movement
- 2.1.12: _find_dependent_signals
- 2.1.13: _analyze_trade_outcome

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 2.1.14: Training Database Schema**
**Duration**: 3 hours  
**Dependencies**: 2.1.13

**Implementation**: See OPTIMIZER_V3_AUTOMATED_TRAINER.md → "Training Database Schema"

```python
# Complete schema from design doc
class TrainingEvent(Base):
    __tablename__ = 'training_events'
    # ... (complete implementation from doc)
```

**Acceptance Criteria**:
- [ ] Matches design spec exactly

**Sign-off**: ☐ Developer ☐ Lead ☐ DBA

---

### **Task 2.1.15: Database Migration & Indexes**
**Duration**: 2 hours  
**Dependencies**: 2.1.14

**File**: `alembic/versions/YYYYMMDD_add_training_tables.py`

**Implementation**:
```python
"""Add training tables

Revision ID: 20260205_001
Created: 2026-02-05
"""

def upgrade():
    # Create training_events table
    op.create_table(
        'training_events',
        # ... (all columns from Task 2.1.14)
    )
    
    # Create indexes
    op.create_index('idx_training_signal', 'training_events', ['signal_name'])
    op.create_index('idx_training_timeframe', 'training_events', ['timeframe'])
    op.create_index('idx_training_timestamp', 'training_events', ['timestamp'])
    
def downgrade():
    op.drop_table('training_events')
```

**Acceptance Criteria**:
- [ ] Migration script created
- [ ] All indexes defined
- [ ] Migration tested

**Sign-off**: ☐ Developer ☐ DBA

---

### **Task 2.1.16: Data Loading Pipeline**
**Duration**: 4 hours  
**Dependencies**: 2.1.15

**Implementation**: Historical data loader with caching

**Acceptance Criteria**:
- [ ] Loads 5m, 15m, 1h, 4h data
- [ ] Memory-efficient streaming
- [ ] Cache mechanism implemented
- [ ] Missing data detection

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 2.1.17: Data Caching System**
**Duration**: 2 hours  
**Dependencies**: 2.1.16

**Implementation**: LRU cache for loaded data

**Acceptance Criteria**:
- [ ] Cache hit/miss tracking
- [ ] Automatic cache invalidation
- [ ] Memory limit enforcement

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 2.1.18: OptimalParameterCalculator**  
**Duration**: 4 hours  
**Dependencies**: 2.1.17

**Implementation**: See OPTIMIZER_V3_AUTOMATED_TRAINER.md → "Optimal Parameter Calculator"

**Acceptance Criteria**:
- [ ] Calculates recheck delays
- [ ] Timing window analysis
- [ ] Statistical validation
- [ ] Confidence scores

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 2.1.19: Statistical Validation**
**Duration**: 3 hours  
**Dependencies**: 2.1.18

**Implementation**: Minimum sample size, outlier detection, cross-validation

**Acceptance Criteria**:
- [ ] Minimum 10+ samples enforced
- [ ] IQR outlier removal
- [ ] Bootstrap validation
- [ ] Confidence intervals

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 2.1.20: TrainingThread Worker**
**Duration**: 3 hours  
**Dependencies**: 2.1.19

**Implementation**: QThread worker class with signals

**Acceptance Criteria**:
- [ ] Progress signals emitted
- [ ] Cancellation support
- [ ] Exception handling
- [ ] ETA calculation

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 2.1.21: Progress Tracking UI**
**Duration**: 2 hours  
**Dependencies**: 2.1.20

**Implementation**: Progress bar, status label, ETA display

**Acceptance Criteria**:
- [ ] Uses PROGRESSBAR_STYLE
- [ ] Real-time updates
- [ ] ETA display
- [ ] Stop button functional

**Sign-off**: ☐ Developer ☐ UI Designer

---

### **Task 2.1.22: Results Display Table**
**Duration**: 3 hours  
**Dependencies**: 2.1.21

**REUSE PATTERN**: Adapts existing `TradesPanel` table structure from `src/optimizer_v3/ui/trades_panel.py`

**Implementation**:
```python
# src/optimizer_v3/ui/training_results_table.py
# REUSES: TradesPanel patterns for institutional-grade table display

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem
from src.strategy_builder.ui.styles import get_table_stylesheet, get_color

class TrainingResultsTable(QWidget):
    """
    Training Results Table - Adapted from TradesPanel
    
    REUSED PATTERNS:
    - NumericTableWidgetItem for proper sorting
    - Color-coded confidence scores (green/yellow/red)
    - Multi-select support
    - Sortable columns
    - Performance summary panel
    - Export to CSV functionality
    """
    
    def __init__(self):
        super().__init__()
        self.results: List[Dict] = []  # Training results from OptimalParameterCalculator
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout()
        
        # Results table (adapted from TradesPanel._create_trades_table)
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            'Signal', 'Timeframe', 'Optimal Delay', 'Range (Min-Max)', 
            'Sample Size', 'Confidence', 'Status'
        ])
        
        # Apply same styling as Trades table
        self.table.setStyleSheet(get_table_stylesheet())
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        
        # Column widths
        column_widths = [200, 120, 120, 150, 120, 120, 120]
        for i, width in enumerate(column_widths):
            self.table.setColumnWidth(i, width)
        
        layout.addWidget(self.table)
        self.setLayout(layout)
    
    def add_result(self, result_data: Dict):
        """
        Add training result - SAME PATTERN as TradesPanel.add_trade()
        
        Args:
            result_data: {
                'signal_name': str,
                'timeframe': str,
                'optimal_delay': int,
                'min_delay': int,
                'max_delay': int,
                'sample_size': int,
                'confidence': float (0.0-1.0)
            }
        """
        # Check for duplicate (same pattern as Trades)
        signal_key = f"{result_data['signal_name']}_{result_data['timeframe']}"
        for i, existing in enumerate(self.results):
            existing_key = f"{existing['signal_name']}_{existing['timeframe']}"
            if existing_key == signal_key:
                # Update existing
                self.results[i].update(result_data)
                self._update_table()
                return
        
        # Add new result
        self.results.append(result_data)
        self._update_table()
    
    def _update_table(self):
        """Update table - SAME PATTERN as TradesPanel._update_table()"""
        self.table.setRowCount(len(self.results))
        
        for row, result in enumerate(self.results):
            # Signal name
            self.table.setItem(row, 0, self._create_item(result['signal_name']))
            
            # Timeframe
            self.table.setItem(row, 1, self._create_item(result['timeframe']))
            
            # Optimal Delay (NumericTableWidgetItem for proper sorting)
            delay_item = NumericTableWidgetItem(str(result['optimal_delay']))
            delay_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, delay_item)
            
            # Range
            range_str = f"{result['min_delay']}-{result['max_delay']}"
            self.table.setItem(row, 3, self._create_item(range_str))
            
            # Sample Size (NumericTableWidgetItem)
            sample_item = NumericTableWidgetItem(str(result['sample_size']))
            sample_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, sample_item)
            
            # Confidence (color-coded like P&L in Trades)
            confidence = result['confidence']
            conf_item = self._create_item(f"{confidence*100:.0f}%")
            if confidence >= 0.8:
                conf_item.setForeground(QColor(get_color('success')))  # Green: High confidence
            elif confidence >= 0.5:
                conf_item.setForeground(QColor(get_color('warning')))  # Yellow: Medium
            else:
                conf_item.setForeground(QColor(get_color('error')))  # Red: Low confidence
            self.table.setItem(row, 5, conf_item)
            
            # Status
            status = 'Valid' if confidence >= 0.5 else 'Low Sample'
            status_item = self._create_item(status)
            if status == 'Low Sample':
                status_item.setForeground(QColor(get_color('error')))
            self.table.setItem(row, 6, status_item)
    
    def _create_item(self, text: str) -> QTableWidgetItem:
        """REUSED from TradesPanel - centered table item"""
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item
```

**REUSED CODE PATTERNS**:
- ✅ `NumericTableWidgetItem` for proper numeric sorting (from Trades ID column)
- ✅ `_update_table()` pattern for real-time updates
- ✅ `add_result()` with duplicate detection (same as `add_trade()`)
- ✅ Color-coded values (confidence like P&L colors)
- ✅ `get_table_stylesheet()` for consistent styling
- ✅ Multi-select support and sortable columns
- ✅ Same column width configuration pattern

**ORM INTEGRATION** (REUSED):
- Results stored in `List[Dict]` (same as Trades)
- Updates via `add_result()` method
- Database-backed via `TrainingEvent` ORM model
- Query results populate table

**Acceptance Criteria**:
- [ ] Uses TradesPanel table structure
- [ ] NumericTableWidgetItem for sorting
- [ ] Color-coded confidence scores
- [ ] Same styling as Trades table
- [ ] Multi-select support
- [ ] Real-time table updates

**Sign-off**: ☐ Developer ☐ UI Designer

---

### **Task 2.1.23: Export Functionality**
**Duration**: 2 hours  
**Dependencies**: 2.1.22

**REUSE PATTERN**: Adapts existing export methods from `TradesPanel._export_trades()` and `_copy_trades()`

**Implementation**:
```python
# src/optimizer_v3/ui/training_results_table.py (continued)

class TrainingResultsTable(QWidget):
    # ... (previous code)
    
    def _export_results(self) -> None:
        """
        Export training results to CSV - REUSED from TradesPanel._export_trades()
        
        SAME PATTERN:
        - Timestamp-based filename
        - CSV format with headers
        - Error handling with try/catch
        - Success confirmation
        """
        from datetime import datetime
        
        if not self.results:
            print("⚠️ No results to export")
            return
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"training_results_{timestamp}.csv"
        
        try:
            with open(filename, 'w') as f:
                # Write header
                f.write("Signal,Timeframe,Optimal Delay,Min Delay,Max Delay,Sample Size,Confidence,Status\n")
                
                # Write results (same CSV pattern as Trades)
                for result in self.results:
                    f.write(
                        f"{result.get('signal_name', '')},"
                        f"{result.get('timeframe', '')},"
                        f"{result.get('optimal_delay', '')},"
                        f"{result.get('min_delay', '')},"
                        f"{result.get('max_delay', '')},"
                        f"{result.get('sample_size', '')},"
                        f"{result.get('confidence', '')},"
                        f"{'Valid' if result.get('confidence', 0) >= 0.5 else 'Low Sample'}\n"
                    )
            
            print(f"✅ Training results exported to {filename}")
            
        except Exception as e:
            print(f"❌ Export failed: {str(e)}")
    
    def _copy_results(self) -> None:
        """
        Copy results to clipboard - REUSED from TradesPanel._copy_trades()
        
        SAME PATTERN:
        - Tab-separated format for Excel
        - Header row + data rows
        - Clipboard integration
        - Success/error messaging
        """
        from PyQt5.QtWidgets import QApplication
        
        if not self.results:
            print("⚠️ No results to copy")
            return
        
        try:
            # Build tab-separated content (same as Trades)
            lines = []
            # Header
            lines.append("Signal\tTimeframe\tOptimal Delay\tRange\tSample Size\tConfidence\tStatus")
            
            # Data rows
            for result in self.results:
                confidence = result.get('confidence', 0)
                status = 'Valid' if confidence >= 0.5 else 'Low Sample'
                range_str = f"{result.get('min_delay', '')}-{result.get('max_delay', '')}"
                
                lines.append(
                    f"{result.get('signal_name', '')}\t"
                    f"{result.get('timeframe', '')}\t"
                    f"{result.get('optimal_delay', '')}\t"
                    f"{range_str}\t"
                    f"{result.get('sample_size', '')}\t"
                    f"{confidence*100:.0f}%\t"
                    f"{status}"
                )
            
            # Copy to clipboard (same QApplication.clipboard() pattern)
            content = '\n'.join(lines)
            clipboard = QApplication.clipboard()
            clipboard.setText(content)
            
            print(f"✅ {len(self.results)} results copied to clipboard")
            
        except Exception as e:
            print(f"❌ Copy failed: {str(e)}")
    
    def _copy_selection(self) -> None:
        """
        Copy selected results - REUSED from TradesPanel._copy_selection()
        
        SAME PATTERN:
        - Get selected row indices
        - Filter results by selection
        - Tab-separated format
        - Multi-select support (Ctrl+Click)
        """
        from PyQt5.QtWidgets import QApplication
        
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            print("⚠️ No results selected - select rows with Ctrl+Click")
            return
        
        try:
            # Get selected indices (same pattern as Trades)
            selected_indices = sorted([row.row() for row in selected_rows])
            selected_results = [self.results[i] for i in selected_indices]
            
            # Build content (same format as _copy_results)
            lines = []
            lines.append("Signal\tTimeframe\tOptimal Delay\tRange\tSample Size\tConfidence\tStatus")
            
            for result in selected_results:
                confidence = result.get('confidence', 0)
                status = 'Valid' if confidence >= 0.5 else 'Low Sample'
                range_str = f"{result.get('min_delay', '')}-{result.get('max_delay', '')}"
                
                lines.append(
                    f"{result.get('signal_name', '')}\t"
                    f"{result.get('timeframe', '')}\t"
                    f"{result.get('optimal_delay', '')}\t"
                    f"{range_str}\t"
                    f"{result.get('sample_size', '')}\t"
                    f"{confidence*100:.0f}%\t"
                    f"{status}"
                )
            
            content = '\n'.join(lines)
            clipboard = QApplication.clipboard()
            clipboard.setText(content)
            
            print(f"✅ {len(selected_results)} selected results copied")
            
        except Exception as e:
            print(f"❌ Copy selection failed: {str(e)}")
```

**REUSED EXPORT PATTERNS**:
- ✅ `_export_results()` - Same CSV export as `TradesPanel._export_trades()`
- ✅ `_copy_results()` - Same clipboard copy as `TradesPanel._copy_trades()`
- ✅ `_copy_selection()` - Same multi-select copy as `TradesPanel._copy_selection()`
- ✅ Timestamp-based filenames
- ✅ Tab-separated format for Excel compatibility
- ✅ Try/catch error handling
- ✅ Success/error messaging

**Acceptance Criteria**:
- [ ] CSV export with timestamp filename
- [ ] Copy all to clipboard (tab-separated)
- [ ] Copy selection to clipboard (multi-select)
- [ ] Same error handling as TradesPanel
- [ ] Excel-compatible format

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 2.1.24: Complete Test Suite**
**Duration**: 6 hours  
**Dependencies**: 2.1.23

**Implementation**: Comprehensive test coverage (100%)

**Test Files**:
- `test_nautilus_training_system.py`
- `test_optimal_parameter_calculator.py`
- `test_training_database.py`
- `test_training_panel_ui.py`
- `test_data_loading_pipeline.py`

**Acceptance Criteria**:
- [ ] 100% code coverage
- [ ] All edge cases tested
- [ ] Performance benchmarks
- [ ] Type safety validation

**Sign-off**: ☐ Developer ☐ QA Lead

---

### **Task 2.1.25: Sprint Sign-Off**
**Duration**: 1 hour  
**Dependencies**: All tasks 2.1.0-2.1.24

**Verification Checklist**:
- [ ] All 25 tasks completed
- [ ] New Tab (Automated Trainer) functional
- [ ] Training database operational
- [ ] 100% test coverage achieved
- [ ] NautilusTrader types throughout
- [ ] Zero hardcoded styles
- [ ] All integration points working
- [ ] Documentation complete

**Sign-off**: ☐ Developer ☐ Lead ☐ Architect

---

**Next Sprint**: `SPRINT_2_2_SIGNAL_INTELLIGENCE.md`
