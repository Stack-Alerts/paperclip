# SPRINT 2.2: SIGNAL INTELLIGENCE SYSTEM
**Event Recording, Metrics Calculation, Performance Dashboard**

**Duration**: 12 days  
**Tasks**: 37  
**Dependencies**: Sprint 2.1 complete, **Sprint 1.8 Exit Conditions**  
**Status**: ☐ Not Started

**CRITICAL UPDATE (Sprint 1.8 Impact)**: This sprint MUST include Exit Condition tracking.
Sprint 1.8 introduces Exit Conditions with three binding levels (STRATEGY/BLOCK/SIGNAL),
two exit modes (ABSOLUTE/FLEXIBLE), and percentage-based partial exits. All signal
intelligence systems MUST track exit condition events alongside entry signals.

**Design Reference**: `docs/v3/UI-UX/OPTIMIZER_V3_SIGNAL_INTELLIGENCE.md` (COMPLETE DOCUMENT)  
**Testing Reference**: `docs/v3/UI-UX/OPTIMIZER_V3_TESTING_FRAMEWORK.md` → Data Validation

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

**Purpose**: Build signal tracking and intelligence system:
- Record EVERY signal fire/non-fire
- Calculate signal effectiveness metrics
- Track signal correlations  
- Performance dashboard with charts
- Warning system for low-weight signals

**Design Reference Sections**:
- Event Recording: "Signal Event Recording"
- Metrics: "Signal Weight Metrics" + "Weight Calculation Algorithm"
- Database: "Database Schema"
- Intelligence: "Signal Intelligence Framework"
- Dashboard: "Signal Performance Dashboard"

---

## ✅ TASK CHECKLIST

- [ ] 2.2.1 SignalEvent class
- [ ] 2.2.2 SignalWeightMetrics class
- [ ] 2.2.3 Weight calculation algorithm
- [ ] 2.2.4 Signal events DB table
- [ ] 2.2.5 Signal metrics DB table
- [ ] 2.2.6 Strategy results DB table
- [ ] 2.2.7 Signal effectiveness analyzer
- [ ] 2.2.8 Warning system (weight <40)
- [ ] 2.2.9 Event recorder integration
- [ ] 2.2.10 Metrics calculator
- [ ] 2.2.11 Database query optimization
- [ ] 2.2.12 Signal correlation analyzer
- [ ] 2.2.13 Dashboard UI
- [ ] 2.2.14 Performance charts (Plotly)
- [ ] 2.2.15 Weight distribution chart
- [ ] 2.2.16 Correlation matrix heatmap
- [ ] 2.2.17 Trade impact visualization
- [ ] 2.2.18 Data export (CSV/JSON)
- [ ] 2.2.19 Integration tests
- [ ] 2.2.20 Accuracy validation
- [ ] 2.2.21 Tests (95% coverage)
- [ ] 2.2.22 Sprint sign-off
- [ ] 2.2.23-2.2.32 Extended analytics (10 tasks)

**🚨 EXIT CONDITION INTEGRATION (Sprint 1.8 Dependency)**:
- [ ] 2.2.33 Exit Condition Event Tracking
- [ ] 2.2.34 Exit Condition Effectiveness Metrics
- [ ] 2.2.35 Exit Condition Dashboard Section
- [ ] 2.2.36 Exit Condition Correlation Analysis
- [ ] 2.2.37 Exit Condition Recommendations

---

## 📝 TASK DETAILS

### **Environment Configuration**
**Duration**: 1 hour  
**Dependencies**: Sprint 2.1 complete

**Implementation**:
```bash
# Add to .env file

# Signal Event Recording
SIGNAL_EVENT_BATCH_SIZE=1000  # events per batch
SIGNAL_EVENT_RETENTION=90  # days to keep events
SIGNAL_EVENT_COMPRESSION=true  # compress old events
SIGNAL_EVENT_BACKUP=true  # backup events database

# Signal Analysis Configuration
SIGNAL_MIN_OCCURRENCES=50  # minimum events for analysis
SIGNAL_MIN_WIN_RATE=0.55  # minimum required win rate
SIGNAL_MIN_PROFIT_FACTOR=1.5  # minimum required profit factor
SIGNAL_MAX_DRAWDOWN=0.10  # maximum allowed drawdown
SIGNAL_MIN_TRADES=30  # minimum trades for significance

# Weight Calculation
WEIGHT_WIN_RATE_FACTOR=0.40  # 40% of weight
WEIGHT_PROFIT_FACTOR=0.20  # 20% of weight
WEIGHT_RISK_REWARD=0.20  # 20% of weight
WEIGHT_MARKET_FIT=0.20  # 20% of weight
WEIGHT_MIN_THRESHOLD=40  # warning threshold
WEIGHT_UPDATE_INTERVAL=3600  # seconds between updates

# Market Condition Analysis
MARKET_VOLATILITY_WINDOW=20  # bars for volatility
MARKET_VOLUME_WINDOW=20  # bars for volume analysis
MARKET_TREND_WINDOW=14  # bars for trend strength
MARKET_SESSION_ZONES=true  # analyze by trading session
MARKET_CONDITION_CACHE=300  # seconds to cache analysis

# Correlation Analysis
CORRELATION_MIN_THRESHOLD=0.7  # minimum for high correlation
CORRELATION_WINDOW=180  # days for correlation analysis
CORRELATION_MIN_OVERLAP=50  # minimum overlapping events
CORRELATION_UPDATE_INTERVAL=86400  # daily updates
CORRELATION_CACHE_ENABLED=true  # cache correlation matrix

# Performance Monitoring
MONITOR_UPDATE_INTERVAL=5  # seconds between updates
MONITOR_HISTORY_LENGTH=1440  # number of data points to keep
MONITOR_ALERT_ENABLED=true  # enable performance alerts
MONITOR_MIN_WIN_RATE=0.50  # alert threshold
MONITOR_MIN_PROFIT=100  # USD minimum profit

# Signal Database Configuration
DB_MAX_EVENTS=1000000  # maximum events to store
DB_CLEANUP_INTERVAL=86400  # cleanup every 24 hours
DB_MIN_KEEP_DAYS=30  # minimum days to keep data
DB_COMPRESSION=true  # compress old data
DB_BACKUP_ENABLED=true  # backup signal database

# Dashboard Configuration
DASH_UPDATE_INTERVAL=5000  # milliseconds
DASH_CHART_POINTS=1000  # points per chart
DASH_TABLE_ROWS=1000  # maximum visible rows
DASH_AUTO_REFRESH=true  # auto refresh data
DASH_CACHE_TIMEOUT=300  # seconds to cache data

# Export Configuration
EXPORT_DECIMAL_PLACES=8  # for numeric values
EXPORT_INCLUDE_TIMESTAMPS=true  # include event times
EXPORT_COMPRESSION=true  # compress exports
EXPORT_BATCH_SIZE=1000  # rows per batch
EXPORT_MAX_ROWS=1000000  # maximum rows per export

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
LOG_PATH=logs/signal_intelligence
LOG_ROTATION=5  # number of files to keep
LOG_MAX_SIZE=10  # MB per log file
```

**Configuration Loading**:
```python
from dotenv import load_dotenv
import os
from decimal import Decimal
from typing import Dict, Any

def get_signal_config() -> Dict[str, Any]:
    """Load signal intelligence configuration from environment"""
    load_dotenv()
    
    return {
        'events': {
            'batch_size': int(os.getenv('SIGNAL_EVENT_BATCH_SIZE')),
            'retention': int(os.getenv('SIGNAL_EVENT_RETENTION')),
            'compression': os.getenv('SIGNAL_EVENT_COMPRESSION').lower() == 'true',
            'backup': os.getenv('SIGNAL_EVENT_BACKUP').lower() == 'true'
        },
        'analysis': {
            'min_occurrences': int(os.getenv('SIGNAL_MIN_OCCURRENCES')),
            'min_win_rate': float(os.getenv('SIGNAL_MIN_WIN_RATE')),
            'min_profit_factor': float(os.getenv('SIGNAL_MIN_PROFIT_FACTOR')),
            'max_drawdown': float(os.getenv('SIGNAL_MAX_DRAWDOWN')),
            'min_trades': int(os.getenv('SIGNAL_MIN_TRADES'))
        },
        'weights': {
            'win_rate_factor': float(os.getenv('WEIGHT_WIN_RATE_FACTOR')),
            'profit_factor': float(os.getenv('WEIGHT_PROFIT_FACTOR')),
            'risk_reward': float(os.getenv('WEIGHT_RISK_REWARD')),
            'market_fit': float(os.getenv('WEIGHT_MARKET_FIT')),
            'min_threshold': int(os.getenv('WEIGHT_MIN_THRESHOLD')),
            'update_interval': int(os.getenv('WEIGHT_UPDATE_INTERVAL'))
        },
        'market': {
            'volatility_window': int(os.getenv('MARKET_VOLATILITY_WINDOW')),
            'volume_window': int(os.getenv('MARKET_VOLUME_WINDOW')),
            'trend_window': int(os.getenv('MARKET_TREND_WINDOW')),
            'session_zones': os.getenv('MARKET_SESSION_ZONES').lower() == 'true',
            'condition_cache': int(os.getenv('MARKET_CONDITION_CACHE'))
        },
        'correlation': {
            'min_threshold': float(os.getenv('CORRELATION_MIN_THRESHOLD')),
            'window': int(os.getenv('CORRELATION_WINDOW')),
            'min_overlap': int(os.getenv('CORRELATION_MIN_OVERLAP')),
            'update_interval': int(os.getenv('CORRELATION_UPDATE_INTERVAL')),
            'cache_enabled': os.getenv('CORRELATION_CACHE_ENABLED').lower() == 'true'
        },
        'monitor': {
            'update_interval': int(os.getenv('MONITOR_UPDATE_INTERVAL')),
            'history_length': int(os.getenv('MONITOR_HISTORY_LENGTH')),
            'alert_enabled': os.getenv('MONITOR_ALERT_ENABLED').lower() == 'true',
            'min_win_rate': float(os.getenv('MONITOR_MIN_WIN_RATE')),
            'min_profit': int(os.getenv('MONITOR_MIN_PROFIT'))
        },
        'database': {
            'max_events': int(os.getenv('DB_MAX_EVENTS')),
            'cleanup_interval': int(os.getenv('DB_CLEANUP_INTERVAL')),
            'min_keep_days': int(os.getenv('DB_MIN_KEEP_DAYS')),
            'compression': os.getenv('DB_COMPRESSION').lower() == 'true',
            'backup_enabled': os.getenv('DB_BACKUP_ENABLED').lower() == 'true'
        },
        'dashboard': {
            'update_interval': int(os.getenv('DASH_UPDATE_INTERVAL')),
            'chart_points': int(os.getenv('DASH_CHART_POINTS')),
            'table_rows': int(os.getenv('DASH_TABLE_ROWS')),
            'auto_refresh': os.getenv('DASH_AUTO_REFRESH').lower() == 'true',
            'cache_timeout': int(os.getenv('DASH_CACHE_TIMEOUT'))
        },
        'export': {
            'decimal_places': int(os.getenv('EXPORT_DECIMAL_PLACES')),
            'include_timestamps': os.getenv('EXPORT_INCLUDE_TIMESTAMPS').lower() == 'true',
            'compression': os.getenv('EXPORT_COMPRESSION').lower() == 'true',
            'batch_size': int(os.getenv('EXPORT_BATCH_SIZE')),
            'max_rows': int(os.getenv('EXPORT_MAX_ROWS'))
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

### **Task 2.2.1: NautilusTrader Signal Event**
**Duration**: 4 hours  
**Dependencies**: Sprint 2.1 complete

**Implementation**:
```python
from dataclasses import dataclass
from datetime import datetime
from nautilus_trader.model.objects import Quantity, Price, Money
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.enums import OrderSide, PositionSide
from decimal import Decimal

@dataclass
class NautilusSignalEvent:
    """Record of signal occurrence with NautilusTrader types"""
    signal_name: str
    block_name: str
    timestamp: datetime
    instrument_id: InstrumentId
    price_at_signal: Price
    fired: bool
    
    # Position sizing
    position_size: Quantity
    position_side: PositionSide
    
    # Risk metrics
    stop_loss_price: Price
    take_profit_price: Price
    risk_amount: Money
    potential_reward: Money
    risk_reward_ratio: Decimal
    
    # Trade outcome (if fired)
    trade_pnl: Money = None
    max_favorable_excursion: Money = None
    max_adverse_excursion: Money = None
    trade_duration: int = None  # bars held
    
    # Market context
    volatility: Decimal  # ATR
    volume_ratio: Decimal  # vs 20-period SMA
    trend_strength: Decimal  # ADX
    session: str  # Asia/London/NY
    
    # Signal context
    confluence_signals: list[str]  # Other signals that fired
    recheck_delay: int  # bars until recheck
    timing_window: int  # max bars for timing constraint
    
    def calculate_metrics(self) -> dict:
        """Calculate signal effectiveness metrics"""
        return {
            'risk_reward_ratio': self.risk_reward_ratio,
            'position_size': self.position_size,
            'stop_distance': abs(self.price_at_signal.as_decimal() - 
                               self.stop_loss_price.as_decimal()),
            'profit_target': abs(self.price_at_signal.as_decimal() - 
                               self.take_profit_price.as_decimal()),
            'risk_amount': self.risk_amount,
            'potential_reward': self.potential_reward,
            'actual_pnl': self.trade_pnl if self.trade_pnl else Money('0', 'USD'),
            'mfe': self.max_favorable_excursion if self.max_favorable_excursion else Money('0', 'USD'),
            'mae': self.max_adverse_excursion if self.max_adverse_excursion else Money('0', 'USD')
        }
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage"""
        return {
            'signal_name': self.signal_name,
            'block_name': self.block_name,
            'timestamp': self.timestamp,
            'instrument_id': self.instrument_id.to_string(),
            'price_at_signal': self.price_at_signal.to_string(),
            'fired': self.fired,
            'position_size': self.position_size.to_string(),
            'position_side': self.position_side.name,
            'stop_loss_price': self.stop_loss_price.to_string(),
            'take_profit_price': self.take_profit_price.to_string(),
            'risk_amount': self.risk_amount.to_string(),
            'potential_reward': self.potential_reward.to_string(),
            'risk_reward_ratio': str(self.risk_reward_ratio),
            'trade_pnl': self.trade_pnl.to_string() if self.trade_pnl else None,
            'mfe': self.max_favorable_excursion.to_string() if self.max_favorable_excursion else None,
            'mae': self.max_adverse_excursion.to_string() if self.max_adverse_excursion else None,
            'trade_duration': self.trade_duration,
            'volatility': str(self.volatility),
            'volume_ratio': str(self.volume_ratio),
            'trend_strength': str(self.trend_strength),
            'session': self.session,
            'confluence_signals': self.confluence_signals,
            'recheck_delay': self.recheck_delay,
            'timing_window': self.timing_window
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'NautilusSignalEvent':
        """Create from dictionary"""
        return cls(
            signal_name=data['signal_name'],
            block_name=data['block_name'],
            timestamp=data['timestamp'],
            instrument_id=InstrumentId.from_string(data['instrument_id']),
            price_at_signal=Price.from_string(data['price_at_signal']),
            fired=data['fired'],
            position_size=Quantity.from_string(data['position_size']),
            position_side=PositionSide[data['position_side']],
            stop_loss_price=Price.from_string(data['stop_loss_price']),
            take_profit_price=Price.from_string(data['take_profit_price']),
            risk_amount=Money.from_string(data['risk_amount']),
            potential_reward=Money.from_string(data['potential_reward']),
            risk_reward_ratio=Decimal(data['risk_reward_ratio']),
            trade_pnl=Money.from_string(data['trade_pnl']) if data['trade_pnl'] else None,
            max_favorable_excursion=Money.from_string(data['mfe']) if data['mfe'] else None,
            max_adverse_excursion=Money.from_string(data['mae']) if data['mae'] else None,
            trade_duration=data['trade_duration'],
            volatility=Decimal(data['volatility']),
            volume_ratio=Decimal(data['volume_ratio']),
            trend_strength=Decimal(data['trend_strength']),
            session=data['session'],
            confluence_signals=data['confluence_signals'],
            recheck_delay=data['recheck_delay'],
            timing_window=data['timing_window']
        )
```

**Testing**:
```python
def test_nautilus_signal_event():
    """Test NautilusTrader type handling"""
    event = NautilusSignalEvent(
        signal_name='HOD_REJECTION',
        block_name='hod',
        timestamp=datetime.now(),
        instrument_id=InstrumentId('BTC-USD'),
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
        confluence_signals=['RSI_OVERBOUGHT', 'VWAP_REJECTION'],
        recheck_delay=25,
        timing_window=20
    )
    
    # Test type safety
    assert isinstance(event.price_at_signal, Price)
    assert isinstance(event.position_size, Quantity)
    assert isinstance(event.risk_amount, Money)
    assert isinstance(event.risk_reward_ratio, Decimal)
    
    # Test serialization
    data = event.to_dict()
    restored = NautilusSignalEvent.from_dict(data)
    assert restored.price_at_signal == event.price_at_signal
    assert restored.position_size == event.position_size
    assert restored.risk_amount == event.risk_amount
    
    # Test metrics calculation
    metrics = event.calculate_metrics()
    assert isinstance(metrics['risk_reward_ratio'], Decimal)
    assert isinstance(metrics['position_size'], Quantity)
    assert isinstance(metrics['risk_amount'], Money)
```

**Acceptance Criteria**:
- [ ] Uses NautilusTrader types throughout
- [ ] Proper type conversion for storage
- [ ] Comprehensive trade metrics
- [ ] Market context tracking
- [ ] Signal relationship tracking
- [ ] Serialization/deserialization
- [ ] 100% test coverage
- [ ] Zero floating point arithmetic

**Sign-off**: ☐ Developer ☐ Lead ☐ NautilusTrader Expert

---

### **Task 2.2.2: NautilusTrader Signal Weight Metrics**
**Duration**: 4 hours  
**Dependencies**: 2.2.1

**Implementation**:
```python
from dataclasses import dataclass
from nautilus_trader.model.objects import Money, Quantity
from decimal import Decimal

@dataclass
class NautilusSignalWeightMetrics:
    """Signal effectiveness metrics with NautilusTrader types"""
    signal_name: str
    block_name: str
    
    # Occurrence metrics
    total_appearances: int
    fire_rate: Decimal  # How often signal fires
    recheck_success_rate: Decimal  # How often recheck confirms
    timing_success_rate: Decimal  # How often timing constraints met
    
    # Performance metrics
    win_rate: Decimal
    profit_factor: Decimal
    avg_win: Money
    avg_loss: Money
    avg_pnl_contribution: Money
    risk_reward_ratio: Decimal
    
    # Position metrics
    avg_position_size: Quantity
    max_position_size: Quantity
    avg_hold_time: int  # bars
    
    # Market condition preferences
    volatility_preference: str  # low/medium/high
    volume_preference: str  # low/medium/high
    trend_strength_preference: str  # weak/strong
    best_session: str  # Asia/London/NY
    
    # Correlation metrics
    correlation_with_wins: Decimal
    correlation_with_pnl: Decimal
    highly_correlated_signals: List[str]  # >0.7 correlation
    
    # Final weight (0-100)
    weight: Decimal
    
    def calculate_weight(self) -> Decimal:
        """Calculate comprehensive signal weight"""
        # Base effectiveness (0-40 points)
        base_score = (
            self.win_rate * Decimal('20') +
            min(self.profit_factor, Decimal('3')) * Decimal('10') +
            self.fire_rate * Decimal('10')
        )
        
        # Risk metrics (0-30 points)
        risk_score = (
            min(self.risk_reward_ratio, Decimal('3')) * Decimal('10') +
            (Decimal('1') - abs(self.avg_loss) / Money('100', 'USD')) * Decimal('10') +
            (self.avg_position_size / self.max_position_size) * Decimal('10')
        )
        
        # Market alignment (0-20 points)
        market_score = Decimal('0')
        if self._matches_current_volatility():
            market_score += Decimal('7')
        if self._matches_current_volume():
            market_score += Decimal('7')
        if self._matches_current_session():
            market_score += Decimal('6')
        
        # Correlation bonus (0-10 points)
        correlation_score = (
            self.correlation_with_wins * Decimal('5') +
            self.correlation_with_pnl * Decimal('5')
        )
        
        # Total weight (0-100)
        total = base_score + risk_score + market_score + correlation_score
        
        # Clamp to 0-100 range
        return max(Decimal('0'), min(Decimal('100'), total))
    
    def _matches_current_volatility(self) -> bool:
        """Check if current volatility matches preference"""
        current_volatility = self._get_current_volatility()
        return current_volatility == self.volatility_preference
    
    def _matches_current_volume(self) -> bool:
        """Check if current volume matches preference"""
        current_volume = self._get_current_volume()
        return current_volume == self.volume_preference
    
    def _matches_current_session(self) -> bool:
        """Check if current session matches preference"""
        current_session = self._get_current_session()
        return current_session == self.best_session
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage"""
        return {
            'signal_name': self.signal_name,
            'block_name': self.block_name,
            'total_appearances': self.total_appearances,
            'fire_rate': str(self.fire_rate),
            'recheck_success_rate': str(self.recheck_success_rate),
            'timing_success_rate': str(self.timing_success_rate),
            'win_rate': str(self.win_rate),
            'profit_factor': str(self.profit_factor),
            'avg_win': self.avg_win.to_string(),
            'avg_loss': self.avg_loss.to_string(),
            'avg_pnl_contribution': self.avg_pnl_contribution.to_string(),
            'risk_reward_ratio': str(self.risk_reward_ratio),
            'avg_position_size': self.avg_position_size.to_string(),
            'max_position_size': self.max_position_size.to_string(),
            'avg_hold_time': self.avg_hold_time,
            'volatility_preference': self.volatility_preference,
            'volume_preference': self.volume_preference,
            'trend_strength_preference': self.trend_strength_preference,
            'best_session': self.best_session,
            'correlation_with_wins': str(self.correlation_with_wins),
            'correlation_with_pnl': str(self.correlation_with_pnl),
            'highly_correlated_signals': self.highly_correlated_signals,
            'weight': str(self.weight)
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'NautilusSignalWeightMetrics':
        """Create from dictionary"""
        return cls(
            signal_name=data['signal_name'],
            block_name=data['block_name'],
            total_appearances=data['total_appearances'],
            fire_rate=Decimal(data['fire_rate']),
            recheck_success_rate=Decimal(data['recheck_success_rate']),
            timing_success_rate=Decimal(data['timing_success_rate']),
            win_rate=Decimal(data['win_rate']),
            profit_factor=Decimal(data['profit_factor']),
            avg_win=Money.from_string(data['avg_win']),
            avg_loss=Money.from_string(data['avg_loss']),
            avg_pnl_contribution=Money.from_string(data['avg_pnl_contribution']),
            risk_reward_ratio=Decimal(data['risk_reward_ratio']),
            avg_position_size=Quantity.from_string(data['avg_position_size']),
            max_position_size=Quantity.from_string(data['max_position_size']),
            avg_hold_time=data['avg_hold_time'],
            volatility_preference=data['volatility_preference'],
            volume_preference=data['volume_preference'],
            trend_strength_preference=data['trend_strength_preference'],
            best_session=data['best_session'],
            correlation_with_wins=Decimal(data['correlation_with_wins']),
            correlation_with_pnl=Decimal(data['correlation_with_pnl']),
            highly_correlated_signals=data['highly_correlated_signals'],
            weight=Decimal(data['weight'])
        )
```

**Testing**:
```python
def test_nautilus_weight_metrics():
    """Test NautilusTrader type handling in metrics"""
    metrics = NautilusSignalWeightMetrics(
        signal_name='HOD_REJECTION',
        block_name='hod',
        total_appearances=100,
        fire_rate=Decimal('0.4'),
        recheck_success_rate=Decimal('0.8'),
        timing_success_rate=Decimal('0.9'),
        win_rate=Decimal('0.65'),
        profit_factor=Decimal('2.5'),
        avg_win=Money('100', 'USD'),
        avg_loss=Money('-50', 'USD'),
        avg_pnl_contribution=Money('75', 'USD'),
        risk_reward_ratio=Decimal('2'),
        avg_position_size=Quantity('0.1'),
        max_position_size=Quantity('1.0'),
        avg_hold_time=12,
        volatility_preference='high',
        volume_preference='high',
        trend_strength_preference='strong',
        best_session='London',
        correlation_with_wins=Decimal('0.8'),
        correlation_with_pnl=Decimal('0.7'),
        highly_correlated_signals=['RSI_OVERBOUGHT'],
        weight=Decimal('0')  # Will be calculated
    )
    
    # Test weight calculation
    weight = metrics.calculate_weight()
    assert isinstance(weight, Decimal)
    assert Decimal('0') <= weight <= Decimal('100')
    
    # Test serialization
    data = metrics.to_dict()
    restored = NautilusSignalWeightMetrics.from_dict(data)
    
    # Verify types
    assert isinstance(restored.avg_win, Money)
    assert isinstance(restored.avg_position_size, Quantity)
    assert isinstance(restored.win_rate, Decimal)
    assert isinstance(restored.weight, Decimal)
    
    # Verify values
    assert restored.avg_win == metrics.avg_win
    assert restored.avg_position_size == metrics.avg_position_size
    assert restored.win_rate == metrics.win_rate
```

**Acceptance Criteria**:
- [ ] Uses NautilusTrader types throughout
- [ ] Comprehensive metrics calculation
- [ ] Proper decimal arithmetic
- [ ] Market condition tracking
- [ ] Correlation analysis
- [ ] Weight calculation (0-100)
- [ ] Serialization/deserialization
- [ ] 100% test coverage
- [ ] Zero floating point arithmetic

**Sign-off**: ☐ Developer ☐ Lead ☐ NautilusTrader Expert

---

### **Task 2.2.3: NautilusTrader Weight Integration**
**Duration**: 6 hours  
**Dependencies**: 2.2.2

**Implementation**:
```python
from nautilus_trader.model.objects import Quantity, Price, Money
from decimal import Decimal
from typing import Dict, Optional

class NautilusWeightIntegrator:
    """Integrate building block and optimizer weights"""
    
    def __init__(self):
        self.weight_calculator = NautilusWeightCalculator()
        self.logger = OptimizerLogger('weight_integrator')
    
    def integrate_weights(self,
                        block_name: str,
                        signal_name: str,
                        block_weight: Decimal,
                        optimizer_metrics: dict) -> Optional[Decimal]:
        """Integrate building block weight with optimizer metrics"""
        try:
            # Register signal if visible in UI
            self.weight_calculator.register_visible_signal(signal_name, block_name)
            
            # Set building block weight
            self.weight_calculator.set_block_weight(
                block_name=block_name,
                signal_name=signal_name,
                weight=block_weight
            )
            
            # Calculate optimizer weight
            optimizer_weight = self._calculate_optimizer_weight(optimizer_metrics)
            if optimizer_weight is not None:
                self.weight_calculator.set_optimizer_weight(
                    block_name=block_name,
                    signal_name=signal_name,
                    weight=optimizer_weight
                )
            
            # Get final weight
            return self.weight_calculator.calculate_final_weight(
                block_name=block_name,
                signal_name=signal_name
            )
            
        except Exception as e:
            self.logger.error(f"Weight integration failed: {str(e)}")
            return None
    
    def _calculate_optimizer_weight(self, metrics: dict) -> Optional[Decimal]:
        """Calculate optimizer weight from metrics"""
        try:
            # Extract core metrics
            win_rate = Decimal(str(metrics.get('win_rate', 0)))
            profit_factor = Decimal(str(metrics.get('profit_factor', 1)))
            risk_reward = Decimal(str(metrics.get('risk_reward_ratio', 1)))
            market_alignment = Decimal(str(metrics.get('market_alignment', 0)))
            
            # Calculate components
            effectiveness = win_rate * Decimal('40')  # 40% weight
            profitability = min(profit_factor, Decimal('3')) * Decimal('20')  # 20% weight
            risk_management = min(risk_reward, Decimal('3')) * Decimal('20')  # 20% weight
            market_fit = market_alignment * Decimal('20')  # 20% weight
            
            # Calculate total weight
            total_weight = (
                effectiveness +
                profitability +
                risk_management +
                market_fit
            )
            
            # Clamp to valid range
            return max(Decimal('0'), min(Decimal('100'), total_weight))
            
        except Exception as e:
            self.logger.error(f"Optimizer weight calculation failed: {str(e)}")
            return None
```

**Testing**:
```python
def test_nautilus_weight_integrator():
    """Test weight integration with NautilusTrader types"""
    integrator = NautilusWeightIntegrator()
    
    # Test data
    block_name = 'hod_rejection'
    signal_name = 'hod_signal'
    block_weight = Decimal('75')
    optimizer_metrics = {
        'win_rate': '0.65',
        'profit_factor': '2.2',
        'risk_reward_ratio': '1.8',
        'market_alignment': '0.8'
    }
    
    # Test integration
    final_weight = integrator.integrate_weights(
        block_name=block_name,
        signal_name=signal_name,
        block_weight=block_weight,
        optimizer_metrics=optimizer_metrics
    )
    
    # Verify result
    assert isinstance(final_weight, Decimal)
    assert Decimal('0') <= final_weight <= Decimal('100')
    
    # Test optimizer weight calculation
    optimizer_weight = integrator._calculate_optimizer_weight(optimizer_metrics)
    assert isinstance(optimizer_weight, Decimal)
    assert Decimal('0') <= optimizer_weight <= Decimal('100')
    
    # Test with missing metrics
    assert integrator._calculate_optimizer_weight({}) == Decimal('0')
```

**Acceptance Criteria**:
- [ ] Uses NautilusTrader types throughout
- [ ] Integrates building block weights
- [ ] Calculates optimizer weights
- [ ] Proper decimal arithmetic
- [ ] Handles visible signals only
- [ ] Weight validation and clamping
- [ ] Error handling and logging
- [ ] 100% test coverage
- [ ] Zero floating point arithmetic

**Sign-off**: ☐ Developer ☐ Lead ☐ NautilusTrader Expert

---

### **Task 2.2.4-2.2.6: Database Tables**
**Duration**: 6 hours total  
**Dependencies**: 2.2.3

See OPTIMIZER_V3_SIGNAL_INTELLIGENCE.md → "Database Schema" for complete table definitions:
- Signal Events Table
- Signal Metrics Table  
- Strategy Results Table

**Sign-off**: ☐ Developer ☐ Lead ☐ DBA

---

### **Task 2.2.7: Signal Effectiveness Analyzer**
**Duration**: 5 hours  
**Dependencies**: 2.2.6

**Implementation**: See OPTIMIZER_V3_SIGNAL_INTELLIGENCE.md → "Signal Intelligence Framework"

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 2.2.8: Warning System**
**Duration**: 3 hours  
**Dependencies**: 2.2.7

**Implementation**: Detect signals with weight < 40 and generate alerts

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 2.2.9-2.2.12: Core Analytics**
**Duration**: 12 hours total

- 2.2.9: Event recorder (record EVERY signal)
- 2.2.10: Metrics calculator (aggregate events → metrics)
- 2.2.11: DB optimization (indexes from schema)
- 2.2.12: Correlation analyzer

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 2.2.13: Dashboard UI**
**Duration**: 6 hours  
**Dependencies**: 2.2.12

**Implementation**: See OPTIMIZER_V3_SIGNAL_INTELLIGENCE.md → "Signal Performance Dashboard"

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

class SignalDashboardUI(QMainWindow):
    """Signal intelligence dashboard with consistent styling"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Signal Intelligence Dashboard")
        self.setStyleSheet(WINDOW_STYLE)
        self.setup_ui()
    
    def setup_ui(self):
        central = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(SPACING_UNIT)
        
        # Charts panel with consistent styling
        charts_panel = QWidget()
        charts_panel.setStyleSheet(PANEL_STYLE)
        charts_layout = QVBoxLayout()
        charts_layout.setSpacing(SPACING_UNIT)
        
        # Performance chart
        perf_chart = PlotlyChart()
        perf_chart.setStyleSheet(CHART_STYLE)
        charts_layout.addWidget(perf_chart)
        
        # Weight distribution chart
        weight_chart = PlotlyChart()
        weight_chart.setStyleSheet(CHART_STYLE)
        charts_layout.addWidget(weight_chart)
        
        # Correlation matrix
        corr_matrix = PlotlyChart()
        corr_matrix.setStyleSheet(CHART_STYLE)
        charts_layout.addWidget(corr_matrix)
        
        charts_panel.setLayout(charts_layout)
        layout.addWidget(charts_panel)
        
        # Metrics table
        metrics_table = QTableWidget()
        metrics_table.setStyleSheet(TABLE_STYLE)
        metrics_table.setFont(create_font())
        layout.addWidget(metrics_table)
        
        central.setLayout(layout)
        self.setCentralWidget(central)
```

**Acceptance Criteria**:
- [ ] Uses WINDOW_STYLE from styles.py
- [ ] Uses PANEL_STYLE for chart containers
- [ ] Uses CHART_STYLE for Plotly charts
- [ ] Uses TABLE_STYLE for metrics table
- [ ] Proper spacing from SPACING_UNIT
- [ ] Consistent fonts using create_font
- [ ] Dark theme compatible
- [ ] No hardcoded styles
- [ ] Visual match with Window 1-4

**Sign-off**: ☐ Developer ☐ Lead ☐ UI Designer

---

### **Task 2.2.14-2.2.18: Visualizations & Export**
**Duration**: 15 hours total

- 2.2.14: Performance charts (time series)
- 2.2.15: Weight distribution (bar chart)
- 2.2.16: Correlation matrix (heatmap)
- 2.2.17: Trade impact (scatter plot)
- 2.2.18: CSV/JSON export

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 2.2.19-2.2.22: Testing & Sign-off**
**Duration**: 10 hours total

- 2.2.19: Integration tests (end-to-end recording)
- 2.2.20: Accuracy validation (vs ground truth)
- 2.2.21: Unit tests (95% coverage + data validation)
- 2.2.22: Sprint sign-off

**Sign-off**: ☐ Developer ☐ Lead ☐ Architect

---

### **Task 2.2.23: Signal Correlation Analyzer**
**Duration**: 2 hours  
**Dependencies**: 2.2.22

**Implementation**:
```python
class SignalCorrelationAnalyzer:
    """Analyze relationships between signals"""
    
    def __init__(self):
        self.signal_db = SignalDatabase()
    
    def analyze_correlations(self) -> pd.DataFrame:
        """Calculate correlation matrix between signals"""
        events = self.signal_db.get_all_events()
        
        # Create time series for each signal
        signal_series = {}
        for event in events:
            if event.signal_name not in signal_series:
                signal_series[event.signal_name] = []
            signal_series[event.signal_name].append({
                'timestamp': event.timestamp,
                'fired': event.did_fire
            })
        
        df = pd.DataFrame(signal_series)
        corr_matrix = df.corr()
        return corr_matrix
```

**Acceptance Criteria**:
- [ ] Correlation matrix calculated for all signals
- [ ] Values between -1 and 1
- [ ] Identifies highly correlated signal pairs (>0.7)

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 2.2.24: Time-of-Day Effectiveness Analysis**
**Duration**: 2 hours  
**Dependencies**: 2.2.23

**Implementation**:
```python
def analyze_time_of_day_effectiveness(signal_name: str) -> dict:
    """Analyze signal effectiveness by hour of day"""
    
    events = db.query(f"""
        SELECT EXTRACT(HOUR FROM timestamp) as hour,
               COUNT(*) as total,
               AVG(CASE WHEN did_fire THEN 1 ELSE 0 END) as fire_rate,
               AVG(CASE WHEN trade_outcome='win' THEN 1 ELSE 0 END) as win_rate
        FROM signal_events
        WHERE signal_name = '{signal_name}'
        GROUP BY EXTRACT(HOUR FROM timestamp)
        ORDER BY hour
    """)
    
    # Identify best hours (Asia/London/NY sessions)
    best_hours = events.nlargest(3, 'win_rate')
    
    return {
        'hourly_stats': events,
        'best_hours': best_hours,
        'asia_performance': events[(events.hour >= 0) & (events.hour < 8)].mean(),
        'london_performance': events[(events.hour >= 8) & (events.hour < 16)].mean(),
        'ny_performance': events[(events.hour >= 16) & (events.hour < 24)].mean()
    }
```

**Acceptance Criteria**:
- [ ] Breakdown by hour (0-23)
- [ ] Session analysis (Asia/London/NY)
- [ ] Identifies best trading hours

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 2.2.25: Volatility Regime Performance**
**Duration**: 2 hours  
**Dependencies**: 2.2.24

**Implementation**:
```python
def analyze_volatility_regime_performance(signal_name: str) -> dict:
    """Analyze signal performance in different volatility regimes"""
    
    events = db.get_events_with_market_data(signal_name)
    
    # Calculate ATR for each event
    for event in events:
        atr = calculate_atr(event.market_data, period=14)
        event.atr = atr
    
    # Classify volatility regimes (33rd and 66th percentiles)
    atr_values = [e.atr for e in events]
    low_threshold = np.percentile(atr_values, 33)
    high_threshold = np.percentile(atr_values, 66)
    
    low_vol = [e for e in events if e.atr < low_threshold]
    med_vol = [e for e in events if low_threshold <= e.atr < high_threshold]
    high_vol = [e for e in events if e.atr >= high_threshold]
    
    return {
        'low_volatility': calculate_regime_stats(low_vol),
        'medium_volatility': calculate_regime_stats(med_vol),
        'high_volatility': calculate_regime_stats(high_vol),
        'recommendation': get_best_regime(low_vol, med_vol, high_vol)
    }
```

**Acceptance Criteria**:
- [ ] Classifies events into low/med/high volatility (ATR-based)
- [ ] Performance metrics per regime
- [ ] Recommends optimal volatility conditions

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 2.2.26: Trend Strength Analysis**
**Duration**: 2 hours  
**Dependencies**: 2.2.25

**Implementation**:
```python
def analyze_trend_strength_impact(signal_name: str) -> dict:
    """Analyze how trend strength affects signal performance"""
    
    events = db.get_events_with_market_data(signal_name)
    
    for event in events:
        adx = calculate_adx(event.market_data, period=14)
        event.adx = adx
        event.trend_strength = 'strong' if adx > 25 else 'weak'
    
    strong_trend = [e for e in events if e.trend_strength == 'strong']
    weak_trend = [e for e in events if e.trend_strength == 'weak']
    
    return {
        'strong_trend_stats': {
            'win_rate': sum(1 for e in strong_trend if e.trade_outcome=='win') / len(strong_trend),
            'avg_adx': np.mean([e.adx for e in strong_trend])
        },
        'weak_trend_stats': {
            'win_rate': sum(1 for e in weak_trend if e.trade_outcome=='win') / len(weak_trend),
            'avg_adx': np.mean([e.adx for e in weak_trend])
        },
        'correlation': calculate_correlation(
            [e.adx for e in events], 
            [1 if e.trade_outcome=='win' else 0 for e in events]
        )
    }
```

**Acceptance Criteria**:
- [ ] ADX calculated for each event (trend strength)
- [ ] Performance in strong vs weak trends
- [ ] Correlation coefficient between ADX and win rate

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 2.2.27: Volume Profile Impact**
**Duration**: 2 hours  
**Dependencies**: 2.2.26

**Implementation**:
```python
def analyze_volume_impact(signal_name: str) -> dict:
    """Analyze how volume affects signal effectiveness"""
    
    events = db.get_events_with_market_data(signal_name)
    
    for event in events:
        vol_sma = calculate_sma([e.volume for e in event.market_data], period=20)
        event.volume_ratio = event.volume / vol_sma
        event.volume_category = (
            'high' if event.volume_ratio > 1.5 else
            'normal' if event.volume_ratio > 0.7 else
            'low'
        )
    
    high_vol = [e for e in events if e.volume_category == 'high']
    normal_vol = [e for e in events if e.volume_category == 'normal']
    low_vol = [e for e in events if e.volume_category == 'low']
    
    return {
        'high_volume_stats': calculate_regime_stats(high_vol),
        'normal_volume_stats': calculate_regime_stats(normal_vol),
        'low_volume_stats': calculate_regime_stats(low_vol)
    }
```

**Acceptance Criteria**:
- [ ] Volume classified (vs 20-period SMA)
- [ ] Performance per volume regime
- [ ] Recommendation on optimal volume conditions

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 2.2.28: Multi-Timeframe Correlation**
**Duration**: 2 hours  
**Dependencies**: 2.2.27

**Implementation**:
```python
def analyze_multi_timeframe_correlation(signal_name: str) -> dict:
    """Analyze signal correlation across timeframes"""
    
    timeframes = ['15m', '1h', '4h', '1D']
    correlations = {}
    
    for tf1 in timeframes:
        correlations[tf1] = {}
        events_tf1 = db.get_events_by_timeframe(signal_name, tf1)
        
        for tf2 in timeframes:
            if tf1 != tf2:
                events_tf2 = db.get_events_by_timeframe(signal_name, tf2)
                aligned = align_timeframes(events_tf1, events_tf2)
                
                correlations[tf1][tf2] = calculate_correlation(
                    [e.did_fire for e in aligned.tf1_events],
                    [e.did_fire for e in aligned.tf2_events]
                )
    
    return {
        'correlation_matrix': correlations,
        'strongest_pairs': sorted(
            [(tf1, tf2, corr) for tf1, corrs in correlations.items() 
             for tf2, corr in corrs.items()],
            key=lambda x: abs(x[2]),
            reverse=True
        )[:5]
    }
```

**Acceptance Criteria**:
- [ ] Correlation for all timeframe pairs
- [ ] Identifies strongest correlations (top 5)

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 2.2.29: Signal Degradation Detection**
**Duration**: 2 hours  
**Dependencies**: 2.2.28

**Implementation**:
```python
def detect_signal_degradation(signal_name: str, window_days: int = 30) -> dict:
    """Detect if signal performance is degrading over time"""
    
    events = db.query(f"""
        SELECT DATE(timestamp) as date,
               AVG(CASE WHEN trade_outcome='win' THEN 1 ELSE 0 END) as win_rate
        FROM signal_events
        WHERE signal_name = '{signal_name}'
          AND timestamp >= NOW() - INTERVAL '{window_days * 2} days'
        GROUP BY DATE(timestamp)
        ORDER BY date
    """)
    
    # Split into old vs recent periods
    midpoint = len(events) // 2
    old_period = events[:midpoint]
    recent_period = events[midpoint:]
    
    old_win_rate = old_period['win_rate'].mean()
    recent_win_rate = recent_period['win_rate'].mean()
    
    # Calculate trend (linear regression)
    from scipy.stats import linregress
    x = range(len(events))
    slope,intercept, r_value, p_value, std_err = linregress(x, events['win_rate'])
    
    return {
        'is_degrading': slope < -0.001 and p_value < 0.05,
        'old_win_rate': old_win_rate,
        'recent_win_rate': recent_win_rate,
        'delta': recent_win_rate - old_win_rate,
        'trend_slope': slope,
        'trend_confidence': 1 - p_value
    }
```

**Acceptance Criteria**:
- [ ] Compares old vs recent performance
- [ ] Statistical significance testing
- [ ] Trend detection via linear regression

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 2.2.30: Adaptive Weight Adjustment**
**Duration**: 3 hours  
**Dependencies**: 2.2.29

**Implementation**:
```python
class AdaptiveWeightAdjuster:
    """Dynamically adjust signal weights based on recent performance"""
    
    def __init__(self, decay_factor: float = 0.95):
        self.decay_factor = decay_factor
    
    def adjust_weights(self, signal_name: str) -> float:
        """Calculate time-weighted signal weight"""
        
        events = db.get_events_ordered_by_time(signal_name)
        
        # Apply exponential decay (recent events = higher weight)
        weighted_wins = 0
        weighted_total = 0
        
        for i, event in enumerate(reversed(events)):
            weight = self.decay_factor ** i
            weighted_total += weight
            
            if event.trade_outcome == 'win':
                weighted_wins += weight
        
        time_weighted_win_rate = weighted_wins / weighted_total if weighted_total > 0 else 0
        
        # Calculate adjusted weight
        base_weight = calculate_signal_weight(signal_name)
        adjustment_factor = time_weighted_win_rate / event.historical_win_rate if event.historical_win_rate > 0 else 1
        
        adjusted_weight = base_weight * adjustment_factor
        
        return max(0, min(100, adjusted_weight))  # Clamp to [0, 100]
```

**Acceptance Criteria**:
- [ ] Implements exponential decay
- [ ] Recent performance weighted higher
- [ ] Adjusted weight clamped to [0, 100]

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 2.2.31: Real-Time Monitoring Dashboard**
**Duration**: 3 hours  
**Dependencies**: 2.2.30

**Implementation**:
```python
class RealTimeMonitoringDashboard:
    """Real-time dashboard for signal performance"""
    
    def __init__(self):
        self.app = Dash(__name__)
        self.setup_layout()
    
    def setup_layout(self):
        self.app.layout = html.Div([
            dcc.Interval(id='interval-component', interval=5000),  # 5s refresh
            html.H1('Signal Intelligence - Live Monitor'),
            
            html.Div(id='live-metrics'),
            dcc.Graph(id='live-performance-chart'),
            dcc.Graph(id='live-weight-distribution')
        ])
        
        @self.app.callback(
            [Output('live-metrics', 'children'),
             Output('live-performance-chart', 'figure'),
             Output('live-weight-distribution', 'figure')],
            [Input('interval-component', 'n_intervals')]
        )
        def update_dashboard(n):
            # Fetch latest metrics
            metrics = db.get_latest_metrics()
            
            # Create live charts
            perf_chart = create_performance_timeline(metrics)
            weight_chart = create_weight_distribution(metrics)
            
            return format_metrics_html(metrics), perf_chart, weight_chart
```

**Acceptance Criteria**:
- [ ] Auto-refreshes every 5 seconds
- [ ] Shows latest signal metrics
- [ ] Live performance charts

**Sign-off**: ☐ Developer ☐ Lead ☐ UI Designer

---

### **Task 2.2.32: Automated Recommendations Engine**
**Duration**: 2 hours  
**Dependencies**: 2.2.31

**Implementation**:
```python
from dataclasses import dataclass
from enum import Enum
from typing import List

class RecommendationType(Enum):
    REMOVE = "remove"
    ADD = "add"
    CONDITIONAL = "conditional"

@dataclass
class Recommendation:
    type: RecommendationType
    signal: str
    reason: str
    priority: str  # HIGH, MEDIUM, LOW
    estimated_impact: float

class AutomatedRecommendationsEngine:
    """Generate signal usage recommendations"""
    
    def __init__(self):
        self.db = SignalDatabase()
    
    def generate_recommendations(self, strategy_id: str) -> List[Recommendation]:
        """Analyze strategy and recommend improvements"""
        
        recommendations = []
        metrics = self.db.get_strategy_signal_metrics(strategy_id)
        
        for signal_metric in metrics:
            # Check if signal is underperforming
            if signal_metric.weight < 40:
                recommendations.append(Recommendation(
                    type=RecommendationType.REMOVE,
                    signal=signal_metric.signal_name,
                    reason=f'Low weight ({signal_metric.weight:.1f}), consider removing',
                    priority='HIGH',
                    estimated_impact=self._calculate_removal_impact(signal_metric)
                ))
            
            # Check if wrong market conditions
            current_regime = self._get_current_market_regime()
            if signal_metric.volatility_preference != current_regime:
                recommendations.append(Recommendation(
                    type=RecommendationType.CONDITIONAL,
                    signal=signal_metric.signal_name,
                    reason=f'Performs best in {signal_metric.volatility_preference} volatility (currently {current_regime})',
                    priority='MEDIUM',
                    estimated_impact=signal_metric.win_rate_delta
                ))
            
            # Check for missing high-correlation signals
            correlations = self.db.get_signal_correlations(signal_metric.signal_name)
            for corr in correlations:
                if corr.correlation > 0.7 and corr.signal_name not in [m.signal_name for m in metrics]:
                    recommendations.append(Recommendation(
                        type=RecommendationType.ADD,
                        signal=corr.signal_name,
                        reason=f'High correlation ({corr.correlation:.2f}) with existing signal {signal_metric.signal_name}',
                        priority='MEDIUM',
                        estimated_impact=self._calculate_addition_impact(corr)
                    ))
        
        # Sort by priority then impact
        priority_order = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
        return sorted(
            recommendations, 
            key=lambda x: (priority_order[x.priority], x.estimated_impact),
            reverse=True
        )
    
    def _calculate_removal_impact(self, metric: SignalMetric) -> float:
        """Estimate impact of removing signal"""
        return abs(metric.avg_pnl_contribution) * metric.fire_rate
    
    def _calculate_addition_impact(self, correlation: SignalCorrelation) -> float:
        """Estimate impact of adding signal"""
        return correlation.signal_weight * correlation.correlation
        
    def _get_current_market_regime(self) -> str:
        """Determine current volatility regime"""
        recent_atr = self.db.get_recent_atr(days=7)
        if recent_atr > 0.03:
            return 'high'
        elif recent_atr > 0.015:
            return 'medium'
        else:
            return 'low'
```

**Acceptance Criteria**:
- [ ] Generates 3 types of recommendations (REMOVE/ADD/CONDITIONAL)
- [ ] Prioritizes by HIGH/MEDIUM/LOW
- [ ] Provides clear reasoning for each recommendation
- [ ] Estimates impact of each recommendation

**Sign-off**: ☐ Developer ☐ Lead

---

## 🚨 EXIT CONDITION INTEGRATION (Sprint 1.8 Dependency)

**CRITICAL**: Sprint 1.8 introduces Exit Conditions which MUST be tracked by the Signal Intelligence system.
Without these tasks, exit conditions will not be analyzed, creating a gap in signal intelligence.

### **Task 2.2.33: Exit Condition Event Tracking**
**Duration**: 4 hours  
**Dependencies**: 2.2.1, Sprint 1.8 complete

**Purpose**: Extend NautilusSignalEvent to track exit condition events

**Implementation**:
```python
from enum import Enum

class SignalEventType(Enum):
    """Type of signal event"""
    ENTRY = "entry"           # Entry signal (Add as AND/OR)
    EXIT_CONDITION = "exit_condition"  # Exit condition signal (Add as Exit)

@dataclass
class NautilusSignalEvent:
    """UPDATED: Record of signal occurrence with Exit Condition support"""
    signal_name: str
    block_name: str
    timestamp: datetime
    instrument_id: InstrumentId
    price_at_signal: Price
    fired: bool
    
    # NEW: Signal event type (entry vs exit condition)
    event_type: SignalEventType = SignalEventType.ENTRY
    
    # NEW: Exit condition specific fields
    exit_mode: Optional[str] = None  # "ABSOLUTE" or "FLEXIBLE"
    exit_percentage: Optional[Decimal] = None  # 0.0-1.0
    binding_level: Optional[str] = None  # "STRATEGY", "BLOCK", "SIGNAL"
    was_deferred: bool = False  # FLEXIBLE mode deferral
    deferral_resolved_by: Optional[str] = None  # "TP1", "TP2", "reversal", etc.
    
    # ... existing fields ...
```

**Database Update**:
```sql
ALTER TABLE signal_events ADD COLUMN event_type VARCHAR(20) DEFAULT 'entry';
ALTER TABLE signal_events ADD COLUMN exit_mode VARCHAR(20);
ALTER TABLE signal_events ADD COLUMN exit_percentage DECIMAL(5,4);
ALTER TABLE signal_events ADD COLUMN binding_level VARCHAR(20);
ALTER TABLE signal_events ADD COLUMN was_deferred BOOLEAN DEFAULT false;
ALTER TABLE signal_events ADD COLUMN deferral_resolved_by VARCHAR(50);
```

**Acceptance Criteria**:
- [ ] SignalEventType enum added
- [ ] NautilusSignalEvent extended with exit condition fields
- [ ] Database schema updated for exit condition tracking
- [ ] Both entry and exit events recorded properly
- [ ] Exit mode (ABSOLUTE/FLEXIBLE) tracked
- [ ] Binding level (STRATEGY/BLOCK/SIGNAL) tracked

**Sign-off**: ☐ Developer ☐ Lead ☐ NautilusTrader Expert

---

### **Task 2.2.34: Exit Condition Effectiveness Metrics**
**Duration**: 4 hours  
**Dependencies**: 2.2.33

**Purpose**: Calculate effectiveness metrics for exit conditions

**Implementation**:
```python
@dataclass
class ExitConditionMetrics:
    """Metrics specific to exit condition effectiveness"""
    exit_condition_name: str
    binding_level: str  # STRATEGY, BLOCK, SIGNAL
    exit_mode: str  # ABSOLUTE, FLEXIBLE
    
    # Occurrence metrics
    total_triggers: int
    trigger_rate: Decimal  # How often exit condition fires
    
    # Performance metrics
    avg_exit_price_vs_entry: Decimal  # % gain/loss at exit
    avg_exit_price_vs_tp1: Decimal  # How close to TP1
    exits_better_than_sl: int  # Count of exits better than SL
    exits_worse_than_tp1: int  # Count of exits worse than TP1
    
    # FLEXIBLE mode specific
    deferred_count: int
    deferral_to_tp_rate: Decimal  # % of deferrals that hit TP
    deferral_to_reversal_rate: Decimal  # % that triggered reversal
    avg_deferral_duration: int  # bars
    
    # PnL impact
    total_pnl_contribution: Money
    avg_pnl_per_exit: Money
    pnl_vs_holding_to_tp: Money  # Comparison: exit vs waiting for TP
    
    # Recommendations
    suggested_percentage_adjustment: Optional[Decimal] = None
    suggested_mode_change: Optional[str] = None
    
    def calculate_effectiveness_score(self) -> Decimal:
        """Calculate exit condition effectiveness 0-100"""
        # Score based on:
        # 1. Better than SL rate (30%)
        # 2. PnL contribution (30%)
        # 3. Deferral resolution rate for FLEXIBLE (20%)
        # 4. Optimal timing (20%)
        ...
```

**Acceptance Criteria**:
- [ ] ExitConditionMetrics dataclass created
- [ ] Calculates trigger rate
- [ ] Compares exit price to entry/TP/SL
- [ ] Tracks FLEXIBLE mode deferral stats
- [ ] Calculates PnL contribution
- [ ] Provides improvement suggestions

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 2.2.35: Exit Condition Dashboard Section**
**Duration**: 3 hours  
**Dependencies**: 2.2.34

**Purpose**: Add exit condition analysis section to Signal Intelligence Dashboard

**Implementation**:
```python
class ExitConditionDashboardSection(QWidget):
    """Dashboard section for exit condition analysis"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Section header with red theme (EXIT_BUTTON_STYLE from styles.py)
        header = QLabel("🔴 EXIT CONDITION ANALYSIS")
        header.setStyleSheet(EXIT_SECTION_HEADER_STYLE)
        layout.addWidget(header)
        
        # Exit condition metrics table
        self.exit_table = QTableWidget()
        self.exit_table.setColumnCount(8)
        self.exit_table.setHorizontalHeaderLabels([
            'Exit Condition', 'Binding Level', 'Mode', 'Triggers',
            'Avg Exit vs Entry', 'Better than SL', 'PnL Contribution', 'Score'
        ])
        layout.addWidget(self.exit_table)
        
        # FLEXIBLE vs ABSOLUTE comparison chart
        self.mode_comparison_chart = PlotlyChart()
        layout.addWidget(self.mode_comparison_chart)
        
        # Deferral resolution pie chart (for FLEXIBLE mode)
        self.deferral_chart = PlotlyChart()
        layout.addWidget(self.deferral_chart)
        
        self.setLayout(layout)
    
    def update_metrics(self, exit_metrics: List[ExitConditionMetrics]):
        """Refresh dashboard with exit condition data"""
        self._update_table(exit_metrics)
        self._update_mode_comparison(exit_metrics)
        self._update_deferral_chart(exit_metrics)
```

**Acceptance Criteria**:
- [ ] Exit condition section added to dashboard
- [ ] Uses red theme from styles.py
- [ ] Shows all exit condition metrics
- [ ] FLEXIBLE vs ABSOLUTE comparison chart
- [ ] Deferral resolution visualization

**Sign-off**: ☐ Developer ☐ Lead ☐ UI Designer

---

### **Task 2.2.36: Exit Condition Correlation Analysis**
**Duration**: 3 hours  
**Dependencies**: 2.2.35

**Purpose**: Analyze correlations between exit conditions and entry signals

**Implementation**:
```python
class ExitConditionCorrelationAnalyzer:
    """Analyze exit condition correlations"""
    
    def analyze_exit_entry_correlation(self, strategy_id: str) -> Dict:
        """Analyze correlation between exit conditions and entry signals"""
        
        results = {
            'exit_entry_correlations': {},  # Exit condition → Entry signal correlations
            'best_exit_per_entry': {},  # Recommend best exit for each entry signal
            'exit_timing_analysis': {},  # When exits fire relative to entries
        }
        
        # For each exit condition
        for exit_cond in self.db.get_exit_conditions(strategy_id):
            entry_correlations = {}
            
            for entry_signal in self.db.get_entry_signals(strategy_id):
                # Calculate: How effective is this exit when triggered by this entry?
                trades = self.db.get_trades_by_entry_and_exit(
                    entry_signal=entry_signal,
                    exit_condition=exit_cond.signal_name
                )
                
                if trades:
                    corr = {
                        'pnl_when_paired': sum(t.pnl for t in trades),
                        'win_rate_when_paired': len([t for t in trades if t.pnl > 0]) / len(trades),
                        'avg_exit_timing': sum(t.bars_to_exit for t in trades) / len(trades)
                    }
                    entry_correlations[entry_signal] = corr
            
            results['exit_entry_correlations'][exit_cond.signal_name] = entry_correlations
        
        return results
    
    def recommend_exit_conditions(self, entry_signal: str) -> List[str]:
        """Recommend best exit conditions for a given entry signal"""
        correlations = self.db.get_exit_correlations_for_entry(entry_signal)
        
        # Rank by effectiveness
        ranked = sorted(
            correlations.items(),
            key=lambda x: x[1]['win_rate_when_paired'] * x[1]['pnl_when_paired'],
            reverse=True
        )
        
        return [exit_name for exit_name, _ in ranked[:3]]
```

**Acceptance Criteria**:
- [ ] Exit-to-entry correlation calculated
- [ ] Best exit recommended per entry signal
- [ ] Exit timing analysis included
- [ ] Integrated with existing correlation matrix

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 2.2.37: Exit Condition Recommendations**
**Duration**: 2 hours  
**Dependencies**: 2.2.36

**Purpose**: Generate AI recommendations for exit condition improvements

**Implementation**:
```python
class ExitConditionRecommendationsEngine:
    """Generate exit condition improvement recommendations"""
    
    def generate_exit_recommendations(self, strategy_id: str) -> List[Recommendation]:
        """Analyze exit conditions and recommend improvements"""
        
        recommendations = []
        exit_metrics = self.db.get_exit_condition_metrics(strategy_id)
        
        for metric in exit_metrics:
            # Check if exit percentage is suboptimal
            if metric.exits_worse_than_tp1 > metric.exits_better_than_sl:
                recommendations.append(Recommendation(
                    type=RecommendationType.ADJUST_EXIT_CONDITION,
                    signal=metric.exit_condition_name,
                    reason=f'Exit triggering too early. {metric.exits_worse_than_tp1} exits below TP1.',
                    priority='HIGH',
                    config={'new_percentage': metric.suggested_percentage_adjustment}
                ))
            
            # Check FLEXIBLE mode effectiveness
            if metric.exit_mode == 'FLEXIBLE':
                deferral_success = metric.deferral_to_tp_rate
                if deferral_success < Decimal('0.3'):
                    recommendations.append(Recommendation(
                        type=RecommendationType.ADJUST_EXIT_CONDITION,
                        signal=metric.exit_condition_name,
                        reason=f'FLEXIBLE mode deferral success rate too low ({deferral_success:.1%}). Consider ABSOLUTE mode.',
                        priority='MEDIUM',
                        config={'mode_change': 'ABSOLUTE'}
                    ))
            
            # Check ABSOLUTE mode - could benefit from FLEXIBLE
            if metric.exit_mode == 'ABSOLUTE':
                # If many exits happen close to TP, suggest FLEXIBLE
                close_to_tp_rate = metric.total_triggers > 0 and (
                    metric.exits_worse_than_tp1 / metric.total_triggers > 0.5
                )
                if close_to_tp_rate:
                    recommendations.append(Recommendation(
                        type=RecommendationType.ADJUST_EXIT_CONDITION,
                        signal=metric.exit_condition_name,
                        reason=f'Many exits close to TP. FLEXIBLE mode could improve results.',
                        priority='MEDIUM',
                        config={'mode_change': 'FLEXIBLE'}
                    ))
            
            # Check for underperforming exit conditions
            if metric.calculate_effectiveness_score() < Decimal('40'):
                recommendations.append(Recommendation(
                    type=RecommendationType.REMOVE,
                    signal=metric.exit_condition_name,
                    reason=f'Exit condition effectiveness score ({metric.calculate_effectiveness_score():.1f}) below threshold.',
                    priority='HIGH',
                    estimated_impact=metric.total_pnl_contribution.as_decimal()
                ))
        
        return recommendations
```

**Acceptance Criteria**:
- [ ] Generates percentage adjustment recommendations
- [ ] Suggests ABSOLUTE ↔ FLEXIBLE mode changes
- [ ] Identifies underperforming exit conditions
- [ ] Integrates with existing recommendations engine
- [ ] Uses ADJUST_EXIT_CONDITION type from Sprint 1.8

**Sign-off**: ☐ Developer ☐ Lead

---

## 🎯 SPRINT SIGN-OFF

**Complete When**:
- [ ] All 37 tasks done (32 original + 5 exit condition tasks)
- [ ] All signals tracked (entry AND exit conditions)
- [ ] Exit condition dashboard section functional
- [ ] Exit condition recommendations generated
- [ ] Dashboard functional
- [ ] 100% coverage

**Sign-off**: ☐ Developer ☐ Lead ☐ Architect

**Next Sprint**: `SPRINT_2_3_ML_GENERATOR.md`
