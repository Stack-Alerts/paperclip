"""
Regression tests for BTCAAAAA-25435: Touch Index FR ingestion worker.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-25435
Component: src/touch_index/fr_worker.py, src/touch_index/__main__.py

Root cause: N/A -- this was a routine execution task. The FR ingestion worker
polls Paperclip for FDR-labelled issues updated in the last 30 minutes,
extracts touched files from comments/git/description, and upserts to
touch_index_fr_files.

This file re-exports the existing unit tests from test_fr_worker.py and
test_fr_runner.py so the Impact Gate runner can discover them by issue ID.
The canonical tests live in tests/test_touch_index/ and must not drift.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-25435"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_fr_worker import (  # noqa: E402, F401
    TestIngestFrIssue,
    TestRunFrWorker,
    TestProcessFrIssue,
    TestMain,
    TestMainProcessFrIssueError,
    TestEmitJsonSummaryRequiresWorker,
)
from tests.test_touch_index.test_fr_runner import (  # noqa: E402, F401
    TestFrRunnerDelegation,
)
