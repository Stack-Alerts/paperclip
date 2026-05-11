"""Unit tests for scripts/run_touch_index_bug_worker.py main() entry point.

All external I/O (DB engine, Paperclip API, sys.exit) is mocked so these
tests run fully offline.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

# Make the scripts directory importable
sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))
sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

import importlib
import types

# Import the runner as a module (it uses __name__ == "__main__" guard only).
# Register it in sys.modules so patch() targets the same object.
runner_path = Path(__file__).parents[2] / "scripts" / "run_touch_index_bug_worker.py"
_spec = importlib.util.spec_from_file_location(
    "run_touch_index_bug_worker", runner_path
)
_runner = importlib.util.module_from_spec(_spec)
sys.modules["run_touch_index_bug_worker"] = _runner
_spec.loader.exec_module(_runner)
main = _runner.main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_engine():
    return MagicMock()


def _make_result(files_indexed: int = 2, skipped: bool = False):
    r = MagicMock()
    r.files_indexed = files_indexed
    r.skipped_no_commits = skipped
    return r


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


_CLEAN_ARGV = ["run_touch_index_bug_worker.py"]


class TestBugRunnerMain:
    def test_db_health_check_failure_exits(self, monkeypatch):
        """When health_check returns False, sys.exit(1) is called."""
        monkeypatch.setattr(sys, "argv", _CLEAN_ARGV)
        with (
            patch("run_touch_index_bug_worker.get_engine", return_value=_make_engine()),
            patch("run_touch_index_bug_worker.health_check", return_value=False),
            patch("run_touch_index_bug_worker.get_closed_non_fdr_issues") as mock_fetch,
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1
        mock_fetch.assert_not_called()

    def test_no_issues_returns_early(self, monkeypatch):
        """When no closed issues are returned, run_bug_worker is never called."""
        monkeypatch.setattr(sys, "argv", _CLEAN_ARGV)
        with (
            patch("run_touch_index_bug_worker.get_engine", return_value=_make_engine()),
            patch("run_touch_index_bug_worker.health_check", return_value=True),
            patch(
                "run_touch_index_bug_worker.get_closed_non_fdr_issues", return_value=[]
            ),
            patch("run_touch_index_bug_worker.run_bug_worker") as mock_worker,
        ):
            main()

        mock_worker.assert_not_called()

    def test_issues_found_calls_run_bug_worker(self, monkeypatch):
        """When issues exist, run_bug_worker is called with engine and the issues."""
        monkeypatch.setattr(sys, "argv", _CLEAN_ARGV)
        issues = [
            {
                "id": "id-1",
                "identifier": "BTCAAAAA-100",
                "completedAt": "2026-05-11T10:00:00Z",
            }
        ]
        engine = _make_engine()

        with (
            patch("run_touch_index_bug_worker.get_engine", return_value=engine),
            patch("run_touch_index_bug_worker.health_check", return_value=True),
            patch(
                "run_touch_index_bug_worker.get_closed_non_fdr_issues",
                return_value=issues,
            ),
            patch(
                "run_touch_index_bug_worker.run_bug_worker",
                return_value=[_make_result()],
            ) as mock_worker,
        ):
            main()

        mock_worker.assert_called_once_with(engine, issues)

    def test_cutoff_is_within_lookback_window(self, monkeypatch):
        """The cutoff passed to get_closed_non_fdr_issues is ~30 min in the past."""
        monkeypatch.setattr(sys, "argv", _CLEAN_ARGV)
        captured = {}

        def _capture_cutoff(closed_after=None):
            captured["cutoff"] = closed_after
            return []

        with (
            patch("run_touch_index_bug_worker.get_engine", return_value=_make_engine()),
            patch("run_touch_index_bug_worker.health_check", return_value=True),
            patch(
                "run_touch_index_bug_worker.get_closed_non_fdr_issues",
                side_effect=_capture_cutoff,
            ),
        ):
            before = datetime.now(timezone.utc)
            main()
            after = datetime.now(timezone.utc)

        cutoff = captured["cutoff"]
        expected_min = before - timedelta(minutes=31)
        expected_max = after - timedelta(minutes=29)
        assert expected_min <= cutoff <= expected_max

    def test_custom_lookback_minutes_arg(self, monkeypatch):
        """--lookback-minutes N overrides the default 30-minute window."""
        monkeypatch.setattr(
            sys, "argv", ["run_touch_index_bug_worker.py", "--lookback-minutes", "60"]
        )
        captured = {}

        def _capture(closed_after=None):
            captured["cutoff"] = closed_after
            return []

        with (
            patch("run_touch_index_bug_worker.get_engine", return_value=_make_engine()),
            patch("run_touch_index_bug_worker.health_check", return_value=True),
            patch(
                "run_touch_index_bug_worker.get_closed_non_fdr_issues",
                side_effect=_capture,
            ),
        ):
            before = datetime.now(timezone.utc)
            main()
            after = datetime.now(timezone.utc)

        cutoff = captured["cutoff"]
        expected_min = before - timedelta(minutes=61)
        expected_max = after - timedelta(minutes=59)
        assert expected_min <= cutoff <= expected_max

    def test_summary_counts_files_and_skipped(self, monkeypatch, caplog):
        """Log summary reflects total files indexed and skipped count."""
        import logging

        monkeypatch.setattr(sys, "argv", _CLEAN_ARGV)
        issues = [
            {
                "id": "id-1",
                "identifier": "BTCAAAAA-101",
                "completedAt": "2026-05-11T10:00:00Z",
            },
            {
                "id": "id-2",
                "identifier": "BTCAAAAA-102",
                "completedAt": "2026-05-11T10:00:00Z",
            },
        ]
        results = [
            _make_result(files_indexed=3, skipped=False),
            _make_result(files_indexed=0, skipped=True),
        ]

        with (
            patch("run_touch_index_bug_worker.get_engine", return_value=_make_engine()),
            patch("run_touch_index_bug_worker.health_check", return_value=True),
            patch(
                "run_touch_index_bug_worker.get_closed_non_fdr_issues",
                return_value=issues,
            ),
            patch("run_touch_index_bug_worker.run_bug_worker", return_value=results),
            caplog.at_level(logging.INFO),
        ):
            main()

        last_log = caplog.records[-1].message
        assert "2 issues" in last_log
        assert "3 files" in last_log
        assert "1 skipped" in last_log
