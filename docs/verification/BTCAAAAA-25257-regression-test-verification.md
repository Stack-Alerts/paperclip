# BTCAAAAA-25257 — Impact Gate: Bug regression tests failing for BTCAAAAA-87

**Status:** RESOLVED
**Verification date:** 2026-05-13
**Verified by:** AutomationEngineer

## Root cause

BTCAAAAA-25257 is an auto-generated blocking issue created by the Impact Gate worker (`src/impact_gate/worker.py:492-508`) when fix issue **BTCAAAAA-7332** (Fix DictWrapper mapping protocol to support ** unpacking) transitioned to `in_review`. BTCAAAAA-87 appeared in its blast-radius regression set. The Impact Gate test runner initially reported failing tests — likely because the test file was committed with only 8 test cases (below the MIN_TESTS_BAR=10) before commit `d8b27fe5` added 2 more.

Additionally, a bug was found: the `_create_blocking_issue` function passed `"body"` instead of `"description"` in the API payload, causing all auto-created blocking issues to have null descriptions. This was fixed in the same heartbeat.

## Fix applied

### Bug fix: `"body"` → `"description"` in API issue-creation payloads

The Paperclip API expects `"description"` not `"body"` when creating issues. All auto-created impact gate blocking issues had null descriptions. Fixed in:

- `src/impact_gate/worker.py:156` — blocking issue creation
- `scripts/scan_done_alert.py:127,139` — scan-done alert creation
- `scripts/nightly_test_alert.py:61,68` — nightly test alert creation
- `scripts/lock_gate_nightly_alert.py:173` — nightly lock gate alert creation
- `scripts/lock_gate_create_signoff.py:112` — lock gate signoff issue creation

Comment-posting code (which correctly uses `"body"`) was NOT modified.

### Test verification

`tests/bug_regression/test_btcaaaaa_87_regression.py` — 10 test cases across 6 classes

| Test class | Tests | Coverage area |
|---|---|---|
| `TestNoSetFixedWidth` | 2 | Zero `setFixedWidth()` calls in `settings_dialog.py` source |
| `TestSettingsDialogMinimumDimensions` | 2 | Minimum width (>=820px) and height (>=600px) |
| `TestAdminPinDialogMinimumDimensions` | 2 | Minimum width (>=440px) in auth and setup modes |
| `TestSettingsDialogTitle` | 1 | Dialog window title is "Settings" |
| `TestSecretFieldWidgetButtons` | 1 | Zero `setFixedWidth()` calls in `SecretFieldWidget` class |
| `TestAdminPinDialogTitles` | 2 | Window titles correct in auth ("Admin Authentication") and setup ("Set Admin PIN") modes |

## Verification results

### Impact Gate runner (PASS)

- Status: PASS
- Total tests: 10, Passed: 10, Failed: 0, Errors: 0
- Test count (10) meets minimum bar (10) ✓

### CI pipeline wiring

Test file present at `.github/workflows/test.yml:90` ✓

## Conclusion

The BTCAAAAA-87 bug regression test suite is complete, all 10 tests pass, and the minimum 10-test bar is met. The blocking issue BTCAAAAA-25257 is resolved. The underlying bug causing empty issue descriptions has been fixed.
