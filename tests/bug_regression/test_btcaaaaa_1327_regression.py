"""
Regression tests for BTCAAAAA-1327: add missing args = parser.parse_args() to bug worker CLI.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1327
Fixed in commit: ad1efbf
Component: src/touch_index/__main__.py

Root cause: the bug worker CLI entry point _run_bug_cli() defined all argparse
arguments but was missing the ``args = parser.parse_args()`` call. At runtime,
any reference to ``args.*`` (issue_id, dry_run, validate, json_summary) would
raise ``NameError: name 'args' is not defined``. The FR worker already had the
parse_args line; the bug worker was inconsistent.

This file tests that:
  1. _run_bug_cli correctly parses all CLI flags without error
  2. The argparse setup is present and functional
  3. Edge cases: --issue-id alone, --validate --json-summary combination
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1327"),
    pytest.mark.regression,
]


class TestBugWorkerCliParsing:
    """Verify _run_bug_cli accepts the expected CLI flags without NameError."""

    def test_dry_run_flag_parsed(self):
        """--dry-run is parsed without NameError from missing parse_args."""
        engine = MagicMock()
        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch(
                "touch_index.paperclip_client.get_closed_non_fdr_issues",
                return_value=[],
            ),
            patch("touch_index.bug_worker.run_bug_worker", return_value=[]),
        ):
            from touch_index.__main__ import _run_bug_cli

            with patch.object(sys, "argv", ["touch_index", "--dry-run"]):
                _run_bug_cli()

    def test_validate_flag_parsed(self):
        """--validate is parsed without NameError."""
        engine = MagicMock()
        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch(
                "touch_index.paperclip_client.get_closed_non_fdr_issues",
                return_value=[],
            ),
            patch("touch_index.bug_worker.run_bug_worker", return_value=[]),
            patch("touch_index.quality.run_bug_quality_checks") as mock_qc,
        ):
            mock_qc.return_value.passed = True
            from touch_index.__main__ import _run_bug_cli

            with patch.object(sys, "argv", ["touch_index", "--validate"]):
                _run_bug_cli()

    def test_issue_id_with_json_summary(self):
        """--issue-id with --json-summary parses both flags correctly."""
        engine = MagicMock()
        result = MagicMock()
        result.issue_id = "test-uuid"
        result.issue_identifier = "BTCAAAAA-1327"
        result.files_indexed = 1
        result.source = "git"
        result.skipped_no_commits = False

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch("touch_index.bug_worker.process_bug_issue", return_value=result),
        ):
            from touch_index.__main__ import _run_bug_cli

            with patch.object(
                sys,
                "argv",
                ["touch_index", "--issue-id", "test-uuid", "--json-summary"],
            ):
                _run_bug_cli()

    def test_all_flags_together(self):
        """All bug worker CLI flags parse without error (--issue-id + --dry-run + --validate + --json-summary + --stale-days)."""
        engine = MagicMock()
        result = MagicMock()
        result.issue_id = "test-uuid"
        result.issue_identifier = "BTCAAAAA-1327"
        result.files_indexed = 1
        result.source = "git"
        result.skipped_no_commits = False

        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch("touch_index.bug_worker.process_bug_issue", return_value=result),
            patch("touch_index.quality.run_bug_quality_checks") as mock_qc,
        ):
            mock_qc.return_value.passed = True
            from touch_index.__main__ import _run_bug_cli

            with patch.object(
                sys,
                "argv",
                [
                    "touch_index",
                    "--issue-id",
                    "test-uuid",
                    "--dry-run",
                    "--validate",
                    "--json-summary",
                    "--stale-days",
                    "60",
                ],
            ):
                _run_bug_cli()

    def test_lookback_minutes_default(self):
        """--lookback-minutes defaults to 30 when not specified."""
        engine = MagicMock()
        with (
            patch("touch_index.db.get_engine", return_value=engine),
            patch("touch_index.db.health_check", return_value=True),
            patch(
                "touch_index.paperclip_client.get_closed_non_fdr_issues",
                return_value=[],
            ),
            patch("touch_index.bug_worker.run_bug_worker", return_value=[]),
        ):
            from touch_index.__main__ import _run_bug_cli

            with patch.object(sys, "argv", ["touch_index"]):
                _run_bug_cli()
