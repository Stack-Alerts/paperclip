"""
Regression tests for BTCAAAAA-25455: Add self-close logic to Blast Radius
worker routine issues.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-25455
Component: src/blast_radius/worker.py

Root cause: the Blast Radius worker's process_issue() function posted a Blast
Radius Report comment on fix/bug issues transitioning to in_review but never
transitioned them to done, causing routine execution issues to accumulate in
in_review.

Fix: after successfully posting a report (non-dry-run, non-skipped),
process_issue() now calls transition_issue_status_board(issue_id, "done") to
self-close the issue, following the same pattern as the Impact Gate and Touch
Index workers.

The canonical tests live in tests/test_blast_radius/ and must not drift.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-25455"),
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
from tests.test_blast_radius.test_runner import (  # noqa: E402, F401
    TestRunnerMain,
)
from tests.test_blast_radius.test_cli import (  # noqa: E402, F401
    TestMainDelegation,
)
