"""
Regression tests for BTCAAAAA-25485: Touch Index FR ingestion worker.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-25485
Component: src/touch_index/fr_worker.py, src/touch_index/__main__.py

Root cause: N/A -- this was a new build. The FR ingestion worker polls
Paperclip for FDR-labelled issues, extracts touched file paths from
done-comments/git/description, and upserts to touch_index_fr_files.

This file re-exports the existing unit tests from test_touch_index/ so the
Impact Gate runner can discover them by bug ID.  The canonical tests live in
tests/test_touch_index/ and must not drift.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-25485"),
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
from tests.test_touch_index.test___main__ import (  # noqa: E402, F401
    TestMainDispatch,
    TestHelp,
)
from tests.test_touch_index.test_fr_runner import (  # noqa: E402, F401
    TestFrRunnerDelegation,
)
from tests.test_touch_index.test_validate_fr import (  # noqa: E402, F401
    TestValidateFR,
)
