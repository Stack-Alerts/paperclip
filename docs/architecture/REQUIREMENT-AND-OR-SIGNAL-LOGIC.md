# Technical Requirement: AND/OR Signal Logic with Order & Dependency Enforcement

**Author:** StrategyResearcher (e3fcab65)
**Date:** 2026-05-13
**Issue:** BTCAAAAA-24644
**Status:** Approved by CEO (73e7ef43) — 2026-05-13
**Supersedes:** docs/strategy-builder/06_AND_OR_LOGIC_SYSTEM.md (v1.0 — incomplete)

---

## 1. Problem Summary

`check_required_signals()` currently only checks **presence** of AND signals — it does not verify that AND signals fired in the correct **order** or that they respected their **dependency chains** (timing constraints, rechecks, parent references). This creates two failure modes:

1. **Too permissive:** Signals that fire out-of-order (e.g., BEARISH_DIVERGENCE before HOD_REJECTION) pass the presence gate.
2. **Too strict:** When `require_all_and_signals=True`, the gate requires ALL AND signals across ALL blocks, ignoring block-level logic (OR blocks should not be checked). The previous heartbeat fixed this but did not address order/dependency.

---

## 2. Design: Layered AND/OR Enforcement

The logic system has **three enforcement layers** that compose together:

```
Layer 1: Signal Evaluation (individual bar)
├── Building block fires signals
├── TimingChainManager validates timing constraints
├── RecheckValidator validates recheck chains
└── Output: all_signals (filtered set that passed timing + recheck)

Layer 2: Block-Level Gate (entry decision)
├── AND blocks: require ALL AND-logic signals to fire
│   └── Enforce block order: signals must fire in block sequence
├── OR blocks: skip (never required)
└── Output: required_ok (boolean)

Layer 3: Confluence Threshold (entry decision)
├── Weighted sum of all fired signals
├── Compare to config.confluence_threshold (default 40)
└── Output: should_enter = required_ok AND confluence >= threshold
```

---

## 3. Signal Order Enforcement Rules

### 3.1 Block Sequence Order

Blocks are evaluated in configuration order. Signals from block[N] must fire before or concurrently with signals from block[N+1].

| Strategy JSON order | Semantic meaning |
|---|---|
| hod (AND) → stochastic_rsi (AND) → rsi_divergence (AND) → order_block (OR) | HOD_REJECTION must fire first, BEARISH_CROSS second, BEARISH_DIVERGENCE third. OR block is order-independent. |

**Rule:** For AND blocks, the `fired_signals` sequence must contain signals from block[N] before block[N+1]. If a later-block signal fires before an earlier-block AND signal, the order is violated.

### 3.2 Signal Sequence Within Block

Signals within a block are also ordered. AND-logic signals in position[i] must fire before AND-logic signals in position[i+1] within the same block.

**Example (rsi_divergence block):**
```
Position 0: BEARISH_DIVERGENCE (AND) → must fire first
Position 1: OVERBOUGHT (OR) → optional, no order enforcement
```

### 3.3 Timing Constraint Enforcement (Existing)

Already handled by `TimingChainManager`. A signal with `timing_constraint.reference` must fire within `max_candles` of the reference signal's fire bar. This is a **hard gate** — signals failing timing are excluded from `all_signals`.

### 3.4 Recheck Chain Enforcement (Existing)

Already handled by `RecheckValidator`. Signals with `recheck_config` or `recheck_chain` must complete all recheck confirmations before they are added to `confirmed_signals`.

---

## 4. Dependency Chain Validation

### 4.1 Signal Dependency Graph

Each AND signal in an AND block may have:
- **Timing dependency:** references another signal (same or different block)
- **Recheck dependency:** must be validated N bars later
- **Parent dependency:** if in a recheck chain, depends on the parent signal

**Validation at entry:**
1. Every AND signal in an AND block must be present in `all_signals`
2. Every AND signal must be present in the correct block/signal position sequence
3. Timing constraints must be satisfied (enforced by TimingChainManager)
4. Recheck chains must be complete (enforced by RecheckValidator)

### 4.2 Cascade Reset Rule

When an AND block's timing constraint fails, the **entire signal chain** must reset:
1. Clear `fired_signals` state for all blocks
2. Queue a cascade reset event
3. Log the reset reason
4. Wait for the first signal in block[0] to re-fire

**Exception:** OR block failures never trigger cascade resets.

---

## 5. Config Flags

| Flag | Type | Default | Description |
|---|---|---|---|
| `require_all_and_signals` | bool | `False` | When True, enforces AND-block signal presence. When False, entry is purely confluence-based. |
| `enforce_signal_order` | bool | `False` | When True, enforces block/signal order for AND-signals. Only valid when `require_all_and_signals=True`. |
| `cascade_reset_on_timing_failure` | bool | `True` | When True, failed timing on AND block triggers full signal reset. |

---

## 6. Implementation Plan

### Phase 1 (Current heartbeat — DONE)
- [x] R5: `require_all_and_signals` flag with default `False`
- [x] Block-level awareness in `check_required_signals` (skip OR blocks)

### Phase 2 (Next heartbeat)
- [ ] Add `enforce_signal_order` flag + order checker
- [ ] Create `_build_dependency_order()` method that builds signal sequence from config
- [ ] Create `_verify_signal_order(fired_signals, config) → bool` method
- [ ] Integrate order check into entry gate (after presence check, before confluence)

### Phase 3 (Next sprint)
- [ ] Implement cascade reset on AND-block timing failure
- [ ] Add `cascade_reset_on_timing_failure` flag
- [ ] Wire cascade reset into TimingChainManager callback
- [ ] Update nautilus_code_generator `_should_reset_strategy()` to use cascade logic
- [ ] Add SignalTelemetry counters: `order_violations`, `cascade_resets`

---

## 7. Examples

### Example A: HOD Rejection — Correct Order

```
Config blocks:
  1. hod (AND): HOD_REJECTION (AND) [bar_delay=25 recheck]
  2. stochastic_rsi (AND): BEARISH_CROSS (AND)
  3. rsi_divergence (AND): BEARISH_DIVERGENCE (AND) [recheck_chain]
  4. order_block (OR): BEARISH_OB (OR)

all_signals at entry (correct order, timing OK, rechecks complete):
  ['hod::HOD_REJECTION', 'stochastic_rsi::BEARISH_CROSS', 
   'rsi_divergence::BEARISH_DIVERGENCE', 'order_block::BEARISH_OB']

check_required_signals → True (all AND-block AND signals present, order OK)
confluence >= threshold → True (e.g. 70 >= 40)
Result: ENTER
```

### Example B: HOD Rejection — Out of Order

```
all_signals at entry (incorrect order):
  ['stochastic_rsi::BEARISH_CROSS', 'hod::HOD_REJECTION', 
   'rsi_divergence::BEARISH_DIVERGENCE']

With enforce_signal_order=True:
  check_order → False (BEARISH_CROSS fired before HOD_REJECTION)
  required_ok → False
Result: BLOCKED (order violation)
```

### Example C: HOD Rejection — Missing AND signal with timing failure

```
all_signals at entry (BEARISH_DIVERGENCE failed recheck):
  ['hod::HOD_REJECTION', 'stochastic_rsi::BEARISH_CROSS']

With require_all_and_signals=True:
  check_required_signals → False (rsi_divergence::BEARISH_DIVERGENCE missing)
  required_ok → False
Result: BLOCKED (missing AND signal)

With require_all_and_signals=False (default):
  required_ok → True (confluence-only)
  confluence = 25 + 20 = 45 >= 40 → True
Result: ENTER
```

---

## 8. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Order enforcement blocks legitimate entries where signals fire near-simultaneously | False rejections | Default `enforce_signal_order=False`. Only opt-in for strict strategies. |
| Cascade reset creates infinite loops if signals never fire in sequence | Zero trades | Add max reset counter (default 3 resets/run). After 3 resets, auto-disable cascade. |
| Order enforcement adds latency to bar-by-bar evaluation | Performance | Order check is O(N) where N = AND signal count (typically <10). Negligible. |

---

## 9. Verification Checklist

- [ ] `require_all_and_signals` flag exists, defaults `False`
- [ ] `check_required_signals` skips OR blocks
- [ ] `enforce_signal_order` flag exists, defaults `False`
- [ ] Order verification compares signal fire sequence against config block/signal order
- [ ] Cascade reset clears all signal state on AND-block timing failure
- [ ] Cascade reset has max reset counter
- [ ] SignalTelemetry tracks order violations and cascade resets
- [ ] All unit tests pass
- [ ] QAEngineer live X11 verification (BTCAAAAA-1478)

---

## 10. Related Documents

- `docs/strategy-builder/06_AND_OR_LOGIC_SYSTEM.md` (v1.0 — superseded by this doc)
- `docs/strategy-builder/05_SIGNAL_CONFIGURATION.md` (signal config with timing constraints)
- `docs/architecture/adr/ADR-0001-zero-trades-regression-audit.md` (zero-trades analysis)
- `src/optimizer_v3/core/confluence_calculator.py` (check_required_signals implementation)
- `src/optimizer_v3/core/institutional_signal_evaluator.py` (entry gate)
- `src/strategy_builder/core/nautilus_code_generator.py` (generated strategy code)
