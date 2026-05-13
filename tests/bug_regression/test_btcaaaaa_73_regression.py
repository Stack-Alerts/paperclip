"""
Regression tests for BTCAAAAA-73.

Bug: post-commit hook (scripts/hooks/post-commit) fails to auto-push when
the Paperclip harness strips the git remote config between heartbeats.

Fix: the hook now auto-detects a missing origin remote, re-adds it using
GIT_REMOTE_URL (or a hardcoded default), sets upstream tracking, and pushes.

These tests verify the hook logic in isolation using temp git repos.
"""

from __future__ import annotations

import os
import stat
import subprocess as sp
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-73"),
    pytest.mark.regression,
]

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parents[1]
_HOOK_PATH = _REPO_ROOT / "scripts" / "hooks" / "post-commit"
_FAKE_URL = "git@github.com:btc-aaaaa-73-test/repo.git"


def _init_repo(tmp: Path) -> Path:
    """Create a bare-bones git repo at *tmp* and install the post-commit hook."""
    repo = tmp / "repo"
    repo.mkdir()
    sp.run(["git", "init"], cwd=str(repo), capture_output=True, check=True)
    sp.run(["git", "config", "user.email", "test@test"], cwd=str(repo), capture_output=True, check=True)
    sp.run(["git", "config", "user.name", "Test"], cwd=str(repo), capture_output=True, check=True)
    (repo / "README.md").write_text("# test")
    sp.run(["git", "add", "README.md"], cwd=str(repo), capture_output=True, check=True)
    sp.run(["git", "commit", "-m", "init"], cwd=str(repo), capture_output=True, check=True)
    hook_dest = repo / ".git" / "hooks" / "post-commit"
    hook_dest.write_bytes(_HOOK_PATH.read_bytes())
    hook_dest.chmod(hook_dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return repo


class TestPostCommitHookAutoRecover:
    """Regression safety net for BTCAAAAA-73 — post-commit remote recovery."""

    def test_hook_script_exists(self):
        """The post-commit hook script exists and is executable."""
        assert _HOOK_PATH.exists(), f"Hook not found at {_HOOK_PATH}"
        assert os.access(str(_HOOK_PATH), os.X_OK), "Hook is not executable"

    def test_hook_adds_missing_remote(self, tmp_path):
        """When origin remote is missing, the hook auto-adds it before pushing."""
        repo = _init_repo(tmp_path)
        assert "origin" not in _remotes(repo), "Fresh git init should have no remote"

        env = {**os.environ, "GIT_REMOTE_URL": _FAKE_URL}
        (repo / "file1.md").write_text("change 1")
        sp.run(["git", "add", "file1.md"], cwd=str(repo), capture_output=True, check=True)
        proc = sp.run(
            ["git", "commit", "-m", "test hook recover"],
            cwd=str(repo),
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        print(f"commit stdout: {proc.stdout}")
        print(f"commit stderr: {proc.stderr}")

        remotes = _remotes(repo)
        assert "origin" in remotes, f"Expected origin remote to be re-added. Remotes: {remotes}"
        assert remotes["origin"] == _FAKE_URL, f"Expected {_FAKE_URL}, got {remotes['origin']}"

    def test_hook_respects_no_auto_push(self, tmp_path):
        """When NO_AUTO_PUSH=1, the hook skips auto-push and exits before remote recovery."""
        repo = _init_repo(tmp_path)
        assert "origin" not in _remotes(repo)

        env = {**os.environ, "GIT_REMOTE_URL": _FAKE_URL, "NO_AUTO_PUSH": "1"}
        (repo / "file2.md").write_text("change 2")
        sp.run(["git", "add", "file2.md"], cwd=str(repo), capture_output=True, check=True)
        proc = sp.run(
            ["git", "commit", "-m", "test no push"],
            cwd=str(repo),
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        print(f"stdout: {proc.stdout}")
        print(f"stderr: {proc.stderr}")
        assert proc.returncode == 0, "Commit should succeed even with NO_AUTO_PUSH"
        # The hook exits before remote recovery when NO_AUTO_PUSH=1,
        # so origin should remain absent
        assert "origin" not in _remotes(repo), (
            "With NO_AUTO_PUSH=1 the hook exits early and should NOT recover the remote"
        )

    def test_hook_handles_detached_head(self, tmp_path):
        """When HEAD is detached, the hook skips auto-push gracefully."""
        repo = _init_repo(tmp_path)
        env = {**os.environ, "GIT_REMOTE_URL": _FAKE_URL}

        head_sha = sp.run(
            ["git", "rev-parse", "HEAD"], cwd=str(repo), capture_output=True, text=True, check=True
        ).stdout.strip()
        sp.run(["git", "checkout", "--detach", head_sha], cwd=str(repo), capture_output=True, check=True)

        (repo / "detached.md").write_text("detached change")
        sp.run(["git", "add", "detached.md"], cwd=str(repo), capture_output=True, check=True)
        proc = sp.run(
            ["git", "commit", "-m", "detached head test"],
            cwd=str(repo),
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        print(f"detached stdout: {proc.stdout}")
        print(f"detached stderr: {proc.stderr}")
        # Should not crash — hook exits 0 for detached HEAD
        assert proc.returncode == 0

    def test_hook_preserves_existing_remote(self, tmp_path):
        """When origin remote already exists with the default URL, the hook does not overwrite it."""
        repo = _init_repo(tmp_path)
        existing_url = "git@github.com:existing/repo.git"
        sp.run(["git", "remote", "add", "origin", existing_url], cwd=str(repo), capture_output=True, check=True)

        env = {**os.environ, "GIT_REMOTE_URL": _FAKE_URL}
        (repo / "file3.md").write_text("change 3")
        sp.run(["git", "add", "file3.md"], cwd=str(repo), capture_output=True, check=True)
        proc = sp.run(
            ["git", "commit", "-m", "test existing remote"],
            cwd=str(repo),
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        print(f"existing remote stdout: {proc.stdout}")
        print(f"existing remote stderr: {proc.stderr}")

        remotes = _remotes(repo)
        assert "origin" in remotes
        assert remotes["origin"] == existing_url, (
            f"Expected existing remote URL to be preserved: {existing_url}, got {remotes['origin']}"
        )


def _remotes(repo: Path) -> dict[str, str]:
    """Return {remote_name: url} for the repo."""
    proc = sp.run(
        ["git", "remote", "-v"],
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    result: dict[str, str] = {}
    for line in proc.stdout.strip().splitlines():
        parts = line.split()
        if len(parts) >= 2:
            name = parts[0]
            url = parts[1]
            if name not in result:
                result[name] = url
    return result
