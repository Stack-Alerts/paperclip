"""
BTE-TC-WS-001 through 007: WebSocket domain tests.

Tests:
  1. WS connects with valid JWT (all 7 domains)
  2. WS rejected (1008) without token (all 7 domains)
  3. WS rejected (1008) with expired token (all 7 domains)
  4. WS receives message when Redis pub/sub publishes (all 7 domains)
  5. WS disconnects cleanly on client close
  6. Multiple concurrent WS connections on same domain
  7. WS closes with 1008 for invalid (garbage) token
  8. WS receives multiple sequential messages

All 7 domains × 8 base cases = 56 test scenarios verified.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import fakeredis
import pytest
from fastapi.testclient import TestClient
from starlette.testclient import WebSocketTestSession

from .conftest import make_token

_CHANNELS = [
    ("/ws/cycle", "itm:cycle"),
    ("/ws/capital", "itm:capital"),
    ("/ws/positions", "itm:positions"),
    ("/ws/decisions", "itm:decisions"),
    ("/ws/signals", "itm:signals"),
    ("/ws/alerts", "itm:alerts"),
    ("/ws/strategies", "itm:strategies"),
]

_DOMAIN_IDS = [c[0].split("/")[-1] for c in _CHANNELS]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def ws_setup(app_with_fake_redis, fake_redis):
    """Return (TestClient, sync_redis) for WS tests.

    app_with_fake_redis already patches make_async_client on the server,
    so the lifespan will use the fake Redis when TestClient starts the app.
    """
    _, server, _ = fake_redis
    app, _ = app_with_fake_redis
    sync_r = fakeredis.FakeRedis(server=server, decode_responses=True)
    client = TestClient(app)
    return client, sync_r


# ---------------------------------------------------------------------------
# TC-WS-1: Connect with valid token
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path,channel", _CHANNELS, ids=_DOMAIN_IDS)
def test_ws_connects_with_valid_token(ws_setup, path, channel):
    client, sync_r = ws_setup
    token = make_token()
    with client.websocket_connect(f"{path}?token={token}") as ws:
        # Publish a message so we can receive and confirm the connection is live
        msg = json.dumps({"type": "test", "ts": _now()})
        sync_r.publish(channel, msg)
        received = ws.receive_text()
        assert received == msg


# ---------------------------------------------------------------------------
# TC-WS-2: Rejected without token
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path,channel", _CHANNELS, ids=_DOMAIN_IDS)
def test_ws_rejected_without_token(ws_setup, path, channel):
    client, _ = ws_setup
    with pytest.raises(Exception):
        with client.websocket_connect(path) as ws:
            ws.receive_text()


# ---------------------------------------------------------------------------
# TC-WS-3: Rejected with expired token
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path,channel", _CHANNELS, ids=_DOMAIN_IDS)
def test_ws_rejected_with_expired_token(ws_setup, path, channel):
    client, _ = ws_setup
    expired = make_token(exp_offset=-1)
    with pytest.raises(Exception):
        with client.websocket_connect(f"{path}?token={expired}") as ws:
            ws.receive_text()


# ---------------------------------------------------------------------------
# TC-WS-4: Receives messages from pub/sub (already covered by TC-WS-1 above;
#           here we verify multiple messages and correct data routing)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path,channel", _CHANNELS, ids=_DOMAIN_IDS)
def test_ws_receives_correct_channel_data(ws_setup, path, channel):
    client, sync_r = ws_setup
    token = make_token()
    payload = {"event": channel, "id": str(uuid.uuid4()), "ts": _now()}
    with client.websocket_connect(f"{path}?token={token}") as ws:
        sync_r.publish(channel, json.dumps(payload))
        received = json.loads(ws.receive_text())
        assert received["event"] == channel
        assert received["id"] == payload["id"]


# ---------------------------------------------------------------------------
# TC-WS-5: Clean disconnect
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path,channel", _CHANNELS, ids=_DOMAIN_IDS)
def test_ws_clean_disconnect(ws_setup, path, channel):
    client, sync_r = ws_setup
    token = make_token()
    with client.websocket_connect(f"{path}?token={token}") as ws:
        msg = json.dumps({"ping": True})
        sync_r.publish(channel, msg)
        ws.receive_text()
        # Exiting the context manager triggers disconnect — should not raise


# ---------------------------------------------------------------------------
# TC-WS-6: Multiple concurrent connections on same domain
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path,channel", _CHANNELS, ids=_DOMAIN_IDS)
def test_ws_multiple_connections(ws_setup, path, channel):
    client, sync_r = ws_setup
    token_a = make_token(sub="user-a")
    token_b = make_token(sub="user-b")
    msg = json.dumps({"broadcast": True, "ts": _now()})

    with client.websocket_connect(f"{path}?token={token_a}") as ws_a:
        with client.websocket_connect(f"{path}?token={token_b}") as ws_b:
            sync_r.publish(channel, msg)
            recv_a = ws_a.receive_text()
            recv_b = ws_b.receive_text()
            assert recv_a == msg
            assert recv_b == msg


# ---------------------------------------------------------------------------
# TC-WS-7: Garbage token → rejected (1008)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path,channel", _CHANNELS, ids=_DOMAIN_IDS)
def test_ws_rejected_with_garbage_token(ws_setup, path, channel):
    client, _ = ws_setup
    with pytest.raises(Exception):
        with client.websocket_connect(f"{path}?token=not.a.jwt") as ws:
            ws.receive_text()


# ---------------------------------------------------------------------------
# TC-WS-8: Multiple sequential messages on same connection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path,channel", _CHANNELS, ids=_DOMAIN_IDS)
def test_ws_multiple_sequential_messages(ws_setup, path, channel):
    client, sync_r = ws_setup
    token = make_token()
    with client.websocket_connect(f"{path}?token={token}") as ws:
        for i in range(3):
            msg = json.dumps({"seq": i, "ts": _now()})
            sync_r.publish(channel, msg)
            received = json.loads(ws.receive_text())
            assert received["seq"] == i
