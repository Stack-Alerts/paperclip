"""Backup retention pruner — deletes old backups by age and count limits.

The ``BackupProvider.list_backups`` contract returns a list of dicts (see
``src/backup/local_provider.py``); each entry carries at least ``remote_id``
plus a timestamp field (``uploaded_at`` for ``LocalProvider`` /
``RcloneProvider``, ``created_at`` for ``BackupManifest``). Retention uses
whichever field is present so this module works against either provider.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

_TS_KEYS = ("uploaded_at", "created_at")


def _parse_dt(entry: dict[str, Any]) -> datetime:
    """Read a timestamp from either ``uploaded_at`` or ``created_at`` field.

    Returns ``datetime.min`` (UTC) on parse failure so a malformed row sorts
    older than any valid one and is the first candidate for deletion rather
    than the last.
    """
    raw: Optional[str] = None
    for key in _TS_KEYS:
        value = entry.get(key)
        if value:
            raw = value if isinstance(value, str) else str(value)
            break
    if not raw:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _remote_id(entry: dict[str, Any]) -> Optional[str]:
    """Extract a ``remote_id`` from a list_backups entry.

    Returns ``None`` when the entry has no usable identifier so the caller
    can skip it rather than raising.
    """
    rid = entry.get("remote_id")
    if rid:
        return str(rid)
    ident = entry.get("id")
    if ident:
        return str(ident)
    return None


def apply_retention(
    provider: Any,
    *,
    retention_days: Optional[int] = None,
    retention_count: Optional[int] = None,
    prefix: str = "",
) -> list[str]:
    """Delete backups that violate the retention policy.

    A backup is **kept** when it satisfies *either* rule:

    1. Age: ``created_at >= now - retention_days`` (only meaningful when
       ``retention_days`` is set), OR
    2. Count: it is among the newest ``retention_count`` backups (only
       meaningful when ``retention_count`` is set).

    The intersection (whichever rule deletes more) wins — a backup is only
    pruned when it fails both applicable tests.

    Returns the list of ``remote_id`` strings that were deleted.
    """
    manifests = provider.list_backups(prefix=prefix)
    if not manifests:
        return []

    if retention_days is None and retention_count is None:
        return []

    sorted_manifests = sorted(
        manifests,
        key=lambda m: _parse_dt(m),
        reverse=True,
    )

    cutoff: Optional[datetime] = None
    if retention_days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

    keep_indices: set[int] = set()

    if retention_count is not None:
        for i in range(min(retention_count, len(sorted_manifests))):
            keep_indices.add(i)

    if cutoff is not None:
        for i, m in enumerate(sorted_manifests):
            if _parse_dt(m) >= cutoff:
                keep_indices.add(i)

    deleted: list[str] = []
    for i, m in enumerate(sorted_manifests):
        if i in keep_indices:
            continue
        remote_id = _remote_id(m)
        if not remote_id:
            logger.warning("Retention: skipping entry without remote_id: %r", m)
            continue
        try:
            provider.delete(remote_id)
            deleted.append(remote_id)
            logger.info(
                "Retention: deleted backup %s (ts=%s)",
                remote_id,
                m.get("uploaded_at") or m.get("created_at"),
            )
        except Exception:
            logger.exception("Retention: failed to delete %s", remote_id)

    return deleted
