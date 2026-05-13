"""
Regression tests for BTCAAAAA-1662: Guard malformed timestamp parsing in
bug-close ingestion worker and paperclip API client.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1662
Components: src/touch_index/bug_worker.py, src/touch_index/paperclip_client.py

Fixed in commits: 06be5c72, c5330e22

Root cause: _parse_completed_at in bug_worker.py raised ValueError on malformed
completedAt from the API, crashing the webhook entry point (process_bug_issue)
and silently skipping issues in polling mode.  Added try/except ValueError so
malformed timestamps return None instead of crashing.

Same pattern existed in 4 places in paperclip_client.py (get_fdr_issues,
get_closed_bug_issues, get_closed_non_fdr_issues, get_all_done_issues) where
unguarded fromisoformat would crash the entire API function on a single
malformed timestamp.  Extracted _parse_iso_ts helper with proper try/except
and replaced all inline calls.

This file re-exports the existing unit tests from test_bug_worker.py and
test_paperclip_client.py so the Impact Gate runner can discover them by
issue ID.  The canonical tests live in tests/test_touch_index/ and must
not drift.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1662"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_bug_worker import (  # noqa: E402, F401
    TestParseCompletedAt,
)

from tests.test_touch_index.test_paperclip_client import (  # noqa: E402, F401
    TestParseIsoTs,
)
