# INSTITUTIONAL GRADE VALIDATION FRAMEWORK
## Strategy Builder v3 - Post Sprint 1.8

**Date**: 2026-01-29  
**Status**: DESIGN SPECIFICATION  
**Priority**: CRITICAL - Real Money at Risk  
**Author**: Cline (NAUTILUS EXPERT Mode)

---

## EXECUTIVE SUMMARY

After Sprint 1.8 completion, the Strategy Builder has significantly increased in complexity with:
- Exit conditions at 3 binding levels (STRATEGY/BLOCK/SIGNAL)
- RECHECK chains (RECHECK of RECHECK of RECHECK...)
- Timing constraints across blocks
- Multiple exit modes (ABSOLUTE/FLEXIBLE)
- Percentage-based partial exits

**Current validation is TOO SIMPLISTIC** and fails to detect:
1. RECHECK circular dependencies
2. RECHECK of RECHECK infinite loops
3. Exit condition conflicts across binding levels
4. Dead code (unreachable signals)
5. Exit signals that don't exist
6. Timing constraint circular references
7. Percentage overflow across binding hierarchies
8. Conflicting exit modes for same signal
9. Exit conditions bound to wrong levels
10. RECHECK chains exceeding reasonable depth

---

## VALIDATION GAPS IDENTIFIED

### Gap 1: RECHECK Circular Dependencies
**Risk**: INFINITE LOOP - Strategy Deadlock  
**Example**:
```
Signal A: RECHECK (validates Signal B)
Signal B: RECHECK (validates Signal A)
```
**Impact**: Strategy never executes, waits forever

**Current Validation**: ❌ NOT DETECTED  
**Required**: Graph-based cycle detection in RECHECK references

---

### Gap 2: RECHECK of RECHECK Depth Limit
**Risk**: EXCESSIVE NESTING - Performance Degradation  
**Example**:
```
Signal A: RECHECK (validates Signal B, 3 bars)
  Signal B: RECHECK (validates Signal C, 5 bars)
    Signal C: RECHECK (validates Signal D, 10 bars)
      Signal D: RECHECK (validates Signal E, 15 bars)
```
**Impact**: 
- Cumulative bar delay: 3+5+10+15 = 33 bars
- Complex state tracking
- Memory overhead
- Difficult to debug

**Current Validation**: ❌ NOT DETECTED  
**Required**: 
- Maximum RECHECK depth limit (recommend 3)
- Cumulative bar delay calculation
- Warning at depth > 2

---

### Gap 3: Exit Condition Signal Reference Validation
**Risk**: RUNTIME ERROR - Exit Signal Not Found  
**Example**:
```
Strategy Exit: AT_ASIA_50
  Block: HOD_REJECTION
    Signal: HOD_REJECTION
    Signal: BELOW_HOD
```
**AT_ASIA_50 signal never added to strategy!**

**Current Validation**: ❌ NOT DETECTED  
**Required**: Verify all exit condition signal_names exist in building blocks registry

---

### Gap 4: Exit Percentage Conflicts Across Binding Levels
**Risk**: OVER-EXITING - More than 100% Position Closed  
**Example**:
```
STRATEGY Level:
  Exit 1: 50% AT_ASIA_50
  Exit 2: 30% VWAP_CROSS

BLOCK Level (HOD_REJECTION):
  Exit 3: 40% BEARISH_CROSS

SIGNAL Level (HOD_REJECTION::BELOW_HOD):
  Exit 4: 30% BEARISH_DIVERGENCE
```

For position from BELOW_HOD signal:
- Strategy exits: 50% + 30% = 80%
- Block exits: 40%
- Signal exits: 30%
- **TOTAL**: 150% (IMPOSSIBLE!)

**Current Validation**: ❌ NOT DETECTED  
**Required**: 
- Calculate cumulative exit percentages by binding hierarchy
- Strategy + Block + Signal <= 100%
- Warn at > 100%

---

### Gap 5: Dead Code Detection
**Risk**: MISLEADING CONFIGURATION - Never Executes  
**Example**:
```
Block 1 [AND]:
  Signal A [AND]
  Signal B [OR]  ← DEAD CODE if Block is AND
  
Block 2 [OR]:
  Signal C [AND] with timing "Within 5 bars of Block 1"
  Signal D [OR] with timing "Within 10 bars of Block 1"
```
If Block 2 is OR, but Signal C requires Block 1, and Signal D also requires Block 1...
what is the actual logic?

**Current Validation**: ❌ NOT DETECTED  
**Required**:
- Detect unreachable signals (wrong logic combinations)
- Detect timing constraints that can never be satisfied
- Warn about misleading configurations

---

### Gap 6: Timing Constraint Circular References
**Risk**: DEADLOCK - Circular Wait  
**Example**:
```
Block A::Signal 1: timing constraint "Within 5 bars of Block B::Signal 2"
Block B::Signal 2: timing constraint "Within 10 bars of Block A::Signal 1"
```

**Current Validation**: ❌ NOT DETECTED  
**Required**: 
- Build timing constraint DAG (Directed Acyclic Graph)
- Detect cycles
- Allow cross-block forward references only

---

### Gap 7: Exit Binding Level Mismatch
**Risk**: EXIT NEVER TRIGGERS - Wrong Binding Level  
**Example**:
```
Exit Condition:
  signal_name: "VWAP_CROSS_UP"
  binding_level: "BLOCK"
  block_name: "HOD_REJECTION"
  
But VWAP_CROSS_UP is in block "ASIA_SESSION", NOT "HOD_REJECTION"!
```

**Current Validation**: ❌ NOT DETECTED  
**Required**:
- Verify signal_name exists in bound block
- Verify signal_name exists in bound signal's block
- Verify block_name exists in strategy

---

### Gap 8: Conflicting Exit Modes for Same Signal
**Risk**: UNDEFINED BEHAVIOR - Which Mode Wins?  
**Example**:
```
STRATEGY Level:
  Exit: AT_ASIA_50, 20%, ABSOLUTE

BLOCK Level:
  Exit: AT_ASIA_50, 30%, FLEXIBLE
```
If AT_ASIA_50 triggers, which exit mode executes?

**Current Validation**: ❌ NOT DETECTED  
**Required**:
- Detect same signal_name in multiple exit conditions
- Flag conflicting exit_mode settings
- Recommend consolidation

---

### Gap 9: RECHECK Chain Bar Delay Accumulation
**Risk**: EXCESSIVE DELAY - Strategy Too Slow  
**Example**:
```
Signal A: bar_delay=10
  RECHECK 1: bar_delay=15
    RECHECK 2: bar_delay=20
```
Cumulative delay: 10 + 15 + 20 = 45 bars (3.75 hours on 5-min chart!)

**Current Validation**: ❌ NOT DETECTED  
**Required**:
- Calculate cumulative RECHECK delays
- Warn if cumulative > 30 bars
- Error if cumulative > 50 bars

---

### Gap 10: Exit Condition RECHECK Validation
**Risk**: EXIT RECHECK NOT VALIDATED  
**Example**:
```
Exit Condition:
  signal_name: "VWAP_CROSS"
  recheck_enabled: True
  recheck_bar_delay: 5
  
  Exit has RECHECK, but what does it validate?
  RECHECK of exit signal itself? Or entry signal?
```

**Current Validation**: ❌ NOT CLEARLY DEFINED  
**Required**:
- Define RECHECK semantics for exit conditions
- Validate RECHECK configuration on exits
- Prevent RECHECK of RECHECK on exits? (Or allow with limits)

---

## INSTITUTIONAL-GRADE VALIDATION RULES

### Severity Levels
```python
class ValidationSeverity(Enum):
    INFO = 0       # Informational, no action needed
    WARNING = 1    # Should review, not critical
    ERROR = 2      # Must fix before backtest
    CRITICAL = 3   # Must fix before live trading
```

### Validation Rule Categories

#### CATEGORY A: STRUCTURAL INTEGRITY (CRITICAL)
1. ✅ Strategy has name
2. ✅ Strategy has >= 1 block
3. ✅ Each block has >= 1 signal
4. ✅ No duplicate block names
5. ✅ No duplicate signal names within block
6. ✅ Valid logic values (AND/OR)
7. **NEW**: No orphaned exit conditions (signal_name must exist)
8. **NEW**: No circular timing constraints
9. **NEW**: No circular RECHECK dependencies

#### CATEGORY B: RECHECK VALIDATION (CRITICAL)
10. **NEW**: RECHECK depth <= 3 levels
11. **NEW**: RECHECK cumulative bar delay <= 50 bars (ERROR) / <= 30 bars (WARNING)
12. **NEW**: RECHECK parent_signal exists in same block
13. **NEW**: No RECHECK circular references (A→B→A)
14. **NEW**: RECHECK bar_delay > 0
15. **NEW**: RECHECK chains have increasing bar delays (depth 1 < depth 2 < depth 3)

#### CATEGORY C: EXIT CONDITION VALIDATION (CRITICAL)
16. ✅ Exit percentage 0 < pct <= 1.0
17. ✅ Exit mode in [ABSOLUTE, FLEXIBLE]
18. ✅ Binding level in [STRATEGY, BLOCK, SIGNAL]
19. ✅ Strategy-level exits total <= 100%
20. ✅ Block-level exits total <= 100%
21. ✅ Signal-level exits total <= 100%
22. **NEW**: Exit signal_name exists in registry
23. **NEW**: Cumulative exits (strategy + block + signal) <= 100% per position source
24. **NEW**: No conflicting exit modes for same signal across levels
25. **NEW**: Exit binding level matches signal location
26. **NEW**: FLEXIBLE mode: tp_proximity_threshold > 0
27. **NEW**: FLEXIBLE mode: reversal_trigger > 0
28. **NEW**: Exit RECHECK configuration valid (if enabled)

#### CATEGORY D: TIMING CONSTRAINT VALIDATION (ERROR)
29. ✅ Timing constraint reference signal exists
30. ✅ max_candles > 0
31. **NEW**: No circular timing dependencies
32. **NEW**: Cross-block timing references are forward-only
33. **NEW**: Timing constraint reference format valid (block::signal or signal)

#### CATEGORY E: LOGIC FLOW VALIDATION (WARNING)
34. **NEW**: No dead code (unreachable signals)
35. **NEW**: AND block with all OR signals (suspect)
36. **NEW**: OR block with all AND signals (works but misleading)
37. **NEW**: Timing constraints that can never be satisfied
38. **NEW**: Signal with timing but no dependent signal

#### CATEGORY F: PERFORMANCE & BEST PRACTICES (WARNING)
39. ✅ Total blocks <= 15
40. ✅ Signals per block <= 10
41. **NEW**: Total exit conditions <= 20
42. **NEW**: RECHECK chains <= 2 depth (recommend 1)
43. **NEW**: Cumulative RECHECK delay <= 20 bars (best practice)
44. **NEW**: Strategy level exits <= 5 (readability)

#### CATEGORY G: NAUTILUS COMPATIBILITY (WARNING)
45. ✅ Strategy name is valid Python identifier
46. ✅ Block names are valid Python identifiers
47. ✅ Signal names are valid Python identifiers
48. **NEW**: Exit signal names are valid Python identifiers
49. **NEW**: No special characters in binding references

---

## VALIDATION REPORT STRUCTURE

### Enhanced Validation Report
```python
@dataclass
class ValidationIssue:
    """Single validation issue with context"""
    severity: ValidationSeverity
    category: str
    rule_id: str
    rule_name: str
    message: str
    location: str  # e.g., "Block: HOD_REJECTION, Signal: BELOW_HOD"
    suggestion: Optional[str] = None
    affected_components: List[str] = field(default_factory=list)
    
@dataclass
class ValidationReport:
    """Comprehensive validation report"""
    timestamp: str
    is_valid: bool
    validation_level: ValidationLevel
    
    critical_issues: List[ValidationIssue] = field(default_factory=list)
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    info: List[ValidationIssue] = field(default_factory=list)
    
    strategy_summary: Dict[str, Any] = field(default_factory=dict)
    complexity_metrics: Dict[str, int] = field(default_factory=dict)
    
    def total_issues(self) -> int:
        return (len(self.critical_issues) + len(self.errors) + 
                len(self.warnings) + len(self.info))
    
    def blocking_issues(self) -> int:
        """Issues that prevent backtest/live trading"""
        return len(self.critical_issues) + len(self.errors)
```

### Complexity Metrics
```python
complexity_metrics = {
    'total_blocks': 6,
    'total_signals': 15,
    'total_exit_conditions': 8,
    'max_recheck_depth': 2,
    'max_recheck_cumulative_delay': 25,
    'total_timing_constraints': 4,
    'circular_dependencies': 0,
    'dead_code_signals': 0,
    'strategy_complexity_score': 45  # 0-100 scale
}
```

---

## CONFIGURATION BROWSER ENHANCEMENT

### **ISSUE**: Exit conditions not shown in Configuration display

### Current Display (Screenshot 1)
```
1. HOD_REJECTION [AND]
2. BELOW_HOD [AND]
    └── TIME CONSTRAINT
        └── Within 15 candles of previous signal
    └── RECHECK (6 bars)
        └── RECHECK of RECHECK (5 bars)
        └── RECHECK of Signal (10 bars)
```

### Enhanced Display (Required)
```
1. HOD_REJECTION [AND]
2. BELOW_HOD [AND]
    └── TIME CONSTRAINT
        └── Within 15 candles of previous signal
    └── RECHECK (6 bars)
        └── RECHECK of RECHECK (5 bars)
        └── RECHECK of Signal (10 bars)
    └── EXIT CONDITIONS (2)
        └── AT_ASIA_50: 30% FLEXIBLE (TP Proximity: 2.0%)
        └── VWAP_CROSS_DOWN: 20% ABSOLUTE
3. BEARISH [AND]
```

### Implementation
```python
def _format_signal_tree(signal: SignalConfig, block: BlockConfig) -> List[str]:
    """Format signal with all dependencies"""
    lines = []
    
    # Signal name and logic
    color = get_color('success') if signal.logic == 'AND' else get_color('warning')
    lines.append(f"<span style='color:{color}'>{signal.name} [{signal.logic}]</span>")
    
    # Timing constraints
    if signal.timing_constraint:
        lines.append(f"    └── TIME CONSTRAINT")
        lines.append(f"        └── Within {signal.timing_constraint.max_candles} candles of {signal.timing_constraint.reference}")
    
    # RECHECK configurations
    if signal.recheck_config and signal.recheck_config.enabled:
        lines.append(f"    └── RECHECK ({signal.recheck_config.bar_delay} bars)")
        
        # Nested RECHECKs
        for i, nested in enumerate(signal.recheck_chain, 1):
            lines.append(f"        └── RECHECK of RECHECK ({nested.bar_delay} bars)")
    
    # EXIT CONDITIONS (NEW!)
    if signal.exit_conditions:
        exit_count = len(signal.exit_conditions)
        lines.append(f"    └── <span style='color:{get_color('aqua')}'>EXIT CONDITIONS ({exit_count})</span>")
        
        for exit_cond in signal.exit_conditions:
            mode_str = f"{exit_cond.exit_mode}"
            if exit_cond.exit_mode == "FLEXIBLE":
                mode_str += f" (TP Prox: {exit_cond.tp_proximity_threshold}%)"
            
            pct_str = f"{exit_cond.percentage*100:.0f}%"
            lines.append(f"        └── {exit_cond.signal_name}: {pct_str} {mode_str}")
    
    return lines
```

---

## VALIDATION ALGORITHM PSEUDOCODE

### RECHECK Circular Dependency Detection
```python
def detect_recheck_cycles(config: StrategyConfig) -> List[str]:
    """Detect circular RECHECK dependencies"""
    errors = []
    
    # Build RECHECK dependency graph
    graph = {}
    for block in config.blocks:
        for signal in block.signals:
            node_id = f"{block.name}::{signal.name}"
            graph[node_id] = []
            
            # Add RECHECK dependency
            if signal.recheck_config and signal.recheck_config.enabled:
                parent = signal.recheck_config.parent_signal
                if parent:
                    parent_id = f"{block.name}::{parent}"
                    graph[node_id].append(parent_id)
            
            # Add nested RECHECK dependencies
            for nested in signal.recheck_chain:
                if nested.parent_signal:
                    parent_id = f"{block.name}::{nested.parent_signal}"
                    graph[node_id].append(parent_id)
    
    # DFS cycle detection
    visited = set()
    rec_stack = set()
    
    def has_cycle(node, path):
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                if has_cycle(neighbor, path.copy()):
                    return True
            elif neighbor in rec_stack:
                # Cycle found!
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                errors.append(f"RECHECK circular dependency: {' → '.join(cycle)}")
                return True
        
        rec_stack.remove(node)
        return False
    
    for node in graph:
        if node not in visited:
            has_cycle(node, [])
    
    return errors
```

### Cumulative Exit Percentage Calculation
```python
def calculate_cumulative_exit_percentages(config: StrategyConfig) -> Dict[str, float]:
    """Calculate cumulative exit percentages for each signal"""
    cumulative = {}
    
    for block in config.blocks:
        for signal in block.signals:
            signal_id = f"{block.name}::{signal.name}"
            total_pct = 0.0
            
            # Strategy-level exits (apply to all)
            for exit in config.exit_conditions:
                if exit.binding_level == "STRATEGY":
                    total_pct += exit.percentage
            
            # Block-level exits (apply to signals in this block)
            for exit in block.exit_conditions:
                if exit.binding_level == "BLOCK":
                    total_pct += exit.percentage
            
            # Signal-level exits (apply to this signal only)
            for exit in signal.exit_conditions:
                if exit.binding_level == "SIGNAL":
                    total_pct += exit.percentage
            
            cumulative[signal_id] = total_pct
            
            # Flag if > 100%
            if total_pct > 1.0:
                errors.append(
                    f"Signal {signal_id} has cumulative exits of {total_pct*100:.0f}% (> 100%)"
                )
    
    return cumulative
```

---

## IMPLEMENTATION ROADMAP

### Phase 1: Enhanced Validation Engine (2-3 hours)
- [ ] Create `InstitutionalValidator` class
- [ ] Implement RECHECK cycle detection
- [ ] Implement exit percentage accumulation
- [ ] Implement dead code detection
- [ ] Implement timing constraint cycle detection

### Phase 2: Validation Report UI (1-2 hours)
- [ ] Enhanced `ValidationReport` dataclass
- [ ] Severity-based categorization
- [ ] Expandable issue details
- [ ] One-click fix suggestions (where possible)

### Phase 3: Configuration Browser Enhancement (1 hour)
- [ ] Add exit conditions to signal display
- [ ] Color-code by binding level
- [ ] Show cumulative exit percentages
- [ ] Expandable exit details

### Phase 4: Testing & Documentation (1-2 hours)
- [ ] Test with HOD Rejection strategy
- [ ] Test with complex RECHECK chains
- [ ] Test with multi-level exit conditions
- [ ] Document all validation rules
- [ ] Update user guide

**Total Estimated Time**: 5-8 hours

---

## SUCCESS CRITERIA

✅ All 49 validation rules implemented  
✅ RECHECK circular dependencies detected  
✅ Exit percentage conflicts detected  
✅ Dead code detected  
✅ Configuration browser shows exit conditions  
✅ Validation report shows severity levels  
✅ All tests passing  
✅ Documentation complete  

---

## CONCLUSION

The current validation system is **TOO SIMPLISTIC** for the complexity introduced in Sprint 1.8. This institutional-grade framework provides:

1. **10 NEW validation categories** addressing critical gaps
2. **49 total validation rules** (up from 7)
3. **4 severity levels** for proper issue prioritization
4. **Comprehensive detection** of circular dependencies, conflicts, and dead code
5. **Enhanced UI** showing exit conditions in configuration browser

**RISK MITIGATION**: These validations prevent:
- Strategy deadlocks (circular RECHECKss)
- Over-exiting positions (> 100%)
- Runtime errors (missing exit signals)
- Dead code (never executes)
- Excessive complexity (performance issues)

**PRODUCTION STATUS**: This framework is **REQUIRED** before any strategy with Sprint 1.8 features can safely trade live.

---

**Document Status**: DESIGN COMPLETE - Ready for Implementation  
**Next Step**: Implement Phase 1 (Enhanced Validation Engine)  
**Owner**: Cline (NAUTILUS EXPERT Mode)  
**Review Date**: 2026-01-29
