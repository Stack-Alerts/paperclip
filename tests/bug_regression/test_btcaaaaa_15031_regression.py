"""
Regression tests for BTCAAAAA-15031: Touch Index bug-close ingestion worker.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-15031
Component: python -m touch_index bug (src/touch_index/__main__.py)

The bug-close ingestion worker polls Paperclip for done non-FDR issues
closed in the last N minutes, extracts touched files from git history
(or falls back to issue comments/description), upserts to
touch_index_bug_files, and transitions each processed issue to "done".

This file re-exports the "_run_bug_cli()" CLI entry point tests from
``tests/test_touch_index/test_bug_worker.py`` so the Impact Gate runner
can discover them by issue ID. The canonical tests live in
``tests/test_touch_index/test_bug_worker.py`` and must not drift.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-15031"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_bug_worker import (  # noqa: E402, F401
    TestMain,
    TestMainProcessBugIssueError,
)
