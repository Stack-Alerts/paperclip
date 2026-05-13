"""
Regression tests for BTCAAAAA-25459: Touch Index FR ingestion worker (operational).

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-25459
Component: scripts/run_touch_index_fr_worker.py, scripts/touch-index-fr-worker.service,
           scripts/touch-index-fr-worker.timer, scripts/setup_touch_index_fr_worker.sh

Root cause: N/A -- operational deployment. Adds systemd timer + service + setup
script to run the FR ingestion worker on a recurring 15-minute schedule with
data quality validation on every cycle.

This file re-exports the existing unit tests from test_fr_worker.py and
test_fr_runner.py so the Impact Gate runner can discover them by issue ID.
The canonical tests live in tests/test_touch_index/ and must not drift.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-25459"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_fr_worker import (  # noqa: E402, F401
    TestIngestFrIssue,
    TestRunFrWorker,
    TestProcessFrIssue,
    TestMain,
    TestMainProcessFrIssueError,
    TestEmitJsonSummaryRequiresWorker,
)
from tests.test_touch_index.test_fr_runner import (  # noqa: E402, F401
    TestFrRunnerDelegation,
)
