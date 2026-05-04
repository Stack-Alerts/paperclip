# SPRINT 2.1.0: CONFIG DISCOVERY ENGINE
**Test Wiring → Permutation-Based Config Optimizer**

**Sprint**: 2.1.0
**Status**: 🔄 IN PROGRESS
**Duration**: TBD
**Dependencies**: Sprint 2.0.x (MultiCore Backtest Engine), Sprint 1.9.1 (Config Browser Enhancements)
**Priority**: MEDIUM - Core Feature (Test Wiring Upgrade)

---

## 🎯 OBJECTIVES

Transform the **"🔬 Test Wiring"** button from a passive connectivity check into a full **Config Discovery and Optimization Engine** that:

1. Runs permutations of config settings against the currently-open strategy
2. Grades each configuration by: profit, trade frequency, Sharpe ratio, win rate, and exit quality
3. Presents results in a ranked results window
4. Allows the user to select a config from the results and apply it to `BacktestConfigPanel`

**Feature Location**: `BacktestConfigPanel` → `_on_test_wiring_clicked()` (`src/strategy_builder/ui/backtest_config_panel.py:3018`)

**Key Limitation Being Fixed**: Current Test Wiring uses **trade count** as the sole metric, which cannot detect broken exit wiring (SL/TP parameters produce identical entry counts regardless of exit parameter changes). This sprint adds exit-level metrics and permutation-based scoring.

---

## ⚠️ SCOPE CLARIFICATION

**THIS SPRINT MODIFIES:**
- `BacktestConfigPanel` Test Wiring handler and supporting classes
- `BacktestWorker` / result objects (extend to emit per-trade exit data)
- New `ConfigPermutationEngine` class
- New `ConfigDiscoveryResultsDialog` UI widget

**THIS SPRINT DOES NOT MODIFY:**
- Strategy Browser Configuration Panel (handled in Sprint 1.9.1)
- NautilusTrader live execution path
- Main window or strategy builder configuration forms
- Existing 23-scenario CSV test-wiring output (must remain unaffected)

---

## ✅ TASK CHECKLIST (Complete in Phase Order — Check Off Before Moving to Next Phase)

### **Phase 0: Architecture Design (Architect)**

- [ ] **Task 2.1.0.0.1** — Define `ConfigDiscoveryResult` data model: per-run metrics (`total_pnl`, `trade_count`, `win_rate`, `sharpe`, `avg_bars_held`, `exit_type_distribution`, `config_snapshot`)
- [ ] **Task 2.1.0.0.2** — Design permutation strategy: extend `generate_pairwise_scenarios()` (from `tests/integration/test_scenarios.py`) as the base; define user-selectable parameter ranges
- [ ] **Task 2.1.0.0.3** — Decide bar-caching architecture: load bars once in memory, pass to all runs (reference: `docs/optimizer/MULTICORE_BACKTEST_ENGINE_DESIGN.md`)

### **Phase 1: Enhanced Metrics Collection (UIEngineer)**

- [ ] **Task 2.1.0.1.1** — Extend `BacktestWorker` / result objects to emit per-trade exit data: `exit_type`, `exit_price`, `pnl`, `bars_held` per trade
- [ ] **Task 2.1.0.1.2** — Implement `_generate_discovery_report()` to aggregate: `total_pnl`, `win_rate`, `sharpe`, `avg_pnl_per_trade`, `exit_type_distribution` per scenario
- [ ] **Task 2.1.0.1.3** — Implement bar caching: load bars once before the discovery loop, reuse across all scenario runs

### **Phase 2: Permutation Engine (UIEngineer)**

- [ ] **Task 2.1.0.2.1** — Build `ConfigPermutationEngine`: generates N scenario configs from parameter ranges (expanding on `generate_pairwise_scenarios()`)
- [ ] **Task 2.1.0.2.2** — Add user-configurable parameter ranges: which parameters to sweep, how many steps, and sensible defaults
- [ ] **Task 2.1.0.2.3** — Implement fast execution loop using multicore engine (as designed in `docs/optimizer/MULTICORE_BACKTEST_ENGINE_DESIGN.md`)

### **Phase 3: Results Window UI (UIEngineer)**

- [ ] **Task 2.1.0.3.1** — Design `ConfigDiscoveryResultsDialog`: tabular results ranked by metric (most profitable, most frequent, best Sharpe)
- [ ] **Task 2.1.0.3.2** — Implement sortable/filterable table: columns = config key params + all metrics
- [ ] **Task 2.1.0.3.3** — Implement "Apply Config" button: user selects a row → applies that config to `BacktestConfigPanel`
- [ ] **Task 2.1.0.3.4** — Add grading badges: gold/silver/bronze per ranking category
- [ ] **Task 2.1.0.3.5** — Preserve current config as a "baseline" row for comparison

### **Phase 4: Sprint File (DocWriter)**

- [x] **Task 2.1.0.4.1** — Create `docs/optimizer/sprints/SPRINT_2_1_0_CONFIG_DISCOVERY_ENGINE.md` in the repository ✅

### **Phase 5: Testing (QAEngineer)**

- [ ] **Task 2.1.0.5.1** — Unit tests for `ConfigPermutationEngine` (correct scenario generation, parameter sweeps)
- [ ] **Task 2.1.0.5.2** — Unit tests for `ConfigDiscoveryResult` aggregation (metrics calculation)
- [ ] **Task 2.1.0.5.3** — Integration tests for the full discovery flow (mock backtest worker, verify results window populates)
- [ ] **Task 2.1.0.5.4** — Regression tests confirming existing "🔬 Test Wiring" behavior (run 23 scenarios → CSV) is preserved or gracefully upgraded

**Total Tasks: 16** | **Phase 4 Status: ✅ COMPLETE**

---

## 📋 TASK BREAKDOWN

### **Phase 0: Architecture Design** (Architect)

#### Task 2.1.0.0.1: Define ConfigDiscoveryResult Data Model
- **Purpose**: Establish per-run result schema consumed by results window and ranking logic
- **Required Fields**:
  - `config_snapshot`: dict — the full parameter config for the run
  - `total_pnl`: float — net P&L across all trades
  - `trade_count`: int — total trade count
  - `win_rate`: float — fraction of winning trades (0–1)
  - `sharpe`: float — Sharpe ratio
  - `avg_bars_held`: float — average bars held per trade
  - `exit_type_distribution`: dict[str, int] — count per exit type (SL, TP, signal, etc.)
- **Output**: Architecture Decision Record / data class definition

#### Task 2.1.0.0.2: Design Permutation Strategy
- **Base**: `generate_pairwise_scenarios()` in `tests/integration/test_scenarios.py`
- **Extension**: Allow user-defined parameter ranges and step counts
- **Output**: Interface spec for `ConfigPermutationEngine`

#### Task 2.1.0.0.3: Bar-Caching Architecture Decision
- **Reference**: `docs/optimizer/MULTICORE_BACKTEST_ENGINE_DESIGN.md`
- **Decision needed**: Pre-load bars once → pass as shared reference to all runs
- **Memory constraint**: 90–365 days of 1-min bars ≈ 130k–700k rows; monitor peak RAM
- **Output**: Architecture decision documented in design doc

---

### **Phase 1: Enhanced Metrics Collection** (UIEngineer)

#### Task 2.1.0.1.1: Extend BacktestWorker for Per-Trade Exit Data
- **FILE**: `src/strategy_builder/ui/backtest_config_panel.py` (BacktestWorker class)
- **ADD**: Per-trade exit data emission: `exit_type`, `exit_price`, `pnl`, `bars_held`
- **CONSTRAINT**: Must not break existing Trades/Metrics panels — coordinate with UIEngineer

#### Task 2.1.0.1.2: Implement `_generate_discovery_report()`
- **AGGREGATIONS**: `total_pnl`, `win_rate`, `sharpe`, `avg_pnl_per_trade`, `exit_type_distribution` per scenario
- **RETURNS**: List of `ConfigDiscoveryResult` objects, one per scenario run

#### Task 2.1.0.1.3: Implement Bar Caching
- **PATTERN**: Load bars once before the permutation loop; pass cached reference to each run
- **ESTIMATED SAVINGS**: ~4.5 min per full run set (from design doc)

---

### **Phase 2: Permutation Engine** (UIEngineer)

#### Task 2.1.0.2.1: Build ConfigPermutationEngine
- **CLASS**: `ConfigPermutationEngine`
- **INPUT**: Base config + parameter range definitions
- **OUTPUT**: Iterator of `dict` scenario configs
- **BASE**: Extends `generate_pairwise_scenarios()` from `tests/integration/test_scenarios.py`

#### Task 2.1.0.2.2: User-Configurable Parameter Ranges
- **UI**: Parameter sweep configuration dialog (which params, step count, range bounds)
- **DEFAULTS**: Sensible defaults for common parameters (SL %, TP %, lookback bars)

#### Task 2.1.0.2.3: Fast Execution Loop
- **ENGINE**: Multicore engine from `docs/optimizer/MULTICORE_BACKTEST_ENGINE_DESIGN.md`
- **TARGET**: 3–5 s per scenario vs 30–60 s without multicore
- **PROJECTED TOTAL**: ~2 min for 20+ scenarios (down from ~17 min)

---

### **Phase 3: Results Window UI** (UIEngineer)

#### Task 2.1.0.3.1: Design ConfigDiscoveryResultsDialog
- **CLASS**: `ConfigDiscoveryResultsDialog`
- **RANKING VIEWS**: Most profitable | Most frequent trades | Best Sharpe
- **LAYOUT**: Tabular main view + sidebar summary

#### Task 2.1.0.3.2: Sortable/Filterable Results Table
- **COLUMNS**: Config key params (SL%, TP%, lookback, etc.) + all metrics
- **SORTING**: Click column header to sort ascending/descending
- **FILTER**: Minimum trade count / minimum win rate filters

#### Task 2.1.0.3.3: Apply Config Button
- **ACTION**: User selects a row → confirm dialog → applies config snapshot to `BacktestConfigPanel`
- **VALIDATION**: Verify config is valid before applying

#### Task 2.1.0.3.4: Grading Badges
- **GOLD**: #1 in each ranking category
- **SILVER**: #2 in each ranking category
- **BRONZE**: #3 in each ranking category
- **DISPLAY**: Badge icon in table row + summary panel

#### Task 2.1.0.3.5: Baseline Row
- **PRESERVE**: Current config is always shown as a highlighted "Baseline" row
- **PURPOSE**: User can compare discovered configs against their starting point

---

### **Phase 5: Testing** (QAEngineer)

#### Task 2.1.0.5.1: Unit Tests — ConfigPermutationEngine
- **FILE**: `tests/strategy_builder/test_config_permutation_engine.py`
- **CASES**: Correct scenario count, parameter sweeps, edge cases (single param, empty range)

#### Task 2.1.0.5.2: Unit Tests — ConfigDiscoveryResult Aggregation
- **FILE**: `tests/strategy_builder/test_config_discovery_result.py`
- **CASES**: Metrics calculations, exit_type_distribution grouping, edge cases (no trades)

#### Task 2.1.0.5.3: Integration Tests — Full Discovery Flow
- **FILE**: `tests/strategy_builder/test_config_discovery_flow.py`
- **APPROACH**: Mock BacktestWorker, verify results window populates from mock results

#### Task 2.1.0.5.4: Regression Tests — Existing Test Wiring
- **VERIFY**: 23-scenario run still produces CSV output unchanged
- **VERIFY**: "🔬 Test Wiring" button still visible and functional after changes

---

## ✅ ACCEPTANCE CRITERIA

- [ ] Config discovery runs N permutations of settings against the opened strategy
- [ ] Results window shows: most profitable, most frequent trades, best Sharpe, and full config per run
- [ ] User can select a config from results and apply it to the config panel
- [ ] No existing "🔬 Test Wiring" functionality is broken (CSV output preserved or gracefully upgraded)
- [ ] Sprint file created at `docs/optimizer/sprints/SPRINT_2_1_0_CONFIG_DISCOVERY_ENGINE.md` ✅
- [ ] Tests cover permutation engine, metrics aggregation, and results window

---

## 📚 KEY FILE REFERENCES

| File | Purpose |
|------|---------|
| `src/strategy_builder/ui/backtest_config_panel.py:2199` | Test Wiring button & handler entry point |
| `src/strategy_builder/ui/backtest_config_panel.py:3018` | `_on_test_wiring_clicked()` |
| `src/strategy_builder/ui/backtest_config_panel.py:3281` | `_generate_wiring_report()` |
| `tests/integration/test_scenarios.py` | 23 hard-coded scenarios + `generate_pairwise_scenarios()` |
| `tests/integration/test_wiring_enhanced.py` | Enhanced analysis placeholder with exit-metric notes |
| `docs/optimizer/MULTICORE_BACKTEST_ENGINE_DESIGN.md` | Bar caching + multicore engine design |

---

## 🔗 DEPENDENCIES

**Required (must be complete before full implementation):**
- `docs/optimizer/MULTICORE_BACKTEST_ENGINE_DESIGN.md` — design reference for bar caching and multicore execution
- `tests/integration/test_scenarios.py` — base scenario generator
- `tests/integration/test_wiring_enhanced.py` — exit-metric placeholder and analysis notes

**Related Sprints:**
- Sprint 2.0.x — MultiCore Backtest Engine (provides the fast execution backend)
- Sprint 1.9.1 — Configuration Browser Enhancements (separate component, not a hard dependency)

---

## 🏗️ DELEGATION

| Work | Agent |
|------|-------|
| Phase 0: Architecture (data model, bar caching decisions) | Architect |
| Phase 1–3: Implementation (metrics, engine, UI) | UIEngineer |
| Phase 4: Sprint file | DocWriter ✅ |
| Phase 5: Testing | QAEngineer |

---

## ⚠️ RISK REGISTER

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Bar caching memory usage | LOW | 90–365 days 1-min bars ≈ 130k–700k rows; acceptable; monitor |
| BacktestWorker schema extension breaks Trades/Metrics panels | MEDIUM | Coordinate with UIEngineer; keep existing result keys intact |
| No breaking changes to existing Test Wiring path | MEDIUM | Regression tests (Task 2.1.0.5.4) enforce baseline behavior |
| Multicore engine not available | LOW | Fallback to single-core with warning |

---

## 🚫 NOT IN SCOPE

- Changing the Strategy Browser Configuration Panel (Sprint 1.9.1)
- NautilusTrader live execution
- Automatic config application without user confirmation
- AI-driven recommendation ranking (future sprint)

---

## 🔄 ROLLBACK PLAN

- Test Wiring button behavior is gated by a feature flag or progressive enhancement
- New `ConfigPermutationEngine` and `ConfigDiscoveryResultsDialog` are additive classes — removing them does not affect existing code
- `BacktestWorker` schema extension is backward-compatible (new fields are optional)
- All new test files are standalone — no changes to existing test infrastructure

---

**Sprint Status**: 🔄 IN PROGRESS (Phase 4 complete — awaiting Phase 0 architecture)
**Next Step**: Architect to complete Phase 0 (Tasks 2.1.0.0.1–2.1.0.0.3), then UIEngineer picks up Phase 1
**Estimated Completion**: TBD (depends on Architect and UIEngineer scheduling)
**Priority**: MEDIUM — Core feature upgrade, not critical path
