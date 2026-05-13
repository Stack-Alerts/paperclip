"""
Regression tests for BTCAAAAA-25699: Touch Index bug-close ingestion worker.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-25699
Component: src/touch_index/bug_worker.py, src/touch_index/__main__.py

Root cause: The bug-close ingestion worker's --issue-id path unconditionally
transitioned issues to done, including non-done issues received via webhook
events (issue_created, issue_updated). This caused premature closure of issues
that were still in_progress or in_review.

The fix adds an issue_status field to BugIngestionResult and only transitions
issues that are already in "done" status (or have unknown/None status).

This file re-exports the existing unit tests from tests/test_touch_index/ so the
Impact Gate runner can discover them by issue ID. The canonical tests live in
tests/test_touch_index/ and must not drift.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-25699"),
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
from tests.test_touch_index.test_validate_bug import (  # noqa: E402, F401
    TestValidateBug,
)
