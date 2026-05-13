## QA: PASS

- **Issue**: BTCAAAAA-25739 — QA: Signal-accuracy differential audit — verify investigation findings
- **Parent**: BTCAAAAA-24636 — Signal-accuracy differential audit
- **QA Engineer**: QAEngineer
- **Date**: 2026-05-13

### Acceptance Criteria

| Criterion | Status | Evidence |
|---|---|---|
| 1. Fix correct — OR blocks with AND signals are not falsely required | ✅ PASS | `check_required_signals` skips OR blocks (`confluence_calculator.py:194-198`). 7/7 BTCAAAAA-24644 tests pass. |
| 2. `require_all_and_signals` flag gates the strict all-AND check | ✅ PASS | Default `False` — `institutional_signal_evaluator.py:524-531`. Gate is strictly opt-in. |
| 3. Backward compatible — zero behavioral delta for existing strategies | ✅ PASS | 14/14 differential PnL audit tests pass. Default behavior = confluence-only gating (pre-ca8dba93). |
| 4. Regression tests added for OR-block AND-signal fix | ✅ PASS | `tests/bug_regression/test_btcaaaaa_24644_fix.py` — 7 tests covering all scenarios |
| 5. Pre-existing BTCAAAAA-7364 AND enforcement preserved | ✅ PASS | `tests/bug_regression/test_btcaaaaa_7364_regression.py` — 10/10 pass |

### Test Results

| Suite | Tests | Passed | Failed |
|---|---|---|---|
| BTCAAAAA-24644 regression fix | 7 | 7 | 0 |
| BTCAAAAA-7364 AND enforcement | 10 | 10 | 0 |
| Differential PnL audit (BTCAAAAA-25474) | 14 | 14 | 0 |
| **Total** | **31** | **31** | **0** |

### Investigation Findings Verified

1. **Root cause** (`ca8dba93`): `check_required_signals` scanned ALL blocks (including OR blocks) for AND signals. When an OR block contained AND-level signal logic, those signals were falsely required — blocking entries that should have passed.
   - **Confirmed**: After ca8dba93, strategies with OR blocks containing AND-level signal logic would see false rejections → explains $1000+ → -$400 PnL regression.

2. **Fix** (`927c15ee`): Two-part fix
   - (a) `check_required_signals` now skips OR blocks — only AND signals in AND blocks are required
   - (b) `require_all_and_signals` gate (default `False`) avoids zero-trades vectors from timing/recheck chains

### Code Quality

- [x] No debugging `print()` statements left in code
- [x] No hardcoded API keys or credentials
- [x] Type hints present on all public functions (`check_required_signals`, `evaluate_bar`)
- [x] Logging is comprehensive (entry decisions logged)
- [x] Error handling present for all execution paths
- [x] No bare floats — NautilusTrader types used (`Price`, `Quantity`)
- [x] NautilusTrader enum values used consistently
- [x] Imports from `nautilus_trader` only — no custom re-implementations

### Pre-Deployment Checklist

Since this is a core-logic-only change (no UI, no trading config), the full pre-deployment checklist applies partially:

- [x] `pytest` — 31/31 relevant tests pass
- [x] Strategy class initializes correctly — `InstitutionalSignalEvaluator` init covered by integration tests
- [x] Edge cases tested: empty blocks, all-OR blocks, missing AND signals, mixed blocks
- [x] No debugging print statements
- [x] No hardcoded credentials
- [x] Type hints present
- [x] Risk parameters — not applicable (core logic change, not risk config change)
- [x] Backtest results — not applicable (logic change verified via unit + audit tests)

### Fact-Check

- `scripts/qa_fact_check_pipeline.py` does not exist — pipeline not yet deployed. Skipped.

### Sign-off

- **Status**: done
- **Sign-off**: ready for next stage — unblocks BTCAAAAA-24636 for CEO escalation
