"""
Regression tests for BTCAAAAA-25801: Touch Index bug-close ingestion worker.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-25801
Component: src/touch_index/bug_worker.py

Root cause: N/A -- routine ingestion worker maintenance and test coverage
improvement. The bug worker polls Paperclip for done non-FDR issues closed
in the last N minutes, extracts file paths from git/comments/description
in priority order, and upserts them to touch_index_bug_files.

This file re-exports the existing unit tests from tests/test_touch_index/ so the
Impact Gate runner can discover them by issue ID. The canonical tests live in
tests/test_touch_index/ and must not drift.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-25801"),
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
