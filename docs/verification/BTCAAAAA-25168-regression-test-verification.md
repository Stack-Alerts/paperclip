# BTCAAAAA-25168 — Impact Gate: Bug regression tests failing for BTCAAAAA-79

**Status:** RESOLVED
**Verification date:** 2026-05-13
**Verified by:** AutomationEngineer

## Root cause

BTCAAAAA-25168 is an auto-generated blocking issue created by the Impact Gate worker (`src/impact_gate/worker.py:492-508`) when a fix issue attempted `in_review` promotion and had BTCAAAAA-79 in its blast-radius regression set. At that time, no regression bridge file existed at `tests/bug_regression/test_btcaaaaa_79_regression.py`, causing the Impact Gate to return MISSING for BTCAAAAA-79.

## Fix applied

Commit `e1f6856e` created the regression test file (538 lines, 45 test cases):

- `tests/bug_regression/test_btcaaaaa_79_regression.py` — full coverage of the Security Architecture for Settings per BTCAAAAA-79

Test classes implemented:

| Test class | Tests | Coverage area |
|---|---|---|
| `TestRoleModel` | 4 | Default role, admin state, drop_admin |
| `TestPinAuthentication` | 8 | bcrypt hash, PIN verify, first-run, PermissionError |
| `TestAccessControl` | 6 | _check_access gate for admin-only keys |
| `TestMaskedDisplay` | 5 | Last-4-chars masking, short/empty values |
| `TestSaveSentinelLogic` | 5 | Bullet sentinel skip for user + admin settings |
| `TestEnvPermissions` | 2 | .env chmod 600 enforcement |
| `TestSecretFieldWidget` | 6 | Masked display, edit mode, sentinel return |
| `TestAdminPinDialogLockout` | 4 | 3-failure lockout, countdown, reset |
| `TestSettingsDialogAdminSectionVisibility` | 4 | Tab hidden/revealed/concealed |
| `TestSecurityInvariant` | 1 | No admin key fetch on non-admin open |

## Verification results

### pytest (45/45 passed)

All 45 tests pass with no failures or errors.

### Impact Gate runner (PASS)

- Status: PASS
- Total tests: 45, Passed: 45, Failed: 0, Errors: 0
- Test count (45) exceeds minimum bar (10) ✓

### CI pipeline wiring

Test file present at `.github/workflows/test.yml:87` ✓

### Source dependencies

- `src.strategy_builder.ui.settings_service.SettingsService` — all methods tested exist and work
- `src.strategy_builder.ui.settings_dialog.SecretFieldWidget` — present and functional
- `src.strategy_builder.ui.settings_dialog.AdminPinDialog` — present and functional
- `src.strategy_builder.ui.settings_dialog.SettingsDialog` — present and functional

### Keyring integration

Tests use `unittest.mock.patch` for keyring; no live keyring required. Importable and mock-compatible ✓

## Conclusion

The BTCAAAAA-79 bug regression test suite is complete, all 45 tests pass, and the minimum 10-test bar is exceeded (45 tests). The Impact Gate blocking issue BTCAAAAA-25168 is resolved.
