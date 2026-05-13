"""
Regression tests for BTCAAAAA-1734: Edge case tests for single-issue transition
errors and bug_worker.main() delegation.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1734
Component: src/touch_index/__main__.py, src/touch_index/bug_worker.py,
           src/touch_index/fr_worker.py

Changes:
   1. test_fr_worker: covers single-issue FR path when transition_issue_status
      raises (except block in _run_fr_cli, previously uncovered).
   2. test_bug_worker: covers single-issue bug path when transition_issue_status
      raises (except block in _run_bug_cli, previously uncovered).
   3. test_bug_worker: covers bug_worker.main() delegation to
      __main__._run_bug_cli() (previously uncovered lines).
   4. All touch_index core modules now at 100%% code coverage.

This file re-exports the existing unit tests from test_bug_worker.py and
test_fr_worker.py so the Impact Gate runner can discover them by issue ID.
The canonical tests live in tests/test_touch_index/ and must not drift.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1734"),
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

from tests.test_touch_index.test_fr_worker import (  # noqa: E402, F401
    TestIngestFrIssue,
    TestRunFrWorker,
    TestProcessFrIssue,
    TestMainProcessFrIssueError,
    TestCatchUpEligibleFrIssues,
    TestEmitJsonSummaryRequiresWorker,
)
