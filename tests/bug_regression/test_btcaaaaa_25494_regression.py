"""
Regression tests for BTCAAAAA-25494: Touch Index FR ingestion worker catch-up.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-25494
Component: src/touch_index/fr_worker.py, src/touch_index/__main__.py

Root cause: The FR ingestion worker's 30-minute lookback window missed FDR
issues that were created or updated outside that window. New FDR issues would
never be indexed unless explicitly triggered via --issue-id, causing coverage
to drift below the 90% quality threshold.

Fix: Add catch_up_eligible_fr_issues() to the FR worker, analogous to the bug
worker's catch_up_eligible_bug_issues(). On every polling cycle, after
processing lookback-window issues, the catch-up scans ALL FDR issues from
Paperclip and ingests any not yet indexed in touch_index_fr_files.

This file re-exports the existing unit tests from test_touch_index/ so the
Impact Gate runner can discover them by bug ID.  The canonical tests live in
tests/test_touch_index/ and must not drift.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-25494"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_fr_worker import (  # noqa: E402, F401
    TestCatchUpEligibleFrIssues,
)
from tests.test_touch_index.test___main__ import (  # noqa: E402, F401
    TestMainDispatch,
    TestHelp,
)
