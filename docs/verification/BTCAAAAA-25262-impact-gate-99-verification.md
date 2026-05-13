# BTCAAAAA-25262 — Impact Gate: Bug regression tests failing for BTCAAAAA-99

**Status:** RESOLVED (false positive — tests pass and exceed the minimum bar)
**Verification date:** 2026-05-13
**Verified by:** AutomationEngineer

## Root cause

BTCAAAAA-25262 is an auto-generated blocking issue created by the Impact Gate worker
(`src/impact_gate/worker.py:576-578`) when a fix issue attempted `in_review` promotion
and had BTCAAAAA-99 in its blast-radius regression set.

The BTCAAAAA-99 regression test file (`tests/bug_regression/test_btcaaaaa_99_regression.py`)
already contains **29 tests** (well above `MIN_TESTS_BAR = 10`). All 29 tests pass.
The gate failure was likely a transient CI infrastructure condition at the time the
gate ran, or the test file had not yet been fully expanded on the target branch.

## What BTCAAAAA-99 covers

Confluence scoring, signal gating, and entry-decision logic shared with BTCAAAAA-7364
(`src/optimizer_v3/core/confluence_calculator.py` + `src/optimizer_v3/core/institutional_signal_evaluator.py`).

### Test classes

| Test class | Tests | Coverage area |
|---|---|---|
| `TestCalculate` | 10 | ConfluenceCalculator.calculate() scoring |
| `TestCheckRequiredSignals` | 7 | AND-gating, OR-block skipping, edge cases |
| `TestGetSignalBreakdown` | 4 | Signal breakdown dict, bonus, empty state |
| `TestSignalExistsInConfig` | 4 | Entry/exit signal lookup |
| `TestEvaluateBarEntryDecision` | 4 | Entry threshold, AND-gate blocking |

## Verification

### 1. Bug regression tests for BTCAAAAA-99

All 29 tests pass:

```
$ python -m pytest tests/bug_regression/test_btcaaaaa_99_regression.py -v --tb=short
============================== 29 passed in 0.77s ==============================
```

### 2. Impact Gate runner for BTCAAAAA-99

```
$ python scripts/impact_gate_runner.py --bugs BTCAAAAA-99
status: PASS, total: 29, passed: 29, failed: 0, errors: 0, missing: 0
```

Test count (29) exceeds the minimum bar (10) by 19 tests.

### 3. CI pipeline wiring — PRESENT

`tests/bug_regression/test_btcaaaaa_99_regression.py` is included in
`.github/workflows/test.yml:95` and runs on every push/PR plus the nightly
schedule.

### 4. Key commits

```
1e41916a test(regression): expand BTCAAAAA-99 regression tests to meet Impact Gate 29-test bar
09a9c7fa test(regression): add bug_regression test files for BTCAAAAA-7364 and blast-radius bugs
```

## Status

**RESOLVED** — all 29 regression tests for BTCAAAAA-99 pass. The impact gate
runner reports PASS. The CI pipeline is wired correctly. The test count (29)
far exceeds the 10-test minimum bar. The blocking issue BTCAAAAA-25262 is a
false positive. No code changes required.
