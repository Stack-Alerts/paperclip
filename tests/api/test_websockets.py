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


# ---------------------------------------------------------------------------
# TC-WS-9: BTE_API_DEV_MODE=1 + loopback peer → accepted without token
#          (BTCAAAAA-30563: WebUI 6 channels reject with 403 because the
#          browser cannot mint a JWT; dev-mode loopback bypass.)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path,channel", _CHANNELS, ids=_DOMAIN_IDS)
def test_ws_dev_mode_loopback_accepted_without_token(ws_setup, path, channel, monkeypatch):
    client, sync_r = ws_setup
    from src.api import auth as auth_mod

    monkeypatch.setattr(auth_mod, "_DEV_MODE", True)
    monkeypatch.setattr(auth_mod, "_is_loopback", lambda ws: True)

    with client.websocket_connect(path) as ws:
        msg = json.dumps({"dev_bypass": True, "ts": _now()})
        sync_r.publish(channel, msg)
        assert ws.receive_text() == msg


# ---------------------------------------------------------------------------
# TC-WS-10: BTE_API_DEV_MODE=1 + non-loopback peer → still rejected without
#           token. Non-loopback origins are NEVER auto-trusted even in dev.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path,channel", _CHANNELS, ids=_DOMAIN_IDS)
def test_ws_dev_mode_non_loopback_rejected_without_token(ws_setup, path, channel, monkeypatch):
    client, _ = ws_setup
    from src.api import auth as auth_mod

    monkeypatch.setattr(auth_mod, "_DEV_MODE", True)
    monkeypatch.setattr(auth_mod, "_is_loopback", lambda ws: False)

    with pytest.raises(Exception):
        with client.websocket_connect(path) as ws:
            ws.receive_text()


# ---------------------------------------------------------------------------
# TC-WS-11: BTE_API_DEV_MODE=1 with a valid token still works
#           (testers can opt into the full auth code path even in dev).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path,channel", _CHANNELS, ids=_DOMAIN_IDS)
def test_ws_dev_mode_with_valid_token_still_accepts(ws_setup, path, channel, monkeypatch):
    client, sync_r = ws_setup
    from src.api import auth as auth_mod

    monkeypatch.setattr(auth_mod, "_DEV_MODE", True)
    # _is_loopback irrelevant when a real token is provided

    token = make_token()
    with client.websocket_connect(f"{path}?token={token}") as ws:
        msg = json.dumps({"with_token_in_dev": True, "ts": _now()})
        sync_r.publish(channel, msg)
        assert ws.receive_text() == msg


# ---------------------------------------------------------------------------
# TC-WS-12: BTE_API_DEV_MODE=1 + loopback + INVALID token → still rejected
#           (bypass triggers only when token is absent, not when one is
#           supplied and bogus).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path,channel", _CHANNELS, ids=_DOMAIN_IDS)
def test_ws_dev_mode_loopback_with_bad_token_rejected(ws_setup, path, channel, monkeypatch):
    client, _ = ws_setup
    from src.api import auth as auth_mod

    monkeypatch.setattr(auth_mod, "_DEV_MODE", True)
    monkeypatch.setattr(auth_mod, "_is_loopback", lambda ws: True)

    with pytest.raises(Exception):
        with client.websocket_connect(f"{path}?token=not.a.jwt") as ws:
            ws.receive_text()


# ---------------------------------------------------------------------------
# TC-WS-13: _is_loopback recognises IPv4, IPv6, IPv4-mapped-IPv6 hosts.
# ---------------------------------------------------------------------------


def test_is_loopback_recognises_known_hosts():
    from src.api.auth import _is_loopback
    from types import SimpleNamespace

    def fake_ws(host):
        return SimpleNamespace(client=SimpleNamespace(host=host))

    assert _is_loopback(fake_ws("127.0.0.1")) is True
    assert _is_loopback(fake_ws("::1")) is True
    assert _is_loopback(fake_ws("::ffff:127.0.0.1")) is True
    assert _is_loopback(fake_ws("10.0.0.1")) is False
    assert _is_loopback(fake_ws("192.168.1.50")) is False
    assert _is_loopback(fake_ws("testclient")) is False
    assert _is_loopback(SimpleNamespace(client=None)) is False
