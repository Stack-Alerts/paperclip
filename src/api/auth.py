"""
JWT validation for the BTC Trade Engine API.

The RSA-2048 public key is embedded at build time. The matching private key
is kept outside the repo (env var BTE_JWT_PRIVATE_KEY or secrets store).

All REST and WebSocket endpoints call require_jwt() / ws_require_jwt().
"""

from __future__ import annotations

import os
from typing import Any, Optional

import jwt
from fastapi import Depends, HTTPException, Query, WebSocket, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# ---------------------------------------------------------------------------
# Embedded RSA-2048 public key (BTE API v1, 2026-05-16)
# ---------------------------------------------------------------------------
# To regenerate:
#   from cryptography.hazmat.primitives.asymmetric import rsa
#   from cryptography.hazmat.primitives import serialization
#   k = rsa.generate_private_key(65537, 2048)
#   print(k.public_key().public_bytes(serialization.Encoding.PEM,
#         serialization.PublicFormat.SubjectPublicKeyInfo).decode())

_EMBEDDED_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEApRPgVCTtcOjPUtaAq/Qi
OFyjNyusoHlYLQgeHCE59JP6LJpxqPZ5P+kfpojBAUwJ2HViypopyiHIbLoCRM6U
GstyD8p/k+VNYF+NbXNIcQfkQxRQhima7QSQhD0ApgaKRRpARLHiOFmOcAZ9hoaQ
QFLqkbmPooyhokltdWd7iCgtX7gBh2vktSznxHOztP/BCuYOmf9icD7nWMYnFaQ4
NYBKgF0Xo36+TrSmAE3nPnagJkqERkWgtUa7qFpbQ9bRCS3kwHtDBh8585erJsvu
SCjmKNes6u9M/cYImUuLApHGKo3YrRMVFWyZlMK4DDq3iaKV/Tz4Zg6sasNp6/Q4
lQIDAQAB
-----END PUBLIC KEY-----"""

# Allow override via env for test environments that use a different key
_PUBLIC_KEY: str = os.environ.get("BTE_JWT_PUBLIC_KEY", _EMBEDDED_PUBLIC_KEY).strip()

_ALGORITHMS = ["RS256"]

# Set BTE_API_DEV_MODE=1 in .env to disable JWT validation for local development.
# NEVER enable in production — all requests are accepted without a token.
_DEV_MODE: bool = os.environ.get("BTE_API_DEV_MODE", "").lower() in ("1", "true", "yes")

_bearer = HTTPBearer(auto_error=not _DEV_MODE)


def _decode(token: str) -> dict[str, Any]:
    """Decode and verify a Bearer JWT; raise 401 on any failure."""
    try:
        return jwt.decode(token, _PUBLIC_KEY, algorithms=_ALGORITHMS)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
        )


# ---------------------------------------------------------------------------
# REST dependency
# ---------------------------------------------------------------------------


async def require_jwt(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> dict[str, Any]:
    """FastAPI dependency: validates Bearer JWT for REST endpoints."""
    if _DEV_MODE:
        return {"sub": "dev", "dev_mode": True}
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _decode(credentials.credentials)


# ---------------------------------------------------------------------------
# WebSocket JWT (query-param based, browsers can't set WS headers)
# ---------------------------------------------------------------------------


async def ws_require_jwt(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
) -> dict[str, Any]:
    """Validate JWT for WebSocket upgrades.

    Accepts token as ``?token=<jwt>`` query parameter.
    Closes the socket with 1008 (Policy Violation) on failure.
    """
    try:
        return _decode(token)
    except HTTPException:
        await websocket.close(code=1008, reason="Unauthorized")
        raise
