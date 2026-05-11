"""Unit tests for scripts/blast_radius_cli.py — subcommand dispatch.

All external I/O is mocked so these tests run fully offline.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

# Insert both src/ and scripts/ so the CLI module can be loaded directly.
_SRC = Path(__file__).parents[2] / "src"
_SCRIPTS = Path(__file__).parents[2] / "scripts"
for p in (_SRC, _SCRIPTS):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import importlib

_runner_path = _SCRIPTS / "blast_radius_cli.py"
_spec = importlib.util.spec_from_file_location("blast_radius_cli", _runner_path)
_cli = importlib.util.module_from_spec(_spec)
sys.modules["blast_radius_cli"] = _cli
_spec.loader.exec_module(_cli)

cmd_query = _cli.cmd_query
cmd_generate = _cli.cmd_generate
cmd_worker = _cli.cmd_worker
main = _cli.main


class _FakeArgs:
    """Minimal argparse.Namespace stand-in for direct cmd_* calls."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


# ---------------------------------------------------------------------------
# cmd_query
# ---------------------------------------------------------------------------


class TestCmdQuery:
    def test_calls_query_blast_radius(self, monkeypatch):
        expected = {"fr_impact_set": [], "regression_set": [], "downstream_set": []}
        captured = {"files": None}

        def mock_query(files, engine=None):
            captured["files"] = files
            from blast_radius.query import BlastRadiusData
            return BlastRadiusData()

        def mock_to_json(data):
            return expected

        monkeypatch.setattr("blast_radius.query.query_blast_radius", mock_query)
        monkeypatch.setattr("blast_radius.query.to_json_dict", mock_to_json)

        args = _FakeArgs(files=["src/a.py", "src/b.py"])
        assert cmd_query(args) == 0
        assert captured["files"] == ["src/a.py", "src/b.py"]


# ---------------------------------------------------------------------------
# cmd_generate
# ---------------------------------------------------------------------------


class TestCmdGenerate:
    def test_calls_generate_and_post(self, monkeypatch):
        result = {"issue": "BTCAAAAA-100", "dry_run": True}
        captured = {}

        def mock_gen(issue_id, touched_files=None, dry_run=False):
            captured["issue_id"] = issue_id
            captured["touched_files"] = touched_files
            captured["dry_run"] = dry_run
            return result

        monkeypatch.setattr("blast_radius.generator.generate_and_post", mock_gen)

        args = _FakeArgs(issue_id="uuid-1", files=None, dry_run=True)
        assert cmd_generate(args) == 0
        assert captured["issue_id"] == "uuid-1"
        assert captured["dry_run"] is True

    def test_passes_touched_files(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(
            "blast_radius.generator.generate_and_post",
            lambda issue_id, touched_files=None, dry_run=False: (
                captured.update(issue_id=issue_id, touched_files=touched_files)
            ) or {},
        )

        args = _FakeArgs(issue_id="uuid-1", files=["src/x.py"], dry_run=False)
        cmd_generate(args)
        assert captured["touched_files"] == ["src/x.py"]


# ---------------------------------------------------------------------------
# cmd_worker — polling mode
# ---------------------------------------------------------------------------


class TestCmdWorkerRunOnce:
    def test_default_calls_run_once(self, monkeypatch):
        captured = {}

        def mock_run_once(dry_run=False, force_reprocess=False):
            captured["dry_run"] = dry_run
            captured["force_reprocess"] = force_reprocess
            return []

        monkeypatch.setattr("blast_radius.worker.run_once", mock_run_once)

        args = _FakeArgs(issue_id=None, loop=None, dry_run=False, force_reprocess=False, old_status=None)
        assert cmd_worker(args) == 0
        assert captured["dry_run"] is False
        assert captured["force_reprocess"] is False

    def test_dry_run_flag(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(
            "blast_radius.worker.run_once",
            lambda dry_run=False, force_reprocess=False: (
                captured.update(dry_run=dry_run, force_reprocess=force_reprocess)
            ) or [],
        )

        args = _FakeArgs(issue_id=None, loop=None, dry_run=True, force_reprocess=False, old_status=None)
        cmd_worker(args)
        assert captured["dry_run"] is True

    def test_force_reprocess_flag(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(
            "blast_radius.worker.run_once",
            lambda dry_run=False, force_reprocess=False: (
                captured.update(dry_run=dry_run, force_reprocess=force_reprocess)
            ) or [],
        )

        args = _FakeArgs(issue_id=None, loop=None, dry_run=False, force_reprocess=True, old_status=None)
        cmd_worker(args)
        assert captured["force_reprocess"] is True


class TestCmdWorkerLoop:
    def test_calls_run_loop(self, monkeypatch):
        captured = {}

        def mock_run_loop(interval_seconds=120, dry_run=False, force_reprocess=False):
            captured["interval"] = interval_seconds
            captured["dry_run"] = dry_run
            captured["force_reprocess"] = force_reprocess

        monkeypatch.setattr("blast_radius.worker.run_loop", mock_run_loop)

        args = _FakeArgs(issue_id=None, loop=300, dry_run=False, force_reprocess=False, old_status=None)
        assert cmd_worker(args) == 0
        assert captured["interval"] == 300
        assert captured["dry_run"] is False

    def test_loop_with_dry_run(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(
            "blast_radius.worker.run_loop",
            lambda interval_seconds=120, dry_run=False, force_reprocess=False: (
                captured.update(interval=interval_seconds, dry_run=dry_run)
            ),
        )

        args = _FakeArgs(issue_id=None, loop=120, dry_run=True, force_reprocess=False, old_status=None)
        cmd_worker(args)
        assert captured["dry_run"] is True
        assert captured["interval"] == 120


class TestCmdWorkerIssueId:
    def test_calls_process_issue(self, monkeypatch):
        captured = {}

        def mock_process(issue_id, dry_run=False, old_status=None, force_reprocess=False):
            captured["issue_id"] = issue_id
            captured["dry_run"] = dry_run
            captured["old_status"] = old_status
            captured["force_reprocess"] = force_reprocess
            return {"issue": "BTCAAAAA-100"}

        monkeypatch.setattr("blast_radius.worker.process_issue", mock_process)

        args = _FakeArgs(issue_id="uuid-1", loop=None, dry_run=False, force_reprocess=False, old_status=None)
        assert cmd_worker(args) == 0
        assert captured["issue_id"] == "uuid-1"

    def test_with_old_status(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(
            "blast_radius.worker.process_issue",
            lambda issue_id, dry_run=False, old_status=None, force_reprocess=False: (
                captured.update(issue_id=issue_id, old_status=old_status)
            ) or {"issue": "BTCAAAAA-100"},
        )

        args = _FakeArgs(issue_id="uuid-1", loop=None, dry_run=False, force_reprocess=False, old_status="in_progress")
        cmd_worker(args)
        assert captured["old_status"] == "in_progress"

    def test_with_dry_run(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(
            "blast_radius.worker.process_issue",
            lambda issue_id, dry_run=False, old_status=None, force_reprocess=False: (
                captured.update(issue_id=issue_id, dry_run=dry_run)
            ) or {"issue": "BTCAAAAA-100", "dry_run": True},
        )

        args = _FakeArgs(issue_id="uuid-2", loop=None, dry_run=True, force_reprocess=False, old_status=None)
        cmd_worker(args)
        assert captured["dry_run"] is True

    def test_returns_zero_when_skipped(self, monkeypatch):
        monkeypatch.setattr(
            "blast_radius.worker.process_issue",
            lambda issue_id, dry_run=False, old_status=None, force_reprocess=False: None,
        )

        args = _FakeArgs(issue_id="missing-uuid", loop=None, dry_run=True, force_reprocess=False, old_status=None)
        assert cmd_worker(args) == 0


# ---------------------------------------------------------------------------
# main() — CLI entry point dispatch
# ---------------------------------------------------------------------------


class TestMainDispatch:
    _CLEAN_ARGV = ["blast_radius_cli.py"]

    def test_query_subcommand(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", self._CLEAN_ARGV + ["query", "--files", "src/a.py"])
        with patch("blast_radius_cli.cmd_query", return_value=0) as mock_cmd:
            assert main() == 0
            mock_cmd.assert_called_once()

    def test_generate_subcommand(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", self._CLEAN_ARGV + ["generate", "--issue-id", "uuid-1"])
        with patch("blast_radius_cli.cmd_generate", return_value=0) as mock_cmd:
            main()
            mock_cmd.assert_called_once()

    def test_serve_subcommand(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", self._CLEAN_ARGV + ["serve", "--port", "9000"])
        with patch("blast_radius_cli.cmd_serve", return_value=0) as mock_cmd:
            main()
            mock_cmd.assert_called_once()

    def test_worker_subcommand(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", self._CLEAN_ARGV + ["worker"])
        with patch("blast_radius_cli.cmd_worker", return_value=0) as mock_cmd:
            main()
            mock_cmd.assert_called_once()

    def test_worker_with_issue_id(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", self._CLEAN_ARGV + ["worker", "--issue-id", "uuid-1"])
        with patch("blast_radius_cli.cmd_worker", return_value=0) as mock_cmd:
            main()
            mock_cmd.assert_called_once()

    def test_worker_with_loop(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", self._CLEAN_ARGV + ["worker", "--loop", "60"])
        with patch("blast_radius_cli.cmd_worker", return_value=0) as mock_cmd:
            main()
            mock_cmd.assert_called_once()

    def test_verbose_flag(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", self._CLEAN_ARGV + ["--verbose", "query", "--files", "src/a.py"])
        with patch("blast_radius_cli.cmd_query", return_value=0):
            assert main() == 0
