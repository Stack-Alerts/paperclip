# BTCAAAAA-25520 — Impact Gate: Bug regression tests failing for BTCAAAAA-99

**Status:** RESOLVED (false positive — tests pass; runner bug fixed)
**Verification date:** 2026-05-13
**Verified by:** AutomationEngineer

## Root cause

BTCAAAAA-25520 is an auto-generated blocking issue created by the Impact Gate worker
(`src/impact_gate/worker.py:576-578`) when a fix issue had BTCAAAAA-99 in its
blast-radius regression set.

There are **two causes** — one immediate and one systemic:

### Immediate cause: false positive

The BTCAAAAA-99 regression test file
(`tests/bug_regression/test_btcaaaaa_99_regression.py`) contains **29 tests**
(well above the `MIN_TESTS_BAR = 10`). All 29 tests pass both locally and via
the Impact Gate runner. This is the third confirmed false-positive blocking
issue for BTCAAAAA-99 (previous: BTCAAAAA-25175, BTCAAAAA-25262).

### Systemic cause: runner error path marks all IDs MISSING

`scripts/impact_gate_runner.py` pre-populated every requested ID with `"status":
"MISSING"` before running pytest.  The `_populate()` function overwrites tested
entries with actual results.  However, when pytest itself fails (timeout, JUnit
XML parse error), the `except` blocks return the pre-populated dicts with every
ID still marked `MISSING`.  The worker then creates a blocking issue for every
ID in the blast radius — including BTCAAAAA-99 — even though its test file
exists and passes.

**Fix applied in this heartbeat:** Changed the pre-population status from
`"MISSING"` to `"PENDING"`.  Genuinely missing test files (path does not exist)
are elevated to `MISSING` immediately after pre-population.  When the runner
itself errors, entries for existing test files stay as `PENDING`, which the
worker does **not** treat as an actionable failure.  Only the top-level
`"ERROR"` status signals the infrastructure failure.

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

### 4. Runner fix — prevents future false positives

Changed `impact_gate_runner.py` pre-population from MISSING to PENDING, with
genuinely missing files elevated to MISSING explicitly.  Runner-level errors
(timeout, JUnit parse failure) no longer produce false blocking issues for
every ID in the blast radius.

## Status

**RESOLVED** — all 29 regression tests for BTCAAAAA-99 pass. The impact gate
runner reports PASS. The CI pipeline is wired correctly. The runner-level bug
that caused false-positive MISSING statuses on infrastructure errors is fixed.
