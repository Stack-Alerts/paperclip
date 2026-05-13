"""
Regression tests for BTCAAAAA-25495: Touch Index bug-close ingestion worker.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-25495
Component: src/touch_index/bug_worker.py, src/touch_index/__main__.py,

Root cause: N/A — this is a data quality monitoring and observability
improvement for the bug-close ingestion worker. Adds actionable metadata
(missing eligible identifiers) to the quality snapshot so the team can
identify which specific issues need investigation when eligible coverage
drops below the 90% threshold.

This file re-exports the existing unit tests from test_bug_worker.py and
test_snapshot_quality.py so the Impact Gate runner can discover them by
issue ID.  The canonical tests live in tests/test_touch_index/ and must
not drift.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-25495"),
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
from tests.test_touch_index.test_snapshot_quality import (  # noqa: E402, F401
    TestBuildBugReport,
)
