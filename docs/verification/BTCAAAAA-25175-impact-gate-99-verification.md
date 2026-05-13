# BTCAAAAA-25175 — Impact Gate: Bug regression tests failing for BTCAAAAA-99

**Status:** RESOLVED
**Verification date:** 2026-05-13
**Verified by:** AutomationEngineer

## Root cause

BTCAAAAA-25175 is an auto-generated blocking issue created by the Impact Gate worker () when a fix issue referencing BTCAAAAA-99 in its blast-radius regression set was scanned for gate compliance. The initial scan at  found the existing regression test file had only 1 test (below the 10-test minimum bar), causing a FAIL status.

## Fix applied

Commit  expanded the regression test file from 1 smoke test to 29 test cases:

-  — 29 test cases across 5 test classes

| Test class | Tests | Coverage area |
|---|---|---|
| TestCalculate | 10 | ConfluenceCalculator.calculate() scoring |
| TestCheckRequiredSignals | 7 | AND-gating, OR-block skipping, edge cases |
| TestGetSignalBreakdown | 4 | Signal breakdown dict, bonus, empty state |
| TestSignalExistsInConfig | 4 | Entry/exit signal lookup |
| TestEvaluateBarEntryDecision | 4 | Entry threshold, AND-gate blocking |

## Verification results

### pytest (29/29 passed)

All 29 tests pass with no failures or errors.

### Test count

- Total tests: 29 (exceeds minimum 10-test bar)
- Passed: 29, Failed: 0, Errors: 0

### CI pipeline wiring

Test file present at .github/workflows/test.yml:93

## Conclusion

The BTCAAAAA-99 bug regression test suite is complete. All 29 tests pass, and the minimum 10-test bar is exceeded (29 tests). The fix commit 1e41916a has been pushed to origin/main. The Impact Gate blocking issue BTCAAAAA-25175 is resolved.
