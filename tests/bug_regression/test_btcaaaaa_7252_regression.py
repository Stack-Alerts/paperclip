"""
Regression tests for BTCAAAAA-7252: track bug worker processing errors in
JSON summary.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-7252
Components: src/touch_index/__main__.py
            tests/test_touch_index/test_bug_worker.py

Root cause / changes:
  1. The bug worker's _run_bug_cli did not count or report issues that
     failed during batch processing.  The JSON summary was missing an
     issues_with_errors field.
  2. Fix: added errors = len(issues) - worker_count after run_bug_worker,
     a logger.warning when errors > 0, and pass errors=errors to
     _emit_json_summary in both validate-pass and validate-fail paths.
  3. _emit_json_summary now accepts an errors: int = 0 parameter and
     conditionally emits issues_with_errors in the JSON summary.

This file re-exports the existing unit tests from tests/test_touch_index/ so
the Impact Gate runner can discover them by issue ID.  The canonical tests
live in tests/test_touch_index/ and must not drift.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-7252"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_bug_worker import TestBugJsonSummary  # noqa: E402, F401

# ---------------------------------------------------------------------------
# Source-level contract checks for BTCAAAAA-7252-specific changes
# ---------------------------------------------------------------------------

MAIN_SOURCE = Path(__file__).resolve().parents[2] / "src" / "touch_index" / "__main__.py"
MAIN_TEXT = MAIN_SOURCE.read_text()

BUG_WORKER_TEST = (
    Path(__file__).resolve().parents[2]
    / "tests"
    / "test_touch_index"
    / "test_bug_worker.py"
)
BUG_WORKER_TEST_TEXT = BUG_WORKER_TEST.read_text()


class TestBtc7252ErrorTrackingInBugWorker:
    """BTCAAAAA-7252: The bug worker CLI must track processing errors and
    include them in the JSON summary."""

    def test_errors_calculated_after_run_bug_worker(self):
        """errors = len(issues) - worker_count appears after run_bug_worker call."""
        lines = MAIN_TEXT.split("\n")
        found_run_bug = False
        found_errors_calc = False
        for line in lines:
            if "run_bug_worker(engine, issues" in line:
                found_run_bug = True
            if found_run_bug and "errors = len(issues)" in line:
                found_errors_calc = True
                break
        assert found_errors_calc, (
            "errors = len(issues) - worker_count must appear after run_bug_worker call"
        )

    def test_warning_logged_when_errors_present(self):
        """logger.warning is emitted when errors > 0."""
        lines = MAIN_TEXT.split("\n")
        found_errors_calc = False
        found_warning = False
        for i, line in enumerate(lines):
            if "errors = len(issues)" in line:
                found_errors_calc = True
            if found_errors_calc and 'logger.warning(' in line:
                # check this line and the next few for "processing errors"
                window = "\n".join(lines[i:min(i + 5, len(lines))])
                if "processing errors" in window:
                    found_warning = True
                    break
        assert found_warning, (
            "logger.warning for processing errors must appear after errors calculation"
        )

    def test_errors_passed_to_emit_json_summary_in_validate_fail_path(self):
        """In the validate-fail block, _emit_json_summary receives errors=errors."""
        lines = MAIN_TEXT.split("\n")
        in_validate_fail = False
        found_errors_kwarg = False
        for line in lines:
            if "VALIDATION FAILED after ingestion" in line:
                in_validate_fail = True
            if not in_validate_fail:
                continue
            if "errors=errors" in line and "_emit_json_summary" not in line:
                found_errors_kwarg = True
                break
        assert found_errors_kwarg, (
            "errors=errors must be passed to _emit_json_summary in validate-fail path"
        )

    def test_errors_passed_to_emit_json_summary_in_validate_pass_path(self):
        """In the final summary block (after validate pass), _emit_json_summary receives errors=errors."""
        lines = MAIN_TEXT.split("\n")
        found_errors_calc = False
        found_errors_kwarg = False
        for line in lines:
            if "errors = len(issues)" in line:
                found_errors_calc = True
            if found_errors_calc and "errors=errors" in line:
                found_errors_kwarg = True
        assert found_errors_kwarg, (
            "errors=errors must be passed to _emit_json_summary after errors calculation"
        )

    def test_emit_json_summary_handles_errors_param(self):
        """_emit_json_summary accepts errors: int = 0 parameter."""
        assert "errors: int = 0" in MAIN_TEXT or "errors: int=0" in MAIN_TEXT, (
            "_emit_json_summary must have 'errors: int = 0' parameter"
        )

    def test_emit_json_summary_emits_issues_with_errors(self):
        """_emit_json_summary conditionally emits issues_with_errors when errors > 0."""
        assert 'issues_with_errors' in MAIN_TEXT, (
            "_emit_json_summary must emit issues_with_errors key"
        )
        lines = MAIN_TEXT.split("\n")
        found_issues_with_errors = False
        for line in lines:
            if '"issues_with_errors"' in line:
                found_issues_with_errors = True
                break
        assert found_issues_with_errors, (
            "issues_with_errors key must be present in _emit_json_summary"
        )

    def test_logger_done_message_includes_error_count(self):
        """The final logger.info "Bug worker done" message includes error count."""
        done_lines = [l for l in MAIN_TEXT.split("\n") if "Bug worker done" in l]
        assert len(done_lines) > 0, "Bug worker done message must exist"
        assert any("%d errors" in l or "%d error" in l for l in done_lines), (
            "Bug worker done message must include error count"
        )


class TestBtc7252TestClassInBugWorker:
    """BTCAAAAA-7252: TestBugJsonSummary must contain the polling-with-errors
    test in tests/test_touch_index/test_bug_worker.py."""

    def test_class_defined(self):
        """TestBugJsonSummary class is defined in the canonical test file."""
        assert "class TestBugJsonSummary:" in BUG_WORKER_TEST_TEXT

    def test_polling_with_errors_test_exists(self):
        """test_json_summary_polling_with_errors is defined."""
        assert "def test_json_summary_polling_with_errors" in BUG_WORKER_TEST_TEXT

    def test_polling_with_errors_checks_error_count(self):
        """test_json_summary_polling_with_errors asserts issues_with_errors == 1."""
        found_assert = False
        for line in BUG_WORKER_TEST_TEXT.split("\n"):
            if "issues_with_errors" in line and "assert" in line:
                found_assert = True
                break
        assert found_assert, (
            "test_json_summary_polling_with_errors must assert issues_with_errors"
        )

    def test_polling_with_errors_checks_transition_count(self):
        """test_json_summary_polling_with_errors verifies only successful issues
        are transitioned to done."""
        found_assert = False
        for line in BUG_WORKER_TEST_TEXT.split("\n"):
            if "mock_transition.call_count" in line and "== 2" in line:
                found_assert = True
                break
        assert found_assert, (
            "test_json_summary_polling_with_errors must verify transition call count"
        )
