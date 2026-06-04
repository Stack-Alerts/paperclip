"""
Tests for PUT /strategy-builder/strategies/{id} blocks support (BTCAAAAA-34625).

Three cases:
  1. Supplied blocks are written onto the new version row.
  2. Omitting blocks inherits the prior version's blocks (back-compat).
  3. Empty list is written as empty (distinguishable from "inherit").
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from .conftest import make_token


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SAMPLE_BLOCKS = [
    {"name": "EMA Cross", "logic": "ema_cross", "signals": {}, "exit_conditions": {}}
]
_PRIOR_BLOCKS = [
    {"name": "RSI Block", "logic": "rsi", "signals": {}, "exit_conditions": {}}
]


def _make_version(strategy_id: str, blocks: list) -> dict:
    """Return a minimal version dict as returned by get_latest_version."""
    vid = str(uuid.uuid4())
    return {
        "version_id": vid,
        "version_number": 1,
        "strategy_id": strategy_id,
        "name": "MyStrategy",
        "description": "",
        "blocks": blocks,
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


def _build_mock_db(strategy_id: str, prior_blocks: list) -> MagicMock:
    """Return a mock DB manager that simulates scoped_managers context."""
    prior_version = _make_version(strategy_id, prior_blocks)
    new_version_id = str(uuid.uuid4())

    written_version_data: dict = {}

    def fake_create_strategy_version(data: dict) -> str:
        written_version_data.update(data)
        return new_version_id

    scoped = MagicMock()
    scoped.strategy.get_latest_version.return_value = prior_version
    scoped.strategy.create_strategy_version.side_effect = fake_create_strategy_version
    scoped.strategy.rename_strategy.return_value = True
    new_version = _make_version(strategy_id, written_version_data.get("blocks", prior_blocks))
    scoped.strategy.get_strategy_version.return_value = new_version
    scoped.test_results.get_version_test_results.return_value = []

    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=scoped)
    ctx.__exit__ = MagicMock(return_value=False)

    db = MagicMock()
    db.scoped_managers.return_value = ctx

    db._scoped = scoped
    db._written = written_version_data
    db._new_version_id = new_version_id
    return db


def _put(client: TestClient, strategy_id: str, body: dict, token: str) -> object:
    return client.put(
        f"/strategy-builder/strategies/{strategy_id}",
        json=body,
        headers={"Authorization": f"Bearer {token}"},
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_sb_update_writes_blocks_when_supplied(app_with_fake_redis):
    """PUT with blocks:[...] writes the supplied list onto the new version."""
    app, _ = app_with_fake_redis
    strategy_id = str(uuid.uuid4())
    db = _build_mock_db(strategy_id, _PRIOR_BLOCKS)

    with patch("src.api.app._get_sb_db", return_value=db):
        with TestClient(app, raise_server_exceptions=True) as client:
            resp = _put(
                client,
                strategy_id,
                {"name": "MyStrategy", "blocks": _SAMPLE_BLOCKS},
                make_token(),
            )

    assert resp.status_code == 200
    call_args = db._scoped.strategy.create_strategy_version.call_args[0][0]
    assert call_args["blocks"] == _SAMPLE_BLOCKS


def test_sb_update_inherits_blocks_when_omitted(app_with_fake_redis):
    """PUT without blocks keeps the prior version's blocks (back-compat)."""
    app, _ = app_with_fake_redis
    strategy_id = str(uuid.uuid4())
    db = _build_mock_db(strategy_id, _PRIOR_BLOCKS)

    with patch("src.api.app._get_sb_db", return_value=db):
        with TestClient(app, raise_server_exceptions=True) as client:
            resp = _put(
                client,
                strategy_id,
                {"name": "MyStrategy"},
                make_token(),
            )

    assert resp.status_code == 200
    call_args = db._scoped.strategy.create_strategy_version.call_args[0][0]
    # blocks must equal the prior version's blocks (inherited, not overwritten)
    assert call_args["blocks"] == _PRIOR_BLOCKS


def test_sb_update_empty_blocks_list(app_with_fake_redis):
    """PUT with blocks:[] writes empty list, distinguishable from 'inherit'."""
    app, _ = app_with_fake_redis
    strategy_id = str(uuid.uuid4())
    db = _build_mock_db(strategy_id, _PRIOR_BLOCKS)

    with patch("src.api.app._get_sb_db", return_value=db):
        with TestClient(app, raise_server_exceptions=True) as client:
            resp = _put(
                client,
                strategy_id,
                {"name": "MyStrategy", "blocks": []},
                make_token(),
            )

    assert resp.status_code == 200
    call_args = db._scoped.strategy.create_strategy_version.call_args[0][0]
    assert call_args["blocks"] == []
