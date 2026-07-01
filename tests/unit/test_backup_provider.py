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


# ---------------------------------------------------------------------------
# Security — input validation gates (path traversal / arg injection)
# ---------------------------------------------------------------------------


class TestLocalProviderSecurity:
    @pytest.mark.parametrize(
        "bad_id",
        [
            "../etc/passwd",          # path traversal (slash + ..)
            "..",                     # traversal component
            "foo..bar",               # double-dot anywhere
            "foo/bar",                # slash
            "foo\\bar",               # backslash
            "-rf",                    # leading dash
            "",                       # empty
            "name with space",        # shell metachar
            "name;rm",                # shell metachar
            "name`whoami`",           # backticks
            "name$(whoami)",          # cmdsubst
            "name\nwhoami",           # newline
            "a" * 257,                # too long
        ],
    )
    def test_invalid_remote_id_rejected(self, provider, tmp_path, bad_id):
        src = tmp_path / "src.bin"
        src.write_bytes(b"hello")
        with pytest.raises(ValueError, match="Invalid remote_id"):
            provider.upload(src, bad_id)
        with pytest.raises(ValueError, match="Invalid remote_id"):
            provider.download(bad_id, tmp_path / "out.bin")
        with pytest.raises(ValueError, match="Invalid remote_id"):
            provider.delete(bad_id)
        # empty string is a sentinel for "list all" — only validate non-empty
        if bad_id:
            with pytest.raises(ValueError, match="Invalid prefix"):
                provider.list_backups(prefix=bad_id)

    def test_valid_remote_id_accepted(self, provider, tmp_path):
        src = tmp_path / "src.bin"
        src.write_bytes(b"hello")
        # Allowed chars: [A-Za-z0-9._-]
        provider.upload(src, "backup_2026-06-30.v1")
        provider.upload(src, "backup.v2")
        provider.upload(src, "a")
        assert any(
            m["remote_id"] == "backup_2026-06-30.v1"
            for m in provider.list_backups()
        )


class TestRcloneProviderSecurity:
    def test_remote_id_with_colon_rejected(self, monkeypatch):
        from src.backup.rclone_provider import RcloneProvider
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            from subprocess import CompletedProcess
            return CompletedProcess(cmd, 0, stdout="[]", stderr="")

        monkeypatch.setattr("subprocess.run", fake_run)
        provider = RcloneProvider("gdrive:backups/btc")
        with pytest.raises(ValueError, match="Invalid remote_id"):
            provider.upload("/tmp/x.bin", "evil:other_remote:lol")
        # The subprocess must NOT have been called for the bad request.
        assert calls == []

    def test_invalid_remote_id_rejected(self, monkeypatch):
        from src.backup.rclone_provider import RcloneProvider
        def fake_run(cmd, **kwargs):
            raise AssertionError("subprocess must not run on invalid id")
        monkeypatch.setattr("subprocess.run", fake_run)
        provider = RcloneProvider("gdrive:backups/btc")
        for bad in ("foo/bar", "../escape", "-flag", "", "name with space"):
            with pytest.raises(ValueError, match="Invalid"):
                provider.upload("/tmp/x.bin", bad)
            with pytest.raises(ValueError, match="Invalid"):
                provider.download(bad, "/tmp/out.bin")
            with pytest.raises(ValueError, match="Invalid"):
                provider.delete(bad)

    def test_leading_dash_remote_rejected(self):
        from src.backup.rclone_provider import RcloneProvider
        with pytest.raises(ValueError, match="Invalid remote"):
            RcloneProvider("--config=/etc/passwd")

    def test_valid_ids_call_rclone(self, monkeypatch):
        from src.backup.rclone_provider import RcloneProvider
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            from subprocess import CompletedProcess
            return CompletedProcess(cmd, 0, stdout="[]", stderr="")

        monkeypatch.setattr("subprocess.run", fake_run)
        provider = RcloneProvider("gdrive:backups/btc")
        provider.list_backups(prefix="backup_2026")
        # argv list contains the joined remote path as a single element,
        # proving no shell parsing happened.
        flattened = " ".join(" ".join(c) for c in calls)
        assert "backup_2026" in flattened


# ---------------------------------------------------------------------------
# Security — restore_db_dump shell arg validation
# ---------------------------------------------------------------------------


class TestRestoreDbUrlValidation:
    @pytest.mark.parametrize(
        "bad_url",
        [
            "",
            "not-a-url",
            "file:///etc/passwd",
            "http://attacker.example/exfil",
            "postgresql",  # scheme only, no netloc
            "postgresql:",  # scheme+sep, no netloc
        ],
    )
    def test_non_postgres_url_validation(self, bad_url, tmp_path):
        from src.backup.restore import _is_postgres_url
        assert _is_postgres_url(bad_url) is False

    def test_postgres_url_accepted(self, tmp_path):
        from src.backup.restore import _is_postgres_url
        assert _is_postgres_url("postgresql://u@h/d") is True
        assert _is_postgres_url("postgres://u@h/d") is True
        assert _is_postgres_url("http://x") is False
        assert _is_postgres_url("") is False
