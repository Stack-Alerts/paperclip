"""Unit tests for blast_radius.generator -- no DB or live network required."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from blast_radius.query import BlastRadiusData, FRImpact, RegressionRisk


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MOCK_ISSUE = {
    "id": "issue-uuid",
    "identifier": "BTCAAAAA-100",
    "title": "Fix null pointer in loader",
    "description": '{"touchedFiles": ["src/loader.py", "src/db.py"]}',
}

_MOCK_ISSUE_NO_TF = {
    "id": "issue-uuid-2",
    "identifier": "FAKE-000",
    "title": "Fix cache bug",
    "description": "No touched files here",
}

_MOCK_BR_DATA = BlastRadiusData(
    fr_impact_set=[
        FRImpact(
            fr_identifier="FDR-850", fr_owner_agent_id="agent-1", fr_issue_id="fr-uuid"
        ),
    ],
    regression_set=[
        RegressionRisk(bug_identifier="BTCAAAAA-50", bug_issue_id="bug-uuid"),
    ],
    downstream_set=[],
)


# ---------------------------------------------------------------------------
# generate_and_post
# ---------------------------------------------------------------------------


class TestGenerateAndPost:
    def test_generates_and_posts(self):
        from blast_radius.generator import generate_and_post

        with (
            patch(
                "blast_radius.generator.get_issue_by_id", return_value=_MOCK_ISSUE
            ) as mock_get,
            patch(
                "blast_radius.generator.query_blast_radius", return_value=_MOCK_BR_DATA
            ) as mock_query,
            patch(
                "blast_radius.generator._get_agent_name", return_value="Alice"
            ) as mock_name,
            patch("blast_radius.generator._post_comment") as mock_post,
        ):
            result = generate_and_post("issue-uuid", dry_run=False)

        assert result["issue"] == "BTCAAAAA-100"
        assert result["dry_run"] is False
        mock_get.assert_called_once_with("issue-uuid")
        mock_query.assert_called_once()
        mock_post.assert_called_once()

    def test_dry_run_does_not_post(self):
        from blast_radius.generator import generate_and_post

        with (
            patch("blast_radius.generator.get_issue_by_id", return_value=_MOCK_ISSUE),
            patch(
                "blast_radius.generator.query_blast_radius", return_value=_MOCK_BR_DATA
            ),
            patch("blast_radius.generator._get_agent_name", return_value="Alice"),
            patch("blast_radius.generator._post_comment") as mock_post,
        ):
            result = generate_and_post("issue-uuid", dry_run=True)

        assert result["dry_run"] is True
        mock_post.assert_not_called()

    def test_skipped_when_no_touched_files(self):
        from blast_radius.generator import generate_and_post

        with (
            patch(
                "blast_radius.generator.get_issue_by_id", return_value=_MOCK_ISSUE_NO_TF
            ),
            patch(
                "touch_index.git_extractor.get_files_for_issue", return_value=[]
            ) as mock_git,
            patch("blast_radius.generator._post_comment") as mock_post,
        ):
            result = generate_and_post("issue-uuid-2", dry_run=False)

        assert result.get("skipped") is True
        assert result.get("reason") == "no touchedFiles"
        mock_post.assert_not_called()
        mock_git.assert_called_once_with("FAKE-000")

    def test_skipped_when_touched_files_none_after_extraction(self):
        from blast_radius.generator import generate_and_post

        with (
            patch(
                "blast_radius.generator.get_issue_by_id", return_value=_MOCK_ISSUE_NO_TF
            ),
            patch(
                "touch_index.git_extractor.get_files_for_issue", return_value=[]
            ) as mock_git,
            patch("blast_radius.generator._post_comment") as mock_post,
        ):
            result = generate_and_post("issue-uuid-2", dry_run=True)

        assert result.get("skipped") is True
        mock_git.assert_called_once_with("FAKE-000")

    def test_uses_provided_touched_files(self):
        from blast_radius.generator import generate_and_post

        with (
            patch(
                "blast_radius.generator.get_issue_by_id", return_value=_MOCK_ISSUE_NO_TF
            ),
            patch(
                "blast_radius.generator.query_blast_radius", return_value=_MOCK_BR_DATA
            ) as mock_query,
            patch("blast_radius.generator._get_agent_name", return_value="Alice"),
            patch("blast_radius.generator._post_comment") as mock_post,
        ):
            result = generate_and_post(
                "issue-uuid-2", touched_files=["src/override.py"], dry_run=False
            )

        assert result["issue"] == "FAKE-000"
        assert result.get("skipped") is None
        mock_query.assert_called_once_with(["src/override.py"])
        mock_post.assert_called_once()

    def test_resolves_agent_names_for_mention(self):
        from blast_radius.generator import generate_and_post

        with (
            patch("blast_radius.generator.get_issue_by_id", return_value=_MOCK_ISSUE),
            patch(
                "blast_radius.generator.query_blast_radius", return_value=_MOCK_BR_DATA
            ),
            patch(
                "blast_radius.generator._get_agent_name", return_value="Alice"
            ) as mock_name,
            patch("blast_radius.generator._post_comment") as mock_post,
        ):
            generate_and_post("issue-uuid", dry_run=False)

        mock_name.assert_called_once_with("agent-1")

    def test_skips_agent_name_when_none_returned(self):
        from blast_radius.generator import generate_and_post

        with (
            patch("blast_radius.generator.get_issue_by_id", return_value=_MOCK_ISSUE),
            patch(
                "blast_radius.generator.query_blast_radius", return_value=_MOCK_BR_DATA
            ),
            patch("blast_radius.generator._get_agent_name", return_value=None),
            patch("blast_radius.generator._post_comment") as mock_post,
        ):
            result = generate_and_post("issue-uuid", dry_run=False)

        assert result["issue"] == "BTCAAAAA-100"
        mock_post.assert_called_once()

    def test_issue_not_found_raises(self):
        from blast_radius.generator import generate_and_post

        with (
            patch("blast_radius.generator.get_issue_by_id", return_value=None),
        ):
            with pytest.raises(RuntimeError, match="not found"):
                generate_and_post("bad-uuid", dry_run=False)

    def test_empty_issue_description(self):
        """An empty description should not crash extract_touched_files."""
        from blast_radius.generator import generate_and_post

        issue = {**_MOCK_ISSUE, "description": ""}

        with (
            patch("blast_radius.generator.get_issue_by_id", return_value=issue),
            patch(
                "touch_index.git_extractor.get_files_for_issue", return_value=[]
            ) as mock_git,
            patch("blast_radius.generator._post_comment") as mock_post,
        ):
            result = generate_and_post("issue-uuid", dry_run=False)

        assert result.get("skipped") is True
        mock_post.assert_not_called()
        mock_git.assert_called_once_with("BTCAAAAA-100")

    def test_git_fallback_success(self):
        """When no touchedFiles in description, git fallback should derive files from history."""
        from blast_radius.generator import generate_and_post

        with (
            patch(
                "blast_radius.generator.get_issue_by_id", return_value=_MOCK_ISSUE_NO_TF
            ),
            patch(
                "touch_index.git_extractor.get_files_for_issue",
                return_value=["src/git_file.py"],
            ) as mock_git,
            patch(
                "blast_radius.generator.query_blast_radius", return_value=_MOCK_BR_DATA
            ) as mock_query,
            patch("blast_radius.generator._get_agent_name", return_value="Alice"),
            patch("blast_radius.generator._post_comment") as mock_post,
        ):
            result = generate_and_post("issue-uuid-2", dry_run=False)

        assert result.get("skipped") is None
        assert result["issue"] == "FAKE-000"
        mock_git.assert_called_once_with("FAKE-000")
        mock_query.assert_called_once_with(["src/git_file.py"])
        mock_post.assert_called_once()

    def test_git_fallback_exception(self):
        """When git fallback raises, should log warning and skip gracefully."""
        from blast_radius.generator import generate_and_post

        with (
            patch(
                "blast_radius.generator.get_issue_by_id", return_value=_MOCK_ISSUE_NO_TF
            ),
            patch(
                "touch_index.git_extractor.get_files_for_issue",
                side_effect=RuntimeError("git error"),
            ) as mock_git,
            patch("blast_radius.generator._post_comment") as mock_post,
        ):
            result = generate_and_post("issue-uuid-2", dry_run=False)

        assert result.get("skipped") is True
        assert result.get("reason") == "no touchedFiles"
        mock_git.assert_called_once_with("FAKE-000")
        mock_post.assert_not_called()

    def test_no_fr_impact_set_does_not_call_get_agent_name(self):
        """When fr_impact_set is empty, _get_agent_name should not be called."""
        from blast_radius.generator import generate_and_post

        empty_data = BlastRadiusData()

        with (
            patch("blast_radius.generator.get_issue_by_id", return_value=_MOCK_ISSUE),
            patch("blast_radius.generator.query_blast_radius", return_value=empty_data),
            patch("blast_radius.generator._get_agent_name") as mock_name,
            patch("blast_radius.generator._post_comment"),
        ):
            generate_and_post("issue-uuid", dry_run=False)

        mock_name.assert_not_called()


# ---------------------------------------------------------------------------
# _get_agent_name
# ---------------------------------------------------------------------------


def _mock_session() -> MagicMock:
    """Return a MagicMock configured as a context manager for _session()."""
    mock_sess = MagicMock()
    mock_sess.__enter__.return_value = mock_sess
    mock_sess.__exit__.return_value = False
    return mock_sess


class TestGetAgentName:
    def test_returns_name(self):
        from blast_radius.generator import _get_agent_name

        mock_sess = _mock_session()
        mock_sess.get.return_value.ok = True
        mock_sess.get.return_value.json.return_value = {"name": "Alice"}

        with patch("blast_radius.generator._session", return_value=mock_sess):
            result = _get_agent_name("agent-1")

        assert result == "Alice"

    def test_returns_name_key_when_name_missing(self):
        from blast_radius.generator import _get_agent_name

        mock_sess = _mock_session()
        mock_sess.get.return_value.ok = True
        mock_sess.get.return_value.json.return_value = {"nameKey": "bot-alice"}

        with patch("blast_radius.generator._session", return_value=mock_sess):
            result = _get_agent_name("agent-1")

        assert result == "bot-alice"

    def test_returns_none_on_api_error(self):
        from blast_radius.generator import _get_agent_name

        mock_sess = _mock_session()
        mock_sess.get.return_value.ok = False

        with patch("blast_radius.generator._session", return_value=mock_sess):
            result = _get_agent_name("agent-1")

        assert result is None

    def test_returns_none_on_exception(self):
        from blast_radius.generator import _get_agent_name

        mock_sess = _mock_session()
        mock_sess.get.side_effect = RuntimeError("timeout")

        with patch("blast_radius.generator._session", return_value=mock_sess):
            result = _get_agent_name("agent-1")

        assert result is None


# ---------------------------------------------------------------------------
# _post_comment
# ---------------------------------------------------------------------------


class TestPostComment:
    def test_posts_to_correct_endpoint(self):
        from blast_radius.generator import _post_comment

        mock_sess = _mock_session()

        with (
            patch("touch_index.paperclip_client.is_issue_done", return_value=False),
            patch("blast_radius.generator._board_session", return_value=mock_sess),
            patch("blast_radius.generator.PAPERCLIP_RUN_ID", ""),
        ):
            _post_comment("issue-uuid", "body text")

        args, kwargs = mock_sess.post.call_args
        assert "issue-uuid/comments" in args[0]
        assert kwargs["json"]["body"] == "body text"

    def test_includes_run_header_when_set(self):
        from blast_radius.generator import _post_comment

        mock_sess = _mock_session()

        with (
            patch("touch_index.paperclip_client.is_issue_done", return_value=False),
            patch("blast_radius.generator._board_session", return_value=mock_sess),
            patch("blast_radius.generator.PAPERCLIP_RUN_ID", "run-123"),
        ):
            _post_comment("issue-uuid", "body")

        _, kwargs = mock_sess.post.call_args
        mock_sess.headers.update.assert_called_once()


# ---------------------------------------------------------------------------
# _get_issue
# ---------------------------------------------------------------------------


class TestGetIssue:
    def test_fetches_issue(self):
        from blast_radius.generator import _get_issue

        with patch("blast_radius.generator.get_issue_by_id", return_value={"id": "i1"}):
            assert _get_issue("i1") == {"id": "i1"}

    def test_raises_on_not_found(self):
        from blast_radius.generator import _get_issue

        with patch("blast_radius.generator.get_issue_by_id", return_value=None):
            with pytest.raises(RuntimeError, match="not found"):
                _get_issue("missing")


# ---------------------------------------------------------------------------
# _run_headers
# ---------------------------------------------------------------------------


class TestRunHeaders:
    def test_returns_empty_when_no_run_id(self):
        from blast_radius.generator import _run_headers

        with patch("blast_radius.generator.PAPERCLIP_RUN_ID", ""):
            assert _run_headers() == {}

    def test_returns_run_header_when_set(self):
        from blast_radius.generator import _run_headers

        with patch("blast_radius.generator.PAPERCLIP_RUN_ID", "run-123"):
            assert _run_headers() == {"X-Paperclip-Run-Id": "run-123"}
