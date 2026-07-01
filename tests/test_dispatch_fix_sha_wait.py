"""Tests for the Gap 5 wait-for-Fix-SHA helper (BTCAAAAA-38472).

Closes the race window between an agent flipping an issue to `in_review`
with a Fix-SHA comment and the merge-dispatch periodic sweep picking it
up before the comment API has indexed the new comment. The helper
re-fetches with bounded retries and emits `defer_missing_fix_sha_at_dispatch`
on persistent absence.

Acceptance criteria:
- Dispatch routine waits up to 3x10s for `Fix-SHA:` comment to appear
  before acting.
- Log field `defer_missing_fix_sha_at_dispatch` is emitted cleanly when
  all retries are exhausted.
- Successful early return does NOT sleep the full backoff budget.
"""

import logging
import sys
import time as time_module
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import merge_dispatch_routine as mdr  # noqa: E402


VALID_SHA = "b" * 40


def _comments_with_sha(sha: str) -> list[dict]:
    return [{"id": "c-1", "body": f"Fix-SHA: {sha}\n\nPR opened.", "createdAt": "2026-06-30T20:00:00Z"}]


def _empty_comments() -> list[dict]:
    return []


def test_returns_sha_on_first_attempt_without_sleeping():
    sleep_calls: list[float] = []

    def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    with patch.object(mdr, "fetch_issue_comments", return_value=_comments_with_sha(VALID_SHA)), \
         patch.object(time_module, "sleep", side_effect=fake_sleep):
        result = mdr.wait_for_fix_sha_comment("issue-1", max_retries=3, sleep_s=10)

    assert result == VALID_SHA
    assert sleep_calls == [], "must not sleep when SHA appears on first fetch"


def test_returns_sha_on_second_attempt_after_one_sleep(caplog):
    sleep_calls: list[float] = []
    fetch_call_count = {"n": 0}

    def fake_fetch(issue_id: str) -> list[dict]:
        fetch_call_count["n"] += 1
        if fetch_call_count["n"] < 2:
            return _empty_comments()
        return _comments_with_sha(VALID_SHA)

    def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    with caplog.at_level(logging.INFO, logger="merge_dispatch_routine"), \
         patch.object(mdr, "fetch_issue_comments", side_effect=fake_fetch), \
         patch.object(time_module, "sleep", side_effect=fake_sleep):
        result = mdr.wait_for_fix_sha_comment("issue-2", max_retries=3, sleep_s=10)

    assert result == VALID_SHA
    assert sleep_calls == [10], "must sleep once between attempt 1 and attempt 2"


def test_returns_none_and_logs_when_sha_never_appears(caplog):
    sleep_calls: list[float] = []

    def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    with caplog.at_level(logging.INFO, logger="merge_dispatch"), \
         patch.object(mdr, "fetch_issue_comments", return_value=_empty_comments()), \
         patch.object(time_module, "sleep", side_effect=fake_sleep):
        result = mdr.wait_for_fix_sha_comment("issue-3", max_retries=3, sleep_s=10)

    assert result is None
    assert sleep_calls == [10, 10], "3 attempts -> 2 inter-attempt sleeps"
    matching = [
        r for r in caplog.records
        if "defer_missing_fix_sha_at_dispatch" in r.getMessage()
    ]
    assert matching, f"expected defer_missing_fix_sha_at_dispatch log, got {caplog.records}"
    msg = matching[-1].getMessage()
    assert "issue=issue-3" in msg
    assert "retries=3" in msg


def test_respects_custom_retry_and_sleep_arguments():
    sleep_calls: list[float] = []

    def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    with patch.object(mdr, "fetch_issue_comments", return_value=_empty_comments()), \
         patch.object(time_module, "sleep", side_effect=fake_sleep):
        result = mdr.wait_for_fix_sha_comment("issue-4", max_retries=2, sleep_s=2)

    assert result is None
    assert sleep_calls == [2], "2 attempts -> 1 inter-attempt sleep"


def test_defaults_match_acceptance_criteria():
    assert mdr._FIX_SHA_WAIT_DEFAULT_RETRIES == 3
    assert mdr._FIX_SHA_WAIT_DEFAULT_SLEEP_S == 10