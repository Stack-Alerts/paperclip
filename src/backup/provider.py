"""Abstract backup provider interface."""
from __future__ import annotations

import abc
from pathlib import Path


class BackupProvider(abc.ABC):
    """Abstract base class for backup providers."""

    @abc.abstractmethod
    def upload(self, local_path: Path | str, remote_id: str) -> dict:
        """Upload a local file and return a manifest dict."""

    @abc.abstractmethod
    def download(self, remote_id: str, local_path: Path | str) -> Path:
        """Download a remote backup to local_path and return the resolved path."""

    @abc.abstractmethod
    def list_backups(self, prefix: str = "") -> list[dict]:
        """List available backups, optionally filtered by prefix."""

    @abc.abstractmethod
    def delete(self, remote_id: str) -> None:
        """Delete a backup by remote_id."""

    @abc.abstractmethod
    def test_connection(self) -> dict:
        """Test provider connectivity; returns status dict with at least {'ok': bool}."""
