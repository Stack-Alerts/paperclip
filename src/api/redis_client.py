"""
Redis client factory for the BTC Trade Engine API.

Provides both sync (for startup/health checks) and async (for FastAPI handlers)
Redis clients, configured from environment variables.

Environment variables
---------------------
BTE_REDIS_HOST      Redis host (default: localhost)
BTE_REDIS_PORT      Redis port (default: 6379)
BTE_REDIS_DB        Redis DB index (default: 0)
BTE_REDIS_PASSWORD  Redis password (default: None)
"""

from __future__ import annotations

import os

import redis
import redis.asyncio as aioredis

_HOST = os.environ.get("BTE_REDIS_HOST", "localhost")
_PORT = int(os.environ.get("BTE_REDIS_PORT", "6379"))
_DB = int(os.environ.get("BTE_REDIS_DB", "0"))
_PASSWORD = os.environ.get("BTE_REDIS_PASSWORD") or None


def make_sync_client() -> redis.Redis:
    """Return a connected synchronous Redis client."""
    return redis.Redis(
        host=_HOST,
        port=_PORT,
        db=_DB,
        password=_PASSWORD,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
    )


def make_async_client() -> aioredis.Redis:
    """Return an async Redis client (not yet connected — connects on first use)."""
    return aioredis.Redis(
        host=_HOST,
        port=_PORT,
        db=_DB,
        password=_PASSWORD,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
    )
