# BTCAAAAA-25259: Impact Gate Verification Report

## Issue
Bug regression tests for BTCAAAAA-92 reported as failing by Impact Gate.

## Root cause

BTCAAAAA-25259 is an auto-generated blocking issue created by the Impact Gate worker (`src/impact_gate/worker.py:576-578`) when a fix issue attempted `in_review` promotion. At the time the gate ran, the BTCAAAAA-92 regression test file (`tests/bug_regression/test_btcaaaaa_92_regression.py`) had only 5 test cases (from commit `0a14255c`). The impact gate enforces a minimum test bar of 10 tests (`MIN_TESTS_BAR = 10` in `worker.py:51`). With only 5 tests collected, the total fell below the bar, causing the gate to demote the runner's PASS to FAIL.

## Fix applied

Commit `7647efe1` expanded the regression test file from 5 to 10 test cases (334 lines total):

- `tests/bug_regression/test_btcaaaaa_92_regression.py` — comprehensive coverage of SettingsDialog tab-switch auto-resize behavior

### Test classes implemented

| Test class | Tests | Coverage area |
|---|---|---|
| `TestTabSwitchAdjustSizeSource` | 2 | AST check: `QTimer.singleShot(0, adjustSize)` wiring and `currentChanged.connect(lambda)` |
| `TestRevealAdminTabAdjustSize` | 1 | AST check: `_reveal_admin_tab` calls `QTimer.singleShot(0, adjustSize)` |
| `TestInitAdjustSize` | 2 | AST check: `__init__` calls `QTimer.singleShot(0, adjustSize)`; at least 2 total calls |
| `TestConcealAdminTab` | 1 | AST check: `_conceal_admin_tab` switches to tab 0 before hiding |
| `TestDialogConstruction` | 2 | Runtime: 3 tabs exist; admin tab hidden initially |
| `TestSettingsDialogTabSwitchBehavior` | 2 | Runtime: tab switch triggers `adjustSize`; `_reveal_admin_tab` triggers `adjustSize` |

## What BTCAAAAA-92 covers

`SettingsDialog` in `src/strategy_builder/ui/settings_dialog.py` would clip content when switching to the Admin tab because the dialog never recomputed its ideal size. The fix connects `QTabWidget.currentChanged` to `QTimer.singleShot(0, self.adjustSize)` and `_reveal_admin_tab()` calls `QTimer.singleShot(0, self.adjustSize)` after making Admin tab visible.

## Verification

### 1. Bug regression tests for BTCAAAAA-92
All 10 tests pass:
```
$ python -m pytest tests/bug_regression/test_btcaaaaa_92_regression.py -v
10 passed in ~0.50s
```

Tests verified:
- `TestTabSwitchAdjustSizeSource::test_current_changed_connected_to_adjust_size` — PASS
- `TestTabSwitchAdjustSizeSource::test_current_changed_signal_wired_to_lambda_with_timer` — PASS
- `TestRevealAdminTabAdjustSize::test_reveal_admin_tab_calls_adjust_size` — PASS
- `TestInitAdjustSize::test_init_calls_single_shot_adjust_size` — PASS
- `TestInitAdjustSize::test_adjust_size_called_in_both_init_and_reveal` — PASS
- `TestConcealAdminTab::test_conceal_admin_switches_to_tab_zero` — PASS
- `TestDialogConstruction::test_dialog_has_three_tabs` — PASS
- `TestDialogConstruction::test_admin_tab_hidden_initially` — PASS
- `TestSettingsDialogTabSwitchBehavior::test_tab_switch_triggers_adjust_size` — PASS
- `TestSettingsDialogTabSwitchBehavior::test_reveal_admin_triggers_adjust_size` — PASS

### 2. Impact Gate runner for BTCAAAAA-92
```
$ python scripts/impact_gate_runner.py --bugs BTCAAAAA-92
status: PASS, total: 10, passed: 10, failed: 0, errors: 0
```
Test count (10) meets minimum bar (10).

### 3. AST source-level verification
All 4 fix patterns confirmed present in `src/strategy_builder/ui/settings_dialog.py`:
- `QTimer.singleShot(0, self.adjustSize)` — 5 instances (line 325, 367, 476, 502, 1343)
- `currentChanged.connect(lambda: QTimer.singleShot(...))` — line 502
- `_reveal_admin_tab` calls `QTimer.singleShot(0, self.adjustSize)` — line 1343
- `__init__` calls `QTimer.singleShot(0, self.adjustSize)` — line 476

### 4. CI pipeline wiring
`tests/bug_regression/test_btcaaaaa_92_regression.py` is included in `.github/workflows/test.yml:91` and runs on every push/PR plus nightly schedule.

### 5. Key commits
```
7647efe1 test(regression): expand BTCAAAAA-92 regression tests from 5 to 10 to meet 10-test impact gate bar
0a14255c test(regression): add missing bug regression test for BTCAAAAA-92 — auto-resize SettingsDialog on tab switch
f44ec144 fix(ui): call adjustSize on tab switch to prevent Admin tab clipping (BTCAAAAA-92)
```

## Status
**RESOLVED** — all 10 regression tests for BTCAAAAA-92 pass. The impact gate runner reports PASS. The CI pipeline is wired correctly. The test count now meets the 10-test minimum bar. The expansion commit (`7647efe1`) resolved the root cause of the impact gate failure. No further code changes required.
