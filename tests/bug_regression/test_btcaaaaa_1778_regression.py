"""
Regression tests for BTCAAAAA-1778: fix bug-close ingestion worker control flow
and add FR worker JSON summary.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1778
Component: src/touch_index/__main__.py, src/touch_index/quality.py

Root cause: (1) The --validate flag in _run_bug_cli() for single-issue mode was
running validation even when the issue was not found or in dry-run, due to an
indentation error that placed it outside the non-dry-run success branch.
(2) The FR worker lacked structured JSON output for CI consumers.

Fix:
- Moved validate block into the correct if/else branch in _run_bug_cli()
- Added --json-summary flag and _emit_json_summary() to _run_fr_cli()
- Added to_dict() methods to CoverageReport, FreshnessReport, ConsistencyReport,
  and QualityReport dataclasses

This file re-exports the existing unit tests from tests/test_touch_index/ so
the Impact Gate runner can discover them by issue ID. The canonical tests live
in tests/test_touch_index/ and must not drift.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1778"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_bug_worker import (  # noqa: E402, F401
    TestMain,
)

from tests.test_touch_index.test_fr_worker import (  # noqa: E402, F401
    TestEmitJsonSummaryRequiresWorker,
)
