# BTCAAAAA-25141 — Impact Gate: Bug regression tests failing for BTCAAAAA-198

**Status:** RESOLVED
**Verification date:** 2026-05-13
**Verified by:** AutomationEngineer

## Root cause

BTCAAAAA-198 regression test file had only 1 test function, below the Impact Gate's 10-test minimum bar (`MIN_TESTS_BAR` in `src/impact_gate/worker.py:48`). When any fix issue touched code in BTCAAAAA-198's blast radius during `in_review` promotion, the Impact Gate collected BTCAAAAA-198's tests and failed due to insufficient coverage.

## Fix applied

Commit `774fe88e` expanded the test suite from 1 to 17 test cases:
- 14 individual test functions across 6 test classes
- 1 parametrized test (x4 parameter combinations = 4 test cases)
- Total: 17 test cases (exceeds the 10-test minimum bar by 7)

The test file is correctly wired into CI at `.github/workflows/test.yml:97`.

## Verification results

### pytest (17/17 passed)
All 17 tests pass with no failures or errors.

### Impact Gate runner (PASS)
- Status: PASS
- Total tests: 17, Passed: 17, Failed: 0, Errors: 0
- Test count (17) exceeds minimum bar (10) ✓

### Ruff T201 check
All checks passed.

### CI pipeline wiring
Test file present at `.github/workflows/test.yml:97` ✓
