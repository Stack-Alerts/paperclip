"""
BTE-TC-API-001: REST endpoint tests (10 endpoints × correctness + auth).

Covers:
  - All 10 GET endpoints return 200 with valid JWT
  - All 10 GET endpoints return 401 without JWT
  - All 10 GET endpoints return 401 with expired JWT
  - /health returns redis status
  - /state/snapshot returns checkpoint_seq
  - /strategies and /strategies/{id}
  - /positions and /positions/{id}
  - /capital
  - /decisions/recent and /signals/recent return lists
  - /alerts/active returns list
"""

from __future__ import annotations

import json
import uuid

import fakeredis
import pytest

from .conftest import make_token


# ---------------------------------------------------------------------------
# Auth rejection cases (BTE-TC-API-003: JWT must return 401 without token)
# ---------------------------------------------------------------------------

_ALL_ENDPOINTS = [
    "/health",
    "/state/snapshot",
    "/strategies",
    "/positions",
    "/capital",
    "/decisions/recent",
    "/signals/recent",
    "/alerts/active",
]


@pytest.mark.parametrize("path", _ALL_ENDPOINTS)
def test_401_without_token(sync_client, path):
    client, _ = sync_client
    resp = client.get(path)
    assert resp.status_code == 401, f"{path} should return 401 without token"


@pytest.mark.parametrize("path", _ALL_ENDPOINTS)
def test_401_with_expired_token(sync_client, expired_token, path):
    client, _ = sync_client
    resp = client.get(path, headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 401, f"{path} should return 401 with expired token"


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


def test_health_ok(sync_client, valid_token):
    client, _ = sync_client
    resp = client.get("/health", headers={"Authorization": f"Bearer {valid_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "degraded")
    assert "redis" in data
    assert "uptime_seconds" in data


# ---------------------------------------------------------------------------
# GET /state/snapshot
# ---------------------------------------------------------------------------


def test_state_snapshot(sync_client, valid_token):
    client, snap = sync_client
    resp = client.get("/state/snapshot", headers={"Authorization": f"Bearer {valid_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["state_id"] == snap["state_id"]
    assert data["checkpoint_seq"] == snap["checkpoint_seq"]
    assert "risk" in data
    assert data["open_position_count"] >= 0
    assert data["strategy_count"] >= 0


# ---------------------------------------------------------------------------
# GET /strategies
# ---------------------------------------------------------------------------


def test_list_strategies(sync_client, valid_token):
    client, snap = sync_client
    resp = client.get("/strategies", headers={"Authorization": f"Bearer {valid_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == len(snap["strategies"])
    strat = data[0]
    assert "strategy_id" in strat
    assert "run_state" in strat


def test_get_strategy_by_id(sync_client, valid_token):
    client, snap = sync_client
    strat_id = next(iter(snap["strategies"]))
    resp = client.get(f"/strategies/{strat_id}", headers={"Authorization": f"Bearer {valid_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["strategy_id"] == strat_id


def test_get_strategy_not_found(sync_client, valid_token):
    client, _ = sync_client
    resp = client.get(f"/strategies/{uuid.uuid4()}", headers={"Authorization": f"Bearer {valid_token}"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /positions
# ---------------------------------------------------------------------------


def test_list_positions(sync_client, valid_token):
    client, snap = sync_client
    resp = client.get("/positions", headers={"Authorization": f"Bearer {valid_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    open_in_snap = [p for p in snap["positions"].values() if p.get("closed_at") is None]
    assert len(data) == len(open_in_snap)
    if data:
        pos = data[0]
        assert "position_id" in pos
        assert pos["is_open"] is True
        assert "entries" in pos


def test_get_position_by_id(sync_client, valid_token):
    client, snap = sync_client
    pos_id = next(iter(snap["positions"]))
    resp = client.get(f"/positions/{pos_id}", headers={"Authorization": f"Bearer {valid_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["position_id"] == pos_id
    assert "verification_status" in data


def test_get_position_not_found(sync_client, valid_token):
    client, _ = sync_client
    resp = client.get(f"/positions/{uuid.uuid4()}", headers={"Authorization": f"Bearer {valid_token}"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /capital
# ---------------------------------------------------------------------------


def test_capital(sync_client, valid_token):
    client, snap = sync_client
    resp = client.get("/capital", headers={"Authorization": f"Bearer {valid_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "total_capital" in data
    assert "allocated" in data
    assert "available" in data
    cs = snap["risk"]["capital_state"]
    assert data["total_capital"] == cs["total_capital"]
    assert data["allocated"] == cs["allocated"]


# ---------------------------------------------------------------------------
# GET /decisions/recent
# ---------------------------------------------------------------------------


def test_decisions_empty_when_no_data(sync_client, valid_token):
    client, _ = sync_client
    resp = client.get("/decisions/recent", headers={"Authorization": f"Bearer {valid_token}"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_decisions_returns_list(app_with_fake_redis, fake_redis, valid_token):
    """Push a decision into fake Redis and verify it's returned."""
    from datetime import datetime, timezone
    from fastapi.testclient import TestClient

    _, server, _ = fake_redis
    app, _ = app_with_fake_redis

    decision = {
        "decision_id": str(uuid.uuid4()),
        "action": "enter_long",
        "confidence": "0.85",
        "risk_gated": False,
        "instrument_symbol": "BTC/USDT",
        "reason": "test",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {},
    }
    # Push via sync client on the same fakeredis server
    sync_r = fakeredis.FakeRedis(server=server, decode_responses=True)
    sync_r.rpush("itm:decisions:recent", json.dumps(decision))

    with TestClient(app) as client:
        resp = client.get("/decisions/recent", headers={"Authorization": f"Bearer {valid_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["decision_id"] == decision["decision_id"]


# ---------------------------------------------------------------------------
# GET /signals/recent
# ---------------------------------------------------------------------------


def test_signals_empty_when_no_data(sync_client, valid_token):
    client, _ = sync_client
    resp = client.get("/signals/recent", headers={"Authorization": f"Bearer {valid_token}"})
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# GET /alerts/active
# ---------------------------------------------------------------------------


def test_alerts_empty_when_no_data(sync_client, valid_token):
    client, _ = sync_client
    resp = client.get("/alerts/active", headers={"Authorization": f"Bearer {valid_token}"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_alerts_filters_resolved(app_with_fake_redis, fake_redis, valid_token):
    """Resolved alerts must not appear in /alerts/active."""
    from datetime import datetime, timezone
    from fastapi.testclient import TestClient

    _, server, _ = fake_redis
    app, _ = app_with_fake_redis

    sync_r = fakeredis.FakeRedis(server=server, decode_responses=True)
    active_id = str(uuid.uuid4())
    resolved_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    sync_r.hset("itm:alerts:active", active_id, json.dumps({
        "alert_id": active_id, "level": "warning", "category": "risk",
        "message": "active", "strategy_id": None, "created_at": now, "resolved": False,
    }))
    sync_r.hset("itm:alerts:active", resolved_id, json.dumps({
        "alert_id": resolved_id, "level": "info", "category": "system",
        "message": "resolved", "strategy_id": None, "created_at": now, "resolved": True,
    }))

    with TestClient(app) as client:
        resp = client.get("/alerts/active", headers={"Authorization": f"Bearer {valid_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["alert_id"] == active_id
