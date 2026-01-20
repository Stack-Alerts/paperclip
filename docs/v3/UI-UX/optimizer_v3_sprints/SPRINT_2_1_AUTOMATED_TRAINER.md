# SPRINT 2.1: AUTOMATED TRAINER (WINDOW 4)
**Forward-Looking Analysis, Training Database, Optimal Parameters**

**Duration**: 10 days  
**Tasks**: 20  
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

3. **[OPTIMIZER_V3_FLOW_DIAGRAM.md](./OPTIMIZER_V3_FLOW_DIAGRAM.md)**
   - System architecture
   - UI component flow
   - Data flow patterns
   - Configuration flow
   - Integration points

---

## 📋 SPRINT OVERVIEW

**Purpose**: Build automated training system (NEW Window 4):
- Forward-looking signal analysis
- Training database for historical signals
- Optimal parameter calculator
- Standalone training UI

**Critical Success Factors**:
- 100% NautilusTrader type coverage
- Zero hardcoded styles
- Dark theme compatible
- Visual consistency with Window 1-3
- All styles from styles.py
- Proper spacing and alignment
- Responsive UI updates
- Memory efficient

**Design Reference Sections**:
- UI Design: Section "Window 4: Training Panel UI"
- Implementation: Section "Implementation"
- Database: Section "Training Database Schema"
- Calculator: Section "Optimal Parameter Calculator"

---

## ✅ TASK CHECKLIST

- [ ] 2.1.1 Create TrainingPanelUI (Window 4)
- [ ] 2.1.2 Block selection checkboxes
- [ ] 2.1.3 Mode selection (Entry/Exit)
- [ ] 2.1.4 Period selection
- [ ] 2.1.5 Timeframe checkboxes
- [ ] 2.1.6 Resource estimator
- [ ] 2.1.7 Confirmation dialog
- [ ] 2.1.8 AutomatedTrainingSystem class
- [ ] 2.1.9 Forward analyzer
- [ ] 2.1.10 Signal recurrence detector
- [ ] 2.1.11 Price movement tracker
- [ ] 2.1.12 Dependent signal finder
- [ ] 2.1.13 Trade outcome analyzer
- [ ] 2.1.14 Training database schema
- [ ] 2.1.15 Data storage pipeline
- [ ] 2.1.16 OptimalParameterCalculator
- [ ] 2.1.17 Progress tracking UI
- [ ] 2.1.18 Results display
- [ ] 2.1.19 Tests (95% coverage)
- [ ] 2.1.20 Sprint sign-off

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

### **Task 2.1.1: Create TrainingPanelUI (Window 4)**
**Duration**: 4 hours  
**Dependencies**: Phase 1 complete

**Implementation**: See OPTIMIZER_V3_AUTOMATED_TRAINER.md → "Window 4: Training Panel UI"

```python
# src/optimizer_v3/ui/training_panel.py
from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget
from src.strategy_builder.ui.styles import (
    WINDOW_STYLE,
    PANEL_TITLE_STYLE,
    SPACING_UNIT
)

class TrainingPanelUI(QMainWindow):
    """Window 4: Standalone training panel"""
    
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
- [ ] Window 4 created
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

### **Task 2.1.15-2.1.16: Data Pipeline & Calculator**
See OPTIMIZER_V3_AUTOMATED_TRAINER.md for complete specifications

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 2.1.17-2.1.20: UI Results & Testing**
**Duration**: 8 hours total

**Tasks**:
- 2.1.17: Progress tracking (PROGRESSBAR_STYLE)
- 2.1.18: Results display (TABLE_STYLE)
- 2.1.19: All tests (95% coverage)
- 2.1.20: Sprint sign-off

**Sign-off**: ☐ Developer ☐ Lead ☐ Architect

---

## 🎯 SPRINT SIGN-OFF

**Complete When**:
- [ ] All 20 tasks done
- [ ] Window 4 fully functional
- [ ] Training database working
- [ ] 100% test coverage

**Sign-off**: ☐ Developer ☐ Lead ☐ Architect

**Next Sprint**: `SPRINT_2_2_SIGNAL_INTELLIGENCE.md`
