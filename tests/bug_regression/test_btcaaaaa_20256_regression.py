"""
Regression tests for BTCAAAAA-20256: Impact Gate — narrow fix/bug issue title
matching to first-word pattern.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-20256
Component: scripts/scan_fix_issues_done.py, scripts/run_impact_gate_worker.py

Root cause: _is_fix_issue and _fetch_in_review_fix_issues used substring
matching for 'fix', 'bug', 'regression', 'hotfix' in issue titles, causing
false positives for non-fix issues like 'Impact Gate: scan for fix issues
done'.  Switched to re.match so the keyword must be the first word.

This file re-exports the existing Impact Gate scan-done and runner unit tests
from tests/test_impact_gate/test_scan_done.py and
tests/test_impact_gate/test_runner.py so the Impact Gate runner can discover
them by bug ID.  The canonical tests live in tests/test_impact_gate/ and must
not drift.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-20256"),
    pytest.mark.regression,
]

from tests.test_impact_gate.test_scan_done import (  # noqa: E402, F401
    TestIsFixIssue,
    TestGateHeaderRegex,
    TestCheckGateStatus,
    TestScanFunction,
    TestMain,
)

from tests.test_impact_gate.test_runner import (  # noqa: E402, F401
    TestFetchInReviewFixIssues,
    TestRunnerMain,
)
