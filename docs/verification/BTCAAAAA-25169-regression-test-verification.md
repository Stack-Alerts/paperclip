# BTCAAAAA-25169 — Impact Gate: Bug regression tests failing for BTCAAAAA-795

**Status:** RESOLVED
**Verification date:** 2026-05-13
**Verified by:** AutomationEngineer

## Root cause

BTCAAAAA-25169 is an auto-generated blocking issue created by the Impact Gate worker (`src/impact_gate/worker.py:492-508`) when a fix issue attempted `in_review` promotion and had BTCAAAAA-795 in its blast-radius regression set. At that time, no dedicated regression test file existed at `tests/bug_regression/test_btcaaaaa_795_regression.py` (regression tests were in `tests/unit/test_data_manager_integrity.py` only), causing the Impact Gate to return MISSING for BTCAAAAA-795.

## Fix applied

Commit `8498e8aa` created the dedicated regression test file (139 lines, 13 test cases):

- `tests/bug_regression/test_btcaaaaa_795_regression.py` — comprehensive coverage of `_determine_source()` tz-awareness fix

Test class implemented:

| Test class | Tests | Coverage area |
|---|---|---|
| `TestDetermineSourceTzAwareness` | 13 | UTC-aware, naive, and mixed tz inputs; Binance/LakeAPI/AUTO routing; null dates; equal dates; hybrid range |

Commit `3e9b7a72` wired the test file into the CI pipeline at `.github/workflows/test.yml:105`.

## Verification results

### pytest (13/13 passed)

All 13 tests pass with no failures or errors.

### Impact Gate runner (PASS)

- Status: PASS
- Total tests: 13, Passed: 13, Failed: 0, Errors: 0
- Test count (13) exceeds minimum bar (10) ✓

### CI pipeline wiring

Test file present at `.github/workflows/test.yml:105` ✓

### Source dependencies

- `src.data_manager.unified_manager.UnifiedDataManager._determine_source()` — method exists and is functional
- `src.data_manager.unified_manager.DataSource` — enum with `BINANCE`, `LAKEAPI`, `AUTO` members

## Conclusion

The BTCAAAAA-795 bug regression test suite is complete, all 13 tests pass, and the minimum 10-test bar is exceeded (13 tests). The Impact Gate blocking issue BTCAAAAA-25169 is resolved.
