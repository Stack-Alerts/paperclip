"""Unit tests for blast_radius.__main__ CLI.

All subcommands (worker, query, generate, serve) are tested via argv patching.
"""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _preserve_argv():
    orig = sys.argv.copy()
    yield
    sys.argv = orig


# ---------------------------------------------------------------------------
# TestRunWorkerCli
# ---------------------------------------------------------------------------


class TestRunWorkerCli:
    def test_default_runs_worker_once(self):
        with (
            patch.object(sys, "argv", ["blast-radius"]),
            patch("blast_radius.worker.run_once", return_value=[]) as mock_run_once,
        ):
            from blast_radius.__main__ import main
            result = main()
        assert result == 0
        mock_run_once.assert_called_once()

    def test_worker_subcommand_runs_once(self):
        with (
            patch.object(sys, "argv", ["blast-radius", "worker"]),
            patch("blast_radius.worker.run_once", return_value=[]) as mock_run_once,
        ):
            from blast_radius.__main__ import main
            result = main()
        assert result == 0
        mock_run_once.assert_called_once()

    def test_worker_with_dry_run(self):
        with (
            patch.object(sys, "argv", ["blast-radius", "worker", "--dry-run"]),
            patch("blast_radius.worker.run_once", return_value=[]) as mock_run_once,
        ):
            from blast_radius.__main__ import main
            result = main()
        assert result == 0
        kwargs = mock_run_once.call_args.kwargs
        assert kwargs.get("dry_run") is True

    def test_worker_with_force_reprocess(self):
        with (
            patch.object(sys, "argv", ["blast-radius", "worker", "--force-reprocess"]),
            patch("blast_radius.worker.run_once", return_value=[]) as mock_run_once,
        ):
            from blast_radius.__main__ import main
            result = main()
        assert result == 0
        kwargs = mock_run_once.call_args.kwargs
        assert kwargs.get("force_reprocess") is True

    def test_worker_with_issue_id(self):
        with (
            patch.object(sys, "argv", ["blast-radius", "worker", "--issue-id", "uuid-123"]),
            patch("blast_radius.worker.process_issue", return_value={}) as mock_proc,
        ):
            from blast_radius.__main__ import main
            result = main()
        assert result == 0
        mock_proc.assert_called_once()
        args, kwargs = mock_proc.call_args
        assert args[0] == "uuid-123"

    def test_worker_with_issue_id_and_old_status(self):
        with (
            patch.object(sys, "argv", [
                "blast-radius", "worker",
                "--issue-id", "uuid-123",
                "--old-status", "in_progress",
            ]),
            patch("blast_radius.worker.process_issue", return_value={}) as mock_proc,
        ):
            from blast_radius.__main__ import main
            result = main()
        assert result == 0
        kwargs = mock_proc.call_args.kwargs
        assert kwargs.get("old_status") == "in_progress"

    def test_worker_with_loop(self):
        with (
            patch.object(sys, "argv", ["blast-radius", "worker", "--loop", "60"]),
            patch("blast_radius.worker.run_loop") as mock_loop,
        ):
            from blast_radius.__main__ import main
            result = main()
        assert result == 0
        kwargs = mock_loop.call_args.kwargs
        assert kwargs.get("interval_seconds") == 60

    def test_flat_dry_run_backward_compat(self):
        with (
            patch.object(sys, "argv", ["blast-radius", "--dry-run"]),
            patch("blast_radius.worker.run_once", return_value=[]) as mock_run_once,
        ):
            from blast_radius.__main__ import main
            result = main()
        assert result == 0
        kwargs = mock_run_once.call_args.kwargs
        assert kwargs.get("dry_run") is True

    def test_flat_issue_id_backward_compat(self):
        with (
            patch.object(sys, "argv", ["blast-radius", "--issue-id", "uuid-456"]),
            patch("blast_radius.worker.process_issue", return_value={}) as mock_proc,
        ):
            from blast_radius.__main__ import main
            result = main()
        assert result == 0
        args, kwargs = mock_proc.call_args
        assert args[0] == "uuid-456"

    def test_multiple_workers_not_run_in_parallel(self):
        with (
            patch.object(sys, "argv", ["blast-radius", "worker"]),
            patch("blast_radius.worker.run_once", return_value=[]) as mock_run_once,
            patch("blast_radius.worker.run_loop") as mock_loop,
            patch("blast_radius.worker.process_issue") as mock_proc,
        ):
            from blast_radius.__main__ import main
            result = main()
        assert result == 0
        mock_run_once.assert_called_once()
        mock_loop.assert_not_called()
        mock_proc.assert_not_called()


# ---------------------------------------------------------------------------
# TestQuerySubcommand
# ---------------------------------------------------------------------------


class TestQuerySubcommand:
    def test_query_calls_query_blast_radius(self):
        with (
            patch.object(sys, "argv", [
                "blast-radius", "query", "--files", "src/a.py", "src/b.py",
            ]),
            patch("blast_radius.query.query_blast_radius") as mock_query,
            patch("blast_radius.query.to_json_dict", return_value={}),
        ):
            from blast_radius.__main__ import main
            result = main()
        assert result == 0
        args, kwargs = mock_query.call_args
        assert list(args[0]) == ["src/a.py", "src/b.py"]

    def test_query_requires_files(self):
        with (
            patch.object(sys, "argv", ["blast-radius", "query"]),
        ):
            from blast_radius.__main__ import main
            with pytest.raises(SystemExit):
                main()


# ---------------------------------------------------------------------------
# TestGenerateSubcommand
# ---------------------------------------------------------------------------


class TestGenerateSubcommand:
    def test_generate_calls_generate_and_post(self):
        with (
            patch.object(sys, "argv", [
                "blast-radius", "generate", "--issue-id", "uuid-gen",
            ]),
            patch("blast_radius.generator.generate_and_post", return_value={}) as mock_gen,
        ):
            from blast_radius.__main__ import main
            result = main()
        assert result == 0
        args, kwargs = mock_gen.call_args
        assert kwargs.get("issue_id") == "uuid-gen"

    def test_generate_with_dry_run(self):
        with (
            patch.object(sys, "argv", [
                "blast-radius", "generate", "--issue-id", "uuid-gen", "--dry-run",
            ]),
            patch("blast_radius.generator.generate_and_post", return_value={}) as mock_gen,
        ):
            from blast_radius.__main__ import main
            result = main()
        assert result == 0
        kwargs = mock_gen.call_args.kwargs
        assert kwargs.get("dry_run") is True

    def test_generate_with_files_override(self):
        with (
            patch.object(sys, "argv", [
                "blast-radius", "generate", "--issue-id", "uuid-gen",
                "--files", "src/c.py",
            ]),
            patch("blast_radius.generator.generate_and_post", return_value={}) as mock_gen,
        ):
            from blast_radius.__main__ import main
            result = main()
        assert result == 0
        kwargs = mock_gen.call_args.kwargs
        assert kwargs.get("touched_files") == ["src/c.py"]


# ---------------------------------------------------------------------------
# TestServeSubcommand
# ---------------------------------------------------------------------------


class TestServeSubcommand:
    def test_serve_starts_server(self):
        with (
            patch.object(sys, "argv", ["blast-radius", "serve"]),
            patch("blast_radius.api_server.serve") as mock_serve,
        ):
            from blast_radius.__main__ import main
            result = main()
        assert result == 0
        mock_serve.assert_called_once()

    def test_serve_with_custom_port(self):
        with (
            patch.object(sys, "argv", ["blast-radius", "serve", "--port", "9999"]),
            patch("blast_radius.api_server.serve") as mock_serve,
        ):
            from blast_radius.__main__ import main
            result = main()
        assert result == 0
        kwargs = mock_serve.call_args.kwargs
        assert kwargs.get("port") == 9999


# ---------------------------------------------------------------------------
# TestJsonSummary
# ---------------------------------------------------------------------------


class TestJsonSummary:
    def test_json_summary_flag_emits_json(self, capsys):
        with (
            patch.object(sys, "argv", [
                "blast-radius", "worker", "--json-summary",
            ]),
            patch("blast_radius.worker.run_once", return_value=[]),
        ):
            from blast_radius.__main__ import main
            result = main()
        assert result == 0
        captured = capsys.readouterr()
        assert '"worker": "blast-radius"' in captured.out
        assert '"mode": "polling"' in captured.out

    def test_json_summary_with_issue_id(self, capsys):
        with (
            patch.object(sys, "argv", [
                "blast-radius", "worker", "--issue-id", "uuid-json", "--json-summary",
            ]),
            patch("blast_radius.worker.process_issue", return_value={"skipped": False}),
        ):
            from blast_radius.__main__ import main
            result = main()
        assert result == 0
        captured = capsys.readouterr()
        assert '"mode": "single-issue"' in captured.out

    def test_json_summary_with_skipped_issue(self, capsys):
        with (
            patch.object(sys, "argv", [
                "blast-radius", "worker", "--issue-id", "uuid-skip", "--json-summary",
            ]),
            patch("blast_radius.worker.process_issue", return_value=None),
        ):
            from blast_radius.__main__ import main
            result = main()
        assert result == 0
        captured = capsys.readouterr()
        assert '"skipped"' in captured.out

    def test_verbose_flag_enables_debug(self):
        with (
            patch.object(sys, "argv", ["blast-radius", "-v"]),
            patch("blast_radius.worker.run_once", return_value=[]),
            patch("blast_radius.__main__.logging.basicConfig") as mock_log,
        ):
            from blast_radius.__main__ import main
            result = main()
        assert result == 0
        kwargs = mock_log.call_args.kwargs
        assert kwargs.get("level") == 10  # DEBUG

