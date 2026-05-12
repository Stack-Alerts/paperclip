# ADR-0001: Zero-Trades Regression — Module-Wide Audit & Architectural Fix

**Issue:** BTCAAAAA-1477  
**Author:** Architect (73eaab54)  
**Status:** In Review  
**Date:** 2026-05-12  
**Priority:** CRITICAL  
**Parent:** BTCAAAAA-1476 — Board reports BOTH Mode 1 & Mode 2 = 0 trades

---

## Context

Zero-trades has recurred at least 6 times in 72 hours (2026-05-09 through 2026-05-11). Each prior fix was piecemeal — addressing a single proximate cause without hardening the architecture against the failure class. The board attached to BTCAAAAA-1476 shows BOTH Mode 1 and Mode 2 producing zero trades at 18:25 UTC on 2026-05-11, ~10 hours after QA signoff (BTCAAAAA-1205).

Per CEO policy: after two piecemeal fixes for the same bug class fail, the next fix must be a module-wide audit with structural hardening.

## Decision: Module-Wide Structural Hardening

We will implement architectural defenses at 3 layers to prevent any single-point failure from causing zero trades:

1. **Observability Layer** — Signal-to-trade telemetry so the failure class is detectable before board escalation
2. **Defense-in-Depth Entry Gate** — Redundant trade-entry paths so no single code path can silently suppress all trades
3. **State Isolation** — Eliminate global mutable state that creates cross-run contamination

---

## Architecture Analysis

### Trade Execution Pipeline (Current)

```
┌──────────┐    ┌──────────────┐    ┌───────────────────┐    ┌──────────────┐
│   Data   │───▶│    Signal     │───▶│  Confluence +     │───▶│    Trade     │
│ Provider │    │  Evaluator    │    │  Required Signals │    │  Registry    │
│(Mode1/2) │    │ (Building     │    │  → Entry Decision │    │  (Singleton) │
└──────────┘    │  Blocks)      │    └───────────────────┘    └──────────────┘
                └──────────────┘
```

### Single Points of Failure (SPOF) Identified

#### SPOF-1: Building Block Instantiation (`BlockRegistry.instantiate`)
- **Location:** `src/optimizer_v3/core/institutional_signal_evaluator.py:257`
- **Failure mode:** Returns `None` silently → all building blocks skipped → 0 signals → 0 trades
- **Prior fix:** `38a48d5c`, `51474f6b` — added TypeError catch but did not prevent the 0-trades outcome
- **Root cause:** No fallback — if ANY building block fails to instantiate, signals from that block are lost. If ALL blocks fail, zero trades.
- **Detection:** Logger warning, no metric, no alert

#### SPOF-2: Trade Registry Contamination
- **Location:** `src/optimizer_v3/core/trade_registry.py:388` (global singleton)
- **Failure mode:** Registry not cleared between runs → all new trades rejected as duplicates → 0 visible trades
- **Prior fix:** `42834cff` — added `registry.clear()` in `merge_chunk_results()`
- **Root cause:** Global mutable state; `clear()` is not called in the constructor or `run_backtest()` entry point — it's in `merge_chunk_results()` which is called deep in the call chain
- **Risk:** Any code path that calls `get_all_trades()` or `get_trade_registry()` from another place (test, debug, UI refresh) reads stale state

#### SPOF-3: Required Signals Gate (BTCAAAAA-7364)
- **Location:** `src/optimizer_v3/core/institutional_signal_evaluator.py:516-522`
- **Failure mode:** `check_required_signals()` rejects entry when any AND-logic signal is absent, regardless of confluence score
- **Prior fix:** `6c963810` — **introduced** this check as a fix, but it created a new zero-trades vector
- **Scenario for 0 trades:** Strategy has 3 AND signals with timing constraints. If timing chain doesn't validate (rechecks fail, wrong bar window, missing reference signal), all 3 AND signals are filtered out. Confluence never reaches threshold. → 0 trades.
- **Detection:** Only visible in detailed debug logs, not in metrics or UI

#### SPOF-4: Confluence Threshold Unreachable
- **Location:** `src/optimizer_v3/core/institutional_signal_evaluator.py:478`
- **Failure mode:** `confluence_threshold` set higher than any achievable confluence score → 0 trades
- **Prior fix:** `d9d79b53` (BTCAAAAA-732) — detect unreachable threshold
- **Root cause:** Threshold is user-configurable in UI; no validation that any configured signal combination can reach it

#### SPOF-5: Warm-up Period (50 bars)
- **Location:** `src/optimizer_v3/core/institutional_signal_evaluator.py:589`
- **Failure mode:** First 50 bars produce 0 signals (warm-up). If backtest covers a short date range (e.g., 1 day = 96 bars), only 46 bars are actually trading. Combined with other filters, this can result in 0 trades.
- **Impact:** Amplifies during Mode 1 quick backtests where users test small date ranges

#### SPOF-6: Signal Name Mismatch
- **Location:** `src/optimizer_v3/core/institutional_signal_evaluator.py:619`
- **Failure mode:** Building block fires a signal but the signal name doesn't match the strategy config → filtered out → no trade
- **Detection:** Logged only via BTCAAAAA-736 diagnostics at the last bar; not surfaced in UI

### Mode 1 vs Mode 2 Divergence Points

| Aspect | Mode 1 (Historical) | Mode 2 (Live Replay) |
|---|---|---|
| Data source | `BacktestDataProvider.load_bars_for_backtest()` | Same provider, different time params |
| Cache key | `{timeframe}_{start_date}_{end_date}` | Same cache system |
| Signal evaluation | Identical `InstitutionalSignalEvaluator` | Same evaluator |
| Trade registry | Same global singleton | Same global singleton |

**Finding:** The core pipeline is identical for both modes. When zero-trades occurs, it affects BOTH modes simultaneously because they share the same signal evaluator, trade registry, and building block instantiation. This confirms the board observation.

---

## Recommendations

### Immediate (This Heartbeat) — Hardening

#### R1: Add Signal Health Telemetry
Add a `SignalTelemetry` dataclass that tracks per-backtest:
- `signals_fired_total`: Total non-neutral signals from building blocks
- `signals_accepted`: Signals passing name filter
- `signals_filtered`: Signals rejected by name filter
- `and_signals_required`: Count of AND-logic signals in config
- `and_signals_missing`: AND signals that never fired
- `confluence_checks_total`: Number of bars where confluence was calculated
- `confluence_entries_possible`: Bars where confluence >= threshold but required signals failed
- `trade_entries_blocked_by_required`: Count of would-be entries rejected by `check_required_signals`

This data must be surfaced in the Backtest Results UI and logged at `WARNING` level when zero trades are detected.

#### R2: Add Canary Trade Test Hook
Add a `_canary_check()` method to `InstitutionalSignalEvaluator` that, when `total_bars` is the last bar:
- If `total_trades == 0` AND `signals_fired_total > 0`:
  - Log CRITICAL: "CANARY: 0 trades despite {N} signals — check required-signals gate, confluence threshold, or timing chains"
- If `total_trades == 0` AND `signals_fired_total == 0`:
  - Log CRITICAL: "CANARY: 0 signals across all bars — check building block instantiation, data loading, or strategy config"

#### R3: Add Config Validation at Backtest Start
Before entering the signal evaluation loop, validate:
1. A strategy config exists and has blocks with signals
2. At least one entry signal has `logic='OR'` (pure-AND strategies with zero-trades risk should warn)
3. `confluence_threshold` is achievable (at least one signal combination sums to >= threshold)
4. Data has been loaded (len(bars) > 0)
5. Building blocks instantiated successfully (len(self.building_blocks) > 0)

### Short-Term (Next 1-2 Heartbeats) — Structural Fixes

#### R4: Trade Registry → Local Scope
Remove the global singleton pattern. Pass `TradeRegistry` as a constructor parameter or create it in `run_backtest()` and pass through the call chain. The registry should never outlive a single backtest run.

Replacement pattern:
```python
def run_backtest(self, ...):
    registry = TradeRegistry()  # fresh per-run, no global state
    # ...
    chunk_results = evaluate_chunks(...)
    merged = merge_chunk_results(chunk_results, registry=registry)  # explicit
```

#### R5: Required Signals Gate → Configurable
Add a strategy config flag `require_all_and_signals: bool` defaulting to `False`. This makes the BTCAAAAA-7364 change opt-in rather than a hard gate. The old behavior (confluence-only gating) remains available.

Current (hard-wired):
```python
should_enter = required_ok and confluence >= min_confluence
```

Proposed (configurable):
```python
require_all = getattr(self.strategy_config, 'require_all_and_signals', False)
required_ok = self.confluence_calc.check_required_signals(...) if require_all else True
should_enter = required_ok and confluence >= min_confluence
```

#### R6: Building Block Graceful Degradation
If `BlockRegistry.instantiate()` returns `None` for a block, log CRITICAL and continue with remaining blocks. Never silently skip all blocks. At end-of-backtest, if 0 of N blocks instantiated, raise a descriptive error visible in UI.

#### R7: Exit Gate Validation
Validate that exit conditions reference signals that exist in the strategy config. Missing exit signal references cause silent failures in `_get_required_exit_signals()`.

### Long-Term (Next Sprint) — Resilience

#### R8: Automated Canary Regression Test
Create a CI test that:
1. Loads a known-good strategy config
2. Loads a small date range of real BTC data
3. Runs a backtest
4. Asserts `total_trades > 0`
5. Runs nightly via GitHub Actions

This catches zero-trades regressions before they reach a human.

#### R9: Circuit Breaker on Zero-Signal Runs
If a strategy produces 0 accepted signals across all N bars, auto-escalate to CRITICAL log level. If 0 trades across 3+ consecutive runs with different date ranges, auto-suspend backtesting for that strategy config and surface a dialog.

---

## Architecture Decision Diagram

### Current Architecture (Fragile)

```
                    ┌──────────────────────────────┐
                    │    Entry Gate (current)       │
                    │  should_enter = required_ok   │
                    │  AND confluence >= threshold  │
                    └──────────┬───────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                 ▼
    ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐
    │ SPOF-1:     │  │ SPOF-5:      │  │ SPOF-3:          │
    │ No blocks   │  │ 50-bar warm- │  │ AND signals      │
    │ instantiated│  │ up kills     │  │ never fire       │
    │             │  │ short runs   │  │                  │
    └─────────────┘  └──────────────┘  └──────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  RESULT: 0 Trades    │
                    │  No telemetry, no    │
                    │  alert, silent       │
                    └──────────────────────┘
```

### Proposed Architecture (Hardened)

```
                    ┌──────────────────────────────┐
                    │    Entry Gate (hardened)      │
                    │  R3: Pre-flight validation    │
                    │  R5: Configurable required    │
                    │  R6: Graceful degradation     │
                    └──────────┬───────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                 ▼
    ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐
    │ R1: Signal  │  │ R2: Canary   │  │ R4: Scoped       │
    │ Telemetry   │  │ Trade Check  │  │ Trade Registry   │
    │ → UI/metrics│  │ → CRITICAL   │  │ → No cross-run   │
    │             │  │ log on 0     │  │ contamination    │
    └─────────────┘  └──────────────┘  └──────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  RESULT: Trades OR   │
                    │  actionable error    │
                    │  with root cause     │
                    └──────────────────────┘
```

---

## Trade-Offs

| Approach | Pros | Cons |
|---|---|---|
| **R5: Make AND-gate configurable** | Preserves backward compat; user chooses strategy strictness | Two code paths to maintain; AND-gate can still cause 0 trades if enabled |
| **R4: Scoped registry** | Eliminates entire failure class; simpler reasoning | Breaking API change; all callers must be updated |
| **R8: Automated canary test** | Catches regressions before humans; CI-enforceable | Requires test data that reliably produces trades; CI runtime cost |

**Decision:** Implement R1-R7 in the current heartbeat (observability + config hardening). R8-R9 deferred to next sprint as they require test infrastructure investment.

---

## Connected Issues

| Issue | Relationship |
|---|---|
| BTCAAAAA-1476 | Parent — Board observed 0 trades both modes |
| BTCAAAAA-1478 | Child — QAEngineer live X11 verification |
| BTCAAAAA-2173 | Child — BacktestAnalyst EXPERT_MODE 5-report |
| BTCAAAAA-736 | Predecessor — Signal diagnostics |
| BTCAAAAA-7364 | Predecessor — `check_required_signals` wiring |
| BTCAAAAA-693 | Predecessor — TradeRegistry clear fix |
| BTCAAAAA-732 | Predecessor — Unreachable confluence threshold |
| BTCAAAAA-20264 | Predecessor — Expert mode core validation |

---

## Verification Checklist

- [ ] R1: SignalTelemetry surfaced in backtest results UI
- [ ] R2: Canary check logs CRITICAL on zero-signal / zero-trade runs
- [ ] R3: Pre-flight validation catches empty config, no-data, unreachable threshold
- [ ] R4: TradeRegistry scoped to single run (no global singleton)
- [ ] R5: `require_all_and_signals` config flag with default `False`
- [ ] R6: Graceful degradation when BlockRegistry.instantiate fails
- [ ] R7: Exit signal reference validation at backtest start
- [ ] All unit tests pass
- [ ] QAEngineer live X11 verification passes (BTCAAAAA-1478)
- [ ] BacktestAnalyst EXPERT_MODE re-assessment complete (BTCAAAAA-2173)

---

## DoD

- [x] Architecture analysis complete
- [x] All SPOFs documented with locations and failure modes
- [x] Mode 1 / Mode 2 divergence analyzed
- [x] Recommendations prioritized and assigned
- [ ] Implementation of R1-R7 (delegated to NautilusEngineer via child issues)
- [ ] QA verification
- [ ] Push to origin
