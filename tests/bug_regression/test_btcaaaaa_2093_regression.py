"""
Regression tests for BTCAAAAA-2093: apply ruff format to touch_index
bug-close ingestion worker and tests.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-2093
Component: src/touch_index/bug_worker.py, scripts/run_touch_index_bug_worker.py

This file re-exports the canonical unit tests from test_bug_worker.py and
test_bug_runner.py so the Impact Gate runner can discover them by bug ID.
The canonical tests live in tests/test_touch_index/ and must not drift.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-2093"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_bug_worker import (  # noqa: E402, F401
    TestParseCompletedAt,
    TestIngestBugIssue,
    TestRunBugWorker,
    TestProcessBugIssue,
    TestBugWorkerDryRun,
    TestMain,
)

from tests.test_touch_index.test_bug_runner import (  # noqa: E402, F401
    TestBugRunnerDelegation,
)
