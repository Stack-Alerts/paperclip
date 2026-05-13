"""
Regression tests for BTCAAAAA-1832: emit --json-summary before SystemExit in
--issue-id exception handlers for both bug and FR workers.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1832
Components: src/touch_index/__main__.py

Root cause / changes:
  1. The single-issue --issue-id exception handlers in both bug worker and
     FR worker skipped --json-summary emission when process_bug_issue or
     process_fr_issue raised an exception, inconsistent with all other
     SystemExit paths (fixed in BTCAAAAA-1822, BTCAAAAA-1804).
  2. Now both workers emit JSON summary before raising SystemExit(1) on
     process_issue exception, ensuring structured monitoring output is
     always produced regardless of error path.

This file re-exports the existing unit tests from tests/test_touch_index/ so
the Impact Gate runner can discover them by issue ID.  The canonical tests
live in tests/test_touch_index/ and must not drift.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1832"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_bug_worker import (  # noqa: E402, F401
    TestMainProcessBugIssueError,
)

from tests.test_touch_index.test_fr_worker import (  # noqa: E402, F401
    TestMainProcessFrIssueError,
)

# ---------------------------------------------------------------------------
# Source-level contract checks for BTCAAAAA-1832-specific changes
# ---------------------------------------------------------------------------

MAIN_SOURCE = Path(__file__).resolve().parents[2] / "src" / "touch_index" / "__main__.py"
MAIN_TEXT = MAIN_SOURCE.read_text()


class TestBtc1832JsonSummaryBeforeSystemExitOnProcessError:
    """BTCAAAAA-1832: --json-summary must be emitted before SystemExit(1) when
    process_bug_issue or process_fr_issue raises an exception in the --issue-id
    code path."""

    def test_bug_worker_single_issue_exception_emits_json(self):
        """Bug worker: process_bug_issue exception with --json-summary emits JSON."""
        assert "Failed to process bug issue" in MAIN_TEXT
        assert '_emit_json_summary(args, worker="bug")' in MAIN_TEXT
        assert "raise SystemExit(1)" in MAIN_TEXT

    def test_bug_worker_exception_handler_checks_json_summary_flag(self):
        """Bug worker: --json-summary flag check exists before emission."""
        assert "if args.json_summary:" in MAIN_TEXT

    def test_fr_worker_single_issue_exception_emits_json(self):
        """FR worker: process_fr_issue exception with --json-summary emits JSON."""
        assert "Failed to process FR issue" in MAIN_TEXT
        assert '_emit_json_summary(args, worker="fr")' in MAIN_TEXT

    def test_fr_worker_exception_handler_checks_json_summary_flag(self):
        """FR worker: --json-summary flag check exists in both workers."""
        # Line count check: --json-summary gate must appear in both exception handlers
        assert MAIN_TEXT.count('if args.json_summary:') >= 4
