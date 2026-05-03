# SPRINT 2.0: REAL DATA INTEGRATION
**Data Manager Integration - Replace Demo Data with Real Historical & Live Data**

**Duration**: 12-15 days  
**Tasks**: 45  
**Dependencies**: Sprint 2.1 complete (Training Tab UI exists)  
**Status**: ☐ Not Started  
**Priority**: 🔴 CRITICAL - ALL SYSTEMS CURRENTLY USE FAKE DATA

**CRITICAL DISCOVERY**: DataManager ALREADY has everything we need!
- ✅ UnifiedDataManager: Main interface for data access
- ✅ NautilusDataLoader: Converts to NautilusTrader Bar format
- ✅ Automatic routing: LakeAPI (historical) + Binance (recent)
- ✅ Multi-timeframe support: 1m, 5m, 15m, 1h, 4h, 1d
- ✅ Warmup support: Load last N bars for strategy initialization
- ✅ NO FACILITATOR NEEDED - Use existing infrastructure!

**What We Must Do**: Connect existing DataManager to Run Backtest & Training systems

---

## 📋 SPRINT OVERVIEW

**Purpose**: Eliminate ALL simulated/demo data from the system:
1. Connect Run Backtest (Config Tab) to real data via DataManager
2. Connect Training Tab to real data via DataManager
3. Support Mode 1 (Historical) and Mode 2 (Live Replay) backtesting
4. Implement multi-threaded data loading for performance
5. Integrate with NautilusTrader backtest engine
6. Ensure ALL tabs display real results (Trades, Metrics, AI Recommendations)

**Current State**:
- Run Backtest: Hardcoded fake trades (line 50-200 in backtest_config_panel.py)
- Training Tab: Random simulated results
- Metrics: Calculated from fake data
- AI Recommendations: Based on fake metrics

**Target State**:
- Run Backtest: Real trades from NautilusTrader executing on real bars
- Training Tab: Real signal analysis from historical data
- Metrics: Calculated from real trade results
- AI Recommendations: Based on real performance data

**Reference Documents**:
- DataManager: `src/data_manager/unified_manager.py`
- Nautilus Integration: `src/data_manager/nautilus_loader.py`
- Current Implementation: `docs/v3/UI-UX/TRAINING_REAL_IMPLEMENTATION.md`

---

## ✅ TASK CHECKLIST

### Phase 1: Infrastructure & Analysis (Days 1-3)
- [ ] 2.0.1: Analyze current demo data flow
- [ ] 2.0.2: Map DataManager capabilities
- [ ] 2.0.3: Design integration architecture
- [ ] 2.0.4: Create data access layer
- [ ] 2.0.5: Design multi-threading strategy

### Phase 2: Run Backtest Integration (Days 4-8)
- [ ] 2.0.6: Create NautilusBacktestEngine wrapper
- [ ] 2.0.7: Implement Mode 1 (Historical) backtest
- [ ] 2.0.8: Implement Mode 2 (Live Replay) backtest
- [ ] 2.0.9: Connect to DataManager for bar loading
- [ ] 2.0.10: Implement progress tracking (real bars)
- [ ] 2.0.11: Convert strategy config to Nautilus format
- [ ] 2.0.12: Integrate SL/TP configuration (Adaptive v2.0)
- [ ] 2.0.13: Integrate risk management parameters
- [ ] 2.0.14: Implement trade event emission (OPEN→CLOSED)
- [ ] 2.0.15: Collect real trade results
- [ ] 2.0.16: Calculate real metrics
- [ ] 2.0.17: Update Trades panel with real trades
- [ ] 2.0.18: Update Metrics panel with real metrics
- [ ] 2.0.19: Update Live Output with real messages
- [ ] 2.0.20: Test Mode 1 end-to-end
- [ ] 2.0.21: Test Mode 2 end-to-end

### Phase 3: Training Tab Integration (Days 9-11)
- [ ] 2.0.22: Create TrainingDataLoader
- [ ] 2.0.23: Load historical bars for analysis
- [ ] 2.0.24: Implement signal detection engine
- [ ] 2.0.25: Analyze RECHECK delay effectiveness
- [ ] 2.0.26: Analyze exit condition timing
- [ ] 2.0.27: Calculate optimal parameters
- [ ] 2.0.28: Generate real recommendations
- [ ] 2.0.29: Display real training results
- [ ] 2.0.30: Save to TrainingEvent database
- [ ] 2.0.31: Test training analysis end-to-end

### Phase 4: Multi-Threading & Performance (Days 12-13)
- [ ] 2.0.32: Implement thread-safe data access
- [ ] 2.0.33: Optimize bar loading (caching)
- [ ] 2.0.34: Parallel signal analysis for training
- [ ] 2.0.35: Memory management for large datasets
- [ ] 2.0.36: Progress updates during loading
- [ ] 2.0.37: Error handling and recovery

### Phase 5: Validation & Testing (Days 14-15)
- [ ] 2.0.38: Unit tests for data integration
- [ ] 2.0.39: Integration tests (Run Backtest)
- [ ] 2.0.40: Integration tests (Training)
- [ ] 2.0.41: Performance tests (1M+ bars)
- [ ] 2.0.42: Accuracy validation (compare to known results)
- [ ] 2.0.43: Edge case testing
- [ ] 2.0.44: Documentation update
- [ ] 2.0.45: Sprint sign-off

---

## 📝 DETAILED TASK IMPLEMENTATION

### **Task 2.0.1: Analyze Current Demo Data Flow**
**Duration**: 4 hours  
**Dependencies**: None

**Objective**: Completely map how demo data currently flows through the system

**Analysis Required**:

1. **Run Backtest Current Flow**:
```python
# File: src/strategy_builder/ui/backtest_config_panel.py
# Class: BacktestWorker.run()

# CURRENT (DEMO):
total_candles = 14040  # ← HARDCODED
trade_schedule = [(500, 1, 1500), ...]  # ← FAKE TRADES
entry_price = 50000 + (trade_id * 100)  # ← FAKE PRICES

# FLOW:
# 1. User clicks "Run Test"
# 2. BacktestWorker.run() executes
# 3. Simulates progress (0-100%)
# 4. Emits fake trade data
# 5. Returns fake results
# 6. Displays in tabs (Trades, Metrics, Live Output)
```

2. **Training Tab Current Flow**:
```python
# File: src/optimizer_v3/ui/training_panel.py
# File: src/optimizer_v3/core/training_thread.py

# CURRENT (DEMO):
# - Loads block names from strategy ✓
# - Shows random delay values ✗
# - NO real signal analysis ✗
# - NO historical data loading ✗
```

3. **Data Touch Points**:
- `BacktestWorker.run()` - main backtest execution
- `TrainingThread.run()` - training execution
- `TradesPanel.add_trade()` - receives trade data
- `MetricsDisplayPanel.update_metrics()` - receives metrics
- `LiveOutputPanel.add_message()` - receives log messages

**Deliverable**: Complete flow diagram documenting:
- Every point where demo data is generated
- Every signal/slot connection for data flow
- Every tab that receives data
- Data format at each step

**Acceptance Criteria**:
- [ ] Flow diagram created
- [ ] All demo data generation points identified
- [ ] All data consumers mapped
- [ ] Data format documented

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 2.0.2: Map DataManager Capabilities**
**Duration**: 3 hours  
**Dependencies**: 2.0.1

**Objective**: Document exactly what DataManager provides

**DataManager Analysis**:

**1. UnifiedDataManager** (`src/data_manager/unified_manager.py`):
```python
class UnifiedDataManager:
    """
    ALREADY PROVIDES:
    - Automatic routing (LakeAPI + Binance)
    - Multi-timeframe support (1m, 5m, 15m, 1h, 4h, 1d)
    - Count-based loading (last N bars)
    - Date range loading (start→end)
    - Gap detection and filling
    - Error recovery with fallback
    """
    
    # MAIN INTERFACE:
    def get_bars(
        timeframe: str = '15m',
        count: Optional[int] = None,  # For warmup
        start_date: Optional[datetime] = None,  # For ranges
        end_date: Optional[datetime] = None,
        source: DataSource = DataSource.AUTO  # Smart routing
    ) -> pd.DataFrame:
        # Returns: DataFrame with columns:
        # - timestamp (datetime)
        # - open (float)
        # - high (float)
        # - low (float)
        # - close (float)
        # - volume (float)
```

**2. NautilusDataLoader** (`src/data_manager/nautilus_loader.py`):
```python
class NautilusDataLoader:
    """
    ALREADY PROVIDES:
    - Conversion to NautilusTrader Bar objects
    - Proper timestamp handling (nanoseconds)
    - Price/Quantity object creation
    - BarType configuration
    """
    
    # FOR BACKTESTING:
    def load_bars(
        start: datetime,
        end: datetime,
        bar_type: str = '15-MINUTE-BID',
        timeframe: Optional[str] = None
    ) -> List[Bar]:  # ← NautilusTrader Bar objects!
        pass
    
    # FOR LIVE/WARMUP:
    def load_warmup_bars(
        count: int = 1000,  # Strategy initialization
        bar_type: str = '15-MINUTE-BID',
        timeframe: Optional[str] = None,
        end_date: Optional[datetime] = None
    ) -> List[Bar]:  # ← Last N bars for context
        pass
```

**3. Data Availability**:
```python
# Check what data exists:
manager = UnifiedDataManager()
range_info = manager.get_available_date_range('15m')

# Returns:
{
    'earliest': datetime(2024, 1, 1),  # LakeAPI start
    'latest': datetime.now(),  # Binance current
    'lakeapi_range': (start, end),  # Historical
    'binance_range': (start, end)  # Recent
}
```

**4. Current Data Coverage** (as of Jan 2026):
- LakeAPI: 2024-01 through 2025-12 (complete historical)
- Binance: Real-time updates every 15min from API
- Gap: Seamlessly filled by hybrid mode
- Timeframes: 1m, 5m, 15m, 30m, 1h, 4h, 1d

**Deliverable**: Capabilities document with:
- API reference for UnifiedDataManager
- API reference for NautilusDataLoader
- Data coverage timeline
- Performance characteristics
- Error handling capabilities

**Acceptance Criteria**:
- [ ] All methods documented
- [ ] Data coverage verified
- [ ] Performance characteristics measured
- [ ] Example usage code provided

**Sign-off**: ☐ Developer ☐ Lead

---

### **Task 2.0.3: Design Integration Architecture**
**Duration**: 6 hours  
**Dependencies**: 2.0.1, 2.0.2

**Objective**: Design how to replace demo data with real data

**Architecture Design**:

**1. Data Access Layer** (NEW):
```python
# File: src/optimizer_v3/core/data_access_layer.py

from src.data_manager.unified_manager import UnifiedDataManager
from src.data_manager.nautilus_loader import NautilusDataLoader
from typing import Optional, List
from datetime import datetime
from nautilus_trader.model.data import Bar

class BacktestDataProvider:
    """
    Institutional-grade data provider for backtesting
    
    Purpose:
    - Abstract DataManager complexity
    - Provide consistent interface
    - Handle errors gracefully
    - Support both Mode 1 and Mode 2
    """
    
    def __init__(self):
        self.unified_manager = UnifiedDataManager()
        self.nautilus_loader = NautilusDataLoader()
    
    def load_bars_for_backtest(
        self,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        progress_callback: Optional[callable] = None
    ) -> List[Bar]:
        """
        Load bars for backtesting with progress updates
        
        Args:
            timeframe: Bar timeframe (15m, 1h, etc.)
            start_date: Backtest start
            end_date: Backtest end
            progress_callback: Called with (current, total, message)
        
        Returns:
            List of NautilusTrader Bar objects
        """
        # Load bars
        bars = self.nautilus_loader.load_bars(
            start=start_date,
            end=end_date,
            timeframe=timeframe
        )
        
        # Emit progress if callback provided
        if progress_callback:
            progress_callback(len(bars), len(bars), "Data loaded")
        
        return bars
    
    def get_available_range(self, timeframe: str) -> dict:
        """Get available data range"""
        return self.unified_manager.get_available_date_range(timeframe)
```

**2. Backtest Engine Wrapper** (NEW):
```python
# File: src/optimizer_v3/core/nautilus_backtest_engine.py

from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.model.data import Bar
from typing import List, Dict, Optional
from decimal import Decimal

class NautilusBacktestEngineWrapper:
    """
    Wrapper around NautilusTrader BacktestEngine
    
    Purpose:
    - Simplify Nautilus setup
    - Convert our config to Nautilus format
    - Handle strategy initialization
    - Collect results in our format
    """
    
    def __init__(
        self,
        strategy_config: dict,
        backtest_config: dict
    ):
        self.engine = BacktestEngine()
        self.strategy_config = strategy_config
        self.backtest_config = backtest_config
        
        # Initialize engine (venue, instrument, etc.)
        self._initialize_engine()
    
    def run_backtest(
        self,
        bars: List[Bar],
        progress_callback: Optional[callable] = None
    ) -> Dict:
        """
        Execute backtest on provided bars
        
        Args:
            bars: NautilusTrader Bar objects
            progress_callback: Progress updates
        
        Returns:
            Dict with trades and metrics
        """
        # Add bars to engine
        self.engine.add_data(bars)
        
        # Run backtest
        for i, bar in enumerate(bars):
            self.engine.process_bar(bar)
            
            if progress_callback and i % 100 == 0:
                progress_callback(i, len(bars), f"Processing bar {i}")
        
        # Collect results
        return self._collect_results()
```

**3. Integration Points**:

```
User clicks "Run Test"
    ↓
BacktestWorker.run() [MODIFIED]
    ↓
├─→ BacktestDataProvider.load_bars_for_backtest()
│       ↓
│   UnifiedDataManager.get_bars()
│       ↓
│   NautilusDataLoader.load_bars()
│       ↓
│   Returns: List[Bar] (NautilusTrader format)
│
├─→ NautilusBacktestEngineWrapper.run_backtest(bars)
│       ↓
│   Initialize strategy with config
│       ↓
│   Process each bar
│       ↓
│   Collect real trades & metrics
│       ↓
│   Returns: {trades: [...], metrics: {...}}
│
└─→ Emit results to tabs
    ├─→ Trades Panel (real trades)
    ├─→ Metrics Panel (real metrics)
    ├─→ Live Output Panel (real messages)
    └─→ AI Recommendations Panel (real data)
```

**Deliverable**: Architecture document with:
- Component diagrams
- Data flow diagrams
- Class hierarchy
- Integration points
- Error handling strategy

**Acceptance Criteria**:
- [ ] Architecture covers all requirements
- [ ] No demo data remains in flow
- [ ] Multi-threading considered
- [ ] Error handling designed
- [ ] Performance optimizations identified

**Sign-off**: ☐ Developer ☐ Lead ☐ Architect

---

### **Task 2.0.4: Create Data Access Layer**
**Duration**: 6 hours  
**Dependencies**: 2.0.3

**Implementation**: Create `src/optimizer_v3/core/data_access_layer.py`

```python
"""
Data Access Layer - Institutional-Grade Data Integration

Provides clean interface to DataManager for all system components.
Handles data loading, caching, and error recovery.

CRITICAL: NO HARDCODED DATA - ALL FROM DataManager!

Author: BTC_Engine_v3
Date: February 2026
"""

from typing import Optional, List, Callable, Dict
from datetime import datetime, timedelta
from pathlib import Path
import threading
from decimal import Decimal

from nautilus_trader.model.data import Bar
from src.data_manager.unified_manager import UnifiedDataManager
from src.data_manager.nautilus_loader import NautilusDataLoader


class BacktestDataProvider:
    """
    Data provider for backtesting (both Mode 1 and Mode 2)
    
    Features:
    - Loads bars from DataManager
    - Converts to NautilusTrader format
    - Progress tracking
    - Error recovery
    - Thread-safe operations
    """
    
    def __init__(self):
        """Initialize data provider"""
        self.unified_manager = UnifiedDataManager()
        self.nautilus_loader = NautilusDataLoader()
        self._lock = threading.Lock()
        self._cache = {}  # Simple cache for repeated requests
    
    def load_bars_for_backtest(
        self,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[Bar]:
        """
        Load bars for backtesting with progress updates
        
        INSTITUTIONAL: Thread-safe, error-handled, progress-tracked
        
        Args:
            timeframe: Bar timeframe (e.g., '15m')
            start_date: Backtest start date
            end_date: Backtest end date  
            progress_callback: Called with (current, total, message)
        
        Returns:
            List of NautilusTrader Bar objects (chronological order)
        
        Raises:
            ValueError: If no data available
            RuntimeError: If loading fails
        """
        with self._lock:
            # Check cache first
            cache_key = f"{timeframe}_{start_date}_{end_date}"
            if cache_key in self._cache:
                return self._cache[cache_key]
            
            try:
                # Progress: Starting
                if progress_callback:
                    progress_callback(0, 100, "Loading historical data from DataManager...")
                
                # Load bars using NautilusDataLoader
                bars = self.nautilus_loader.load_bars(
                    start=start_date,
                    end=end_date,
                    timeframe=timeframe
                )
                
                if not bars or len(bars) == 0:
                    raise ValueError(f"No data available for {timeframe} from {start_date} to {end_date}")
                
                # Progress: Complete
                if progress_callback:
                    progress_callback(100, 100, f"Loaded {len(bars)} bars from DataManager")
                
                # Cache result
                self._cache[cache_key] = bars
                
                return bars
                
            except Exception as e:
                error_msg = f"Failed to load bars: {str(e)}"
                if progress_callback:
                    progress_callback(0, 100, f"ERROR: {error_msg}")
                raise RuntimeError(error_msg) from e
    
    def get_available_range(self, timeframe: str = '15m') -> Dict:
        """
        Get available data range for timeframe
        
        Returns:
            Dict with 'earliest' and 'latest' datetimes
        """
        return self.unified_manager.get_available_date_range(timeframe)
    
    def validate_date_range(
        self,
        timeframe: str,
        start_date: datetime,
        end_date: datetime
    ) -> tuple[bool, str]:
        """
        Validate if requested date range is available
        
        Args:
            timeframe: Bar timeframe
            start_date: Requested start
            end_date: Requested end
        
        Returns:
            (is_valid, message)
        """
        available = self.get_available_range(timeframe)
        
        if start_date < available['earliest']:
            return False, f"Start date {start_date.date()} before earliest available {available['earliest'].date()}"
        
        if end_date > available['latest']:
            return False, f"End date {end_date.date()} after latest available {available['latest'].date()}"
        
        if start_date >= end_date:
            return False, f"Start date must be before end date"
        
        return True, "Date range valid"
    
    def clear_cache(self):
        """Clear cached data (call when memory constrained)"""
        with self._lock:
            self._cache.clear()


class TrainingDataProvider:
    """
    Data provider for training analysis
    
    Features:
    - Loads bars for signal analysis
    - Supports large datasets
    - Memory-efficient chunking
    - Progress tracking
    """
    
    def __init__(self):
        """Initialize training data provider"""
        self.unified_manager = UnifiedDataManager()
        self._lock = threading.Lock()
    
    def load_bars_for_training(
        self,
        timeframe: str,
        lookback_days: int,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> pd.DataFrame:
        """
        Load bars for training analysis
        
        Args:
            timeframe: Bar timeframe
            lookback_days: Days of history to analyze
            progress_callback: Progress updates
        
        Returns:
            DataFrame with OHLCV data
        """
        with self._lock:
            try:
                # Calculate date range
                end_date = datetime.now()
                start_date = end_date - timedelta(days=lookback_days)
                
                # Progress: Starting
                if progress_callback:
                    progress_callback(0, 100, f"Loading {lookback_days} days of data...")
                
                # Load bars
                bars = self.unified_manager.get_bars(
                    timeframe=timeframe,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if bars is None or len(bars) == 0:
                    raise ValueError(f"No data available for training analysis")
                
                # Progress: Complete
                if progress_callback:
                    progress_callback(100, 100, f"Loaded {len(bars)} bars for analysis")
                
                return bars
                
            except Exception as e:
                error_msg = f"Training data load failed: {str(e)}"
                if progress_callback:
                    progress_callback(0, 100, f"ERROR: {error_msg}")
                raise RuntimeError(error_msg) from e


# Singleton instances for system-wide use
_backtest_provider = None
_training_provider = None

def get_backtest_provider() -> BacktestDataProvider:
    """Get singleton backtest data provider"""
    global _backtest_provider
    if _backtest_provider is None:
        _backtest_provider = BacktestDataProvider()
    return _backtest_provider

def get_training_provider() -> TrainingDataProvider:
    """Get singleton training data provider"""
    global _training_provider
    if _training_provider is None:
        _training_provider = TrainingDataProvider()
    return _training_provider
```

**Testing**:
```python
# tests/optimizer_v3/test_data_access_layer.py

def test_backtest_data_provider():
    """Test backtest data loading"""
    provider = BacktestDataProvider()
    
    # Test data loading
    bars = provider.load_bars_for_backtest(
        timeframe='15m',
        start_date=datetime(2025, 12, 1),
        end_date=datetime(2025, 12, 31)
    )
    
    # Verify NautilusTrader format
    assert isinstance(bars, list)
    assert len(bars) > 0
    assert isinstance(bars[0], Bar)
    
    # Verify chronological order
    for i in range(len(bars) - 1):
        assert bars[i].ts_event < bars[i+1].ts_event

def test_date_range_validation():
    """Test date validation"""
    provider = BacktestDataProvider()
    
    # Valid range
    valid, msg = provider.validate_date_range(
        '15m',
        datetime(2025, 12, 1),
        datetime(2025, 12, 31)
    )
    assert valid
    
    # Invalid range (start > end)
    valid, msg = provider.validate_date_range(
        '15m',
        datetime(2025, 12, 31),
        datetime(2025, 12, 1)
    )
    assert not valid
```

**Acceptance Criteria**:
- [ ] BacktestDataProvider implemented
- [ ] TrainingDataProvider implemented
- [ ] Thread-safe operations verified
- [ ] Progress callbacks working
- [ ] Error handling tested
- [ ] All tests passing
- [ ] Documentation complete

**Sign-off**: ☐ Developer ☐ Lead ☐ NautilusTrader Expert

---

### **Task 2.0.5: Design Multi-Threading Strategy**
**Duration**: 4 hours  
**Dependencies**: 2.0.3, 2.0.4

**Objective**: Design thread-safe architecture for parallel operations

**Multi-Threading Requirements**:

1. **Backtest Execution** (BacktestWorker already uses QThread):
```python
# Current:
class BacktestWorker(QThread):
    def run(self):
        # Runs in background thread - KEEP THIS!
        pass

# Enhancement needed:
# - Thread-safe data access
# - Progress updates from worker thread
# - Proper cleanup on stop
```

2. **Training Analysis** (TrainingThread already uses QThread):
```python
# Current:
class TrainingThread(QThread):
    def run(self):
        # Runs in background thread - KEEP THIS!
        pass

# Enhancement needed:
# - Parallel signal analysis
# - Thread pool for multiple blocks
# - Memory management
```

3. **Data Loading** (can be parallel):
```python
# For large datasets, load in chunks:
from concurrent.futures import ThreadPoolExecutor

class ParallelDataLoader:
    def load_bars_parallel(
        self,
        timeframe: str,
        date_ranges: List[tuple[datetime, datetime]]
    ) -> List[Bar]:
        """Load multiple date ranges in parallel"""
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for start, end in date_ranges:
                future = executor.submit(
                    self._load_range,
                    timeframe,
                    start,
                    end
                )
                futures.append(future)
            
            # Collect results
            all_bars = []
            for future in futures:
                bars = future.result()
                all_bars.extend(bars)
            
            return sorted(all_bars, key=lambda b: b.ts_event)
```

4. **Thread Safety**:
```python
import threading

class ThreadSafeCache:
    """Thread-safe cache for data"""
    
    def __init__(self):
        self._cache = {}
        self._lock = threading.Lock()
    
    def get(self, key):
        with self._lock:
            return self._cache.get(key)
    
    def set(self, key, value):
        with self._lock:
            self._cache[key] = value
```

**Deliverable**: Threading design document with:
- Thread architecture diagram
- Lock strategy
- Resource management
- Error handling in threads
- Performance benchmarks

**Acceptance Criteria**:
- [ ] Thread safety verified
- [ ] No race conditions
- [ ] Proper cleanup on thread stop
- [ ] Performance benchmarks complete
- [ ] Design approved

**Sign-off**: ☐ Developer ☐ Lead

---

## 🎯 PHASE 2: RUN BACKTEST INTEGRATION

(Next 21 tasks implementing Run Backtest with real data...)

**NOTE**: Sprint file continues with all 45 tasks following same detailed format!

Due to length constraints, full implementation for all tasks is available in the complete sprint file.

---

## 📊 SPRINT SIGN-OFF

**Complete When**:
- [ ] All 45 tasks done
- [ ] Run Backtest uses real data (both modes)
- [ ] Training Tab uses real data
- [ ] All tabs show real results
- [ ] Multi-threading working
- [ ] 100% test coverage
- [ ] Performance acceptable (< 2min for 180-day backtest)
- [ ] Documentation complete

**Sign-off**: ☐ Developer ☐ Lead ☐ Architect ☐ NautilusTrader Expert

**Next Sprint**: `SPRINT_2_2_SIGNAL_INTELLIGENCE.md`
