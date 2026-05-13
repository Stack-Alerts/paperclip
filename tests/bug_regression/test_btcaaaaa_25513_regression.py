"""
Regression tests for BTCAAAAA-25513: Touch Index bug-close ingestion worker.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-25513
Component: src/touch_index/bug_worker.py, src/touch_index/__main__.py

Fix: Add missing mock for catch_up_eligible_bug_issues in TestMain and
TestBugJsonSummary polling-mode tests that were hanging by running real
git commands. Each polling-mode test now patches the function to return
empty results, ensuring tests run offline without real I/O.

This file re-exports the existing unit tests from test_bug_worker.py so the
Impact Gate runner can discover them by issue ID.  The canonical tests live in
tests/test_touch_index/test_bug_worker.py and must not drift.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-25513"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_bug_worker import (  # noqa: E402, F401
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
