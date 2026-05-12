"""
Regression tests for BTCAAAAA-3621: add missing bug regression test file for BTCAAAAA-1236.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-3621
Fixed in commit: 240be0c0
Component: tests/bug_regression/test_btcaaaaa_1236_regression.py

Root cause: When the Impact Gate runner processes a fix issue, it always adds
the fix issue's own identifier as a bug ID requiring a regression test at
``tests/bug_regression/test_btcaaaaa_{identifier}_regression.py``.  The fix
for BTCAAAAA-3621 added a regression test for BTCAAAAA-1236 but did not include
a regression test for itself, causing the gate to fail with MISSING status.

Fix: add this file so the Impact Gate can find a regression test for
BTCAAAAA-3621.  The tests from BTCAAAAA-1236 are re-exported here because
the deliverable of BTCAAAAA-3621 IS the BTCAAAAA-1236 regression test.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-3621"),
    pytest.mark.regression,
]

from tests.bug_regression.test_btcaaaaa_1236_regression import (  # noqa: E402, F401
    TestIsFixIssue,
    TestStateHelpers,
    TestRunOnce,
)
