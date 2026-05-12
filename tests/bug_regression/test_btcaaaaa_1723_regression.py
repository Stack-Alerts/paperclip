"""
Regression tests for BTCAAAAA-1723: add coverage for missing processed_issue_ids
branch in _load_state.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1723
Fixed in commit: 11e14bf
Component: src/blast_radius/worker.py

Root cause: _load_state() only handled missing keys for "issue_statuses" but
not for "processed_issue_ids". Loading a state file that had issue_statuses
but omitted processed_issue_ids would raise a KeyError instead of filling the
default.

This file re-exports the existing Blast Radius worker _load_state tests from
tests/test_blast_radius/test_worker.py so the Impact Gate runner can
discover them by bug ID. The canonical tests live in
tests/test_blast_radius/test_worker.py and must not drift.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1723"),
    pytest.mark.regression,
]

from tests.test_blast_radius.test_worker import (  # noqa: E402, F401
    TestStatePersistence,
)
