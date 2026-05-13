"""
Regression tests for BTCAAAAA-25486: Touch Index bug-close ingestion worker.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-25486
Component: src/touch_index/__main__.py, src/touch_index/bug_worker.py

Root cause: The bug-close ingestion worker only processed issues closed
within the lookback window (default 30 min). When new git commits referenced
old issues, those issues became eligible for indexing but were never picked
up, causing eligible coverage to drop below the 90% quality threshold.

Fix: Add a catch-up phase to the polling path that scans all git history for
eligible done non-FDR issues not yet indexed, keeping coverage stable without
requiring a separate backfill run.

This file re-exports the existing unit tests from test_bug_worker.py so the
Impact Gate runner can discover them by issue ID.  The canonical tests live in
tests/test_touch_index/test_bug_worker.py and must not drift.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-25486"),
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
