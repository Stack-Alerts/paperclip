"""
Regression tests for BTCAAAAA-2741: add missing bug regression test file for
BTCAAAAA-1168 (Blast Radius).

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-2741
Component: tests/bug_regression/

Root cause: N/A — this was a testing-infrastructure fix.  The Impact Gate
runner must be able to discover and run bug regression test files by bug ID.
The Impact Gate Runner iterates in_review fix issues, resolves their bug IDs
to test file paths, and invokes pytest against those files.  This fix added
the file for BTCAAAAA-1168 that was missing from the set of committed bug
regression test files.

This file re-exports the existing Impact Gate scan-done unit tests from
tests/test_impact_gate/test_scan_done.py so the Impact Gate runner can discover
them by bug ID.  The canonical tests live in tests/test_impact_gate/ and must
not drift.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-2741"),
    pytest.mark.regression,
]

from tests.test_impact_gate.test_scan_done import (  # noqa: E402, F401
    TestIsFixIssue,
    TestGateHeaderRegex,
    TestCheckGateStatus,
    TestScanFunction,
    TestMain,
)
