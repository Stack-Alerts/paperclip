# BTCAAAAA-25176 — Impact Gate: Bug regression tests failing for BTCAAAAA-991

**Status:** RESOLVED
**Verification date:** 2026-05-13
**Verified by:** AutomationEngineer

## Root cause

BTCAAAAA-25176 is an auto-generated blocking issue created by the Impact Gate worker (`src/impact_gate/worker.py:543-563`) when a fix issue referencing BTCAAAAA-991 in its blast-radius regression set was scanned for gate compliance.

## Fix applied

Two commits already on `main` resolved this blocking issue:

| Commit | Description |
|---|---|
| `d636cbd8` | Expanded the regression test file from original to 26 test cases, exceeding the 10-test minimum bar |
| `09a9c7fa` | Created the dedicated regression test file at `tests/bug_regression/test_btcaaaaa_991_regression.py` |

The test file covers 6 test classes:

| Test class | Tests | Coverage area |
|---|---|---|
| `TestUtcTimestampConversion` | 7 | `datetime.fromtimestamp()` UTC vs CET correctness |
| `TestPriceAttributionInvariant` | 6 | Entry price must be within bar H/L range |
| `TestFloatPrecision` | 4 | `round(float, 2)` must produce clean 2-decimal values |
| `TestPriceAuditInstrumentation` | 3 | Price audit logging detects out-of-range prices |
| `TestEnterTradePriceWarning` | 3 | `enter_trade()` warns on price range violations |
| `TestBacktestEngineEntryTimestamp` | 3 | Stable and correct UTC timestamps across bars |

## Verification results

### pytest (26/26 passed)

All 26 tests pass with no failures or errors.

### Impact Gate runner (PASS)

- Status: PASS
- Total tests: 26, Passed: 26, Failed: 0, Errors: 0
- Test count (26) exceeds minimum bar (10) ✓

### CI pipeline wiring

Test file present at `.github/workflows/test.yml:92` ✓

### Source dependencies

- `src.optimizer_v3.core.multicore_backtest_engine` — UTC timestamp fix at line 241 (`datetime.fromtimestamp(ts / 1e9, tz=timezone.utc).replace(tzinfo=None)`)
- `src.optimizer_v3.core.institutional_signal_evaluator` — price range warning (P1.1 instrumentation) at line 780
- `src.optimizer_v3.core.institutional_signal_evaluator.InstitutionalSignalEvaluator.enter_trade()` — entry price attribution

## Conclusion

The BTCAAAAA-991 bug regression test suite is complete, all 26 tests pass, and the minimum 10-test bar is exceeded (26 tests). The Impact Gate blocking issue BTCAAAAA-25176 is resolved.
