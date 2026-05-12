"""Unit tests for blast_radius.__main__ — subcommand dispatch and backward compat.

All external I/O is mocked so these tests run fully offline.
"""

from __future__ import annotations

import sys
from unittest.mock import patch

# ---------------------------------------------------------------------------
# __main__ module helpers
# ---------------------------------------------------------------------------

import importlib
from pathlib import Path

_main_path = Path(__file__).parents[2] / "src" / "blast_radius" / "__main__.py"
_spec = importlib.util.spec_from_file_location("blast_radius.__main__", _main_path)
_main = importlib.util.module_from_spec(_spec)
sys.modules["blast_radius.__main__"] = _main
_spec.loader.exec_module(_main)

main = _main.main
cmd_query = _main.cmd_query
cmd_generate = _main.cmd_generate
cmd_serve = _main.cmd_serve


class _FakeArgs:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        if not hasattr(self, "json_summary"):
            self.json_summary = False


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
# cmd_serve
# ---------------------------------------------------------------------------


class TestCmdServe:
    def test_calls_serve(self, monkeypatch):
        captured = {"port": None}

        def mock_serve(port=8765):
            captured["port"] = port

        monkeypatch.setattr("blast_radius.api_server.serve", mock_serve)
        args = _FakeArgs(port=9000)
        assert cmd_serve(args) == 0
        assert captured["port"] == 9000


# ---------------------------------------------------------------------------
# main() — subcommand dispatch
# ---------------------------------------------------------------------------


class TestMainDispatch:
    _CLEAN_ARGV = ["blast_radius"]

    def test_query_subcommand(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", self._CLEAN_ARGV + ["query", "--files", "src/a.py"])
        with patch("blast_radius.__main__.cmd_query", return_value=0) as mock_cmd:
            assert main() == 0
            mock_cmd.assert_called_once()

    def test_generate_subcommand(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", self._CLEAN_ARGV + ["generate", "--issue-id", "uuid-1"])
        with patch("blast_radius.__main__.cmd_generate", return_value=0) as mock_cmd:
            main()
            mock_cmd.assert_called_once()

    def test_serve_subcommand(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", self._CLEAN_ARGV + ["serve", "--port", "9000"])
        with patch("blast_radius.__main__.cmd_serve", return_value=0) as mock_cmd:
            main()
            mock_cmd.assert_called_once()

    def test_worker_subcommand(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", self._CLEAN_ARGV + ["worker"])
        with patch("blast_radius.__main__._run_worker_cli", return_value=0) as mock_cmd:
            main()
            mock_cmd.assert_called_once()

    def test_worker_with_issue_id(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", self._CLEAN_ARGV + ["worker", "--issue-id", "uuid-1"])
        with patch("blast_radius.__main__._run_worker_cli", return_value=0) as mock_cmd:
            main()
            mock_cmd.assert_called_once()

    def test_worker_with_loop(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", self._CLEAN_ARGV + ["worker", "--loop", "60"])
        with patch("blast_radius.__main__._run_worker_cli", return_value=0) as mock_cmd:
            main()
            mock_cmd.assert_called_once()

    def test_verbose_flag(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", self._CLEAN_ARGV + ["--verbose", "query", "--files", "src/a.py"])
        with patch("blast_radius.__main__.cmd_query", return_value=0):
            assert main() == 0


# ---------------------------------------------------------------------------
# main() — backward-compat flat-args mode
# ---------------------------------------------------------------------------


class TestMainFlatArgs:
    def test_default_calls_run_once(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["blast_radius"])
        with patch("blast_radius.__main__._run_worker_cli", return_value=0) as mock_cmd:
            main()
            mock_cmd.assert_called_once()

    def test_dry_run_passes_through(self, monkeypatch):
        captured = {}

        def mock_worker(args):
            captured["dry_run"] = args.dry_run
            return 0

        monkeypatch.setattr(sys, "argv", ["blast_radius", "--dry-run"])
        with patch("blast_radius.__main__._run_worker_cli", side_effect=mock_worker) as mock_cmd:
            main()
        assert captured.get("dry_run") is True

    def test_issue_id_passes_through(self, monkeypatch):
        captured = {}

        def mock_worker(args):
            captured["issue_id"] = args.issue_id
            return 0

        monkeypatch.setattr(sys, "argv", ["blast_radius", "--issue-id", "uuid-1"])
        with patch("blast_radius.__main__._run_worker_cli", side_effect=mock_worker) as mock_cmd:
            main()
        assert captured.get("issue_id") == "uuid-1"

    def test_loop_passes_through(self, monkeypatch):
        captured = {}

        def mock_worker(args):
            captured["loop"] = args.loop
            return 0

        monkeypatch.setattr(sys, "argv", ["blast_radius", "--loop", "300"])
        with patch("blast_radius.__main__._run_worker_cli", side_effect=mock_worker) as mock_cmd:
            main()
        assert captured.get("loop") == 300

    def test_force_reprocess_passes_through(self, monkeypatch):
        captured = {}

        def mock_worker(args):
            captured["force_reprocess"] = args.force_reprocess
            return 0

        monkeypatch.setattr(sys, "argv", ["blast_radius", "--force-reprocess"])
        with patch("blast_radius.__main__._run_worker_cli", side_effect=mock_worker) as mock_cmd:
            main()
        assert captured.get("force_reprocess") is True

    def test_old_status_passes_through(self, monkeypatch):
        captured = {}

        def mock_worker(args):
            captured["old_status"] = args.old_status
            return 0

        monkeypatch.setattr(sys, "argv", ["blast_radius", "--issue-id", "uuid-1", "--old-status", "in_progress"])
        with patch("blast_radius.__main__._run_worker_cli", side_effect=mock_worker) as mock_cmd:
            main()
        assert captured.get("old_status") == "in_progress"

    def test_verbose_flag_flat_mode(self, monkeypatch):
        captured = {}

        def mock_worker(args):
            captured["verbose"] = getattr(args, "verbose", None)
            return 0

        monkeypatch.setattr(sys, "argv", ["blast_radius", "--verbose", "--dry-run"])
        with patch("blast_radius.__main__._run_worker_cli", side_effect=mock_worker) as mock_cmd:
            main()
        assert captured.get("verbose") is True

    def test_json_summary_passes_through(self, monkeypatch):
        captured = {}

        def mock_worker(args):
            captured["json_summary"] = args.json_summary
            return 0

        monkeypatch.setattr(sys, "argv", ["blast_radius", "--json-summary"])
        with patch("blast_radius.__main__._run_worker_cli", side_effect=mock_worker) as mock_cmd:
            main()
        assert captured.get("json_summary") is True


# ---------------------------------------------------------------------------
# _run_worker_cli — worker subcommand dispatch
# ---------------------------------------------------------------------------


class TestRunWorkerCli:
    def test_run_once_default(self):
        with patch("blast_radius.worker.run_once", return_value=[]):
            args = _FakeArgs(issue_id=None, loop=None, dry_run=False, force_reprocess=False, old_status=None)
            assert _main._run_worker_cli(args) == 0

    def test_issue_id_calls_process_issue(self):
        with patch("blast_radius.worker.process_issue", return_value={"ok": True}) as mock_process:
            args = _FakeArgs(issue_id="uuid-1", loop=None, dry_run=False, force_reprocess=False, old_status=None)
            assert _main._run_worker_cli(args) == 0
            mock_process.assert_called_once_with("uuid-1", dry_run=False, old_status=None, force_reprocess=False)

    def test_issue_id_skipped_prints_message(self, capsys):
        with patch("blast_radius.worker.process_issue", return_value=None):
            args = _FakeArgs(issue_id="uuid-1", loop=None, dry_run=False, force_reprocess=False, old_status=None)
            assert _main._run_worker_cli(args) == 0
            captured = capsys.readouterr()
            assert "skipped" in captured.out

    def test_loop_calls_run_loop(self):
        with patch("blast_radius.worker.run_loop") as mock_loop:
            args = _FakeArgs(issue_id=None, loop=300, dry_run=False, force_reprocess=False, old_status=None)
            assert _main._run_worker_cli(args) == 0
            mock_loop.assert_called_once_with(interval_seconds=300, dry_run=False, force_reprocess=False)


# ---------------------------------------------------------------------------
# --json-summary
# ---------------------------------------------------------------------------


class TestJsonSummary:
    def test_json_summary_single_issue(self, monkeypatch, capsys):
        import json
        with patch("blast_radius.worker.process_issue", return_value={"ok": True, "issue": "BTCAAAAA-100"}):
            monkeypatch.setattr("sys.argv", ["blast_radius", "--issue-id", "uuid-1", "--json-summary"])
            assert main() == 0

        captured = capsys.readouterr()
        data = json.loads(captured.out.strip())
        assert data["worker"] == "blast-radius"
        assert data["mode"] == "single-issue"
        assert data["result"]["ok"] is True

    def test_json_summary_polling(self, monkeypatch, capsys):
        import json
        with patch("blast_radius.worker.run_once", return_value=[{"ok": True}, {"ok": True}]):
            monkeypatch.setattr("sys.argv", ["blast_radius", "--json-summary"])
            assert main() == 0

        captured = capsys.readouterr()
        data = json.loads(captured.out.strip())
        assert data["worker"] == "blast-radius"
        assert data["mode"] == "polling"
        assert data["issues_processed"] == 2
        assert data["issues_with_errors"] == 0

    def test_json_summary_polling_with_errors(self, monkeypatch, capsys):
        import json
        results = [
            {"ok": True},
            {"error": "API timeout", "issue": "BTCAAAAA-100"},
        ]
        with patch("blast_radius.worker.run_once", return_value=results):
            monkeypatch.setattr("sys.argv", ["blast_radius", "--json-summary"])
            assert main() == 0

        captured = capsys.readouterr()
        data = json.loads(captured.out.strip())
        assert data["issues_with_errors"] == 1

    def test_json_summary_dry_run(self, monkeypatch, capsys):
        import json
        with patch("blast_radius.worker.run_once", return_value=[{"ok": True, "dry_run": True}]):
            monkeypatch.setattr("sys.argv", ["blast_radius", "--json-summary", "--dry-run"])
            assert main() == 0

        captured = capsys.readouterr()
        data = json.loads(captured.out.strip())
        assert data["dry_run"] is True

    def test_json_summary_no_results(self, monkeypatch, capsys):
        import json
        with patch("blast_radius.worker.run_once", return_value=[]):
            monkeypatch.setattr("sys.argv", ["blast_radius", "--json-summary"])
            assert main() == 0

        captured = capsys.readouterr()
        data = json.loads(captured.out.strip())
        assert data["issues_processed"] == 0
        assert data["issues_with_errors"] == 0

    def test_json_summary_worker_subcommand(self, monkeypatch, capsys):
        import json
        with patch("blast_radius.worker.process_issue", return_value={"ok": True}):
            monkeypatch.setattr("sys.argv", ["blast_radius", "worker", "--issue-id", "uuid-1", "--json-summary"])
            assert main() == 0

        captured = capsys.readouterr()
        data = json.loads(captured.out.strip())
        assert data["worker"] == "blast-radius"
        assert data["mode"] == "single-issue"

    def test_json_summary_worker_subcommand_polling(self, monkeypatch, capsys):
        import json
        with patch("blast_radius.worker.run_once", return_value=[{"ok": True}]):
            monkeypatch.setattr("sys.argv", ["blast_radius", "worker", "--json-summary"])
            assert main() == 0

        captured = capsys.readouterr()
        data = json.loads(captured.out.strip())
        assert data["worker"] == "blast-radius"
        assert data["mode"] == "polling"
        assert data["issues_processed"] == 1

    def test_json_summary_single_issue_not_found(self, monkeypatch, capsys):
        """--json-summary --issue-id when no match outputs skipped result."""
        import json
        with patch("blast_radius.worker.process_issue", return_value=None):
            monkeypatch.setattr("sys.argv", ["blast_radius", "--issue-id", "missing-uuid", "--json-summary"])
            assert main() == 0

        captured = capsys.readouterr()
        data = json.loads(captured.out.strip())
        assert data["worker"] == "blast-radius"
        assert data["mode"] == "single-issue"
        assert data["result"] == {"skipped": True, "issue": "missing-uuid"}
