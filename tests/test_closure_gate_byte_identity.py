"""Tests for the squash-merge byte-identity fallback (BTCAAAAA-38471, Gap 3).

Uses a synthetic temp-git-repo to simulate the squash-merge scenario where
the pre-squash Fix-SHA is not an ancestor of main but the content is
byte-identically present.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from closure_gate_routine import (
    _file_content_hash,
    get_files_changed_by_commit,
    process_issue,
    verify_sha_byte_identity,
    verify_sha_on_main,
)

# ---------------------------------------------------------------------------
# Helpers for building a synthetic repo
# ---------------------------------------------------------------------------

def _git(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check,
    )


def _make_squash_repo() -> tuple[Path, str, str]:
    """Create a temp repo that simulates a squash-merge with a local origin remote.

    Returns (repo_path, feature_sha, squash_sha) where:
      - feature_sha: the pre-squash commit SHA (would be Fix-SHA in a PR)
      - squash_sha: the squash-merge commit on main (what origin/main points to)

    Sets up a bare clone as ``origin`` so ``origin/main`` resolves inside the
    working repo — matching what the production routine expects after
    ``fetch_origin_main()``.
    """
    tmp = Path(tempfile.mkdtemp())
    bare = Path(tempfile.mkdtemp())

    _git(["init", "-b", "main"], cwd=tmp)
    _git(["config", "user.email", "test@test.com"], cwd=tmp)
    _git(["config", "user.name", "Tester"], cwd=tmp)

    (tmp / "README.md").write_text("initial\n")
    _git(["add", "README.md"], cwd=tmp)
    _git(["commit", "-m", "initial"], cwd=tmp)

    _git(["checkout", "-b", "feature"], cwd=tmp)
    (tmp / "scripts").mkdir(parents=True, exist_ok=True)
    (tmp / "scripts" / "fix.py").write_text("# fix content\n")
    _git(["add", "scripts/fix.py"], cwd=tmp)
    _git(["commit", "-m", "fix: add fix.py"], cwd=tmp)
    feature_sha = _git(["rev-parse", "HEAD"], cwd=tmp).stdout.strip()

    _git(["checkout", "main"], cwd=tmp)
    _git(["merge", "--squash", "feature"], cwd=tmp)
    _git(["commit", "-m", "squash: merge feature"], cwd=tmp)
    squash_sha = _git(["rev-parse", "HEAD"], cwd=tmp).stdout.strip()

    is_ancestor = _git(
        ["merge-base", "--is-ancestor", feature_sha, "HEAD"],
        cwd=tmp,
        check=False,
    )
    assert is_ancestor.returncode != 0, "feature_sha should NOT be an ancestor after squash"

    # Set up a bare clone as origin and push main so origin/main resolves.
    _git(["clone", "--bare", str(tmp), str(bare)], cwd=tmp)
    _git(["remote", "add", "origin", str(bare)], cwd=tmp)
    _git(["fetch", "origin"], cwd=tmp)

    return tmp, feature_sha, squash_sha


# ---------------------------------------------------------------------------
# Tests for get_files_changed_by_commit
# ---------------------------------------------------------------------------

class TestGetFilesChangedByCommit:
    def test_returns_changed_files(self):
        repo, feature_sha, _ = _make_squash_repo()
        with patch("closure_gate_routine.REPO_ROOT", repo):
            files = get_files_changed_by_commit(feature_sha)
        assert files == ["scripts/fix.py"]

    def test_nonexistent_sha_returns_none(self):
        repo, _, _ = _make_squash_repo()
        with patch("closure_gate_routine.REPO_ROOT", repo):
            result = get_files_changed_by_commit("deadbeef" * 5)
        assert result is None

    def test_squash_commit_returns_files(self):
        """The squash commit itself also lists the changed files."""
        repo, _, squash_sha = _make_squash_repo()
        with patch("closure_gate_routine.REPO_ROOT", repo):
            files = get_files_changed_by_commit(squash_sha)
        assert "scripts/fix.py" in files


# ---------------------------------------------------------------------------
# Tests for _file_content_hash
# ---------------------------------------------------------------------------

class TestFileContentHash:
    def test_returns_sha256_for_existing_file(self):
        repo, feature_sha, _ = _make_squash_repo()
        with patch("closure_gate_routine.REPO_ROOT", repo):
            h = _file_content_hash(feature_sha, "scripts/fix.py")
        expected = hashlib.sha256(b"# fix content\n").hexdigest()
        assert h == expected

    def test_returns_none_for_missing_file(self):
        repo, feature_sha, _ = _make_squash_repo()
        with patch("closure_gate_routine.REPO_ROOT", repo):
            h = _file_content_hash(feature_sha, "nonexistent.py")
        assert h is None

    def test_main_and_feature_hash_match_after_squash(self):
        repo, feature_sha, _ = _make_squash_repo()
        with patch("closure_gate_routine.REPO_ROOT", repo):
            feature_hash = _file_content_hash(feature_sha, "scripts/fix.py")
            main_hash = _file_content_hash("HEAD", "scripts/fix.py")
        assert feature_hash == main_hash, "squash-merged file content should be byte-identical"


# ---------------------------------------------------------------------------
# Tests for verify_sha_byte_identity
# ---------------------------------------------------------------------------

class TestVerifyShaByteIdentity:
    def test_squash_merge_returns_true(self):
        """Pre-squash Fix-SHA should pass byte-identity check against main."""
        repo, feature_sha, _ = _make_squash_repo()
        with patch("closure_gate_routine.REPO_ROOT", repo):
            result = verify_sha_byte_identity(feature_sha)
        assert result is True

    def test_genuinely_missing_sha_returns_false(self):
        """SHA whose content is NOT on main should fail byte-identity."""
        repo, _, _ = _make_squash_repo()

        _git(["checkout", "-b", "divergent"], cwd=repo)
        (repo / "scripts" / "other.py").write_text("# different content not on main\n")
        _git(["add", "scripts/other.py"], cwd=repo)
        _git(["commit", "-m", "divergent fix"], cwd=repo)
        divergent_sha = _git(["rev-parse", "HEAD"], cwd=repo).stdout.strip()
        _git(["checkout", "main"], cwd=repo)

        with patch("closure_gate_routine.REPO_ROOT", repo):
            result = verify_sha_byte_identity(divergent_sha)
        assert result is False

    def test_nonexistent_sha_returns_false(self):
        repo, _, _ = _make_squash_repo()
        with patch("closure_gate_routine.REPO_ROOT", repo):
            result = verify_sha_byte_identity("0" * 40)
        assert result is False

    def test_logs_closure_path_on_success(self, caplog):
        """Should emit 'closure_path: byte_identical_via_archive' log on success."""
        import logging
        repo, feature_sha, _ = _make_squash_repo()
        with patch("closure_gate_routine.REPO_ROOT", repo):
            with caplog.at_level(logging.INFO, logger="closure_gate"):
                result = verify_sha_byte_identity(feature_sha)
        assert result is True
        assert any("closure_path: byte_identical_via_archive" in r.message for r in caplog.records)

    def test_file_deleted_in_both_passes(self):
        """File deleted by Fix-SHA that is also absent on main is a match."""
        repo = Path(tempfile.mkdtemp())
        bare = Path(tempfile.mkdtemp())
        _git(["init", "-b", "main"], cwd=repo)
        _git(["config", "user.email", "t@t.com"], cwd=repo)
        _git(["config", "user.name", "T"], cwd=repo)

        (repo / "to_delete.py").write_text("delete me\n")
        _git(["add", "to_delete.py"], cwd=repo)
        _git(["commit", "-m", "initial"], cwd=repo)

        _git(["checkout", "-b", "feature"], cwd=repo)
        _git(["rm", "to_delete.py"], cwd=repo)
        _git(["commit", "-m", "remove file"], cwd=repo)
        feature_sha = _git(["rev-parse", "HEAD"], cwd=repo).stdout.strip()

        _git(["checkout", "main"], cwd=repo)
        _git(["merge", "--squash", "feature"], cwd=repo)
        _git(["commit", "-m", "squash"], cwd=repo)

        _git(["clone", "--bare", str(repo), str(bare)], cwd=repo)
        _git(["remote", "add", "origin", str(bare)], cwd=repo)
        _git(["fetch", "origin"], cwd=repo)

        with patch("closure_gate_routine.REPO_ROOT", repo):
            result = verify_sha_byte_identity(feature_sha)
        assert result is True


# ---------------------------------------------------------------------------
# Integration: process_issue uses byte-identity fallback
# ---------------------------------------------------------------------------

class TestProcessIssueByteIdentityFallback:
    """process_issue should return 'verified' for squash-merged SHAs."""

    def _make_issue(self, sha: str) -> dict:
        return {
            "id": "issue-abc",
            "identifier": "BTCAAAAA-99999",
            "originKind": "code",
            "comments": [{"body": f"Fix-SHA: {sha}\n"}],
        }

    def test_squash_merge_sha_returns_verified(self):
        repo, feature_sha, _ = _make_squash_repo()
        issue = self._make_issue(feature_sha)

        with (
            patch("closure_gate_routine.REPO_ROOT", repo),
            patch("closure_gate_routine.fetch_issue_comments", return_value=issue["comments"]),
            patch("closure_gate_routine.has_fix_sha_none_exemption", return_value=False),
            patch("closure_gate_routine.extract_no_sha_tag_from_comments", return_value=None),
            patch("closure_gate_routine.detect_unfiled_deferrals", return_value=[]),
            patch("closure_gate_routine.detect_fabrication", return_value={}),
            patch("closure_gate_routine.verify_sha_on_main", return_value=False),
        ):
            action_type, success = process_issue(issue, {}, skip_git_fetch=True)

        assert action_type == "verified"
        assert success is True

    def test_genuinely_missing_sha_still_reopens(self):
        repo, _, _ = _make_squash_repo()
        fake_sha = "a" * 40
        issue = self._make_issue(fake_sha)

        with (
            patch("closure_gate_routine.REPO_ROOT", repo),
            patch("closure_gate_routine.fetch_issue_comments", return_value=issue["comments"]),
            patch("closure_gate_routine.has_fix_sha_none_exemption", return_value=False),
            patch("closure_gate_routine.extract_no_sha_tag_from_comments", return_value=None),
            patch("closure_gate_routine.detect_unfiled_deferrals", return_value=[]),
            patch("closure_gate_routine.detect_fabrication", return_value={}),
            patch("closure_gate_routine.verify_sha_on_main", return_value=False),
            patch("closure_gate_routine.reopen_issue", return_value=True),
        ):
            action_type, success = process_issue(issue, {}, skip_git_fetch=True)

        assert action_type == "reopen"
