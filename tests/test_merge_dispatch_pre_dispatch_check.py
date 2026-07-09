"""Tests for pre_dispatch_already_merged_check (BTCAAAAA-38470 Gap 1).

The helper closes the BTC-30048 chronic "Failed to create PR" loop on issues
whose fix is already on main via squash-merge. Two complementary strategies:

1. Byte-identity: every file touched by fix_sha is byte-equal between the fix
   commit and origin/main. Survives squash-merge and back-ports.
2. Squash-merge short-circuit: branch ref is gone AND origin/main's log
   references fix_sha's short SHA.

These tests mock git subprocess output so they don't require a live repo.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import merge_dispatch_routine as mdr  # noqa: E402


VALID_SHA = "1" * 40
VALID_SHORT = VALID_SHA[:8]


def _fake_proc(*, returncode: int, stdout: bytes = b"", stderr: bytes = b""):
    p = MagicMock()
    p.returncode = returncode
    p.stdout = stdout
    p.stderr = stderr
    return p


# --- (a) branch still alive: byte-identity fails, log-search no match -> proceed ---


def test_returns_false_when_branch_alive_and_files_differ():
    """Branch ref exists, files differ between fix-sha and origin/main.

    The helper must return (False, "") -- proceed with dispatch. We patch
    _run_git_text to simulate a live branch that has changes not yet on main.
    """
    def fake_run_git(args, timeout=10):
        if args[:2] == ["diff-tree", "--no-commit-id"]:
            return "src/foo.py\n"
        if args[:2] == ["branch", "-r"]:
            return "origin/fix/some-branch\n"
        if args[:2] == ["log", "origin/main"]:
            return ""
        return None

    def fake_subprocess_run(cmd, **kwargs):
        if len(cmd) >= 3 and cmd[1] == "show":
            if cmd[2].startswith(VALID_SHA):
                return _fake_proc(returncode=0, stdout=b"new content\n")
            return _fake_proc(returncode=0, stdout=b"old content\n")
        return _fake_proc(returncode=0, stdout=b"")

    with patch.object(mdr, "_run_git_text", side_effect=fake_run_git), \
         patch.object(mdr.subprocess, "run", side_effect=fake_subprocess_run), \
         patch.object(mdr, "is_ancestor_of_main", return_value=False):
        should_skip, reason = mdr.pre_dispatch_already_merged_check(VALID_SHA)

    assert should_skip is False
    assert reason == ""


# --- (b) branch gone + byte-identity matches -> skip with byte-identity reason ---


def test_returns_true_when_branch_gone_and_byte_identity_matches():
    """Branch ref gone, every file byte-equal between fix-sha and origin/main.

    The helper must return (True, "byte-identity: ...") -- skip dispatch.
    """
    def fake_run_git(args, timeout=10):
        if args[:2] == ["diff-tree", "--no-commit-id"]:
            return "src/foo.py\nREADME.md\n"
        if args[:2] == ["branch", "-r"]:
            return ""
        if args[:2] == ["log", "origin/main"]:
            return ""
        return None

    def fake_subprocess_run(cmd, **kwargs):
        if len(cmd) >= 3 and cmd[1] == "show":
            return _fake_proc(returncode=0, stdout=b"identical content here\n")
        return _fake_proc(returncode=0, stdout=b"")

    with patch.object(mdr, "_run_git_text", side_effect=fake_run_git), \
         patch.object(mdr.subprocess, "run", side_effect=fake_subprocess_run), \
         patch.object(mdr, "is_ancestor_of_main", return_value=False):
        should_skip, reason = mdr.pre_dispatch_already_merged_check(VALID_SHA)

    assert should_skip is True
    assert "byte-identity" in reason
    assert "2 file" in reason


# --- (c) branch gone + log-search matches -> skip with squash-merge short-circuit ---


def test_returns_true_when_branch_gone_and_log_grep_matches():
    """Branch ref gone, bytes differ BUT origin/main log references short SHA.

    The helper must return (True, "squash-merge short-circuit: ...") -- skip.
    """
    def fake_run_git(args, timeout=10):
        if args[:2] == ["diff-tree", "--no-commit-id"]:
            return "src/foo.py\n"
        if args[:2] == ["branch", "-r"]:
            return ""
        if args[:2] == ["log", "origin/main"]:
            return f"{VALID_SHORT} squash merge commit message\n"
        return None

    def fake_subprocess_run(cmd, **kwargs):
        if len(cmd) >= 3 and cmd[1] == "show":
            if cmd[2].startswith(VALID_SHA):
                return _fake_proc(returncode=0, stdout=b"new content\n")
            return _fake_proc(returncode=0, stdout=b"different content\n")
        return _fake_proc(returncode=0, stdout=b"")

    with patch.object(mdr, "_run_git_text", side_effect=fake_run_git), \
         patch.object(mdr.subprocess, "run", side_effect=fake_subprocess_run), \
         patch.object(mdr, "is_ancestor_of_main", return_value=False):
        should_skip, reason = mdr.pre_dispatch_already_merged_check(VALID_SHA)

    assert should_skip is True
    assert "squash-merge short-circuit" in reason
    assert VALID_SHORT in reason


# --- (d) branch gone + no log match + bytes differ -> re-trigger original error path ---


def test_returns_false_when_branch_gone_and_no_match():
    """Branch ref gone AND bytes differ AND no log match -> proceed (re-trigger).

    This is the original BTC-30048 symptom: the routine should still try.
    """
    def fake_run_git(args, timeout=10):
        if args[:2] == ["diff-tree", "--no-commit-id"]:
            return "src/foo.py\n"
        if args[:2] == ["branch", "-r"]:
            return ""
        if args[:2] == ["log", "origin/main"]:
            return ""
        return None

    def fake_subprocess_run(cmd, **kwargs):
        if len(cmd) >= 3 and cmd[1] == "show":
            if cmd[2].startswith(VALID_SHA):
                return _fake_proc(returncode=0, stdout=b"new content\n")
            return _fake_proc(returncode=0, stdout=b"completely different bytes\n")
        return _fake_proc(returncode=0, stdout=b"")

    with patch.object(mdr, "_run_git_text", side_effect=fake_run_git), \
         patch.object(mdr.subprocess, "run", side_effect=fake_subprocess_run), \
         patch.object(mdr, "is_ancestor_of_main", return_value=False):
        should_skip, reason = mdr.pre_dispatch_already_merged_check(VALID_SHA)

    assert should_skip is False
    assert reason == ""


# --- Input validation ---


def test_returns_false_for_empty_sha():
    should_skip, reason = mdr.pre_dispatch_already_merged_check("")
    assert should_skip is False
    assert reason == ""


def test_returns_false_for_short_sha():
    should_skip, reason = mdr.pre_dispatch_already_merged_check("abc123")
    assert should_skip is False
    assert reason == ""


def test_returns_false_when_git_subprocess_raises():
    """If git is unavailable, helper must not crash -- return (False, "")."""
    with patch.object(mdr, "list_files_changed_by_commit",
                      side_effect=RuntimeError("git not found")), \
         patch.object(mdr, "is_ancestor_of_main", return_value=False):
        should_skip, reason = mdr.pre_dispatch_already_merged_check(VALID_SHA)
    assert should_skip is False
    assert reason == ""


# --- BTCAAAAA-66670: Strategy 0 (ancestor-of-main) ---

# (e) SHA is an ancestor of origin/main → skip with ancestor-of-main reason.


def test_returns_true_via_strategy0_when_ancestor_of_main():
    """is_ancestor_of_main returns True → skip with ancestor-of-main reason.

    The cheapest check should win regardless of what the byte-identity or log-grep
    paths would have returned (no mocks needed — strategy 0 short-circuits).
    """
    with patch.object(mdr, "is_ancestor_of_main", return_value=True):
        should_skip, reason = mdr.pre_dispatch_already_merged_check(VALID_SHA)

    assert should_skip is True
    assert "ancestor-of-main" in reason
    assert VALID_SHORT in reason


# (f) Strategy 0 wins even when byte-identity would also have matched.


def test_strategy0_wins_over_byte_identity_match():
    """Both Strategy 0 (ancestor) and Strategy 1 (byte-identity) would trigger — S0 wins.

    Order matters: S0 runs first because it is a single `git merge-base` call vs the
    per-file `git show` round-trips S1 requires. The reason string must reference
    ancestor-of-main, NOT byte-identity.
    """
    def fake_run_git(args, timeout=10):
        if args[:2] == ["diff-tree", "--no-commit-id"]:
            return "src/foo.py\n"
        if args[:2] == ["branch", "-r"]:
            return ""
        if args[:2] == ["log", "origin/main"]:
            return ""
        return None

    def fake_subprocess_run(cmd, **kwargs):
        if len(cmd) >= 3 and cmd[1] == "show":
            # Identical bytes → Strategy 1 would succeed.
            return _fake_proc(returncode=0, stdout=b"identical bytes\n")
        return _fake_proc(returncode=0, stdout=b"")

    with patch.object(mdr, "_run_git_text", side_effect=fake_run_git), \
         patch.object(mdr.subprocess, "run", side_effect=fake_subprocess_run), \
         patch.object(mdr, "is_ancestor_of_main", return_value=True):
        should_skip, reason = mdr.pre_dispatch_already_merged_check(VALID_SHA)

    assert should_skip is True
    assert "ancestor-of-main" in reason
    assert "byte-identity" not in reason


# (g) Strategy 0 wins even when the squash-merge log-grep would also have matched.


def test_strategy0_wins_over_squash_merge_log_grep():
    """Strategy 0 and Strategy 2 (log-grep) both would trigger — S0 wins.

    Real BTCAAAAA-38544 / 38552 cases: the SHA is on main (ancestor) AND main's log
    still references the short SHA from an earlier squash-merge before a force-push.
    The cheapest check must short-circuit before we hit the log scan.
    """
    def fake_run_git(args, timeout=10):
        if args[:2] == ["diff-tree", "--no-commit-id"]:
            return "src/foo.py\n"
        if args[:2] == ["branch", "-r"]:
            return ""
        if args[:2] == ["log", "origin/main"]:
            return f"{VALID_SHORT} squash merge commit\n"
        return None

    def fake_subprocess_run(cmd, **kwargs):
        if len(cmd) >= 3 and cmd[1] == "show":
            # Different bytes — Strategy 1 would NOT have matched.
            if cmd[2].startswith(VALID_SHA):
                return _fake_proc(returncode=0, stdout=b"new content\n")
            return _fake_proc(returncode=0, stdout=b"different bytes\n")
        return _fake_proc(returncode=0, stdout=b"")

    with patch.object(mdr, "_run_git_text", side_effect=fake_run_git), \
         patch.object(mdr.subprocess, "run", side_effect=fake_subprocess_run), \
         patch.object(mdr, "is_ancestor_of_main", return_value=True):
        should_skip, reason = mdr.pre_dispatch_already_merged_check(VALID_SHA)

    assert should_skip is True
    assert "ancestor-of-main" in reason
    assert "squash-merge short-circuit" not in reason
