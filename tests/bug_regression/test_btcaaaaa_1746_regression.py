"""
Regression tests for BTCAAAAA-1746: wrap process_bug_issue in try/except
in single-issue CLI path.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1746
Component: src/touch_index/__main__.py

Root cause: The --issue-id CLI path in _run_bug_cli was missing exception
handling around process_bug_issue(), unlike the webhook handler and polling
path which both have error handling. An API/git/DB error would crash the CLI
with a traceback instead of exiting gracefully with SystemExit(1).

Changes:
  1. _run_bug_cli: wrapped process_bug_issue() in try/except that logs
     the error and exits non-zero.
  2. _run_fr_cli: same fix applied for consistency.

This file re-exports the existing canonical unit tests from
test_bug_worker.py so the Impact Gate runner can discover them by issue ID.
The canonical tests live in tests/test_touch_index/test_bug_worker.py
and must not drift.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1746"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_bug_worker import (  # noqa: E402, F401
    TestMain,
    TestMainProcessBugIssueError,
)
