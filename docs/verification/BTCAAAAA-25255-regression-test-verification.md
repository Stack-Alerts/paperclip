# BTCAAAAA-25255 — Impact Gate: Bug regression tests failing for BTCAAAAA-79

**Status:** RESOLVED (false positive)
**Verification date:** 2026-05-13
**Verified by:** AutomationEngineer

## Root cause

BTCAAAAA-25255 is an auto-generated blocking issue created by the Impact Gate worker
(`src/impact_gate/worker.py:492-508`) when a fix issue attempted `in_review` promotion
and had BTCAAAAA-79 in its blast-radius regression set. This is a transient/false-positive
failure — the BTCAAAAA-79 regression test suite is present and all tests pass.

## Test suite status

File: `tests/bug_regression/test_btcaaaaa_79_regression.py` (538 lines, 45 tests)

### Local verification — PASS (45/45)

```
python -m pytest tests/bug_regression/test_btcaaaaa_79_regression.py -v --tb=short
============================== 45 passed in 2.08s ==============================
```

### Impact Gate runner — PASS

```
python scripts/impact_gate_runner.py --bugs BTCAAAAA-79
{"status": "PASS", "summary": {"total": 45, "passed": 45, "failed": 0, "errors": 0, ...}}
```

### CI pipeline wiring — PRESENT

Test file listed at `.github/workflows/test.yml:87` (line 89 in test matrix).

### Test classes (10 classes, 45 tests)

| Test class | Tests | Area |
|---|---|---|
| `TestRoleModel` | 4 | Default role, admin state, drop_admin |
| `TestPinAuthentication` | 8 | bcrypt hash, PIN verify, first-run |
| `TestAccessControl` | 6 | _check_access gate for admin-only keys |
| `TestMaskedDisplay` | 5 | Last-4-chars masking |
| `TestSaveSentinelLogic` | 5 | Bullet sentinel skip |
| `TestEnvPermissions` | 2 | .env chmod 600 enforcement |
| `TestSecretFieldWidget` | 6 | Masked display, edit mode, sentinel return |
| `TestAdminPinDialogLockout` | 4 | 3-failure lockout |
| `TestSettingsDialogAdminSectionVisibility` | 4 | Tab hidden/revealed/concealed |
| `TestSecurityInvariant` | 1 | No admin key fetch on non-admin open |

All 45 tests pass — 35 tests above the minimum 10-test bar.

## Source dependencies

- `src/strategy_builder/ui/settings_service.SettingsService` — all referenced methods exist
- `src/strategy_builder/ui/settings_dialog.SecretFieldWidget` — present
- `src/strategy_builder/ui/settings_dialog.AdminPinDialog` — present
- `src/strategy_builder/ui/settings_dialog.SettingsDialog` — present

No breaking changes to any of these files since the test file was created (commit `e1f6856e`).

## Previous resolution

Identical issue BTCAAAAA-25168 was resolved on 2026-05-13 with the same root cause
and fix (commit `e1f6856e` created the test file). BTCAAAAA-25255 is a duplicate
transient failure — the Impact Gate worker created a new blocking issue because the
dedup key differed (different source fix issue triggering the gate).

## Conclusion

The BTCAAAAA-79 bug regression test suite is complete and passing. All 45 tests pass
locally and via the Impact Gate runner. The blocking issue BTCAAAAA-25255 is a
false positive and should be closed.
