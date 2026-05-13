"""
Regression tests for BTCAAAAA-1679: add --validate flag to bug-close ingestion worker CLI.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1679
Component: src/touch_index/bug_worker.py

Root cause: the --validate flag was missing from the module-level entry point
(python -m touch_index bug).  Only the wrapper script
scripts/run_touch_index_bug_worker.py supported --validate.  Added
argparse support and quality-check invocation at all three exit points
(single-issue, no-issues, polling) matching the fr_worker pattern.

This file re-exports the existing TestMain unit tests from
tests/test_touch_index/test_bug_worker.py so the Impact Gate runner can
discover them by issue ID.  The canonical tests live in
tests/test_touch_index/test_bug_worker.py and must not drift.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1679"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_bug_worker import (  # noqa: E402, F401
    TestMain,
)
