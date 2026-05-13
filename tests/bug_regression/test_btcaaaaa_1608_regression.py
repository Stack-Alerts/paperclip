"""
Regression tests for BTCAAAAA-1608: add --dry-run flag to bug-close ingestion worker.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1608
Fixed in commit: 4ca691ba
Component: src/touch_index/bug_worker.py, scripts/run_touch_index_bug_worker.py

Root cause: the bug-close ingestion worker lacked a --dry-run flag for safe
preview of what would be indexed.  This feature added dry_run support across
ingest_bug_issue(), process_bug_issue(), and run_bug_worker() so that the
worker can log what it would do without writing to the database.

This file is the canonical regression location.  The full scenario (4 dry-run
unit tests covering ingest, batch, webhook, and comment-fallback paths) is
imported from the authoritative unit-test file so it cannot drift from the
original fix verification.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1608"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_bug_worker import (  # noqa: E402, F401
    TestBugWorkerDryRun,
)
