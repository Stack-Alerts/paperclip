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
_DEFAULT_URL = "git@github.com:Stack-Alerts/BTC-Trade-Engine-PaperClip.git"
_GIT_TIMEOUT = 30


def _init_repo(tmp: Path) -> Path:
    repo = tmp / "repo"
    repo.mkdir()
    sp.run(["git", "init"], cwd=str(repo), capture_output=True, check=True, timeout=_GIT_TIMEOUT)
    sp.run(["git", "config", "user.email", "test@test"], cwd=str(repo), capture_output=True, check=True, timeout=_GIT_TIMEOUT)
    sp.run(["git", "config", "user.name", "Test"], cwd=str(repo), capture_output=True, check=True, timeout=_GIT_TIMEOUT)
    (repo / "README.md").write_text("# test")
    sp.run(["git", "add", "README.md"], cwd=str(repo), capture_output=True, check=True, timeout=_GIT_TIMEOUT)
    sp.run(["git", "commit", "-m", "init"], cwd=str(repo), capture_output=True, check=True, timeout=_GIT_TIMEOUT)
    hook_dest = repo / ".git" / "hooks" / "post-commit"
    hook_dest.write_bytes(_HOOK_PATH.read_bytes())
    hook_dest.chmod(hook_dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return repo


class TestPostCommitHookAutoRecover:

    def test_hook_script_exists(self):
        assert _HOOK_PATH.exists(), f"Hook not found at {_HOOK_PATH}"
        assert os.access(str(_HOOK_PATH), os.X_OK), "Hook is not executable"

    def test_hook_adds_missing_remote(self, tmp_path):
        repo = _init_repo(tmp_path)
        assert "origin" not in _remotes(repo), "Fresh git init should have no remote"

        env = {**os.environ, "GIT_REMOTE_URL": _FAKE_URL}
        (repo / "file1.md").write_text("change 1")
        sp.run(["git", "add", "file1.md"], cwd=str(repo), capture_output=True, check=True, timeout=_GIT_TIMEOUT)
        proc = sp.run(
            ["git", "commit", "-m", "test hook recover"],
            cwd=str(repo),
            capture_output=True,
            text=True,
            env=env,
            check=False,
            timeout=_GIT_TIMEOUT,
        )
        print(f"commit stdout: {proc.stdout}")
        print(f"commit stderr: {proc.stderr}")

        remotes = _remotes(repo)
        assert "origin" in remotes, f"Expected origin remote to be re-added. Remotes: {remotes}"
        assert remotes["origin"] == _FAKE_URL, f"Expected {_FAKE_URL}, got {remotes['origin']}"

    def test_hook_respects_no_auto_push(self, tmp_path):
        repo = _init_repo(tmp_path)
        assert "origin" not in _remotes(repo)

        env = {**os.environ, "GIT_REMOTE_URL": _FAKE_URL, "NO_AUTO_PUSH": "1"}
        (repo / "file2.md").write_text("change 2")
        sp.run(["git", "add", "file2.md"], cwd=str(repo), capture_output=True, check=True, timeout=_GIT_TIMEOUT)
        proc = sp.run(
            ["git", "commit", "-m", "test no push"],
            cwd=str(repo),
            capture_output=True,
            text=True,
            env=env,
            check=False,
            timeout=_GIT_TIMEOUT,
        )
        print(f"stdout: {proc.stdout}")
        print(f"stderr: {proc.stderr}")
        assert proc.returncode == 0, "Commit should succeed even with NO_AUTO_PUSH"
        assert "origin" not in _remotes(repo), (
            "With NO_AUTO_PUSH=1 the hook exits early and should NOT recover the remote"
        )

    def test_hook_handles_detached_head(self, tmp_path):
        repo = _init_repo(tmp_path)
        env = {**os.environ, "GIT_REMOTE_URL": _FAKE_URL}

        head_sha = sp.run(
            ["git", "rev-parse", "HEAD"], cwd=str(repo), capture_output=True, text=True, check=True,
        ).stdout.strip()
        sp.run(["git", "checkout", "--detach", head_sha], cwd=str(repo), capture_output=True, check=True, timeout=_GIT_TIMEOUT)

        (repo / "detached.md").write_text("detached change")
        sp.run(["git", "add", "detached.md"], cwd=str(repo), capture_output=True, check=True, timeout=_GIT_TIMEOUT)
        proc = sp.run(
            ["git", "commit", "-m", "detached head test"],
            cwd=str(repo),
            capture_output=True,
            text=True,
            env=env,
            check=False,
            timeout=_GIT_TIMEOUT,
        )
        print(f"detached stdout: {proc.stdout}")
        print(f"detached stderr: {proc.stderr}")
        assert proc.returncode == 0

    def test_hook_preserves_existing_remote(self, tmp_path):
        repo = _init_repo(tmp_path)
        existing_url = "git@github.com:existing/repo.git"
        sp.run(["git", "remote", "add", "origin", existing_url], cwd=str(repo), capture_output=True, check=True, timeout=_GIT_TIMEOUT)

        env = {**os.environ, "GIT_REMOTE_URL": _FAKE_URL}
        (repo / "file3.md").write_text("change 3")
        sp.run(["git", "add", "file3.md"], cwd=str(repo), capture_output=True, check=True, timeout=_GIT_TIMEOUT)
        proc = sp.run(
            ["git", "commit", "-m", "test existing remote"],
            cwd=str(repo),
            capture_output=True,
            text=True,
            env=env,
            check=False,
            timeout=_GIT_TIMEOUT,
        )
        print(f"existing remote stdout: {proc.stdout}")
        print(f"existing remote stderr: {proc.stderr}")

        remotes = _remotes(repo)
        assert "origin" in remotes
        assert remotes["origin"] == existing_url, (
            f"Expected existing remote URL to be preserved: {existing_url}, got {remotes['origin']}"
        )

    def test_hook_default_url_fallback(self, tmp_path):
        repo = _init_repo(tmp_path)
        assert "origin" not in _remotes(repo)

        env = {**os.environ}
        if "GIT_REMOTE_URL" in env:
            del env["GIT_REMOTE_URL"]
        (repo / "file4.md").write_text("change 4")
        sp.run(["git", "add", "file4.md"], cwd=str(repo), capture_output=True, check=True, timeout=_GIT_TIMEOUT)
        proc = sp.run(
            ["git", "commit", "-m", "test default url fallback"],
            cwd=str(repo),
            capture_output=True,
            text=True,
            env=env,
            check=False,
            timeout=_GIT_TIMEOUT,
        )
        print(f"default url stdout: {proc.stdout}")
        print(f"default url stderr: {proc.stderr}")

        remotes = _remotes(repo)
        assert "origin" in remotes, f"Expected origin to be added with default URL. Remotes: {remotes}"
        assert remotes["origin"] == _DEFAULT_URL, (
            f"Expected default URL {_DEFAULT_URL}, got {remotes['origin']}"
        )

    def test_hook_idempotent_recovery(self, tmp_path):
        repo = _init_repo(tmp_path)
        assert "origin" not in _remotes(repo)

        env = {**os.environ, "GIT_REMOTE_URL": _FAKE_URL}

        (repo / "file5a.md").write_text("change 5a")
        sp.run(["git", "add", "file5a.md"], cwd=str(repo), capture_output=True, check=True, timeout=_GIT_TIMEOUT)
        proc1 = sp.run(
            ["git", "commit", "-m", "first commit"],
            cwd=str(repo),
            capture_output=True,
            text=True,
            env=env,
            check=False,
            timeout=_GIT_TIMEOUT,
        )
        print(f"first commit stdout: {proc1.stdout}")
        print(f"first commit stderr: {proc1.stderr}")

        remotes1 = _remotes(repo)
        assert "origin" in remotes1, "First commit should have added origin"
        assert remotes1["origin"] == _FAKE_URL

        (repo / "file5b.md").write_text("change 5b")
        sp.run(["git", "add", "file5b.md"], cwd=str(repo), capture_output=True, check=True, timeout=_GIT_TIMEOUT)
        proc2 = sp.run(
            ["git", "commit", "-m", "second commit"],
            cwd=str(repo),
            capture_output=True,
            text=True,
            env=env,
            check=False,
            timeout=_GIT_TIMEOUT,
        )
        print(f"second commit stdout: {proc2.stdout}")
        print(f"second commit stderr: {proc2.stderr}")

        remotes2 = _remotes(repo)
        assert "origin" in remotes2, "Second commit should preserve origin"
        assert remotes2["origin"] == _FAKE_URL, (
            f"Second commit should preserve same URL. Expected {_FAKE_URL}, got {remotes2['origin']}"
        )

    def test_hook_feature_branch(self, tmp_path):
        repo = _init_repo(tmp_path)
        env = {**os.environ, "GIT_REMOTE_URL": _FAKE_URL}

        sp.run(["git", "checkout", "-b", "feature/test-branch"], cwd=str(repo), capture_output=True, check=True, timeout=_GIT_TIMEOUT)
        (repo / "feat.md").write_text("feature change")
        sp.run(["git", "add", "feat.md"], cwd=str(repo), capture_output=True, check=True, timeout=_GIT_TIMEOUT)
        proc = sp.run(
            ["git", "commit", "-m", "feature branch commit"],
            cwd=str(repo),
            capture_output=True,
            text=True,
            env=env,
            check=False,
            timeout=_GIT_TIMEOUT,
        )
        print(f"feature branch stdout: {proc.stdout}")
        print(f"feature branch stderr: {proc.stderr}")

        assert proc.returncode == 0, "Commit on feature branch should succeed"
        branch = sp.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(repo), capture_output=True, text=True, check=True,
        ).stdout.strip()
        assert branch == "feature/test-branch"

        remotes = _remotes(repo)
        assert "origin" in remotes, "Origin should be recovered on feature branch"
        assert remotes["origin"] == _FAKE_URL

    def test_hook_exits_zero_on_push_failure(self, tmp_path):
        repo = _init_repo(tmp_path)
        env = {**os.environ, "GIT_REMOTE_URL": "git@github.com:nonexistent/never-gonna-push.git"}

        (repo / "file6.md").write_text("change 6")
        sp.run(["git", "add", "file6.md"], cwd=str(repo), capture_output=True, check=True, timeout=_GIT_TIMEOUT)
        proc = sp.run(
            ["git", "commit", "-m", "push failure test"],
            cwd=str(repo),
            capture_output=True,
            text=True,
            env=env,
            check=False,
            timeout=_GIT_TIMEOUT,
        )
        print(f"push fail stdout: {proc.stdout}")
        print(f"push fail stderr: {proc.stderr}")
        assert proc.returncode == 0, "Hook must exit 0 even when push fails"

    def test_hook_handles_empty_commit(self, tmp_path):
        repo = _init_repo(tmp_path)
        env = {**os.environ, "GIT_REMOTE_URL": _FAKE_URL}

        proc = sp.run(
            ["git", "commit", "--allow-empty", "-m", "empty commit"],
            cwd=str(repo),
            capture_output=True,
            text=True,
            env=env,
            check=False,
            timeout=_GIT_TIMEOUT,
        )
        print(f"empty commit stdout: {proc.stdout}")
        print(f"empty commit stderr: {proc.stderr}")
        assert proc.returncode == 0, "Empty commit should not crash the hook"


def _remotes(repo: Path) -> dict[str, str]:
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
