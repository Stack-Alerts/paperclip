"""
Regression tests for BTCAAAAA-15014: include issues without timestamps in
bug-close ingestion worker poll functions instead of skipping.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-15014
Fixed in commit: 68d2982e
Component: src/touch_index/paperclip_client.py

Root cause: ``get_closed_non_fdr_issues()``, ``get_fdr_issues()``,
``get_closed_bug_issues()``, and ``get_all_done_issues()`` all had the same
bug: when a time filter (``closed_after`` / ``updated_after`` /
``completed_after``) was applied, issues without the relevant timestamp
(completedAt/updatedAt) were skipped entirely via a logger.warning + continue.
This caused the bug-close ingestion worker (17.1% coverage) to systematically
exclude done issues missing completedAt, since those issues could never be
returned by ``get_closed_non_fdr_issues``.

Fix: include issues without timestamps in the filtered result instead of
skipping them. The upsert is idempotent, so re-processing is safe.

This file re-exports the existing ``TestGetClosedNonFdrIssues`` tests from
``tests/test_touch_index/test_paperclip_client.py`` so the Impact Gate runner
can discover them by bug ID. The canonical tests live in
``tests/test_touch_index/test_paperclip_client.py`` and must not drift.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-15014"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_paperclip_client import (  # noqa: E402, F401
    TestGetClosedNonFdrIssues,
)
