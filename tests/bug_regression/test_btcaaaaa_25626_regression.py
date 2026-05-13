"""
Regression tests for BTCAAAAA-25626: Blast Radius worker — detect fix→in_review
and post report.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-25626
Component: src/blast_radius/worker.py, src/blast_radius/__main__.py

Root cause: N/A — routine execution automation. The Blast Radius worker polls
for fix/bug issues transitioning to in_review, generates a Blast Radius Report
comment, and self-closes the issue to done. The CI workflow runs every 5 minutes
via GitHub Actions schedule or on demand via repository_dispatch webhooks.

This file re-exports the existing unit tests from tests/test_blast_radius/ so
the Impact Gate runner can discover them by issue ID. The canonical tests live
in tests/test_blast_radius/ and must not drift.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-25626"),
    pytest.mark.regression,
]

from tests.test_blast_radius.test_worker import (  # noqa: E402, F401
    TestIsFixIssue,
    TestStatePersistence,
    TestDetectTransitions,
    TestSyncStatuses,
    TestFetchInReviewIssues,
    TestRunOnce,
    TestProcessIssue,
    TestRunLoop,
    TestMain,
)
from tests.test_blast_radius.test_main import (  # noqa: E402, F401
    TestRunWorkerCli,
    TestJsonSummary,
)
from tests.test_blast_radius.test_runner import (  # noqa: E402, F401
    TestRunnerMain,
)
from tests.test_blast_radius.test_cli import (  # noqa: E402, F401
    TestMainDelegation,
)
from tests.test_blast_radius.test_generator import (  # noqa: E402, F401
    TestGenerateAndPost,
    TestGetAgentName,
    TestPostComment,
    TestGetIssue,
    TestRunHeaders,
)
from tests.test_blast_radius.test_report import (  # noqa: E402, F401
    TestRenderReport,
    TestExtractTouchedFiles,
)
