"""
Regression tests for BTCAAAAA-1586: Webhook/event-driven trigger support for
the bug-close ingestion worker.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1586
Component: src/touch_index/bug_worker.py, src/touch_index/__main__.py

Root cause: The bug worker's CLI only supported polling mode.  Added
process_bug_issue() single-issue webhook entry point and --issue-id flag
to run_touch_index_bug_worker.py, plus fixes for dead HAVING COUNT(*) = 0
queries in bug and FR validation tools.

This file re-exports the existing unit tests from test_bug_worker.py so the
Impact Gate runner can discover them by issue ID.  The canonical tests live in
tests/test_touch_index/ and must not drift.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1586"),
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
