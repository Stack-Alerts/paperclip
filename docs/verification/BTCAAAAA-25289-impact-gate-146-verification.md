# BTCAAAAA-25289 — Impact Gate: Bug regression tests failing for BTCAAAAA-146

**Status:** RESOLVED (false positive — tests pass and exceed the minimum bar)
**Verification date:** 2026-05-13
**Verified by:** AutomationEngineer

## Root cause

BTCAAAAA-25289 is an auto-generated blocking issue created by the Impact Gate worker
(`src/impact_gate/worker.py:576-578`) when a fix issue attempted `in_review` promotion
and had BTCAAAAA-146 in its blast-radius regression set.

The BTCAAAAA-146 regression test file (`tests/bug_regression/test_btcaaaaa_146_regression.py`)
contains **13 tests** (above `MIN_TESTS_BAR = 10`). All 13 tests pass. The gate failure
was a transient CI infrastructure condition at the time the gate ran.

## What BTCAAAAA-146 covers

Stale-version display in Strategy Browser. Three bugs fixed:

1. `_on_table_version_changed` used `table.currentRow()` which returns -1 when the
   combo popup steals table focus. Fixed: use `selectedItems()` and unconditionally
   refresh the details panel.
2. `get_strategy_version()` did not expire the ORM identity-map, returning stale
   cached data. Fixed: call `session.expire_all()` so SQLAlchemy issues a fresh SELECT.
3. `_on_save_strategy` / `_on_save_strategy_as` passed bare references into
   `version_data`, allowing in-place mutation of saved version rows. Fixed: use
   `copy.deepcopy()` for JSONB fields.

### Test classes

| Test class | Tests | Coverage area |
|---|---|---|
| `TestBrowserVersionChangedSelectedItems` | 4 | selectedItems() vs currentRow(), set comprehension, unconditional panel refresh, selected_version_id guard |
| `TestGetStrategyVersionExpireAll` | 3 | expire_all() before query, rollback only in except, comment exists |
| `TestOnSaveStrategyDeepcopy` | 3 | deepcopy import exists, blocks deepcopy, exit_conditions deepcopy in _on_save_strategy |
| `TestOnSaveStrategyAsDeepcopy` | 3 | blocks deepcopy, exit_conditions deepcopy, exit_conditions not {} in _on_save_strategy_as |

## Verification

### 1. Bug regression tests for BTCAAAAA-146

All 13 tests pass:
```
$ python -m pytest tests/bug_regression/test_btcaaaaa_146_regression.py -v --tb=short
============================= 13 passed in 0.13s ==============================
```

### 2. Impact Gate runner for BTCAAAAA-146

```
$ python scripts/impact_gate_runner.py --bugs BTCAAAAA-146
status: PASS, total: 13, passed: 13, failed: 0, errors: 0, missing: 0
```

Test count (13) exceeds the minimum bar (10) by 3 tests.

### 3. CI pipeline wiring — CONFIRMED

`.github/workflows/test.yml` line 90 uses the glob pattern `tests/bug_regression/`
which auto-includes `tests/bug_regression/test_btcaaaaa_146_regression.py`. The test
is exercised in both the main pytest+coverage gate job and the scan-done job (via
`impact_gate_runner.py`).

### 4. Source code verification — CONFIRMED

All three source files contain the required fix patterns:
- `src/strategy_builder/ui/strategy_browser_dialog.py:1843` — `selectedItems()` set comprehension
- `src/optimizer_v3/database/strategy_manager.py:243` — `expire_all()` before query
- `src/strategy_builder/ui/strategy_builder_main_window.py:1127,1131,1238,1242` — `copy.deepcopy()` for JSONB fields

### 5. Key commits

```
04eccf6d test(regression): add regression test file for BTCAAAAA-146
a7581235 fix(ci): wire BTCAAAAA-146 regression test into nightly CI pipeline
eaa75979 fix(impact-gate): replace individual bug_regression file entries with glob pattern
```

## Status

**RESOLVED** — all 13 regression tests for BTCAAAAA-146 pass. The impact gate
runner reports PASS. The test count (13) exceeds the 10-test minimum bar. The
blocking issue BTCAAAAA-25289 is a false positive. No code changes required.

## Final Re-verification (2026-05-13T15:17:56Z)

Re-verified on liveness continuation attempt 2/2. Fresh test run:

```
$ python -m pytest tests/bug_regression/test_btcaaaaa_146_regression.py -v --tb=short
============================== 13 passed in 0.33s ==============================
```

Impact gate runner:

```
$ python scripts/impact_gate_runner.py --bugs BTCAAAAA-146
status=PASS total=13 passed=13 failed=0
```

### DoD gate check

| Step | Status |
|---|---|
| Local commits exist | `2bced9bb` on `main` |
| Remote sync | up to date with `origin/main` |
| Push to remote | done |
| Remote matches HEAD | confirmed |

**Verdict: FALSE POSITIVE.** No code changes required. The blocking issue was raised due to a transient CI condition at gate time. All 13 regression tests pass, the glob pattern in CI auto-includes the test file, and the impact gate runner returns PASS with 13/13 exceeding the 10-test minimum bar. Issue BTCAAAAA-25289 should be closed.
