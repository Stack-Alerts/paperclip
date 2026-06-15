"""
Regression tests for BTCAAAAA-36508.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-36508
Component: src/api/app.py  ->  POST /data/update (update_data)

Bug: The web "Market Data -> Update" flow reported "update completed" but no
market data was actually refreshed. The web modal sends a date-only endDate
("YYYY-MM-DD") which the backend parsed as 00:00 UTC. _fetch_binance_range
clamps results to <= end_ts, so the entire current day's candles were silently
excluded -- the update "succeeded" while OHLCV freshness stayed stale. The
thick client used datetime.now(UTC) as the end and did not have this problem.

Fix: a date-only end on/after today is extended to the real current time, and
the success message now reflects how many new bars (if any) were downloaded.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import fakeredis
import fakeredis.aioredis as fake_aio
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import make_token

pytestmark = [
    pytest.mark.bug("BTCAAAAA-36508"),
    pytest.mark.regression,
]


@pytest.fixture
def valid_token() -> str:
    return make_token()


@pytest.fixture
def sync_client():
    """Self-contained API client backed by fakeredis (bug_regression dir does
    not inherit tests/api/conftest.py fixtures)."""
    server = fakeredis.FakeServer()
    async_client = fake_aio.FakeRedis(server=server, decode_responses=True)
    with patch("src.api.app.make_async_client", return_value=async_client):
        import src.api.app as api_app
        with TestClient(api_app.app, raise_server_exceptions=True) as c:
            yield c, None


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _empty_manager(captured: dict) -> MagicMock:
    """A manager whose _fetch_binance_range records its window and returns no bars."""
    manager = MagicMock()

    def fake_fetch(timeframe, start_ts, end_ts, **_kw):
        captured[timeframe] = (start_ts, end_ts)
        return pd.DataFrame()

    manager._fetch_binance_range.side_effect = fake_fetch
    return manager


class TestEndDateExtendedPastMidnight:
    def test_date_only_today_end_extends_into_current_day(self, sync_client, valid_token):
        client, _ = sync_client
        captured: dict = {}
        manager = _empty_manager(captured)

        now = datetime.now(timezone.utc)
        start = (now - timedelta(days=7)).date().isoformat()
        end = now.date().isoformat()  # date-only, parses to 00:00 UTC

        with patch("src.api.app._get_unified_manager", return_value=manager), \
                patch("requests.get") as mock_get:
            mock_get.return_value.raise_for_status.return_value = None
            resp = client.post(
                "/data/update",
                json={"startDate": start, "endDate": end},
                headers=_auth(valid_token),
            )

        assert resp.status_code == 200
        assert captured, "_fetch_binance_range was never called"

        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        for tf, (_s, end_ts) in captured.items():
            end_aware = end_ts if end_ts.tzinfo else end_ts.replace(tzinfo=timezone.utc)
            assert end_aware > midnight, (
                f"{tf}: end {end_ts} was not extended past 00:00 UTC -- the current "
                f"day's candles would be silently excluded"
            )

    def test_end_never_fetches_into_the_future(self, sync_client, valid_token):
        client, _ = sync_client
        captured: dict = {}
        manager = _empty_manager(captured)

        now = datetime.now(timezone.utc)
        start = (now - timedelta(days=1)).date().isoformat()
        future = (now + timedelta(days=5)).date().isoformat()

        with patch("src.api.app._get_unified_manager", return_value=manager), \
                patch("requests.get") as mock_get:
            mock_get.return_value.raise_for_status.return_value = None
            resp = client.post(
                "/data/update",
                json={"startDate": start, "endDate": future},
                headers=_auth(valid_token),
            )

        assert resp.status_code == 200
        after = datetime.now(timezone.utc) + timedelta(seconds=2)
        for tf, (_s, end_ts) in captured.items():
            end_aware = end_ts if end_ts.tzinfo else end_ts.replace(tzinfo=timezone.utc)
            assert end_aware <= after, f"{tf}: end {end_ts} fetched into the future"

    def test_explicit_historical_range_is_preserved(self, sync_client, valid_token):
        """A date-only end strictly before today must NOT be bumped to now.

        Per BTCAAAAA-36499 (which superseded 36508's midnight-only logic), a
        date-only endDate is interpreted as the END of that day so the day's own
        candles are included. A historical end therefore lands at 23:59:59 of the
        requested day — still firmly historical, never bumped forward to now.
        """
        client, _ = sync_client
        captured: dict = {}
        manager = _empty_manager(captured)

        with patch("src.api.app._get_unified_manager", return_value=manager), \
                patch("requests.get") as mock_get:
            mock_get.return_value.raise_for_status.return_value = None
            resp = client.post(
                "/data/update",
                json={"startDate": "2024-01-01", "endDate": "2024-03-01"},
                headers=_auth(valid_token),
            )

        assert resp.status_code == 200
        for tf, (_s, end_ts) in captured.items():
            end_aware = end_ts if end_ts.tzinfo else end_ts.replace(tzinfo=timezone.utc)
            assert end_aware == datetime(2024, 3, 1, 23, 59, 59, tzinfo=timezone.utc), (
                f"{tf}: historical end {end_ts} was incorrectly modified"
            )


class TestHonestSuccessMessage:
    def test_zero_new_bars_reports_already_up_to_date(self, sync_client, valid_token):
        client, _ = sync_client
        manager = _empty_manager({})

        now = datetime.now(timezone.utc)
        with patch("src.api.app._get_unified_manager", return_value=manager), \
                patch("requests.get") as mock_get:
            mock_get.return_value.raise_for_status.return_value = None
            resp = client.post(
                "/data/update",
                json={
                    "startDate": (now - timedelta(days=1)).date().isoformat(),
                    "endDate": now.date().isoformat(),
                },
                headers=_auth(valid_token),
            )

        body = resp.json()
        assert resp.status_code == 200
        assert body["success"] is True
        assert "already up to date" in body["message"].lower()
        assert "complete" not in body["message"].lower()

    def test_downloaded_bars_reported_in_message(self, sync_client, valid_token):
        client, _ = sync_client
        manager = MagicMock()

        def fake_fetch(timeframe, start_ts, end_ts, **_kw):
            return pd.DataFrame({"timestamp": [end_ts]})

        manager._fetch_binance_range.side_effect = fake_fetch

        now = datetime.now(timezone.utc)
        with patch("src.api.app._get_unified_manager", return_value=manager), \
                patch("requests.get") as mock_get:
            mock_get.return_value.raise_for_status.return_value = None
            resp = client.post(
                "/data/update",
                json={
                    "startDate": (now - timedelta(days=1)).date().isoformat(),
                    "endDate": now.date().isoformat(),
                },
                headers=_auth(valid_token),
            )

        body = resp.json()
        assert resp.status_code == 200
        assert body["success"] is True
        assert "new bars downloaded" in body["message"].lower()
        # one bar per timeframe (15m, 1h, 1d) -> 3
        assert "3" in body["message"]
        manager._save_binance_bars.assert_called()
