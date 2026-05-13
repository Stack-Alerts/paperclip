"""
Regression tests for BTCAAAAA-1784: --json-summary support in bug-close ingestion worker.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1784
Component: src/touch_index/__main__.py, src/touch_index/quality.py

Root cause: The bug-close ingestion worker (touch_index __main__ --bug mode)
lacked structured JSON output.  The FR worker had --json-summary but the bug
worker did not.  Also, _emit_json_summary hardcoded "fr" as the worker name,
so the FR worker's JSON summaries were mislabeled.

Changes:
  - Parameterized _emit_json_summary with a `worker` argument (default "bug"
    for backward compatibility with the FR entry path until explicitly passed).
  - Added --json-summary flag to the bug worker CLI (single-issue, polling,
    and no-issues paths).
  - Added to_dict() methods to BugCoverageReport, BugFreshnessReport,
    BugConsistencyReport, and BugQualityReport dataclasses.

This file re-exports the existing unit tests from test_bug_worker.py so the
Impact Gate runner can discover them by issue ID.  The canonical tests live in
tests/test_touch_index/ and must not drift.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1784"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_bug_worker import (  # noqa: E402, F401
    TestBugJsonSummary,
    TestEmitJsonSummaryRequiresWorker,
)
