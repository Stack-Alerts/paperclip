"""
Regression tests for BTCAAAAA-25881: Touch Index bug-close ingestion worker.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-25881
Component: src/touch_index/bug_worker.py, src/touch_index/__main__.py

Root cause: The catch_up_eligible_bug_issues function was not finding all
eligible git-referenced issues because the list endpoint sometimes omits
the ``description`` field, preventing the description fallback from firing.
Fixed in BTCAAAAA-25776 with a retry that fetches the full issue by ID when
git and comments produce no files and the batch-description is empty.

This file re-exports the existing bug worker unit tests so the Impact Gate
runner can discover them by issue ID.  The canonical tests live in
tests/test_touch_index/ and must not drift.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-25881"),
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
