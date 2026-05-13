"""
Regression tests for BTCAAAAA-25681: Touch Index FR ingestion worker.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-25681
Component: src/touch_index/fr_worker.py, src/touch_index/__main__.py,
  tests/test_touch_index/test_validate_fr.py

Root cause: N/A -- maintenance and test coverage improvement. The FR worker
polls Paperclip for FDR-labelled issues, extracts file paths from
comments/git/description in priority order, upserts them to
touch_index_fr_files, and transitions issues to done.

This file re-exports the existing unit tests from test_touch_index/ so the
Impact Gate runner can discover them by issue ID. The canonical tests live in
tests/test_touch_index/ and must not drift.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-25681"),
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
