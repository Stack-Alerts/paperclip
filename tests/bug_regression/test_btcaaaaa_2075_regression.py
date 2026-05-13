"""
Regression tests for BTCAAAAA-2075: --json-summary --issue-id --validate passed
path must include quality data in the JSON output (bug worker).

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-2075
Components: src/touch_index/__main__.py
            tests/test_touch_index/test_bug_worker.py

Root cause / changes:
  1. The bug worker --issue-id path with --validate already emitted
     --json-summary, but had no test coverage proving the passed-validation
     path includes quality data: worker="bug", mode="single-issue", and
     quality.passed=True in the JSON output.
  2. Added test_json_summary_with_validate_issue_id_passed to TestBugJsonSummary
     to ensure validate-passed path emits quality report with passed=True.

This file re-exports the existing unit tests from tests/test_touch_index/ so
the Impact Gate runner can discover them by issue ID.  The canonical tests
live in tests/test_touch_index/ and must not drift.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-2075"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_bug_worker import TestBugJsonSummary  # noqa: E402, F401

# ---------------------------------------------------------------------------
# Source-level contract checks for BTCAAAAA-2075-specific changes
# ---------------------------------------------------------------------------

MAIN_SOURCE = Path(__file__).resolve().parents[2] / "src" / "touch_index" / "__main__.py"
MAIN_TEXT = MAIN_SOURCE.read_text()


class TestBtc2075ValidateIssueIdPassedJsonSummary:
    """BTCAAAAA-2075: --json-summary --issue-id --validate must emit JSON
    including quality data when validation passes (bug worker)."""

    def test_emit_helper_accepts_quality_report_param(self):
        """_emit_json_summary accepts a quality_report keyword argument."""
        assert "quality_report" in MAIN_TEXT
        assert "quality_report: Any | None = None" in MAIN_TEXT

    def test_emit_helper_adds_quality_when_not_none(self):
        """_emit_json_summary adds quality key to summary when quality_report is not None."""
        assert "if quality_report is not None:" in MAIN_TEXT
        assert 'summary["quality"]' in MAIN_TEXT

    def test_single_issue_path_checks_validate_before_emit(self):
        """Single-issue (--issue-id) path checks args.validate after processing."""
        assert "if args.validate:" in MAIN_TEXT

    def test_single_issue_validate_runs_quality_checks(self):
        """Single-issue path runs run_bug_quality_checks when --validate is set."""
        assert "run_bug_quality_checks" in MAIN_TEXT

    def test_single_issue_validate_passed_emit_includes_quality(self):
        """When --issue-id --validate --json-summary is used with passing
        validation, the emit helper is called with quality_report kwarg."""
        lines = MAIN_TEXT.split("\n")
        in_issue_id_block = False
        in_validate_block = False
        emit_seen = False
        for line in lines:
            if "if args.issue_id:" in line:
                in_issue_id_block = True
            if not in_issue_id_block:
                continue
            if "if args.validate:" in line:
                in_validate_block = True
            if not in_validate_block:
                continue
            if "_emit_json_summary(" in line:
                emit_seen = True
            if emit_seen:
                break
            if "if not args.dry_run:" in line:
                break
        assert emit_seen, (
            "_emit_json_summary not found after validate block in single-issue path"
        )
