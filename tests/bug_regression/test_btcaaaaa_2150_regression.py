"""
Regression tests for BTCAAAAA-2150: add --stale-days CLI arg coverage for
bug-close ingestion worker.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-2150
Components: src/touch_index/__main__.py
            tests/test_touch_index/test_bug_worker.py

Root cause / changes:
  1. The bug worker supported --stale-hours only in the FR worker path; the
     --stale-days argument and plumbing into run_bug_quality_checks was
     added but lacked test coverage proving it reaches the quality checker.
  2. Added test_main_validate_stale_days_polling, _no_issues, and _issue_id
     to TestMain to verify --stale-days is passed through to
     run_bug_quality_checks in all three modes (polling, no-issues, and
     single-issue), mirroring the --stale-hours tests in the FR worker.

This file re-exports the existing unit tests from tests/test_touch_index/ so
the Impact Gate runner can discover them by issue ID.  The canonical tests
live in tests/test_touch_index/ and must not drift.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-2150"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_bug_worker import TestMain  # noqa: E402, F401

# ---------------------------------------------------------------------------
# Source-level contract checks for BTCAAAAA-2150-specific changes
# ---------------------------------------------------------------------------

MAIN_SOURCE = Path(__file__).resolve().parents[2] / "src" / "touch_index" / "__main__.py"
MAIN_TEXT = MAIN_SOURCE.read_text()


class TestBtc2150StaleDaysCliArg:
    """BTCAAAAA-2150: --stale-days CLI argument must be defined and plumbed
    into run_bug_quality_checks in all three modes (polling, no-issues,
    single-issue)."""

    def test_stale_days_argparser_defined(self):
        """argparse defines --stale-days as an int with default 30."""
        assert "--stale-days" in MAIN_TEXT
        assert 'default=30' in MAIN_TEXT
        assert 'type=int' in MAIN_TEXT

    def test_stale_days_documented_in_module_docstring(self):
        """Module docstring describes --stale-days and shows usage example."""
        assert "--stale-days <N>               Bug worker: stale alert threshold" in MAIN_TEXT
        assert "python -m touch_index bug --stale-days 60" in MAIN_TEXT

    def test_stale_days_in_single_issue_mode(self):
        """Single-issue (--issue-id) path passes stale_threshold_days to
        run_bug_quality_checks."""
        assert (
            'engine, stale_threshold_days=args.stale_days'
        ) in MAIN_TEXT, (
            "stale_threshold_days=args.stale_days must appear in single-issue validate path"
        )
        lines = MAIN_TEXT.split("\n")
        count = sum(
            1 for line in lines
            if "stale_threshold_days=args.stale_days" in line
        )
        assert count >= 3, (
            f"Expected stale_threshold_days=args.stale_days in at least 3 locations, found {count}"
        )

    def test_stale_days_in_polling_mode(self):
        """Polling mode (issues present) passes stale_threshold_days in the
        validate block after run_bug_worker."""
        lines = MAIN_TEXT.split("\n")
        found_run_worker = False
        found_quality_with_stale = False
        for line in lines:
            if "results = run_bug_worker" in line:
                found_run_worker = True
            if found_run_worker and "stale_threshold_days=args.stale_days" in line:
                found_quality_with_stale = True
                break
        assert found_quality_with_stale, (
            "stale_threshold_days=args.stale_days not found after run_bug_worker in polling path"
        )

    def test_stale_days_in_no_issues_mode(self):
        """No-issues path also passes stale_threshold_days after catch-up block."""
        lines = MAIN_TEXT.split("\n")
        in_no_issues = False
        found_stale = False
        for line in lines:
            if 'if not issues:' in line:
                in_no_issues = True
            if not in_no_issues:
                continue
            if "stale_threshold_days=args.stale_days" in line:
                found_stale = True
                break
        assert found_stale, (
            "stale_threshold_days=args.stale_days not found in no-issues path"
        )
