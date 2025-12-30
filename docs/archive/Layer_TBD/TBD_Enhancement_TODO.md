# Layer TBD Enhancement TODO List

**Created**: December 27, 2025  
**Branch**: TBD_Flow_Check  
**Priority**: Optional Quality Improvements  

---

## Overview

Based on the comprehensive flow validation report, these are recommended enhancements to bring the implementation to 100% diagram compliance and improve quality.

---

## Code Enhancements

### 1. Board Meeting Volume Decline Check 📋

**Location**: `src/layers/layer_tbd_method.py` - `_detect_board_meeting()` method

**Current Behavior**: Checks early vs late volume but doesn't reject patterns with declining volume

**Diagram Specification**:
> "STEP 3: QUALITY CHECK - Early volume < late volume? (Institutions building)"

**Implementation Needed**:
```python
def _detect_board_meeting(self, data: pd.DataFrame, current_price: float) -> Optional[PatternData]:
    # ... existing code ...
    
    # ADD THIS QUALITY CHECK (around line 800):
    # Optional quality enhancement: check volume pattern
    if self.layer_config.board_require_volume_buildup:
        early_vol = recent.iloc[:len(recent)//2]['volume'].mean()
        late_vol = recent.iloc[len(recent)//2:]['volume'].mean()
        
        # Require late volume > early volume (institutions accumulating)
        if late_vol <= early_vol:
            logger.debug("Board Meeting: Volume not building up, skipping pattern")
            return None
```

**Config Addition**:
```python
@dataclass
class TBDConfig:
    # ... existing config ...
    
    # Board Meeting enhancements
    board_require_volume_buildup: bool = False  # Optional quality check
```

**Benefits**:
- Filters out low-quality consolidations
- Confirms institutional accumulation
- May improve win rate by 3-5%

---

### 2. Explicit Pattern Length Validation 📋

**Location**: `src/layers/layer_tbd_method.py` - All pattern detection methods

**Current Behavior**: Has min/max in config but doesn't explicitly validate

**Implementation Needed**:

#### M/W Pattern Length Checks:
```python
def _detect_m_pattern(self, data: pd.DataFrame, current_price: float) -> Optional[PatternData]:
    # ... find peaks code ...
    
    # ADD EXPLICIT LENGTH VALIDATION:
    pattern_length = peak2_idx - peak1_idx
    
    if pattern_length < self.layer_config.mw_pattern_length_min:
        logger.debug(f"M-Pattern too short: {pattern_length} candles")
        return None
        
    if pattern_length > self.layer_config.mw_pattern_length_max:
        logger.debug(f"M-Pattern too long: {pattern_length} candles")
        return None
    
    # ... rest of pattern detection ...
```

#### Board Meeting Length Checks:
```python
def _detect_board_meeting(self, data: pd.DataFrame, current_price: float) -> Optional[PatternData]:
    # ... existing code ...
    
    # ADD LENGTH VALIDATION:
    consolidation_length = len(recent)
    
    if consolidation_length < self.layer_config.board_min_candles:
        return None
    
    if consolidation_length > self.layer_config.board_max_candles:
        return None
    
    # ... rest of detection ...
```

#### One Formation Length Checks:
```python
def _detect_one_formation(self, data: pd.DataFrame, current_price: float) -> Optional[PatternData]:
    # Add configurable lookback
    lookback = getattr(self.layer_config, 'one_formation_lookback', 30)
    
    # ... rest of detection ...
```

**Config Addition**:
```python
@dataclass
class TBDConfig:
    # ... existing config ...
    
    # One Formation parameters
    one_formation_lookback: int = 30
    one_formation_min_candles: int = 20
    one_formation_max_candles: int = 40
```

**Benefits**:
- Prevents edge case patterns
- Ensures patterns match diagram specs
- Improves consistency

---

## Documentation Updates

### 1. Update TBD_Decision_Flow_Diagram.md

**Add to Stage 2 (Level Tracking)**:
```markdown
### Stage 2.5: Liquidation Level Loading (v2.0 Enhancement)

┌────────────────────────────────────────┐
│  LOAD LIQUIDATION DATA (Lazy Loading)  │
│  • Check if enabled in config          │
│  • Load recent liquidation history     │
│  • Identify clusters (>$1M threshold)  │
│  • Calculate proximity scores          │
└────────────┬──────────────────────────┘
             │
             ▼
        [Continue to Stage 3]

ENHANCEMENT: v2.0 adds institutional-grade liquidation tracking
DATA: 24 months history, ~18MB monthly parquet files
SCORING: +0.3 boost for proximity to liquidation clusters
```

**Add to Stage 3 (Timing Analysis)**:
```markdown
## DST-Aware Sessions (v2.0 Enhancement)

### Winter Sessions (November - March)
- **Asian**: 23:00 - 08:00 UTC (unchanged, Japan no DST)
- **London**: 08:00 - 17:00 UTC (GMT, Standard Time)
- **US**: 13:00 - 22:00 UTC (EST, UTC-5)

### Summer Sessions (March - November)
- **Asian**: 23:00 - 08:00 UTC (unchanged)
- **London**: 07:00 - 16:00 UTC (BST, UTC+1, -1 hour shift)
- **US**: 12:00 - 21:00 UTC (EDT, UTC-4, -1 hour shift)

**Transition Dates**:
- UK: Last Sunday March / Last Sunday October
- US: 2nd Sunday March / 1st Sunday November

**Implementation**: Automatic detection with `_is_uk_dst()` and `_is_us_dst()`
```

---

### 2. Update TBD_Logic_and_Rules_Diagram.md

**Add Section After Level Analysis**:
```markdown
### Liquidation Level Proximity (v2.0)

┌──────────────────────────────────────┐
│  CHECK LIQUIDATION CLUSTERS          │
│  Near current price?                 │
└────────────┬─────────────────────────┘
             │
    ┌────────┴────────┬──────────┐
    │                 │          │
  <1%              <2%         >2%
    │                 │          │
    ▼                 ▼          ▼
┌────────────┐ ┌────────────┐ ┌──────┐
│ Score: +0.3│ │ Score: +0.2│ │ +0.0 │
│ (Very      │ │ (Near      │ │ (Far)│
│  Close)    │ │  cluster)  │ │      │
└────────────┘ └────────────┘ └──────┘

INTERPRETATION:
├─ <1%: Price at major liquidation zone (+0.3)
├─ <2%: Approaching liquidation zone (+0.2)
└─ >2%: Not near liquidation zones (0.0)

REASON: Liquidation clusters attract price action and create reversal/breakout opportunities
```

**Update Session Times Table**:
```markdown
### DST-Aware Session Times (v2.0)

┌──────────────┬────────────────┬────────────────┐
│ Session      │ Winter (GMT/EST) │ Summer (BST/EDT) │
├──────────────┼────────────────┼────────────────┤
│ ASIAN        │ 23:00-08:00    │ 23:00-08:00    │
│ (Unchanged)  │                │                │
├──────────────┼────────────────┼────────────────┤
│ LONDON       │ 08:00-17:00    │ 07:00-16:00    │
│ (GMT/BST)    │ (GMT)          │ (BST, -1h)     │
├──────────────┼────────────────┼────────────────┤
│ NEW YORK     │ 13:00-22:00    │ 12:00-21:00    │
│ (EST/EDT)    │ (EST)          │ (EDT, -1h)     │
├──────────────┼────────────────┼────────────────┤
│ OVERLAP      │ 13:00-17:00    │ 12:00-16:00    │
│              │ (4 hours)      │ (4 hours)      │
└──────────────┴────────────────┴────────────────┘

AUTO-DETECTION: System automatically adjusts for DST transitions
```

---

### 3. Update TBD_Pattern_Decision_Trees.md

**Update Board Meeting Pattern**:
```markdown
#### Pattern 4: Board Meeting ✅

**Diagram Logic**:
1. Find consolidation (<2% range over 6-24 candles)
2. Duration check (6-24 candles)
3. **Quality Check: Early volume < Late volume? (OPTIONAL)**  ⚠️ NEW
4. Breakout detection (>50% of range)
5. Volume confirmation (>avg × 1.5)
6. Direction = breakout direction
7. Measured move targets (height × 1/2/3)

**Step 3 Enhancement (Optional)**:
```python
# Optional quality check
if board_require_volume_buildup:
    early_vol = data[:len//2]['volume'].mean()
    late_vol = data[len//2:]['volume'].mean()
    
    if late_vol <= early_vol:
        return None  # No institutional buildup
```

**Note**: This is an **optional quality filter**. Pattern works without it,
but enabling it may improve win rate by filtering weak consolidations.
```

---

## Testing Requirements

### New Tests Needed

1. **Board Meeting Volume Decline Test**:
```python
def test_board_meeting_volume_decline_optional():
    """Test Board Meeting with volume decline check (optional)"""
    # Create consolidation with declining volume
    # With check disabled: Should detect pattern
    # With check enabled: Should NOT detect pattern
    # Verify config flag works correctly
```

2. **Pattern Length Validation Tests**:
```python
def test_m_pattern_length_validation():
    """Test M-Pattern length limits"""
    # Create pattern with 5 candles (too short)
    # Should NOT detect (< min_length)
    
    # Create pattern with 60 candles (too long)
    # Should NOT detect (> max_length)
    
    # Create pattern with 30 candles (perfect)
    # Should detect

def test_w_pattern_length_validation():
    """Test W-Pattern length limits"""
    # Same structure as M-Pattern test

def test_board_meeting_length_validation():
    """Test Board Meeting consolidation length"""
    # Test min/max candles enforcement
```

---

## Implementation Priority

### High Priority (Do First)
1. ✅ Validation report (DONE)
2. 📋 Pattern length validation (quality improvement)
3. 📋 Board Meeting volume check (optional)

### Medium Priority (Can Wait)
4. 📝 Update diagram documents
5. ✅ Test coverage (already at 100%)

### Low Priority (Nice to Have)
6. Additional pattern variations
7. Advanced liquidation analysis
8. Multi-timeframe confirmation

---

## Estimated Time

| Task | Time | Complexity |
|------|------|------------|
| Pattern length validation | 30min | Low |
| Board Meeting volume check | 20min | Low |
| Test additions | 45min | Medium |
| Diagram updates | 1 hour | Low |
| **Total** | **2.5 hours** | **Low-Medium** |

---

## Success Criteria

- [ ] All patterns enforce length limits
- [ ] Board Meeting has optional volume check
- [ ] All tests pass (52/52 or 50/50)
- [ ] Diagrams reflect v2.0 features
- [ ] Code coverage maintains 100%
- [ ] Implementation matches updated diagrams

---

## Notes

These enhancements are **optional quality improvements**. The current v2.0 implementation is production-ready and validated at 98% accuracy. These changes would bring it to 100% diagram compliance and add optional quality filters.

**Recommendation**: Implement incrementally and backtest each change to measure impact on win rate and signal frequency.

---

## Related Documents

- `TBD_Flow_Validation_Report.md` - Full validation analysis
- `TBD_Decision_Flow_Diagram.md` - 9-stage flow specification
- `TBD_Logic_and_Rules_Diagram.md` - Rules and confirmations
- `TBD_Pattern_Decision_Trees.md` - Pattern algorithms
- `CHANGELOG_v2.0.md` - Version 2.0 changes

---

**Status**: Ready for implementation  
**Branch**: TBD_Flow_Check  
**Next**: Merge current work, then implement enhancements in v2.0.1
