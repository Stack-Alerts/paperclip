"""
Regression tests for BTCAAAAA-1735: use result.issue_id for transition-to-done
in single-issue webhook path.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1735
Fixed in commit: a9c79e82
Components: src/touch_index/__main__.py, tests/test_touch_index/test_bug_worker.py

Root cause: the bug worker and FR worker single-issue webhook paths used
args.issue_id (raw CLI input) instead of result.issue_id (verified API
response ID) for transition_issue_status, inconsistent with the batch
polling path.

Fix:
- Use result.issue_id for transition_issue_status in both _run_bug_cli()
  and _run_fr_cli() in src/touch_index/__main__.py
- Add missing transition_issue_status patch/assertion in bug worker
  single-issue tests to properly cover the success path and avoid real
  HTTP calls

This file re-exports the existing TestMain tests from
tests/test_touch_index/test_bug_worker.py so the Impact Gate runner can
discover them by bug ID.  The canonical tests live in
tests/test_touch_index/test_bug_worker.py and must not drift.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1735"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_bug_worker import TestMain  # noqa: E402, F401
