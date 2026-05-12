"""Unit tests for blast_radius.generator — no DB or live network required."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from blast_radius.generator import generate_and_post
from blast_radius.query import BlastRadiusData, FRImpact, RegressionRisk


@pytest.fixture
def mock_issue():
    return {
        "id": "issue-uuid-1",
        "identifier": "BTCAAAAA-100",
        "title": "Fix the thing",
        "description": '```json\n{"touchedFiles": ["src/foo.py", "src/bar.py"]}\n```',
    }


@pytest.fixture
def mock_empty_touched_issue():
    return {
        "id": "issue-uuid-2",
        "identifier": "BTCAAAAA-200",
        "title": "Fix another thing",
        "description": "No touched files here.",
    }


class TestGenerateAndPost:
    def _patch_all(self, monkeypatch, issue, query_data=None):
        """Wire up all external dependencies."""
        monkeypatch.setattr(
            "blast_radius.generator._get_issue",
            lambda issue_id: issue,
        )
        monkeypatch.setattr(
            "blast_radius.generator._get_agent_name",
            lambda agent_id: f"Agent-{agent_id[:8]}",
        )
        monkeypatch.setattr(
            "blast_radius.generator._post_comment",
            lambda issue_id, body: None,
        )
        if query_data is None:
            query_data = BlastRadiusData()
        monkeypatch.setattr(
            "blast_radius.generator.query_blast_radius",
            lambda file_paths: query_data,
        )

    def test_generates_and_posts(self, monkeypatch, mock_issue):
        self._patch_all(monkeypatch, mock_issue)

        result = generate_and_post(issue_id="issue-uuid-1", dry_run=False)

        assert result["issue"] == "BTCAAAAA-100"
        assert result["dry_run"] is False

    def test_dry_run_does_not_post(self, monkeypatch, mock_issue):
        posted = []
        monkeypatch.setattr(
            "blast_radius.generator._get_issue",
            lambda issue_id: mock_issue,
        )
        monkeypatch.setattr(
            "blast_radius.generator._get_agent_name",
            lambda agent_id: "TestAgent",
        )
        monkeypatch.setattr(
            "blast_radius.generator._post_comment",
            lambda issue_id, body: posted.append(issue_id),
        )
        monkeypatch.setattr(
            "blast_radius.generator.query_blast_radius",
            lambda file_paths: BlastRadiusData(),
        )

        result = generate_and_post(issue_id="issue-uuid-1", dry_run=True)

        assert result["dry_run"] is True
        assert posted == []

    def test_posts_comment_in_live_mode(self, monkeypatch, mock_issue):
        posted = []
        monkeypatch.setattr(
            "blast_radius.generator._get_issue",
            lambda issue_id: mock_issue,
        )
        monkeypatch.setattr(
            "blast_radius.generator._get_agent_name",
            lambda agent_id: "TestAgent",
        )
        monkeypatch.setattr(
            "blast_radius.generator._post_comment",
            lambda issue_id, body: posted.append(issue_id),
        )
        monkeypatch.setattr(
            "blast_radius.generator.query_blast_radius",
            lambda file_paths: BlastRadiusData(),
        )

        generate_and_post(issue_id="issue-uuid-1", dry_run=False)

        assert posted == ["issue-uuid-1"]

    def test_uses_provided_touched_files(self, monkeypatch, mock_issue):
        captured = []
        monkeypatch.setattr(
            "blast_radius.generator._get_issue",
            lambda issue_id: mock_issue,
        )
        monkeypatch.setattr(
            "blast_radius.generator._get_agent_name",
            lambda agent_id: "TestAgent",
        )
        monkeypatch.setattr(
            "blast_radius.generator._post_comment",
            lambda issue_id, body: None,
        )
        monkeypatch.setattr(
            "blast_radius.generator.query_blast_radius",
            lambda file_paths: captured.append(list(file_paths)) or BlastRadiusData(),
        )

        generate_and_post(
            issue_id="issue-uuid-1",
            touched_files=["src/override.py"],
            dry_run=True,
        )

        assert captured == [["src/override.py"]]

    def test_skips_when_no_touched_files(self, monkeypatch, mock_empty_touched_issue):
        monkeypatch.setattr(
            "blast_radius.generator._get_issue",
            lambda issue_id: mock_empty_touched_issue,
        )
        monkeypatch.setattr(
            "blast_radius.generator._get_agent_name",
            lambda agent_id: "TestAgent",
        )
        posted = []
        monkeypatch.setattr(
            "blast_radius.generator._post_comment",
            lambda issue_id, body: posted.append(issue_id),
        )

        result = generate_and_post(issue_id="issue-uuid-2", dry_run=False)

        assert result["skipped"] is True
        assert result["reason"] == "no touchedFiles"
        assert posted == []

    def test_includes_fr_impact_in_result(self, monkeypatch, mock_issue):
        data = BlastRadiusData(
            fr_impact_set=[
                FRImpact(
                    fr_identifier="FDR-100",
                    fr_owner_agent_id="agent-uuid-fr-owner",
                    fr_issue_id="fr-issue-uuid",
                )
            ]
        )
        self._patch_all(monkeypatch, mock_issue, query_data=data)

        result = generate_and_post(issue_id="issue-uuid-1", dry_run=True)

        assert len(result["fr_impact_set"]) == 1
        assert result["fr_impact_set"][0]["fr_identifier"] == "FDR-100"

    def test_includes_regression_risk_in_result(self, monkeypatch, mock_issue):
        data = BlastRadiusData(
            regression_set=[
                RegressionRisk(
                    bug_identifier="BTCAAAAA-500",
                    bug_issue_id="bug-uuid-1",
                )
            ]
        )
        self._patch_all(monkeypatch, mock_issue, query_data=data)

        result = generate_and_post(issue_id="issue-uuid-1", dry_run=True)

        assert len(result["regression_set"]) == 1
        assert result["regression_set"][0]["bug_identifier"] == "BTCAAAAA-500"

    def test_resolves_agent_names_for_mentions(self, monkeypatch, mock_issue):
        data = BlastRadiusData(
            fr_impact_set=[
                FRImpact(
                    fr_identifier="FDR-200",
                    fr_owner_agent_id="agent-uuid-abc",
                    fr_issue_id="fr-uuid-2",
                )
            ]
        )
        resolved = {}
        monkeypatch.setattr(
            "blast_radius.generator._get_issue",
            lambda issue_id: mock_issue,
        )
        monkeypatch.setattr(
            "blast_radius.generator._get_agent_name",
            lambda agent_id: resolved.update({agent_id: "ResolvedName"}) or "ResolvedName",
        )
        posted_body = []
        monkeypatch.setattr(
            "blast_radius.generator._post_comment",
            lambda issue_id, body: posted_body.append(body),
        )
        monkeypatch.setattr(
            "blast_radius.generator.query_blast_radius",
            lambda file_paths: data,
        )

        generate_and_post(issue_id="issue-uuid-1", dry_run=False)

        assert "ResolvedName" in posted_body[0]
        assert "FDR-200" in posted_body[0]

    def test_error_in_get_issue_raises(self, monkeypatch):
        monkeypatch.setattr(
            "blast_radius.generator._get_issue",
            lambda issue_id: (_ for _ in ()).throw(RuntimeError("API down")),
        )

        with pytest.raises(RuntimeError, match="API down"):
            generate_and_post(issue_id="bad-uuid", dry_run=True)


# ---------------------------------------------------------------------------
# Generator HTTP helper functions
# ---------------------------------------------------------------------------

class TestRunHeaders:
    def test_returns_empty_without_env(self, monkeypatch):
        import blast_radius.generator as gen_mod
        monkeypatch.setattr(gen_mod, "PAPERCLIP_RUN_ID", "")
        assert gen_mod._run_headers() == {}

    def test_returns_run_id_header_when_set(self, monkeypatch):
        import blast_radius.generator as gen_mod
        monkeypatch.setattr(gen_mod, "PAPERCLIP_RUN_ID", "run-abc-123")
        result = gen_mod._run_headers()
        assert result == {"X-Paperclip-Run-Id": "run-abc-123"}


class TestGetIssue:
    def test_fetches_issue_by_id(self, monkeypatch):
        from blast_radius.generator import _get_issue

        expected = {"id": "iss-1", "identifier": "BTCAAAAA-100"}
        monkeypatch.setattr(
            "blast_radius.generator.get_issue_by_id",
            lambda issue_id: expected,
        )

        result = _get_issue("iss-1")
        assert result == expected

    def test_raises_on_http_error(self, monkeypatch):
        from blast_radius.generator import _get_issue

        monkeypatch.setattr(
            "blast_radius.generator.get_issue_by_id",
            lambda issue_id: (_ for _ in ()).throw(RuntimeError("404 Not Found")),
        )

        with pytest.raises(RuntimeError, match="404 Not Found"):
            _get_issue("bad-id")

    def test_raises_on_not_found(self, monkeypatch):
        from blast_radius.generator import _get_issue

        monkeypatch.setattr(
            "blast_radius.generator.get_issue_by_id",
            lambda issue_id: None,
        )

        with pytest.raises(RuntimeError, match="not found"):
            _get_issue("missing-id")


class TestGetAgentName:
    def test_returns_name_on_success(self, monkeypatch):
        from blast_radius.generator import _get_agent_name

        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"name": "CoderBot"}
        mock_sess = MagicMock()
        mock_sess.__enter__.return_value = mock_sess
        mock_sess.get.return_value = mock_resp

        monkeypatch.setattr(
            "blast_radius.generator._session",
            lambda: mock_sess,
        )

        result = _get_agent_name("agent-uuid")
        assert result == "CoderBot"

    def test_falls_back_to_name_key(self, monkeypatch):
        from blast_radius.generator import _get_agent_name

        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"nameKey": "agent-coder-01"}
        mock_sess = MagicMock()
        mock_sess.__enter__.return_value = mock_sess
        mock_sess.get.return_value = mock_resp

        monkeypatch.setattr(
            "blast_radius.generator._session",
            lambda: mock_sess,
        )

        result = _get_agent_name("agent-uuid")
        assert result == "agent-coder-01"

    def test_returns_none_on_http_error(self, monkeypatch):
        from blast_radius.generator import _get_agent_name

        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_sess = MagicMock()
        mock_sess.__enter__.return_value = mock_sess
        mock_sess.get.return_value = mock_resp

        monkeypatch.setattr(
            "blast_radius.generator._session",
            lambda: mock_sess,
        )

        result = _get_agent_name("agent-uuid")
        assert result is None

    def test_returns_none_on_exception(self, monkeypatch):
        from blast_radius.generator import _get_agent_name

        def thrower(*args, **kwargs):
            raise ConnectionError("Network timeout")

        mock_sess = MagicMock()
        mock_sess.__enter__.return_value = mock_sess
        mock_sess.get.side_effect = thrower

        monkeypatch.setattr(
            "blast_radius.generator._session",
            lambda: mock_sess,
        )

        result = _get_agent_name("agent-uuid")
        assert result is None

    def test_returns_none_on_missing_both_name_and_name_key(self, monkeypatch):
        from blast_radius.generator import _get_agent_name

        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"id": "agent-uuid"}
        mock_sess = MagicMock()
        mock_sess.__enter__.return_value = mock_sess
        mock_sess.get.return_value = mock_resp

        monkeypatch.setattr(
            "blast_radius.generator._session",
            lambda: mock_sess,
        )

        result = _get_agent_name("agent-uuid")
        assert result is None


class TestPostComment:
    def test_posts_comment(self, monkeypatch):
        from blast_radius.generator import _post_comment

        mock_resp = MagicMock()
        mock_sess = MagicMock()
        mock_sess.__enter__.return_value = mock_sess
        mock_sess.post.return_value = mock_resp

        monkeypatch.setattr(
            "blast_radius.generator._session",
            lambda: mock_sess,
        )
        monkeypatch.setattr(
            "blast_radius.generator._run_headers",
            lambda: {},
        )

        _post_comment("iss-1", "Hello world")

        mock_sess.post.assert_called_once()
        call_args = mock_sess.post.call_args
        assert "/api/issues/iss-1/comments" in str(call_args[0][0])
        assert call_args[1]["json"] == {"body": "Hello world"}

    def test_raises_on_http_error(self, monkeypatch):
        from blast_radius.generator import _post_comment

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = RuntimeError("422 Unprocessable")
        mock_sess = MagicMock()
        mock_sess.__enter__.return_value = mock_sess
        mock_sess.post.return_value = mock_resp

        monkeypatch.setattr(
            "blast_radius.generator._session",
            lambda: mock_sess,
        )
        monkeypatch.setattr(
            "blast_radius.generator._run_headers",
            lambda: {},
        )

        with pytest.raises(RuntimeError, match="422 Unprocessable"):
            _post_comment("bad-id", "body")

    def test_includes_run_header(self, monkeypatch):
        from blast_radius.generator import _post_comment

        mock_resp = MagicMock()
        mock_sess = MagicMock()
        mock_sess.__enter__.return_value = mock_sess
        mock_sess.post.return_value = mock_resp

        monkeypatch.setattr(
            "blast_radius.generator._session",
            lambda: mock_sess,
        )
        monkeypatch.setattr(
            "blast_radius.generator._run_headers",
            lambda: {"X-Paperclip-Run-Id": "run-xyz"},
        )

        _post_comment("iss-1", "body")

        # _run_headers result should be merged into session headers
        mock_sess.headers.update.assert_called_once_with(
            {"X-Paperclip-Run-Id": "run-xyz"}
        )
