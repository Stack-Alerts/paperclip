"""Tests for Impact Gate monitoring event-gate (Stage 2) — BTCAAAAA-38266.

Mirrors the merge-dispatch event-gate pattern (BTCAAAAA-38258) so the
5-minute periodic sweep does no work when the ungated-issues set is
unchanged AND the safety floor has not elapsed. Behavior is controlled
by the IMPACT_GATE_MONITORING_IDEMPOTENT env var (default: true) so
the team can roll back without code change.

These tests cover:
  - watermark load/save round-trip
  - safety floor (5h default) blocks re-scan
  - watermark set-inequality forces a full run
  - kill-switch env var disables gating
  - telemetry log line is emitted on every run
  - main() wiring: telemetry + watermark integration + kill-switch
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import impact_gate_monitoring_routine as igmr  # noqa: E402


# --- Watermark load/save round-trip ---


def test_load_watermark_returns_none_when_file_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(igmr, "WATERMARK_FILE", tmp_path / "no-such-watermark.json")
    assert igmr.load_watermark() is None


def test_load_watermark_returns_dict_when_present(tmp_path, monkeypatch):
    monkeypatch.setattr(igmr, "WATERMARK_FILE", tmp_path / "wm.json")
    payload = {
        "lastScanAt": datetime.now(timezone.utc).isoformat(),
        "lastUngatedIssueIds": ["id-a", "id-b"],
    }
    igmr.WATERMARK_FILE.write_text(json.dumps(payload))
    out = igmr.load_watermark()
    assert out == payload


def test_load_watermark_handles_corrupt_file(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(igmr, "WATERMARK_FILE", tmp_path / "wm.json")
    igmr.WATERMARK_FILE.write_text("{not valid json")
    with caplog.at_level("WARNING"):
        out = igmr.load_watermark()
    assert out is None


def test_save_watermark_creates_file_and_dirs(tmp_path, monkeypatch):
    target = tmp_path / "subdir" / "wm.json"
    monkeypatch.setattr(igmr, "WATERMARK_FILE", target)
    ok = igmr.save_watermark(
        ungated_ids=["id-a", "id-b"],
        routine_origin_id="orig",
        issue_id="iss",
    )
    assert ok is True
    assert target.exists()
    payload = json.loads(target.read_text())
    assert sorted(payload["lastUngatedIssueIds"]) == ["id-a", "id-b"]
    assert payload["routineOriginId"] == "orig"
    assert payload["issueId"] == "iss"
    assert "lastScanAt" in payload


def test_save_watermark_sorts_and_dedupes(tmp_path, monkeypatch):
    target = tmp_path / "wm.json"
    monkeypatch.setattr(igmr, "WATERMARK_FILE", target)
    igmr.save_watermark(ungated_ids=["b", "a", "a", ""], routine_origin_id="")
    payload = json.loads(target.read_text())
    assert payload["lastUngatedIssueIds"] == ["a", "b"]


# --- Safety floor & set comparison ---


def test_check_early_exit_returns_false_when_kill_switch_off(monkeypatch):
    monkeypatch.setattr(igmr, "IMPACT_GATE_MONITORING_IDEMPOTENT", False)
    assert igmr.check_early_exit(current_ungated_ids=["x"], watermark={}) is False


def test_check_early_exit_returns_false_when_no_watermark(tmp_path, monkeypatch):
    monkeypatch.setattr(igmr, "WATERMARK_FILE", tmp_path / "missing.json")
    monkeypatch.setattr(igmr, "IMPACT_GATE_MONITORING_IDEMPOTENT", True)
    assert igmr.check_early_exit(current_ungated_ids=["x"]) is False


def test_check_early_exit_returns_false_when_watermark_stale(
    tmp_path, monkeypatch
):
    target = tmp_path / "wm.json"
    monkeypatch.setattr(igmr, "WATERMARK_FILE", target)
    monkeypatch.setattr(igmr, "IMPACT_GATE_MONITORING_IDEMPOTENT", True)
    # 6 hours stale — past the 5h safety floor
    stale = (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat()
    target.write_text(
        json.dumps(
            {
                "lastScanAt": stale,
                "lastUngatedIssueIds": ["x"],
            }
        )
    )
    assert igmr.check_early_exit(current_ungated_ids=["x"]) is False


def test_check_early_exit_returns_true_when_fresh_and_unchanged(
    tmp_path, monkeypatch
):
    target = tmp_path / "wm.json"
    monkeypatch.setattr(igmr, "WATERMARK_FILE", target)
    monkeypatch.setattr(igmr, "IMPACT_GATE_MONITORING_IDEMPOTENT", True)
    # Recent (1h ago, well under 5h floor)
    target.write_text(
        json.dumps(
            {
                "lastScanAt": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
                "lastUngatedIssueIds": ["x", "y"],
            }
        )
    )
    assert igmr.check_early_exit(current_ungated_ids=["y", "x"]) is True


def test_check_early_exit_returns_false_when_set_differs(
    tmp_path, monkeypatch
):
    target = tmp_path / "wm.json"
    monkeypatch.setattr(igmr, "WATERMARK_FILE", target)
    monkeypatch.setattr(igmr, "IMPACT_GATE_MONITORING_IDEMPOTENT", True)
    target.write_text(
        json.dumps(
            {
                "lastScanAt": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
                "lastUngatedIssueIds": ["x"],
            }
        )
    )
    # New issue appeared in ungated set — must re-scan
    assert igmr.check_early_exit(current_ungated_ids=["x", "y"]) is False


def test_check_early_exit_handles_unparseable_timestamp(
    tmp_path, monkeypatch
):
    target = tmp_path / "wm.json"
    monkeypatch.setattr(igmr, "WATERMARK_FILE", target)
    monkeypatch.setattr(igmr, "IMPACT_GATE_MONITORING_IDEMPOTENT", True)
    target.write_text(
        json.dumps({"lastScanAt": "not-a-date", "lastUngatedIssueIds": ["x"]})
    )
    assert igmr.check_early_exit(current_ungated_ids=["x"]) is False


# --- Safety floor constant default is 5h ---


def test_safety_floor_default_is_five_hours(monkeypatch):
    monkeypatch.delenv("IMPACT_GATE_MONITORING_SAFETY_FLOOR_MINUTES", raising=False)
    # Re-import to pick up env
    import importlib
    importlib.reload(igmr)
    assert igmr.IMPACT_GATE_MONITORING_SAFETY_FLOOR_MINUTES == 300
    # Restore for downstream tests
    importlib.reload(igmr)


# --- Telemetry log line ---


def test_emit_telemetry_log_includes_required_fields(caplog):
    caplog.set_level("INFO", logger="impact_gate_monitoring.telemetry")
    igmr.emit_telemetry_log(
        fired_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        idempotency_skip=True,
        would_work_count=0,
        child_created=0,
    )
    record = next(
        r for r in caplog.records if r.name == "impact_gate_monitoring.telemetry"
    )
    payload = json.loads(record.getMessage())
    assert payload["routine"] == "impact_gate_monitoring"
    assert payload["idempotency_skip"] is True
    assert payload["would_work_count"] == 0
    assert payload["child_created"] == 0
    assert "fired_at" in payload


# --- main() wiring: telemetry + watermark integration ---


def test_main_returns_early_on_fresh_unchanged_watermark(
    tmp_path, monkeypatch, capsys
):
    target = tmp_path / "wm.json"
    target.write_text(
        json.dumps(
            {
                "lastScanAt": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
                "lastUngatedIssueIds": ["i-1", "i-2"],
            }
        )
    )
    monkeypatch.setattr(igmr, "WATERMARK_FILE", target)
    monkeypatch.setattr(igmr, "IMPACT_GATE_MONITORING_IDEMPOTENT", True)
    monkeypatch.setattr(
        igmr, "_scan_for_ungated", lambda: ["i-1", "i-2"]
    )

    rc = igmr.main([])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["idempotency_skip"] is True
    assert out["would_work_count"] == 0
    assert out["child_created"] == 0


def test_main_full_run_saves_watermark(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(igmr, "WATERMARK_FILE", tmp_path / "wm.json")
    monkeypatch.setattr(igmr, "IMPACT_GATE_MONITORING_IDEMPOTENT", True)
    monkeypatch.setattr(
        igmr, "_scan_for_ungated", lambda: ["i-1"]
    )
    monkeypatch.setattr(igmr, "_post_tracking_comment", lambda *a, **kw: True)
    monkeypatch.setattr(igmr, "_TRACKING_ISSUE_ID", "iss-tracking")

    rc = igmr.main([])
    assert rc == 0
    saved = json.loads((tmp_path / "wm.json").read_text())
    assert saved["lastUngatedIssueIds"] == ["i-1"]


def test_main_emits_telemetry_even_on_early_exit(tmp_path, monkeypatch, capsys, caplog):
    target = tmp_path / "wm.json"
    target.write_text(
        json.dumps(
            {
                "lastScanAt": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
                "lastUngatedIssueIds": ["i-1"],
            }
        )
    )
    monkeypatch.setattr(igmr, "WATERMARK_FILE", target)
    monkeypatch.setattr(igmr, "IMPACT_GATE_MONITORING_IDEMPOTENT", True)
    monkeypatch.setattr(igmr, "_scan_for_ungated", lambda: ["i-1"])

    with caplog.at_level("INFO", logger="impact_gate_monitoring.telemetry"):
        igmr.main([])
    telemetry = [
        r for r in caplog.records if r.name == "impact_gate_monitoring.telemetry"
    ]
    assert len(telemetry) == 1


def test_main_kill_switch_disables_gating(tmp_path, monkeypatch, capsys):
    """With IMPACT_GATE_MONITORING_IDEMPOTENT=false, a fresh/unchanged
    watermark must NOT short-circuit the run."""
    target = tmp_path / "wm.json"
    target.write_text(
        json.dumps(
            {
                "lastScanAt": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
                "lastUngatedIssueIds": ["i-1"],
            }
        )
    )
    monkeypatch.setattr(igmr, "WATERMARK_FILE", target)
    monkeypatch.setattr(igmr, "IMPACT_GATE_MONITORING_IDEMPOTENT", False)
    monkeypatch.setattr(
        igmr, "_scan_for_ungated", lambda: ["i-1"]
    )
    monkeypatch.setattr(igmr, "_post_tracking_comment", lambda *a, **kw: True)
    monkeypatch.setattr(igmr, "_TRACKING_ISSUE_ID", "iss-tracking")

    rc = igmr.main([])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out.get("idempotency_skip") is False


def test_main_stale_watermark_forces_full_run(tmp_path, monkeypatch, capsys):
    """Safety floor: even if the set is unchanged, a stale watermark (>5h)
    must force a full run."""
    target = tmp_path / "wm.json"
    target.write_text(
        json.dumps(
            {
                "lastScanAt": (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat(),
                "lastUngatedIssueIds": ["i-1"],
            }
        )
    )
    monkeypatch.setattr(igmr, "WATERMARK_FILE", target)
    monkeypatch.setattr(igmr, "IMPACT_GATE_MONITORING_IDEMPOTENT", True)
    monkeypatch.setattr(
        igmr, "_scan_for_ungated", lambda: ["i-1"]
    )
    monkeypatch.setattr(igmr, "_post_tracking_comment", lambda *a, **kw: True)
    monkeypatch.setattr(igmr, "_TRACKING_ISSUE_ID", "iss-tracking")

    rc = igmr.main([])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out.get("idempotency_skip") is False
    # Watermark should have been refreshed
    saved = json.loads(target.read_text())
    assert saved["lastUngatedIssueIds"] == ["i-1"]
