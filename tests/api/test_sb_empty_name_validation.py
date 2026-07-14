"""
Tests for empty-name validation on the strategy-builder endpoints (BTCAAAAA-39319).

Before the fix, an empty ``name`` propagated to the ORM and surfaced as a generic
500. The contract here is that empty names are rejected at the FastAPI layer with
a structured 422 carrying field-level detail.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from .conftest import make_token


def _post(client: TestClient, body: dict, token: str) -> object:
    return client.post(
        "/strategy-builder/strategies",
        json=body,
        headers={"Authorization": f"Bearer {token}"},
    )


def _put(client: TestClient, strategy_id: str, body: dict, token: str) -> object:
    return client.put(
        f"/strategy-builder/strategies/{strategy_id}",
        json=body,
        headers={"Authorization": f"Bearer {token}"},
    )


def _make_version(strategy_id: str) -> dict:
    """Return a minimal version dict as returned by get_latest_version."""
    vid = str(uuid.uuid4())
    return {
        "version_id": vid,
        "version_number": 1,
        "strategy_id": strategy_id,
        "name": "MyStrategy",
        "description": "",
        "blocks": [],
        "signals": {},
        "parameters": {},
        "entry_conditions": {},
        "exit_conditions": {},
        "risk_management": {},
        "backtest_config": {},
        "tags": [],
        "validation_history": [],
        "strategy_type": None,
        "timestamp": "2026-01-01T00:00:00Z",
        "created_at": "2026-01-01T00:00:00Z",
        "config_hash": None,
        "validation_timestamp": None,
    }


def _build_mock_db_for_create() -> MagicMock:
    """Mock DB manager that records the create_strategy call.

    The POST endpoint uses ``db.strategy.*`` directly (no
    ``scoped_managers`` context), unlike the PUT path.
    """
    created_strategy_id = str(uuid.uuid4())
    created_version_id = str(uuid.uuid4())

    new_version = _make_version(created_strategy_id)
    new_version["version_id"] = created_version_id

    db = MagicMock()
    db.strategy.create_strategy.return_value = created_strategy_id
    db.strategy.create_strategy_version.return_value = created_version_id
    db.strategy.get_strategy_version.return_value = new_version
    return db


def _build_mock_db_for_update(strategy_id: str) -> MagicMock:
    """Mock DB manager for the PUT path (no ORM call should happen on empty name)."""
    prior_version = _make_version(strategy_id)
    new_version_id = str(uuid.uuid4())

    scoped = MagicMock()
    scoped.strategy.get_latest_version.return_value = prior_version
    scoped.strategy.create_strategy_version.return_value = new_version_id
    scoped.strategy.rename_strategy.return_value = True
    new_version = _make_version(strategy_id)
    new_version["version_id"] = new_version_id
    scoped.strategy.get_strategy_version.return_value = new_version
    scoped.test_results.get_version_test_results.return_value = []

    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=scoped)
    ctx.__exit__ = MagicMock(return_value=False)

    db = MagicMock()
    db.scoped_managers.return_value = ctx
    db._scoped = scoped
    return db


# ---------------------------------------------------------------------------
# POST /strategy-builder/strategies — empty name rejected with 422
# ---------------------------------------------------------------------------


def test_post_create_rejects_empty_name(app_with_fake_redis):
    """Empty name must return 422 instead of bubbling up as 500."""
    app, _ = app_with_fake_redis
    db = _build_mock_db_for_create()

    with patch("src.api.app._get_sb_db", return_value=db):
        with TestClient(app, raise_server_exceptions=True) as client:
            resp = _post(client, {"name": ""}, make_token())

    assert resp.status_code == 422
    # Must NOT have touched the ORM
    db.strategy.create_strategy.assert_not_called()
    db.strategy.create_strategy_version.assert_not_called()


def test_post_create_accepts_nonempty_name(app_with_fake_redis):
    """Sanity check: a valid name still passes through to the ORM."""
    app, _ = app_with_fake_redis
    db = _build_mock_db_for_create()

    with patch("src.api.app._get_sb_db", return_value=db):
        with TestClient(app, raise_server_exceptions=True) as client:
            resp = _post(client, {"name": "RealStrategy"}, make_token())

    assert resp.status_code == 201
    db.strategy.create_strategy.assert_called_once_with("RealStrategy")


def test_post_create_rejects_missing_name(app_with_fake_redis):
    """Missing name is also a 422 (was already required, but worth pinning)."""
    app, _ = app_with_fake_redis
    db = _build_mock_db_for_create()

    with patch("src.api.app._get_sb_db", return_value=db):
        with TestClient(app, raise_server_exceptions=True) as client:
            resp = _post(client, {"description": "no name"}, make_token())

    assert resp.status_code == 422
    db.strategy.create_strategy.assert_not_called()


# ---------------------------------------------------------------------------
# PUT /strategy-builder/strategies/{id} — empty name rejected with 422
# ---------------------------------------------------------------------------


def test_put_update_rejects_empty_name(app_with_fake_redis):
    """Empty name on the update path must return 422 instead of 500."""
    app, _ = app_with_fake_redis
    strategy_id = str(uuid.uuid4())
    db = _build_mock_db_for_update(strategy_id)

    with patch("src.api.app._get_sb_db", return_value=db):
        with TestClient(app, raise_server_exceptions=True) as client:
            resp = _put(client, strategy_id, {"name": ""}, make_token())

    assert resp.status_code == 422
    # ORM must not have been touched
    db._scoped.strategy.create_strategy_version.assert_not_called()
    db._scoped.strategy.get_latest_version.assert_not_called()


def test_put_update_accepts_nonempty_name(app_with_fake_redis):
    """Sanity check: a valid name on PUT still writes a new version."""
    app, _ = app_with_fake_redis
    strategy_id = str(uuid.uuid4())
    db = _build_mock_db_for_update(strategy_id)

    with patch("src.api.app._get_sb_db", return_value=db):
        with TestClient(app, raise_server_exceptions=True) as client:
            resp = _put(
                client,
                strategy_id,
                {"name": "RenamedStrategy"},
                make_token(),
            )

    assert resp.status_code == 200
    call_args = db._scoped.strategy.create_strategy_version.call_args[0][0]
    assert call_args["name"] == "RenamedStrategy"
