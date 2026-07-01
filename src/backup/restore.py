"""Shared restore logic — used by CLI (P4) and UI (P5)."""

from __future__ import annotations

import hashlib
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from .manifest import CURRENT_SCHEMA_VERSION, BackupManifest, ManifestEntry
from .provider import BackupProvider

logger = logging.getLogger(__name__)

_PSQL = os.environ.get(
    "PSQL_BIN", "/home/sirrus/.pg0/installation/18.1.0/bin/psql"
)

# ---------------------------------------------------------------------------
# Return types
# ---------------------------------------------------------------------------


@dataclass
class FileStatus:
    path: str
    size_bytes: int
    sha256_expected: str
    sha256_actual: str | None = None
    ok: bool = False
    skipped: bool = False  # True in dry-run
    error: str | None = None


@dataclass
class BackupContents:
    manifest: BackupManifest
    entries: list[ManifestEntry]


@dataclass
class RestoreReport:
    manifest_id: str
    dry_run: bool
    files: list[FileStatus] = field(default_factory=list)
    db_restored: bool = False
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return not self.errors and all(
            f.ok or f.skipped for f in self.files
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def inspect_backup(
    provider: BackupProvider, manifest: BackupManifest
) -> BackupContents:
    """Read manifest, return file list with sizes and sha256 hashes."""
    _check_schema_version(manifest)
    return BackupContents(manifest=manifest, entries=list(manifest.contents))


def restore_to_path(
    provider: BackupProvider,
    manifest: BackupManifest,
    target_dir: str | Path,
    *,
    dry_run: bool = True,
) -> RestoreReport:
    """Download every manifest entry under ``<target_dir>/<kind>/<id>/``.

    Each file's sha256 is verified after download. ``dry_run=True`` returns
    what *would* be done without writing any files or making any connections.
    """
    _check_schema_version(manifest)
    _warn_cross_host(manifest)

    report = RestoreReport(manifest_id=str(manifest.id), dry_run=dry_run)
    dest_root = Path(target_dir) / manifest.kind / str(manifest.id)

    for entry in manifest.contents:
        status = FileStatus(
            path=entry.path,
            size_bytes=entry.size_bytes,
            sha256_expected=entry.sha256,
        )
        if dry_run:
            status.skipped = True
            status.ok = True
            report.files.append(status)
            continue

        local_dest = dest_root / entry.path
        local_dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            provider.download(entry.path, local_dest)
            actual = _sha256_file(local_dest)
            status.sha256_actual = actual
            if actual == entry.sha256:
                status.ok = True
            else:
                status.error = (
                    f"sha256 mismatch: expected {entry.sha256}, got {actual}"
                )
                report.errors.append(f"{entry.path}: {status.error}")
        except Exception as exc:
            status.error = str(exc)
            report.errors.append(f"{entry.path}: {exc}")
        report.files.append(status)

    return report


def restore_db_dump(
    provider: BackupProvider,
    manifest: BackupManifest,
    target_pg_url: str,
    *,
    dry_run: bool = True,
) -> RestoreReport:
    """Stream db/optimizer_v3.sql.gz from the provider into psql.

    ``dry_run=True`` skips the download and DB connection entirely.
    """
    _check_schema_version(manifest)
    _warn_cross_host(manifest)

    report = RestoreReport(manifest_id=str(manifest.id), dry_run=dry_run)
    # LocalProvider's hardened `_validate_remote_id` only accepts
    # ``[A-Za-z0-9._-]{1,256}`` (no ``/``), so the dump must live under a
    # single flat remote id. The ``optimizer_v3_`` prefix keeps the file
    # namespace from colliding with system-backup ids staged in the same
    # provider directory.
    dump_remote_id = "optimizer_v3.sql.gz"

    if dry_run:
        report.files.append(
            FileStatus(
                path=dump_remote_id,
                size_bytes=manifest.size_bytes,
                sha256_expected=manifest.sha256,
                skipped=True,
                ok=True,
            )
        )
        report.warnings.append(
            "dry_run=True — no download, no DB connection made"
        )
        return report

    # Reject any non-postgresql scheme up front. ``target_pg_url`` is supplied
    # by the caller, so an attacker could otherwise have us pipe the dump into
    # ``curl`` or a webhook via shell parsing.
    if not _is_postgres_url(target_pg_url):
        report.errors.append(
            f"unsafe target_pg_url: must be a postgresql:// URL (got {target_pg_url!r})"
        )
        return report

    with tempfile.TemporaryDirectory(prefix="btc_restore_") as tmp:
        local_gz = Path(tmp) / "optimizer_v3.sql.gz"
        provider.download(dump_remote_id, local_gz)

        actual_sha = _sha256_file(local_gz)
        status = FileStatus(
            path=dump_remote_id,
            size_bytes=local_gz.stat().st_size,
            sha256_expected=manifest.sha256,
            sha256_actual=actual_sha,
        )

        if actual_sha != manifest.sha256:
            status.error = (
                f"sha256 mismatch: expected {manifest.sha256}, got {actual_sha}"
            )
            report.files.append(status)
            report.errors.append(status.error)
            return report

        status.ok = True
        report.files.append(status)

        try:
            # No shell. argv lists only. ``gunzip -c`` feeds psql via stdin.
            gunzip = subprocess.Popen(
                ["gunzip", "-c", str(local_gz)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                psql_proc = subprocess.run(
                    [_PSQL, target_pg_url],
                    stdin=gunzip.stdout,
                    capture_output=True,
                    text=True,
                )
            finally:
                if gunzip.stdout is not None:
                    gunzip.stdout.close()
            gunzip.wait()
            if psql_proc.returncode != 0:
                err = (psql_proc.stderr or "").strip() or (
                    psql_proc.stdout or ""
                ).strip()
                report.errors.append(
                    f"psql exited {psql_proc.returncode}: {err}"
                )
            else:
                report.db_restored = True
        except Exception as exc:
            report.errors.append(f"restore subprocess failed: {exc}")

    return report


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _check_schema_version(manifest: BackupManifest) -> None:
    if manifest.schema_version < CURRENT_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported manifest schema_version={manifest.schema_version}. "
            f"Expected >={CURRENT_SCHEMA_VERSION}. "
            "Re-export the backup or upgrade manually."
        )


def _warn_cross_host(manifest: BackupManifest) -> None:
    if os.environ.get("RESTORE_SKIP_FINGERPRINT_CHECK"):
        return
    current_id = _machine_id()
    if current_id and manifest.host_fingerprint != current_id:
        logger.warning(
            "Cross-host restore detected: backup created on host %s, "
            "restoring on host %s. Set RESTORE_SKIP_FINGERPRINT_CHECK=1 to suppress.",
            manifest.host_fingerprint,
            current_id,
        )


def _machine_id() -> str:
    for path in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
        try:
            return Path(path).read_text().strip()
        except OSError:
            continue
    return ""


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_postgres_url(url: str) -> bool:
    """Validate that ``url`` is a ``postgresql://`` or ``postgres://`` URL.

    Accepted schemes: ``postgresql``, ``postgres``. Anything else (including
    empty, ``file://``, ``http://``, ``curl``-style strings with extra args)
    is rejected so that ``psql`` is never pointed at a non-DB target.
    """
    if not isinstance(url, str) or not url:
        return False
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    return parsed.scheme in ("postgresql", "postgres") and bool(parsed.netloc)
