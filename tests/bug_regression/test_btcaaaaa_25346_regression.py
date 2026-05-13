"""
Regression tests for BTCAAAAA-25346: Touch Index FR ingestion worker.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-25346
Component: src/touch_index/fr_worker.py
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-25346"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_fr_worker import (  # noqa: E402, F401
    TestIngestFrIssue,
    TestRunFrWorker,
    TestProcessFrIssue,
    TestMain,
    TestMainProcessFrIssueError,
)
