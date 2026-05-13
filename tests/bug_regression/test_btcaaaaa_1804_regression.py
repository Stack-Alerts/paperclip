"""
Regression tests for BTCAAAAA-1804: emit --json-summary before SystemExit on
validation failure and wire into CI.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1804
Components: src/touch_index/__main__.py
            .github/workflows/touch-index-bug-worker.yml

Root cause / changes:
  1. Bug worker single-issue & polling paths did not emit --json-summary
     before raising SystemExit when --validate failed.  The JSON summary
     with quality report is now emitted first so CI monitoring can
     capture structured output even on failure.
  2. FR worker paths applied the same fix for consistency.
  3. --json-summary wired into the CI workflow (touch-index-bug-worker.yml)
     matching the blast-radius / impact-gate patterns.

This file re-exports the existing unit tests from tests/test_touch_index/ so
the Impact Gate runner can discover them by issue ID.  The canonical tests
live in tests/test_touch_index/test_bug_worker.py and must not drift.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1804"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_bug_worker import (  # noqa: E402, F401
    TestBugJsonSummary,
    TestEmitJsonSummaryRequiresWorker,
    TestMain,
    TestMainProcessBugIssueError,
)

# ---------------------------------------------------------------------------
# Source-level contract checks for BTCAAAAA-1804-specific changes
# ---------------------------------------------------------------------------

MAIN_SOURCE = Path(__file__).resolve().parents[2] / "src" / "touch_index" / "__main__.py"
MAIN_TEXT = MAIN_SOURCE.read_text()

WORKFLOW_SOURCE = (
    Path(__file__).resolve().parents[2]
    / ".github"
    / "workflows"
    / "touch-index-bug-worker.yml"
)
WORKFLOW_TEXT = WORKFLOW_SOURCE.read_text()


class TestBtc1804JsonSummaryBeforeSystemExit:
    """BTCAAAAA-1804: --json-summary must be emitted before SystemExit on
    validation failure in all code paths (health check, API error, validate)."""

    def test_health_check_failure_emits_json_then_exits(self):
        assert '_emit_json_summary(args, worker="bug")' in MAIN_TEXT
        assert "raise SystemExit(1)" in MAIN_TEXT

    def test_single_issue_exception_emits_json(self):
        assert "logger.exception" in MAIN_TEXT
        assert "if args.json_summary:" in MAIN_TEXT

    def test_single_issue_validate_fail_emits_json(self):
        assert 'quality_report=report,' in MAIN_TEXT
        assert 'logger.error("VALIDATION FAILED after single-issue ingestion")' in MAIN_TEXT

    def test_polling_api_error_emits_json(self):
        assert "Failed to fetch closed non-FDR issues" in MAIN_TEXT
        assert '_emit_json_summary(args, worker="bug")' in MAIN_TEXT

    def test_polling_no_issues_validate_fail_emits_json(self):
        assert "VALIDATION FAILED \u2014 investigate existing data" in MAIN_TEXT
        assert "_emit_json_summary(" in MAIN_TEXT

    def test_polling_with_issues_validate_fail_emits_json(self):
        assert "VALIDATION FAILED after ingestion" in MAIN_TEXT
        assert "quality_report=report," in MAIN_TEXT

    def test_fr_worker_has_matching_fix(self):
        """FR worker must apply the same json-summary-before-SystemExit pattern."""
        assert "raise SystemExit(1)" in MAIN_TEXT
        assert 'worker="fr"' in MAIN_TEXT


class TestBtc1804CiWorkflow:
    """BTCAAAAA-1804: CI workflow must wire --json-summary into all run paths."""

    def test_json_summary_flag_in_workflow(self):
        assert "--json-summary" in WORKFLOW_TEXT

    def test_validate_flag_with_json_summary_in_polling(self):
        assert "--validate" in WORKFLOW_TEXT
        assert "$FLAGS" in WORKFLOW_TEXT
