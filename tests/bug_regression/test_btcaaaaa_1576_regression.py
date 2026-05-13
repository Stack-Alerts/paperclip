"""
Regression tests for BTCAAAAA-1576: close HTTP session in _get_issue() and
add comment_extractor tests.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1576
Components: src/blast_radius/worker.py
            src/touch_index/paperclip_client.py
            src/touch_index/comment_extractor.py
            tests/test_touch_index/test_comment_extractor.py

Root cause: _get_issue() in blast_radius/worker.py created an HTTP session
via _session() without closing it, causing session/resource leaks.  The fix
first wrapped the call with a context manager (``with _session() as sess:``),
then was refactored to delegate to ``get_issue_by_id()`` which now uses the
context-manager pattern.

This file exercises the session lifecycle in get_issue_by_id() plus the
extract_files_from_comments() and fetch_and_extract() functions that were
test-validated in the same commit.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1576"),
    pytest.mark.regression,
]


# ---------------------------------------------------------------------------
# get_issue_by_id -- session context-manager lifecycle
# ---------------------------------------------------------------------------


class TestGetIssueByIdSessionContextManager:
    """Verify get_issue_by_id() uses the requests.Session as a context manager
    so the HTTP session is closed after the API call, preventing resource leaks."""

    def test_session_enter_called(self) -> None:
        from touch_index.paperclip_client import get_issue_by_id

        mock_sess = MagicMock()
        mock_sess.__enter__.return_value = mock_sess
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "iss-1576", "identifier": "BTCAAAAA-1576"}
        mock_resp.raise_for_status.return_value = None
        mock_sess.get.return_value = mock_resp

        with (
            patch("touch_index.paperclip_client._base", return_value="https://api.example.com"),
            patch("touch_index.paperclip_client._session", return_value=mock_sess),
        ):
            result = get_issue_by_id("test-issue-id")
            assert result == {"id": "iss-1576", "identifier": "BTCAAAAA-1576"}

        mock_sess.__enter__.assert_called_once()
        mock_sess.get.assert_called_once_with(
            "https://api.example.com/api/issues/test-issue-id", timeout=30
        )

    def test_session_exit_called_on_success(self) -> None:
        from touch_index.paperclip_client import get_issue_by_id

        mock_sess = MagicMock()
        mock_sess.__enter__.return_value = mock_sess
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "ok"}
        mock_resp.raise_for_status.return_value = None
        mock_sess.get.return_value = mock_resp

        with (
            patch("touch_index.paperclip_client._base", return_value="https://api.x"),
            patch("touch_index.paperclip_client._session", return_value=mock_sess),
        ):
            get_issue_by_id("any-id")

        mock_sess.__exit__.assert_called_once()

    def test_session_exit_called_on_404(self) -> None:
        """__exit__ must still be called when the API returns 404."""
        from touch_index.paperclip_client import get_issue_by_id

        mock_sess = MagicMock()
        mock_sess.__enter__.return_value = mock_sess
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_sess.get.return_value = mock_resp

        with (
            patch("touch_index.paperclip_client._base", return_value="https://api.x"),
            patch("touch_index.paperclip_client._session", return_value=mock_sess),
        ):
            result = get_issue_by_id("missing-id")
            assert result is None

        mock_sess.__exit__.assert_called_once()

    def test_session_exit_called_on_http_error(self) -> None:
        """__exit__ must still be called when the API request raises an error."""
        from touch_index.paperclip_client import get_issue_by_id

        mock_sess = MagicMock()
        mock_sess.__enter__.return_value = mock_sess
        mock_sess.get.side_effect = RuntimeError("API timeout")

        with (
            patch("touch_index.paperclip_client._base", return_value="https://api.x"),
            patch("touch_index.paperclip_client._session", return_value=mock_sess),
        ):
            with pytest.raises(RuntimeError, match="API timeout"):
                get_issue_by_id("bad-id")

        mock_sess.__exit__.assert_called_once()

    def test_session_closed_on_successful_call(self) -> None:
        """The session must be properly entered, used, and exited for a
        successful API call -- exit proves session lifecycle completion."""
        from touch_index.paperclip_client import get_issue_by_id

        mock_sess = MagicMock()
        mock_sess.__enter__.return_value = mock_sess
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "x"}
        mock_resp.raise_for_status.return_value = None
        mock_sess.get.return_value = mock_resp

        with (
            patch("touch_index.paperclip_client._base", return_value="https://api.x"),
            patch("touch_index.paperclip_client._session", return_value=mock_sess),
        ):
            result = get_issue_by_id("sess-lifecycle")
            assert result == {"id": "x"}

        mock_sess.__enter__.assert_called_once()
        mock_sess.__exit__.assert_called_once()

    def test_raise_for_status_called(self) -> None:
        """raise_for_status must be called on the response within the context."""
        from touch_index.paperclip_client import get_issue_by_id

        mock_sess = MagicMock()
        mock_sess.__enter__.return_value = mock_sess
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "ok"}
        mock_sess.get.return_value = mock_resp

        with (
            patch("touch_index.paperclip_client._base", return_value="https://api.x"),
            patch("touch_index.paperclip_client._session", return_value=mock_sess),
        ):
            get_issue_by_id("check-status")

        mock_resp.raise_for_status.assert_called_once()


# ---------------------------------------------------------------------------
# _get_issue from blast_radius.worker -- delegates to get_issue_by_id
# ---------------------------------------------------------------------------


class TestGetIssueDelegation:
    """Verify _get_issue() in blast_radius/worker.py (the original buggy function)
    now delegates to get_issue_by_id() which uses a context-managed session."""

    def test_delegates_to_get_issue_by_id(self, monkeypatch) -> None:
        from blast_radius.worker import _get_issue

        mock_issue = {"id": "abc", "identifier": "BTCAAAAA-1576"}
        monkeypatch.setattr(
            "blast_radius.worker.get_issue_by_id",
            lambda iid: mock_issue if iid == "test-id" else None,
        )
        result = _get_issue("test-id")
        assert result == mock_issue

    def test_raises_when_issue_not_found(self, monkeypatch) -> None:
        from blast_radius.worker import _get_issue

        monkeypatch.setattr(
            "blast_radius.worker.get_issue_by_id",
            lambda iid: None,
        )
        with pytest.raises(RuntimeError, match="Issue missing-id not found"):
            _get_issue("missing-id")

    def test_raises_on_fetch_failure(self, monkeypatch) -> None:
        from blast_radius.worker import _get_issue

        monkeypatch.setattr(
            "blast_radius.worker.get_issue_by_id",
            lambda iid: (_ for _ in ()).throw(RuntimeError("API down")),
        )
        with pytest.raises(RuntimeError, match="API down"):
            _get_issue("err-id")


# ---------------------------------------------------------------------------
# extract_files_from_comments
# ---------------------------------------------------------------------------


class TestExtractFilesFromCommentsRegression:
    def test_aggregates_across_multiple_comments(self) -> None:
        from touch_index.comment_extractor import extract_files_from_comments

        comments = [
            {"body": "Changed `src/foo.py` in PR #1"},
            {"body": "Also touched `src/bar.py`"},
        ]
        files = extract_files_from_comments(comments)
        assert files == ["src/bar.py", "src/foo.py"]

    def test_deduplicates_across_comments(self) -> None:
        from touch_index.comment_extractor import extract_files_from_comments

        comments = [
            {"body": "Changed `src/foo.py`"},
            {"body": "Re-fixed `src/foo.py`"},
        ]
        files = extract_files_from_comments(comments)
        assert files == ["src/foo.py"]

    def test_no_paths_returns_empty(self) -> None:
        from touch_index.comment_extractor import extract_files_from_comments

        comments = [{"body": "LGTM"}, {"body": "Approved"}]
        assert extract_files_from_comments(comments) == []

    def test_empty_comment_list(self) -> None:
        from touch_index.comment_extractor import extract_files_from_comments

        assert extract_files_from_comments([]) == []

    def test_comment_without_body_key(self) -> None:
        from touch_index.comment_extractor import extract_files_from_comments

        comments = [{"id": "1"}, {"body": "Changed `src/a.py`"}]
        files = extract_files_from_comments(comments)
        assert files == ["src/a.py"]


# ---------------------------------------------------------------------------
# fetch_and_extract
# ---------------------------------------------------------------------------


class TestFetchAndExtractRegression:
    def test_returns_files_from_api_response(self) -> None:
        from touch_index.comment_extractor import fetch_and_extract

        comments = [
            {"body": "Fixed in `src/worker.py`"},
            {"body": "Also `src/db.py`"},
        ]

        with patch(
            "touch_index.paperclip_client.fetch_issue_comments",
            return_value=comments,
        ) as mock_fetch:
            files = fetch_and_extract("issue-uuid-1")

        assert files == ["src/db.py", "src/worker.py"]
        mock_fetch.assert_called_once_with("issue-uuid-1")

    def test_empty_comments_returns_empty(self) -> None:
        from touch_index.comment_extractor import fetch_and_extract

        with patch(
            "touch_index.paperclip_client.fetch_issue_comments",
            return_value=[],
        ) as mock_fetch:
            assert fetch_and_extract("issue-uuid-2") == []
        mock_fetch.assert_called_once_with("issue-uuid-2")

    def test_api_error_propagates(self) -> None:
        from touch_index.comment_extractor import fetch_and_extract

        with patch(
            "touch_index.paperclip_client.fetch_issue_comments",
            side_effect=RuntimeError("API timeout"),
        ) as mock_fetch:
            with pytest.raises(RuntimeError, match="API timeout"):
                fetch_and_extract("issue-uuid-3")
        mock_fetch.assert_called_once_with("issue-uuid-3")

    def test_http_error_raises(self) -> None:
        from requests import HTTPError
        from touch_index.comment_extractor import fetch_and_extract

        with patch(
            "touch_index.paperclip_client.fetch_issue_comments",
            side_effect=HTTPError("403 Forbidden"),
        ) as mock_fetch:
            with pytest.raises(HTTPError, match="403 Forbidden"):
                fetch_and_extract("issue-uuid-4")
        mock_fetch.assert_called_once_with("issue-uuid-4")
