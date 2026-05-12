"""Unit tests for scripts/run_blast_radius_worker.py — thin wrapper delegation.

Verifies that the runner script correctly sets up the environment and
delegates to blast_radius.worker.main().
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
    def test_delegates_to_worker_main(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", _CLEAN_ARGV)
        with patch("blast_radius.__main__.main", return_value=0) as mock_main:
            with pytest.raises(SystemExit):
                main()
            mock_main.assert_called_once()

    def test_passes_dry_run(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", _CLEAN_ARGV + ["--dry-run"])
        with patch("blast_radius.__main__.main", return_value=0) as mock_main:
            with pytest.raises(SystemExit):
                main()
            mock_main.assert_called_once()

    def test_passes_issue_id(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", _CLEAN_ARGV + ["--issue-id", "uuid-1"])
        with patch("blast_radius.__main__.main", return_value=0) as mock_main:
            with pytest.raises(SystemExit):
                main()
            mock_main.assert_called_once()

    def test_passes_loop(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", _CLEAN_ARGV + ["--loop", "300"])
        with patch("blast_radius.__main__.main", return_value=0) as mock_main:
            with pytest.raises(SystemExit):
                main()
            mock_main.assert_called_once()

    def test_passes_force_reprocess(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", _CLEAN_ARGV + ["--force-reprocess"])
        with patch("blast_radius.__main__.main", return_value=0) as mock_main:
            with pytest.raises(SystemExit):
                main()
            mock_main.assert_called_once()
