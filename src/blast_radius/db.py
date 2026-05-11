"""Database connection helper — delegates to touch_index.db for consistency."""

from __future__ import annotations

from touch_index.db import get_engine, health_check

__all__ = ["get_engine", "health_check"]
