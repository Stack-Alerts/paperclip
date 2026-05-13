"""
Regression tests for BTCAAAAA-25347: Touch Index bug-close ingestion worker.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-25347
Component: src/touch_index/bug_worker.py
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-25347"),
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
)
