"""Rclone-based backup provider — wraps the rclone binary."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .provider import BackupProvider

RCLONE_BIN = os.environ.get("RCLONE_BIN", "/usr/bin/rclone")
DEFAULT_CONFIG = os.path.expanduser("~/.config/rclone/rclone.conf")


class RcloneProvider(BackupProvider):
    """Upload/download backups using an rclone remote."""

    def __init__(self, remote: str, config_path: str | None = None) -> None:
        """
        Args:
            remote: rclone remote path prefix, e.g. ``gdrive:backups/btc``.
            config_path: path to rclone.conf; defaults to $RCLONE_CONFIG or ~/.config/rclone/rclone.conf.
        """
        self.remote = remote.rstrip("/")
        self.config_path = config_path or os.environ.get("RCLONE_CONFIG", DEFAULT_CONFIG)

    def _run(self, args: list[str], **kwargs) -> subprocess.CompletedProcess:
        cmd = [RCLONE_BIN, "--config", self.config_path] + args
        result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
        if result.returncode != 0:
            raise RuntimeError(
                f"rclone exited {result.returncode}: {result.stderr.strip()}"
            )
        return result

    def upload(self, local_path: Path | str, remote_id: str) -> dict:
        local_path = Path(local_path)
        data = local_path.read_bytes()
        sha256 = hashlib.sha256(data).hexdigest()
        remote_dest = f"{self.remote}/{remote_id}"
        self._run(["copyto", str(local_path), remote_dest])
        manifest = {
            "remote_id": remote_id,
            "provider": "rclone",
            "remote": self.remote,
            "size": len(data),
            "sha256": sha256,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "source": str(local_path),
        }
        return manifest

    def download(self, remote_id: str, local_path: Path | str) -> Path:
        local_path = Path(local_path)
        remote_src = f"{self.remote}/{remote_id}"
        self._run(["copyto", remote_src, str(local_path)])
        return local_path

    def list_backups(self, prefix: str = "") -> list[dict]:
        remote_path = f"{self.remote}/{prefix}" if prefix else self.remote
        result = self._run(["lsjson", remote_path])
        entries = json.loads(result.stdout)
        backups = []
        for entry in entries:
            if not entry.get("IsDir"):
                backups.append(
                    {
                        "remote_id": entry["Name"],
                        "provider": "rclone",
                        "remote": self.remote,
                        "size": entry.get("Size", 0),
                        "modified_at": entry.get("ModTime", ""),
                    }
                )
        return backups

    def delete(self, remote_id: str) -> None:
        remote_target = f"{self.remote}/{remote_id}"
        self._run(["deletefile", remote_target])

    def test_connection(self) -> dict:
        try:
            self._run(["lsd", self.remote], timeout=15)
            return {"ok": True, "provider": "rclone", "remote": self.remote}
        except Exception as exc:
            return {"ok": False, "provider": "rclone", "remote": self.remote, "error": str(exc)}
