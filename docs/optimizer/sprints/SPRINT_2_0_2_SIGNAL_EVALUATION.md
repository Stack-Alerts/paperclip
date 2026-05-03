# SPRINT 2.0.2: INSTITUTIONAL SIGNAL EVALUATION SYSTEM
**Build Institutional-Grade Signal Evaluation Engine with RECHECK, TIMING, and EXIT Hierarchy**

**Parent Sprint**: Sprint 2.0 - Real Data Integration  
**Duration**: 5 days (updated from 3 - institutional complexity validated)  
**Tasks**: 9 (updated from 6 - added RECHECK, TIMING, EXIT components)  
**Status**: 🟡 PARTIALLY COMPLETE (Core Foundation Done - TP/SL Integration Pending)  
**Priority**: 🔴🔴🔴 CRITICAL - Foundation for ALL trade decision logic  
**Dependencies**: Sprint 2.0.1 Complete

**VALIDATED FROM**: HOD Rejection v9 (Production Strategy, Created 2026-02-05 12:36)

---

## ✅ IMPLEMENTATION STATUS (Updated 2026-02-09 16:17)

### **COMPLETED TASKS** ✅

**Task 2.0.2.7**: ✅ **Config Integration COMPLETE** (2026-02-09)
- ✅ Expanded `get_config()` in backtest_config_panel.py (line ~1790)
- ✅ ALL parameters now passed:
  - Starting Capital ($10,000)
  - Risk % (10%)
  - Risk:Reward (1.2:1)
  - Leverage (10x)
  - Confluence Threshold (20 pts)
  - Max Bars Held (200 bars)
  - Complete Adaptive SL v2.0 settings (8 parameters)
- ✅ File: `src/strategy_builder/ui/backtest_config_panel.py`
- ✅ Test Result: Config logging works perfectly (see logs)

**Task 2.0.2.8**: ✅ **Config Logging COMPLETE** (2026-02-09)
- ✅ Comprehensive logging at backtest start (line ~263)
- ✅ Logs ALL config before data loading
- ✅ Formatted for readability with sections
- ✅ File: `src/strategy_builder/ui/backtest_config_panel.py`
- ✅ Test Result: Full config visible in Live Output

**Critical Fix**: ✅ **Timing Constraint Evaluation FIXED** (2026-02-09)
- ✅ Issue #5 from BACKTEST_CRITICAL_ISSUES_ANALYSIS.md resolved
- ✅ Timing constraints now properly evaluate using bar indices
- ✅ Sequential timing works: Signal2 must fire within N bars of Signal1
- ✅ File: `src/optimizer_v3/core/institutional_signal_evaluator.py`
- ✅ Test Result: Entry #1 triggered with proper timing validation

### **TEST RESULTS** (2026-02-09 16:10)

**Backtest Run**: 50% Asia Rejection Simple Strategy
```
Candles: 7,008
Trades: 1 (entry #1 at bar ~500)
Config Logging: ✅ ALL PARAMETERS LOGGED
Timing Constraints: ✅ EVALUATED CORRECTLY
Entry Detection: ✅ WORKING
```

**Current Limitation**: Trade never exits
- **Reason**: Sprint 2.0.3 (TP/SL Management) NOT YET IMPLEMENTED
- **Current**: No TP/SL levels calculated
- **Current**: No max bars held check
- **Current**: Only signal-driven exits work (none configured in test strategy)
- **Next**: Implement Sprint 2.0.3 to add TP/SL and exit logic

### **REMAINING TASKS** (Sprint 2.0.3 Needed)

**Current State**:
```python
# Trade opens but never closes because:
# 1. No TP levels calculated (Sprint 2.0.3)
# 2. No SL levels calculated (Sprint 2.0.3)
# 3. Max bars held not checked (Sprint 2.0.3)
# 4. Only signal-driven exits work
```

**What's Needed**: Sprint 2.0.3 - TP/SL Management
- Task 2.0.3.1: Implement TPSLCalculator (Fibonacci/Hybrid/Fixed)
- Task 2.0.3.2: Implement Adaptive SL v2.0 logic
- Task 2.0.3.3: Connect to user config parameters ✅ (DONE in 2.0.2.7)
- Task 2.0.3.4: Emergency SL during delay
- Task 2.0.3.5: SL updates each candle
- Task 2.0.3.6: Max bars held exit check

**Files Ready for Sprint 2.0.3**:
- ✅ `src/strategies/universal_optimizer/modules/dynamic_tp_calculator.py` (EXISTS)
- ✅ `src/strategies/universal_optimizer/modules/dynamic_sl_calculator.py` (EXISTS)
- ⏳ Need wiring in BacktestWorker.run()
- ⏳ Need TP/SL level checks every bar
- ⏳ Need max bars held check every bar

### **HANDOFF TO SPRINT 2.0.3**

**What Works Now**:
1. ✅ Config collection from UI (ALL 20+ parameters)
2. ✅ Config logging (visible in Live Output)
3. ✅ Config passing to backtest (complete dict)
4. ✅ Signal evaluation (timing constraints working)
5. ✅ Trade entry (confluence-based)

**What's Missing** (Sprint 2.0.3 scope):
1. ❌ TP level calculation (modules exist, need wiring)
2. ❌ SL level calculation (modules exist, need wiring)
3. ❌ TP/SL level checking each bar
4. ❌ Max bars held checking
5. ❌ Emergency SL during delay period
6. ❌ Adaptive SL updates

**Integration Point** (src/strategy_builder/ui/backtest_config_panel.py line ~990):
```python
# After evaluator.evaluate_bar():
# ADD Sprint 2.0.3:
# 1. Calculate TP/SL at entry using tpsl_calculator
# 2. Check TP/SL levels each bar
# 3. Check max bars held
# 4. Update Adaptive SL if enabled
# 5. Exit when conditions met
```

**Testing Checklist for Sprint 2.0.3**:
- [ ] Trade exits at TP1 level
- [ ] Trade exits at SL level
- [ ] Trade exits at max bars held (200 bars = ~50 hours for 15m)
- [ ] Emergency SL protects during delay (2 bars)
- [ ] Adaptive SL updates each candle post-delay
- [ ] Multiple trades can occur (position recycling)

---


---

## 🎯 SPRINT OBJECTIVE

Build institutional-grade SignalEvaluator to evaluate building block signals with multi-level RECHECK validation, sequential TIMING constraints, 3-tier EXIT hierarchy, and TP-aware exit calculations.

**CRITICAL INSTITUTIONAL FEATURES** (Validated from HOD Rejection v9):

1. **RECHECK System**: Multi-level signal validation
   - Initial signal fires → queue recheck
   - Recheck validates signal still true after N bars
   - Nested rechecks (recheck of recheck) up to 3 levels deep
   - Example: BELOW_HOD → 3 bar recheck → 2 bar recheck → 5 bar recheck

2. **TIMING Constraints**: Sequential signal chain
   - Signals must fire within time window of reference signal
   - Example: BELOW_HOD must fire within 12 candles of HOD_REJECTION
   - Chain: HOD_REJECTION → BELOW_HOD (12 bars) → BEARISH (10 bars)

3. **EXIT Hierarchy**: 3-tier exit system
   - Strategy-level exits (apply to ALL trades)
   - Block-level exits (apply to specific block)
   - Signal-level exits (apply to specific signal)
   - First match wins, hierarchical evaluation

4. **TP-Aware Exits**: Dynamic percentage calculation
   - Exit percentages apply to REMAINING position
   - Example: TP1 takes 30% → remaining 70% → exit 50% = 35% of original
   - Critical for partial exits

**Current State** (Hardcoded):
```python
# Line 107-135 in BacktestWorker.run():
trade_schedule = [
    (500, 1, 1500),   # Hardcoded entry at candle 500, exit at 1500
    (800, 2, 2200),
    # ... 24 hardcoded trades
]
```

**Target State** (Real Signal Evaluation):
```python
# Evaluate signals on each candle
for i, bar in enumerate(bars):
    confluence_score = signal_evaluator.evaluate_signals(
        bar,
        bars[max(0, i-100):i],  # Lookback
        strategy_config
    )
    
    if confluence_score >= config['confluence_threshold']:
        # Real entry triggered by real signals!
        open_trade(bar, confluence_score)
```

---

## ✅ TASK CHECKLIST (Updated - Institutional Architecture)

- [ ] 2.0.2.1: Design Institutional SignalEvaluator Architecture (8 hours)
- [ ] 2.0.2.2: Implement InstitutionalSignalEvaluator Core (~1,000 lines, 12 hours)
- [ ] 2.0.2.3: Implement RecheckValidator (~300 lines, 6 hours)
- [ ] 2.0.2.4: Implement TimingChainManager (~200 lines, 4 hours)
- [ ] 2.0.2.5: Implement ExitHierarchyEvaluator (~250 lines, 6 hours)
- [ ] 2.0.2.6: Implement ConfluenceCalculator with scaling (4 hours)
- [ ] 2.0.2.7: Connect to strategy config from orchestrator (3 hours)
- [ ] 2.0.2.8: Replace hardcoded trade_schedule (2 hours)
- [ ] 2.0.2.9: Implement comprehensive debug logging (4 hours)
- [ ] 2.0.2.10: Comprehensive testing (8 hours)

**Total Effort**: ~1,750 lines code, 5 days duration

---

## 📝 DETAILED TASK IMPLEMENTATION

### **Task 2.0.2.1: Design SignalEvaluator Architecture**
**Duration**: 6 hours  
**File**: Design document (then code)  
**Dependencies**: Sprint 2.0.1 complete

**Objective**: Design comprehensive architecture for signal evaluation

**Architecture Design**:

```python
"""
Signal Evaluation System Architecture

Purpose:
- Evaluate building block signals on each candle
- Calculate confluence scores
- Determine trade entries
- Track which signals fired

Components:
1. SignalEvaluator - Main evaluator class
2. BuildingBlockLoader - Loads block definitions
3. SignalConditionChecker - Checks individual signal conditions
4. ConfluenceCalculator - Calculates confluence scores
"""

class SignalEvaluator:
    """
    Main signal evaluation engine
    
    Responsibilities:
    - Load building block definitions for strategy
    - Evaluate all signals on each candle
    - Calculate confluence scores
    - Return entry decision + fired signals
    
    Usage:
        evaluator = SignalEvaluator(strategy_config)
        
        for bar in bars:
            result = evaluator.evaluate_signals(bar, lookback_bars)
            
            if result.confluence_score >= threshold:
                enter_trade(bar, result)
    """
    
    def __init__(self, strategy_config: Dict):
        """Initialize evaluator with strategy configuration"""
        self.strategy_config = strategy_config
        self.blocks = self._load_building_blocks()
        self.condition_checker = SignalConditionChecker()
        self.confluence_calc = ConfluenceCalculator()
    
    def evaluate_signals(
        self,
        current_bar: Bar,
        lookback_bars: List[Bar],
        bar_index: int
    ) -> SignalEvaluationResult:
        """
        Evaluate all signals for current candle
        
        Args:
            current_bar: Current candle to evaluate
            lookback_bars: Historical bars for context
            bar_index: Index of current bar in sequence
        
        Returns:
            SignalEvaluationResult with:
            - confluence_score: Total points earned
            - signals_fired: List of signals that triggered
            - should_enter: Boolean (score >= threshold)
        """
        pass

class SignalEvaluationResult:
    """Result of signal evaluation"""
    confluence_score: int
    signals_fired: List[str]
    signal_details: Dict[str, Any]
    should_enter: bool
    entry_side: str  # 'LONG' or 'SHORT'


class BuildingBlockLoader:
    """Loads building block definitions from registry"""
    
    def load_blocks_for_strategy(
        self,
        strategy_config: Dict
    ) -> List[BuildingBlock]:
        """Load building blocks specified in strategy"""
        pass


class SignalConditionChecker:
    """Checks individual signal conditions"""
    
    def check_signal(
        self,
        signal_name: str,
        current_bar: Bar,
        lookback_bars: List[Bar]
    ) -> bool:
        """
        Check if signal condition is met
        
        Args:
            signal_name: Name of signal (e.g., 'SIGNAL_1_HOD_REJECTION')
            current_bar: Current candle
            lookback_bars: Historical bars
        
        Returns:
            True if signal fired, False otherwise
        """
        pass


class ConfluenceCalculator:
    """Calculates confluence scores"""
    
    def calculate_confluence(
        self,
        strategy_config: Dict,
        fired_signals: List[str]
    ) -> int:
        """
        Calculate total confluence points
        
        Logic:
        - Each signal has a weight (points)
        - AND logic: Required for entry
        - OR logic: Bonus points
        
        Args:
            strategy_config: Strategy configuration
            fired_signals: List of signals that fired
        
        Returns:
            Total confluence points
        """
        pass
```

**Deliverable**: Architecture document with:
- Component diagrams
- Class hierarchy
- Data flow
- Signal evaluation algorithm
- Confluence calculation formula

**Acceptance Criteria**:
- [ ] Architecture document created
- [ ] All components defined
- [ ] Data flow documented
- [ ] Algorithm specified
- [ ] Approved by lead & Nautilus expert

**Sign-off**: ☐ Developer ☐ Architect ☐ Nautilus Expert

---

### **Task 2.0.2.2: Implement InstitutionalSignalEvaluator Core**
**Duration**: 12 hours  
**File**: `src/optimizer_v3/core/institutional_signal_evaluator.py` (NEW, ~1,000 lines)  
**Dependencies**: 2.0.2.1

**Objective**: Implement core institutional-grade signal evaluator with building block instantiation, bar-by-bar evaluation, and state management

**VALIDATED FROM**: HOD Rejection v9 real production strategy

**Implementation**:

```python
"""
Signal Evaluator - Real Signal Evaluation on Real Bars

Evaluates building block signals to determine trade entries.

CRITICAL: NO HARDCODED ENTRIES - ALL FROM REAL SIGNAL EVALUATION!

Author: BTC_Engine_v3
Date: February 2026
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from nautilus_trader.model.data import Bar
from src.strategy_builder.building_blocks_registry import get_registry


@dataclass
class SignalEvaluationResult:
    """Result of signal evaluation"""
    confluence_score: int
    signals_fired: List[str]
    signal_details: Dict[str, Any]
    should_enter: bool
    entry_side: str  # 'LONG' or 'SHORT'
    timestamp: datetime
    bar_index: int


class SignalConditionChecker:
    """
    Checks individual signal conditions
    
    Each building block has signals with specific conditions.
    This class evaluates those conditions on real bars.
    """
    
    def __init__(self):
        """Initialize condition checker"""
        self.registry = get_registry()
    
    def check_signal(
        self,
        building_block_name: str,
        signal_name: str,
        current_bar: Bar,
        lookback_bars: List[Bar]
    ) -> bool:
        """
        Check if signal condition is met
        
        Args:
            building_block_name: Name of building block (e.g., 'HOD_Rejection')
            signal_name: Name of signal (e.g., 'SIGNAL_1')
            current_bar: Current candle to evaluate
            lookback_bars: Historical bars for context (typically last 100)
        
        Returns:
            True if signal condition is met, False otherwise
        
        Example:
            checker = SignalConditionChecker()
            
            fired = checker.check_signal(
                'HOD_Rejection',
                'SIGNAL_1',
                current_bar,
                lookback_bars
            )
            
            if fired:
                print("HOD Rejection Signal 1 fired!")
        """
        # Get building block definition from registry
        block_def = self.registry.get_block(building_block_name)
        
        if not block_def:
            return False
        
        # Get signal definition
        signal_def = self._get_signal_definition(block_def, signal_name)
        
        if not signal_def:
            return False
        
        # Evaluate signal condition
        # NOTE: This is where actual signal logic goes
        # Each building block has different signal conditions
        
        try:
            return self._evaluate_signal_condition(
                signal_def,
                current_bar,
                lookback_bars
            )
        except Exception as e:
            # Log error but don't crash - just return False
            print(f"Error evaluating {building_block_name}.{signal_name}: {e}")
            return False
    
    def _get_signal_definition(
        self,
        block_def: Dict,
        signal_name: str
    ) -> Optional[Dict]:
        """Get signal definition from block"""
        if 'signals' not in block_def:
            return None
        
        for signal in block_def['signals']:
            if signal.get('name') == signal_name:
                return signal
        
        return None
    
    def _evaluate_signal_condition(
        self,
        signal_def: Dict,
        current_bar: Bar,
        lookback_bars: List[Bar]
    ) -> bool:
        """
        Evaluate specific signal condition
        
        This is the core signal detection logic.
        Each signal type has different conditions.
        
        Common Signal Types:
        - Price pattern detection (M-pattern, W-pattern, HOD/LOD rejection)
        - Volume analysis
        - Trend alignment
        - Support/Resistance
        - Indicator crossovers (RSI, VWAP, etc.)
        """
        signal_type = signal_def.get('type', 'generic')
        
        if signal_type == 'hod_rejection':
            return self._check_hod_rejection(current_bar, lookback_bars)
        elif signal_type == 'lod_rejection':
            return self._check_lod_rejection(current_bar, lookback_bars)
        elif signal_type == 'm_pattern':
            return self._check_m_pattern(current_bar, lookback_bars)
        elif signal_type == 'volume_spike':
            return self._check_volume_spike(current_bar, lookback_bars)
        elif signal_type == 'trend_alignment':
            return self._check_trend_alignment(current_bar, lookback_bars)
        else:
            # Generic condition check (placeholder)
            return False
    
    def _check_hod_rejection(
        self,
        current_bar: Bar,
        lookback_bars: List[Bar]
    ) -> bool:
        """
        Check for HOD (High of Day) rejection pattern
        
        Condition:
        - Price tested HOD
        - Strong rejection (wick > body)
        - Closed below HOD
        """
        if not lookback_bars:
            return False
        
        # Find HOD in lookback period
        hod = max(bar.high for bar in lookback_bars)
        
        # Current bar tested HOD (within 0.1%)
        tested_hod = abs(current_bar.high - hod) / hod < 0.001
        
        # Strong rejection (upper wick > body)
        body_size = abs(current_bar.close - current_bar.open)
        upper_wick = current_bar.high - max(current_bar.open, current_bar.close)
        rejection = upper_wick > body_size
        
        # Closed below HOD
        closed_below = current_bar.close < hod
        
        return tested_hod and rejection and closed_below
    
    def _check_lod_rejection(
        self,
        current_bar: Bar,
        lookback_bars: List[Bar]
    ) -> bool:
        """Check for LOD rejection pattern"""
        if not lookback_bars:
            return False
        
        lod = min(bar.low for bar in lookback_bars)
        tested_lod = abs(current_bar.low - lod) / lod < 0.001
        
        body_size = abs(current_bar.close - current_bar.open)
        lower_wick = min(current_bar.open, current_bar.close) - current_bar.low
        rejection = lower_wick > body_size
        
        closed_above = current_bar.close > lod
        
        return tested_lod and rejection and closed_above
    
    def _check_m_pattern(
        self,
        current_bar: Bar,
        lookback_bars: List[Bar]
    ) -> bool:
        """
        Check for M-pattern (double top)
        
        Condition:
        - Two similar highs
        - Dip between them
        - Current bar breaking neckline
        """
        if len(lookback_bars) < 10:
            return False
        
        # Simplified M-pattern detection
        # (Real implementation would be more sophisticated)
        
        # Find recent highs
        recent_highs = [bar.high for bar in lookback_bars[-10:]]
        
        # Check for double top pattern
        # (This is placeholder - real pattern detection is more complex)
        return False  # Placeholder
    
    def _check_volume_spike(
        self,
        current_bar: Bar,
        lookback_bars: List[Bar]
    ) -> bool:
        """Check for volume spike"""
        if len(lookback_bars) < 20:
            return False
        
        # Average volume over lookback
        avg_volume = sum(bar.volume for bar in lookback_bars[-20:]) / 20
        
        # Current volume > 2x average
        return current_bar.volume > (avg_volume * 2)
    
    def _check_trend_alignment(
        self,
        current_bar: Bar,
        lookback_bars: List[Bar]
    ) -> bool:
        """Check for trend alignment"""
        if len(lookback_bars) < 50:
            return False
        
        # Simple trend check (placeholder)
        # Real implementation would use moving averages, etc.
        recent_close = current_bar.close
        past_close = lookback_bars[-50].close
        
        # Uptrend if current > 50 bars ago
        return recent_close > past_close
```

**Testing**:
```python
# tests/optimizer_v3/test_signal_condition_checker.py

def test_hod_rejection_detection():
    """Test HOD rejection detection"""
    checker = SignalConditionChecker()
    
    # Create test bars with HOD rejection pattern
    lookback_bars = create_test_bars_with_hod(high=50100)
    current_bar = create_rejection_bar(
        high=50100,  # Tested HOD
        close=50000,  # Closed below
        open=50050,
        low=49990
    )
    
    result = checker.check_signal(
        'HOD_Rejection',
        'SIGNAL_1',
        current_bar,
        lookback_bars
    )
    
    assert result == True

def test_volume_spike_detection():
    """Test volume spike detection"""
    checker = SignalConditionChecker()
    
    # Normal volume bars
    lookback_bars = create_test_bars_with_volume(volume=1000)
    
    # Volume spike bar
    current_bar = create_bar_with_volume(volume=3000)  # 3x average
    
    result = checker._check_volume_spike(current_bar, lookback_bars)
    
    assert result == True
```

**Acceptance Criteria**:
- [ ] SignalConditionChecker implemented
- [ ] All signal types supported
- [ ] Conditions evaluate correctly on real bars
- [ ] Error handling robust
- [ ] All unit tests passing

**Functional Test**:
- [ ] Load real bars from Dec 2025
- [ ] Check HOD rejection signal - verify detects real rejections
- [ ] Check volume spike - verify detects real spikes
- [ ] Check with no signals - verify returns False correctly

**Data Accuracy Test**:
- [ ] Test with known HOD rejection (manual verification)
- [ ] Verify signal fires on correct candle
- [ ] Verify signal doesn't fire on non-rejection candles
- [ ] Test edge cases (no lookback, invalid data)

**Sign-off**: ☐ Developer ☐ QA ☐ Nautilus Expert

---

### **Task 2.0.2.3: Implement Confluence Calculation**
**Duration**: 4 hours  
**File**: `src/optimizer_v3/core/signal_evaluator.py` (continue)  
**Dependencies**: 2.0.2.2

**Objective**: Calculate confluence scores from fired signals

**Implementation**:

```python
class ConfluenceCalculator:
    """
    Calculates confluence scores
    
    Confluence Logic:
    - Each signal has a weight (points contribution)
    - AND logic signals: Required (minimum threshold)
    - OR logic signals: Bonus points
    - Total score = sum of all fired signal weights
    """
    
    def __init__(self):
        """Initialize confluence calculator"""
        pass
    
    def calculate_confluence(
        self,
        strategy_config: Dict,
        fired_signals: Dict[str, bool]
    ) -> int:
        """
        Calculate total confluence points
        
        Args:
            strategy_config: Strategy configuration with blocks and signals
            fired_signals: Dict of {signal_id: fired_bool}
        
        Returns:
            Total confluence points
        
        Example:
            calculator = ConfluenceCalculator()
            
            fired_signals = {
                'HOD_Rejection.SIGNAL_1': True,   # 25 pts (AND)
                'HOD_Rejection.SIGNAL_2': False,  # 0 pts
                'Volume_Confirm.SIGNAL_1': True,  # 15 pts (OR)
            }
            
            score = calculator.calculate_confluence(
                strategy_config,
                fired_signals
            )
            # Returns: 40 pts (25 + 15)
        """
        total_score = 0
        
        # Iterate through strategy blocks
        for block in strategy_config.get('blocks', []):
            block_name = block.get('name')
            
            # Iterate through block signals
            for signal in block.get('signals', []):
                signal_id = f"{block_name}.{signal['name']}"
                
                # Check if signal fired
                if fired_signals.get(signal_id, False):
                    # Add signal weight to total
                    weight = signal.get('weight', 10)  # Default 10 pts
                    total_score += weight
        
        return total_score
    
    def check_required_signals(
        self,
        strategy_config: Dict,
        fired_signals: Dict[str, bool]
    ) -> bool:
        """
        Check if all required (AND logic) signals fired
        
        Args:
            strategy_config: Strategy configuration
            fired_signals: Dict of fired signals
        
        Returns:
            True if all required signals fired, False otherwise
        """
        for block in strategy_config.get('blocks', []):
            block_name = block.get('name')
            
            for signal in block.get('signals', []):
                signal_id = f"{block_name}.{signal['name']}"
                
                # If signal has AND logic and didn't fire
                if signal.get('logic') == 'AND':
                    if not fired_signals.get(signal_id, False):
                        return False  # Required signal missing!
        
        return True  # All required signals fired
```

**Testing**:
```python
def test_confluence_calculation():
    """Test confluence calculation"""
    calculator = ConfluenceCalculator()
    
    strategy_config = {
        'blocks': [
            {
                'name': 'HOD_Rejection',
                'signals': [
                    {'name': 'SIGNAL_1', 'weight': 25, 'logic': 'AND'},
                    {'name': 'SIGNAL_2', 'weight': 15, 'logic': 'OR'}
                ]
            }
        ]
    }
    
    fired_signals = {
        'HOD_Rejection.SIGNAL_1': True,   # 25 pts
        'HOD_Rejection.SIGNAL_2': False   # 0 pts
    }
    
    score = calculator.calculate_confluence(strategy_config, fired_signals)
    
    assert score == 25

def test_required_signals_check():
    """Test required signal checking"""
    calculator = ConfluenceCalculator()
    
    # Missing required signal
    fired_signals = {
        'HOD_Rejection.SIGNAL_1': False,  # AND logic - REQUIRED!
        'HOD_Rejection.SIGNAL_2': True    # OR logic - bonus
    }
    
    result = calculator.check_required_signals(strategy_config, fired_signals)
    
    assert result == False  # Required signal missing
```

**Acceptance Criteria**:
- [ ] Confluence calculation working
- [ ] Weights applied correctly
- [ ] AND/OR logic handled
- [ ] Required signal checking working
- [ ] All tests passing

**Sign-off**: ☐ Developer ☐ QA

---

### **Task 2.0.2.4: Connect to Strategy Config from Orchestrator**
**Duration**: 3 hours  
**File**: `src/strategy_builder/ui/backtest_config_panel.py`  
**Dependencies**: 2.0.2.2, 2.0.2.3

**Objective**: Connect SignalEvaluator to real strategy configuration

**Implementation**:

```python
# In BacktestWorker.__init__()
from src.optimizer_v3.core.signal_evaluator import SignalEvaluator

class BacktestWorker(QThread):
    def __init__(self, orchestrator, config: dict, output_panel=None):
        super().__init__()
        self.orchestrator = orchestrator
        self.config = config
        # ... existing fields ...
        
        # NEW: Get strategy config from orchestrator
        self.strategy_config = self.orchestrator.get_current_config()
        
        # NEW: Initialize signal evaluator
        if self.strategy_config:
            self.signal_evaluator = SignalEvaluator(self.strategy_config)
        else:
            self.signal_evaluator = None
            
# In BacktestWorker.run()
def run(self):
    """Run backtest with REAL signal evaluation"""
    try:
        # Load bars (from Sprint 2.0.1)
        bars = self.data_provider.load_bars_for_backtest(...)
        total_candles = len(bars)
        
        # Verify strategy configured
        if not self.signal_evaluator:
            raise RuntimeError("No strategy configured! Please create a strategy first.")
        
        # NEW: Process each bar with signal evaluation
        open_positions = {}
        trade_id = 0
        
        for i, bar in enumerate(bars):
            # Update progress
            if i % 100 == 0:
                self.progress_updated.emit(i, total_candles, f"Evaluating signals...")
            
            # Check for stop
            if self.should_stop:
                break
            
            # NEW: Evaluate signals
            result = self.signal_evaluator.evaluate_signals(
                current_bar=bar,
                lookback_bars=bars[max(0, i-100):i],
                bar_index=i
            )
            
            # Check if entry triggered
            if result.should_enter:
                trade_id += 1
                
                self.live_message.emit(
                    f"Entry {trade_id}: Signals fired! "
                    f"Confluence: {result.confluence_score} pts "
                    f"({', '.join(result.signals_fired)})",
                    "DECISION",
                    "SIGNAL"
                )
                
                # Open position
                # (TP/SL calculation in Sprint 2.0.3)
                # For now, placeholder
                
        self.backtest_finished.emit(True, {'trades': trade_id})
        
    except Exception as e:
        self.live_message.emit(f"Error: {str(e)}", "ERROR", "SYSTEM")
        self.backtest_finished.emit(False, {'error': str(e)})
```

**Acceptance Criteria**:
- [ ] Strategy config loaded from orchestrator
- [ ] Signal evaluator initialized with strategy
- [ ] Signals evaluated on each bar
- [ ] Entry decisions made from real signals
- [ ] Live messages show fired signals

**Functional Test**:
- [ ] Create strategy with 2 building blocks
- [ ] Run backtest
- [ ] Verify signals evaluate on each bar
- [ ] Verify entry messages show fired signals
- [ ] Verify confluence scores displayed

**Sign-off**: ☐ Developer ☐ QA

---

### **Task 2.0.2.5: Replace Hardcoded trade_schedule**
**Duration**: 2 hours  
**File**: `src/strategy_builder/ui/backtest_config_panel.py`  
**Dependencies**: 2.0.2.4

**Objective**: Remove ALL hardcoded trade schedule references

**Implementation**:

```python
# REMOVE THESE LINES (lines 107-135):
# trade_schedule = [
#     (500, 1, 1500),
#     (800, 2, 2200),
#     # ... 24 hardcoded trades
# ]

# REPLACE WITH (already done in 2.0.2.4):
# Signal evaluation determines entries dynamically!
# No hardcoded schedule needed!
```

**Verification**:
```bash
# Search for hardcoded trade_schedule
grep -n "trade_schedule" src/strategy_builder/ui/backtest_config_panel.py
#Should return: 0 matches
```

**Acceptance Criteria**:
- [ ] No trade_schedule variable exists
- [ ] No hardcoded entry candles
- [ ] Entries determined by signal evaluation only
- [ ] Trade count varies based on strategy and data

**Functional Test**:
- [ ] Run with aggressive strategy - verify MORE trades
- [ ] Run with conservative strategy - verify FEWER trades
- [ ] Run with same strategy twice - verify CONSISTENT results
- [ ] Trade count NOT fixed at 24

**Data Accuracy Test**:
- [ ] Strategy with high confluence threshold (80 pts)
- [ ] Run on Dec 2025 data
- [ ] Verify only high-quality setups trigger
- [ ] Verify trade count < 10 (selective)

**Sign-off**: ☐ Developer ☐ QA

---

### **Task 2.0.2.9: Implement Comprehensive Debug Logging**
**Duration**: 4 hours  
**File**: `src/optimizer_v3/core/signal_evaluator.py` (add logging)  
**Dependencies**: 2.0.2.2, 2.0.2.3, 2.0.2.4

**Objective**: Add institutional-grade debug logging for every signal evaluation decision

**CRITICAL**: Uses existing ConfigDebugger from `src/debugger_logger/config_debugger.py`

**Requirements**:
1. Log file created automatically in `logs/signal_evaluation_TIMESTAMP.log`
2. Controlled via Main Window → Tools → Debug Logger → Enable Logging
3. Every signal evaluation logged with full context
4. Every entry/exit decision logged with reasoning
5. Every RECHECK validation logged
6. Every TIMING constraint logged
7. Every EXIT hierarchy evaluation logged
8. Viewable via Main Window → Tools → Debug Logger → View Current Log File

**Implementation**:

```python
"""
Signal Evaluator with Comprehensive Debug Logging

CRITICAL: All logging controlled via ConfigDebugger
- Enable: Main Window → Tools → Debug Logger → Enable Logging
- View: Main Window → Tools → Debug Logger → View Current Log File
"""

from src.debugger_logger.config_debugger import ConfigDebugger
from pathlib import Path
from datetime import datetime


class SignalEvaluator:
    """Signal evaluator with institutional-grade debug logging"""
    
    def __init__(self, strategy_config: Dict):
        """Initialize evaluator with debug logging"""
        self.strategy_config = strategy_config
        
        # Initialize debug logger
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.debugger = ConfigDebugger(
            name="SignalEvaluator",
            log_file=Path(f"logs/signal_evaluation_{timestamp}.log")
        )
        
        # Log initialization
        self.debugger.log_action(
            action="SIGNAL_EVALUATOR_INIT",
            config_keys_used=[],
            parameters={
                'strategy_name': strategy_config.get('name'),
                'blocks_count': len(strategy_config.get('blocks', [])),
                'total_signals': self._count_total_signals()
            }
        )
    
    def evaluate_signals(
        self,
        current_bar: Bar,
        lookback_bars: List[Bar],
        bar_index: int
    ) -> SignalEvaluationResult:
        """
        Evaluate signals with comprehensive logging
        
        LOGS:
        - Bar info (timestamp, OHLCV)
        - Each signal evaluation attempt
        - Each signal fire/fail
        - Confluence calculation
        - Entry decision
        """
        # Log bar evaluation start
        self.debugger.log_action(
            action="BAR_EVALUATION_START",
            config_keys_used=[],
            parameters={
                'bar_index': bar_index,
                'timestamp': current_bar.ts_event,
                'open': float(current_bar.open),
                'high': float(current_bar.high),
                'low': float(current_bar.low),
                'close': float(current_bar.close),
                'volume': float(current_bar.volume)
            }
        )
        
        fired_signals = {}
        
        # Evaluate each building block
        for block in self.strategy_config.get('blocks', []):
            block_name = block.get('name')
            
            self.debugger.log_action(
                action="BLOCK_EVALUATION_START",
                config_keys_used=[],
                parameters={'block_name': block_name}
            )
            
            # Evaluate each signal in block
            for signal in block.get('signals', []):
                signal_name = signal.get('name')
                signal_id = f"{block_name}.{signal_name}"
                
                # Check signal condition
                fired = self.condition_checker.check_signal(
                    block_name,
                    signal_name,
                    current_bar,
                    lookback_bars
                )
                
                fired_signals[signal_id] = fired
                
                # Log signal result
                self.debugger.log_action(
                    action="SIGNAL_EVALUATED",
                    config_keys_used=[],
                    parameters={
                        'signal_id': signal_id,
                        'fired': fired,
                        'logic': signal.get('logic'),
                        'weight': signal.get('weight'),
                        'bar_index': bar_index
                    }
                )
                
                if fired:
                    self.debugger.log_action(
                        action="SIGNAL_FIRED",
                        config_keys_used=[],
                        parameters={
                            'signal_id': signal_id,
                            'signal_type': signal.get('type'),
                            'weight': signal.get('weight')
                        }
                    )
        
        # Calculate confluence
        confluence_score = self.confluence_calc.calculate_confluence(
            self.strategy_config,
            fired_signals
        )
        
        self.debugger.log_action(
            action="CONFLUENCE_CALCULATED",
            config_keys_used=[],
            parameters={
                'confluence_score': confluence_score,
                'signals_fired_count': sum(1 for v in fired_signals.values() if v),
                fired_signals': {k: v for k, v in fired_signals.items() if v}
            }
        )
        
        # Determine entry decision
        threshold = self.strategy_config.get('confluence_threshold', 40)
        should_enter = confluence_score >= threshold
        
        if should_enter:
            self.debugger.log_action(
                action="ENTRY_TRIGGERED",
                config_keys_used=[],
                parameters={
                    'bar_index': bar_index,
                    'confluence_score': confluence_score,
                    'threshold': threshold,
                    'signals_fired': [k for k, v in fired_signals.items() if v],
                    'entry_price': float(current_bar.close),
                    'entry_side': self.strategy_config.get('type', 'LONG')
                }
            )
        else:
            self.debugger.log_action(
                action="ENTRY_REJECTED",
                config_keys_used=[],
                parameters={
                    'bar_index': bar_index,
                    'confluence_score': confluence_score,
                    'threshold': threshold,
                    'deficit': threshold - confluence_score
                }
            )
        
        # Return result
        result = SignalEvaluationResult(
            confluence_score=confluence_score,
            signals_fired=[k for k, v in fired_signals.items() if v],
            signal_details=fired_signals,
            should_enter=should_enter,
            entry_side=self.strategy_config.get('type', 'LONG'),
            timestamp=current_bar.ts_event,
            bar_index=bar_index
        )
        
        return result


class RecheckValidator:
    """RECHECK validation with debug logging"""
    
    def __init__(self):
        """Initialize with debug logger"""
        self.debugger = ConfigDebugger(
            name="RecheckValidator",
            log_file=Path("logs/recheck_validation.log")
        )
    
    def queue_recheck(
        self,
        signal_id: str,
        initial_bar_index: int,
        recheck_bars: int,
        reference_type: str
    ):
        """Queue recheck with logging"""
        self.debugger.log_action(
            action="RECHECK_QUEUED",
            config_keys_used=[],
            parameters={
                'signal_id': signal_id,
                'initial_bar_index': initial_bar_index,
                'recheck_bars': recheck_bars,
                'recheck_due_at': initial_bar_index + recheck_bars,
                'reference_type': reference_type
            }
        )
    
    def validate_recheck(
        self,
        signal_id: str,
        current_bar_index: int,
        condition_still_true: bool
    ):
        """Validate recheck with logging"""
        self.debugger.log_action(
            action="RECHECK_VALIDATED",
            config_keys_used=[],
            parameters={
                'signal_id': signal_id,
                'current_bar_index': current_bar_index,
                'condition_still_true': condition_still_true,
                'status': 'PASS' if condition_still_true else 'FAIL'
            }
        )
```

**Log File Format Example**:
```
[2026-02-06 07:45:00] [SIGNAL_EVALUATOR_INIT] Strategy: HOD Rejection, Blocks: 4, Signals: 11
[2026-02-06 07:45:00] [BAR_EVALUATION_START] Bar #500, Time: 2025-12-15 10:30, O:50100 H:50150 L:50050 C:50075 V:1250
[2026-02-06 07:45:00] [BLOCK_EVALUATION_START] Block: HOD_REJECTION
[2026-02-06 07:45:00] [SIGNAL_EVALUATED] hod.SIGNAL_1, Fired: True, Logic: AND, Weight: 25
[2026-02-06 07:45:00] [SIGNAL_FIRED] hod.SIGNAL_1, Type: hod_rejection, Weight: 25
[2026-02-06 07:45:00] [SIGNAL_EVALUATED] hod.SIGNAL_2, Fired: False, Logic: AND, Weight: 15
[2026-02-06 07:45:00] [ENTRY_REJECTED] Bar #500, Score: 25, Threshold: 40, Deficit: 15
[2026-02-06 07:45:01] [BAR_EVALUATION_START] Bar #501, Time: 2025-12-15 10:45...
```

**Acceptance Criteria**:
- [ ] Debug logger initialized with timestamp log file
- [ ] Every bar evaluation logged
- [ ] Every signal evaluation logged (fired/not fired)
- [ ] Every confluence calculation logged
- [ ] Every entry decision logged with reasoning
- [ ] Log file viewable via Main Window → Tools
- [ ] Logging controlled via Enable/Disable toggle
- [ ] Log files in logs/ directory
- [ ] No performance impact when logging disabled

**Functional Test**:
- [ ] Enable logging via Main Window → Tools → Debug Logger
- [ ] Run backtest with HOD Rejection strategy
- [ ] View log file via Main Window → Tools → View Current Log File
- [ ] Verify every signal evaluation logged
- [ ] Verify entry decisions logged
- [ ] Disable logging - verify no log file created
- [ ] Re-enable - verify new log file created

**Log File Validation**:
- [ ] Run 100-bar backtest
- [ ] Verify log has 100 BAR_EVALUATION_START entries
- [ ] Verify each bar has signal evaluations
- [ ] Verify confluence calculations present
- [ ] Verify entry/reject decisions present
- [ ] Verify log readable and parseable

**Performance Test**:
- [ ] Logging disabled: 1000 bars/second evaluation
- [ ] Logging enabled: 500 bars/second minimum
- [ ] Log file size reasonable (< 10MB per 1000 bars)

**Sign-off**: ☐ Developer ☐ QA

---

### **Task 2.0.2.10: End-to-End Testing**
**Duration**: 4 hours  
**Dependencies**: ALL above tasks

**Objective**: Comprehensive testing of signal evaluation system

**Test Cases**:

**1. Signal Detection Accuracy**:
- [ ] Create test strategy with known signals
- [ ] Run on historical data with verified patterns
- [ ] Verify signals fire on correct candles
- [ ] Verify confluence scores accurate

**2. Multiple Building Blocks**:
- [ ] Strategy with 3 building blocks
- [ ] Each block has 3 signals
- [ ] Run backtest
- [ ] Verify all blocks evaluated
- [ ] Verify confluence from all blocks

**3. AND vs OR Logic**:
- [ ] Test required (AND) signals
- [ ] Test optional (OR) signals
- [ ] Verify entry only when AND signals met
- [ ] Verify OR signals add bonus points

**4. Edge Cases**:
- [ ] Strategy with no blocks - verify error
- [ ] Strategy with all AND signals - verify selective entries
- [ ] Strategy with all OR signals - verify frequent entries
- [ ] No lookback bars - verify handles gracefully

**5. Performance**:
- [ ] 30-day backtest - evaluate time < 10s
- [ ] 180-day backtest - evaluate time < 60s
- [ ] 1000 signal evaluations/second minimum

**6. Data Accuracy**:
- [ ] Trade count varies with strategy
- [ ] Confluence scores match expected
- [ ] Signals fired list accurate
- [ ] Entry decisions consistent

**Acceptance Criteria**:
- [ ] All functional tests passing
- [ ] All data accuracy tests passing
- [ ] Performance acceptable
- [ ] No regressions

**Sign-off**: ☐ Developer ☐ QA ☐ Lead

---

## 📊 SPRINT 2.0.2 COMPLETION CRITERIA

**Complete When**:
- [ ] All 6 tasks complete
- [ ] SignalEvaluator implemented and tested
- [ ] Signals evaluate correctly on real bars
- [ ] Confluence calculation working
- [ ] Strategy config integrated
- [ ] No hardcoded trade schedules remain
- [ ] All tests passing
- [ ] Entries determined by real signals

**Sign-off Required**:
- [ ] Developer
- [ ] QA (Functional)
- [ ] QA (Data Accuracy)
- [ ] Nautilus Expert
- [ ] Lead

**Next Sprint**: 2.0.3 - TP/SL Management
