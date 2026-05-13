"""
Regression tests for BTCAAAAA-25361: Blast Radius worker — detect fix→in_review
and post report.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-25361
Component: src/blast_radius/worker.py

Root cause: N/A — this was a feature (routine execution) rather than a bug fix.
The Blast Radius worker polls for fix/bug issues transitioning to in_review
and generates a Blast Radius Report comment. It runs every 5 minutes.

This file re-exports the existing unit tests from test_worker.py and
test_main.py so the Impact Gate runner can discover them by bug ID. The
canonical tests live in tests/test_blast_radius/ and must not drift.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-25361"),
    pytest.mark.regression,
]

from tests.test_blast_radius.test_worker import (  # noqa: E402, F401
    TestIsFixIssue,
    TestStatePersistence,
    TestDetectTransitions,
    TestSyncStatuses,
    TestFetchInReviewIssues,
    TestRunOnce,
    TestProcessIssue,
    TestRunLoop,
    TestMain,
)
from tests.test_blast_radius.test_main import (  # noqa: E402, F401
    TestRunWorkerCli,
    TestJsonSummary,
)
