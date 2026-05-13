"""Regression tests for BTCAAAAA-25860: Blast Radius worker — detect fix→in_review
and post report.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-25860
Component: src/blast_radius/worker.py,
            src/blast_radius/__main__.py,
            src/blast_radius/generator.py,
            src/blast_radius/report.py,
            src/blast_radius/query.py,
            .github/workflows/blast-radius-worker.yml,
            .github/workflows/blast-radius-monitor.yml,
            scripts/blast_radius_monitor.py,
            scripts/blast_radius_cli.py,
            scripts/run_blast_radius_worker.py,
            docs/runbook-blast-radius-worker.md

Root cause: N/A — routine execution automation. The Blast Radius worker polls
for fix/bug issues transitioning to in_review, generates a Blast Radius Report
comment, and self-closes the issue to done. The CI workflow runs every 5 minutes
via GitHub Actions schedule or on demand via repository_dispatch webhooks. A
companion monitor workflow health-checks the worker output and creates alert
issues on errors.

This file re-exports the existing unit tests from tests/test_blast_radius/ so
the Impact Gate runner can discover them by issue ID. The canonical tests live
in tests/test_blast_radius/ and must not drift.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-25860"),
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
