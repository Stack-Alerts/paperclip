"""
Regression tests for BTCAAAAA-25529: Touch Index bug-close ingestion worker.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-25529
Component: src/touch_index/quality.py, scripts/snapshot_touch_index_quality.py

Fix: Add source distribution tracking to bug quality monitoring (mirroring the
FR quality monitoring feature added in commit 8180b5b3). The
BugConsistencyReport now includes a ``source_distribution`` field tracking row
counts by extraction method (comments, git, description), enabling monitoring
of extraction health and early detection when a source drops off.

- quality.py: add ``source_distribution`` field to ``BugConsistencyReport``,
  query source distribution in ``check_bug_consistency()``, and log it in
  ``run_bug_quality_checks()``.
- snapshot_touch_index_quality.py: include source_distribution in bug report.
- test_snapshot_quality.py: update mocks for new field.

This file re-exports the existing unit tests from test_quality.py and
test_snapshot_quality.py so the Impact Gate runner can discover them by issue
ID.  The canonical tests live in tests/test_touch_index/ and must not drift.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-25529"),
    pytest.mark.regression,
]

# Re-export bug quality test classes
from tests.test_touch_index.test_quality import (  # noqa: E402, F401
    TestComputeBugCoverage,
    TestComputeBugFreshness,
    TestCheckBugConsistency,
    TestRunBugQualityChecks,
    TestCheckBugConsistencyExtended,
    TestRunBugQualityChecksExtended,
    TestReportToDict,
    TestBugQualityReportToDictExtended,
)

# Re-export bug snapshot quality tests
from tests.test_touch_index.test_snapshot_quality import (  # noqa: E402, F401
    TestBuildBugReport,
)
