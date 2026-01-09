# Layer TBD v2.0 - Complete Implementation Plan

**Created**: December 27, 2025  
**Status**: EXECUTION PHASE  
**Estimated Time**: 11-14 hours  

---

## Current State Analysis

### Session Implementation (Lines 1055-1073)
**Current**:
- Hardcoded time objects: `asian_session_start: time = time(0, 0)`
- No DST awareness
- Session logic uses `.hour` comparison only

**Issue**: No auto-detection of UK/US DST changes

### Board Meeting Implementation (Lines 702-760)
**Current**:
- Checks consolidation range < threshold (0.02 = 2%)
- Requires volume declining in second half
- Breakout must exceed range/2
- Measured move targets (1x, 2x, 3x range)

**Differences from Docs**:
- Doc says "tight consolidation" but doesn't specify exact declining volume formula
- Implementation adds volume decline check (late_vol < early_vol * 1.2)
- This is actually MORE sophisticated than documented

**Verdict**: Implementation is CORRECT and more complete than docs

### Liquidation Levels
**Current**: `enable_liquidation_levels: bool = False`
**Available**: Data in `data/raw/liquidations/`
**Required**: Loader + integration into `_analyze_levels()`

---

## Decisions Made (From User)

1. **DST Handling**: Auto-detect (not hardcoded Winter/Summer)
2. **Liquidation Priority**: Phase 1 (foundation)
3. **Board Meeting**: Document current implementation (it's correct)
4. **Execution Order**: Phase 1 (all docs) → Phase 2 (all tests) → Phase 3 (validation)
5. **Versioning**: TBD v2.0 (breaking changes due to session times)

---

## PHASE 1: Documentation & Configuration

### 1.1 ✅ Read Current Implementation
**Status**: COMPLETE
- Sessions use config time objects
- Board Meeting correctly implements methodology
- No liquidation integration yet

### 1.2 Implement DST Auto-Detection

**File**: `src/layers/layer_tbd_method.py`

**Current Code** (lines 1055-1073):
```python
def _get_current_session(self, timestamp: pd.Timestamp) -> Session:
    hour = timestamp.hour
    # Uses hardcoded config times
```

**New Implementation Required**:
```python
def _is_uk_dst(self, timestamp: pd.Timestamp) -> bool:
    """Check if UK is in daylight saving time (last Sunday March - last Sunday October)"""
    import calendar
    year = timestamp.year
    month = timestamp.month
    
    # DST starts last Sunday in March
    march_last = max(week[-1] for week in calendar.monthcalendar(year, 3) if week[-1] != 0)
    dst_start = pd.Timestamp(year, 3, march_last, 1, 0, tz='UTC')
    
    # DST ends last Sunday in October
    oct_last = max(week[-1] for week in calendar.monthcalendar(year, 10) if week[-1] != 0)
    dst_end = pd.Timestamp(year, 10, oct_last, 1, 0, tz='UTC')
    
    return dst_start <= timestamp < dst_end

def _is_us_dst(self, timestamp: pd.Timestamp) -> bool:
    """Check if US is in daylight saving time (2nd Sunday March - 1st Sunday November)"""
    import calendar
    year = timestamp.year
    month = timestamp.month
    
    # DST starts 2nd Sunday in March
    march_weeks = calendar.monthcalendar(year, 3)
    march_sundays = [week[-1] for week in march_weeks if week[-1] != 0]
    dst_start = pd.Timestamp(year, 3, march_sundays[1], 2, 0, tz='UTC')
    
    # DST ends 1st Sunday in November
    nov_weeks = calendar.monthcalendar(year, 11)
    nov_sundays = [week[-1] for week in nov_weeks if week[-1] != 0]
    dst_end = pd.Timestamp(year, 11, nov_sundays[0], 2, 0, tz='UTC')
    
    return dst_start <= timestamp < dst_end

def _get_session_times(self, timestamp: pd.Timestamp) -> dict:
    """Get session times adjusted for DST"""
    uk_dst = self._is_uk_dst(timestamp)
    us_dst = self._is_us_dst(timestamp)
    
    # Base times (UTC)
    if uk_dst:
        london_start, london_end = 7, 16  # UK Summer (BST = UTC+1)
    else:
        london_start, london_end = 8, 17  # UK Winter (GMT = UTC+0)
    
    if us_dst:
        ny_start, ny_end = 12, 21  # US Summer (EDT = UTC-4)
    else:
        ny_start, ny_end = 13, 22  # US Winter (EST = UTC-5)
    
    # Asian session unchanged (Japan no DST)
    return {
        'asian': (23, 8),  # Note: 23:00 previous day to 08:00
        'london': (london_start, london_end),
        'ny': (ny_start, ny_end)
    }

def _get_current_session(self, timestamp: pd.Timestamp) -> Session:
    """Determine current trading session with DST awareness"""
    hour = timestamp.hour
    day = timestamp.dayofweek
    
    if day >= 5:
        return Session.WEEKEND
    
    times = self._get_session_times(timestamp)
    
    # Check overlaps first
    if (times['london'][0] <= hour < times['london'][1] and 
        times['ny'][0] <= hour < times['ny'][1]):
        return Session.OVERLAP
    
    # Individual sessions
    if times['ny'][0] <= hour < times['ny'][1]:
        return Session.NEW_YORK
    elif times['london'][0] <= hour < times['london'][1]:
        return Session.LONDON
    elif hour >= times['asian'][0] or hour < times['asian'][1]:
        return Session.ASIAN
    else:
        return Session.ASIAN  # Default fallback
```

**Testing Required**:
- March 30, 2025 (UK DST starts)
- March 9, 2025 (US DST starts)
- October 26, 2025 (UK DST ends)
- November 2, 2025 (US DST ends)

### 1.3 Integrate Liquidation Levels

**Data Location**: `data/raw/liquidations/`

**File Structure Expected**:
```
data/raw/liquidations/
├── BTC-USDT_liquidations_2024-01.parquet
├── BTC-USDT_liquidations_2024-02.parquet
└── ...
```

**New Class Required**:
```python
class LiquidationLevelTracker:
    """Track and analyze liquidation clusters"""
    
    def __init__(self, data_path: str = "data/raw/liquidations"):
        self.data_path = data_path
        self.clusters = {}
    
    def load_recent_liquidations(self, lookback_hours: int = 24):
        """Load recent liquidation data"""
        # Load parquet files
        # Aggregate by price levels
        # Identify clusters (>1M USD within 1% range)
    
    def get_nearby_clusters(self, price: float, threshold_pct: float = 0.02):
        """Get liquidation clusters near current price"""
        # Return list of (level, size, type) tuples
```

**Integration into Layer**:
```python
# In TBDConfig:
enable_liquidation_levels: bool = True  # Changed from False
liquidation_cluster_threshold: float = 1_000_000  # Min USD for cluster
liquidation_proximity_pct: float = 0.02  # Within 2% of price

# In LayerTBD.__init__():
if self.config.enable_liquidation_levels:
    self.liq_tracker = LiquidationLevelTracker()

# In _analyze_levels():
if self.config.enable_liquidation_levels and self.liq_tracker:
    clusters = self.liq_tracker.get_nearby_clusters(current_price)
    if clusters:
        score += 0.2  # Boost for proximity to liquidation
        metadata['liquidation_clusters'] = clusters
```

### 1.4 Update TBD_Implementation_Complete.md

**Sections to Add**:

#### Test Coverage Section
```markdown
## Test Coverage Results

**Status**: 92.5% Coverage (37/40 tests passing)

### Results by Category
| Category | Passing | Total | Coverage |
|----------|---------|-------|----------|
| M-Pattern | 4 | 4 | 100% ✅ |
| W-Pattern | 4 | 4 | 100% ✅ |
| Weekend Trap | 4 | 4 | 100% ✅ |
| Board Meeting | 4 | 4 | 100% ✅ |
| Three Hits | 2 | 4 | 50% ⚠️ |
| Trapping Volume | 0 | 4 | 0% ❌ |
| One Formation | 0 | 4 | 0% ❌ |
| Level Tracking | 4 | 4 | 100% ✅ |
| Sessions | 5 | 5 | 100% ✅ |
| Configuration | 6 | 6 | 100% ✅ |
| Signal Generation | 8 | 8 | 100% ✅ |

### Remaining Test Gaps
- Trapping Volume: 4 tests needed
- One Formation: 4 tests needed (2 overlap with Board Meeting)
- Three Hits: 2 enhancement tests needed
```

#### Critical Bugs Section
```markdown
## Critical Bugs Fixed

### Bug #1: M-Pattern Neckline Break Inversion
**Severity**: CRITICAL  
**Commit**: 8255c61  
**Impact**: Would have entered SHORT on bullish breakouts

**Before**:
```python
if current_price > neckline * (1 + break_threshold):
    return None  # WRONG: checking for break ABOVE
```

**After**:
```python
if current_price > neckline * (1 - break_threshold):
    return None  # CORRECT: price must break BELOW for bearish M
```

### Bug #2: W-Pattern Neckline Break Inversion
**Severity**: CRITICAL  
**Commit**: 8255c61  
**Impact**: Would have entered LONG on bearish breakdowns

**Before**:
```python
if current_price < neckline * (1 - break_threshold):
    return None  # WRONG: checking for break BELOW
```

**After**:
```python
if current_price < neckline * (1 + break_threshold):
    return None  # CORRECT: price must break ABOVE for bullish W
```

**Result**: Both bugs would have caused systematic losses by trading wrong direction.
```

#### Data Acquisition Section
```markdown
## Data Acquisition System

### Available Data Sources

#### Primary: Crypto-Lake API
- **Script**: `scripts/data_download/download_liquidations_funding_oi.py`
- **Coverage**: Jan 2024 - Present
- **Data Types**:
  - Liquidations (long/short separation)
  - Funding rates (8-hour intervals)
  - Open interest (trend validation)
- **Format**: Monthly parquet files
- **Location**: `data/raw/{liquidations,funding,open_interest}/`

#### Backup: Binance Futures API
- **Script**: `scripts/data_download/download_binance_liquidations.py`
- **Endpoint**: Public (no API key required)
- **Limitation**: 1000 records per request
- **Use Case**: Gaps or recent data

### Integration Status
- [x] Downloaders implemented
- [x] Historical data acquired (2024-2025)
- [ ] Liquidation level integration (Phase 1.3)
- [ ] Funding rate analysis (Phase 3 - future)
- [ ] Open interest validation (Phase 3 - future)
```

### 1.5 Document All 7 Patterns in Layer_TBD_Method.md

**Patterns Currently Missing Details**:
1. Weekend Trap (mentioned only)
2. Board Meeting (mentioned only)
3. Trapping Volume (not mentioned)
4. One Formation (not mentioned)

**Template for Each Pattern**:
```markdown
### Pattern X: [Name]

#### Formation
[Describe what the pattern looks like visually]

#### Market Maker Psychology
[Why do market makers create this pattern?]

#### Detection Algorithm
```python
# Pseudo-code
1. Check condition A
2. Verify condition B
3. Calculate entry/stop/targets
```

#### Entry Rules
- Entry: [Price level]
- Direction: [Long/Short]
- Confirmation: [Volume/Level/etc]

#### Exit Rules
- Stop Loss: [Calculation]
- Take Profit 1: [Target calculation]
- Take Profit 2: [Target calculation]
- Take Profit 3: [Target calculation]

#### Risk Parameters
- ATR Multiplier: [Default value]
- Position Size: [% of capital]
- Max Hold Time: [Hours/Days]

#### Example
[Real example with numbers]
```

### 1.6 Document All 50+ Config Parameters

**Create Comprehensive Reference**:

```markdown
## Complete Configuration Reference

### Pattern Detection Switches (7)
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| enable_m_pattern | bool | True | Enable M-Pattern (Double Top) detection |
| enable_w_pattern | bool | True | Enable W-Pattern (Double Bottom) detection |
| enable_weekend_trap | bool | True | Enable Monday reversal pattern |
| enable_board_meeting | bool | True | Enable consolidation breakout |
| enable_three_hits_rule | bool | True | Enable 3-touch reversal |
| enable_trapping_volume | bool | False | Enable wick trap detection |
| enable_one_formation | bool | False | Enable decisive breakout pattern |

### M/W Pattern Parameters (6)
[... continue for all 50+ parameters ...]
```

### 1.7 Update Session Times Across All Docs

**Files to Update**:
- [x] `docs/Layer_TBD/TBD_Implementation_Complete.md` (user already updated)
- [ ] `docs/Layer_TBD/Layer_TBD_Method.md`
- [ ] `docs/Layer_TBD/TBD_Rules.md`
- [ ] `docs/Layer_TBD/Layer_TBD_Flow.md`
- [ ] `docs/Layer_TBD/TBD_Cross_Reference_Analysis.md`

**Standard Session Time Block** (Now Implemented):
```markdown
## Trading Sessions (DST-Aware) ✅ IMPLEMENTED v2.0

The system automatically detects and adjusts for Daylight Saving Time transitions.

**Winter Sessions (November - March)**:
- **Asian Session**: 23:00-08:00 UTC - Low priority
  - Japan has no DST, times remain constant
  - Weekend preparation period
- **London Session**: 08:00-17:00 UTC - High priority (GMT)
  - Skip first 30 minutes (low liquidity)
  - Primary European trading activity
- **New York Session**: 13:00-22:00 UTC - High priority (EST)
  - US market hours, highest volatility
- **UK/US Overlap**: 13:00-17:00 UTC - MAXIMUM priority
  - Peak global liquidity window

**Summer Sessions (March - November)**:
- **Asian Session**: 23:00-08:00 UTC - Low priority (unchanged)
- **London Session**: 07:00-16:00 UTC - High priority (BST)
  - **1-hour earlier** than winter (BST = GMT-1)
  - Auto-adjusts after last Sunday in March
- **New York Session**: 12:00-21:00 UTC - High priority (EDT)
  - **1-hour earlier** than winter (EDT = EST-1)
  - Auto-adjusts after 2nd Sunday in March
- **UK/US Overlap**: 12:00-16:00 UTC - MAXIMUM priority
  - Shifted 1 hour earlier in summer

**DST Transition Dates** (Automatic Detection):
- **UK (British Summer Time)**: Last Sunday in March → Last Sunday in October
- **US (Eastern Daylight Time)**: 2nd Sunday in March → 1st Sunday in November
- **Implementation**: `_is_uk_dst()` and `_is_us_dst()` methods detect current DST status
- **No manual adjustment required** - session times update automatically

**Session Priority Weighting**:
- Asian only: 0.3x multiplier (low priority)
- London/NY: 1.0x multiplier (standard priority)  
- UK/US Overlap: 1.5x multiplier (maximum priority)
- Weekend: 0.5x multiplier (optional - can disable weekend trading)
```

---

## PHASE 2: Complete Test Coverage

### 2.1 Trapping Volume Tests (4 tests)

**File**: `tests/test_layer_tbd.py`

```python
class TestTrappingVolume:
    """Test trapping volume pattern detection"""
    
    def test_bullish_trap_detection(self, sample_data):
        """Test large lower wick + volume spike → SHORT signal"""
        # Create candle with large lower wick (60% of range)
        # Volume 2x average
        # Close in upper 40% of range
        # Expected: SHORT signal (trap reversal)
    
    def test_bearish_trap_detection(self, sample_data):
        """Test large upper wick + volume spike → LONG signal"""
        # Create candle with large upper wick (60% of range)
        # Volume 2x average
        # Close in lower 40% of range
        # Expected: LONG signal (trap reversal)
    
    def test_volume_requirement_not_met(self, sample_data):
        """Test large wick without volume spike → NO signal"""
        # Large wick but normal volume
        # Expected: None (no pattern)
    
    def test_wick_size_requirement_not_met(self, sample_data):
        """Test high volume without large wick → NO signal"""
        # High volume but small wick (< 50% range)
        # Expected: None (no pattern)
```

### 2.2 One Formation Tests (4 tests)

```python
class TestOneFormation:
    """Test one formation pattern detection"""
    
    def test_consolidation_detection(self, sample_data):
        """Test 30+ candles in <3% range"""
        # Create 35 candles in 2.5% range
        # Expected: Consolidation detected, no signal yet
    
    def test_breakout_long_validation(self, sample_data):
        """Test bullish breakout (2x avg range, 2x volume)"""
        # Consolidation + large upward breakout
        # Expected: LONG signal with measured move targets
    
    def test_breakout_short_validation(self, sample_data):
        """Test bearish breakout (2x avg range, 2x volume)"""
        # Consolidation + large downward breakout
        # Expected: SHORT signal with measured move targets
    
    def test_measured_move_calculation(self, sample_data):
        """Test TP targets = 1x, 2x, 3x consolidation range"""
        # Verify exact calculations for targets
```

### 2.3 Three Hits Enhancement Tests (2 tests)

```python
class TestThreeHitsEnhanced:
    """Enhanced three hits pattern tests"""
    
    def test_rejection_validation_quality(self, sample_data):
        """Test rejection wick formation quality"""
        # Weak rejection (small wick, close near level) → NO signal
        # Strong rejection (large wick, close away) → SIGNAL
    
    def test_premature_signal_prevention(self, sample_data):
        """Test no signal before 3rd touch"""
        # Touch 1: no signal, counter = 1
        # Touch 2: no signal, counter = 2
        # Touch 3: check for signal
        # Touch 4: verify signal strength increases
```

### 2.4 Board Meeting Documentation

**Action**: Document that implementation is CORRECT and MORE sophisticated than docs.

**Add to Method Doc**:
```markdown
### Board Meeting Pattern

**Implementation Note**: The current implementation is more sophisticated than initial documentation. It includes:
1. Consolidation range check (<2% default)
2. Minimum candle count (6-24 candles)
3. **Volume decline validation** (late volume < early volume * 1.2) ← NOT in original doc
4. Breakout size validation (>50% of consolidation range)
5. Measured move targets (1x, 2x, 3x consolidation range)

The volume decline check ensures we're detecting true pre-breakout compression, not random consolidation.
```

### 2.5 Run Full Test Suite

**Command**:
```bash
pytest tests/test_layer_tbd.py -v --cov=src.layers.layer_tbd_method --cov-report=term-missing
```

**Target**: 46/46 tests passing (100%)

---

## PHASE 3: Validation & Version Control

### 3.1 Update Version to TBD v2.0

**Files to Update**:
- `src/layers/layer_tbd_method.py` (add VERSION constant)
- All documentation headers
- `memory-bank/layer_tbd_reference.md`

### 3.2 Backtest Comparison

**Test Scenarios**:
1. 30-day period during UK DST (April 2024)
2. 30-day period during US DST transition (March 2024)
3. 30-day period with known liquidation events

**Metrics to Compare**:
- Signal count (v1 vs v2)
- Signal quality (confidence distribution)
- Win rate by session
- Impact of liquidation levels

### 3.3 Update Cross-Reference Analysis

**Add Section**:
```markdown
## Version 2.0 Changes

### Breaking Changes
1. Session times now DST-aware (auto-detected)
2. Liquidation levels integrated (opt-in)
3. Board Meeting documented correctly

### Non-Breaking Enhancements
1. Test coverage: 92.5% → 100%
2. Documentation: 62.5% → 100% alignment
3. All 7 patterns fully documented
```

### 3.4 Git Commit

**Commit Message**:
```
feat: Layer TBD v2.0 - DST Support, Liquidation Levels, 100% Test Coverage

BREAKING CHANGES:
- Session times now auto-detect UK/US DST transitions
- Default liquidation level integration (can be disabled)

Features:
- DST-aware session detection (UK/US)
- Liquidation level tracking and integration
- Complete test coverage (46/46 tests, 100%)
- All 7 patterns fully documented
- 50+ configuration parameters documented

Fixes:
- Documented Board Meeting implementation (correct, more sophisticated)
- Updated all session time references across docs

Documentation:
- Added test coverage section to implementation doc
- Added critical bugs section (2 neckline inversions)
- Added data acquisition section
- Completed pattern documentation (all 7 patterns)
- Complete configuration reference (50+ parameters)
- Updated cross-reference analysis

Tests:
- Added 4 Trapping Volume tests
- Added 4 One Formation tests
- Added 2 Three Hits enhancement tests
- All tests passing (100%)

Co-authored-by: Development Team
```

---

## Execution Checklist

### Pre-Flight
- [ ] Backup current layer_tbd_method.py
- [ ] Create feature branch: `feature/layer-tbd-v2`
- [ ] Review all user requirements one more time

### Phase 1 Execution (6-8 hours)
- [ ] 1.2 DST auto-detection implementation
- [ ] 1.3 Liquidation level integration
- [ ] 1.4 Update implementation doc (3 sections)
- [ ] 1.5 Document 4 missing patterns
- [ ] 1.6 Document all 50+ parameters
- [ ] 1.7 Update session times (5 docs)

### Phase 2 Execution (4-5 hours)
- [ ] 2.1 Write 4 Trapping Volume tests
- [ ] 2.2 Write 4 One Formation tests
- [ ] 2.3 Write 2 Three Hits tests
- [ ] 2.4 Document Board Meeting correctly
- [ ] 2.5 Run full test suite (46/46)

### Phase 3 Execution (2-3 hours)
- [ ] 3.1 Version updates (v2.0)
- [ ] 3.2 Backtest comparison
- [ ] 3.3 Update cross-reference
- [ ] 3.4 Git commit with detailed message

### Post-Flight
- [ ] Merge feature branch to master
- [ ] Tag release: `v2.0.0`
- [ ] Update project status docs
- [ ] Notify stakeholders

---

## Risk Mitigation

### Risks Identified
1. **DST Logic Complexity**: Edge cases around transition dates
2. **Liquidation Data Load Time**: May slow down signal generation
3. **Breaking Changes**: Existing backtests will show different results
4. **Test Suite Expansion**: More tests = longer CI/CD time

### Mitigation Strategies
1. Comprehensive DST transition testing
2. Lazy loading + caching for liquidation data
3. Version clearly as v2.0, maintain v1 branch for comparison
4. Parallel test execution where possible

---

## Success Criteria

### Must Have (Phase 1 & 2)
- [ ] 100% test coverage (46/46 tests passing)
- [ ] DST auto-detection working correctly
- [ ] All 7 patterns fully documented
- [ ] Liquidation levels integrated and tested

### Nice to Have (Phase 3)
- [ ] Backtest showing improved performance
- [ ] Documentation at 100% alignment
- [ ] Clean git history with detailed commit

### Show Stoppers
- ❌ Any test regressions
- ❌ DST logic errors near transition dates
- ❌ Liquidation data loading failures

---

**Status**: READY FOR EXECUTION  
**Next Step**: Begin Phase 1.2 (DST Implementation)  
**Estimated Completion**: December 27, 2025 (end of day)
