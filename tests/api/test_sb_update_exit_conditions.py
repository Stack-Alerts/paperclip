"""
Tests for PUT /strategy-builder/strategies/{id} exitConditions support
(BTCAAAAA-36755, save-side).

The read-side fix (PR #109) made _build_sb_strategy surface
`strategy_versions.exit_conditions` as `exitConditions` on GET. The save-side
fix here makes the PUT body accept the same field and write it to the new
version row's `exit_conditions` JSONB column so the user's strategy-level
exits round-trip end-to-end.

Three cases:
  1. Supplied exitConditions are written onto the new version row.
  2. Omitting exitConditions inherits the prior version's exit_conditions
     (back-compat — older clients don't send the field).
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

_SAMPLE_STRATEGY_EXITS = [
    {
        "signal_name": "ELMA_CROSSOVER",
        "percentage": 0.5,
        "exit_mode": "ABSOLUTE",
        "tp_proximity_threshold": 2.0,
        "reversal_trigger": False,
        "binding_level": "STRATEGY",
    },
    {
        "signal_name": "ANCHORED_VWAP",
        "percentage": 0.33,
        "exit_mode": "TP_AWARE",
        "tp_proximity_threshold": 1.5,
        "reversal_trigger": True,
        "binding_level": "STRATEGY",
    },
]
_PRIOR_STRATEGY_EXITS = [
    {
        "signal_name": "RANGE_LIQUIDITY",
        "percentage": 1.0,
        "exit_mode": "ABSOLUTE",
        "binding_level": "STRATEGY",
    }
]


def _make_version(strategy_id: str, exit_conditions: list) -> dict:
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
        "exit_conditions": exit_conditions,
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


def _build_mock_db(strategy_id: str, prior_exits: list) -> MagicMock:
    """Return a mock DB manager that simulates scoped_managers context."""
    prior_version = _make_version(strategy_id, prior_exits)
    new_version_id = str(uuid.uuid4())

    written_version_data: dict = {}

    def fake_create_strategy_version(data: dict) -> str:
        written_version_data.update(data)
        return new_version_id

    scoped = MagicMock()
    scoped.strategy.get_latest_version.return_value = prior_version
    scoped.strategy.create_strategy_version.side_effect = fake_create_strategy_version
    scoped.strategy.rename_strategy.return_value = True
    new_version = _make_version(
        strategy_id, written_version_data.get("exit_conditions", prior_exits)
    )
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


def test_sb_update_writes_exit_conditions_when_supplied(app_with_fake_redis):
    """PUT with exitConditions:[...] writes the supplied list onto the new
    version row's exit_conditions column (BTCAAAAA-36755 save-side)."""
    app, _ = app_with_fake_redis
    strategy_id = str(uuid.uuid4())
    db = _build_mock_db(strategy_id, _PRIOR_STRATEGY_EXITS)

    with patch("src.api.app._get_sb_db", return_value=db):
        with TestClient(app, raise_server_exceptions=True) as client:
            resp = _put(
                client,
                strategy_id,
                {"name": "MyStrategy", "exitConditions": _SAMPLE_STRATEGY_EXITS},
                make_token(),
            )

    assert resp.status_code == 200
    call_args = db._scoped.strategy.create_strategy_version.call_args[0][0]
    # The body field is camelCase (exitConditions) but the JSONB column is
    # snake_case (exit_conditions) — that's the contract this test pins.
    assert call_args["exit_conditions"] == _SAMPLE_STRATEGY_EXITS


def test_sb_update_inherits_exit_conditions_when_omitted(app_with_fake_redis):
    """PUT without exitConditions keeps the prior version's exit_conditions
    (back-compat — older clients don't send the field)."""
    app, _ = app_with_fake_redis
    strategy_id = str(uuid.uuid4())
    db = _build_mock_db(strategy_id, _PRIOR_STRATEGY_EXITS)

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
    # exit_conditions must equal the prior version's exit_conditions
    # (inherited, not overwritten with null/empty).
    assert call_args["exit_conditions"] == _PRIOR_STRATEGY_EXITS


def test_sb_update_empty_exit_conditions_list(app_with_fake_redis):
    """PUT with exitConditions:[] writes empty list, distinguishable from
    'inherit' (matches the analogous empty-blocks-list contract)."""
    app, _ = app_with_fake_redis
    strategy_id = str(uuid.uuid4())
    db = _build_mock_db(strategy_id, _PRIOR_STRATEGY_EXITS)

    with patch("src.api.app._get_sb_db", return_value=db):
        with TestClient(app, raise_server_exceptions=True) as client:
            resp = _put(
                client,
                strategy_id,
                {"name": "MyStrategy", "exitConditions": []},
                make_token(),
            )

    assert resp.status_code == 200
    call_args = db._scoped.strategy.create_strategy_version.call_args[0][0]
    assert call_args["exit_conditions"] == []
