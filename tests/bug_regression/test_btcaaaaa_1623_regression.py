"""
Regression tests for BTCAAAAA-1623: add CLI entry point tests for blast_radius.worker.main().

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1623
Fixed in commits: e0fe7cc
Component: src/blast_radius/worker.py

Root cause: N/A — this was a testing gap rather than a bug fix.

This file re-exports the existing Blast Radius worker main() CLI tests from
tests/test_blast_radius/test_worker.py so the Impact Gate runner can
discover them by bug ID.  The canonical tests live in
tests/test_blast_radius/test_worker.py and must not drift.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1623"),
    pytest.mark.regression,
]

from tests.test_blast_radius.test_worker import (  # noqa: E402, F401
    TestMain,
)
