"""
Regression tests for BTCAAAAA-1685: mark bug issues as done after ingestion worker completes.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1685
Component: src/touch_index/bug_worker.py

Fixed in commits: 960fe5bb, e2a51eb6

Root cause: after the bug-close ingestion worker processed a batch of closed
non-FDR issues, those issues were never transitioned to 'done' in Paperclip,
leaving them in an incomplete lifecycle state.  Wired transition_issue_status
into bug_worker.main() so each processed issue is transitioned to 'done'.
Dry-run mode skips the transition, already-done issues are skipped to avoid
403 errors, and failed transitions log the error without crashing the worker.

This file re-exports the existing TestMain unit tests from
tests/test_touch_index/test_bug_worker.py so the Impact Gate runner can
discover them by issue ID.  The canonical tests live in
tests/test_touch_index/test_bug_worker.py and must not drift.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1685"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_bug_worker import (  # noqa: E402, F401
    TestMain,
)
