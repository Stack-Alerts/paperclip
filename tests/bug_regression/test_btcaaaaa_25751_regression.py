"""
Regression tests for BTCAAAAA-25751: Touch Index bug-close ingestion worker.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-25751
Component: src/touch_index/fr_worker.py

Root cause: The FR ingestion worker's run_fr_worker and
catch_up_eligible_fr_issues did not capture issue_status from the issue dict
and did not propagate it through ingest_fr_issue into the FRIngestionResult.
This made the transition guard in the FR polling path (which checks
r.issue_status == "done" or r.issue_status is None) always see None and
always transition regardless of actual status — rendering the guard
ineffective.

Fix: Add issue_status parameter to ingest_fr_issue, and pass
issue_status=issue.get("status") from both run_fr_worker and
catch_up_eligible_fr_issues so the transition guard in __main__ sees the
real issue status.

This file re-exports the existing unit tests from tests/test_touch_index/ so the
Impact Gate runner can discover them by issue ID. The canonical tests live in
tests/test_touch_index/ and must not drift.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-25751"),
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
