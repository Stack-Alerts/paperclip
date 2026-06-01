"""Unit tests for deploy/backup/prune-local-dumps.sh.

The pruner keeps the newest N local Paperclip DB dumps under
``$PAPERCLIP_HOME/instances/default/data/backups/`` and writes a state file
documenting how much was reclaimed. Tested by stubbing a fake PAPERCLIP_HOME
under ``tmp_path`` and invoking the shell script via subprocess.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[2]
SCRIPT = REPO_ROOT / "deploy" / "backup" / "prune-local-dumps.sh"

pytestmark = [pytest.mark.bug("BTCAAAAA-33092"), pytest.mark.regression]


def _make_fake_backups(backup_dir: Path, count: int) -> list[Path]:
    """Create `count` fake dump files with distinct mtimes, newest last."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []
    for i in range(count):
        # Filename mirrors real format paperclip-YYYYMMDD-HHMMSS.sql.gz
        name = f"paperclip-2026{i:04d}-{i:06d}.sql.gz"
        p = backup_dir / name
        p.write_bytes(b"x" * 1024)  # 1 KiB body — small but real
        # Distinct mtime, oldest first, separated by 1h
        ts = 1700000000 + i * 3600
        os.utime(p, (ts, ts))
        files.append(p)
    return files


def _run(env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT)],
        env={**os.environ, **env},
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


class TestNoOpBelowThreshold:
    def test_does_nothing_when_fewer_than_keep(self, tmp_path):
        home = tmp_path / "ph"
        backup_dir = home / "instances" / "default" / "data" / "backups"
        files = _make_fake_backups(backup_dir, 5)
        result = _run({"PAPERCLIP_HOME": str(home), "BACKUP_RETENTION_KEEP": "10"})
        assert result.returncode == 0, result.stderr
        remaining = sorted(backup_dir.glob("paperclip-*.sql.gz"))
        assert len(remaining) == 5
        assert {p.name for p in remaining} == {p.name for p in files}
        assert "nothing to prune" in result.stdout.lower()

    def test_skips_missing_backup_dir(self, tmp_path):
        home = tmp_path / "ph-empty"
        # Don't create the data/backups dir at all
        result = _run({"PAPERCLIP_HOME": str(home), "BACKUP_RETENTION_KEEP": "10"})
        assert result.returncode == 0, result.stderr
        assert "does not exist" in result.stdout.lower()


class TestPrunesExtras:
    def test_keeps_newest_n_and_deletes_the_rest(self, tmp_path):
        home = tmp_path / "ph"
        backup_dir = home / "instances" / "default" / "data" / "backups"
        files = _make_fake_backups(backup_dir, 15)
        # Newest is files[-1] (highest mtime).
        result = _run({"PAPERCLIP_HOME": str(home), "BACKUP_RETENTION_KEEP": "10"})
        assert result.returncode == 0, result.stderr
        remaining = sorted(backup_dir.glob("paperclip-*.sql.gz"))
        assert len(remaining) == 10
        # The 10 newest (highest mtime) survived; the 5 oldest were deleted.
        expected_survivors = sorted(files[-10:])
        assert remaining == expected_survivors

    def test_respects_custom_retention(self, tmp_path):
        home = tmp_path / "ph"
        backup_dir = home / "instances" / "default" / "data" / "backups"
        files = _make_fake_backups(backup_dir, 8)
        result = _run({"PAPERCLIP_HOME": str(home), "BACKUP_RETENTION_KEEP": "3"})
        assert result.returncode == 0, result.stderr
        remaining = sorted(backup_dir.glob("paperclip-*.sql.gz"))
        assert len(remaining) == 3
        assert remaining == sorted(files[-3:])

    def test_writes_last_prune_state(self, tmp_path):
        home = tmp_path / "ph"
        backup_dir = home / "instances" / "default" / "data" / "backups"
        _make_fake_backups(backup_dir, 12)
        result = _run({"PAPERCLIP_HOME": str(home), "BACKUP_RETENTION_KEEP": "10"})
        assert result.returncode == 0, result.stderr
        state_file = home / "instances" / "default" / "backup-state" / "last-prune.json"
        assert state_file.exists(), result.stdout
        state = json.loads(state_file.read_text())
        assert state["kept"] == 10
        assert state["totalBefore"] == 12
        assert state["purgedCount"] == 2
        assert state["purgedBytes"] >= 2 * 1024
        assert state["bytesBefore"] > state["bytesAfter"]

    def test_idempotent_when_already_at_cap(self, tmp_path):
        home = tmp_path / "ph"
        backup_dir = home / "instances" / "default" / "data" / "backups"
        _make_fake_backups(backup_dir, 10)
        first = _run({"PAPERCLIP_HOME": str(home), "BACKUP_RETENTION_KEEP": "10"})
        second = _run({"PAPERCLIP_HOME": str(home), "BACKUP_RETENTION_KEEP": "10"})
        assert first.returncode == 0 and second.returncode == 0
        remaining = list(backup_dir.glob("paperclip-*.sql.gz"))
        assert len(remaining) == 10


class TestIgnoresUnrelatedFiles:
    def test_leaves_non_dump_files_alone(self, tmp_path):
        home = tmp_path / "ph"
        backup_dir = home / "instances" / "default" / "data" / "backups"
        _make_fake_backups(backup_dir, 15)
        other = backup_dir / "README.md"
        other.write_text("hands off")
        also = backup_dir / "paperclip-config.json"  # No .sql.gz suffix
        also.write_text("{}")
        result = _run({"PAPERCLIP_HOME": str(home), "BACKUP_RETENTION_KEEP": "10"})
        assert result.returncode == 0, result.stderr
        assert other.exists()
        assert also.exists()
        assert len(list(backup_dir.glob("paperclip-*.sql.gz"))) == 10
