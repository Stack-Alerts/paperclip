"""
Regression tests for BTCAAAAA-25880: Touch Index FR ingestion worker.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-25880
Component: src/touch_index/fr_worker.py, src/touch_index/__main__.py,
  tests/test_touch_index/test_fr_worker.py

Root cause: N/A -- routine ingestion worker maintenance and test coverage
improvement.  The FR worker polls Paperclip for FDR-labelled issues updated
in the last N minutes, extracts file paths from comments/git/description
in priority order, and upserts them to touch_index_fr_files.

This file re-exports the existing FR worker unit tests so the Impact Gate
runner can discover them by issue ID.  The canonical tests live in
tests/test_touch_index/ and must not drift.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-25880"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_fr_worker import (  # noqa: E402, F401
    TestIngestFrIssue,
    TestRunFrWorker,
    TestProcessFrIssue,
    TestMain,
    TestMainProcessFrIssueError,
    TestCatchUpEligibleFrIssues,
    TestEmitJsonSummaryRequiresWorker,
)
from tests.test_touch_index.test_validate_fr import (  # noqa: E402, F401
    TestValidateFR,
)
from tests.test_touch_index.test_fr_runner import (  # noqa: E402, F401
    TestFrRunnerDelegation,
)
