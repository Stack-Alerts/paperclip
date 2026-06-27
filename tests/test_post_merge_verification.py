"""Tests for post-merge verification (BTCAAAAA-38470 Gap 2).

BTC-38125 documented: routine logs `PR 200 merged successfully` but follow-up
`gh pr view 200` shows `state=OPEN, mergedAt=null`. This test asserts the
verifier raises a typed `MergeVerificationFailed` exception (NOT silent
success) when upstream view disagrees with the local log.

Also covers:
- token_scope_preflight returning (False, auth_failed_rc_<n>) on 401/403
- token_scope_preflight returning (True, "ok") on clean list
- verify_pr_merged returning the upstream dict when state=MERGED
- verify_pr_merged raising when gh pr view returns no data
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import merge_dispatch_execution_handler as mdeh  # noqa: E402


def _fake_proc(*, returncode: int, stdout: str = "", stderr: str = ""):
    p = MagicMock()
    p.returncode = returncode
    p.stdout = stdout
    p.stderr = stderr
    return p


# --- verify_pr_merged: success path ---


def test_verify_pr_merged_returns_upstream_view_on_merged_state():
    """When gh pr view reports state=MERGED, return the dict unchanged."""
    upstream = {
        "state": "MERGED",
        "mergedAt": "2026-06-25T12:00:00Z",
        "mergeCommit": {"oid": "abc1234567890abcdef1234567890abcdef12345"},
        "url": "https://github.com/Stack-Alerts/BTC-Trade-Engine-PaperClip/pull/200",
        "headRefName": "fix/BTCAAAAA-99999",
        "number": 200,
    }

    with patch.object(mdeh, "_run_gh_pr_view", return_value=upstream), \
         patch("time.sleep"):
        result = mdeh.verify_pr_merged(200)

    assert result == upstream
    assert result["state"] == "MERGED"


# --- verify_pr_merged: FAILURE path (BTC-38125 scenario) ---


def test_verify_pr_merged_raises_on_open_state_after_logged_merge():
    """When gh pr view reports state=OPEN after a logged merge, MUST raise.

    Silent success on this state is the BTC-38125 / BTC-30048 family of bugs.
    The exception must carry the upstream view as a structured payload so the
    routine can post it as an audit comment.
    """
    upstream = {
        "state": "OPEN",
        "mergedAt": None,
        "mergeCommit": None,
        "url": "https://github.com/Stack-Alerts/BTC-Trade-Engine-PaperClip/pull/200",
        "headRefName": "fix/BTCAAAAA-99999",
        "number": 200,
    }

    with patch.object(mdeh, "_run_gh_pr_view", return_value=upstream), \
         patch("time.sleep"):
        with pytest.raises(mdeh.MergeVerificationFailed) as excinfo:
            mdeh.verify_pr_merged(200)

    exc = excinfo.value
    assert exc.pr_number == 200
    assert exc.upstream_view == upstream
    assert "OPEN" in str(exc) or "200" in str(exc)


def test_verify_pr_merged_raises_when_upstream_view_is_none():
    """When gh pr view returns None (network/CLI failure), MUST raise."""
    with patch.object(mdeh, "_run_gh_pr_view", return_value=None), \
         patch("time.sleep"):
        with pytest.raises(mdeh.MergeVerificationFailed) as excinfo:
            mdeh.verify_pr_merged(200)

    exc = excinfo.value
    assert exc.pr_number == 200
    assert exc.upstream_view == {}
    assert "could not query" in str(exc).lower()


def test_verify_pr_merged_raises_on_closed_but_not_merged_state():
    """When state=CLOSED but mergedAt=null (closed without merge), MUST raise."""
    upstream = {
        "state": "CLOSED",
        "mergedAt": None,
        "mergeCommit": None,
        "url": "https://github.com/Stack-Alerts/BTC-Trade-Engine-PaperClip/pull/200",
        "headRefName": "fix/BTCAAAAA-99999",
        "number": 200,
    }

    with patch.object(mdeh, "_run_gh_pr_view", return_value=upstream), \
         patch("time.sleep"):
        with pytest.raises(mdeh.MergeVerificationFailed) as excinfo:
            mdeh.verify_pr_merged(200)

    exc = excinfo.value
    assert exc.pr_number == 200
    assert exc.upstream_view["state"] == "CLOSED"


# --- token_scope_preflight ---


def test_token_scope_preflight_returns_true_on_clean_list():
    """When gh pr list returns 0, preflight returns (True, 'ok')."""
    with patch("shutil.which", return_value="/usr/bin/gh"), \
         patch("subprocess.run", return_value=_fake_proc(returncode=0, stdout="[]")):
        ok, detail = mdeh.token_scope_preflight()
    assert ok is True
    assert detail == "ok"


def test_token_scope_preflight_returns_auth_failed_on_401():
    """On 401, preflight returns (False, 'auth_failed_rc_401:...').

    The routine caller checks for the 'auth_failed_rc_' prefix and escalates
    routine_token_has_no_upstream_access BEFORE any other work.
    """
    with patch("shutil.which", return_value="/usr/bin/gh"), \
         patch("subprocess.run",
               return_value=_fake_proc(returncode=401, stderr="Bad credentials")):
        ok, detail = mdeh.token_scope_preflight()
    assert ok is False
    assert detail.startswith("auth_failed_rc_401")
    assert "Bad credentials" in detail


def test_token_scope_preflight_returns_auth_failed_on_403():
    """On 403 (forbidden / insufficient_scope), same escalation."""
    with patch("shutil.which", return_value="/usr/bin/gh"), \
         patch("subprocess.run",
               return_value=_fake_proc(returncode=403, stderr="Resource not accessible")):
        ok, detail = mdeh.token_scope_preflight()
    assert ok is False
    assert detail.startswith("auth_failed_rc_403")


def test_token_scope_preflight_returns_soft_fail_on_404():
    """On 404 (repo not found / no access), soft-fail (not auth)."""
    with patch("shutil.which", return_value="/usr/bin/gh"), \
         patch("subprocess.run",
               return_value=_fake_proc(returncode=404, stderr="Not Found")):
        ok, detail = mdeh.token_scope_preflight()
    assert ok is False
    assert not detail.startswith("auth_failed_rc_")


def test_token_scope_preflight_returns_gh_not_on_path():
    """When gh CLI is missing entirely, return (False, 'gh_cli_not_on_path')."""
    with patch("shutil.which", return_value=None):
        ok, detail = mdeh.token_scope_preflight()
    assert ok is False
    assert detail == "gh_cli_not_on_path"


def test_token_scope_preflight_returns_preflight_timeout_on_hang():
    """When gh pr list hangs past 15s, return (False, 'preflight_timeout')."""
    import subprocess as sp
    with patch("shutil.which", return_value="/usr/bin/gh"), \
         patch("subprocess.run", side_effect=sp.TimeoutExpired(cmd="gh", timeout=15)):
        ok, detail = mdeh.token_scope_preflight()
    assert ok is False
    assert detail == "preflight_timeout"


# --- MergeVerificationFailed exception shape ---


def test_merge_verification_failed_carries_pr_number_and_view():
    """The typed exception must carry pr_number and upstream_view for the
    routine's escalation comment to reference both without re-querying."""
    upstream = {"state": "OPEN", "mergedAt": None}
    exc = mdeh.MergeVerificationFailed(
        pr_number=200,
        upstream_view=upstream,
        message="test message",
    )
    assert exc.pr_number == 200
    assert exc.upstream_view == upstream
    assert str(exc) == "test message"
    assert isinstance(exc, Exception)
