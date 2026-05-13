"""
Regression tests for BTCAAAAA-1655: add missing status=done to FDR label skip test.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1655
Fixed in commits: fe936fff, 383e6ea6
Component: tests/test_touch_index/test_bug_worker.py

Root cause: the FDR label skip test (test_skips_fdr_labelled_issues) was
missing ``"status": "done"`` in the mock issue dict, causing the test to
exit at the status check before reaching the FDR label check in
``process_bug_issue``, leaving lines 143-145 uncovered.

This file re-exports the existing TestProcessBugIssue tests from
tests/test_touch_index/test_bug_worker.py so the Impact Gate runner can
discover them by bug ID.  The canonical tests live in
tests/test_touch_index/test_bug_worker.py and must not drift.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1655"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_bug_worker import (  # noqa: E402, F401
    TestProcessBugIssue,
)
