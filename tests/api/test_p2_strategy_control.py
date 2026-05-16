"""
BTE-TC-P2-001: P2 write endpoints — strategy enable/disable + emergency halt.

Tests:
  POST /strategies/{id}/enable
  POST /strategies/{id}/disable
  POST /halt

All require JWT.  Registry is injected via configure() before each test.
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from .conftest import make_token


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_entry(state: str = "active", strategy_id: str | None = None) -> MagicMock:
    """Build a mock StrategyEntry with the given lifecycle state."""
    sid = strategy_id or f"strat-{uuid.uuid4().hex[:8]}"
    entry = MagicMock()
    entry.strategy_id = sid
    entry.state.value = state
    entry.is_active = state == "active"
    entry.is_paused = state == "paused"
    entry.is_stopped = state == "stopped"
    return entry


def _make_registry(entries: list[MagicMock] | None = None) -> MagicMock:
    """Build a mock StrategyRegistry."""
    entries = entries or []
    registry = MagicMock()
    entry_map = {e.strategy_id: e for e in entries}

    registry.get.side_effect = lambda sid: entry_map.get(sid)
    registry.all_entries.return_value = entries
    registry.active_entries.return_value = [e for e in entries if e.state.value == "active"]
    return registry


@pytest.fixture
def app_p2(fake_redis):
    """FastAPI app with fakeredis and a mock registry injected."""
    import fakeredis.aioredis as fake_aio
    from unittest.mock import patch
    _, server, _ = fake_redis

    async_client = fake_aio.FakeRedis(server=server, decode_responses=True)

    with patch("src.api.app.make_async_client", return_value=async_client):
        import src.api.app as api_app
        api_app._registry = None  # reset
        yield api_app


@pytest.fixture
def token():
    return make_token()


# ---------------------------------------------------------------------------
# Auth checks for P2 endpoints
# ---------------------------------------------------------------------------

_P2_POST_ENDPOINTS = [
    "/strategies/some-id/enable",
    "/strategies/some-id/disable",
    "/halt",
]


@pytest.mark.parametrize("path", _P2_POST_ENDPOINTS)
def test_p2_401_without_token(app_p2, path):
    with TestClient(app_p2.app, raise_server_exceptions=True) as client:
        resp = client.post(path)
    assert resp.status_code == 401, f"{path} should return 401 without token"


# ---------------------------------------------------------------------------
# 503 when registry not configured
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", _P2_POST_ENDPOINTS)
def test_p2_503_no_registry(app_p2, token, path):
    app_p2._registry = None  # explicitly not configured
    with TestClient(app_p2.app, raise_server_exceptions=True) as client:
        resp = client.post(path, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 503, f"{path} should return 503 when registry not injected"


# ---------------------------------------------------------------------------
# POST /strategies/{id}/enable
# ---------------------------------------------------------------------------


def test_enable_strategy_success(app_p2, token):
    entry_before = _make_entry(state="paused", strategy_id="strat-alpha")
    entry_after = _make_entry(state="active", strategy_id="strat-alpha")

    registry = _make_registry([entry_before])
    # activate() returns the updated entry
    registry.activate.return_value = entry_after

    app_p2._registry = registry

    with TestClient(app_p2.app, raise_server_exceptions=True) as client:
        resp = client.post(
            "/strategies/strat-alpha/enable",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["strategy_id"] == "strat-alpha"
    assert data["previous_state"] == "paused"
    assert data["current_state"] == "active"
    assert data["action"] == "enabled"
    assert "timestamp" in data
    registry.activate.assert_called_once_with("strat-alpha")


def test_enable_strategy_not_found(app_p2, token):
    registry = _make_registry([])  # empty registry
    app_p2._registry = registry

    with TestClient(app_p2.app, raise_server_exceptions=True) as client:
        resp = client.post(
            "/strategies/nonexistent/enable",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 404
    assert "nonexistent" in resp.json()["detail"]


def test_enable_strategy_conflict_stopped(app_p2, token):
    """Enabling a STOPPED strategy raises StrategyRegistryError → 409."""
    from src.itm.orchestrator.registry import StrategyRegistryError

    entry = _make_entry(state="stopped", strategy_id="strat-beta")
    registry = _make_registry([entry])
    registry.activate.side_effect = StrategyRegistryError("Cannot activate stopped strategy")
    app_p2._registry = registry

    with TestClient(app_p2.app, raise_server_exceptions=True) as client:
        resp = client.post(
            "/strategies/strat-beta/enable",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 409
    assert "stopped" in resp.json()["detail"].lower()


def test_enable_already_active_is_idempotent(app_p2, token):
    """Registry.activate() is a no-op for ACTIVE strategies; API returns 200."""
    entry = _make_entry(state="active", strategy_id="strat-gamma")
    registry = _make_registry([entry])
    registry.activate.return_value = entry  # returns same entry unchanged
    app_p2._registry = registry

    with TestClient(app_p2.app, raise_server_exceptions=True) as client:
        resp = client.post(
            "/strategies/strat-gamma/enable",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["current_state"] == "active"


# ---------------------------------------------------------------------------
# POST /strategies/{id}/disable
# ---------------------------------------------------------------------------


def test_disable_strategy_success(app_p2, token):
    entry_before = _make_entry(state="active", strategy_id="strat-delta")
    entry_after = _make_entry(state="paused", strategy_id="strat-delta")

    registry = _make_registry([entry_before])
    registry.pause.return_value = entry_after
    app_p2._registry = registry

    with TestClient(app_p2.app, raise_server_exceptions=True) as client:
        resp = client.post(
            "/strategies/strat-delta/disable",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["strategy_id"] == "strat-delta"
    assert data["previous_state"] == "active"
    assert data["current_state"] == "paused"
    assert data["action"] == "disabled"
    # Reason must be api:disabled
    registry.pause.assert_called_once_with("strat-delta", reason="api:disabled")


def test_disable_strategy_not_found(app_p2, token):
    registry = _make_registry([])
    app_p2._registry = registry

    with TestClient(app_p2.app, raise_server_exceptions=True) as client:
        resp = client.post(
            "/strategies/ghost/disable",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 404


def test_disable_strategy_conflict_stopped(app_p2, token):
    from src.itm.orchestrator.registry import StrategyRegistryError

    entry = _make_entry(state="stopped", strategy_id="strat-zeta")
    registry = _make_registry([entry])
    registry.pause.side_effect = StrategyRegistryError("Cannot pause stopped strategy")
    app_p2._registry = registry

    with TestClient(app_p2.app, raise_server_exceptions=True) as client:
        resp = client.post(
            "/strategies/strat-zeta/disable",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# POST /halt
# ---------------------------------------------------------------------------


def test_halt_pauses_all_active(app_p2, token):
    entries = [
        _make_entry(state="active", strategy_id="s1"),
        _make_entry(state="active", strategy_id="s2"),
        _make_entry(state="paused", strategy_id="s3"),  # already paused — not in active_entries
    ]
    registry = _make_registry(entries)
    # active_entries returns only active ones
    registry.active_entries.return_value = [e for e in entries if e.state.value == "active"]
    paused_entry = _make_entry(state="paused")
    registry.pause.return_value = paused_entry
    app_p2._registry = registry

    with TestClient(app_p2.app, raise_server_exceptions=True) as client:
        resp = client.post("/halt", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "halted"
    assert data["halted_count"] == 2
    assert set(data["halted_strategy_ids"]) == {"s1", "s2"}
    assert registry.pause.call_count == 2
    # Verify reason used
    calls = registry.pause.call_args_list
    for call in calls:
        assert call.kwargs.get("reason") == "emergency_halt" or call.args[1] == "emergency_halt"


def test_halt_empty_registry(app_p2, token):
    """Halt with no active strategies returns 200 with count 0."""
    registry = _make_registry([])
    app_p2._registry = registry

    with TestClient(app_p2.app, raise_server_exceptions=True) as client:
        resp = client.post("/halt", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["halted_count"] == 0
    assert data["halted_strategy_ids"] == []
    assert data["status"] == "halted"


def test_halt_partial_failure_continues(app_p2, token):
    """Halt continues even if one strategy's pause raises an unexpected error."""
    from src.itm.orchestrator.registry import StrategyRegistryError

    entries = [
        _make_entry(state="active", strategy_id="ok"),
        _make_entry(state="active", strategy_id="bad"),
    ]
    registry = _make_registry(entries)
    registry.active_entries.return_value = entries

    ok_paused = _make_entry(state="paused", strategy_id="ok")

    def _pause_side_effect(sid, reason):
        if sid == "bad":
            raise Exception("Simulated failure")
        return ok_paused

    registry.pause.side_effect = _pause_side_effect
    app_p2._registry = registry

    with TestClient(app_p2.app, raise_server_exceptions=True) as client:
        resp = client.post("/halt", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    data = resp.json()
    # Only 'ok' succeeded
    assert data["halted_count"] == 1
    assert "ok" in data["halted_strategy_ids"]
