# SPRINT 2.0.2: SIGNAL EVALUATION ARCHITECTURE
**Institutional-Grade Signal Evaluation Engine - Complete Implementation Specification**

**Parent Document**: SPRINT_2_0_2_SIGNAL_EVALUATION.md  
**Validated From**: HOD Rejection Strategy v9 (Created 2026-02-05 12:36)  
**Author**: BTC_Engine_v3 Team  
**Date**: February 2026  
**Status**: Implementation Specification

---

## 🎯 DOCUMENT PURPOSE

This document provides **complete institutional-grade implementation details** for the Signal Evaluation System validated against the real production HOD Rejection v9 strategy.

**Use this document for**:
- Implementation reference
- Architecture understanding
- Code review
- Testing specifications

**Refer to SPRINT_2_0_2_SIGNAL_EVALUATION.md for**:
- High-level task breakdown
- Sprint planning
- Timeline estimates
- Sign-off requirements

---

## 📊 HOD REJECTION V9 - PRODUCTION STRATEGY ANALYSIS

**Real Strategy Structure** (Screenshot validation):

```
HOD Rejection (● Bearish)

Configuration:
1. HOD_REJECTION [AND] - REQUIRED ENTRY SIGNAL
2. BELOW_HOD [AND] - REQUIRED ENTRY SIGNAL
   ├─ TIME CONSTRAINT: Within 12 candles of previous signal
   ├─ RECHECK (3 bars) - validate signal still true
   ├─ RECHECK of RECHECK (2 bars) - validate first recheck
   ├─ RECHECK of Signal (5 bars) - validate original signal
   └─ EXIT: VWAP_CROSS_UP - 15% TP-aware exit [SIGNAL]

Block-Level Exit Conditions (hod):
├─ EXIT: AT_ASIA_50 - 50% TP-aware exit [BLOCK]
└─ EXIT: BULLISH - 0% TP-aware exit [BLOCK]

3. BEARISH [AND] - REQUIRED ENTRY SIGNAL
   └─ TIME CONSTRAINT: Within 10 candles of previous signal

4. BEARISH_CROSS [OR] - OPTIONAL ENTRY SIGNAL
   ├─ RECHECK (10 bars)
   └─ RECHECK of RECHECK (10 bars)

5. BEARISH_DIVERGENCE [OR] - OPTIONAL ENTRY SIGNAL

6. BEARISH_SWEEP [OR] - OPTIONAL ENTRY SIGNAL
   ├─ RECHECK (10 bars)
   └─ RECHECK of RECHECK (10 bars)

Strategy-Level Exit Conditions (apply to all):
├─ EXIT: BULLISH_BREAKER - 50% TP-aware exit [STRATEGY]
└─ EXIT: BULLISH_CROSS - 50% immediate exit [STRATEGY]

Entry: 6 signals
Exit: 5 conditions (3 levels)
Version: v9
Created: 2026-02-05 12:36
```

---

## 🏗️ INSTITUTIONAL ARCHITECTURE COMPONENTS

### **Component 1: InstitutionalSignalEvaluator (Core Engine)**

**Responsibilities**:
- Instantiate building blocks from registry
- Evaluate signals bar-by-bar
- Manage RECHECK queue
- Validate TIMING constraints
- Calculate confluence with scaling
- Evaluate 3-tier EXIT hierarchy
- Track single trade state

**File**: `src/optimizer_v3/core/institutional_signal_evaluator.py` (~1,000 lines)

**Complete Implementation**:

```python
"""
Institutional Signal Evaluator - Production-Grade Trade Decision Engine

VALIDATED FROM: HOD Rejection v9 Strategy (Real Production)

Features:
- Multi-level RECHECK validation
- Sequential TIMING constraints
- 3-tier EXIT hierarchy
- TP-aware exit calculations
- Single trade management
- Bar-by-bar state transitions

Author: BTC_Engine_v3
Date: February 2026
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from nautilus_trader.model.data import Bar
from nautilus_trader.model.objects import Price, Quantity
from src.detectors.building_blocks.registry import BlockRegistry


@dataclass
class SignalEvaluationResult:
    """Result of signal evaluation for current bar"""
    confluence_score: int
    signals_fired: List[str]
    recheck_confirmations: List[str]
    should_enter: bool
    should_exit: bool
    exit_percentage: float
    exit_reason: str
    timing_violations: List[str]
    bar_index: int
    timestamp: datetime


@dataclass
class RecheckState:
    """
    State for pending recheck validation
    
    ENHANCED: Institutional-grade flexibility
    - reference_type: PARENT (from parent recheck) or SIGNAL (from original signal)
    - timing_mode: AT (check at bar X) or WITHIN (must re-fire within X bars)
    - signal_fire_bar: Tracks original signal bar through nested chains
    """
    signal_name: str
    block_name: str
    original_condition: Dict[str, Any]  # Condition to re-validate
    fire_bar: int  # Bar when THIS recheck was queued
    bar_delay: int  # Bars to wait before validation
    validation_mode: str  # 'SIGNAL', 'RECHECK', 'CONFIDENCE'
    
    # INSTITUTIONAL ENHANCEMENTS
    reference_type: str = 'PARENT'  # 'PARENT' or 'SIGNAL'
    timing_mode: str = 'AT'  # 'AT' or 'WITHIN'
    signal_fire_bar: Optional[int] = None  # Original signal bar (for SIGNAL reference)
    window_validated: bool = False  # For WITHIN mode tracking
    
    nested_rechecks: List['RecheckState'] = field(default_factory=list)
    parent_recheck: Optional['RecheckState'] = None


@dataclass
class TimingConstraint:
    """Timing constraint for signal"""
    signal_name: str
    reference_signal: str
    max_candles: int
    reference_fire_bar: Optional[int] = None


@dataclass
class ExitCondition:
    """Exit condition configuration"""
    signal_name: str
    percentage: float  # 0.0-1.0
    mode: str  # 'ABSOLUTE', 'FLEXIBLE'
    binding_level: str  # 'STRATEGY', 'BLOCK', 'SIGNAL'
    recheck_config: Optional[Dict] = None


@dataclass
class TradeState:
    """Current trade state (single trade)"""
    entry_bar: int
    entry_price: Price
    entry_side: str  # 'LONG', 'SHORT'
    remaining_position: float = 1.0  # 1.0 = 100%
    tp_hits: List[str] = field(default_factory=list)  # ['TP1', 'TP2']


class InstitutionalSignalEvaluator:
    """
    Production-grade signal evaluation engine
    
    CRITICAL FEATURES:
    1. Multi-level RECHECK validation (up to 3 deep)
    2. Sequential TIMING constraints
    3. 3-tier EXIT hierarchy
    4. TP-aware exit calculations
    5. Single trade management
    
    Example Flow (HOD Rejection v9):
    
    Bar 100: HOD_REJECTION fires
      └─ Record timing reference
    
    Bar 105: BELOW_HOD fires (within 12 bars ✓)
      ├─ Queue RECHECK in 3 bars
      └─ Record timing reference
    
    Bar 108: RECHECK BELOW_HOD (3 bars later)
      ├─ Validate: price still < HOD? 
      ├─ If YES: Confirm signal
      │    └─ Queue nested RECHECK in 2 bars
      └─ If NO: Invalidate signal
    
    Bar 110: RECHECK of RECHECK (2 bars after first recheck)
      ├─ Validate: first recheck still valid?
      └─ Queue next nested RECHECK in 5 bars
    
    Bar 110: BEARISH fires (within 10 bars of BELOW_HOD ✓)
      └─ All required signals confirmed
    
    Bar 110: Calculate confluence
      ├─ HOD_REJECTION: 25 pts
      ├─ BELOW_HOD (triple confirmed): 30 pts
      ├─ BEARISH: 20 pts
      └─ Total: 75 pts >= 40 threshold → ENTER
    
    Bar 150: VWAP_CROSS_UP fires (exit signal)
      ├─ Check 3-tier hierarchy
      ├─ Signal-level exit: 15% TP-aware
      ├─ Calculate: 15% of remaining position
      └─ Exit 15% of position
    """
    
    def __init__(self, strategy_config: Any):
        """
        Initialize institutional signal evaluator
        
        Args:
            strategy_config: StrategyConfig with blocks, signals, exits
        """
        self.strategy_config = strategy_config
        
        # Building blocks (instantiated from registry)
        self.building_blocks = self._instantiate_building_blocks()
        
        # State management
        self.pending_rechecks: List[RecheckState] = []
        self.timing_constraints: Dict[str, TimingConstraint] = {}
        self.fired_signals: Dict[str, int] = {}  # signal_name → fire_bar
        self.current_trade: Optional[TradeState] = None
        
        # Exit conditions (organized by level)
        self.exit_conditions = self._organize_exit_conditions()
        
        # Components
        self.recheck_validator = RecheckValidator()
        self.timing_manager = TimingChainManager()
        self.exit_evaluator = ExitHierarchyEvaluator()
        self.confluence_calc = ConfluenceCalculator()
    
    def _instantiate_building_blocks(self) -> Dict[str, Any]:
        """
        Instantiate building blocks from registry
        
        Returns:
            Dict of {block_name: block_instance}
        """
        blocks = {}
        
        for block_config in self.strategy_config.blocks:
            # Instantiate block from registry
            block_instance = BlockRegistry.instantiate(
                block_config.name,
                timeframe='15m'  # System designed for 15m
            )
            
            blocks[block_config.name] = block_instance
        
        return blocks
    
    def _organize_exit_conditions(self) -> Dict[str, List[ExitCondition]]:
        """
        Organize exit conditions by binding level
        
        Returns:
            Dict of {level: [ExitCondition]}
        """
        exits = {
            'STRATEGY': [],
            'BLOCK': {},  # {block_name: [ExitCondition]}
            'SIGNAL': {}  # {signal_name: [ExitCondition]}
        }
        
        # Strategy-level exits
        if hasattr(self.strategy_config, 'exit_conditions'):
            for exit_cond in self.strategy_config.exit_conditions:
                exits['STRATEGY'].append(ExitCondition(
                    signal_name=exit_cond.signal_name,
                    percentage=exit_cond.percentage,
                    mode=exit_cond.mode,
                    binding_level='STRATEGY',
                    recheck_config=getattr(exit_cond, 'recheck_config', None)
                ))
        
        # Block and Signal-level exits
        for block in self.strategy_config.blocks:
            # Block-level exits
            if hasattr(block, 'exit_conditions'):
                exits['BLOCK'][block.name] = [
                    ExitCondition(
                        signal_name=ec.signal_name,
                        percentage=ec.percentage,
                        mode=ec.mode,
                        binding_level='BLOCK',
                        recheck_config=getattr(ec, 'recheck_config', None)
                    )
                    for ec in block.exit_conditions
                ]
            
            # Signal-level exits
            for signal in block.signals:
                if hasattr(signal, 'exit_conditions'):
                    signal_id = f"{block.name}::{signal.name}"
                    exits['SIGNAL'][signal_id] = [
                        ExitCondition(
                            signal_name=ec.signal_name,
                            percentage=ec.percentage,
                            mode=ec.mode,
                            binding_level='SIGNAL',
                            recheck_config=getattr(ec, 'recheck_config', None)
                        )
                        for ec in signal.exit_conditions
                    ]
        
        return exits
    
    def evaluate_bar(
        self,
        bar: Bar,
        bar_index: int,
        lookback_bars: List[Bar]
    ) -> SignalEvaluationResult:
        """
        Evaluate signals for current bar - CORE EVALUATION LOOP
        
        Process:
        1. Process pending rechecks (validate confirmations)
        2. Evaluate building blocks (fresh signals)
        3. Apply timing constraints (sequential chain)
        4. Queue new rechecks (schedule validations)
        5. Calculate confluence (scaled points)
        6. If in trade: evaluate exits (3-tier hierarchy)
        7. If not in trade: check entry (confluence threshold)
        
        Args:
            bar: Current bar
            bar_index: Index in sequence
            lookback_bars: Historical bars for context
        
        Returns:
            SignalEvaluationResult with decision
        """
        # STEP 1: Process pending rechecks
        confirmed_signals = self.recheck_validator.validate_pending(
            self.pending_rechecks,
            bar,
            bar_index,
            lookback_bars,
            self.building_blocks
        )
        
        # STEP 2: Evaluate fresh signals from building blocks
        fresh_signals = self._evaluate_building_blocks(bar, lookback_bars)
        
        # STEP 3: Apply timing constraints
        valid_signals, violations = self.timing_manager.validate_timing(
            fresh_signals,
            self.fired_signals,
            bar_index
        )
        
        # STEP 4: Queue rechecks for valid signals
        new_rechecks = self._queue_rechecks(valid_signals, bar_index, bar)
        self.pending_rechecks.extend(new_rechecks)
        
        # STEP 5: Calculate confluence
        all_signals = list(valid_signals.keys()) + confirmed_signals
        confluence = self.confluence_calc.calculate(
            self.strategy_config,
            all_signals
        )
        
        # STEP 6: If in trade, check exits
        if self.current_trade:
            exit_decision = self.exit_evaluator.evaluate(
                bar,
                bar_index,
                lookback_bars,
                self.exit_conditions,
                self.current_trade,
                self.building_blocks
            )
            
            return SignalEvaluationResult(
                confluence_score=confluence,
                signals_fired=list(valid_signals.keys()),
                recheck_confirmations=confirmed_signals,
                should_enter=False,  # Already in trade
                should_exit=exit_decision.should_exit,
                exit_percentage=exit_decision.percentage,
                exit_reason=exit_decision.reason,
                timing_violations=violations,
                bar_index=bar_index,
                timestamp=bar.ts_event
            )
        
        # STEP 7: Check entry decision
        min_confluence = 40  # From strategy config
        should_enter = confluence >= min_confluence
        
        return SignalEvaluationResult(
            confluence_score=confluence,
            signals_fired=list(valid_signals.keys()),
            recheck_confirmations=confirmed_signals,
            should_enter=should_enter,
            should_exit=False,
            exit_percentage=0.0,
            exit_reason='',
            timing_violations=violations,
            bar_index=bar_index,
            timestamp=bar.ts_event
        )
    
    def _evaluate_building_blocks(
        self,
        bar: Bar,
        lookback: List[Bar]
    ) -> Dict[str, Dict]:
        """
        Evaluate all building blocks for current bar
        
        Returns:
            Dict of {signal_id: signal_data}
        """
        fired = {}
        
        for block_name, block_instance in self.building_blocks.items():
            # Call building block's analyze method
            result = block_instance.analyze(lookback + [bar])
            
            # Check if signal fired
            if result.get('signal') and result['signal'] != 'NO_SIGNAL':
                signal_id = f"{block_name}::{result['signal']}"
                fired[signal_id] = result
        
        return fired
    
    def _queue_rechecks(
        self,
        signals: Dict[str, Dict],
        bar_index: int,
        bar: Bar
    ) -> List[RecheckState]:
        """
        Queue rechecks for signals that have recheck config
        
        Returns:
            List of RecheckState objects to add to pending
        """
        rechecks = []
        
        for signal_id, signal_data in signals.items():
            # Check if signal has recheck config
            recheck_config = signal_data.get('recheck_config')
            
            if recheck_config and recheck_config.get('enabled'):
                # Create recheck state
                recheck = RecheckState(
                    signal_name=signal_id,
                    block_name=signal_id.split('::')[0],
                    original_condition={
                        'price': bar.close,
                        'signal_type': signal_data.get('signal'),
                        'metadata': signal_data.get('metadata', {})
                    },
                    fire_bar=bar_index,
                    bar_delay=recheck_config.get('bar_delay', 0),
                    validation_mode=recheck_config.get('validation_mode', 'SIGNAL')
                )
                
                # Add nested rechecks if configured
                if 'recheck_chain' in signal_data:
                    for nested_config in signal_data['recheck_chain']:
                        nested = RecheckState(
                            signal_name=signal_id,
                            block_name=signal_id.split('::')[0],
                            original_condition=recheck.original_condition,
                            fire_bar=bar_index,
                            bar_delay=nested_config.get('bar_delay', 0),
                            validation_mode=nested_config.get('validation_mode', 'RECHECK'),
                            parent_recheck=recheck
                        )
                        recheck.nested_rechecks.append(nested)
                
                rechecks.append(recheck)
        
        return rechecks
    
    def enter_trade(
        self,
        bar: Bar,
        bar_index: int,
        side: str
    ):
        """Record trade entry"""
        self.current_trade = TradeState(
            entry_bar=bar_index,
            entry_price=Price(bar.close, 2),
            entry_side=side
        )
    
    def exit_trade(
        self,
        percentage: float
    ):
        """Execute partial or full exit"""
        if self.current_trade:
            self.current_trade.remaining_position -= percentage
            
            if self.current_trade.remaining_position <= 0:
                self.current_trade = None  # Trade fully closed
```

---

### **Component 2: RecheckValidator**

**File**: `src/optimizer_v3/core/recheck_validator.py` (~300 lines)

```python
"""
RECHECK Validator - Multi-Level Signal Confirmation

Validates signals remain true after delay period.

EXAMPLE (BELOW_HOD from HOD Rejection v9):
- Bar 105: BELOW_HOD fires (price < HOD)
- Bar 108: Recheck #1 - is price still < HOD?
- Bar 110: Recheck #2 - is recheck #1 still valid?
- Bar 115: Recheck #3 - is original signal still valid?

Author: BTC_Engine_v3
Date: February 2026
"""

from typing import List, Dict, Any
from nautilus_trader.model.data import Bar


class RecheckValidator:
    """
    Validates pending recheck confirmations
    
    ENHANCED RECHECK SYSTEM:
    
    REFERENCE TYPES:
    - PARENT: Recheck relative to parent recheck fire bar
      Example: Recheck #2 at bar 2 after Recheck #1
    - SIGNAL: Recheck relative to ORIGINAL signal fire bar
      Example: Recheck of signal at bar 5 after original signal
    
    TIMING MODES:
    - AT: Validate condition AT bar X (or later)
      Example: "Check if price still < HOD at bar 108"
    - WITHIN: Signal must RE-FIRE within X bars
      Example: "HOD_REJECTION must re-fire within 20 bars"
    
    CRITICAL FIX: Preserves signal_fire_bar through nested chains
    """
    
    def validate_pending(
        self,
        pending_rechecks: List['RecheckState'],
        bar: Bar,
        bar_index: int,
        lookback: List[Bar],
        building_blocks: Dict[str, Any]
    ) -> List[str]:
        """
        Validate all pending rechecks due at current bar
        
        ENHANCED: Supports both AT and WITHIN timing modes
        
        Args:
            pending_rechecks: List of pending validations
            bar: Current bar
            bar_index: Current bar index
            lookback: Historical bars
            building_blocks: Instantiated blocks for re-evaluation
        
        Returns:
            List of confirmed signal IDs
        """
        confirmed = []
        still_pending = []
        
        for recheck in pending_rechecks:
            # Determine reference bar based on reference_type
            if recheck.reference_type == 'SIGNAL':
                # Relative to ORIGINAL signal
                reference_bar = recheck.signal_fire_bar or recheck.fire_bar
            else:  # 'PARENT'
                # Relative to parent recheck (or signal if no parent)
                reference_bar = recheck.fire_bar
            
            # Apply timing mode
            if recheck.timing_mode == 'AT':
                # AT mode: Check condition at bar X (or later)
                if bar_index >= reference_bar + recheck.bar_delay:
                    is_valid = self._validate_recheck_condition(
                        recheck,
                        bar,
                        lookback,
                        building_blocks
                    )
                    
                    if is_valid:
                        confirmed.append(recheck.signal_name)
                        
                        # Queue nested rechecks with correct reference
                        for nested in recheck.nested_rechecks:
                            if nested.reference_type == 'PARENT':
                                nested.fire_bar = bar_index  # Current bar
                            else:  # 'SIGNAL'
                                nested.fire_bar = recheck.signal_fire_bar or recheck.fire_bar
                            
                            # Preserve original signal fire bar
                            nested.signal_fire_bar = recheck.signal_fire_bar or recheck.fire_bar
                            
                            still_pending.append(nested)
                else:
                    # Not yet time
                    still_pending.append(recheck)
            
            elif recheck.timing_mode == 'WITHIN':
                # WITHIN mode: Signal must re-fire within window
                window_start = reference_bar
                window_end = reference_bar + recheck.bar_delay
                
                if bar_index < window_start:
                    # Before window starts
                    still_pending.append(recheck)
                
                elif window_start <= bar_index <= window_end:
                    # Inside window - check if signal re-fires
                    if not recheck.window_validated:
                        is_valid = self._check_signal_refires(
                            recheck,
                            bar,
                            lookback,
                            building_blocks
                        )
                        
                        if is_valid:
                            # Signal re-fired! Confirmed
                            confirmed.append(recheck.signal_name)
                            recheck.window_validated = True
                            
                            # Queue nested rechecks
                            for nested in recheck.nested_rechecks:
                                if nested.reference_type == 'PARENT':
                                    nested.fire_bar = bar_index
                                else:
                                    nested.fire_bar = recheck.signal_fire_bar or recheck.fire_bar
                                
                                nested.signal_fire_bar = recheck.signal_fire_bar or recheck.fire_bar
                                still_pending.append(nested)
                        else:
                            # Still waiting for re-fire
                            still_pending.append(recheck)
                    # else: Already validated, don't check again
                
                else:  # bar_index > window_end
                    # Past window without re-fire - invalidated
                    pass  # Don't add to confirmed or still_pending
        
        # Update pending list (in place)
        pending_rechecks.clear()
        pending_rechecks.extend(still_pending)
        
        return confirmed
    
    def _validate_recheck_condition(
        self,
        recheck: 'RecheckState',
        bar: Bar,
        lookback: List[Bar],
        building_blocks: Dict
    ) -> bool:
        """
        Validate if recheck condition still holds
        
        Validation Modes:
        - SIGNAL: Re-evaluate building block signal
        - RECHECK: Validate parent recheck still holds
        - CONFIDENCE: Check confidence threshold still met
        """
        if recheck.validation_mode == 'SIGNAL':
            return self._validate_signal_mode(recheck, bar, lookback, building_blocks)
        elif recheck.validation_mode == 'RECHECK':
            return self._validate_recheck_mode(recheck, bar, lookback)
        elif recheck.validation_mode == 'CONFIDENCE':
            return self._validate_confidence_mode(recheck, bar, lookback)
        
        return False
    
    def _validate_signal_mode(
        self,
        recheck: 'RecheckState',
        bar: Bar,
        lookback: List[Bar],
        building_blocks: Dict
    ) -> bool:
        """
        SIGNAL mode: Re-evaluate building block
        
        Example: BELOW_HOD
        - Original: price < HOD at bar 105
        - Recheck: is price still < HOD at bar 108?
        """
        block = building_blocks.get(recheck.block_name)
        
        if not block:
            return False
        
        # Re-evaluate block
        result = block.analyze(lookback + [bar])
        
        # Check if same signal still fires
        original_signal = recheck.original_condition.get('signal_type')
        current_signal = result.get('signal')
        
        return current_signal == original_signal
    
    def _validate_recheck_mode(
        self,
        recheck: 'RecheckState',
        bar: Bar,
        lookback: List[Bar]
    ) -> bool:
        """
        RECHECK mode: Validate parent recheck still holds
        
        Example: RECHECK of RECHECK
        - Parent recheck validated at bar 108
        - Child recheck validates parent still true at bar 110
        """
        if not recheck.parent_recheck:
            return False
        
        # Check if parent condition still holds
        # (Simplified - real implementation would re-validate parent)
        return True  # Placeholder
    
    def _validate_confidence_mode(
        self,
        recheck: 'RecheckState',
        bar: Bar,
        lookback: List[Bar]
    ) -> bool:
        """
        CONFIDENCE mode: Check confidence threshold
        
        Example: High confidence signal
        - Original: 95% confidence
        - Recheck: confidence still >= 90%?
        """
        original_confidence = recheck.original_condition.get('metadata', {}).get('confidence', 0)
        
        # Re-evaluate (simplified)
        return original_confidence >= 90
    
    def _check_signal_refires(
        self,
        recheck: 'RecheckState',
        bar: Bar,
        lookback: List[Bar],
        building_blocks: Dict
    ) -> bool:
        """
        WITHIN mode: Check if signal re-fires this bar
        
        Example: HOD_REJECTION within 20 bars
        - Window: bars 100-120
        - Check each bar if HOD_REJECTION fires again
        - First re-fire confirms signal
        """
        block = building_blocks.get(recheck.block_name)
        
        if not block:
            return False
        
        # Evaluate block for current bar
        result = block.analyze(lookback + [bar])
        
        # Check if same signal fires
        original_signal = recheck.original_condition.get('signal_type')
        current_signal = result.get('signal')
        
        return current_signal == original_signal
```

---

### **Component 3: TimingChainManager**

**File**: `src/optimizer_v3/core/timing_chain_manager.py` (~200 lines)

```python
"""
Timing Chain Manager - Sequential Signal Constraints

Validates signals fire within time window of reference signal.

EXAMPLE (HOD Rejection v9):
Bar 100: HOD_REJECTION fires → record as reference
Bar 105: BELOW_HOD must fire within 12 bars (100-112) ✓
Bar 110: BEARISH must fire within 10 bars of BELOW_HOD (105-115) ✓

Sequential chain validation.

Author: BTC_Engine_v3
Date: February 2026
"""

from typing import Dict, List, Tuple


class TimingChainManager:
    """
    Manages sequential timing constraints
    
    TIMING CONSTRAINT = Reference-Based Window:
    - Signal A fires at bar N (reference)
    - Signal B must fire within X bars of Signal A
    - Window: bar N to bar N+X
    - Outside window: Signal B invalid
    """
    
    def validate_timing(
        self,
        fresh_signals: Dict[str, Dict],
        fired_history: Dict[str, int],
        bar_index: int
    ) -> Tuple[Dict[str, Dict], List[str]]:
        """
        Validate timing constraints for fresh signals
        
        Args:
            fresh_signals: Signals that fired this bar
            fired_history: Historical fired signals {id: bar_index}
            bar_index: Current bar index
        
        Returns:
            (valid_signals, violations)
        """
        valid = {}
        violations = []
        
        for signal_id, signal_data in fresh_signals.items():
            # Check if signal has timing constraint
            timing = signal_data.get('timing_constraint')
            
            if not timing:
                # No constraint, always valid
                valid[signal_id] = signal_data
                fired_history[signal_id] = bar_index
                continue
            
            # Validate timing window
            reference = timing.get('reference_signal')
            max_candles = timing.get('max_candles')
            
            if reference not in fired_history:
                # Reference hasn't fired yet, signal invalid
                violations.append(
                    f"{signal_id} requires {reference} first"
                )
                continue
            
            reference_bar = fired_history[reference]
            
            if bar_index <= reference_bar + max_candles:
                # Within window ✓
                valid[signal_id] = signal_data
                fired_history[signal_id] = bar_index
            else:
                # Outside window ✗
                violations.append(
                    f"{signal_id} fired too late "
                    f"(bar {bar_index} > {reference_bar + max_candles})"
                )
        
        return valid, violations
```

---

### **Component 4: ExitHierarchyEvaluator**

**File**: `src/optimizer_v3/core/exit_hierarchy_evaluator.py` (~250 lines)

```python
"""
Exit Hierarchy Evaluator - 3-Tier Exit System

Evaluates exits in hierarchical order:
1. STRATEGY-level (highest priority)
2. BLOCK-level (medium priority)
3. SIGNAL-level (lowest priority)

First match wins.

EXAMPLE (HOD Rejection v9):
Strategy exits:
  - BULLISH_BREAKER: 50% TP-aware
  - BULLISH_CROSS: 50% immediate

Block exits (hod):
  - AT_ASIA_50: 50% TP-aware
  - BULLISH: 0% TP-aware

Signal exits (BELOW_HOD):
  - VWAP_CROSS_UP: 15% TP-aware

If BULLISH_BREAKER fires → exit 50% (strategy level wins)
If none fire → check block level
If none fire → check signal level

Author: BTC_Engine_v3
Date: February 2026
"""

from typing import Dict, List, Any
from dataclasses import dataclass
from nautilus_trader.model.data import Bar


@dataclass
class ExitDecision:
    """Result of exit evaluation"""
    should_exit: bool
    percentage: float  # TP-aware percentage
    reason: str
    mode: str


class ExitHierarchyEvaluator:
    """
    Evaluates 3-tier exit hierarchy
    
    Evaluation Order:
    1. Strategy-level (all trades)
    2. Block-level (specific block)
    3. Signal-level (specific signal)
    
    First match wins.
    """
    
    def evaluate(
        self,
        bar: Bar,
        bar_index: int,
        lookback: List[Bar],
        exit_conditions: Dict[str, List['ExitCondition']],
        current_trade: 'TradeState',
        building_blocks: Dict[str, Any]
    ) -> ExitDecision:
        """
        Evaluate 3-tier exit hierarchy
        
        Args:
            bar: Current bar
            bar_index: Current bar index
            lookback: Historical bars
            exit_conditions: Organized by level
            current_trade: Current trade state
            building_blocks: Blocks for signal evaluation
        
        Returns:
            ExitDecision with should_exit and percentage
        """
        # TIER 1: Strategy-level exits (highest priority)
        for exit_cond in exit_conditions['STRATEGY']:
            if self._check_exit_signal(exit_cond, bar, lookback, building_blocks):
                return ExitDecision(
                    should_exit=True,
                    percentage=self._calculate_tp_aware_percentage(
                        exit_cond.percentage,
                        current_trade
                    ),
                    reason=f"STRATEGY: {exit_cond.signal_name}",
                    mode=exit_cond.mode
                )
        
        # TIER 2: Block-level exits
        for block_name, exits in exit_conditions['BLOCK'].items():
            for exit_cond in exits:
                if self._check_exit_signal(exit_cond, bar, lookback, building_blocks):
                    return ExitDecision(
                        should_exit=True,
                        percentage=self._calculate_tp_aware_percentage(
                            exit_cond.percentage,
                            current_trade
                        ),
                        reason=f"BLOCK({block_name}): {exit_cond.signal_name}",
                        mode=exit_cond.mode
                    )
        
        # TIER 3: Signal-level exits
        for signal_id, exits in exit_conditions['SIGNAL'].items():
            for exit_cond in exits:
                if self._check_exit_signal(exit_cond, bar, lookback, building_blocks):
                    return ExitDecision(
                        should_exit=True,
                        percentage=self._calculate_tp_aware_percentage(
                            exit_cond.percentage,
                            current_trade
                        ),
                        reason=f"SIGNAL({signal_id}): {exit_cond.signal_name}",
                        mode=exit_cond.mode
                    )
        
        # No exit triggered
        return ExitDecision(
            should_exit=False,
            percentage=0.0,
            reason='',
            mode=''
        )
    
    def _check_exit_signal(
        self,
        exit_cond: 'ExitCondition',
        bar: Bar,
        lookback: List[Bar],
        building_blocks: Dict
    ) -> bool:
        """
        Check if exit signal fired
        
        Re-evaluates building block to check for exit signal
        """
        # Parse signal name to get block
        # Format: "VWAP_CROSS_UP" or "BULLISH_BREAKER"
        # Need to find which block contains this exit signal
        
        for block_name, block_instance in building_blocks.items():
            result = block_instance.analyze(lookback + [bar])
            
            if result.get('signal') == exit_cond.signal_name:
                return True
        
        return False
    
    def _calculate_tp_aware_percentage(
        self,
        requested_pct: float,
        current_trade: 'TradeState'
    ) -> float:
        """
        Calculate TP-aware exit percentage
        
        TP-AWARE = Exit applies to REMAINING position
        
        Example:
        - Original: 100%
        - TP1 hit (30%): Remaining = 70%
        - Exit requests 50%: Actually 50% of 70% = 35%
        
        Args:
            requested_pct: Requested exit percentage (0.0-1.0)
            current_trade: Current trade state
        
        Returns:
            Actual percentage to exit (0.0-1.0)
        """
        return requested_pct * current_trade.remaining_position
```

---

### **Component 5: ConfluenceCalculator**

**File**: `src/optimizer_v3/core/confluence_calculator.py` (~100 lines)

```python
"""
Confluence Calculator - Signal Confluence Scoring

Calculates total confluence points from fired signals.

EXAMPLE (HOD Rejection v9):
Signals:
  - HOD_REJECTION (AND): 25 pts ✓ fired
  - BELOW_HOD (AND): 30 pts ✓ fired (triple confirmed)
  - BEARISH (AND): 20 pts ✓ fired
  - BEARISH_CROSS (OR): 15 pts ✗ not fired
  - BEARISH_DIVERGENCE (OR): 10 pts ✗ not fired
  - BEARISH_SWEEP (OR): 10 pts ✗ not fired

Total: 75 pts (25 + 30 + 20)
Threshold: 40 pts
Decision: ENTER (75 >= 40)

Author: BTC_Engine_v3
Date: February 2026
"""

from typing import List, Dict, Any


class ConfluenceCalculator:
    """
    Calculates confluence scores with scaling
    
    CONFLUENCE = Weighted Signal Sum:
    - Each signal has weight (points)
    - AND signals: Required (must fire)
    - OR signals: Bonus points (optional)
    - RECHECK bonus: +20% for confirmed signals
    """
    
    def calculate(
        self,
        strategy_config: Any,
        fired_signals: List[str]
    ) -> int:
        """
        Calculate total confluence points
        
        Args:
            strategy_config: Strategy configuration
            fired_signals: List of signal IDs that fired
        
        Returns:
            Total confluence points
        """
        total = 0
        
        for block in strategy_config.blocks:
            for signal in block.signals:
                signal_id = f"{block.name}::{signal.name}"
                
                if signal_id in fired_signals:
                    # Base weight
                    weight = getattr(signal, 'weight', 10)
                    
                    # RECHECK bonus: +20% if triple confirmed
                    if signal_id.endswith('::CONFIRMED_3X'):
                        weight = int(weight * 1.2)
                    
                    total += weight
        
        return total
    
    def check_required_signals(
        self,
        strategy_config: Any,
        fired_signals: List[str]
    ) -> bool:
        """
        Check if all required (AND) signals fired
        
        Returns:
            True if all AND signals present
        """
        for block in strategy_config.blocks:
            for signal in block.signals:
                if signal.logic == 'AND':
                    signal_id = f"{block.name}::{signal.name}"
                    
                    if signal_id not in fired_signals:
                        return False  # Missing required signal!
        
        return True  # All required signals present
```

---

## 📚 USAGE EXAMPLES

### **Example 1: Simple Entry Detection**

```python
from src.optimizer_v3.core.institutional_signal_evaluator import InstitutionalSignalEvaluator

# Initialize
evaluator = InstitutionalSignalEvaluator(strategy_config)

# Evaluate bar-by-bar
for i, bar in enumerate(bars):
    result = evaluator.evaluate_bar(
        bar=bar,
        bar_index=i,
        lookback_bars=bars[max(0, i-200):i]
    )
    
    if result.should_enter:
        print(f"Bar {i}: ENTER!")
        print(f"  Confluence: {result.confluence_score} pts")
        print(f"  Signals: {result.signals_fired}")
        print(f"  Confirmed: {result.recheck_confirmations}")
        
        evaluator.enter_trade(bar, i, 'SHORT')
    
    if result.should_exit:
        print(f"Bar {i}: EXIT!")
        print(f"  Reason: {result.exit_reason}")
        print(f"  Percentage: {result.exit_percentage * 100}%")
        
        evaluator.exit_trade(result.exit_percentage)
```

---

### **Example 2: HOD Rejection v9 Flow**

```python
"""
Complete flow for HOD Rejection v9 strategy
"""

# Bar 100: HOD_REJECTION fires
result = evaluator.evaluate_bar(bars[100], 100, bars[0:100])
# Result:
#   signals_fired: ['hod::HOD_REJECTION']
#   confluence: 25 pts
#   should_enter: False (need BELOW_HOD and BEARISH)

# Bar 105: BELOW_HOD fires (within 12 bars ✓)
result = evaluator.evaluate_bar(bars[105], 105, bars[0:105])
# Result:
#   signals_fired: ['hod::BELOW_HOD']
#   timing_violations: [] (within window)
#   confluence: 55 pts (25 + 30)
#   should_enter: False (still need BEARISH)
#   pending_rechecks: [BELOW_HOD @ bar 108, 110, 115]

# Bar 108: RECHECK #1 validates
result = evaluator.evaluate_bar(bars[108], 108, bars[0:108])
# Result:
#   recheck_confirmations: ['hod::BELOW_HOD::RECHECK_1']
#   pending_rechecks: [BELOW_HOD @ bar 110, 115]

# Bar 110: BEARISH fires + RECHECK #2 validates
result = evaluator.evaluate_bar(bars[110], 110, bars[0:110])
# Result:
#   signals_fired: ['hod::BEARISH']
#   recheck_confirmations: ['hod::BELOW_HOD::RECHECK_2']
#   confluence: 75 pts (25 + 30 + 20)
#   should_enter: True ✓ (75 >= 40 threshold)

# Enter trade
evaluator.enter_trade(bars[110], 110, 'SHORT')

# Bar 150: VWAP_CROSS_UP (signal-level exit)
result = evaluator.evaluate_bar(bars[150], 150, bars[0:150])
# Result:
#   should_exit: True
#   exit_percentage: 0.15 (15% TP-aware)
#   exit_reason: 'SIGNAL(hod::BELOW_HOD): VWAP_CROSS_UP'

# Partial exit
evaluator.exit_trade(0.15)  # Remaining: 85%
```

---

## 🧪 TESTING SPECIFICATIONS

### **Unit Tests**

```python
# tests/optimizer_v3/test_institutional_signal_evaluator.py

def test_recheck_validation():
    """Test multi-level RECHECK validation"""
    evaluator = InstitutionalSignalEvaluator(hod_rejection_v9_config)
    
    # Bar 105: BELOW_HOD fires
    result = evaluator.evaluate_bar(bars[105], 105, bars[0:105])
    assert 'hod::BELOW_HOD' in result.signals_fired
    assert len(evaluator.pending_rechecks) == 3  # 3-level recheck
    
    # Bar 108: First recheck
    result = evaluator.evaluate_bar(bars[108], 108, bars[0:108])
    assert 'hod::BELOW_HOD::RECHECK_1' in result.recheck_confirmations
    
    # Bar 110: Second recheck
    result = evaluator.evaluate_bar(bars[110], 110, bars[0:110])
    assert 'hod::BELOW_HOD::RECHECK_2' in result.recheck_confirmations


def test_timing_constraints():
    """Test sequential timing validation"""
    evaluator = InstitutionalSignalEvaluator(hod_rejection_v9_config)
    
    # HOD_REJECTION fires at bar 100
    evaluator.fired_signals['hod::HOD_REJECTION'] = 100
    
    # BELOW_HOD fires at bar 105 (within 12 bars ✓)
    fresh_signals = {'hod::BELOW_HOD': {...}}
    valid, violations = evaluator.timing_manager.validate_timing(
        fresh_signals,
        evaluator.fired_signals,
        105
    )
    assert 'hod::BELOW_HOD' in valid
    assert len(violations) == 0
    
    # BELOW_HOD fires at bar 120 (outside 12 bars ✗)
    valid, violations = evaluator.timing_manager.validate_timing(
        fresh_signals,
        evaluator.fired_signals,
        120
    )
    assert 'hod::BELOW_HOD' not in valid
    assert len(violations) > 0


def test_exit_hierarchy():
    """Test 3-tier exit evaluation"""
    evaluator = InstitutionalSignalEvaluator(hod_rejection_v9_config)
    evaluator.enter_trade(bars[110], 110, 'SHORT')
    
    # Strategy-level exit should win
    # (Mock BULLISH_BREAKER signal)
    result = evaluator.evaluate_bar(bars[150], 150, bars[0:150])
    assert result.should_exit
    assert 'STRATEGY' in result.exit_reason
    assert result.exit_percentage == 0.5  # 50%


def test_tp_aware_exits():
    """Test TP-aware percentage calculation"""
    evaluator = InstitutionalSignalEvaluator(hod_rejection_v9_config)
    evaluator.enter_trade(bars[110], 110, 'SHORT')
    
    # Original: 100%
    assert evaluator.current_trade.remaining_position == 1.0
    
    # TP1 hits: 30% exit
    evaluator.exit_trade(0.3)
    assert evaluator.current_trade.remaining_position == 0.7
    
    # Exit 50% TP-aware (50% of remaining 70% = 35%)
    actual_pct = evaluator.exit_evaluator._calculate_tp_aware_percentage(
        0.5,
        evaluator.current_trade
    )
    assert actual_pct == 0.35  # 50% of 70%
```

---

## 📊 IMPLEMENTATION CHECKLIST

### **Phase 1: Core Components (3 days)**
- [ ] InstitutionalSignalEvaluator core (~1,000 lines)
  - [ ] Building block instantiation
  - [ ] Bar-by-bar evaluation loop
  - [ ] State management
  - [ ] Component integration
- [ ] RecheckValidator (~300 lines)
  - [ ] Pending queue management
  - [ ] Validation modes (SIGNAL, RECHECK, CONFIDENCE)
  - [ ] Nested recheck handling
- [ ] TimingChainManager (~200 lines)
  - [ ] Reference tracking
  - [ ] Window validation
  - [ ] Violation reporting

### **Phase 2: Exit System (2 days)**
- [ ] ExitHierarchyEvaluator (~250 lines)
  - [ ] 3-tier evaluation
  - [ ] TP-aware calculations
  - [ ] Exit signal checking
- [ ] ConfluenceCalculator (~100 lines)
  - [ ] Weight summation
  - [ ] RECHECK bonuses
  - [ ] Required signal validation

### **Phase 3: Integration & Testing (2 days)**
- [ ] Integration with BacktestWorker
- [ ] Strategy config loading
- [ ] Unit tests (100% coverage)
- [ ] Integration tests
- [ ] HOD Rejection v9 validation

---

## ✅ VALIDATION CRITERIA

### **Must Pass**:
1. **HOD Rejection v9 Re-creation**
   - Load v9 from database
   - Recreate exact signal flow
   - Verify rechecks fire correctly
   - Verify timing constraints respected
   - Verify exits hierarchical

2. **Institutional Requirements**
   - No hardcoded trade schedules
   - All entries from real signals
   - All exits from real conditions
   - State management correct
   - Error handling robust

3. **Performance**
   - 180-day backtest < 60 seconds
   - Memory efficient
   - No memory leaks
   - Thread-safe

4. **Accuracy**
   - Signal detection 100% accurate
   - Timing validation 100% correct
   - Exit hierarchy first-match guarantee
   - TP-aware calculations precise

---

## 📖 REFERENCE

**Parent Sprint**: SPRINT_2_0_2_SIGNAL_EVALUATION.md  
**Validated From**: HOD Rejection v9 (Production)  
**Total Implementation**: ~1,750 lines  
**Duration**: 5 days  

**Status**: Ready for Implementation ✅

**Author**: BTC_Engine_v3 Team  
**Date**: February 2026  
**Version**: 1.0
