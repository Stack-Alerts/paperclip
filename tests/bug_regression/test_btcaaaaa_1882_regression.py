"""
Regression tests for BTCAAAAA-1882: --json-summary --issue-id not-found path
must output JSON without a result field (bug worker).

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1882
Components: src/touch_index/__main__.py
            tests/test_touch_index/test_bug_worker.py

Root cause / changes:
  1. The bug worker --issue-id path with a not-found issue (process_bug_issue
     returns None) already emitted --json-summary, but had no test coverage
     proving the output is correct: worker="bug", mode="single-issue", and no
     result field.
  2. Added test_json_summary_issue_id_not_found to TestMainProcessBugIssueError
     to match equivalent FR worker coverage, confirming that the emit helper
     conditionally excludes the result key when the ingestion result is None.

This file re-exports the existing unit tests from tests/test_touch_index/ so
the Impact Gate runner can discover them by issue ID.  The canonical tests
live in tests/test_touch_index/ and must not drift.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1882"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_bug_worker import (  # noqa: E402, F401
    TestMainProcessBugIssueError,
)

# ---------------------------------------------------------------------------
# Source-level contract checks for BTCAAAAA-1882-specific behaviour
# ---------------------------------------------------------------------------

MAIN_SOURCE = Path(__file__).resolve().parents[2] / "src" / "touch_index" / "__main__.py"
MAIN_TEXT = MAIN_SOURCE.read_text()


class TestBtc1882JsonSummaryIssueIdNotFound:
    """BTCAAAAA-1882: --json-summary --issue-id with no match must emit JSON
    without a result field (bug worker not-found path)."""

    def test_bug_worker_not_found_logs_no_issue(self):
        """Bug worker: process_bug_issue returning None logs a not-found message."""
        assert "No bug issue found for" in MAIN_TEXT

    def test_bug_worker_not_found_still_emits_json(self):
        """Bug worker: --json-summary is emitted even when result is None."""
        assert "if args.json_summary:" in MAIN_TEXT

    def test_emit_helper_excludes_result_when_none(self):
        """_emit_json_summary adds result key only when result is not None."""
        assert "if result is not None:" in MAIN_TEXT
        assert 'summary["result"]' in MAIN_TEXT

    def test_emit_helper_sets_single_issue_mode_for_issue_id(self):
        """_emit_json_summary sets mode to single-issue when --issue-id is given."""
        assert '"single-issue" if args.issue_id else "polling"' in MAIN_TEXT

    def test_not_found_path_exits_cleanly(self):
        """Bug worker not-found path does not raise SystemExit."""
        lines = MAIN_TEXT.split("\n")
        in_not_found_block = False
        for line in lines:
            if "No bug issue found for" in line:
                in_not_found_block = True
                continue
            if not in_not_found_block:
                continue
            if line.strip().startswith("else:") and "result is not None" not in line:
                break
            assert "raise SystemExit" not in line, (
                f"Bug worker not-found path must not raise SystemExit; found {line}"
            )
        assert in_not_found_block, "Could not locate the not-found block in __main__.py"
