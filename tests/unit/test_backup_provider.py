"""Unit tests for LocalProvider — P1 acceptance gate.

Gate: round-trip a 1 MB binary blob through upload → list_backups → download;
sha256 must match pre-upload and post-download.
"""
from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

import pytest

from src.backup.local_provider import LocalProvider
from src.backup.provider import BackupProvider


@pytest.fixture()
def provider(tmp_path):
    return LocalProvider(tmp_path / "backups")


@pytest.fixture()
def blob_1mb(tmp_path) -> tuple[Path, str]:
    data = os.urandom(1024 * 1024)
    sha256 = hashlib.sha256(data).hexdigest()
    p = tmp_path / "source.bin"
    p.write_bytes(data)
    return p, sha256


class TestLocalProviderRoundTrip:
    def test_upload_returns_manifest(self, provider, blob_1mb):
        path, sha = blob_1mb
        manifest = provider.upload(path, "backup-001")
        assert manifest["remote_id"] == "backup-001"
        assert manifest["sha256"] == sha
        assert manifest["size"] == 1024 * 1024
        assert manifest["provider"] == "local"

    def test_download_restores_identical_bytes(self, provider, blob_1mb, tmp_path):
        path, sha = blob_1mb
        provider.upload(path, "backup-001")
        dest = tmp_path / "restored.bin"
        returned = provider.download("backup-001", dest)
        assert returned == dest
        assert hashlib.sha256(dest.read_bytes()).hexdigest() == sha

    def test_list_backups_shows_uploaded(self, provider, blob_1mb):
        path, _ = blob_1mb
        provider.upload(path, "backup-list-test")
        listing = provider.list_backups()
        ids = [m["remote_id"] for m in listing]
        assert "backup-list-test" in ids

    def test_list_backups_prefix_filter(self, provider, blob_1mb):
        path, _ = blob_1mb
        provider.upload(path, "alpha-001")
        provider.upload(path, "beta-001")
        alpha = provider.list_backups(prefix="alpha")
        beta = provider.list_backups(prefix="beta")
        assert all(m["remote_id"].startswith("alpha") for m in alpha)
        assert all(m["remote_id"].startswith("beta") for m in beta)

    def test_delete_removes_backup(self, provider, blob_1mb):
        path, _ = blob_1mb
        provider.upload(path, "to-delete")
        provider.delete("to-delete")
        listing = provider.list_backups()
        assert not any(m["remote_id"] == "to-delete" for m in listing)

    def test_download_missing_raises(self, provider, tmp_path):
        with pytest.raises(FileNotFoundError):
            provider.download("nonexistent", tmp_path / "out.bin")

    def test_test_connection_ok(self, provider):
        result = provider.test_connection()
        assert result["ok"] is True
        assert result["provider"] == "local"

    def test_sha256_invariant_across_roundtrip(self, provider, blob_1mb, tmp_path):
        """End-to-end: sha256 before upload == sha256 after download."""
        src, pre_sha = blob_1mb
        provider.upload(src, "integrity-check")
        dest = tmp_path / "integrity-out.bin"
        provider.download("integrity-check", dest)
        post_sha = hashlib.sha256(dest.read_bytes()).hexdigest()
        assert pre_sha == post_sha

    def test_multiple_uploads_listed(self, provider, blob_1mb):
        path, _ = blob_1mb
        for i in range(3):
            provider.upload(path, f"multi-{i:03d}")
        listing = provider.list_backups()
        assert len(listing) >= 3


class TestBackupProviderInterface:
    def test_localproivder_is_backupprovider(self, provider):
        assert isinstance(provider, BackupProvider)

    def test_import_without_rclone(self):
        """BackupProvider ABC must import cleanly without rclone installed."""
        from src.backup.provider import BackupProvider as BP  # noqa: F401
