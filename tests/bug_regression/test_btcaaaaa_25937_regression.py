"""Regression tests for BTCAAAAA-25937: Impact Gate — scan for fix issues done.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-25937
Component: scripts/scan_fix_issues_done.py,
            scripts/scan_done_alert.py,
            scripts/impact_gate_runner.py,
            scripts/run_impact_gate_worker.py,
            scripts/impact_gate_worker.py,
            src/impact_gate/worker.py,
            src/impact_gate/runner.py,
            src/blast_radius/worker.py,
            src/blast_radius/generator.py,
            src/blast_radius/query.py,
            src/blast_radius/report.py,
            src/blast_radius/api_server.py,
            src/touch_index/bug_worker.py,
            src/touch_index/fr_worker.py,
            src/touch_index/comment_extractor.py,
            src/touch_index/git_extractor.py,
            src/touch_index/paperclip_client.py,
            src/touch_index/quality.py,
            .github/workflows/impact-gate-scan-done.yml,
            .github/workflows/impact-gate-worker.yml,
            .github/workflows/blast-radius-worker.yml,
            .github/workflows/blast-radius-monitor.yml,
            docs/runbook-impact-gate-scan-done.md,
            docs/architecture/IMPACT_GATE.md

Root cause: N/A — parent orchestration verification.  The scan-done pipeline
audits done fix/bug issues for Impact Gate coverage on a 5-minute cadence,
with done-guard protection against reopen loops and persistent muted-state to
avoid redundant API calls across CI runs.  This issue aggregates the full
Impact Gate scan-done subsystem: Impact Gate gating, Blast Radius worker
fix→in_review detection, Touch Index FR/bug ingestion, and the paperclip
client that ties them together.

This file re-exports the existing unit tests from tests/test_impact_gate/,
tests/test_blast_radius/, and tests/test_touch_index/ so the Impact Gate
runner can discover them by issue ID.  The canonical tests live in those
directories and must not drift.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-25937"),
    pytest.mark.regression,
]

# Impact Gate tests
from tests.test_impact_gate.test_scan_done import (  # noqa: E402, F401
    TestIsFixIssue,
    TestGateHeaderRegex,
    TestCheckGateStatus,
    TestScanFunction,
    TestMain as TestScanDoneMain,
)
from tests.test_impact_gate.test_scan_done_alert import (  # noqa: E402, F401
    TestFindTodaysAlert,
    TestCreateAlert,
    TestMain as TestScanDoneAlertMain,
)
from tests.test_impact_gate.test_worker import (  # noqa: E402, F401
    TestHasBypassLabel,
    TestBuildDedupKey,
    TestCommentBuilders,
    TestProcessIssue,
    TestFindExistingBlockingIssue,
    TestCreateBlockingIssue,
    TestSetBlockedBy,
    TestMinimumTestBar,
    TestPostComment,
    TestGetIssue,
    TestScanDoneIssues,
)
from tests.test_impact_gate.test_runner import (  # noqa: E402, F401
    TestFetchInReviewFixIssues,
    TestRunnerMain,
)
from tests.test_impact_gate.test_e2e import (  # noqa: E402, F401
    TestImpactGateRunnerE2E,
    TestImpactGateRunnerCLI,
)

# Blast Radius tests
from tests.test_blast_radius.test_worker import (  # noqa: E402, F401
    TestIsFixIssue as TestBRIsFixIssue,
    TestStatePersistence,
    TestDetectTransitions,
    TestSyncStatuses,
    TestFetchInReviewIssues,
    TestRunOnce,
    TestProcessIssue as TestBRProcessIssue,
    TestRunLoop,
    TestMain as TestBLWorkerMain,
)
from tests.test_blast_radius.test_main import (  # noqa: E402, F401
    TestRunWorkerCli,
    TestQuerySubcommand,
    TestGenerateSubcommand,
    TestServeSubcommand,
    TestJsonSummary,
)
from tests.test_blast_radius.test_runner import (  # noqa: E402, F401
    TestRunnerMain as TestBRRunnerMain,
)
from tests.test_blast_radius.test_cli import (  # noqa: E402, F401
    TestMainDelegation,
)
from tests.test_blast_radius.test_generator import (  # noqa: E402, F401
    TestGenerateAndPost,
    TestGetAgentName,
    TestPostComment as TestBRPostComment,
    TestGetIssue as TestBRGetIssue,
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

# Touch Index tests
from tests.test_touch_index.test___main__ import (  # noqa: E402, F401
    TestMainDispatch,
    TestHelp,
)
from tests.test_touch_index.test_bug_runner import (  # noqa: E402, F401
    TestBugRunnerDelegation,
)
from tests.test_touch_index.test_bug_worker import (  # noqa: E402, F401
    TestParseCompletedAt,
    TestIngestBugIssue,
    TestRunBugWorker,
    TestProcessBugIssue,
    TestBugWorkerDryRun,
    TestMain as TestBugWorkerMain,
    TestMainProcessBugIssueError,
    TestBugWorkerMain as TestBugWorkerMainAlt,
    TestBugJsonSummary,
    TestEmitJsonSummaryRequiresWorker as TestEmitJsonSummaryRequiresWorkerBug,
    TestCatchUpEligibleBugIssues,
)
from tests.test_touch_index.test_comment_extractor import (  # noqa: E402, F401
    TestNormalise,
    TestHasAllowedPrefix,
    TestExtractFilesFromText,
    TestExtractFilesFromComments,
    TestFetchAndExtract,
    TestFetchIssueComments,
)
from tests.test_touch_index.test_db import (  # noqa: E402, F401
    TestGetEngine,
    TestHealthCheck,
)
from tests.test_touch_index.test_fr_runner import (  # noqa: E402, F401
    TestFrRunnerDelegation,
)
from tests.test_touch_index.test_fr_worker import (  # noqa: E402, F401
    TestIngestFrIssue,
    TestRunFrWorker,
    TestProcessFrIssue,
    TestMain as TestFRWorkerMain,
    TestMainProcessFrIssueError,
    TestCatchUpEligibleFrIssues,
    TestEmitJsonSummaryRequiresWorker,
)
from tests.test_touch_index.test_git_extractor import (  # noqa: E402, F401
    TestIsSourceFile,
    TestGetCommitHashes,
    TestGetFilesForCommit,
    TestGetFilesForIssue,
    TestGetAllReferencedIssueIds,
    TestRunErrorHandling,
)
from tests.test_touch_index.test_paperclip_client import (  # noqa: E402, F401
    TestRetryStrategy,
    TestParseIsoTs,
    TestGetClosedNonFdrIssues,
    TestGetFdrIssues,
    TestGetClosedBugIssues,
    TestGetAllDoneIssues,
    TestPaginate,
    TestGetIssueById,
    TestGetIssueByIdentifier,
    TestGetAllIssueIds,
    TestTransitionIssueStatus,
    TestTransitionIssueStatusBoard,
    TestGetIssueAssignee,
    TestGetClosedBugIssuesExtended,
    TestGetAllDoneIssuesExtended,
    TestBoardSession,
    TestListIssues,
    TestFetchIssueComments as TestFetchIssueCommentsClient,
    TestBase,
    TestCompany,
    TestListLiveRuns,
    TestCancelHeartbeatRun,
    TestForceReleaseIssue,
)
from tests.test_touch_index.test_quality import (  # noqa: E402, F401
    TestComputeCoverage,
    TestComputeFreshness,
    TestCheckConsistency,
    TestRunQualityChecks,
    TestComputeBugCoverage,
    TestComputeBugFreshness,
    TestCheckBugConsistency,
    TestRunBugQualityChecks,
    TestCheckConsistencyExtended,
    TestRunQualityChecksExtended,
    TestCheckBugConsistencyExtended,
    TestRunBugQualityChecksExtended,
    TestReportToDict,
    TestReportToDictExtended,
    TestBugQualityReportToDictExtended,
)
from tests.test_touch_index.test_snapshot_quality import (  # noqa: E402, F401
    TestBuildFrReport,
    TestBuildBugReport,
    TestMain as TestSnapshotMain,
)
from tests.test_touch_index.test_validate_bug import (  # noqa: E402, F401
    TestValidateBug,
)
from tests.test_touch_index.test_validate_fr import (  # noqa: E402, F401
    TestValidateFR,
)
