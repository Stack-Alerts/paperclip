# BTCAAAAA-25164 — Impact Gate: Bug regression tests failing for BTCAAAAA-668

**Status:** RESOLVED
**Verification date:** 2026-05-13
**Verified by:** AutomationEngineer

## Root cause

BTCAAAAA-25164 is an auto-generated blocking issue created by the Impact Gate worker (`src/impact_gate/worker.py:492-508`) when a fix issue attempted `in_review` promotion and had BTCAAAAA-668 in its blast-radius regression set. At that time, no regression bridge file existed at `tests/bug_regression/test_btcaaaaa_668_regression.py`, causing the Impact Gate to return MISSING for BTCAAAAA-668.

## Fix applied

Commit `eeaa683b` created the regression bridge file and wired it into CI:
- `tests/bug_regression/test_btcaaaaa_668_regression.py` re-exports 4 test classes (18 tests) from the canonical QA file `tests/strategy_builder/ui/test_btcaaaaa_668_trade_registry_and_signals_key.py`
- Test file listed in CI pipeline at `.github/workflows/test.yml:166`

## Verification results

### pytest (18/18 passed)
All 18 tests pass with no failures or errors.

### Impact Gate runner (PASS)
- Status: PASS
- Total tests: 18, Passed: 18, Failed: 0, Errors: 0
- Test count (18) exceeds minimum bar (10) ✓

### Source imports
- `src.strategy_builder.ui.backtest_config_panel.BacktestWorker` — importable, `inspect.getsource()` works
- `src.optimizer_v3.core.comprehensive_ai_request_builder.ComprehensiveAIRequestBuilder` — importable
- `src.optimizer_v3.core.trade_registry.TradeRegistry` — importable

### CI pipeline wiring
Test file present at `.github/workflows/test.yml:166` ✓
