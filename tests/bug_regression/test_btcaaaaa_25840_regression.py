"""Regression tests for BTCAAAAA-25840: Impact Gate — scan for fix issues done.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-25840
Component: scripts/scan_fix_issues_done.py,
            scripts/scan_done_alert.py,
            scripts/impact_gate_runner.py,
            scripts/run_impact_gate_worker.py,
            scripts/impact_gate_worker.py,
            src/impact_gate/worker.py,
            src/blast_radius/worker.py,
            src/impact_gate/runner.py,
            src/touch_index/paperclip_client.py,
            .github/workflows/impact-gate-scan-done.yml,
            .github/workflows/impact-gate-worker.yml,
            docs/runbook-impact-gate-scan-done.md,
            docs/architecture/IMPACT_GATE.md

Root cause: N/A — orchestration verification.  The scan-done pipeline audits
done fix/bug issues for Impact Gate coverage on a 5-minute cadence, with
done-guard protection against reopen loops and persistent muted-state to
avoid redundant API calls across CI runs.  Retroactive gating is enabled on
scheduled runs with a 7-day look-back window.

This file re-exports the existing unit tests from tests/test_impact_gate/ so
the Impact Gate runner can discover them by issue ID.  The canonical tests
live in tests/test_impact_gate/ and must not drift.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-25840"),
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
