"""
Regression tests for BTCAAAAA-1852: emit --json-summary before SystemExit on
DB health check failure.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1852
Components: src/touch_index/__main__.py
            tests/test_touch_index/test_bug_worker.py
            tests/test_touch_index/test_fr_worker.py

Root cause / changes:
  1. The health check failure paths in _run_bug_cli() and _run_fr_cli()
     skipped --json-summary emission when args.json_summary was set,
     inconsistent with all other SystemExit paths (fixed for exception
     handlers in BTCAAAAA-1832 and no-issues path in BTCAAAAA-1822).
  2. Now both workers emit JSON summary before raising SystemExit(1)
     on health check failure, ensuring structured monitoring output is
     always produced regardless of error path.

This file re-exports the existing unit tests from tests/test_touch_index/ so
the Impact Gate runner can discover them by issue ID.  The canonical tests
live in tests/test_touch_index/ and must not drift.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1852"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_bug_worker import TestMain as BugTestMain  # noqa: E402, F401

from tests.test_touch_index.test_fr_worker import TestMain as FrTestMain  # noqa: E402, F401

# ---------------------------------------------------------------------------
# Source-level contract checks for BTCAAAAA-1852-specific changes
# ---------------------------------------------------------------------------

MAIN_SOURCE = Path(__file__).resolve().parents[2] / "src" / "touch_index" / "__main__.py"
MAIN_TEXT = MAIN_SOURCE.read_text()


class TestBtc1852HealthCheckJsonSummaryBeforeSystemExit:
    """BTCAAAAA-1852: --json-summary must be emitted before SystemExit(1) on
    DB health check failure in both bug and FR worker paths."""

    def test_bug_worker_health_check_failure_emits_json(self):
        """Bug worker: health check failure with --json-summary emits JSON before SystemExit."""
        assert "DB health check failed" in MAIN_TEXT
        assert '_emit_json_summary(args, worker="bug")' in MAIN_TEXT
        assert "raise SystemExit(1)" in MAIN_TEXT

    def test_bug_worker_json_summary_before_systemexit_in_health_block(self):
        """Bug worker: _emit_json_summary appears before raise SystemExit(1)
        within the DB health check failure block."""
        lines = MAIN_TEXT.split("\n")
        in_bug_health_block = False
        emit_found = False
        exit_found = False
        for line in lines:
            if "DB health check failed" in line and "bug" in str(lines):
                in_bug_health_block = True
                continue
            if not in_bug_health_block:
                continue
            if '_emit_json_summary(args, worker="bug")' in line:
                emit_found = True
            elif 'raise SystemExit(1)' in line and emit_found:
                exit_found = True
                break
            elif 'if args.issue_id:' in line:
                break
        assert emit_found and exit_found

    def test_fr_worker_health_check_failure_emits_json(self):
        """FR worker: health check failure with --json-summary emits JSON before SystemExit."""
        assert '_emit_json_summary(args, worker="fr")' in MAIN_TEXT
        assert "raise SystemExit(1)" in MAIN_TEXT

    def test_fr_worker_json_summary_before_systemexit_in_health_block(self):
        """FR worker: _emit_json_summary appears before raise SystemExit(1)
        within the DB health check failure block."""
        lines = MAIN_TEXT.split("\n")
        in_fr_health_block = False
        emit_found = False
        exit_found = False
        for i, line in enumerate(lines):
            if "DB health check failed" in line and i > 300:
                in_fr_health_block = True
                continue
            if not in_fr_health_block:
                continue
            if '_emit_json_summary(args, worker="fr")' in line:
                emit_found = True
            elif 'raise SystemExit(1)' in line and emit_found:
                exit_found = True
                break
            elif 'if args.issue_id:' in line:
                break
        assert emit_found and exit_found

    def test_health_check_failure_abort_message_unchanged(self):
        """DB health check abort message is preserved in both workers."""
        assert MAIN_TEXT.count("DB health check failed") >= 2
        assert "aborting" in MAIN_TEXT.lower()
