"""
Regression tests for BTCAAAAA-25633: Blast Radius worker -- detect fix->in_review
and post report (CI/CD infrastructure and worker deployment).

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-25633
Component: .github/workflows/blast-radius-worker.yml,
            .github/workflows/blast-radius-monitor.yml,
            scripts/blast_radius_monitor.py,
            src/blast_radius/worker.py,
            src/blast_radius/__main__.py

Root cause: N/A -- automation infrastructure. The Blast Radius worker is deployed
as a GitHub Actions workflow (every 5 min via schedule and on-demand via
repository_dispatch webhooks). A companion monitor workflow health-checks the
worker output and creates alert issues on errors. The worker detects fix/bug
issues transitioning to in_review, generates a Blast Radius Report comment, then
self-closes the issue to done.

This file re-exports the existing unit tests from tests/test_blast_radius/ so
the Impact Gate runner can discover them by issue ID. The canonical tests live
in tests/test_blast_radius/ and must not drift.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-25633"),
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
