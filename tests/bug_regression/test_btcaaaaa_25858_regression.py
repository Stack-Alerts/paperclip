"""
Regression tests for BTCAAAAA-25858: Touch Index bug-close ingestion worker.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-25858
Component: src/touch_index/bug_worker.py, src/touch_index/__main__.py,
            tests/test_touch_index/test_bug_worker.py,
            tests/test_touch_index/test_validate_bug.py

Root cause: N/A — parent orchestration issue.  The bug-close ingestion worker
audits done non-FDR issues on a 15-minute cadence, extracting referenced files
from git commits, Paperclip comments, and issue descriptions, then upserts them
to touch_index_bug_files with done-guard protection against reopen loops.
This is the top-level orchestration issue that spawned child issues for
individual regression test shims (BTCAAAAA-25831, BTCAAAAA-25837,
BTCAAAAA-25843, BTCAAAAA-25850).

This file re-exports the existing unit tests from tests/test_touch_index/ so
the Impact Gate runner can discover them by issue ID.  The canonical tests
live in tests/test_touch_index/ and must not drift.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-25858"),
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
