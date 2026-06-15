"""
Regression tests for BTCAAAAA-36499: ohlcv_15m gap "update successful" but
the gap never clears.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-36499
Component: src/api/app.py  (POST /data/update)

Root cause: the Market Data Update Manager sends a date-only ``endDate``
("2026-06-15") from the ``<input type="date">`` control. ``update_data``
parsed that as ``2026-06-15T00:00:00`` — midnight at the START of the day —
so the fetch window ``[start, midnight-today]`` excluded every candle from
the current day. Those trailing candles are exactly the "up to 1 day missing"
gap the user is trying to fill. The historical bars up to midnight downloaded
fine (success=True), but the gap persisted and re-running reported success
again without ever fetching today's bars.

Fix: interpret a date-only ``endDate`` as the END of that day, then clamp to
``now`` so the current day's trailing bars are included in the fetch window.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-36499"),
    pytest.mark.regression,
]


# The shared API fixtures live under tests/api/conftest.py and are only visible
# to that package, so re-expose the ones this test needs here.
@pytest.fixture
def valid_token() -> str:
    from tests.api.conftest import make_token
    return make_token()


@pytest.fixture
def sync_client():
    import json

    import fakeredis
    import fakeredis.aioredis as fake_aio
    from fastapi.testclient import TestClient
    from unittest.mock import patch

    from tests.api.conftest import _minimal_snapshot

    server = fakeredis.FakeServer()
    sync = fakeredis.FakeRedis(server=server, decode_responses=True)
    snap = _minimal_snapshot()
    sync.set("itm:state:snapshot", json.dumps(snap))
    async_client = fake_aio.FakeRedis(server=server, decode_responses=True)

    with patch("src.api.app.make_async_client", return_value=async_client):
        import src.api.app as api_app
        with TestClient(api_app.app, raise_server_exceptions=True) as c:
            yield c, snap


class _CapturingManager:
    """Fake UnifiedDataManager that records the fetch window per timeframe."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def _fetch_binance_range(self, timeframe, start_ts, end_ts, **kwargs):
        self.calls.append({
            "timeframe": timeframe,
            "start_ts": start_ts,
            "end_ts": end_ts,
        })
        # Return no bars so _save_binance_bars is never exercised.
        return pd.DataFrame()

    def _save_binance_bars(self, bars, tf):  # pragma: no cover - not reached
        raise AssertionError("should not save when fetch is empty")


@pytest.fixture
def _patched_update(monkeypatch):
    """Patch the data manager + Binance ping so /data/update runs offline."""
    import src.api.app as api_app

    fake = _CapturingManager()
    monkeypatch.setattr(api_app, "_get_unified_manager", lambda: fake)

    class _PingResp:
        def raise_for_status(self):
            return None

    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **k: _PingResp())
    return fake


def _post_update(sync_client, valid_token, start: str, end: str):
    client, _ = sync_client
    return client.post(
        "/data/update",
        json={"startDate": start, "endDate": end},
        headers={"Authorization": f"Bearer {valid_token}"},
    )


class TestDateOnlyEndDateReachesNow:
    def test_today_date_only_end_extends_to_now(
        self, sync_client, valid_token, _patched_update
    ):
        today = datetime.now(timezone.utc).date().isoformat()
        start = (datetime.now(timezone.utc) - timedelta(days=7)).date().isoformat()

        resp = _post_update(sync_client, valid_token, start, today)
        assert resp.status_code == 200, resp.text

        assert _patched_update.calls, "fetch was never invoked"
        end_ts = _patched_update.calls[0]["end_ts"]
        end_aware = end_ts if end_ts.tzinfo else end_ts.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        midnight_today = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        # The bug: end_ts stuck at 00:00:00 today. The fix pushes it to ~now,
        # so the current day's trailing bars fall inside the window.
        assert end_aware > midnight_today + timedelta(minutes=1), (
            f"end_ts {end_aware} did not advance past midnight-today — "
            "today's trailing bars would be excluded (BTCAAAAA-36499)"
        )
        # And never past now (no unformed future bars requested).
        assert end_aware <= now + timedelta(seconds=5), end_aware

    def test_historical_date_only_end_covers_full_day(
        self, sync_client, valid_token, _patched_update
    ):
        # A genuinely historical end date must include that day's last bars,
        # i.e. extend to end-of-day, not stop at 00:00:00.
        resp = _post_update(
            sync_client, valid_token, "2024-01-01", "2024-01-31"
        )
        assert resp.status_code == 200, resp.text

        end_ts = _patched_update.calls[0]["end_ts"]
        end_aware = end_ts if end_ts.tzinfo else end_ts.replace(tzinfo=timezone.utc)
        jan31_midnight = datetime(2024, 1, 31, tzinfo=timezone.utc)
        assert end_aware > jan31_midnight, (
            f"end_ts {end_aware} excludes Jan-31 bars — date-only end must "
            "cover the whole day"
        )
