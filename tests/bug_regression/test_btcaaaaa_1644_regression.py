"""
Regression tests for BTCAAAAA-1644: Skip non-done issues in bug-close ingestion
webhook entry point.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1644
Component: src/touch_index/bug_worker.py

Root cause: The bug worker's webhook entry point was processing in-progress
issues, leading to partial data and null closed_at being indexed.  The fix added
a status check in process_bug_issue to only process done issues, which was
later reverted by BTCAAAAA-1719 (wire transition-to-done into webhook path and
remove dead status check).  The current behavior accepts non-done issues with
the caller responsible for transitioning.

This file re-exports the existing unit tests from test_bug_worker.py so the
Impact Gate runner can discover them by issue ID.  The canonical tests live in
tests/test_touch_index/ and must not drift.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1644"),
    pytest.mark.regression,
]

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
