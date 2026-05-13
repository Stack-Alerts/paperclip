"""
Regression tests for BTCAAAAA-25775: Touch Index FR ingestion worker.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-25775
Component: src/touch_index/fr_worker.py

Root cause: catch_up_eligible_fr_issues was missing the description-fallback
retry that run_fr_worker already implements. When the Paperclip list endpoint
omits the description field, and neither comments nor git find files, the
catch-up now fetches the full issue by ID and retries description-based
extraction before skipping.

This file re-exports the existing unit tests from tests/test_touch_index/ so the
Impact Gate runner can discover them by issue ID. The canonical tests live in
tests/test_touch_index/ and must not drift.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-25775"),
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
