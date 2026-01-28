# SPRINT 1.8: EXIT CONDITIONS FOUNDATION
**Strategy Builder Exit Conditions Enhancement**

**Duration**: 9-10 days  
**Total Tasks**: 102  
**Total Phases**: 10  
**Total Files**: 35  
**Dependencies**: Sprint 1.7 complete  
**Status**: 📋 Ready for Implementation

---

## 📋 SPRINT OVERVIEW

**Purpose**: Implement comprehensive exit condition support in Strategy Builder:
- Separate exit conditions from TP1/TP2/TP3 and SL configuration
- Add "Add as Exit" button (red) alongside AND/OR buttons
- Support percentage-based exit conditions with three binding levels
- Support nested RECHECK validation for exits
- Support ABSOLUTE and FLEXIBLE intelligent exit modes
- Full integration with existing backtest engine

**Critical Success Factors**:
- Exit condition data structures complete
- UI components for configuration
- Database schema updates
- Backtest engine integration
- Zero hardcoded styles
- Institutional-grade implementation

---

## ✅ SYSTEMATIC IMPLEMENTATION CHECKLIST

**INSTRUCTIONS**: Complete each task in order. Each task MUST be completed before proceeding to the next.

---

### PHASE 1: CORE DATA STRUCTURES (Day 1)

**File**: `src/strategy_builder/core/strategy_config_engine.py`

- [x] **1.8.1** Create ExitCondition dataclass
  ```python
  @dataclass
  class ExitCondition:
      """Exit condition with intelligent mode support"""
      signal_name: str
      percentage: float = 0.5  # 0.0 to 1.0
      exit_mode: str = "ABSOLUTE"  # "ABSOLUTE" or "FLEXIBLE"
      tp_proximity_threshold: float = 2.0
      reversal_trigger: float = 0.5
      recheck_config: Optional[RecheckConfig] = None
      recheck_chain: List[RecheckConfig] = field(default_factory=list)
      parent_signal: Optional[str] = None
      binding_level: str = "STRATEGY"  # "STRATEGY", "BLOCK", "SIGNAL"
  ```

- [x] **1.8.2** Add exit_conditions field to SignalConfig
  ```python
  @dataclass
  class SignalConfig:
      # ... existing fields ...
      exit_conditions: List[ExitCondition] = field(default_factory=list)
  ```

- [x] **1.8.3** Add exit_conditions field to BlockConfig
  ```python
  @dataclass
  class BlockConfig:
      # ... existing fields ...
      exit_conditions: List[ExitCondition] = field(default_factory=list)
  ```

- [x] **1.8.4** Add exit_conditions field to StrategyConfig
  ```python
  @dataclass
  class StrategyConfig:
      # ... existing fields ...
      exit_conditions: List[ExitCondition] = field(default_factory=list)
  ```

- [x] **1.8.5** Add DeferredExit dataclass for FLEXIBLE mode runtime tracking
  ```python
  @dataclass
  class DeferredExit:
      """Tracks deferred exit condition waiting for resolution"""
      exit_condition: ExitCondition
      position_id: str
      trigger_bar: int
      trigger_price: float
      nearest_tp: float
      nearest_tp_name: str
      peak_price_toward_tp: float
  ```

- [x] **1.8.6** Add validate_exit_conditions() to ConfigValidators class
  ```python
  @staticmethod
  def validate_exit_conditions(config: StrategyConfig) -> List[str]:
      """Validate all exit conditions across strategy"""
      errors = []
      # Validate strategy-level exits total <= 100%
      # Validate block-level exits total <= 100%
      # Validate signal-level exits total <= 100%
      # Validate each percentage in range (0, 1.0]
      # Validate exit signal exists in registry
      return errors
  ```

- [x] **1.8.7** Unit test: Verify ExitCondition dataclass creation and validation

---

### PHASE 2: PERSISTENCE LAYER (Day 1-2)

**File**: `src/strategy_builder/persistence/strategy_persistence.py`

- [x] **1.8.8** Add _exit_condition_to_dict() serialization method
  ```python
  def _exit_condition_to_dict(self, exit_condition: ExitCondition) -> dict:
      return {
          'signal_name': exit_condition.signal_name,
          'percentage': exit_condition.percentage,
          'exit_mode': exit_condition.exit_mode,
          'tp_proximity_threshold': exit_condition.tp_proximity_threshold,
          'reversal_trigger': exit_condition.reversal_trigger,
          'recheck_config': self._recheck_to_dict(exit_condition.recheck_config),
          'recheck_chain': [self._recheck_to_dict(rc) for rc in exit_condition.recheck_chain],
          'binding_level': exit_condition.binding_level
      }
  ```

- [x] **1.8.9** Add _dict_to_exit_condition() deserialization method
  ```python
  def _dict_to_exit_condition(self, data: dict) -> ExitCondition:
      return ExitCondition(
          signal_name=data['signal_name'],
          percentage=data.get('percentage', 0.5),
          exit_mode=data.get('exit_mode', 'ABSOLUTE'),
          tp_proximity_threshold=data.get('tp_proximity_threshold', 2.0),
          reversal_trigger=data.get('reversal_trigger', 0.5),
          recheck_config=self._dict_to_recheck(data.get('recheck_config')),
          recheck_chain=[self._dict_to_recheck(rc) for rc in data.get('recheck_chain', [])],
          binding_level=data.get('binding_level', 'STRATEGY')
      )
  ```

- [x] **1.8.10** Update _config_to_dict() to include strategy-level exit_conditions

- [x] **1.8.11** Update _config_to_dict() block loop to include block-level exit_conditions

- [x] **1.8.12** Update _config_to_dict() signal loop to include signal-level exit_conditions

- [x] **1.8.13** Update _dict_to_config() to parse strategy-level exit_conditions

- [x] **1.8.14** Update _dict_to_config() block parsing to include block-level exit_conditions

- [x] **1.8.15** Update _dict_to_config() signal parsing to include signal-level exit_conditions

- [x] **1.8.16** Unit test: Verify exit condition serialization round-trip

---

### PHASE 3: DATABASE SCHEMA (Day 2)

> **NOTE**: Sprint 1.6.1 now includes ORM Model Classes. Sprint 1.8 database tasks should:
> 1. Use existing `StrategyVersion.exit_conditions` column (already in 1.6.1 ORM)
> 2. Add new columns using ORM model updates (not raw SQL)
> 3. Generate Alembic migrations from ORM changes

**File**: `src/optimizer_v3/database/models.py`

- [x] **1.8.17** Verify exit_conditions JSONB column exists in StrategyVersion model
  ```python
  # Already in Sprint 1.6.1 ORM:
  exit_conditions = Column(JSONB, nullable=False)  # ✓ EXISTS
  ```

- [x] **1.8.18** Add exit_condition_results JSONB column to StrategyTestResult model
  ```python
  exit_condition_results = Column(JSONB, nullable=True)
  ```

- [x] **1.8.19** Add "exit_condition" to SignalEvent.signal_type enum values

- [x] **1.8.20** Add exit_condition_triggers field to StrategyVariation model
  ```python
  exit_condition_triggers = Column(Integer, default=0)
  ```

- [x] **1.8.21** Add exit_condition_results to BacktestResult statistics JSONB schema

**File**: `alembic/versions/[new]_add_exit_conditions.py`

- [x] **1.8.22** Create database migration script for exit_conditions columns
  ```python
  def upgrade():
      op.add_column('strategy_versions', sa.Column('exit_conditions', JSONB, nullable=False, server_default='[]'))
      op.add_column('strategy_test_results', sa.Column('exit_condition_results', JSONB, nullable=True))
      op.add_column('strategy_variations', sa.Column('exit_condition_triggers', sa.Integer, default=0))
  ```

- [x] **1.8.23** Run migration: `alembic upgrade head`

**File**: `src/optimizer_v3/database/strategy_manager.py`

- [x] **1.8.24** Update save_strategy() to include exit_conditions (Already in Sprint 1.6.1)

- [x] **1.8.25** Update load_strategy() to parse exit_conditions (Already in Sprint 1.6.1)

- [x] **1.8.26** Unit test: Verify database exit condition persistence

**File**: `src/optimizer_v3/database/test_results_manager.py`

- [x] **1.8.27** Update save_test_result() to include exit_condition_results

- [x] **1.8.28** Update load_test_result() to parse exit_condition_results

- [x] **1.8.29** Add get_exit_condition_statistics() method for aggregate stats
  ```python
  def get_exit_condition_statistics(self, strategy_id: str) -> Dict:
      """Get aggregate exit condition statistics for a strategy"""
      return {
          'total_triggers': 0,
          'trigger_by_condition': {},
          'avg_exit_percentage': Decimal(0),
          'pnl_by_condition': {}
      }
  ```

---

### PHASE 4: ORCHESTRATOR METHODS (Day 2-3)

**File**: `src/strategy_builder/integration/strategy_builder_orchestrator.py`

- [x] **1.8.30** Add add_exit_condition() WorkflowStep method
  ```python
  def add_exit_condition(
      self,
      signal_name: str,
      percentage: float,
      binding_level: str = "STRATEGY",
      block_name: Optional[str] = None,
      parent_signal_name: Optional[str] = None,
      exit_mode: str = "ABSOLUTE",
      tp_proximity_threshold: float = 2.0,
      reversal_trigger: float = 0.5
  ) -> WorkflowResult:
      """Add exit condition at specified binding level"""
  ```

- [x] **1.8.31** Add remove_exit_condition() WorkflowStep method
  ```python
  def remove_exit_condition(
      self,
      signal_name: str,
      binding_level: str = "STRATEGY",
      block_name: Optional[str] = None,
      parent_signal_name: Optional[str] = None
  ) -> WorkflowResult:
      """Remove exit condition"""
  ```

- [x] **1.8.32** Add configure_exit_condition() WorkflowStep method
  ```python
  def configure_exit_condition(
      self,
      signal_name: str,
      **kwargs
  ) -> WorkflowResult:
      """Update exit condition settings"""
  ```

- [x] **1.8.33** Unit test: Verify orchestrator exit condition CRUD methods

---

### PHASE 5: VALIDATION (Day 3)

**File**: `src/strategy_builder/validation/strategy_validator.py`

- [x] **1.8.34** Create ExitConditionValidator class
  ```python
  class ExitConditionValidator:
      def validate_exit_conditions(self, config: StrategyConfig) -> List[str]:
          errors = []
          # 1. Total percentage per binding level cannot exceed 100%
          # 2. Each percentage must be 0 < pct <= 1.0
          # 3. Exit signal must exist in registry
          # 4. No circular exit dependencies
          return errors
  ```

- [x] **1.8.35** Integrate ExitConditionValidator into main validation flow

- [x] **1.8.36** Unit test: Verify validation rules (percentage limits, circular deps)

**File**: `src/strategy_builder/ui/validation_panel.py`

- [x] **1.8.37** Add exit condition validation error category in _update_validation_display()
  ```python
  # Add "exit" keyword detection for categorizing exit validation errors
  exit_errors = [e for e in errors_list if 'exit' in e.lower()]
  if exit_errors:
      self._update_section(self.exit_section, "❌ Exit Condition Validation", "#EF4444", exit_errors)
  ```

- [x] **1.8.38** Add exit validation section widget (🔴 Exit Conditions: VALID/INVALID)

**File**: `src/strategy_builder/core/signal_dependency_resolver.py`

- [x] **1.8.39** Add ExitConditionNode dataclass for exit dependency tracking
  ```python
  @dataclass
  class ExitConditionNode:
      """Node for exit condition in dependency graph"""
      signal_name: str
      exit_mode: str  # "ABSOLUTE" or "FLEXIBLE"
      binding_level: str  # "STRATEGY", "BLOCK", "SIGNAL"
      timing_constraint: Optional[TimingConstraint] = None
      is_exit: bool = True  # Distinguishes from entry signals
  ```

- [x] **1.8.40** Update build_graph() to include exit condition nodes
  ```python
  # Add exit conditions as separate nodes
  for exit_cond in config.exit_conditions:
      node = ExitConditionNode(
          signal_name=exit_cond.signal_name,
          exit_mode=exit_cond.exit_mode,
          binding_level=exit_cond.binding_level,
          is_exit=True
      )
      graph.add_exit_node(node)
  ```

- [x] **1.8.41** Update has_circular_dependency() to handle exit condition nodes
  ```python
  # Exit conditions should NOT cause circular dependency errors
  # when they reference entry signals (exits naturally depend on entries)
  ```

- [x] **1.8.42** Update should_reset_strategy() to exclude exit condition timing violations
  ```python
  # Exit condition timing violations should NOT trigger strategy reset
  # Only entry signal timing violations cause reset
  if node.is_exit:
      continue  # Skip exit nodes for reset decision
  ```

---

### PHASE 6: UI STYLES (Day 3)

**File**: `src/strategy_builder/ui/styles.py`

- [x] **1.8.43** Add EXIT_BUTTON_STYLE constant (red theme)
  ```python
  EXIT_BUTTON_STYLE = f"""
      QPushButton {{
          background-color: {COLORS['error']};
          color: {COLORS['text_on_primary']};
          border-radius: {BORDER_RADIUS}px;
          padding: {SPACING_UNIT}px {SPACING_UNIT * 2}px;
          font-weight: 600;
      }}
      QPushButton:hover {{
          background-color: #C0392B;
      }}
  """
  ```

- [x] **1.8.44** Add EXIT_DIALOG_STYLE constant

- [x] **1.8.45** Add EXIT_TREE_ITEM_STYLE constant
  ```python
  EXIT_TREE_ITEM_STYLE = f"color: {COLORS['error']}; font-weight: 600;"
  ```

---

### PHASE 7: UI COMPONENTS (Day 3-4)

**File**: `src/strategy_builder/ui/exit_condition_dialog.py` (CREATE NEW)

- [x] **1.8.46** Create ExitConditionDialog class with:
  - Percentage input (QSpinBox 1-100%)
  - Exit mode radio buttons (ABSOLUTE/FLEXIBLE)
  - TP proximity threshold input (for FLEXIBLE mode)
  - Reversal trigger input (for FLEXIBLE mode)
  - RECHECK enable checkbox
  - Bar delay input for RECHECK
  - Tooltips for all fields
  - Centralized styles from styles.py

**File**: `src/strategy_builder/ui/block_search_panel.py`

- [x] **1.8.47** Add "Add as Exit" red button next to AND/OR buttons
  - Use EXIT_BUTTON_STYLE from styles.py
  - Add signal_added_as_exit PyQt signal
  - Connect to ExitConditionDialog

**File**: `src/strategy_builder/ui/strategy_blocks_panel.py`

- [x] **1.8.48** Add exit condition tree items display (🔴 EXIT: signal_name (50%))

- [x] **1.8.49** Add strategy-level exit conditions section at bottom of blocks panel
  - Collapsible section: "🔴 STRATEGY EXIT CONDITIONS"
  - "Add Exit Condition" button
  - Exit removal buttons [✕]

- [x] **1.8.50** Add exit condition editing support (double-click to configure)

**File**: `src/strategy_builder/ui/strategy_info_panel.py`

- [x] **1.8.51** Add Exit Conditions count to metadata row
  ```python
  # Add separator after rechecked_signals_label
  sep5 = QLabel("|")
  sep5.setStyleSheet(f"color: {get_color('text_muted')}; font-weight: bold;")
  meta_layout.addWidget(sep5)
  
  # Exit Conditions label
  exit_cond_label = QLabel("Exit Conditions:")
  exit_cond_label.setStyleSheet(get_label_style('muted'))
  exit_cond_label.setToolTip("Number of exit conditions configured")
  meta_layout.addWidget(exit_cond_label)
  
  self.exit_conditions_label = QLabel("0")
  exit_conditions_font = QFont()
  exit_conditions_font.setBold(True)
  exit_conditions_font.setPointSize(10)
  self.exit_conditions_label.setFont(exit_conditions_font)
  self.exit_conditions_label.setStyleSheet(f"color: {get_color('error')};")  # Red for exits
  meta_layout.addWidget(self.exit_conditions_label)
  ```

- [x] **1.8.52** Add _update_exit_conditions_count() method
  ```python
  def _update_exit_conditions_count(self):
      """Count exit conditions across all levels"""
      try:
          config = self.orchestrator.get_current_config()
          count = len(config.exit_conditions) if config.exit_conditions else 0  # Strategy-level
          for block in config.blocks:
              count += len(block.exit_conditions) if block.exit_conditions else 0  # Block-level
              for signal in block.signals:
                  count += len(signal.exit_conditions) if hasattr(signal, 'exit_conditions') and signal.exit_conditions else 0
          self.exit_conditions_label.setText(str(count))
          if count > 0:
              self.exit_conditions_label.setStyleSheet(f"color: {get_color('error')}; font-weight: bold;")
          else:
              self.exit_conditions_label.setStyleSheet(f"color: {get_color('text_disabled')};")
      except Exception:
          self.exit_conditions_label.setText("0")
  ```

- [x] **1.8.53** Call _update_exit_conditions_count() in refresh_from_orchestrator() and _update_metadata_row()

---

### PHASE 8: EXECUTION LAYER (Day 4-6)

**File**: `src/strategy_builder/execution/block_state_manager.py`

- [x] **1.8.54** Add ExitSignalState dataclass for exit signal tracking

- [x] **1.8.55** Add exit_signal_states dict to track exit condition state per position

- [x] **1.8.56** Add exit_signal_fired() method to record when exit signal triggers

- [x] **1.8.57** Add is_exit_condition_met() method to check if exit should execute

**File**: `src/strategy_builder/testing/walkforward_test_engine.py`

- [x] **1.8.58** Add deferred_exits dict for FLEXIBLE mode tracking
  ```python
  self.deferred_exits: Dict[str, DeferredExit] = {}
  ```

- [x] **1.8.59** Add _process_exit_conditions() method
  ```python
  def _process_exit_conditions(self, bar: pd.Series, bar_index: int) -> None:
      """Process exit conditions with intelligent mode support"""
      self._check_deferred_exits(bar, bar_index)
      for position in self.open_positions:
          for exit_condition in position.exit_conditions:
              if self._validate_exit_condition(exit_condition, bar):
                  self._handle_exit_trigger(position, exit_condition, bar, bar_index)
  ```

- [x] **1.8.60** Add _handle_exit_trigger() method with ABSOLUTE/FLEXIBLE mode logic
  ```python
  def _handle_exit_trigger(self, position, exit_condition, bar, bar_index):
      if exit_condition.exit_mode == "ABSOLUTE":
          self._execute_partial_exit(position, exit_condition.percentage, f"EXIT_{exit_condition.signal_name}")
      else:
          # FLEXIBLE: Check TP proximity, defer if appropriate
          ...
  ```

- [x] **1.8.61** Add _check_deferred_exits() method for deferred exit resolution
  ```python
  def _check_deferred_exits(self, bar: pd.Series, bar_index: int) -> None:
      """Check if deferred exits should be resolved (TP hit or reversal)"""
  ```

- [x] **1.8.62** Add _execute_partial_exit() method for partial position closure

- [x] **1.8.63** Add exit_condition_triggers, partial_exit_count, exit_condition_pnl to WalkforwardResult

- [x] **1.8.64** Update get_adjustment_report() to include exit condition tracking
  ```python
  def get_adjustment_report(self) -> Dict[str, Any]:
      report = {
          # ... existing ...
          'by_type': {
              'TP1': ...,
              'TP2': ...,
              'TP3': ...,
              'SL': ...,
              'EXIT_CONDITION': sum(1 for a in self.adjustments if a.adjustment_type.startswith("EXIT_")),  # NEW
          },
          'exit_conditions': {
              'total_triggers': 0,
              'by_condition_name': {},
              'partial_exits': 0,
              'deferred_exits': 0
          }
      }
      return report
  ```

**File**: `src/optimizer_v3/core/results/trade_analyzer.py`

- [x] **1.8.65** Add _analyze_exit_condition_performance() method
  ```python
  def _analyze_exit_condition_performance(self, trades: List[Dict]) -> Dict:
      """Analyze exit condition trigger performance"""
      return {
          'total_exit_condition_triggers': 0,
          'exit_condition_pnl': Money(0, USD),
          'exit_condition_vs_tp_comparison': {},
          'avg_exit_price_vs_tp': Decimal(0),
          'exits_by_condition': {},
          'best_performing_exit': None,
          'worst_performing_exit': None
      }
  ```

- [x] **1.8.66** Update analyze_all_trades() to include exit condition analysis
  - Add call to _analyze_exit_condition_performance()
  - Include in returned analysis dict

**File**: `src/optimizer_v3/core/results/csv_exporter.py`

- [x] **1.8.67** Add exit condition columns to _get_default_summary_columns()
  ```python
  # Add to list:
  'exit_condition_triggers',
  'exit_condition_pnl', 
  'partial_exit_count'
  ```

- [x] **1.8.68** Add exit condition columns to _get_default_trade_columns()
  ```python
  # Add to list:
  'exit_type',  # TP1/TP2/TP3/SL/EXIT_CONDITION
  'exit_condition_name',  # if applicable
  'partial_exit_percentage'
  ```

**File**: `src/optimizer_v3/core/results/recheck_metrics.py`

- [x] **1.8.69** Add exit_condition_recheck_results tracking
  ```python
  self.exit_condition_recheck_results: List[Dict] = []
  ```

- [x] **1.8.70** Add add_exit_condition_recheck_result() method
  ```python
  def add_exit_condition_recheck_result(
      self,
      exit_condition_name: str,
      recheck_passed: bool,
      recheck_bar_count: int,
      exit_executed: bool
  ) -> None:
      """Track exit condition recheck validation results"""
  ```

- [x] **1.8.71** Update calculate_metrics() to include exit condition recheck stats

**File**: `src/optimizer_v3/ui/trades_panel.py`

- [x] **1.8.72** Add exit condition columns to trades table
  - Add 'Exit Type' column (TP1/TP2/TP3/SL/EXIT_CONDITION)
  - Add 'Exit Condition' column (condition name if applicable)
  - Add 'Partial %' column (exit percentage if partial)

- [x] **1.8.73** Update add_trade() and _update_table() to display exit condition data

**File**: `src/optimizer_v3/ui/metrics_display_panel.py`

- [x] **1.8.74** Add exit condition metrics to _update_performance_table()
  - exit_condition_triggers
  - exit_condition_pnl
  - partial_exit_count

- [x] **1.8.75** Add exit condition ratings in _get_rating() method

**File**: `src/optimizer_v3/ui/backtest_panels.py`

- [x] **1.8.76** Update BacktestProgressPanel.update_results() to display exit condition results

**File**: `src/optimizer_v3/ui/live_output_panel.py`

- [x] **1.8.77** Add _append_exit_condition_message() method for exit condition triggers
  ```python
  def _append_exit_condition_message(self, msg_data: Dict) -> None:
      """Format and append exit condition trigger message"""
      # Format: [EXIT_CONDITION] signal_name triggered at price (exit_mode)
  ```

- [x] **1.8.78** Add exit condition message styling (red theme)

**File**: `src/strategy_builder/ui/backtest_config_panel.py`

- [x] **1.8.79** Update BacktestWorker.trade_data_emit signal to include exit condition fields
  ```python
  trade_data = {
      # ... existing fields ...
      'exit_type': 'EXIT_CONDITION',  # TP1/TP2/TP3/SL/EXIT_CONDITION
      'exit_condition_name': exit_condition.signal_name if exit_condition else None,
      'partial_exit_percentage': exit_condition.percentage if exit_condition else None
  }
  ```

- [x] **1.8.80** Add exit_conditions_triggered counter to progress tracking
  ```python
  # Add to progress stats line:
  exit_conditions_widget = QLabel("Exit Conditions: <b>0</b>")
  self.exit_conditions_label = exit_conditions_widget
  ```

- [x] **1.8.81** Update _populate_tabs_with_results() to include exit condition metrics
  ```python
  metrics_data = {
      # ... existing metrics ...
      'exit_condition_triggers': total_exit_triggers,
      'exit_condition_pnl': Decimal(str(exit_pnl)),
      'partial_exit_count': partial_exits
  }
  ```

- [x] **1.8.82** Add exit condition adjustment tracking to results display
  ```python
  # Update adjustments display:
  breakdown = f"(TP1: {tp1}, TP2: {tp2}, TP3: {tp3}, SL: {sl}, EXIT: {exit_count})"
  ```

**File**: `src/optimizer_v3/ui/compare_view_panel.py`

- [x] **1.8.83** Add exit condition metrics to _create_metrics_section()
  ```python
  # Add to metric_keys list:
  ('exit_condition_triggers', 'Exit Triggers', lambda x: str(int(x))),
  ('exit_condition_pnl', 'Exit PnL', lambda x: f"${float(x):,.2f}"),
  ('partial_exit_count', 'Partial Exits', lambda x: str(int(x))),
  ```

- [x] **1.8.84** Add exit condition columns to _export_comparison()
  ```python
  # Add exit_condition_triggers, exit_condition_pnl, partial_exit_count to export
  ```

**File**: `src/optimizer_v3/ui/ai_recommendations_panel.py`

- [x] **1.8.85** Add ADD_EXIT_CONDITION type to _format_action_summary()
  ```python
  elif rec_type == 'ADD_EXIT_CONDITION':
      signal_name = self.recommendation.get('signal_name', '')
      percentage = config.get('percentage', 50)
      exit_mode = config.get('exit_mode', 'ABSOLUTE')
      return f"Add exit condition: '{signal_name}' at {percentage}% ({exit_mode} mode)"
  ```

- [x] **1.8.86** Add ADJUST_EXIT_CONDITION type to _format_action_summary()
  ```python
  elif rec_type == 'ADJUST_EXIT_CONDITION':
      signal_name = self.recommendation.get('signal_name', '')
      new_percentage = config.get('new_percentage', '?')
      return f"Adjust exit condition '{signal_name}' to {new_percentage}%"
  ```

---

### PHASE 9: TESTING (Day 8-9)

**File**: `tests/strategy_builder/test_exit_conditions.py` (CREATE NEW)

- [x] **1.8.87** Unit tests for ExitCondition dataclass creation
- [x] **1.8.88** Unit tests for ExitCondition validation (percentage limits)

**File**: `tests/strategy_builder/test_exit_persistence.py` (CREATE NEW)

- [x] **1.8.89** Unit tests for exit condition serialization
- [x] **1.8.90** Unit tests for exit condition deserialization

**File**: `tests/strategy_builder/test_exit_orchestrator.py` (CREATE NEW)

- [x] **1.8.91** Unit tests for add_exit_condition()
- [x] **1.8.92** Unit tests for remove_exit_condition()
- [x] **1.8.93** Unit tests for configure_exit_condition()

**File**: `tests/strategy_builder/test_exit_validation.py` (CREATE NEW)

- [x] **1.8.94** Unit tests for percentage validation rules
- [x] **1.8.95** Unit tests for circular dependency detection

**File**: `tests/integration/test_exit_workflow.py` (CREATE NEW)

- [x] **1.8.96** Integration test: Complete exit condition workflow (add → save → load → execute)
- [x] **1.8.97** Integration test: ABSOLUTE mode execution

**File**: `tests/integration/test_exit_flexible_mode.py` (CREATE NEW)

- [x] **1.8.98** Integration test: FLEXIBLE mode TP proximity deferral
- [x] **1.8.99** Integration test: FLEXIBLE mode reversal trigger

---

### PHASE 10: UI POLISH & DOCUMENTATION (Day 9-10)

**File**: `src/strategy_builder/ui/strategy_browser_dialog.py`

- [x] **1.8.100** Add exit conditions to strategy preview

**File**: `src/strategy_builder/ui/content_measurement.py`

- [x] **1.8.101** Add exit condition row height estimation

**File**: Documentation

- [x] **1.8.102** Update user documentation with exit conditions usage
  - Add EXIT_CONDITIONS.md user guide
  - Add tooltips to all exit condition UI elements

---

## 📊 IMPLEMENTATION ORDER SUMMARY

```
PHASE 1: Core Data Structures (Tasks 1.8.1-1.8.7)
    ↓
PHASE 2: Persistence Layer (Tasks 1.8.8-1.8.16)
    ↓
PHASE 3: Database Schema (Tasks 1.8.17-1.8.29)
    ↓
PHASE 4: Orchestrator Methods (Tasks 1.8.30-1.8.33)
    ↓
PHASE 5: Validation (Tasks 1.8.34-1.8.42)
    ↓
PHASE 6: UI Styles (Tasks 1.8.43-1.8.45)
    ↓
PHASE 7: UI Components (Tasks 1.8.46-1.8.53)
    ↓
PHASE 8: Execution Layer (Tasks 1.8.54-1.8.86)
    ↓
PHASE 9: Testing (Tasks 1.8.87-1.8.99)
    ↓
PHASE 10: UI Polish & Documentation (Tasks 1.8.100-1.8.102)
```

---

## 📁 FILES TO MODIFY/CREATE (35 Total)

| # | File Path | Action | Phase | Description |
|---|-----------|--------|-------|-------------|
| 1 | `src/strategy_builder/core/strategy_config_engine.py` | MODIFY | 1 | ExitCondition, DeferredExit dataclasses |
| 2 | `src/strategy_builder/persistence/strategy_persistence.py` | MODIFY | 2 | Serialization/deserialization methods |
| 3 | `src/optimizer_v3/database/models.py` | MODIFY | 3 | JSONB columns for exit_conditions |
| 4 | `alembic/versions/[new]_add_exit_conditions.py` | CREATE | 3 | Database migration |
| 5 | `src/optimizer_v3/database/strategy_manager.py` | MODIFY | 3 | Save/load exit conditions |
| 6 | `src/optimizer_v3/database/test_results_manager.py` | MODIFY | 3 | Exit condition results storage |
| 7 | `src/strategy_builder/integration/strategy_builder_orchestrator.py` | MODIFY | 4 | CRUD methods |
| 8 | `src/strategy_builder/validation/strategy_validator.py` | MODIFY | 5 | ExitConditionValidator |
| 9 | `src/strategy_builder/ui/validation_panel.py` | MODIFY | 5 | Exit validation error display |
| 10 | `src/strategy_builder/core/signal_dependency_resolver.py` | MODIFY | 5 | Exit condition dependency tracking |
| 11 | `src/strategy_builder/ui/styles.py` | MODIFY | 6 | EXIT_BUTTON_STYLE, EXIT_DIALOG_STYLE |
| 12 | `src/strategy_builder/ui/exit_condition_dialog.py` | CREATE | 7 | Exit configuration dialog |
| 13 | `src/strategy_builder/ui/block_search_panel.py` | MODIFY | 7 | "Add as Exit" button |
| 14 | `src/strategy_builder/ui/strategy_blocks_panel.py` | MODIFY | 7 | Exit display, strategy-level section |
| 15 | `src/strategy_builder/ui/strategy_info_panel.py` | MODIFY | 7 | Exit Conditions count in metadata |
| 16 | `src/strategy_builder/execution/block_state_manager.py` | MODIFY | 8 | Exit signal state tracking |
| 17 | `src/strategy_builder/testing/walkforward_test_engine.py` | MODIFY | 8 | Exit processing, FLEXIBLE mode, adjustment report |
| 18 | `src/optimizer_v3/core/results/trade_analyzer.py` | MODIFY | 8 | Exit condition performance analysis |
| 19 | `src/optimizer_v3/core/results/csv_exporter.py` | MODIFY | 8 | Exit condition columns in exports |
| 20 | `src/optimizer_v3/core/results/recheck_metrics.py` | MODIFY | 8 | Exit condition recheck stats |
| 21 | `src/optimizer_v3/ui/trades_panel.py` | MODIFY | 8 | Exit condition columns in trades table |
| 22 | `src/optimizer_v3/ui/metrics_display_panel.py` | MODIFY | 8 | Exit condition metrics display |
| 23 | `src/optimizer_v3/ui/backtest_panels.py` | MODIFY | 8 | Exit condition results display |
| 24 | `src/optimizer_v3/ui/live_output_panel.py` | MODIFY | 8 | Exit condition message formatting |
| 25 | `src/strategy_builder/ui/backtest_config_panel.py` | MODIFY | 8 | BacktestWorker exit data, progress tracking |
| 26 | `src/optimizer_v3/ui/compare_view_panel.py` | MODIFY | 8 | Exit condition comparison metrics |
| 27 | `src/optimizer_v3/ui/ai_recommendations_panel.py` | MODIFY | 8 | Exit condition recommendation types |
| 28 | `tests/strategy_builder/test_exit_conditions.py` | CREATE | 9 | Unit tests |
| 29 | `tests/strategy_builder/test_exit_persistence.py` | CREATE | 9 | Persistence tests |
| 30 | `tests/strategy_builder/test_exit_orchestrator.py` | CREATE | 9 | Orchestrator tests |
| 31 | `tests/strategy_builder/test_exit_validation.py` | CREATE | 9 | Validation tests |
| 32 | `tests/integration/test_exit_workflow.py` | CREATE | 9 | Integration tests |
| 33 | `tests/integration/test_exit_flexible_mode.py` | CREATE | 9 | FLEXIBLE mode tests |
| 34 | `src/strategy_builder/ui/strategy_browser_dialog.py` | MODIFY | 10 | Exit preview |
| 35 | `src/strategy_builder/ui/content_measurement.py` | MODIFY | 10 | Exit row height |

---

## 🎯 EXIT CONDITION BINDING LEVELS

Exit conditions can be applied at **THREE** levels:

| Level | Scope | Use Case |
|-------|-------|----------|
| **STRATEGY** | All positions from this strategy | Single exit logic for entire strategy |
| **BLOCK** | Positions from specific block | Different blocks need different exits |
| **SIGNAL** | Bound to triggering signal | Granular per-signal exit control |

---

## 🧠 EXIT MODES

| Mode | Behavior |
|------|----------|
| **ABSOLUTE** | Exit IMMEDIATELY when signal triggers |
| **FLEXIBLE** | Consider TP proximity; defer if price heading toward TP; fire on reversal |

---

## 📈 EXIT CONDITION FLOW EXAMPLES

> **Note:** All signal names below are REAL signals from the Building Blocks Registry.
> Reference: `src/detectors/building_blocks/`

### Example 1: ABSOLUTE Mode - Immediate Exit (50%)

**Setup:**
- Strategy has `HOD_REJECTION` (from `hod` block) as exit condition at 50%
- LONG position open at $45,000
- TP1 at $45,500, TP2 at $46,000, TP3 at $46,500, SL at $44,500

**Signal Reference:** `src/detectors/building_blocks/price_levels/hod.py`
```python
valid_signals=['HOD_REJECTION', 'AT_HOD', 'BELOW_HOD', 'ABOVE_HOD', 'BULLISH', 'BEARISH', 'NEUTRAL']
```

**Flow:**
```
Bar 15: HOD_REJECTION signal fires (price rejected from yesterday's high)
        ↓
        Exit Mode = ABSOLUTE
        ↓
        Execute 50% position exit immediately
        ↓
        Exit at current price $45,200
        ↓
        Remaining 50% continues toward TP targets
```

**Result:** 50% position closed at $45,200, 50% still tracking TP1/TP2/TP3/SL

---

### Example 2: FLEXIBLE Mode - Price Heading Toward TP (Defer)

**Setup:**
- Strategy has `BELOW_HOD` (from `hod` block) as exit condition at 30%
- Exit mode = FLEXIBLE, TP proximity threshold = 2.0%
- LONG position at $45,000
- TP1 at $45,500 (1.1% away), current price $45,300

**Signal Reference:** `src/detectors/building_blocks/price_levels/hod.py`
```python
'BELOW_HOD': {'description': 'Price below yesterday\'s high. HOD acting as resistance.'}
```

**Flow:**
```
Bar 20: BELOW_HOD signal fires
        ↓
        Exit Mode = FLEXIBLE
        ↓
        Check TP proximity: $45,300 → $45,500 = 0.44% (within 2.0% threshold)
        ↓
        Check price direction: Price rising toward TP1 ✓
        ↓
        DEFER EXIT - Create DeferredExit object
        ↓
        Monitor for: TP1 hit OR reversal (0.5% pullback)
```

**Bar 22:** Price hits TP1 at $45,500
```
        DeferredExit resolved by TP1
        ↓
        No need for exit condition exit
        ↓
        Position closed at TP1 ($45,500)
```

**Result:** Deferred exit allowed position to reach TP1 instead of early exit at $45,300

---

### Example 3: FLEXIBLE Mode - Reversal Trigger

**Setup:**
- Strategy has `BEARISH_BREAKDOWN` (from `double_top` block) as exit condition at 40%
- Exit mode = FLEXIBLE, TP proximity = 2.0%, reversal trigger = 0.5%
- LONG position at $45,000
- TP1 at $45,500, current price $45,250

**Signal Reference:** `src/detectors/building_blocks/patterns/double_top.py`
```python
'BEARISH_BREAKDOWN': {'description': 'Neckline support broken. Enter shorts aggressively.'}
```

**Flow:**
```
Bar 25: BEARISH_BREAKDOWN signal fires (double top pattern completed)
        ↓
        Exit Mode = FLEXIBLE
        ↓
        Check TP proximity: 0.55% to TP1 (within threshold)
        ↓
        Price rising toward TP1 → DEFER
        ↓
        Create DeferredExit, track peak_price = $45,250
```

**Bar 27:** Price reverses to $45,020 (0.51% pullback from peak)
```
        Reversal threshold breached (0.51% > 0.5%)
        ↓
        Execute deferred exit at 40%
        ↓
        Position partially closed at $45,020
```

**Result:** Exit executed after reversal, protecting gains from double top breakdown

---

### Example 4: Exit Condition with RECHECK

**Setup:**
- Strategy has `PATTERN_FORMING` (from `double_top` block) as exit condition at 25%
- RECHECK enabled: bar_delay = 10, must_still_be_true = True
- LONG position at $45,000

**Signal Reference:** `src/detectors/building_blocks/patterns/double_top.py`
```python
'PATTERN_FORMING': {'description': 'Two equal highs detected. Bearish reversal pattern forming.'}
```

**Flow:**
```
Bar 30: PATTERN_FORMING signal fires (initial trigger)
        ↓
        RECHECK configured → Wait 10 bars
        ↓
        Start recheck countdown: bars_remaining = 10
```

**Bar 40:** Recheck validation
```
        10 bars have passed
        ↓
        Check PATTERN_FORMING still true? YES ✓
        ↓
        Recheck passed → Execute 25% exit
```

**Result:** Exit only executed after confirming double top pattern persisted for 10 bars

---

### Example 5: Multiple Exit Conditions (Different Binding Levels)

**Setup:**
- Strategy-level: `BEARISH` (simple signal from `hod` block) at 30%
- Block-level (hod block): `HOD_REJECTION` (granular signal) at 20%
- Signal-level (AT_HOD): `BELOW_HOD` (after testing resistance) at 15%

**Signal References:**
```python
# From hod.py - Dual Signal Architecture
'signal_simple': 'BEARISH'     # Simple mode
'signal_granular': 'HOD_REJECTION'  # Advanced mode
```

**Position:** LONG from `ABOVE_HOD` signal in hod block

**Flow:**
```
Bar 45: BELOW_HOD fires (signal-level - price fell below resistance)
        ↓
        Execute 15% exit (signal-specific)
        ↓
        Remaining: 85%

Bar 48: HOD_REJECTION fires (block-level - confirmed rejection)
        ↓
        Execute 20% exit (of REMAINING 85% = 17% of original)
        ↓
        Remaining: 68% of original

Bar 52: BEARISH fires (strategy-level - overall bearish bias)
        ↓
        Execute 30% exit (of REMAINING 68% = 20.4% of original)
        ↓
        Remaining: 47.6% of original → continues to TP/SL
```

**Result:** Cascading exits reduce exposure while allowing remaining position to track targets

---

### Example 6: Exit Condition Overridden by SL

**Setup:**
- Strategy has `AT_HOD` (from `hod` block) exit at 50% (FLEXIBLE mode)
- LONG position at $45,000
- SL at $44,500

**Signal Reference:** `src/detectors/building_blocks/price_levels/hod.py`
```python
'AT_HOD': {'description': 'Price testing yesterday\'s high. Key decision level.'}
```

**Flow:**
```
Bar 55: Price drops rapidly
        ↓
Bar 56: AT_HOD fires (price touched HOD then fell)
        ↓
        Check FLEXIBLE mode conditions
        ↓
        But price at $44,480 (below SL)
        ↓
        SL TAKES PRIORITY
        ↓
        Full position closed at SL ($44,500)
        ↓
        Exit condition exit NOT executed (position already closed)
```

**Result:** SL always takes priority over exit conditions

---

### Example 7: Nested RECHECK Chain on Exit

**Setup:**
- Exit condition: `BEARISH_BREAKDOWN` (from `double_top` block) at 35%
- RECHECK chain: [`HOD_REJECTION` (5 bars), `BELOW_HOD` (3 bars)]

**Signal References:**
```python
# From double_top.py
'BEARISH_BREAKDOWN': {'description': 'Neckline support broken'}

# From hod.py (used as RECHECK confirmation)
'HOD_REJECTION': {'description': 'Price rejected from yesterday\'s high'}
'BELOW_HOD': {'description': 'Price below yesterday\'s high'}
```

**Flow:**
```
Bar 60: BEARISH_BREAKDOWN fires (double top neckline broken)
        ↓
        Start RECHECK chain
        
Bar 65: Check HOD_REJECTION - TRUE ✓ (price also rejected HOD)
        ↓
        Continue to next recheck
        
Bar 68: Check BELOW_HOD - TRUE ✓ (price confirmed below HOD)
        ↓
        All rechecks passed
        ↓
        Execute 35% exit
```

**Result:** Multi-stage validation with REAL signals ensures high-confidence exit

---

### Example 8: Percentage Limits Per Binding Level

**Validation Rules:**
```
STRATEGY level: Total exit % cannot exceed 100%
BLOCK level: Each block's exits cannot exceed 100%
SIGNAL level: Each signal's exits cannot exceed 100%

Valid Example (using REAL signals from Building Blocks):
├── Strategy: BEARISH (30%) + BEARISH_BREAKDOWN (25%) = 55% ✓
├── hod block: HOD_REJECTION (40%) ✓
│   └── AT_HOD signal: BELOW_HOD exit (20%) ✓
│   └── ABOVE_HOD signal: HOD_REJECTION exit (15%) ✓
└── double_top block: BEARISH_BREAKDOWN (50%) ✓

Invalid Example (will fail validation):
├── Strategy: BEARISH (60%) + BEARISH_BREAKDOWN (50%) = 110% ❌ EXCEEDS 100%
```

**Available Exit Signals (from Registry):**
```
hod block:        HOD_REJECTION, AT_HOD, BELOW_HOD, ABOVE_HOD, BEARISH
double_top block: BEARISH_BREAKDOWN, PATTERN_FORMING, BEARISH
lod block:        LOD_REJECTION, AT_LOD, BELOW_LOD, ABOVE_LOD, BULLISH
```

---

## 📊 DEFINITION OF DONE

- [ ] All 102 tasks completed and verified (Tasks 1.8.1 - 1.8.102)
- [ ] All 10 phases completed in order
- [ ] Database migration applied successfully
- [ ] All 35 files modified/created
- [ ] All unit tests passing (Phase 9)
- [ ] All integration tests passing (Phase 9)
- [ ] UI components functional with centralized styles
- [ ] Zero hardcoded styles in component files
- [ ] Exit conditions visible in optimizer UI panels
- [ ] Exit conditions visible in Compare panel metrics
- [ ] AI recommendations support EXIT_CONDITION types
- [ ] BacktestWorker emits exit condition data
- [ ] Progress tracking shows exit condition counter
- [ ] Signal dependency resolver handles exit conditions
- [ ] Documentation updated

---

**Status**: 📋 Ready for Implementation  
**Start**: Phase 1, Task 1.8.1  
**Estimated Completion**: 9-10 days (10 phases)
