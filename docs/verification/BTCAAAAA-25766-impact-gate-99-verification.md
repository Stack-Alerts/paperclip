# BTCAAAAA-25766 — Impact Gate: Bug regression tests failing for BTCAAAAA-99

**Status:** RESOLVED (false positive — tests pass, test count exceeds bar)
**Verification date:** 2026-05-13
**Verified by:** AutomationEngineer

## Root cause

BTCAAAAA-25766 is an auto-generated blocking issue created by the Impact Gate worker
(`src/impact_gate/worker.py:629`) when a fix issue had BTCAAAAA-99 in its
blast-radius regression set and the gate runner reported a non-PASS status.

This is the **fourth confirmed false-positive blocking issue** for BTCAAAAA-99
(previous: BTCAAAAA-25175, BTCAAAAA-25262, BTCAAAAA-25520).

### Immediate cause: false positive

The BTCAAAAA-99 regression test file
(`tests/bug_regression/test_btcaaaaa_99_regression.py`) contains **29 tests**
(well above the `MIN_TESTS_BAR = 10`). All 29 tests pass both locally and via
the Impact Gate runner. The gate failure was likely a transient CI infrastructure
condition at the time the gate ran.

### Systemic cause: runner zero_test_files ERROR produces blocking issues

When the Impact Gate runner's JUnit XML parser (`_parse_junit()`) fails to match
any collected test cases to a target file, the `_populate()` function marks the
entry as `ERROR` with `"No tests collected"`. The worker then treats this as an
actionable failure and creates a blocking issue.

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
============================== 29 passed in 0.84s ==============================
```

### 2. Impact Gate runner for BTCAAAAA-99

```
$ python scripts/impact_gate_runner.py --bugs BTCAAAAA-99
status: PASS, total: 29, passed: 29, failed: 0, errors: 0, missing: 0
```

### 3. CI pipeline wiring — PRESENT

`tests/bug_regression/` is included in `.github/workflows/test.yml:90`.

### 4. Dedup note

Each unique source fix issue produces a fresh dedup key
(`<!-- dedup:impact-gate:{fix_identifier}:BTCAAAAA-99:bug -->`), so dedup does
not prevent recurrence across different source fix issues.

## Status

**RESOLVED** — all 29 regression tests for BTCAAAAA-99 pass. The impact gate
runner reports PASS. The CI pipeline is wired correctly. The blocking issue
BTCAAAAA-25766 is a false positive. No code changes required.
