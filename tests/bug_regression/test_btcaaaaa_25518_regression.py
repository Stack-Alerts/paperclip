"""
Regression tests for BTCAAAAA-25518: Touch Index bug-close ingestion worker.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-25518
Component: src/touch_index/bug_worker.py, src/touch_index/__main__.py,
           src/touch_index/fr_worker.py

Fix:
  - Add catch_up_eligible_bug_issues() to scan git history for eligible done
    non-FDR issues not yet indexed, ensuring eligible coverage stays above
    quality threshold without requiring full backfill.
  - Add catch-up phase to bug worker polling path for both the no-issues and
    post-worker paths.
  - Fix worker_count capture before results.extend(catchup_results) to ensure
    accurate error reporting.
  - Remove redundant worker_count = len(results) after the catch-up block.
  - Add catch_up_eligible_fr_issues() to the FR worker, analogous to the bug
    worker catch-up, and wire it into the FR worker polling path.
  - Add missing mocks for catch_up_eligible_bug_issues in polling-mode tests
    that were running real git commands offline.

This file re-exports the existing unit tests from test_bug_worker.py and
test_fr_worker.py so the Impact Gate runner can discover them by issue ID.
The canonical tests live in tests/test_touch_index/ and must not drift.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-25518"),
    pytest.mark.regression,
]

# Re-export all bug worker test classes
from tests.test_touch_index.test_bug_worker import (  # noqa: E402, F401
    TestCatchUpEligibleBugIssues,
)

# Re-export FR worker catch-up tests
from tests.test_touch_index.test_fr_worker import (  # noqa: E402, F401
    TestCatchUpEligibleFrIssues,
)
