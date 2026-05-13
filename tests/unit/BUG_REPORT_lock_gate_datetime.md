## Bug Report

**Summary**: `scripts/lock_gate.py:89` TypeError — can't subtract offset-naive and offset-aware datetimes
**Steps to Reproduce**:
1. Run `pytest tests/unit/test_lock_gate.py -v --tb=long`
2. Observe 3 test failures in `TestEndToEnd`

**Expected Behavior**: All lock_gate tests should pass
**Actual Behavior**: `TypeError: can't subtract offset-naive and offset-aware datetimes` at line 89 of `scripts/lock_gate.py` where `parsed - now` fails because `parsed` is offset-aware (from ISO parsing) and `now` is offset-naive

**Root Cause**: `validate_exception_entry()` in `scripts/lock_gate.py` receives an offset-naive `now` via `validate_exceptions_file()` which defaults `now=None` and falls back to `datetime.now()` (naive), while ISO-parsed `expires_iso` produces offset-aware datetimes.

**Fix**: Change `datetime.now()` to `datetime.now(timezone.utc)` in `validate_exceptions_file()` at the fallback for `now`.

**Severity**: Medium
**Affected Component**: `scripts/lock_gate.py` — Module Lock Gate validation
**Discovered By**: QAEngineer
**Discovery Context**: Unit test regression during QA review of BTCAAAAA-224/BTCAAAAA-24971
