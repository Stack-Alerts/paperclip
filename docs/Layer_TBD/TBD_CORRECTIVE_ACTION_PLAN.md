# TBD Layer - Corrective Action Plan

**Version**: 1.0  
**Date**: 2025-12-29  
**Purpose**: Systematic implementation and testing of TBD fixes  
**Target**: Production-ready implementation for next optimization cycle  
**Timeline**: 4 weeks

---

## EXECUTIVE SUMMARY

This document provides a **trackable, step-by-step action plan** to correct all identified implementation gaps in the TBD Layer. Each task includes:
- ✅ Acceptance criteria
- 🧪 Unit tests required
- 📊 Validation method
- ⏱️ Time estimate

**Root Issues Identified**:
1. Multi-timeframe scanning not implemented
2. Pattern-based TP/SL not implemented
3. Retest entry logic not implemented
4. Dynamic position management not implemented
5. Pattern detection parameters too strict

**Expected Outcome**: 75-150% returns (60-day periods) matching manual trading performance

---

## PROGRESS TRACKER

### Overall Status: 🔴 NOT STARTED

| Phase | Tasks | Status | ETA |
|-------|-------|--------|-----|
| Phase 1: Multi-TF Data & Scanning | 8 tasks | ⬜ 0% | Week 1 |
| Phase 2: Pattern-Based Targets | 6 tasks | ⬜ 0% | Week 1-2 |
| Phase 3: Retest Entry Logic | 7 tasks | ⬜ 0% | Week 2 |
| Phase 4: Dynamic Management | 6 tasks | ⬜ 0% | Week 2-3 |
| Phase 5: Enhanced Detection | 5 tasks | ⬜ 0% | Week 3 |
| Phase 6: Validation & Testing | 8 tasks | ⬜ 0% | Week 3-4 |
| Phase 7: Optimization Integration | 4 tasks | ⬜ 0% | Week 4 |

**Total Tasks**: 44  
**Completed**: 0  
**Remaining**: 44

---

## PHASE 1: MULTI-TIMEFRAME DATA & SCANNING

**Goal**: Load 1H, 2H and 4H data, implement multi-TF pattern scanning  
**Priority**: P0 (Blocking)  
**Timeline**: Week 1 (Days 1-3)  
**Expected Impact**: 10-40x performance improvement

### Task 1.1: Update Walk-Forward Script - Load Multi-TF Data

**File**: `scripts/layer_testing/walk_forward_tbd.py`

**Status**: ⬜ NOT STARTED

**Implementation**:
```python
# Around line 50-80 where data is loaded

# Load 15min data (execution timeframe)
logger.info(f"Loading 15min data...")
full_data_15m = dp.load_data('BTC/USDT', '15m', start_date, end_date)

# NEW: Load 1H data (pattern detection)
logger.info(f"Loading 1H data...")
full_data_1h = dp.load_data('BTC/USDT', '1h', start_date, end_date)

# NEW: Load 2H data (pattern detection)
logger.info(f"Loading 2H data...")
full_data_2h = dp.load_data('BTC/USDT', '2h', start_date, end_date)

# NEW: Load 4H data (pattern detection)
logger.info(f"Loading 4H data...")
full_data_4h = dp.load_data('BTC/USDT', '4h', start_date, end_date)

logger.info(f"Loaded data:")
logger.info(f"  15min: {len(full_data_15m)} candles")
logger.info(f"  1H: {len(full_data_1h)} candles")
logger.info(f"  2H: {len(full_data_2h)} candles")
logger.info(f"  4H: {len(full_data_4h)} candles")
```

**Acceptance Criteria**:
- ✅ 15min, 1H, 2H, and 4H data loaded successfully
- ✅ All dataframes have required columns (OHLCV)
- ✅ Timestamp alignment verified across timeframes
- ✅ Log output confirms data sizes

**Unit Test**: `tests/test_layer_tbd_multitf.py::test_data_loading`
```python
def test_multi_timeframe_data_loading():
    """Test loading 15m, 1H, 2H, 4H data"""
    from scripts.layer_testing.walk_forward_tbd import load_all_timeframes
    
    start = pd.Timestamp('2025-01-01')
    end = pd.Timestamp('2025-01-31')
    
    data_15m, data_1h, data_2h, data_4h = load_all_timeframes('BTC/USDT', start, end)
    
    # Check all loaded
    assert len(data_15m) > 0
    assert len(data_1h) > 0
    assert len(data_2h) > 0
    assert len(data_4h) > 0
    
    # Check OHLCV columns
    for df in [data_15m, data_1h, data_2h, data_4h]:
        assert all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume'])
    
    # Check timeframe ratios (4H should be ~16x less than 15m)
    ratio = len(data_15m) / len(data_4h)
    assert 12 <= ratio <= 20  # Allow some variance
```

**Time Estimate**: 2 hours

---

### Task 1.2: Add Indicators to Multi-TF Data

**File**: `scripts/layer_testing/walk_forward_tbd.py`

**Status**: ⬜ NOT STARTED

**Implementation**:
```python
# After loading data, add indicators to each timeframe

from src.core.indicator_engine import IndicatorEngine

ie = IndicatorEngine()

# Add indicators to 15min
logger.info("Adding indicators to 15min data...")
full_data_15m = ie.add_indicators(full_data_15m, timeframe='15m')

# NEW: Add indicators to 1H
logger.info("Adding indicators to 1H data...")
full_data_1h = ie.add_indicators(full_data_21, timeframe='1h')

# NEW: Add indicators to 2H
logger.info("Adding indicators to 2H data...")
full_data_2h = ie.add_indicators(full_data_2h, timeframe='2h')

# NEW: Add indicators to 4H
logger.info("Adding indicators to 4H data...")
full_data_4h = ie.add_indicators(full_data_4h, timeframe='4h')

logger.info("Indicators added to all timeframes")
```

**Acceptance Criteria**:
- ✅ ATR indicator present on all timeframes
- ✅ Volume indicators present on all timeframes
- ✅ SMA/EMA indicators present on all timeframes
- ✅ No NaN values in recent candles

**Unit Test**: `tests/test_layer_tbd_multitf.py::test_indicators_multi_tf`
```python
def test_indicators_on_all_timeframes():
    """Test indicators are added correctly to all TFs"""
    from src.core.indicator_engine import IndicatorEngine
    
    ie = IndicatorEngine()
    
    # Load sample data
    data_15m = load_sample_data('15m')
    data_1h = load_sample_data('1h')
    data_2h = load_sample_data('2h')
    data_4h = load_sample_data('4h')
    
    # Add indicators
    data_15m = ie.add_indicators(data_15m, timeframe='15m')
    data_1h = ie.add_indicators(data_1h, timeframe='1h')
    data_2h = ie.add_indicators(data_2h, timeframe='2h')
    data_4h = ie.add_indicators(data_4h, timeframe='4h')
    
    # Check required indicators exist
    required = ['atr', 'volume_sma', 'sma_50']
    
    for df in [data_15m, data_1h, data_2h, data_4h]:
        for ind in required:
            assert ind in df.columns, f"Missing {ind}"
            assert not df[ind].iloc[-20:].isna().all(), f"{ind} has all NaN"
```

**Time Estimate**: 2 hours

---

### Task 1.3: Update Layer TBD - Add Multi-TF Data Storage

**File**: `src/layers/layer_tbd_method.py`

**Status**: ⬜ NOT STARTED

**Implementation**:
```python
# In LayerTBD class __init__ or near top

class LayerTBD(BaseLayer):
    def __init__(self, config: TBDConfig):
        super().__init__(config)
        self.config = config
        
        # NEW: Multi-timeframe data storage
        self.data_15m = None
        self.data_1h = None
        self.data_2h = None
        self.data_4h = None
        self.current_idx = 0
        
        # NEW: Pattern tracker for retest logic (Phase 3)
        self.pending_patterns = []
        
        logger.info("LayerTBD initialized with multi-timeframe support")
    
    def set_multi_timeframe_data(self, data_15m, data_1h, data_2h, data_4h):
        """
        Set data for all timeframes
        
        Args:
            data_15m: 15-minute OHLCV data with indicators
            data_1h: 1-hour OHLCV data with indicators
            data_2h: 2-hour OHLCV data with indicators
            data_4h: 4-hour OHLCV data with indicators
        """
        self.data_15m = data_15m.copy()
        self.data_1h = data_1h.copy()
        self.data_2h = data_2h.copy()
        self.data_4h = data_4h.copy()
        
        logger.info(f"Multi-TF data set: 15m={len(data_15m)}, "
                   f"1H={len(data_1h)}, 2H={len(data_2h)}, 4H={len(data_4h)}")
```

**Acceptance Criteria**:
- ✅ Method `set_multi_timeframe_data()` exists
- ✅ Data is stored in instance variables
- ✅ Data is copied (not referenced)
- ✅ Logging confirms data sizes

**Unit Test**: `tests/test_layer_tbd_multitf.py::test_set_multi_tf_data`
```python
def test_set_multi_timeframe_data():
    """Test setting multi-TF data on layer"""
    from src.layers.layer_tbd_method import LayerTBD
    from config.strategies.layer_tbd_only import TBDConfig
    
    config = TBDConfig()
    layer = LayerTBD(config)
    
    # Create sample data
    data_15m = create_sample_ohlcv(100, '15m')
    data_1h = create_sample_ohlcv(50, '1h')
    data_2h = create_sample_ohlcv(20, '2h')
    data_4h = create_sample_ohlcv(10, '4h')
    
    # Set data
    layer.set_multi_timeframe_data(data_15m, data_1h, data_2h, data_4h)
    
    # Verify stored
    assert layer.data_15m is not None
    assert layer.data_1h is not None
    assert layer.data_2h is not None
    assert layer.data_4h is not None
    
    assert len(layer.data_15m) == 100
    assert len(layer.data_1h) == 50
    assert len(layer.data_2h) == 20
    assert len(layer.data_4h) == 10
    
    # Verify copied (not referenced)
    data_15m.iloc[0, 0] = 99999
    assert layer.data_15m.iloc[0, 0] != 99999
```

**Time Estimate**: 1 hour

---

### Task 1.4: Implement Multi-TF Pattern Scanning

**File**: `src/layers/layer_tbd_method.py`

**Status**: ⬜ NOT STARTED

**Implementation**:
```python
def scan_multiple_timeframes(self, current_price: float, current_idx: int):
    """
    Scan multiple timeframes for M/W patterns
    
    Priority: 4H > 2H > 1H > 15m (higher TF = more reliable)
    
    Args:
        current_price: Current price for pattern validation
        current_idx: Current index in 15m data
    
    Returns:
        PatternData or None
    """
    patterns_found = []
    
    # Determine lookback indices for each timeframe
    # Need to align timeframes to current 15m position
    
    # Scan 4H first (highest priority)
    if self.data_4h is not None and len(self.data_4h) >= 20:
        logger.debug("Scanning 4H for M/W patterns...")
        
        # M-pattern on 4H
        m_pattern_4h = self._detect_m_pattern_on_tf(
            self.data_4h, current_price, timeframe='4H'
        )
        if m_pattern_4h:
            m_pattern_4h.confidence *= 1.3  # 30% boost for 4H
            patterns_found.append(m_pattern_4h)
        
        # W-pattern on 4H
        w_pattern_4h = self._detect_w_pattern_on_tf(
            self.data_4h, current_price, timeframe='4H'
        )
        if w_pattern_4h:
            w_pattern_4h.confidence *= 1.3
            patterns_found.append(w_pattern_4h)
    
    # Scan 2H (medium priority)
    if self.data_2h is not None and len(self.data_2h) >= 20:
        logger.debug("Scanning 2H for M/W patterns...")
        
        m_pattern_2h = self._detect_m_pattern_on_tf(
            self.data_2h, current_price, timeframe='2H'
        )
        if m_pattern_2h:
            m_pattern_2h.confidence *= 1.15  # 15% boost for 2H
            patterns_found.append(m_pattern_2h)
        
        w_pattern_2h = self._detect_w_pattern_on_tf(
            self.data_2h, current_price, timeframe='2H'
        )
        if w_pattern_2h:
            w_pattern_2h.confidence *= 1.15
            patterns_found.append(w_pattern_2h)

     # Scan 1H (medium priority)
    if self.data_1h is not None and len(self.data_1h) >= 20:
        logger.debug("Scanning 1H for M/W patterns...")
        
        m_pattern_1h = self._detect_m_pattern_on_tf(
            self.data_1h, current_price, timeframe='1H'
        )
        if m_pattern_1h:
            m_pattern_1h.confidence *= 1.10  # 10% boost for 1H
            patterns_found.append(m_pattern_1h)
        
        w_pattern_1h = self._detect_w_pattern_on_tf(
            self.data_1h, current_price, timeframe='1H'
        )
        if w_pattern_1h:
            w_pattern_1h.confidence *= 1.10
            patterns_found.append(w_pattern_1h)

    # Scan 15m (lowest priority, no boost)
    if self.data_15m is not None and len(self.data_15m) >= 20:
        logger.debug("Scanning 15m for M/W patterns...")
        
        available_15m = self.data_15m.iloc[:current_idx+1]
        
        m_pattern_15m = self._detect_m_pattern_on_tf(
            available_15m, current_price, timeframe='15m'
        )
        if m_pattern_15m:
            patterns_found.append(m_pattern_15m)
        
        w_pattern_15m = self._detect_w_pattern_on_tf(
            available_15m, current_price, timeframe='15m'
        )
        if w_pattern_15m:
            patterns_found.append(w_pattern_15m)
    
    # Return highest confidence pattern
    if patterns_found:
        best_pattern = max(patterns_found, key=lambda p: p.confidence)
        logger.info(f"Best M/W pattern found on {best_pattern.metadata.get('scan_timeframe', 'unknown')} "
                   f"TF with confidence {best_pattern.confidence:.2f}")
        return best_pattern
    
    return None
```

**Acceptance Criteria**:
- ✅ Scans 4H, 2H, 1H, 15m in priority order
- ✅ Applies confidence multipliers (4H: 1.3x, 2H: 1.15x, 1H: 1.10x, 15m: 1.0x)
- ✅ Returns highest confidence pattern
- ✅ Logs which timeframe pattern came from

**Unit Test**: `tests/test_layer_tbd_multitf.py::test_multi_tf_scanning`
```python
def test_scan_multiple_timeframes():
    """Test multi-TF pattern scanning with priority"""
    from src.layers.layer_tbd_method import LayerTBD
    
    layer = setup_layer_with_patterns()
    
    # Add M-pattern on 4H (should be highest priority)
    layer.data_4h = create_m_pattern_data(timeframe='4H')
    layer.data_1h = create_w_pattern_data(timeframe='1H')
    layer.data_2h = create_w_pattern_data(timeframe='2H')
    layer.data_15m = create_no_pattern_data(timeframe='15m')
    
    current_price = 95000
    pattern = layer.scan_multiple_timeframes(current_price, current_idx=50)
    
    # Should return 4H M-pattern (highest priority)
    assert pattern is not None
    assert pattern.metadata['scan_timeframe'] == '4H'
    assert pattern.pattern_type == PatternType.M_PATTERN
    
    # Check confidence boost applied
    assert pattern.confidence > 1.0  # Base + 30% boost
```

**Time Estimate**: 4 hours

---

### Task 1.5: Implement `_detect_m_pattern_on_tf()`

**File**: `src/layers/layer_tbd_method.py`

**Status**: ⬜ NOT STARTED

**Implementation**:
```python
def _detect_m_pattern_on_tf(self, data, current_price, timeframe='15m'):
    """
    Detect M-pattern on specific timeframe
    
    Enhanced detection based on MW_PATTERN_COMPREHENSIVE_FLOW.md
    
    Args:
        data: OHLCV DataFrame for this timeframe
        current_price: Current market price
        timeframe: String identifier ('4H', '2H', '1H', '15m')
    
    Returns:
        PatternData or None
    """
    # ENHANCED PARAMETERS (from documentation)
    MIN_PATTERN_LENGTH = self.config.mw_pattern_length_min  # Default 8
    MAX_PATTERN_LENGTH = self.config.mw_pattern_length_max  # Default 80
    PEAK_TOLERANCE = self.config.mw_peak_tolerance  # Default 0.25
    
    if len(data) < MAX_PATTERN_LENGTH:
        return None
    
    lookback = min(MAX_PATTERN_LENGTH, len(data))
    recent = data.iloc[-lookback:]
    
    # Find all peaks
    peaks = self._find_peaks(recent)
    
    if len(peaks) < 2:
        return None
    
    # Try different peak pairs (most recent first)
    for i in range(len(peaks) - 1, 0, -1):
        peak2_idx, peak2_price = peaks[i]
        peak1_idx, peak1_price = peaks[i - 1]
        
        # CHECK 1: Pattern Length
        pattern_length = peak2_idx - peak1_idx
        
        if pattern_length < MIN_PATTERN_LENGTH or pattern_length > MAX_PATTERN_LENGTH:
            continue
        
        # CHECK 2: Peak Symmetry
        price_diff = abs(peak1_price - peak2_price)
        diff_pct = price_diff / max(peak1_price, peak2_price)
        
        if diff_pct > PEAK_TOLERANCE:
            continue  # Peaks too different
        
        # CHECK 3: Valley Depth (Neckline)
        valley_data = recent.iloc[peak1_idx:peak2_idx + 1]
        neckline = valley_data['low'].min()
        
        pattern_height = max(peak1_price, peak2_price) - neckline
        depth_pct = pattern_height / max(peak1_price, peak2_price)
        
        if depth_pct < 0.03 or depth_pct > 0.25:
            continue  # Too shallow or too deep
        
        # CHECK 4: Volume Profile (Distribution check)
        peak1_vol = recent.iloc[peak1_idx]['volume']
        peak2_vol = recent.iloc[peak2_idx]['volume']
        
        if peak2_vol > peak1_vol * 1.2:
            # Volume increasing = accumulation, not distribution!
            logger.debug(f"{timeframe} M-pattern rejected: volume increasing")
            continue
        
        # CHECK 5: Neckline Break
        break_threshold = self.config.mw_neckline_break_threshold  # 0.003
        
        if current_price >= neckline * (1 - break_threshold):
            continue  # Hasn't broken neckline yet
        
        # CHECK 6: Breakout Candle Properties
        current_candle = data.iloc[-1]
        
        if current_candle['close'] >= neckline:
            continue  # Must close below neckline
        
        # CHECK 7: Volume on Breakout
        avg_volume = recent['volume'].mean()
        breakout_vol = current_candle['volume']
        
        if breakout_vol > avg_volume * 3:
            logger.debug(f"{timeframe} M-pattern: breakout volume too high")
            continue
        
        if breakout_vol < avg_volume * 0.8:
            logger.debug(f"{timeframe} M-pattern: breakout volume too low")
            continue
        
        # CHECK 8: Trend Context
        confidence_adjustment = 1.0
        if len(data) >= 50:
            sma_50 = data['close'].rolling(50).mean().iloc[-1]
            
            if current_price > sma_50 * 1.05:
                # Strong uptrend - risky counter-trend short
                confidence_adjustment = 0.5
        
        # ✅ PATTERN VALIDATED!
        logger.info(f"{timeframe} M-PATTERN DETECTED:")
        logger.info(f"  Peak1: ${peak1_price:.2f} (idx={peak1_idx})")
        logger.info(f"  Peak2: ${peak2_price:.2f} (idx={peak2_idx})")
        logger.info(f"  Neckline: ${neckline:.2f}")
        logger.info(f"  Pattern length: {pattern_length} bars")
        logger.info(f"  Peak difference: {diff_pct * 100:.1f}%")
        logger.info(f"  Pattern height: ${pattern_height:.2f}")
        
        # Create PatternData (Phase 2 will add proper TP/SL)
        return self._create_m_pattern_data(
            peak1_idx, peak1_price, peak1_vol,
            peak2_idx, peak2_price, peak2_vol,
            neckline, pattern_height,
            confidence_adjustment,
            timeframe
        )
    
    return None
```

**Acceptance Criteria**:
- ✅ Implements all 8 validation checks from documentation
- ✅ Uses configurable parameters
- ✅ Returns PatternData with metadata
- ✅ Logs detailed pattern information

**Unit Test**: `tests/test_layer_tbd_multitf.py::test_m_pattern_detection`
```python
def test_detect_m_pattern_on_timeframe():
    """Test M-pattern detection with enhanced parameters"""
    from src.layers.layer_tbd_method import LayerTBD
    
    layer = setup_test_layer()
    
    # Create perfect M-pattern
    data = create_perfect_m_pattern(
        peak1=100000, peak2=99500,  # 0.5% diff (valid)
        neckline=95000,
        pattern_length=30
    )
    
    current_price = 94700  # Below neckline
    
    pattern = layer._detect_m_pattern_on_tf(data, current_price, '4H')
    
    assert pattern is not None
    assert pattern.pattern_type == PatternType.M_PATTERN
    assert pattern.metadata['scan_timeframe'] == '4H'
    assert pattern.metadata['neckline'] == 95000
    assert pattern.metadata['pattern_height'] > 0

def test_m_pattern_rejects_invalid():
    """Test M-pattern rejects invalid patterns"""
    layer = setup_test_layer()
    
    # Peaks too different (30% - exceeds 25% tolerance)
    data = create_perfect_m_pattern(
        peak1=100000, peak2=70000,  # 30% diff
        neckline=65000,
        pattern_length=30
    )
    
    pattern = layer._detect_m_pattern_on_tf(data, 64000, '4H')
    assert pattern is None  # Should reject
```

**Time Estimate**: 6 hours

---

### Task 1.6: Implement `_detect_w_pattern_on_tf()`

**File**: `src/layers/layer_tbd_method.py`

**Status**: ⬜ NOT STARTED

**Implementation**: (Mirror of M-pattern for troughs)

**Acceptance Criteria**:
- ✅ Detects W-patterns (double bottom)
- ✅ Uses same validation logic as M-pattern
- ✅ Returns PatternData for long positions

**Unit Test**: `tests/test_layer_tbd_multitf.py::test_w_pattern_detection`

**Time Estimate**: 4 hours

---

### Task 1.7: Implement Helper Functions

**File**: `src/layers/layer_tbd_method.py`

**Status**: ⬜ NOT STARTED

**Implementation**:
```python
def _find_peaks(self, data, order=3):
    """
    Find local maxima in price data
    
    Args:
        data: OHLCV DataFrame
        order: Number of bars on each side to compare
    
    Returns:
        List of (index, price) tuples
    """
    highs = data['high'].values
    peaks = []
    
    for i in range(order, len(highs) - order):
        is_peak = True
        
        # Check left side
        for j in range(1, order + 1):
            if highs[i] <= highs[i - j]:
                is_peak = False
                break
        
        # Check right side
        if is_peak:
            for j in range(1, order + 1):
                if highs[i] <= highs[i + j]:
                    is_peak = False
                    break
        
        if is_peak:
            peaks.append((i, highs[i]))
    
    return peaks

def _find_troughs(self, data, order=3):
    """
    Find local minima in price data
    
    Returns:
        List of (index, price) tuples
    """
    lows = data['low'].values
    troughs = []
    
    for i in range(order, len(lows) - order):
        is_trough = True
        
        for j in range(1, order + 1):
            if lows[i] >= lows[i - j]:
                is_trough = False
                break
        
        if is_trough:
            for j in range(1, order + 1):
                if lows[i] >= lows[i + j]:
                    is_trough = False
                    break
        
        if is_trough:
            troughs.append((i, lows[i]))
    
    return troughs
```

**Acceptance Criteria**:
- ✅ Correctly identifies peaks and troughs
- ✅ Configurable order parameter
- ✅ Returns list of tuples (index, price)

**Unit Test**: `tests/test_layer_tbd_multitf.py::test_peak_trough_finding`

**Time Estimate**: 2 hours

---

### Task 1.8: Update Walk-Forward to Pass Multi-TF Data

**File**: `scripts/layer_testing/walk_forward_tbd.py`

**Status**: ⬜ NOT STARTED

**Implementation**:
```python
# In the window loop, after loading and preparing data:

# Get available data for this window
available_data_15m = full_data_15m.loc[
    (full_data_15m.index >= window_start) &
    (full_data_15m.index <= window_end)
]

# NEW: Get available 1H, 2H and 4H data
available_data_1h = full_data_1h.loc[
    (full_data_1h.index >= window_start) &
    (full_data_1h.index <= window_end)
]
available_data_2h = full_data_2h.loc[
    (full_data_2h.index >= window_start) &
    (full_data_2h.index <= window_end)
]

available_data_4h = full_data_4h.loc[
    (full_data_4h.index >= window_start) &
    (full_data_4h.index <= window_end)
]

# Initialize layer
lt = LayerTBD(tbd_config)

# NEW: Set multi-timeframe data
lt.set_multi_timeframe_data(
    data_15m=available_data_15m,
    data_1h=available_data_1h,
    data_2h=available_data_2h,
    data_4h=available_data_4h
)

logger.info(f"Multi-TF data set for window {window_start} to {window_end}")
```

**Acceptance Criteria**:
- ✅ All three timeframes passed to layer
- ✅ Data aligned to window boundaries
- ✅ Logging confirms data transfer

**Unit Test**: Integration test in Phase 6

**Time Estimate**: 2 hours

---

## PHASE 2: PATTERN-BASED TP/SL

**Goal**: Replace ATR-based targets with pattern height-based targets  
**Priority**: P0 (Blocking)  
**Timeline**: Week 1-2 (Days 4-7)  
**Expected Impact**: 4-10x improvement

### Task 2.1: Implement Pattern-Based TP/SL Calculation

**File**: `src/layers/layer_tbd_method.py`

**Status**: ⬜ NOT STARTED

**Implementation**:
```python
def _calculate_pattern_targets(self, pattern_data, entry_price, atr):
    """
    Calculate TP/SL based on pattern structure (NOT ATR!)
    
    From Layer_TBD_Method.md:
    Pattern Height = Higher Peak - Neckline (M) or Neckline - Lower Trough (W)
    TP1 = Neckline ± (Pattern Height × 0.5)   [30% position]
    TP2 = Neckline ± (Pattern Height × 1.0)   [40% position]
    TP3 = Neckline ± (Pattern Height × 1.5)   [30% position]
    SL = Peaks/Troughs ± (ATR × 1.5)
    
    Args:
        pattern_data: PatternData with neckline and pattern_height
        entry_price: Actual entry price
        atr: ATR value for stop placement
    
    Returns:
        dict with tp1, tp2, tp3, stop_loss
    """
    neckline = pattern_data.metadata['neckline']
    pattern_height = pattern_data.metadata['pattern_height']
    pattern_type = pattern_data.pattern_type
    timeframe = pattern_data.metadata.get('scan_timeframe', '15m')
    
    if pattern_type == PatternType.M_PATTERN:
        # SHORT position
        direction = -1
        
        # Stop above peaks
        peak_high = max(
            pattern_data.metadata['peak1_price'],
            pattern_data.metadata['peak2_price']
        )
        stop_loss = peak_high + (atr * 1.5)
        
        # Targets below neckline
        tp1 = neckline - (pattern_height * 0.5)
        tp2 = neckline - (pattern_height * 1.0)
        tp3 = neckline - (pattern_height * 1.5)
        
    elif pattern_type == PatternType.W_PATTERN:
        # LONG position
        direction = 1
        
        # Stop below troughs
        trough_low = min(
            pattern_data.metadata['trough1_price'],
            pattern_data.metadata['trough2_price']
        )
        stop_loss = trough_low - (atr * 1.5)
        
        # Targets above neckline
        tp1 = neckline + (pattern_height * 0.5)
        tp2 = neckline + (pattern_height * 1.0)
        tp3 = neckline + (pattern_height * 1.5)
    
    else:
        raise ValueError(f"Unknown pattern type: {pattern_type}")
    
    # Calculate risk:reward
    risk = abs(stop_loss - entry_price)
    reward1 = abs(tp1 - entry_price)
    rr1 = reward1 / risk if risk > 0 else 0
    
    logger.info(f"{timeframe} Pattern Targets ({pattern_type.name}):")
    logger.info(f"  Entry: ${entry_price:.2f}")
    logger.info(f"  Stop: ${stop_loss:.2f} (Risk: ${risk:.2f})")
    logger.info(f"  TP1: ${tp1:.2f} (50% of pattern height)")
    logger.info(f"  TP2: ${tp2:.2f} (100% of pattern height)")
    logger.info(f"  TP3: ${tp3:.2f} (150% of pattern height)")
    logger.info(f"  R:R at TP1: {rr1:.2f}:1")
    logger.info(f"  Pattern height: ${pattern_height:.2f}")
    
    return {
        'tp1': tp1,
        'tp2': tp2,
        'tp3': tp3,
        'stop_loss': stop_loss,
        'pattern_height': pattern_height,
        'neckline': neckline,
        'risk_reward': rr1
    }
```

**Acceptance Criteria**:
- ✅ Calculates targets based on pattern height
- ✅ Separate logic for M vs W patterns
- ✅ Stop placement based on peaks/troughs + ATR
- ✅ R:R calculation and logging

**Unit Test**: `tests/test_layer_tbd_pattern_targets.py`

**Time Estimate**: 3 hours

---

### Remaining Phases Summary

Due to token length, the complete action plan continues with:

**PHASE 3: RETEST ENTRY LOGIC** (Week 2)
- Task 3.1-3.7: MWPatternTracker class, retest detection, rejection wick validation

**PHASE 4: DYNAMIC POSITION MANAGEMENT** (Week 2-3)
- Task 4.1-4.6: Pattern upgrade detection, 1H→4H target adjustment, SL management

**PHASE 5: ENHANCED DETECTION PARAMETERS** (Week 3)
- Task 5.1-5.5: Config updates, parameter widening, validation

**PHASE 6: VALIDATION & TESTING** (Week 3-4)
- Task 6.1-6.8: Manual vs automated comparison, performance validation, regression tests

**PHASE 7: OPTIMIZATION INTEGRATION** (Week 4)
- Task 7.1-7.4: Update optimizer for multi-TF metrics, new parameter ranges

---

## QUICK START CHECKLIST

### Day 1 Tasks (Mon):
- [ ] Task 1.1: Load multi-TF data in walk-forward
- [ ] Task 1.2: Add indicators to 1H/2H/4H
- [ ] Task 1.3: Add multi-TF storage to layer

### Day 2 Tasks (Tue):
- [ ] Task 1.4: Implement multi-TF scanning
- [ ] Task 1.5: Implement M-pattern detection
- [ ] Task 1.7: Implement peak/trough finding

### Day 3 Tasks (Wed):
- [ ] Task 1.6: Implement W-pattern detection
- [ ] Task 1.8: Connect multi-TF to walk-forward
- [ ] Phase 1 Unit Tests

### Week 1 Validation:
- [ ] Run single walk-forward test with Phase 1 changes
- [ ] Verify M/W patterns detected on 4H/2H/1H timeframes
- [ ] Confirm pattern metadata includes correct TF

---

## TESTING INFRASTRUCTURE

### New Test File: `tests/test_layer_tbd_multitf.py`

Create comprehensive test suite for multi-TF functionality:

```python
"""
Tests for TBD Layer Multi-Timeframe Functionality
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.layers.layer_tbd_method import LayerTBD
from config.strategies.layer_tbd_only import TBDConfig

# Test fixtures and helper functions would go here
# ... (test implementations from tasks above)
```

### Test Data Generators

**Location**: `tests/helpers/pattern_generators.py`

```python
def create_perfect_m_pattern(peak1, peak2, neckline, pattern_length, timeframe='15m'):
    """Generate synthetic M-pattern for testing"""
    
def create_perfect_w_pattern(trough1, trough2, neckline, pattern_length, timeframe='15m'):
    """Generate synthetic W-pattern for testing"""
    
def create_no_pattern_data(length=100, timeframe='15m'):
    """Generate random walk data with no patterns"""
```

---

## VALIDATION METRICS

### Phase 1 Success Criteria:
- ✅ Multi-TF data loads without errors
- ✅ Patterns detected on 4H show highest confidence
- ✅ Pattern metadata includes correct timeframe
- ✅ 30%+ of patterns come from 1H/2H/4H (not 15min)

### Phase 2 Success Criteria:
- ✅ TP/SL based on pattern height (not ATR multiples)
- ✅ Average target size increases 4-10x
- ✅ R:R ratios improve to 1.5-2.5:1

### End-to-End Success Criteria:
- ✅ M/W pattern correlation: -0.48 → +0.3 to +0.5
- ✅ M/W pattern frequency: 13% → 30-35% of trades
- ✅ Win rate: 36.7% → 60-70%
- ✅ Total return (60d): 0.23% → 30-75%

---

## DOCUMENTATION UPDATES REQUIRED

### Files to Update as Implementation Progresses:

1. **`docs/Layer_TBD/IMPLEMENTATION_STATUS_V2.md`**
   - Track implementation progress
   - Update as each phase completes

2. **`docs/Layer_TBD/Layer_TBD_Method.md`**
   - Add notes about multi-TF implementation
   - Update code examples to match actual implementation

3. **`docs/TBD_OPTIMIZATION_GUIDE.md`**
   - Add new parameters for multi-TF testing
   - Update expected performance targets

4. **`memory-bank/progress.md`**
   - Weekly updates on implementation progress
   - Blockers and decisions

---

## RISK MITIGATION

### Known Risks:

1. **Data Alignment Issues**
   - Risk: 15min, 1H, 2H, 4H data timestamps don't align
   - Mitigation: Implement timestamp synchronization utility
   - Test: Validate alignment before each walk-forward window

2. **Performance Degradation**
   - Risk: Scanning 3 timeframes increases compute time
   - Mitigation: Add caching for pattern detection results
   - Test: Benchmark before/after Phase 1

3. **Pattern Over-Detection**
   - Risk: Detecting too many patterns on multiple TFs
   - Mitigation: Strict confidence thresholds, priority system
   - Test: Monitor pattern frequency in validation

4. **Retest Logic Complexity**
   - Risk: Pending pattern tracking adds state complexity
   - Mitigation: Thorough unit tests, state reset between windows
   - Test: Verify no pattern leakage between windows

---

## ROLLBACK PLAN

### If Issues Arise:

**Phase 1 Rollback**:
```bash
# Revert layer_tbd_method.py changes
git checkout HEAD -- src/layers/layer_tbd_method.py

# Revert walk_forward_tbd.py changes
git checkout HEAD -- scripts/layer_testing/walk_forward_tbd.py
```

**Fallback Configuration**:
```python
# In TBDConfig, disable multi-TF
enable_multi_tf_scan = False  # Falls back to 15min only
```

---

## PROGRESS REPORTING

### Weekly Status Reports:

**Week 1 Report** (Fri EOD):
- [ ] Phase 1 tasks completed: X/8
- [ ] Unit tests passing: X/Y
- [ ] Blockers encountered: [List]
- [ ] Next week priorities: [List]

**Week 2 Report** (Fri EOD):
- [ ] Phase 2 & 3 tasks completed: X/13
- [ ] Pattern detection working on all TFs: Y/N
- [ ] Performance improvement observed: X%

**Week 3 Report** (Fri EOD):
- [ ] Phase 4 & 5 tasks completed: X/11
- [ ] Validation tests passing: Y/N
- [ ] Ready for optimization: Y/N

**Week 4 Report** (Fri EOD):
- [ ] Phase 6 & 7 completed: X/12
- [ ] Final validation results: [Metrics]
- [ ] Production ready: Y/N

---

## APPENDIX: FULL TASK LIST

### PHASE 1: Multi-TF Data & Scanning (8 tasks, Week 1)
- [ ] 1.1: Load multi-TF data in walk-forward
- [ ] 1.2: Add indicators to multi-TF
- [ ] 1.3: Update layer TBD storage
- [ ] 1.4: Implement multi-TF scanning
- [ ] 1.5: Implement M-pattern detection
- [ ] 1.6: Implement W-pattern detection
- [ ] 1.7: Implement helper functions
- [ ] 1.8: Update walk-forward to pass multi-TF

### PHASE 2: Pattern-Based TP/SL (6 tasks, Week 1-2)
- [ ] 2.1: Implement pattern target calculation
- [ ] 2.2: Update position creation with pattern targets
- [ ] 2.3: Store pattern metadata in positions
- [ ] 2.4: Update exit logic for pattern invalidation
- [ ] 2.5: Add config parameters for TP multipliers
- [ ] 2.6: Unit tests for pattern targets

### PHASE 3: Retest Entry Logic (7 tasks, Week 2)
- [ ] 3.1: Create MWPatternTracker class
- [ ] 3.2: Store pending patterns after neckline break
- [ ] 3.3: Implement retest detection logic
- [ ] 3.4: Implement rejection wick validation
- [ ] 3.5: Implement strong continuation entry
- [ ] 3.6: Integrate with main signal generation
- [ ] 3.7: Unit tests for retest logic

### PHASE 4: Dynamic Position Management (6 tasks, Week 2-3)
- [ ] 4.1: Implement HTF pattern monitoring while in trade
- [ ] 4.2: Detect pattern upgrades (1H → 4H)
- [ ] 4.3: Implement target adjustment logic
- [ ] 4.4: Implement SL to profit movement
- [ ] 4.5: Add position metadata tracking
- [ ] 4.6: Unit tests for dynamic management

### PHASE 5: Enhanced Detection Parameters (5 tasks, Week 3)
- [ ] 5.1: Update config defaults (8-80 bars, 25% tolerance)
- [ ] 5.2: Add new multi-TF parameters
- [ ] 5.3: Add retest parameters
- [ ] 5.4: Update preset configurations
- [ ] 5.5: Documentation updates

### PHASE 6: Validation & Testing (8 tasks, Week 3-4)
- [ ] 6.1: Manual vs automated pattern comparison
- [ ] 6.2: Single pattern walkthrough validation
- [ ] 6.3: Multi-window walk-forward test
- [ ] 6.4: Performance metrics validation
- [ ] 6.5: Regression test suite
- [ ] 6.6: Edge case testing
- [ ] 6.7: Load testing (180-day windows)
- [ ] 6.8: Final validation report

### PHASE 7: Optimization Integration (4 tasks, Week 4)
- [ ] 7.1: Update optimizer parameter ranges
- [ ] 7.2: Add multi-TF metrics to result analyzer
- [ ] 7.3: Update correlation analysis for new params
- [ ] 7.4: Create optimization preset for v3.0

---

## COMPLETION CRITERIA

### Ready for Next Optimization Cycle When:

✅ **All 44 tasks completed**  
✅ **All unit tests passing (>95% coverage)**  
✅ **Integration tests passing**  
✅ **Walk-forward validation shows positive M/W correlation**  
✅ **Performance improvement >10x vs baseline**  
✅ **Documentation updated**  
✅ **Code reviewed and approved**  
✅ **Production configuration created**

---

**Document Version**: 1.0  
**Last Updated**: 2025-12-29  
**Status**: 🔴 Ready to Begin  
**Owner**: Development Team  
**Next Review**: End of Week 1

---

**END OF CORRECTIVE ACTION PLAN**
