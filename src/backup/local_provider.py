"""Local filesystem backup provider — reference implementation and dev/offline use."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .provider import BackupProvider

_REMOTE_ID_RE = re.compile(r"^(?!-)[A-Za-z0-9._-]{1,256}$")


def _validate_remote_id(remote_id: str, *, field: str = "remote_id") -> None:
    """Reject path traversal / shell metacharacters in backup identifiers.

    Only ``[A-Za-z0-9._-]{1,256}`` is allowed, and the first char must not
    be ``-`` so callers cannot smuggle a flag-like id through argv parsing
    (e.g. ``-rf``). This blocks ``/``, ``\\``, NUL, and shell metachars. The
    double-dot (``..``) component is rejected explicitly so traversal cannot
    be encoded as a single segment.
    """
    if not isinstance(remote_id, str) or not _REMOTE_ID_RE.match(remote_id):
        raise ValueError(
            f"Invalid {field}: {remote_id!r}. "
            "Must match ^[A-Za-z0-9._-]{1,256}$ and must not start with '-'."
        )
    if ".." in remote_id:
        raise ValueError(
            f"Invalid {field}: {remote_id!r}. Contains '..' (path traversal)."
        )


class LocalProvider(BackupProvider):
    """Stores backups in a local directory."""

    def __init__(self, backup_dir: str | Path) -> None:
        self.backup_dir = Path(backup_dir).resolve()
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def _meta_path(self, remote_id: str) -> Path:
        _validate_remote_id(remote_id)
        return self.backup_dir / f"{remote_id}.meta.json"

    def _data_path(self, remote_id: str) -> Path:
        _validate_remote_id(remote_id)
        return self.backup_dir / remote_id

    def upload(self, local_path: Path | str, remote_id: str) -> dict:
        _validate_remote_id(remote_id)
        local_path = Path(local_path)
        data = local_path.read_bytes()
        sha256 = hashlib.sha256(data).hexdigest()
        dest = self._data_path(remote_id)
        if not str(dest.resolve()).startswith(str(self.backup_dir)):
            raise ValueError(f"Refusing remote_id that escapes backup_dir: {remote_id!r}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local_path, dest)
        manifest = {
            "remote_id": remote_id,
            "provider": "local",
            "size": len(data),
            "sha256": sha256,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "source": str(local_path),
        }
        self._meta_path(remote_id).write_text(json.dumps(manifest))
        return manifest

    def download(self, remote_id: str, local_path: Path | str) -> Path:
        _validate_remote_id(remote_id)
        local_path = Path(local_path)
        src = self._data_path(remote_id)
        if not src.resolve().is_relative_to(self.backup_dir):
            raise ValueError(f"Refusing remote_id that escapes backup_dir: {remote_id!r}")
        if not src.exists():
            raise FileNotFoundError(f"Backup {remote_id!r} not found in {self.backup_dir}")
        shutil.copy2(src, local_path)
        return local_path

    def list_backups(self, prefix: str = "") -> list[dict]:
        if prefix:
            _validate_remote_id(prefix, field="prefix")
        results = []
        for meta in sorted(self.backup_dir.glob("*.meta.json")):
            manifest = json.loads(meta.read_text())
            if prefix and not manifest.get("remote_id", "").startswith(prefix):
                continue
            results.append(manifest)
        return results

    def delete(self, remote_id: str) -> None:
        _validate_remote_id(remote_id)
        data = self._data_path(remote_id)
        meta = self._meta_path(remote_id)
        if not data.resolve().is_relative_to(self.backup_dir):
            raise ValueError(f"Refusing remote_id that escapes backup_dir: {remote_id!r}")
        if data.exists():
            data.unlink()
        if meta.exists():
            meta.unlink()

    def test_connection(self) -> dict:
        ok = self.backup_dir.is_dir() and os.access(self.backup_dir, os.W_OK)
        return {"ok": ok, "provider": "local", "backup_dir": str(self.backup_dir)}
