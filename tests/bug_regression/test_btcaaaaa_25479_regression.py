"""
Regression tests for BTCAAAAA-25479: Blast Radius worker -- detect fix->in_review
and post report.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-25479
Component: src/blast_radius/

Root cause: N/A -- this was a routine execution task. The Blast Radius worker
polls for fix/bug issues transitioning to in_review and generates a Blast
Radius Report comment. It runs every 5 minutes.

This file re-exports all existing unit tests from the blast_radius test suite
so the Impact Gate runner can discover them by bug ID.  The canonical tests
live in tests/test_blast_radius/ and must not drift.
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-25479"),
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
from tests.test_blast_radius.test_query import (  # noqa: E402, F401
    TestQueryBlastRadius,
    TestToJsonDict,
    TestFRImpact,
    TestRegressionRisk,
)
from tests.test_blast_radius.test_api_server import (  # noqa: E402, F401
    TestHandlerGet,
    TestHandlerPost,
    TestReadBody,
    TestServe,
    TestHandlerFrWebhook,
    TestHandlerBugWebhook,
)
