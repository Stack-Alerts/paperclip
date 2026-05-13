"""
Regression tests for BTCAAAAA-25502: Touch Index FR ingestion worker.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-25502
Component: src/touch_index/fr_worker.py, src/touch_index/__main__.py

Feature: The FR ingestion worker upserts touch_index_fr_files rows by
extracting file paths from three sources (in priority order):
  1. Issue done-comments — implementing agent's completion comment
  2. Git commits referencing the FDR identifier
  3. Issue description text

The worker supports single-issue (webhook) and polling modes, dry-run,
catch-up for all-indexed coverage, --validate quality gates, and
--json-summary output.

This file re-exports the existing unit tests from test_fr_worker.py so the
Impact Gate runner can discover them by issue ID.  The canonical tests live in
tests/test_touch_index/test_fr_worker.py and must not drift.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-25502"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_fr_worker import (  # noqa: E402, F401
    TestIngestFrIssue,
    TestRunFrWorker,
    TestProcessFrIssue,
    TestMain,
)
