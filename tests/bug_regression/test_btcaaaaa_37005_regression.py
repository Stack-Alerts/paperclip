"""
BTCAAAAA-37005: POST /ai-recommendations/send — backend-mediated AI route.

Tests:
  - 202 with correlationId on valid payload
  - correlationId is a non-empty string
  - Job is enqueued to bte:ai_recommendations:queue in Redis
  - Enqueued job carries the submitted payload
  - 401 without JWT
  - Empty payload body is accepted (all fields optional)
"""

from __future__ import annotations

import json
import uuid

import fakeredis
import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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


def _make_token(exp_offset: int = 3600) -> str:
    import time
    import jwt as pyjwt
    payload = {
        "sub": "test-user",
        "iat": int(time.time()),
        "exp": int(time.time()) + exp_offset,
        "jti": str(uuid.uuid4()),
    }
    return pyjwt.encode(payload, _PRIVATE_KEY, algorithm="RS256")


@pytest.fixture()
def client_and_redis():
    server = fakeredis.FakeServer()
    sync_fake = fakeredis.FakeRedis(server=server, decode_responses=True)
    async_fake = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)

    with patch("src.api.app.make_async_client", return_value=async_fake):
        import src.api.app as api_app
        with TestClient(api_app.app, raise_server_exceptions=True) as c:
            yield c, sync_fake


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

_SAMPLE_PAYLOAD = {
    "strategy_config": {
        "id": "strat-001",
        "name": "RSI Breakout",
        "strategyType": "Bullish",
        "blocks": [],
        "settings": {},
    },
    "backtest_config": {"startDate": "2024-01-01", "endDate": "2024-06-30"},
    "trades": [
        {"tradeId": "t1", "entryPrice": "65000", "exitPrice": "67000", "pnl": "200"}
    ],
    "metrics": {
        "winRate": 0.6,
        "sharpeRatio": 1.2,
        "maxDrawdown": 0.05,
        "totalTrades": 1,
    },
}


def test_send_returns_202_with_correlation_id(client_and_redis):
    client, _ = client_and_redis
    token = _make_token()
    resp = client.post(
        "/ai-recommendations/send",
        json=_SAMPLE_PAYLOAD,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 202, resp.text
    data = resp.json()
    assert "correlationId" in data
    assert isinstance(data["correlationId"], str)
    assert len(data["correlationId"]) > 0


def test_send_enqueues_job_in_redis(client_and_redis):
    client, redis = client_and_redis
    token = _make_token()
    resp = client.post(
        "/ai-recommendations/send",
        json=_SAMPLE_PAYLOAD,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 202
    correlation_id = resp.json()["correlationId"]

    queue_len = redis.llen("bte:ai_recommendations:queue")
    assert queue_len == 1, "Exactly one job should be enqueued"

    raw = redis.lrange("bte:ai_recommendations:queue", 0, 0)[0]
    job = json.loads(raw)
    assert job["correlationId"] == correlation_id
    assert "enqueuedAt" in job
    assert "payload" in job


def test_send_payload_preserved_in_queue(client_and_redis):
    client, redis = client_and_redis
    token = _make_token()
    client.post(
        "/ai-recommendations/send",
        json=_SAMPLE_PAYLOAD,
        headers={"Authorization": f"Bearer {token}"},
    )
    raw = redis.lrange("bte:ai_recommendations:queue", 0, 0)[0]
    job = json.loads(raw)
    payload = job["payload"]
    assert payload["strategy_config"]["name"] == "RSI Breakout"
    assert payload["metrics"]["winRate"] == 0.6
    assert len(payload["trades"]) == 1


def test_send_requires_auth(client_and_redis):
    client, _ = client_and_redis
    # Patch _DEV_MODE off so auth is enforced even in dev environments.
    with patch("src.api.auth._DEV_MODE", False):
        resp = client.post("/ai-recommendations/send", json=_SAMPLE_PAYLOAD)
    assert resp.status_code == 401


def test_send_accepts_empty_body(client_and_redis):
    client, redis = client_and_redis
    token = _make_token()
    resp = client.post(
        "/ai-recommendations/send",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 202
    data = resp.json()
    assert "correlationId" in data

    raw = redis.lrange("bte:ai_recommendations:queue", 0, 0)[0]
    job = json.loads(raw)
    payload = job["payload"]
    assert payload["strategy_config"] is None
    assert payload["trades"] is None
