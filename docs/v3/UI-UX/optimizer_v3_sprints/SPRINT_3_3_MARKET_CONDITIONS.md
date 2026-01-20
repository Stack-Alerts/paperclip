# SPRINT 3.3: MARKET CONDITION FILTERS
**Session Detection, Volatility Regimes, Time-of-Day Analysis**

**Duration**: 3 days  
**Tasks**: 12  
**Dependencies**: Sprint 3.2 complete  
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

**Purpose**: Optimize based on market conditions:
- Session detection (Asia/London/NY)
- Volatility regime classifier
- Trend vs range detection
- Time-of-day optimization
- Filter UI

---

## ✅ TASK CHECKLIST

- [ ] 3.3.1 Session detector
- [ ] 3.3.2 Volatility regime detector
- [ ] 3.3.3 Trend vs range classifier
- [ ] 3.3.4 Time-of-day optimizer
- [ ] 3.3.5 Filter UI
- [ ] 3.3.6 Integration tests
- [ ] 3.3.7 Accuracy validation
- [ ] 3.3.8 Write all tests
- [ ] 3.3.9 Documentation
- [ ] 3.3.10 Phase 3 complete sign-off
- [ ] 3.3.11-3.3.12 Extended analysis (2 tasks)

---

## 📝 TASK DETAILS

### **Environment Configuration**
**Duration**: 1 hour  
**Dependencies**: Sprint 3.2 complete

**Implementation**:
```bash
# Add to .env file

# Session Analysis Configuration
SESSION_ASIA_START=0  # UTC hour
SESSION_ASIA_END=8  # UTC hour
SESSION_LONDON_START=8  # UTC hour
SESSION_LONDON_END=16  # UTC hour
SESSION_NY_START=16  # UTC hour
SESSION_NY_END=24  # UTC hour
SESSION_OVERLAP_BUFFER=1  # hour buffer for session overlap

# Volatility Analysis Configuration
VOL_ATR_PERIOD=14  # ATR calculation period
VOL_LOOKBACK=180  # days for volatility analysis
VOL_LOW_THRESHOLD=0.8  # ratio for low volatility
VOL_HIGH_THRESHOLD=1.2  # ratio for high volatility
VOL_UPDATE_INTERVAL=300  # seconds between updates
VOL_MIN_SAMPLES=50  # minimum samples for analysis

# Trend Analysis Configuration
TREND_MIN_STRENGTH=0.6  # minimum trend strength
TREND_LOOKBACK=20  # bars for trend analysis
TREND_ADX_PERIOD=14  # ADX calculation period
TREND_MIN_MOVEMENT=0.001  # minimum price movement
TREND_UPDATE_INTERVAL=300  # seconds between updates

# Volume Analysis Configuration
VOL_MA_PERIOD=20  # volume moving average period
VOL_HIGH_RATIO=1.5  # ratio for high volume
VOL_LOW_RATIO=0.5  # ratio for low volume
VOL_MIN_SAMPLES=50  # minimum samples for analysis
VOL_UPDATE_INTERVAL=300  # seconds between updates

# Time-of-Day Analysis
TOD_INTERVAL=60  # minutes per interval
TOD_MIN_TRADES=20  # minimum trades per interval
TOD_MIN_SAMPLES=50  # minimum samples per interval
TOD_UPDATE_INTERVAL=3600  # seconds between updates
TOD_HISTORY_DAYS=180  # days of historical data

# Market Regime Configuration
REGIME_MIN_SAMPLES=100  # minimum samples for regime
REGIME_UPDATE_INTERVAL=3600  # seconds between updates
REGIME_TRANSITION_THRESHOLD=0.7  # regime change threshold
REGIME_MIN_DURATION=3600  # seconds minimum regime duration
REGIME_HISTORY_LENGTH=180  # days of regime history

# Filter Configuration
FILTER_MIN_TRADES=30  # minimum trades for filter
FILTER_MIN_IMPROVEMENT=0.05  # minimum improvement required
FILTER_MAX_REDUCTION=0.3  # maximum trade reduction
FILTER_UPDATE_INTERVAL=3600  # seconds between updates
FILTER_CACHE_TIMEOUT=300  # seconds to cache results

# Performance Requirements
PERF_MIN_TRADES_SESSION=5  # minimum trades per session
PERF_MIN_WIN_RATE=0.55  # minimum win rate required
PERF_MIN_PROFIT_FACTOR=1.5  # minimum profit factor
PERF_MAX_DRAWDOWN=0.10  # maximum drawdown allowed
PERF_MIN_SHARPE=1.5  # minimum Sharpe ratio

# Resource Management
RESOURCE_MAX_MEMORY=4096  # MB maximum memory usage
RESOURCE_MAX_CPU=90  # maximum CPU usage
RESOURCE_CHECK_INTERVAL=60  # seconds between checks
RESOURCE_CLEANUP_ENABLED=true  # auto cleanup
RESOURCE_BACKUP_ENABLED=true  # backup before changes

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
LOG_PATH=logs/market_conditions
LOG_ROTATION=5  # number of files to keep
LOG_MAX_SIZE=10  # MB per log file
```

**Configuration Loading**:
```python
from dotenv import load_dotenv
import os
from decimal import Decimal
from typing import Dict, Any

def get_market_config() -> Dict[str, Any]:
    """Load market conditions configuration from environment"""
    load_dotenv()
    
    return {
        'sessions': {
            'asia_start': int(os.getenv('SESSION_ASIA_START')),
            'asia_end': int(os.getenv('SESSION_ASIA_END')),
            'london_start': int(os.getenv('SESSION_LONDON_START')),
            'london_end': int(os.getenv('SESSION_LONDON_END')),
            'ny_start': int(os.getenv('SESSION_NY_START')),
            'ny_end': int(os.getenv('SESSION_NY_END')),
            'overlap_buffer': int(os.getenv('SESSION_OVERLAP_BUFFER'))
        },
        'volatility': {
            'atr_period': int(os.getenv('VOL_ATR_PERIOD')),
            'lookback': int(os.getenv('VOL_LOOKBACK')),
            'low_threshold': float(os.getenv('VOL_LOW_THRESHOLD')),
            'high_threshold': float(os.getenv('VOL_HIGH_THRESHOLD')),
            'update_interval': int(os.getenv('VOL_UPDATE_INTERVAL')),
            'min_samples': int(os.getenv('VOL_MIN_SAMPLES'))
        },
        'trend': {
            'min_strength': float(os.getenv('TREND_MIN_STRENGTH')),
            'lookback': int(os.getenv('TREND_LOOKBACK')),
            'adx_period': int(os.getenv('TREND_ADX_PERIOD')),
            'min_movement': float(os.getenv('TREND_MIN_MOVEMENT')),
            'update_interval': int(os.getenv('TREND_UPDATE_INTERVAL'))
        },
        'volume': {
            'ma_period': int(os.getenv('VOL_MA_PERIOD')),
            'high_ratio': float(os.getenv('VOL_HIGH_RATIO')),
            'low_ratio': float(os.getenv('VOL_LOW_RATIO')),
            'min_samples': int(os.getenv('VOL_MIN_SAMPLES')),
            'update_interval': int(os.getenv('VOL_UPDATE_INTERVAL'))
        },
        'time_of_day': {
            'interval': int(os.getenv('TOD_INTERVAL')),
            'min_trades': int(os.getenv('TOD_MIN_TRADES')),
            'min_samples': int(os.getenv('TOD_MIN_SAMPLES')),
            'update_interval': int(os.getenv('TOD_UPDATE_INTERVAL')),
            'history_days': int(os.getenv('TOD_HISTORY_DAYS'))
        },
        'regime': {
            'min_samples': int(os.getenv('REGIME_MIN_SAMPLES')),
            'update_interval': int(os.getenv('REGIME_UPDATE_INTERVAL')),
            'transition_threshold': float(os.getenv('REGIME_TRANSITION_THRESHOLD')),
            'min_duration': int(os.getenv('REGIME_MIN_DURATION')),
            'history_length': int(os.getenv('REGIME_HISTORY_LENGTH'))
        },
        'filter': {
            'min_trades': int(os.getenv('FILTER_MIN_TRADES')),
            'min_improvement': float(os.getenv('FILTER_MIN_IMPROVEMENT')),
            'max_reduction': float(os.getenv('FILTER_MAX_REDUCTION')),
            'update_interval': int(os.getenv('FILTER_UPDATE_INTERVAL')),
            'cache_timeout': int(os.getenv('FILTER_CACHE_TIMEOUT'))
        },
        'performance': {
            'min_trades_session': int(os.getenv('PERF_MIN_TRADES_SESSION')),
            'min_win_rate': float(os.getenv('PERF_MIN_WIN_RATE')),
            'min_profit_factor': float(os.getenv('PERF_MIN_PROFIT_FACTOR')),
            'max_drawdown': float(os.getenv('PERF_MAX_DRAWDOWN')),
            'min_sharpe': float(os.getenv('PERF_MIN_SHARPE'))
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

### **Task 3.3.1: NautilusTrader Market Condition Analyzer**
**Duration**: 6 hours  
**Dependencies**: Sprint 3.2 complete

**Implementation**:
```python
from nautilus_trader.model.objects import Quantity, Price, Money
from nautilus_trader.model.identifiers import InstrumentId
from decimal import Decimal
import numpy as np
from datetime import datetime, timezone

class NautilusMarketAnalyzer:
    """Market condition analysis with NautilusTrader types"""
    
    def __init__(self, logger: OptimizerLogger):
        self.logger = logger
        self.instrument_id = InstrumentId('BTC-USD')
    
    def analyze_market_conditions(self, data: dict) -> dict:
        """Analyze current market conditions"""
        try:
            # Convert price data to NautilusTrader types
            prices = [Price(str(p)) for p in data['prices']]
            volumes = [Quantity(str(v)) for v in data['volumes']]
            
            # Analyze conditions
            session = self._detect_session(data['timestamp'])
            volatility = self._calculate_volatility(prices)
            trend = self._detect_trend(prices)
            volume_profile = self._analyze_volume(volumes)
            
            return {
                'session': session,
                'volatility_regime': self._classify_volatility(volatility),
                'trend_strength': volatility['trend_strength'],
                'is_trending': trend['is_trending'],
                'trend_direction': trend['direction'],
                'volume_profile': volume_profile,
                'metrics': {
                    'atr': Money(str(volatility['atr']), 'USD'),
                    'volatility_ratio': Decimal(str(volatility['ratio'])),
                    'trend_score': Decimal(str(trend['score'])),
                    'volume_ratio': Decimal(str(volume_profile['ratio']))
                }
            }
            
        except Exception as e:
            self.logger.error(f"Market analysis failed: {str(e)}")
            raise
    
    def _detect_session(self, timestamp: datetime) -> str:
        """Detect trading session with timezone awareness"""
        utc_hour = timestamp.astimezone(timezone.utc).hour
        
        # Convert to major session times
        if 0 <= utc_hour < 8:
            return 'ASIA'
        elif 8 <= utc_hour < 16:
            return 'LONDON'
        else:
            return 'NY'
    
    def _calculate_volatility(self, prices: List[Price]) -> dict:
        """Calculate volatility metrics with NautilusTrader types"""
        # Calculate True Range
        tr_values = []
        for i in range(1, len(prices)):
            high = prices[i].as_decimal()
            low = prices[i-1].as_decimal()
            close = prices[i-1].as_decimal()
            
            tr = max(
                high - low,
                abs(high - close),
                abs(low - close)
            )
            tr_values.append(tr)
        
        # Calculate ATR
        atr = sum(tr_values) / len(tr_values) if tr_values else Decimal('0')
        
        # Calculate volatility ratio (current vs historical)
        current_vol = tr_values[-5:] if len(tr_values) >= 5 else tr_values
        historical_vol = tr_values[:-5] if len(tr_values) >= 5 else tr_values
        
        vol_ratio = (
            sum(current_vol) / len(current_vol) /
            (sum(historical_vol) / len(historical_vol))
            if historical_vol else Decimal('1')
        )
        
        # Calculate trend strength using ADX-like measure
        dx_values = self._calculate_directional_movement(prices)
        trend_strength = sum(dx_values) / len(dx_values) if dx_values else Decimal('0')
        
        return {
            'atr': atr,
            'ratio': vol_ratio,
            'trend_strength': trend_strength
        }
    
    def _detect_trend(self, prices: List[Price]) -> dict:
        """Detect trend with NautilusTrader types"""
        price_changes = []
        for i in range(1, len(prices)):
            change = prices[i].as_decimal() - prices[i-1].as_decimal()
            price_changes.append(change)
        
        # Calculate trend score
        up_moves = sum(1 for x in price_changes if x > 0)
        down_moves = sum(1 for x in price_changes if x < 0)
        
        trend_score = Decimal(str(abs(up_moves - down_moves) / len(price_changes)))
        is_trending = trend_score > Decimal('0.6')
        direction = 'UP' if up_moves > down_moves else 'DOWN'
        
        return {
            'is_trending': is_trending,
            'direction': direction,
            'score': trend_score
        }
    
    def _analyze_volume(self, volumes: List[Quantity]) -> dict:
        """Analyze volume profile with NautilusTrader types"""
        # Calculate volume moving average
        period = 20
        if len(volumes) < period:
            return {'ratio': Decimal('1')}
        
        current_vol = volumes[-1].as_decimal()
        avg_vol = sum(v.as_decimal() for v in volumes[-period:]) / period
        
        return {
            'ratio': current_vol / avg_vol if avg_vol > 0 else Decimal('1')
        }
    
    def _classify_volatility(self, volatility: dict) -> str:
        """Classify volatility regime"""
        ratio = volatility['ratio']
        if ratio < Decimal('0.8'):
            return 'LOW'
        elif ratio > Decimal('1.2'):
            return 'HIGH'
        else:
            return 'NORMAL'
    
    def _calculate_directional_movement(self, prices: List[Price]) -> List[Decimal]:
        """Calculate directional movement for trend strength"""
        dm_values = []
        for i in range(1, len(prices)):
            high_diff = prices[i].as_decimal() - prices[i-1].as_decimal()
            low_diff = prices[i-1].as_decimal() - prices[i].as_decimal()
            
            if high_diff > low_diff:
                dm_values.append(high_diff)
            else:
                dm_values.append(Decimal('0'))
        
        return dm_values
```

**Testing**:
```python
def test_nautilus_market_analyzer():
    """Test market analysis with NautilusTrader types"""
    analyzer = NautilusMarketAnalyzer(OptimizerLogger('test'))
    
    # Test data
    data = {
        'timestamp': datetime.now(timezone.utc),
        'prices': ['50000', '50100', '49900', '50200', '50150'],
        'volumes': ['100', '120', '80', '150', '90']
    }
    
    # Test analysis
    result = analyzer.analyze_market_conditions(data)
    
    # Verify session detection
    assert result['session'] in ['ASIA', 'LONDON', 'NY']
    
    # Verify volatility metrics
    assert isinstance(result['metrics']['atr'], Money)
    assert isinstance(result['metrics']['volatility_ratio'], Decimal)
    assert result['volatility_regime'] in ['LOW', 'NORMAL', 'HIGH']
    
    # Verify trend detection
    assert isinstance(result['metrics']['trend_score'], Decimal)
    assert isinstance(result['is_trending'], bool)
    assert result['trend_direction'] in ['UP', 'DOWN']
    
    # Verify volume analysis
    assert isinstance(result['metrics']['volume_ratio'], Decimal)
```

**Acceptance Criteria**:
- [ ] Uses NautilusTrader types throughout
- [ ] Session detection with timezone handling
- [ ] Volatility analysis with proper types
- [ ] Trend detection with Decimal arithmetic
- [ ] Volume analysis with Quantity type
- [ ] Market regime classification
- [ ] Comprehensive metrics with proper types
- [ ] 95%+ test coverage
- [ ] Zero floating point arithmetic

**Sign-off**: ☐ Developer ☐ Lead ☐ NautilusTrader Expert

---

### **Task 3.3.2-3.3.10: Filters, UI & Testing**
**Duration**: 18 hours total

**UI Implementation**:
```python
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QCheckBox
from src.strategy_builder.ui.styles import (
    WINDOW_STYLE,
    PANEL_STYLE,
    GROUPBOX_STYLE,
    CHECKBOX_STYLE,
    SPACING_UNIT,
    create_font,
    PRIMARY_COLOR,
    SECONDARY_COLOR
)

class MarketConditionFiltersUI(QWidget):
    """Market condition filters with consistent styling"""
    
    def __init__(self):
        super().__init__()
        self.setStyleSheet(WINDOW_STYLE)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(SPACING_UNIT)
        
        # Session filters
        session_group = QGroupBox("Trading Sessions")
        session_group.setStyleSheet(GROUPBOX_STYLE)
        session_group.setFont(create_font())
        
        session_layout = QVBoxLayout()
        session_layout.setSpacing(SPACING_UNIT)
        
        for session in ['Asia', 'London', 'NY']:
            checkbox = QCheckBox(session)
            checkbox.setStyleSheet(CHECKBOX_STYLE)
            checkbox.setFont(create_font())
            session_layout.addWidget(checkbox)
        
        session_group.setLayout(session_layout)
        
        # Volatility filters
        vol_group = QGroupBox("Volatility Regime")
        vol_group.setStyleSheet(GROUPBOX_STYLE)
        vol_group.setFont(create_font())
        
        vol_layout = QVBoxLayout()
        vol_layout.setSpacing(SPACING_UNIT)
        
        for regime in ['Low', 'Normal', 'High']:
            checkbox = QCheckBox(regime)
            checkbox.setStyleSheet(CHECKBOX_STYLE)
            checkbox.setFont(create_font())
            vol_layout.addWidget(checkbox)
        
        vol_group.setLayout(vol_layout)
        
        # Add all components
        layout.addWidget(session_group)
        layout.addWidget(vol_group)
        self.setLayout(layout)
```

**Tasks**:
- 3.3.2: Volatility regime detector (ATR-based)
- 3.3.3: Trend/range classifier
- 3.3.4: Time optimization
- 3.3.5: Filter UI with styles.py
- 3.3.6-3.3.9: Testing & docs
- 3.3.10: Phase 3 sign-off

**UI Acceptance Criteria**:
- [ ] Uses WINDOW_STYLE from styles.py
- [ ] Uses GROUPBOX_STYLE for containers
- [ ] Uses CHECKBOX_STYLE for filters
- [ ] Proper spacing from SPACING_UNIT
- [ ] Consistent fonts using create_font
- [ ] Dark theme compatible
- [ ] No hardcoded styles
- [ ] Visual match with Window 1-4

**Sign-off**: ☐ Developer ☐ Lead ☐ Architect

---

### **Task 3.3.11-3.3.12: Extended**
**Duration**: 4 hours total

- Market regime transitions
- Documentation

**Sign-off**: ☐ Developer ☐ Lead

---

## 🎯 SPRINT SIGN-OFF

**Complete When**:
- [ ] All 12 tasks done
- [ ] All Phase 3 complete (42 tasks)

**Sign-off**: ☐ Developer ☐ Lead ☐ Architect

**Next Phase**: `SPRINT_4_1_SYSTEM_INTEGRATION.md` (Phase 4 - Final)
