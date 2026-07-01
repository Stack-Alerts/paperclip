"""Tests for merge-dispatch event-gate (Stage 1) — BTCAAAAA-38258.

Mirrors the closure-gate watermark + safety-floor pattern (BTCAAAAA-37917) so
the periodic sweep does no work when nothing relevant changed. Behavior is
controlled by the MERGE_DISPATCH_IDEMPOTENT env var (default: true) so the
team can roll back without code change.

These tests cover:
  - watermark load/save round-trip
  - safety floor (10 min default) blocks re-scan
  - watermark set-inequality forces a full run
  - kill-switch env var disables gating
  - dispatch_for_issue() (agent-finish path) is NEVER gated
  - telemetry log line is emitted on every run
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import merge_dispatch_routine as mdr  # noqa: E402


# --- Watermark load/save round-trip ---


def test_load_watermark_returns_none_when_file_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(mdr, "WATERMARK_FILE", tmp_path / "no-such-watermark.json")
    assert mdr.load_watermark() is None


def test_load_watermark_returns_dict_when_present(tmp_path, monkeypatch):
    monkeypatch.setattr(mdr, "WATERMARK_FILE", tmp_path / "wm.json")
    payload = {
        "lastScanAt": datetime.now(timezone.utc).isoformat(),
        "lastInReviewIds": ["id-a", "id-b"],
    }
    mdr.WATERMARK_FILE.write_text(json.dumps(payload))
    out = mdr.load_watermark()
    assert out == payload


def test_load_watermark_handles_corrupt_file(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(mdr, "WATERMARK_FILE", tmp_path / "wm.json")
    mdr.WATERMARK_FILE.write_text("{not valid json")
    with caplog.at_level("WARNING"):
        out = mdr.load_watermark()
    assert out is None


def test_save_watermark_creates_file_and_dirs(tmp_path, monkeypatch):
    target = tmp_path / "subdir" / "wm.json"
    monkeypatch.setattr(mdr, "WATERMARK_FILE", target)
    ok = mdr.save_watermark(
        in_review_ids=["id-a", "id-b"],
        routine_origin_id="orig",
        issue_id="iss",
    )
    assert ok is True
    assert target.exists()
    payload = json.loads(target.read_text())
    assert sorted(payload["lastInReviewIds"]) == ["id-a", "id-b"]
    assert payload["routineOriginId"] == "orig"
    assert payload["issueId"] == "iss"
    assert "lastScanAt" in payload


def test_save_watermark_sorts_and_dedupes(tmp_path, monkeypatch):
    target = tmp_path / "wm.json"
    monkeypatch.setattr(mdr, "WATERMARK_FILE", target)
    mdr.save_watermark(in_review_ids=["b", "a", "a", ""], routine_origin_id="")
    payload = json.loads(target.read_text())
    assert payload["lastInReviewIds"] == ["a", "b"]


# --- Safety floor & set comparison ---


def test_check_early_exit_returns_false_when_kill_switch_off(monkeypatch):
    monkeypatch.setattr(mdr, "MERGE_DISPATCH_IDEMPOTENT", False)
    assert mdr.check_early_exit(current_in_review_ids=["x"], watermark={}) is False


def test_check_early_exit_returns_false_when_no_watermark(tmp_path, monkeypatch):
    monkeypatch.setattr(mdr, "WATERMARK_FILE", tmp_path / "missing.json")
    monkeypatch.setattr(mdr, "MERGE_DISPATCH_IDEMPOTENT", True)
    assert mdr.check_early_exit(current_in_review_ids=["x"]) is False


def test_check_early_exit_returns_false_when_watermark_stale(
    tmp_path, monkeypatch
):
    target = tmp_path / "wm.json"
    monkeypatch.setattr(mdr, "WATERMARK_FILE", target)
    monkeypatch.setattr(mdr, "MERGE_DISPATCH_IDEMPOTENT", True)
    stale = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
    target.write_text(
        json.dumps(
            {
                "lastScanAt": stale,
                "lastInReviewIds": ["x"],
            }
        )
    )
    assert mdr.check_early_exit(current_in_review_ids=["x"]) is False


def test_check_early_exit_returns_true_when_fresh_and_unchanged(
    tmp_path, monkeypatch
):
    target = tmp_path / "wm.json"
    monkeypatch.setattr(mdr, "WATERMARK_FILE", target)
    monkeypatch.setattr(mdr, "MERGE_DISPATCH_IDEMPOTENT", True)
    target.write_text(
        json.dumps(
            {
                "lastScanAt": datetime.now(timezone.utc).isoformat(),
                "lastInReviewIds": ["x", "y"],
            }
        )
    )
    assert mdr.check_early_exit(current_in_review_ids=["y", "x"]) is True


def test_check_early_exit_returns_false_when_set_differs(
    tmp_path, monkeypatch
):
    target = tmp_path / "wm.json"
    monkeypatch.setattr(mdr, "WATERMARK_FILE", target)
    monkeypatch.setattr(mdr, "MERGE_DISPATCH_IDEMPOTENT", True)
    target.write_text(
        json.dumps(
            {
                "lastScanAt": datetime.now(timezone.utc).isoformat(),
                "lastInReviewIds": ["x"],
            }
        )
    )
    # New issue appeared in in_review — must re-scan
    assert mdr.check_early_exit(current_in_review_ids=["x", "y"]) is False


def test_check_early_exit_handles_unparseable_timestamp(
    tmp_path, monkeypatch
):
    target = tmp_path / "wm.json"
    monkeypatch.setattr(mdr, "WATERMARK_FILE", target)
    monkeypatch.setattr(mdr, "MERGE_DISPATCH_IDEMPOTENT", True)
    target.write_text(
        json.dumps({"lastScanAt": "not-a-date", "lastInReviewIds": ["x"]})
    )
    assert mdr.check_early_exit(current_in_review_ids=["x"]) is False


# --- Telemetry log line ---


def test_emit_telemetry_log_includes_required_fields(caplog):
    caplog.set_level("INFO", logger="merge_dispatch.telemetry")
    mdr.emit_telemetry_log(
        fired_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        idempotency_skip=True,
        would_work_count=0,
        merged_count=0,
    )
    record = next(r for r in caplog.records if r.name == "merge_dispatch.telemetry")
    payload = json.loads(record.getMessage())
    assert payload["routine"] == "merge_dispatch"
    assert payload["idempotency_skip"] is True
    assert payload["would_work_count"] == 0
    assert payload["merged_count"] == 0
    assert "fired_at" in payload


# --- dispatch_for_issue (agent-finish path) is NEVER gated ---


def test_dispatch_for_issue_bypasses_watermark(tmp_path, monkeypatch):
    """The agent-finish trigger must dispatch even when the watermark
    would normally cause an early-exit. Its sole job is the per-issue path."""
    target = tmp_path / "wm.json"
    target.write_text(
        json.dumps(
            {
                "lastScanAt": datetime.now(timezone.utc).isoformat(),
                "lastInReviewIds": [],
            }
        )
    )
    monkeypatch.setattr(mdr, "WATERMARK_FILE", target)
    monkeypatch.setattr(mdr, "MERGE_DISPATCH_IDEMPOTENT", True)

    issue = {
        "id": "iss-1",
        "identifier": "BTCAAAAA-1",
        "status": "in_review",
    }
    expected_result = {"issue": "BTCAAAAA-1", "action": "skip", "reason": "no_fix_sha"}

    with patch.object(mdr, "fetch_issue", return_value=issue), \
         patch.object(mdr, "fetch_issue_comments", return_value=[{"body": "Fix-SHA: " + "a" * 40}]), \
         patch.object(mdr, "process_issue", return_value=expected_result) as mock_proc, \
         patch.object(mdr, "load_watermark") as mock_load, \
         patch.object(mdr, "save_watermark") as mock_save:
        rc = mdr.dispatch_for_issue("iss-1")
    assert rc == 0
    mock_proc.assert_called_once_with(issue)
    mock_load.assert_not_called()
    mock_save.assert_not_called()


# --- main() wiring: telemetry + watermark integration ---


def test_main_returns_early_on_fresh_unchanged_watermark(
    tmp_path, monkeypatch, capsys
):
    target = tmp_path / "wm.json"
    target.write_text(
        json.dumps(
            {
                "lastScanAt": datetime.now(timezone.utc).isoformat(),
                "lastInReviewIds": ["i-1", "i-2"],
            }
        )
    )
    monkeypatch.setattr(mdr, "WATERMARK_FILE", target)
    monkeypatch.setattr(mdr, "MERGE_DISPATCH_IDEMPOTENT", True)
    monkeypatch.setattr(
        mdr, "find_in_review_issues", lambda: [{"id": "i-1"}, {"id": "i-2"}]
    )

    rc = mdr.main([])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["idempotency_skip"] is True
    assert out["would_work_count"] == 0


def test_main_full_run_saves_watermark(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(mdr, "WATERMARK_FILE", tmp_path / "wm.json")
    monkeypatch.setattr(mdr, "MERGE_DISPATCH_IDEMPOTENT", True)
    monkeypatch.setattr(
        mdr, "find_in_review_issues", lambda: [{"id": "i-1", "identifier": "X"}]
    )
    with patch.object(mdr, "process_issue", return_value={"issue": "X", "action": "skip", "reason": "no_fix_sha"}):
        rc = mdr.main([])
    assert rc == 0
    saved = json.loads((tmp_path / "wm.json").read_text())
    assert saved["lastInReviewIds"] == ["i-1"]


def test_main_emits_telemetry_even_on_early_exit(tmp_path, monkeypatch, capsys, caplog):
    target = tmp_path / "wm.json"
    target.write_text(
        json.dumps(
            {
                "lastScanAt": datetime.now(timezone.utc).isoformat(),
                "lastInReviewIds": ["i-1"],
            }
        )
    )
    monkeypatch.setattr(mdr, "WATERMARK_FILE", target)
    monkeypatch.setattr(mdr, "MERGE_DISPATCH_IDEMPOTENT", True)
    monkeypatch.setattr(mdr, "find_in_review_issues", lambda: [{"id": "i-1"}])

    with caplog.at_level("INFO", logger="merge_dispatch.telemetry"):
        mdr.main([])
    telemetry = [
        r for r in caplog.records if r.name == "merge_dispatch.telemetry"
    ]
    assert len(telemetry) == 1


def test_main_kill_switch_disables_gating(tmp_path, monkeypatch, capsys):
    """With MERGE_DISPATCH_IDEMPOTENT=false, a fresh/unchanged watermark
    must NOT short-circuit the run."""
    target = tmp_path / "wm.json"
    target.write_text(
        json.dumps(
            {
                "lastScanAt": datetime.now(timezone.utc).isoformat(),
                "lastInReviewIds": ["i-1"],
            }
        )
    )
    monkeypatch.setattr(mdr, "WATERMARK_FILE", target)
    monkeypatch.setattr(mdr, "MERGE_DISPATCH_IDEMPOTENT", False)
    monkeypatch.setattr(
        mdr, "find_in_review_issues", lambda: [{"id": "i-1", "identifier": "X"}]
    )
    with patch.object(mdr, "process_issue", return_value={"issue": "X", "action": "skip", "reason": "no_fix_sha"}):
        rc = mdr.main([])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out.get("idempotency_skip") is False
