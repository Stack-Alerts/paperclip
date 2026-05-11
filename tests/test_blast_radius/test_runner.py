"""Unit tests for scripts/run_blast_radius_worker.py main() entry point.

All external I/O (Paperclip API, state persistence) is mocked so these
tests run fully offline.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))
sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

import importlib

runner_path = Path(__file__).parents[2] / "scripts" / "run_blast_radius_worker.py"
_spec = importlib.util.spec_from_file_location("run_blast_radius_worker", runner_path)
_runner = importlib.util.module_from_spec(_spec)
sys.modules["run_blast_radius_worker"] = _runner
_spec.loader.exec_module(_runner)
main = _runner.main

_CLEAN_ARGV = ["run_blast_radius_worker.py"]


class TestRunnerMain:
    def test_default_calls_run_once(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", _CLEAN_ARGV)
        with (
            patch("run_blast_radius_worker.run_once", return_value=[]) as mock_run_once,
        ):
            main()
        mock_run_once.assert_called_once_with(dry_run=False, force_reprocess=False)

    def test_dry_run_flag_passed_to_run_once(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", [_CLEAN_ARGV[0], "--dry-run"])
        with (
            patch("run_blast_radius_worker.run_once", return_value=[]) as mock_run_once,
        ):
            main()
        mock_run_once.assert_called_once_with(dry_run=True, force_reprocess=False)

    def test_loop_flag_calls_run_loop(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", [_CLEAN_ARGV[0], "--loop", "300"])
        with (
            patch("run_blast_radius_worker.run_loop") as mock_run_loop,
            patch("run_blast_radius_worker.logger"),
        ):
            main()
        mock_run_loop.assert_called_once_with(interval_seconds=300, dry_run=False, force_reprocess=False)

    def test_loop_with_dry_run(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", [_CLEAN_ARGV[0], "--loop", "120", "--dry-run"])
        with (
            patch("run_blast_radius_worker.run_loop") as mock_run_loop,
            patch("run_blast_radius_worker.logger"),
        ):
            main()
        mock_run_loop.assert_called_once_with(interval_seconds=120, dry_run=True, force_reprocess=False)

    def test_logs_result_count_on_completion(self, monkeypatch, caplog):
        import logging

        monkeypatch.setattr(sys, "argv", _CLEAN_ARGV)
        results = [{"issue": "BTCAAAAA-100", "dry_run": False}]
        with (
            patch("run_blast_radius_worker.run_once", return_value=results),
            caplog.at_level(logging.INFO),
        ):
            main()
        assert any("1 issue" in r.message for r in caplog.records)

    def test_logs_zero_issues(self, monkeypatch, caplog):
        import logging

        monkeypatch.setattr(sys, "argv", _CLEAN_ARGV)
        with (
            patch("run_blast_radius_worker.run_once", return_value=[]),
            caplog.at_level(logging.INFO),
        ):
            main()
        assert any("0 issue" in r.message for r in caplog.records)
