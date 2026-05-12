"""
Regression tests for BTCAAAAA-1297: Blast Radius worker — detect fix->in_review and post report.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1297
Fixed in commits: (implemented in src/blast_radius/worker.py)
Component: src/blast_radius/worker.py

Root cause: N/A — this was a feature rather than a bug fix.

This file re-exports the existing Blast Radius worker unit tests from
tests/test_blast_radius/test_worker.py so the Impact Gate runner can
discover them by bug ID.  The canonical tests live in
tests/test_blast_radius/test_worker.py and must not drift.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1297"),
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
