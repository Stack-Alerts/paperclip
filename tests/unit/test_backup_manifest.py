"""Tests for src/backup/manifest.py and src/backup/restore.py — hard gates P2."""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

import pytest

from src.backup.local_provider import LocalProvider
from src.backup.manifest import BackupManifest, ManifestEntry
from src.backup.restore import (
    BackupContents,
    inspect_backup,
    restore_db_dump,
    restore_to_path,
)

PSQL = os.environ.get(
    "PSQL_BIN", "/home/sirrus/.pg0/installation/18.1.0/bin/psql"
)
PG_URL = "postgresql://optimizer_admin@localhost:5432/optimizer_v3"
DRILL_BACKUP = Path(
    "/home/sirrus/backups/optimizer_v3/drill_20260526_112041_post_restore.sql.gz"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _make_manifest(**kwargs) -> BackupManifest:
    defaults = dict(
        provider="local",
        kind="db",
        path="db/optimizer_v3.sql.gz",
        size_bytes=1024,
        sha256="abc123",
        duration_seconds=5,
        host_fingerprint="35a25765b9224d628878d0e7b09d56fb",
    )
    defaults.update(kwargs)
    return BackupManifest(**defaults)


# ---------------------------------------------------------------------------
# Gate 1 — Manifest round-trip
# ---------------------------------------------------------------------------


class TestManifestRoundTrip:
    def test_json_roundtrip(self):
        m = _make_manifest(
            contents=[
                ManifestEntry(
                    path="db/optimizer_v3.sql.gz",
                    size_bytes=2623763,
                    sha256="deadbeef" * 8,
                )
            ]
        )
        serialised = m.to_json()
        restored = BackupManifest.from_json(serialised)
        assert restored == m

    def test_dict_roundtrip(self):
        m = _make_manifest()
        restored = BackupManifest.from_dict(m.to_dict())
        assert restored == m

    def test_id_is_uuid(self):
        m = _make_manifest()
        assert isinstance(m.id, uuid.UUID)

    def test_created_at_is_utc(self):
        m = _make_manifest()
        assert m.created_at.tzinfo is not None

    def test_kind_validation(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            _make_manifest(kind="invalid")

    def test_schema_version_default(self):
        m = _make_manifest()
        assert m.schema_version == 1
        assert m.manifest_version == 1


# ---------------------------------------------------------------------------
# Gate 2 — Restore dry-run: no files written, no DB connection
# ---------------------------------------------------------------------------


class TestRestoreDryRun:
    def test_restore_to_path_dry_run_no_files(self, tmp_path):
        m = _make_manifest(
            contents=[
                ManifestEntry(
                    path="db/file.sql.gz", size_bytes=100, sha256="aa" * 32
                )
            ]
        )
        with tempfile.TemporaryDirectory() as backup_dir:
            provider = LocalProvider(backup_dir)
            report = restore_to_path(provider, m, tmp_path, dry_run=True)

        assert report.dry_run is True
        assert report.success
        # No files written to the target
        assert list(tmp_path.rglob("*")) == []
        assert all(f.skipped for f in report.files)

    def test_restore_db_dump_dry_run_no_connection(self):
        m = _make_manifest()
        with tempfile.TemporaryDirectory() as backup_dir:
            provider = LocalProvider(backup_dir)
            # Would fail if it tried to connect since we pass a bad URL
            report = restore_db_dump(
                provider, m, "postgresql://no-host/no-db", dry_run=True
            )

        assert report.dry_run is True
        assert report.success
        assert "dry_run=True" in report.warnings[0]
        assert not report.db_restored


# ---------------------------------------------------------------------------
# Gate 3 — Live restore via LocalProvider; psql COUNT(*) = 22
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not DRILL_BACKUP.exists(), reason="Drill backup file not present"
)
@pytest.mark.skipif(
    not Path(PSQL).exists(), reason="psql binary not found"
)
@pytest.mark.skipif(
    os.environ.get("BTC_TEST_LIVE_PG") != "1",
    reason="Live PG restore test (requires BTC_TEST_LIVE_PG=1)",
)
class TestLiveRestore:
    def test_restore_db_22_strategies(self, tmp_path):
        sha = _sha256(DRILL_BACKUP)
        m = _make_manifest(
            sha256=sha,
            size_bytes=DRILL_BACKUP.stat().st_size,
        )

        backup_dir = tmp_path / "provider_root"
        backup_dir.mkdir()
        provider = LocalProvider(str(backup_dir))

        # Stage the file where the provider expects it. LocalProvider's
        # hardened `_validate_remote_id` rejects slashes; restore_db_dump
        # looks up the dump under the basename "optimizer_v3.sql.gz".
        dest = backup_dir / "optimizer_v3.sql.gz"
        shutil.copy2(DRILL_BACKUP, dest)

        report = restore_db_dump(provider, m, PG_URL, dry_run=False)

        assert report.success, f"Restore failed: {report.errors}"
        assert report.db_restored

        result = subprocess.run(
            [PSQL, PG_URL, "-t", "-c", "SELECT COUNT(*) FROM strategies;"],
            capture_output=True,
            text=True,
        )
        count = int(result.stdout.strip())
        assert count == 22, f"Expected 22 strategies, got {count}"


# ---------------------------------------------------------------------------
# Gate 4 — Cross-host fingerprint warning
# ---------------------------------------------------------------------------


class TestCrossHostWarning:
    def test_warns_on_different_fingerprint(self, caplog):
        m = _make_manifest(host_fingerprint="ABC-OTHER-HOST")

        with tempfile.TemporaryDirectory() as backup_dir:
            provider = LocalProvider(backup_dir)
            with caplog.at_level(logging.WARNING, logger="src.backup.restore"):
                restore_to_path(provider, m, backup_dir, dry_run=True)

        assert any("Cross-host restore" in r.message for r in caplog.records)

    def test_no_warning_same_fingerprint(self, caplog):
        machine_id = Path("/etc/machine-id").read_text().strip()
        m = _make_manifest(host_fingerprint=machine_id)

        with tempfile.TemporaryDirectory() as backup_dir:
            provider = LocalProvider(backup_dir)
            with caplog.at_level(logging.WARNING, logger="src.backup.restore"):
                restore_to_path(provider, m, backup_dir, dry_run=True)

        assert not any(
            "Cross-host restore" in r.message for r in caplog.records
        )

    def test_env_var_suppresses_warning(self, caplog, monkeypatch):
        monkeypatch.setenv("RESTORE_SKIP_FINGERPRINT_CHECK", "1")
        m = _make_manifest(host_fingerprint="DIFFERENT-HOST")

        with tempfile.TemporaryDirectory() as backup_dir:
            provider = LocalProvider(backup_dir)
            with caplog.at_level(logging.WARNING, logger="src.backup.restore"):
                restore_to_path(provider, m, backup_dir, dry_run=True)

        assert not any(
            "Cross-host restore" in r.message for r in caplog.records
        )


# ---------------------------------------------------------------------------
# Gate 5 — Schema version mismatch → clear error
# ---------------------------------------------------------------------------


class TestSchemaVersionMismatch:
    def test_schema_version_0_rejected(self):
        m = _make_manifest(schema_version=0)
        with tempfile.TemporaryDirectory() as backup_dir:
            provider = LocalProvider(backup_dir)
            with pytest.raises(ValueError, match="schema_version=0"):
                inspect_backup(provider, m)

    def test_schema_version_0_rejected_on_restore_to_path(self, tmp_path):
        m = _make_manifest(schema_version=0)
        with tempfile.TemporaryDirectory() as backup_dir:
            provider = LocalProvider(backup_dir)
            with pytest.raises(ValueError, match="schema_version=0"):
                restore_to_path(provider, m, tmp_path, dry_run=True)

    def test_schema_version_0_rejected_on_restore_db(self):
        m = _make_manifest(schema_version=0)
        with tempfile.TemporaryDirectory() as backup_dir:
            provider = LocalProvider(backup_dir)
            with pytest.raises(ValueError, match="schema_version=0"):
                restore_db_dump(provider, m, PG_URL, dry_run=True)

    def test_current_schema_version_accepted(self):
        m = _make_manifest(schema_version=1)
        with tempfile.TemporaryDirectory() as backup_dir:
            provider = LocalProvider(backup_dir)
            contents = inspect_backup(provider, m)
        assert isinstance(contents, BackupContents)
