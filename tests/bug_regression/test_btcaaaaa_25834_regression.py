"""Regression tests for BTCAAAAA-25834: Impact Gate — scan for fix issues done.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-25834
Component: scripts/scan_fix_issues_done.py,
            scripts/scan_done_alert.py,
            scripts/impact_gate_runner.py,
            scripts/run_impact_gate_worker.py,
            src/impact_gate/worker.py,
            .github/workflows/impact-gate-scan-done.yml,
            .github/workflows/impact-gate-worker.yml,
            docs/runbook-impact-gate-scan-done.md

Root cause: N/A — routine execution automation. The Impact Gate scan-done
workflow audits fix/bug issues in done status for gate coverage every 5 minutes.
It identifies ungated issues, optionally runs retroactive gating, creates alert
issues for the CTO, and persists data quality snapshots. The done-guard prevents
the scan from accidentally reopening done issues via comment/transition mutations.

This file re-exports the existing unit tests from tests/test_impact_gate/ so
the Impact Gate runner can discover them by issue ID. The canonical tests live
in tests/test_impact_gate/ and must not drift.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-25834"),
    pytest.mark.regression,
]

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
