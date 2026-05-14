"""Unit tests for scripts/nightly_test_alert.py — Paperclip alert on nightly CI test failure.

Tests cover the alert-creation payload (workflow name, run URL, test output),
dry-run mode, error handling, and the main() orchestration function.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

pytestmark = [pytest.mark.bug("BTCAAAAA-26496"), pytest.mark.regression]

DUMMY_BASE = "https://api.test"
DUMMY_COMPANY = "test-co"


def _make_mock_sess(post_return=None):
    mock_sess = MagicMock()
    if post_return is not None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = post_return
        mock_sess.post.return_value = mock_resp
    return mock_sess


def _patch_setup(monkeypatch, mock_sess):
    monkeypatch.setattr(
        "scripts.nightly_test_alert._setup_session",
        lambda: (mock_sess, DUMMY_BASE, DUMMY_COMPANY),
    )


class TestCreateAlert:
    def test_dry_run_logs_and_returns_true(self, monkeypatch, capsys):
        from scripts.nightly_test_alert import create_alert, CTO_AGENT_ID, ALERT_LABEL

        _patch_setup(monkeypatch, MagicMock())
        result = create_alert(
            DUMMY_BASE, DUMMY_COMPANY, MagicMock(),
            workflow="Test and Coverage",
            run_id="12345",
            run_url="https://github.com/owner/repo/actions/runs/12345",
            test_output=None,
            dry_run=True,
        )
        assert result is True
        captured = capsys.readouterr().out
        payload = json.loads(captured)
        assert payload["priority"] == "critical"
        assert payload["assigneeAgentId"] == CTO_AGENT_ID
        assert ALERT_LABEL in payload["labels"]
        assert "Test and Coverage" in payload["title"]
        assert "Test and Coverage" in payload["description"]

    def test_dry_run_includes_test_output(self, monkeypatch, capsys):
        from scripts.nightly_test_alert import create_alert

        _patch_setup(monkeypatch, MagicMock())
        result = create_alert(
            DUMMY_BASE, DUMMY_COMPANY, MagicMock(),
            workflow="Walkforward Validation",
            run_id="67890",
            run_url="https://github.com/owner/repo/actions/runs/67890",
            test_output="FAILED test_something.py::test_case - assert 1 == 2",
            dry_run=True,
        )
        assert result is True
        captured = capsys.readouterr().out
        payload = json.loads(captured)
        assert "FAILED test_something.py" in payload["description"]

    def test_dry_run_truncates_long_test_output(self, monkeypatch, capsys):
        from scripts.nightly_test_alert import create_alert

        _patch_setup(monkeypatch, MagicMock())
        long_output = "x" * 6000
        result = create_alert(
            DUMMY_BASE, DUMMY_COMPANY, MagicMock(),
            workflow="Test and Coverage",
            run_id="12345",
            run_url="https://github.com/owner/repo/actions/runs/12345",
            test_output=long_output,
            dry_run=True,
        )
        assert result is True
        captured = capsys.readouterr().out
        payload = json.loads(captured)
        assert len(payload["description"]) <= 5500
        assert long_output[:5000] in payload["description"]

    def test_creates_alert_on_failure(self, monkeypatch):
        from scripts.nightly_test_alert import create_alert

        mock_sess = _make_mock_sess(
            post_return={"identifier": "BTCAAAAA-999", "id": "uuid-99"},
        )
        result = create_alert(
            DUMMY_BASE, DUMMY_COMPANY, mock_sess,
            workflow="Test and Coverage",
            run_id="12345",
            run_url="https://github.com/owner/repo/actions/runs/12345",
            test_output="FAILED test_foo.py::test_bar",
            dry_run=False,
        )
        assert result is True
        assert mock_sess.post.call_count == 1

        call_args = mock_sess.post.call_args
        assert call_args[0][0] == "https://api.test/api/companies/test-co/issues"

        payload = call_args[1]["json"]
        assert payload["priority"] == "critical"
        assert payload["status"] == "todo"
        assert "nightly-alert" in payload["labels"]
        assert "Test and Coverage" in payload["title"]
        assert "12345" in payload["description"]
        assert "https://github.com/owner/repo/actions/runs/12345" in payload["description"]
        assert "FAILED test_foo.py::test_bar" in payload["description"]

    def test_creates_alert_without_test_output(self, monkeypatch):
        from scripts.nightly_test_alert import create_alert

        mock_sess = _make_mock_sess(
            post_return={"identifier": "BTCAAAAA-999", "id": "uuid-99"},
        )
        result = create_alert(
            DUMMY_BASE, DUMMY_COMPANY, mock_sess,
            workflow="Test and Coverage",
            run_id="12345",
            run_url="https://github.com/owner/repo/actions/runs/12345",
            test_output=None,
            dry_run=False,
        )
        assert result is True
        payload = mock_sess.post.call_args[1]["json"]
        assert "### Test Output" not in payload["description"]

    def test_body_includes_workflow_name(self, monkeypatch):
        from scripts.nightly_test_alert import create_alert

        mock_sess = _make_mock_sess(
            post_return={"identifier": "BTCAAAAA-999", "id": "uuid-99"},
        )
        create_alert(
            DUMMY_BASE, DUMMY_COMPANY, mock_sess,
            workflow="Walkforward Validation",
            run_id="67890",
            run_url="https://github.com/owner/repo/actions/runs/67890",
            test_output=None,
            dry_run=False,
        )
        payload = mock_sess.post.call_args[1]["json"]
        assert "Walkforward Validation" in payload["title"]
        assert "`Walkforward Validation`" in payload["description"]

    def test_body_includes_run_url(self, monkeypatch):
        from scripts.nightly_test_alert import create_alert

        mock_sess = _make_mock_sess(
            post_return={"identifier": "BTCAAAAA-999", "id": "uuid-99"},
        )
        run_url = "https://github.com/owner/repo/actions/runs/67890"
        create_alert(
            DUMMY_BASE, DUMMY_COMPANY, mock_sess,
            workflow="Test and Coverage",
            run_id="67890",
            run_url=run_url,
            test_output=None,
            dry_run=False,
        )
        payload = mock_sess.post.call_args[1]["json"]
        assert run_url in payload["description"]

    def test_body_includes_date(self, monkeypatch):
        from scripts.nightly_test_alert import create_alert

        mock_sess = _make_mock_sess(
            post_return={"identifier": "BTCAAAAA-999", "id": "uuid-99"},
        )
        create_alert(
            DUMMY_BASE, DUMMY_COMPANY, mock_sess,
            workflow="Test and Coverage",
            run_id="12345",
            run_url="https://github.com/owner/repo/actions/runs/12345",
            test_output=None,
            dry_run=False,
        )
        payload = mock_sess.post.call_args[1]["json"]
        assert payload["title"].startswith("Nightly CI Test Failure — ")

    def test_returns_false_on_api_error(self, monkeypatch):
        from scripts.nightly_test_alert import create_alert

        mock_sess = MagicMock()
        mock_sess.post.side_effect = ConnectionError("network down")
        result = create_alert(
            DUMMY_BASE, DUMMY_COMPANY, mock_sess,
            workflow="Test and Coverage",
            run_id="12345",
            run_url="https://github.com/owner/repo/actions/runs/12345",
            test_output=None,
            dry_run=False,
        )
        assert result is False

    def test_returns_false_on_http_error(self, monkeypatch):
        from scripts.nightly_test_alert import create_alert

        mock_sess = MagicMock()
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = IOError("HTTP 500")
        mock_sess.post.return_value = mock_resp
        result = create_alert(
            DUMMY_BASE, DUMMY_COMPANY, mock_sess,
            workflow="Test and Coverage",
            run_id="12345",
            run_url="https://github.com/owner/repo/actions/runs/12345",
            test_output=None,
            dry_run=False,
        )
        assert result is False

    def test_assigns_cto_agent(self, monkeypatch):
        from scripts.nightly_test_alert import create_alert, CTO_AGENT_ID

        mock_sess = _make_mock_sess(
            post_return={"identifier": "BTCAAAAA-999", "id": "uuid-99"},
        )
        create_alert(
            DUMMY_BASE, DUMMY_COMPANY, mock_sess,
            workflow="Test and Coverage",
            run_id="12345",
            run_url="https://github.com/owner/repo/actions/runs/12345",
            test_output=None,
            dry_run=False,
        )
        payload = mock_sess.post.call_args[1]["json"]
        assert payload["assigneeAgentId"] == CTO_AGENT_ID

    def test_test_output_included_in_body(self, monkeypatch):
        from scripts.nightly_test_alert import create_alert

        mock_sess = _make_mock_sess(
            post_return={"identifier": "BTCAAAAA-999", "id": "uuid-99"},
        )
        output = "FAILED tests/test_foo.py::test_bar - assert 1 == 2"
        create_alert(
            DUMMY_BASE, DUMMY_COMPANY, mock_sess,
            workflow="Test and Coverage",
            run_id="12345",
            run_url="https://github.com/owner/repo/actions/runs/12345",
            test_output=output,
            dry_run=False,
        )
        payload = mock_sess.post.call_args[1]["json"]
        assert "### Test Output" in payload["description"]
        assert output in payload["description"]

    def test_timeout_set_on_post(self, monkeypatch):
        from scripts.nightly_test_alert import create_alert

        mock_sess = _make_mock_sess(
            post_return={"identifier": "BTCAAAAA-999", "id": "uuid-99"},
        )
        create_alert(
            DUMMY_BASE, DUMMY_COMPANY, mock_sess,
            workflow="Test and Coverage",
            run_id="12345",
            run_url="https://github.com/owner/repo/actions/runs/12345",
            test_output=None,
            dry_run=False,
        )
        assert mock_sess.post.call_args[1]["timeout"] == 30

    def test_auto_generated_footer(self, monkeypatch):
        from scripts.nightly_test_alert import create_alert

        mock_sess = _make_mock_sess(
            post_return={"identifier": "BTCAAAAA-999", "id": "uuid-99"},
        )
        create_alert(
            DUMMY_BASE, DUMMY_COMPANY, mock_sess,
            workflow="Test and Coverage",
            run_id="12345",
            run_url="https://github.com/owner/repo/actions/runs/12345",
            test_output=None,
            dry_run=False,
        )
        payload = mock_sess.post.call_args[1]["json"]
        assert "Auto-generated by nightly CI pipeline" in payload["description"]


class TestMain:
    def _setup_env(self, monkeypatch):
        monkeypatch.setenv("PAPERCLIP_API_URL", "https://api.test")
        monkeypatch.setenv("PAPERCLIP_API_KEY", "test-key")
        monkeypatch.setenv("PAPERCLIP_COMPANY_ID", "test-co")

    def test_main_dry_run(self, monkeypatch, capsys):
        from scripts.nightly_test_alert import main

        self._setup_env(monkeypatch)
        _patch_setup(monkeypatch, MagicMock())
        monkeypatch.setattr(
            "sys.argv",
            [
                "nightly_test_alert.py",
                "--workflow", "Test and Coverage",
                "--run-id", "12345",
                "--run-url", "https://github.com/owner/repo/actions/runs/12345",
                "--dry-run",
            ],
        )

        main()
        captured = capsys.readouterr().out
        payload = json.loads(captured)
        assert payload["priority"] == "critical"
        assert "Test and Coverage" in payload["title"]

    def test_main_with_test_output_file(self, monkeypatch, tmp_path):
        from scripts.nightly_test_alert import main

        self._setup_env(monkeypatch)
        output_file = tmp_path / "test-output.txt"
        output_file.write_text("FAILED test_something.py::test_case")

        mock_sess = _make_mock_sess(
            post_return={"identifier": "BTCAAAAA-999", "id": "uuid-99"},
        )
        _patch_setup(monkeypatch, mock_sess)
        monkeypatch.setattr(
            "sys.argv",
            [
                "nightly_test_alert.py",
                "--workflow", "Test and Coverage",
                "--run-id", "12345",
                "--run-url", "https://github.com/owner/repo/actions/runs/12345",
                "--test-output", str(output_file),
            ],
        )

        main()
        payload = mock_sess.post.call_args[1]["json"]
        assert "FAILED test_something.py" in payload["description"]

    def test_main_exits_1_on_api_failure(self, monkeypatch):
        from scripts.nightly_test_alert import main

        self._setup_env(monkeypatch)
        mock_sess = MagicMock()
        mock_sess.post.side_effect = ConnectionError("network down")
        _patch_setup(monkeypatch, mock_sess)
        monkeypatch.setattr(
            "sys.argv",
            [
                "nightly_test_alert.py",
                "--workflow", "Test and Coverage",
                "--run-id", "12345",
                "--run-url", "https://github.com/owner/repo/actions/runs/12345",
            ],
        )

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    def test_main_missing_test_output_file(self, monkeypatch, tmp_path):
        from scripts.nightly_test_alert import main

        self._setup_env(monkeypatch)
        missing = tmp_path / "does-not-exist.txt"

        mock_sess = _make_mock_sess(
            post_return={"identifier": "BTCAAAAA-999", "id": "uuid-99"},
        )
        _patch_setup(monkeypatch, mock_sess)
        monkeypatch.setattr(
            "sys.argv",
            [
                "nightly_test_alert.py",
                "--workflow", "Test and Coverage",
                "--run-id", "12345",
                "--run-url", "https://github.com/owner/repo/actions/runs/12345",
                "--test-output", str(missing),
            ],
        )

        main()
        payload = mock_sess.post.call_args[1]["json"]
        assert "### Test Output" not in payload["description"]
