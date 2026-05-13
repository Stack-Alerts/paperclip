"""
Regression tests for BTCAAAAA-1719: Wire transition-to-done into webhook path
and remove dead status check in polling path.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1719
Component: src/touch_index/bug_worker.py, src/touch_index/__main__.py

Root cause: The bug-close ingestion worker's transition-to-done feature was
dead code — the polling path queried status=done so all returned issues were
already done (transition loop was a no-op), and the webhook path had no
transition call at all.

Changes:
  1. process_bug_issue: remove status!=done guard so non-done issues are
     accepted (caller transitions them to done).
  2. __main__._run_bug_cli: add transition call after successful
     process_bug_issue in the webhook path.
  3. __main__._run_bug_cli: remove the issue.get('status') == 'done'
     check in the polling path transition loop so ALL processed issues
     are transitioned (except in dry-run mode).
  4. scripts/run_touch_index_bug_worker.py: same fixes for the legacy
     runner script.

This file re-exports the existing unit tests from test_bug_worker.py and
test_bug_runner.py so the Impact Gate runner can discover them by issue ID.
The canonical tests live in tests/test_touch_index/ and must not drift.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1719"),
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

from tests.test_touch_index.test_bug_runner import (  # noqa: E402, F401
    TestBugRunnerDelegation,
)
