# BTCAAAAA-25170 — Impact Gate: Bug regression tests failing for BTCAAAAA-87

**Status:** RESOLVED
**Verification date:** 2026-05-13
**Verified by:** AutomationEngineer

## Root cause

BTCAAAAA-25170 is an auto-generated blocking issue created by the Impact Gate worker (`src/impact_gate/worker.py:492-508`) when a fix issue attempted `in_review` promotion and had BTCAAAAA-87 in its blast-radius regression set. The initial regression test file existed but had only 8 test cases, causing the Impact Gate to report insufficient coverage.

## Fix applied

Commit `d8b27fe5` added 2 test cases to reach the Impact Gate MIN_TESTS_BAR=10:

- `tests/bug_regression/test_btcaaaaa_87_regression.py` — 10 test cases across 6 classes

| Test class | Tests | Coverage area |
|---|---|---|
| `TestNoSetFixedWidth` | 2 | Zero `setFixedWidth()` calls in `settings_dialog.py` source |
| `TestSettingsDialogMinimumDimensions` | 2 | Minimum width (>=820px) and height (>=600px) |
| `TestAdminPinDialogMinimumDimensions` | 2 | Minimum width (>=440px) in auth and setup modes |
| `TestSettingsDialogTitle` | 1 | Dialog window title is "Settings" |
| `TestSecretFieldWidgetButtons` | 1 | Zero `setFixedWidth()` calls in `SecretFieldWidget` class |
| `TestAdminPinDialogTitles` | 2 | Window titles correct in auth ("Admin Authentication") and setup ("Set Admin PIN") modes |

## Verification results

### pytest (10/10 passed)

All 10 tests pass with no failures or errors.

### Impact Gate runner (PASS)

- Status: PASS
- Total tests: 10, Passed: 10, Failed: 0, Errors: 0
- Test count (10) meets minimum bar (10) ✓

### CI pipeline wiring

Test file present at `.github/workflows/test.yml:88` ✓

### Source dependencies

- `src.strategy_builder.ui.settings_dialog.SettingsDialog` — uses `setMinimumWidth(860)` + `adjustSize()` for layout-driven auto-sizing
- `src.strategy_builder.ui.settings_dialog.AdminPinDialog` — uses `setMinimumWidth(440)` + `adjustSize()` for layout-driven auto-sizing
- `src.strategy_builder.ui.settings_dialog.SecretFieldWidget` — uses `setMinimumWidth()` for Show/Edit/Change-PIN buttons

## Conclusion

The BTCAAAAA-87 bug regression test suite is complete, all 10 tests pass, and the minimum 10-test bar is met. The Impact Gate blocking issue BTCAAAAA-25170 is resolved.
