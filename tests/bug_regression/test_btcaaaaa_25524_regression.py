"""
Regression tests for BTCAAAAA-25524: Touch Index bug-close ingestion worker.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-25524
Component: src/touch_index/__main__.py, src/touch_index/bug_worker.py,
           src/touch_index/fr_worker.py

Fix: The "no issues" polling path in both bug and FR workers passed ``results=[]``
to ``_emit_json_summary`` even when the catch-up phase produced results, causing
the JSON summary to incorrectly report zero issues processed. Both paths now
pass the catch-up results (with computed ``total_files`` and ``skipped``) so the
JSON summary accurately reflects all work done in the heartbeat.

This file re-exports the existing unit tests from test_bug_worker.py and
test_fr_worker.py so the Impact Gate runner can discover them by issue ID.
The canonical tests live in tests/test_touch_index/ and must not drift.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-25524"),
    pytest.mark.regression,
]

# Re-export bug worker test classes
from tests.test_touch_index.test_bug_worker import (  # noqa: E402, F401
    TestParseCompletedAt,
    TestIngestBugIssue,
    TestRunBugWorker,
    TestProcessBugIssue,
    TestBugWorkerDryRun,
    TestMain,
    TestMainProcessBugIssueError,
    TestBugWorkerMain,
    TestBugJsonSummary,
    TestEmitJsonSummaryRequiresWorker,
    TestCatchUpEligibleBugIssues,
)

# Re-export FR worker test classes
from tests.test_touch_index.test_fr_worker import (  # noqa: E402, F401
    TestIngestFrIssue,
    TestRunFrWorker,
    TestProcessFrIssue,
    TestMain,
    TestMainProcessFrIssueError,
    TestCatchUpEligibleFrIssues,
    TestEmitJsonSummaryRequiresWorker,
)
