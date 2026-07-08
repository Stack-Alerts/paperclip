"""Tests for src/backup/retention.py — covers hard gate 6.

The fake provider mimics the dictionary contract of
``src/backup/local_provider.LocalProvider.list_backups`` (each entry has
``remote_id`` + ``uploaded_at`` ISO-8601 UTC timestamp). Retention uses
whichever timestamp field is present so the same code path works against
``BackupManifest`` rows too.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from src.backup.retention import apply_retention


# ---------------------------------------------------------------------------
# Minimal in-memory provider
# ---------------------------------------------------------------------------


class _FakeProvider:
    """Implements only the slice of ``BackupProvider`` that retention uses."""

    def __init__(self, entries: list[dict[str, Any]]) -> None:
        self._entries = [dict(e) for e in entries]
        self.deleted: list[str] = []

    def list_backups(self, prefix: str = "") -> list[dict[str, Any]]:
        if prefix:
            return [e for e in self._entries if str(e.get("remote_id", "")).startswith(prefix)]
        return list(self._entries)

    def delete(self, remote_id: str) -> None:
        before = len(self._entries)
        self._entries = [e for e in self._entries if e.get("remote_id") != remote_id]
        if len(self._entries) < before:
            self.deleted.append(remote_id)

    # ---- the rest of the BackupProvider surface (unused here) -------------

    def upload(self, local_path: Any, remote_id: str) -> dict:
        raise NotImplementedError

    def download(self, remote_id: str, local_path: Any) -> Any:
        raise NotImplementedError

    def test_connection(self) -> dict:
        return {"ok": True}


def _make_entry(remote_id: str, days_ago: int) -> dict[str, Any]:
    ts = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
    return {"remote_id": remote_id, "uploaded_at": ts, "provider": "local"}


# ---------------------------------------------------------------------------
# Hard gate 6 — retention
# ---------------------------------------------------------------------------


def test_retention_count_keeps_newest_three():
    """With 5 manifests and count=3, exactly the 3 newest survive."""
    entries = [
        _make_entry("backup-1", days_ago=4),
        _make_entry("backup-2", days_ago=3),
        _make_entry("backup-3", days_ago=2),
        _make_entry("backup-4", days_ago=1),
        _make_entry("backup-5", days_ago=0),
    ]
    provider = _FakeProvider(entries)

    deleted = apply_retention(provider, retention_count=3)

    assert set(deleted) == {"backup-1", "backup-2"}, f"Wrong deleted set: {deleted}"
    survivors = {e["remote_id"] for e in provider.list_backups()}
    assert survivors == {"backup-3", "backup-4", "backup-5"}, f"Wrong survivors: {survivors}"
    assert len(survivors) == 3


def test_retention_count_all_survive_when_count_exceeds_total():
    """If retention_count >= len(entries), nothing is deleted."""
    entries = [_make_entry(f"b-{i}", days_ago=i) for i in range(3)]
    provider = _FakeProvider(entries)
    deleted = apply_retention(provider, retention_count=10)
    assert deleted == []
    assert {e["remote_id"] for e in provider.list_backups()} == {"b-0", "b-1", "b-2"}


def test_retention_days_deletes_old():
    """Backups older than retention_days are pruned."""
    entries = [
        _make_entry("old-1", days_ago=40),
        _make_entry("old-2", days_ago=35),
        _make_entry("recent-1", days_ago=5),
        _make_entry("recent-2", days_ago=1),
    ]
    provider = _FakeProvider(entries)
    deleted = apply_retention(provider, retention_days=30)
    assert set(deleted) == {"old-1", "old-2"}


def test_retention_days_count_whichever_more_permissive():
    """A backup is kept when EITHER rule says so (whichever deletes less wins)."""
    entries = [
        _make_entry("ancient", days_ago=100),  # older than 30d, outside top-3
        _make_entry("medium-1", days_ago=10),  # newer than 30d, kept by age
        _make_entry("medium-2", days_ago=5),   # newer than 30d, kept by age
        _make_entry("fresh-1", days_ago=2),    # newest 3
        _make_entry("fresh-2", days_ago=1),    # newest 3
        _make_entry("fresh-3", days_ago=0),    # newest 3
    ]
    provider = _FakeProvider(entries)
    deleted = apply_retention(provider, retention_days=30, retention_count=3)
    # Only "ancient" should die — outside top-3 AND older than 30d.
    assert deleted == ["ancient"]


def test_retention_empty_provider_noop():
    """Empty provider returns empty deleted list without errors."""
    provider = _FakeProvider([])
    assert apply_retention(provider, retention_count=3) == []
    assert apply_retention(provider, retention_days=30) == []


def test_retention_accepts_neither_rule():
    """When neither retention_days nor retention_count is set, everything survives."""
    entries = [_make_entry(f"b-{i}", days_ago=i) for i in range(5)]
    provider = _FakeProvider(entries)
    deleted = apply_retention(provider)
    assert deleted == []


def test_retention_accepts_created_at_field():
    """BackupManifest dicts use ``created_at`` instead of ``uploaded_at``."""
    now = datetime.now(timezone.utc)
    entries = [
        {"remote_id": f"m-{i}", "created_at": (now - timedelta(days=i)).isoformat()}
        for i in range(5)
    ]
    provider = _FakeProvider(entries)
    deleted = apply_retention(provider, retention_count=2)
    survivors = {e["remote_id"] for e in provider.list_backups()}
    assert survivors == {"m-0", "m-1"}
    assert set(deleted) == {"m-2", "m-3", "m-4"}
