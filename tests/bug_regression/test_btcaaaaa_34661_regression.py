"""
BTCAAAAA-34661: Backend hardening — empty strategy name must return 422, not 500.

Parent BTCAAAAA-34658 guarded the frontend; this covers the backend contract:
_CreateSBStrategyRequest and _UpdateSBStrategyRequest enforce min_length=1 on
``name`` so Pydantic rejects the payload before the handler runs.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.app import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def test_create_strategy_empty_name_returns_422(client: TestClient) -> None:
    resp = client.post("/strategy-builder/strategies", json={"name": ""})
    assert resp.status_code == 422


def test_update_strategy_empty_name_returns_422(client: TestClient) -> None:
    resp = client.put(
        "/strategy-builder/strategies/nonexistent-id", json={"name": ""}
    )
    assert resp.status_code == 422


def test_create_strategy_missing_name_returns_422(client: TestClient) -> None:
    resp = client.post("/strategy-builder/strategies", json={})
    assert resp.status_code == 422
