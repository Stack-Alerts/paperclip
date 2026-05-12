"""Unit tests for paperclip_client.py retry and API helpers.

All external HTTP I/O is mocked so tests run offline.
"""

from __future__ import annotations

import os
from unittest.mock import patch

from urllib3.util import Retry as RetryStrategy


class TestRetryStrategy:
    """Verify the retry strategy is configured correctly."""

    def test_retry_on_session(self):
        """_session() mounts an adapter with the retry strategy."""
        from touch_index.paperclip_client import _session, _RETRY_STRATEGY

        # We need env vars for the session constructor
        with patch.dict(
            os.environ,
            {
                "PAPERCLIP_API_KEY": "test-key",
                "PAPERCLIP_API_URL": "https://api.example.com",
                "PAPERCLIP_COMPANY_ID": "test-company",
            },
            clear=True,
        ):
            s = _session()
            # HTTPAdapter uses an internal Retry object; we verify via the
            # adapter's get_connection method but the simplest check is that
            # the session has adapters mounted for both protocols.
            https_adapter = s.get_adapter("https://api.example.com/foo")
            http_adapter = s.get_adapter("http://api.example.com/foo")
            assert https_adapter.max_retries is not None
            assert http_adapter.max_retries is not None
            # Both adapters use the same retry instance
            assert https_adapter.max_retries.total == 3
            assert http_adapter.max_retries.total == 3
            assert https_adapter.max_retries.backoff_factor == 0.5
            assert http_adapter.max_retries.backoff_factor == 0.5

    def test_retry_on_board_session(self):
        """_board_session() mounts an adapter with the same retry strategy."""
        from touch_index.paperclip_client import _board_session

        with patch.dict(
            os.environ,
            {
                "PAPERCLIP_API_KEY": "test-key",
                "PAPERCLIP_API_URL": "https://api.example.com",
                "PAPERCLIP_COMPANY_ID": "test-company",
            },
            clear=True,
        ):
            s = _board_session()
            https_adapter = s.get_adapter("https://api.example.com/foo")
            assert https_adapter.max_retries.total == 3
            assert https_adapter.max_retries.backoff_factor == 0.5

    def test_retry_status_codes(self):
        """Retry should cover 408, 429, 5xx."""
        from touch_index.paperclip_client import _RETRY_STRATEGY

        assert isinstance(_RETRY_STRATEGY, RetryStrategy)
        assert 408 in _RETRY_STRATEGY.status_forcelist
        assert 429 in _RETRY_STRATEGY.status_forcelist
        assert 500 in _RETRY_STRATEGY.status_forcelist
        assert 502 in _RETRY_STRATEGY.status_forcelist
        assert 503 in _RETRY_STRATEGY.status_forcelist
        assert 504 in _RETRY_STRATEGY.status_forcelist

    def test_retry_allowed_methods(self):
        """GET, PATCH, and POST should be retryable."""
        from touch_index.paperclip_client import _RETRY_STRATEGY

        assert "GET" in _RETRY_STRATEGY.allowed_methods
        assert "PATCH" in _RETRY_STRATEGY.allowed_methods
        assert "POST" in _RETRY_STRATEGY.allowed_methods

    def test_retry_count(self):
        """Should retry up to 3 times."""
        from touch_index.paperclip_client import _RETRY_STRATEGY

        assert _RETRY_STRATEGY.total == 3


# ---------------------------------------------------------------------------
# Timestamp filtering — each API function must include (not skip) issues
# that have a null/missing timestamp when a time filter is applied.
# ---------------------------------------------------------------------------


class TestGetClosedNonFdrIssues:
    """get_closed_non_fdr_issues — done non-FDR issues with optional time filter."""

    def _make_issues(self, completed_ats: list[str | None]) -> list[dict]:
        return [
            {
                "id": f"id-{i}",
                "identifier": f"BTCAAAAA-{100 + i}",
                "status": "done",
                "completedAt": ts,
            }
            for i, ts in enumerate(completed_ats)
        ]

    def test_no_filter_returns_all(self):
        """Without closed_after, all non-FDR done issues are returned."""
        from touch_index.paperclip_client import get_closed_non_fdr_issues

        issues = self._make_issues([None, "2026-05-11T10:00:00Z"])
        with (
            patch("touch_index.paperclip_client._paginate", return_value=issues),
            patch("touch_index.paperclip_client._company", return_value="c"),
        ):
            result = get_closed_non_fdr_issues()
        assert len(result) == 2

    def test_includes_issues_with_recent_completed_at(self):
        """Issues with completedAt >= cutoff are included."""
        from datetime import datetime, timedelta, timezone
        from touch_index.paperclip_client import get_closed_non_fdr_issues

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=1)
        issues = self._make_issues([(now - timedelta(minutes=5)).isoformat()])
        with (
            patch("touch_index.paperclip_client._paginate", return_value=issues),
            patch("touch_index.paperclip_client._company", return_value="c"),
        ):
            result = get_closed_non_fdr_issues(closed_after=cutoff)
        assert len(result) == 1

    def test_excludes_old_completed_at(self):
        """Issues with completedAt < cutoff are excluded."""
        from datetime import datetime, timedelta, timezone
        from touch_index.paperclip_client import get_closed_non_fdr_issues

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=1)
        issues = self._make_issues([(now - timedelta(days=30)).isoformat()])
        with (
            patch("touch_index.paperclip_client._paginate", return_value=issues),
            patch("touch_index.paperclip_client._company", return_value="c"),
        ):
            result = get_closed_non_fdr_issues(closed_after=cutoff)
        assert len(result) == 0

    def test_includes_missing_completed_at(self):
        """NULL or missing completedAt — included (regression: was skipped)."""
        from datetime import datetime, timedelta, timezone
        from touch_index.paperclip_client import get_closed_non_fdr_issues

        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        issues = self._make_issues([None, None])
        with (
            patch("touch_index.paperclip_client._paginate", return_value=issues),
            patch("touch_index.paperclip_client._company", return_value="c"),
        ):
            result = get_closed_non_fdr_issues(closed_after=cutoff)
        assert len(result) == 2

    def test_includes_malformed_completed_at(self):
        """Malformed completedAt — included (regression: was skipped)."""
        from datetime import datetime, timedelta, timezone
        from touch_index.paperclip_client import get_closed_non_fdr_issues

        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        issues = self._make_issues(["not-a-date", "also-bad"])
        with (
            patch("touch_index.paperclip_client._paginate", return_value=issues),
            patch("touch_index.paperclip_client._company", return_value="c"),
        ):
            result = get_closed_non_fdr_issues(closed_after=cutoff)
        assert len(result) == 2

    def test_excludes_fdr_labelled(self):
        """FDR-labelled issues are excluded."""
        from touch_index.paperclip_client import (
            FDR_LABEL_ID,
            get_closed_non_fdr_issues,
        )

        issues = [
            {
                "id": "id-fdr",
                "identifier": "BTCAAAAA-200",
                "status": "done",
                "labelIds": [FDR_LABEL_ID],
            },
            {
                "id": "id-bug",
                "identifier": "BTCAAAAA-201",
                "status": "done",
            },
        ]
        with (
            patch("touch_index.paperclip_client._paginate", return_value=issues),
            patch("touch_index.paperclip_client._company", return_value="c"),
        ):
            result = get_closed_non_fdr_issues()
        assert [i["identifier"] for i in result] == ["BTCAAAAA-201"]


class TestGetFdrIssues:
    """get_fdr_issues — FDR-labelled issues with optional time filter."""

    def _make_issues(self, updated_ats: list[str | None]) -> list[dict]:
        from touch_index.paperclip_client import FDR_LABEL_ID

        return [
            {
                "id": f"id-{i}",
                "identifier": f"BTCAAAAA-{300 + i}",
                "labelIds": [FDR_LABEL_ID],
                "updatedAt": ts,
            }
            for i, ts in enumerate(updated_ats)
        ]

    def test_no_filter_returns_all(self):
        from touch_index.paperclip_client import FDR_LABEL_ID, get_fdr_issues

        issues = self._make_issues([None, "2026-05-11T10:00:00Z"])
        with (
            patch("touch_index.paperclip_client._paginate", return_value=issues),
            patch("touch_index.paperclip_client._company", return_value="c"),
        ):
            result = get_fdr_issues()
        assert len(result) == 2

    def test_includes_recent_updated_at(self):
        from datetime import datetime, timedelta, timezone
        from touch_index.paperclip_client import get_fdr_issues

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=1)
        issues = self._make_issues([(now - timedelta(minutes=5)).isoformat()])
        with (
            patch("touch_index.paperclip_client._paginate", return_value=issues),
            patch("touch_index.paperclip_client._company", return_value="c"),
        ):
            result = get_fdr_issues(updated_after=cutoff)
        assert len(result) == 1

    def test_excludes_old_updated_at(self):
        from datetime import datetime, timedelta, timezone
        from touch_index.paperclip_client import get_fdr_issues

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=1)
        issues = self._make_issues([(now - timedelta(days=30)).isoformat()])
        with (
            patch("touch_index.paperclip_client._paginate", return_value=issues),
            patch("touch_index.paperclip_client._company", return_value="c"),
        ):
            result = get_fdr_issues(updated_after=cutoff)
        assert len(result) == 0

    def test_includes_missing_updated_at(self):
        """NULL or missing updatedAt — included (regression: was skipped)."""
        from datetime import datetime, timedelta, timezone
        from touch_index.paperclip_client import get_fdr_issues

        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        issues = self._make_issues([None, None])
        with (
            patch("touch_index.paperclip_client._paginate", return_value=issues),
            patch("touch_index.paperclip_client._company", return_value="c"),
        ):
            result = get_fdr_issues(updated_after=cutoff)
        assert len(result) == 2


class TestGetClosedBugIssues:
    """get_closed_bug_issues — done issues with bug title prefix."""

    def _make_bugs(self, completed_ats: list[str | None]) -> list[dict]:
        return [
            {
                "id": f"id-{i}",
                "identifier": f"BTCAAAAA-{400 + i}",
                "title": "Bug: test issue",
                "status": "done",
                "completedAt": ts,
            }
            for i, ts in enumerate(completed_ats)
        ]

    def test_includes_missing_completed_at(self):
        """NULL completedAt — included."""
        from datetime import datetime, timedelta, timezone
        from touch_index.paperclip_client import get_closed_bug_issues

        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        with (
            patch(
                "touch_index.paperclip_client._paginate",
                return_value=self._make_bugs([None]),
            ),
            patch("touch_index.paperclip_client._company", return_value="c"),
        ):
            result = get_closed_bug_issues(closed_after=cutoff)
        assert len(result) == 1


class TestGetAllDoneIssues:
    """get_all_done_issues — all done issues with optional time filter."""

    def _make_issues(self, completed_ats: list[str | None]) -> list[dict]:
        return [
            {
                "id": f"id-{i}",
                "identifier": f"BTCAAAAA-{500 + i}",
                "status": "done",
                "completedAt": ts,
            }
            for i, ts in enumerate(completed_ats)
        ]

    def test_includes_missing_completed_at(self):
        """NULL completedAt — included."""
        from datetime import datetime, timedelta, timezone
        from touch_index.paperclip_client import get_all_done_issues

        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        with (
            patch(
                "touch_index.paperclip_client._paginate",
                return_value=self._make_issues([None]),
            ),
            patch("touch_index.paperclip_client._company", return_value="c"),
        ):
            result = get_all_done_issues(completed_after=cutoff)
        assert len(result) == 1
