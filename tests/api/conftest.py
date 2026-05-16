"""
Shared fixtures for BTE API tests.

Uses an in-memory Redis fake via fakeredis and a TestClient / AsyncClient
backed by the FastAPI app.

JWT signing uses the private key embedded here — must match the public key
in src/api/auth.py.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import AsyncGenerator

import fakeredis
import fakeredis.aioredis
import jwt
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

# Private key matching the public key embedded in auth.py
_PRIVATE_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEApRPgVCTtcOjPUtaAq/QiOFyjNyusoHlYLQgeHCE59JP6LJpx
qPZ5P+kfpojBAUwJ2HViypopyiHIbLoCRM6UGstyD8p/k+VNYF+NbXNIcQfkQxRQ
hima7QSQhD0ApgaKRRpARLHiOFmOcAZ9hoaQQFLqkbmPooyhokltdWd7iCgtX7gB
h2vktSznxHOztP/BCuYOmf9icD7nWMYnFaQ4NYBKgF0Xo36+TrSmAE3nPnagJkqE
RkWgtUa7qFpbQ9bRCS3kwHtDBh8585erJsvuSCjmKNes6u9M/cYImUuLApHGKo3Y
rRMVFWyZlMK4DDq3iaKV/Tz4Zg6sasNp6/Q4lQIDAQABAoIBABXxtnh5EDdaO3U/
nos9QO9NIUVMQP50IwyZb6c9o36nzTHwtftICIY+bz6sHzwU55omwKM+Kx/7rbEG
aRbMf1Owh9EhkiQO72JIUXyjPpYH/ogMQ0gSb83iNXPeyB9J70eQXcrD+taS0SSD
OFyRtstWOmh0ymtJVpNEP5DD2OAYgDc46JBCiLeAWRnVeYSFb2aI0GNXu+rzzl0Y
kbat/y8L1iiHlqO7GvgP5pXGg+jcn4CdIHlJRPkNkGC2jFDcYCemcSVRwDyw9qRx
03eaBGakcjrhmljgUmnOvfpUuRQRmpy4VMbGHWdInhEPcfiF5CaEttZr0HbMSVyA
P5lbCmECgYEA5Ny8jD4mETP7HNzaXGdw1tcPdqu5ABs0xXrgBaTGcDzS3eD6HIIn
n/Om9lxRZtxQW9UY82tKWjNUaS+puoqzNMYTNtZ+K2wDQJ7VNFfZ/+rfSMQJ3ebY
QwJbDGaVWobJBUV2aD+/L3LRxtsJoKrJifFUezGHhJBQkJNTssNUxJcCgYEAuKbq
ifBSfeBerMAl0bhQgQGGdqmg6TAj88PWLig8WGVuCQ5o4eEc24AciSfzSLAuA4RN
+nO7Jnf/rfep5dp/91qnO445G+ERTCecYlCMBlKvJJVaO1BpdGjuKj3qgvkAgXka
r7B5nzAuD1OJhDkDQmMm7KDYvzfdmsKzxILQtbMCgYEApsBqpOh3hhtQwRPuClvY
LMFf5AB0+C3agnToG1SWvZqjrcTJl9IBmxrFsUVMjlzCNFcNKfcnopc5zrZKvb9n
mXEk+NTJ80ttBz1zbQMBtOTmMbec1NDpC9IAkwV/lwkUGMIm5whjfef0DybzWdx2
ogpzmptY+W7JNL4TwvFtpxsCgYByuJls+9d0h0qqz3JvurChhd4RqU/ksNkVYO2X
nb3oOZREoiQ9egvgv9Z6zExVM8hSvQdpfC+hNdqvLfjranYoqrTNxo3qqUmC4/VA
C8UDRKm18+isg0gRYAPgULl7h9Jtnl0bHGxjn55uPTtp37YLr+iGCWTAYKgYt7DS
fWfICwKBgE+XHaw0+x+ry/Owewp76VasGnAT21Nwhjy3I5sczqMnPvGDlIPp6EUq
p/BQzCNO3OY8BA2wBwv5anoUJmALazJTjPHniirAONYEBCuplrBgnEVpfvXBvgzw
EDW7RibbOY0Cl0U6JCbkN+cGMylmX5QFQCpjijD5rLjENdhxWaWB
-----END RSA PRIVATE KEY-----"""


def make_token(sub: str = "test-user", exp_offset: int = 3600) -> str:
    """Sign a JWT with the test private key."""
    payload = {
        "sub": sub,
        "iat": int(time.time()),
        "exp": int(time.time()) + exp_offset,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, _PRIVATE_KEY, algorithm="RS256")


def _minimal_snapshot() -> dict:
    """Return a minimal but valid ITMSystemState dict."""
    pos_id = str(uuid.uuid4())
    strat_id = "test-strategy-001"
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    return {
        "state_id": str(uuid.uuid4()),
        "checkpoint_seq": 42,
        "created_at": now,
        "updated_at": now,
        "positions": {
            pos_id: {
                "position_id": pos_id,
                "instrument_symbol": "BTC/USDT",
                "instrument_exchange": "binance",
                "instrument_contract_type": "spot",
                "instrument_tick_size": "0.01",
                "instrument_lot_size": "0.00001",
                "instrument_base_currency": "BTC",
                "instrument_quote_currency": "USDT",
                "direction": "long",
                "entries": [
                    {
                        "order_id": str(uuid.uuid4()),
                        "quantity": "0.01",
                        "price": "65000.00",
                        "timestamp": now,
                    }
                ],
                "exits": [],
                "opened_at": now,
                "closed_at": None,
            }
        },
        "orders": {},
        "risk": {
            "account_heat": {
                "max_heat": "10.0",
                "current_heat": "2.0",
                "per_strategy_heat": {strat_id: "2.0"},
            },
            "capital_state": {
                "total_capital": "10000.00",
                "allocated": "650.00",
                "locked": "0.00",
            },
            "total_open_positions": 1,
            "total_pending_orders": 0,
            "total_realized_pnl": "125.50",
            "total_daily_pnl": "42.30",
            "max_daily_loss": "500.00",
            "max_drawdown_pct": "0.05",
            "current_drawdown_pct": "0.00",
            "updated_at": now,
        },
        "strategies": {
            strat_id: {
                "strategy_id": strat_id,
                "run_state": "active",
                "instrument": {
                    "symbol": "BTC/USDT",
                    "exchange": "binance",
                    "contract_type": "spot",
                    "tick_size": "0.01",
                    "lot_size": "0.00001",
                    "base_currency": "BTC",
                    "quote_currency": "USDT",
                },
                "risk_profile": {
                    "strategy_id": strat_id,
                    "max_drawdown_pct": "0.05",
                    "max_position_qty": "0.1",
                    "heat_limit": "5.0",
                    "max_daily_loss": "100.00",
                    "max_leverage": "1.0",
                },
                "active_position_id": pos_id,
                "open_order_ids": [],
                "daily_pnl": "42.30",
                "heat": "2.0",
                "realized_pnl": "125.50",
                "daily_pnl_date": now,
                "cooldown_until": None,
                "error_message": None,
                "updated_at": now,
            }
        },
    }


@pytest.fixture
def valid_token() -> str:
    return make_token()


@pytest.fixture
def expired_token() -> str:
    return make_token(exp_offset=-1)


@pytest.fixture
def fake_redis():
    """Fakeredis server shared within a test."""
    server = fakeredis.FakeServer()
    client = fakeredis.FakeRedis(server=server, decode_responses=True)
    snap = _minimal_snapshot()
    client.set("itm:state:snapshot", json.dumps(snap))
    return client, server, snap


@pytest.fixture
def app_with_fake_redis(fake_redis):
    """FastAPI app with make_async_client patched to return fakeredis.

    We patch at the factory level so the lifespan context manager picks up
    the fake client instead of trying to connect to a real Redis instance.
    """
    import fakeredis.aioredis as fake_aio
    from unittest.mock import patch
    _, server, snap = fake_redis

    async_client = fake_aio.FakeRedis(server=server, decode_responses=True)

    with patch("src.api.app.make_async_client", return_value=async_client):
        import src.api.app as api_app
        yield api_app.app, snap


@pytest.fixture
def sync_client(app_with_fake_redis):
    app, snap = app_with_fake_redis
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c, snap
