"""
Regression tests for BTCAAAAA-1619: add main() CLI entry point and __main__ dispatch for bug-close ingestion worker.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1619
Fixed in commits: ef9d63fd, d6b0da36
Component: src/touch_index/bug_worker.py, src/touch_index/__main__.py

Root cause: the bug-close ingestion worker lacked a main() CLI entry point and
__main__.py subcommand dispatcher, so it could not be invoked via
``python -m touch_index bug [options]``.  This feature mirrored the FR worker's
CLI entry point (--issue-id, --lookback-minutes, --dry-run) and added a
subcommand dispatcher for ``python -m touch_index [fr|bug]``.

This file re-exports the existing main() CLI tests from
tests/test_touch_index/test_bug_worker.py so the Impact Gate runner can
discover them by bug ID.  The canonical tests live in
tests/test_touch_index/test_bug_worker.py and must not drift.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1619"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_bug_worker import (  # noqa: E402, F401
    TestMain,
    TestBugWorkerMain,
)
