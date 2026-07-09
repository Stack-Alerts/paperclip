"""Tests for the pre-completion diff-check warning cron (BTCAAAAA-39070).

The cron posts a warning comment to ``in_progress`` issues whose workspace
has uncommitted changes and whose ``executionLockedAt`` is older than the
10-minute "active heartbeat" window. Idempotency is enforced two ways:

1. State file ``data/precompletion_warnings.json`` records the last
   warning timestamp per issue (60-minute cooldown).
2. Comment-thread scan via ``has_precompletion_marker`` provides
   resilience when the ``data/`` directory is wiped.

These tests mock the API + filesystem so they run hermetically without a
Paperclip backend. The ``_disable_disk_state`` autouse fixture rewrites
``STATE_DIR`` to a ``tmp_path`` so the real state file is never touched.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "src"))

import precompletion_diff_check as pdc  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures + helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _disable_disk_state(monkeypatch, tmp_path):
    """Redirect STATE_DIR + STATE_FILE under tmp_path so tests never touch disk."""
    monkeypatch.setattr(pdc, "STATE_DIR", tmp_path)
    monkeypatch.setattr(pdc, "STATE_FILE", tmp_path / "precompletion_warnings.json")


class _PostRecorder:
    """Captures ``POST /api/issues/{id}/comments`` calls.

    Returns configurable status codes so tests can exercise both happy and
    failure paths. ``call_kwargs`` carries the json body, headers, and
    timeout so tests can assert the run-id header is wired in.
    """

    def __init__(self, status_code: int = 200):
        self.status_code = status_code
        self.calls: list[dict] = []

    def __call__(self, url: str, *, json_body=None, headers=None, timeout=None, **_):
        self.calls.append(
            {
                "url": url,
                "json": json_body,
                "headers": dict(headers or {}),
                "timeout": timeout,
            }
        )
        resp = SimpleNamespace(
            ok=(200 <= self.status_code < 300),
            status_code=self.status_code,
            text=f"status {self.status_code}",
        )
        return resp


def _issue(
    issue_id: str,
    *,
    assignee: str = "agent-1",
    workspace_id: str = "ws-1",
    locked_minutes_ago: float | None = 15,
    fix_branch: str | None = "fix/BTCAAAAA-39070-precompletion-warning",
) -> dict:
    """Build a minimal issue dict that mirrors what ``list_issues`` returns."""
    issue = {
        "id": issue_id,
        "assigneeAgentId": assignee,
        "executionWorkspaceId": workspace_id,
        "fixBranch": fix_branch,
    }
    if locked_minutes_ago is not None:
        ts = datetime.now(timezone.utc) - timedelta(minutes=locked_minutes_ago)
        issue["executionLockedAt"] = ts.isoformat()
    return issue


def _workspace(
    ws_id: str,
    *,
    cwd: str | None = "/tmp/repo",
    source_type: str = "git_repo",
) -> dict:
    return {
        "id": ws_id,
        "cwd": cwd,
        "sourceType": source_type,
        "name": ws_id,
    }


@pytest.fixture
def fake_session():
    """Patch ``_session`` so we get a deterministic ``_PostRecorder`` instead."""
    recorder = _PostRecorder()

    class _SessionCtx:
        def __enter__(self_inner):
            inner = SimpleNamespace()
            inner.post = lambda url, json=None, headers=None, timeout=None, **kw: recorder(
                url, json_body=json, headers=headers, timeout=timeout, **kw
            )
            return inner

        def __exit__(self_inner, exc_type, exc, tb):
            return False

    with patch.object(pdc, "_session", _SessionCtx):
        yield recorder


# ---------------------------------------------------------------------------
# Happy path + post failures
# ---------------------------------------------------------------------------


def test_happy_path_dirty_workspace_stale_lock_posts_warning(fake_session, monkeypatch):
    # The heartbeat shell inherits PAPERCLIP_RUN_ID; clear it so we can assert
    # the header is None for the default (no-run-id) case in this test.
    monkeypatch.delenv("PAPERCLIP_RUN_ID", raising=False)
    issue = _issue("issue-1", locked_minutes_ago=15)
    workspaces = {"ws-1": _workspace("ws-1")}
    with patch.object(pdc, "_workspace_has_uncommitted_changes", return_value=True):
        posted = pdc.check_precompletion_warnings(
            state={},
            workspaces=workspaces,
            issues=[issue],
            sleep_fn=lambda _s: None,
        )
    assert posted == 1
    assert len(fake_session.calls) == 1
    call = fake_session.calls[0]
    assert call["url"].endswith("/api/issues/issue-1/comments")
    assert "Pre-Completion Diff Warning" in call["json"]["body"]
    assert call["headers"].get("X-Paperclip-Run-Id") is None


def test_happy_path_carries_run_id_header(fake_session, monkeypatch):
    monkeypatch.setenv("PAPERCLIP_RUN_ID", "run-xyz")
    issue = _issue("issue-1", locked_minutes_ago=15)
    workspaces = {"ws-1": _workspace("ws-1")}
    with patch.object(pdc, "_workspace_has_uncommitted_changes", return_value=True):
        pdc.check_precompletion_warnings(
            state={},
            workspaces=workspaces,
            issues=[issue],
            sleep_fn=lambda _s: None,
        )
    assert fake_session.calls[0]["headers"]["X-Paperclip-Run-Id"] == "run-xyz"


def test_post_failure_leaves_cooldown_unset(fake_session):
    fake_session.status_code = 500
    issue = _issue("issue-1", locked_minutes_ago=15)
    workspaces = {"ws-1": _workspace("ws-1")}
    state: dict[str, str] = {}
    with patch.object(pdc, "_workspace_has_uncommitted_changes", return_value=True):
        posted = pdc.check_precompletion_warnings(
            state=state,
            workspaces=workspaces,
            issues=[issue],
            sleep_fn=lambda _s: None,
        )
    assert posted == 0
    # Cooldown only records AFTER successful post — failure must not poison
    # subsequent cycles by claiming we warned when we did not.
    assert "issue-1" not in state


# ---------------------------------------------------------------------------
# Cooldown (state file) gate
# ---------------------------------------------------------------------------


def test_state_file_cooldown_skips_within_60_minutes(fake_session):
    issue = _issue("issue-1", locked_minutes_ago=15)
    workspaces = {"ws-1": _workspace("ws-1")}
    state = {"issue-1": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()}
    with patch.object(pdc, "_workspace_has_uncommitted_changes", return_value=True):
        posted = pdc.check_precompletion_warnings(
            state=state,
            workspaces=workspaces,
            issues=[issue],
            sleep_fn=lambda _s: None,
        )
    assert posted == 0
    assert fake_session.calls == []


def test_state_file_cooldown_expired_allows_re_warn(fake_session):
    issue = _issue("issue-1", locked_minutes_ago=15)
    workspaces = {"ws-1": _workspace("ws-1")}
    state = {"issue-1": (datetime.now(timezone.utc) - timedelta(minutes=120)).isoformat()}
    with patch.object(pdc, "_workspace_has_uncommitted_changes", return_value=True):
        posted = pdc.check_precompletion_warnings(
            state=state,
            workspaces=workspaces,
            issues=[issue],
            sleep_fn=lambda _s: None,
        )
    assert posted == 1


# ---------------------------------------------------------------------------
# Marker (comment-thread) gate
# ---------------------------------------------------------------------------


def test_thread_marker_present_skips_post_but_records_cooldown(fake_session):
    issue = _issue("issue-1", locked_minutes_ago=15)
    workspaces = {"ws-1": _workspace("ws-1")}
    state: dict[str, str] = {}
    with patch.object(pdc, "_workspace_has_uncommitted_changes", return_value=True), patch.object(
        pdc, "_has_marker_in_thread", return_value=True
    ):
        posted = pdc.check_precompletion_warnings(
            state=state,
            workspaces=workspaces,
            issues=[issue],
            sleep_fn=lambda _s: None,
        )
    assert posted == 0
    assert fake_session.calls == []
    # State record keeps the cooldown coherent even when the data/ file is wiped.
    assert "issue-1" in state


def test_thread_marker_present_with_active_cooldown_does_not_overwrite(fake_session):
    issue = _issue("issue-1", locked_minutes_ago=15)
    workspaces = {"ws-1": _workspace("ws-1")}
    stale_ts = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    state = {"issue-1": stale_ts}
    with patch.object(pdc, "_workspace_has_uncommitted_changes", return_value=True), patch.object(
        pdc, "_has_marker_in_thread", return_value=True
    ):
        pdc.check_precompletion_warnings(
            state=state,
            workspaces=workspaces,
            issues=[issue],
            sleep_fn=lambda _s: None,
        )
    # The stale timestamp is preserved — we don't refresh it just because we
    # observed the marker; that would push the cooldown past the actual
    # last-warn time and risk over-warning.
    assert state["issue-1"] == stale_ts


# ---------------------------------------------------------------------------
# Fresh-checkout (active heartbeat) gate
# ---------------------------------------------------------------------------


def test_fresh_checkout_skips(fake_session):
    issue = _issue("issue-1", locked_minutes_ago=2)
    workspaces = {"ws-1": _workspace("ws-1")}
    with patch.object(pdc, "_workspace_has_uncommitted_changes", return_value=True):
        posted = pdc.check_precompletion_warnings(
            state={},
            workspaces=workspaces,
            issues=[issue],
            sleep_fn=lambda _s: None,
        )
    assert posted == 0
    assert fake_session.calls == []


def test_missing_lock_ts_treated_as_inactive_checkout(fake_session):
    issue = _issue("issue-1", locked_minutes_ago=None)
    workspaces = {"ws-1": _workspace("ws-1")}
    with patch.object(pdc, "_workspace_has_uncommitted_changes", return_value=True):
        posted = pdc.check_precompletion_warnings(
            state={},
            workspaces=workspaces,
            issues=[issue],
            sleep_fn=lambda _s: None,
        )
    # No lock record = cron SHOULD warn. This guards the off-by-one risk
    # where ``locked_minutes_ago=None`` is mistaken for "currently checked out".
    assert posted == 1


# ---------------------------------------------------------------------------
# Workspace gates
# ---------------------------------------------------------------------------


def test_missing_workspace_skips(fake_session):
    issue = _issue("issue-1", workspace_id="ws-unknown")
    workspaces = {"ws-1": _workspace("ws-1")}
    with patch.object(pdc, "_workspace_has_uncommitted_changes", return_value=True):
        posted = pdc.check_precompletion_warnings(
            state={},
            workspaces=workspaces,
            issues=[issue],
            sleep_fn=lambda _s: None,
        )
    assert posted == 0
    assert fake_session.calls == []


def test_non_git_repo_workspace_skips(fake_session):
    issue = _issue("issue-1")
    workspaces = {"ws-1": _workspace("ws-1", source_type="local_path")}
    with patch.object(pdc, "_workspace_has_uncommitted_changes", return_value=True):
        posted = pdc.check_precompletion_warnings(
            state={},
            workspaces=workspaces,
            issues=[issue],
            sleep_fn=lambda _s: None,
        )
    assert posted == 0


def test_workspace_with_no_cwd_skips(fake_session):
    issue = _issue("issue-1")
    workspaces = {"ws-1": _workspace("ws-1", cwd=None)}
    with patch.object(pdc, "_workspace_has_uncommitted_changes", return_value=True):
        posted = pdc.check_precompletion_warnings(
            state={},
            workspaces=workspaces,
            issues=[issue],
            sleep_fn=lambda _s: None,
        )
    assert posted == 0


def test_no_execution_workspace_id_skips(fake_session):
    issue = _issue("issue-1", workspace_id=None)
    workspaces = {"ws-1": _workspace("ws-1")}
    with patch.object(pdc, "_workspace_has_uncommitted_changes", return_value=True):
        posted = pdc.check_precompletion_warnings(
            state={},
            workspaces=workspaces,
            issues=[issue],
            sleep_fn=lambda _s: None,
        )
    assert posted == 0


# ---------------------------------------------------------------------------
# Git diff gate
# ---------------------------------------------------------------------------


def test_clean_workspace_skips_no_post(fake_session):
    issue = _issue("issue-1", locked_minutes_ago=15)
    workspaces = {"ws-1": _workspace("ws-1")}
    with patch.object(pdc, "_workspace_has_uncommitted_changes", return_value=False):
        posted = pdc.check_precompletion_warnings(
            state={},
            workspaces=workspaces,
            issues=[issue],
            sleep_fn=lambda _s: None,
        )
    assert posted == 0
    assert fake_session.calls == []


# ---------------------------------------------------------------------------
# Empty / multi-issue behavior
# ---------------------------------------------------------------------------


def test_empty_in_progress_set_is_a_noop(fake_session):
    posted = pdc.check_precompletion_warnings(
        state={},
        workspaces={"ws-1": _workspace("ws-1")},
        issues=[],
        sleep_fn=lambda _s: None,
    )
    assert posted == 0
    assert fake_session.calls == []


def test_multiple_issues_each_get_their_own_decision(fake_session):
    issues = [
        _issue("issue-a", locked_minutes_ago=15),
        _issue("issue-b", locked_minutes_ago=2),  # fresh checkout → skip
        _issue("issue-c", workspace_id="ws-unknown"),  # missing ws → skip
    ]
    workspaces = {"ws-1": _workspace("ws-1")}

    def fake_diff(cwd):
        return True  # everything else would be dirty

    with patch.object(pdc, "_workspace_has_uncommitted_changes", side_effect=fake_diff):
        posted = pdc.check_precompletion_warnings(
            state={},
            workspaces=workspaces,
            issues=issues,
            sleep_fn=lambda _s: None,
        )
    assert posted == 1
    assert len(fake_session.calls) == 1
    assert fake_session.calls[0]["url"].endswith("/api/issues/issue-a/comments")


# ---------------------------------------------------------------------------
# Comment body
# ---------------------------------------------------------------------------


def test_format_warning_body_includes_marker_and_branch_hint():
    body = pdc._format_warning_body("fix/BTCAAAAA-39070-precompletion-warning")
    # Marker must be on the FIRST non-blank line so has_precompletion_marker
    # detects it as the line-anchored heading.
    first_line = body.splitlines()[0]
    assert first_line.strip() == "## Pre-Completion Diff Warning"
    assert "fix/BTCAAAAA-39070-precompletion-warning" in body


def test_format_warning_body_falls_back_to_generic_branch_hint():
    body = pdc._format_warning_body(None)
    assert "your fix branch" in body
    first_line = body.splitlines()[0]
    assert first_line.strip() == "## Pre-Completion Diff Warning"


def test_format_warning_body_falls_back_when_blank_string():
    body = pdc._format_warning_body("")
    assert "your fix branch" in body


# ---------------------------------------------------------------------------
# State file IO
# ---------------------------------------------------------------------------


def test_save_state_writes_atomically(tmp_path, monkeypatch):
    monkeypatch.setattr(pdc, "STATE_DIR", tmp_path)
    monkeypatch.setattr(pdc, "STATE_FILE", tmp_path / "precompletion_warnings.json")
    pdc.save_state({"issue-1": "2026-07-09T13:45:12+00:00"})
    written = (tmp_path / "precompletion_warnings.json").read_text()
    assert "issue-1" in written
    # Atomic write should never leave a .tmp behind.
    assert not (tmp_path / "precompletion_warnings.json.tmp").exists()


def test_load_state_returns_empty_on_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(pdc, "STATE_DIR", tmp_path)
    monkeypatch.setattr(pdc, "STATE_FILE", tmp_path / "precompletion_warnings.json")
    assert pdc.load_state() == {}


def test_load_state_drops_non_string_entries(tmp_path, monkeypatch):
    monkeypatch.setattr(pdc, "STATE_DIR", tmp_path)
    monkeypatch.setattr(pdc, "STATE_FILE", tmp_path / "precompletion_warnings.json")
    (tmp_path / "precompletion_warnings.json").write_text(
        json.dumps({"good": "2026-07-09T13:45:12+00:00", "bad": 12345})
    )
    assert pdc.load_state() == {"good": "2026-07-09T13:45:12+00:00"}


def test_load_state_returns_empty_on_garbage_file(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(pdc, "STATE_DIR", tmp_path)
    monkeypatch.setattr(pdc, "STATE_FILE", tmp_path / "precompletion_warnings.json")
    (tmp_path / "precompletion_warnings.json").write_text("not json {")
    with caplog.at_level(logging.WARNING):
        assert pdc.load_state() == {}
    assert "could not load" in caplog.text


# ---------------------------------------------------------------------------
# is_recent_warning / is_fresh_checkout edge cases
# ---------------------------------------------------------------------------


def test_is_recent_warning_handles_missing_entry():
    assert pdc._is_recent_warning({}, "issue-x") is False


def test_is_recent_warning_handles_malformed_timestamp():
    assert pdc._is_recent_warning({"issue-x": "not-a-timestamp"}, "issue-x") is False


def test_is_recent_warning_handles_none_value():
    assert pdc._is_recent_warning({"issue-x": None}, "issue-x") is False  # type: ignore[dict-item]


def test_is_fresh_checkout_handles_missing_lock_ts():
    assert pdc._is_fresh_checkout({"id": "x"}) is False


def test_is_fresh_checkout_handles_malformed_lock_ts():
    assert pdc._is_fresh_checkout({"id": "x", "executionLockedAt": "garbage"}) is False


def test_is_fresh_checkout_true_within_window():
    issue = _issue("issue-x", locked_minutes_ago=2)
    assert pdc._is_fresh_checkout(issue) is True