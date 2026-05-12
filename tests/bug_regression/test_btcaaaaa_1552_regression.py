"""
Regression tests for BTCAAAAA-1552: opencode watchdog 3-layer ghost detection.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1552
Fixed in commits: f5a7b17, 6a3dcfd
Component: scripts/opencode_watchdog.py

Root cause: the original watchdog had a single detection layer (CPU > 1.0%
threshold), allowing ghost processes that consumed CPU but produced no output
for extended periods to escape detection. Additionally, the dry-run counting
path always reported 0 kills.

This file tests the three-layer ghost detection added in the fix:
  1. Low-CPU ghost: kill at >30min with cpu <= 0.5%
  2. Output-inactive ghost: kill at >30min when stdout/stderr unwritten for 10min
  3. Absolute max-age: unconditional kill at 60min regardless of CPU or output
"""
from __future__ import annotations

import time

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1552"),
    pytest.mark.regression,
]

from scripts.opencode_watchdog import (
    DEFAULT_MAX_ABSOLUTE_AGE_SEC,
    DEFAULT_SILENT_THRESHOLD_SEC,
    KILLABLE_REASONS,
    OUTPUT_INACTIVE_WINDOW_SEC,
    OpenCodeProcess,
    classify_process,
    parse_elapsed,
)


class TestParseElapsed:
    """parse_elapsed: MM:SS and HH:MM:SS format parsing."""
    def test_parses_mm_ss(self) -> None:
        assert parse_elapsed("05:30") == 330.0
    def test_parses_hh_mm_ss(self) -> None:
        assert parse_elapsed("01:15:45") == 4545.0
    def test_zero_elapsed(self) -> None:
        assert parse_elapsed("00:00") == 0.0
    def test_single_digit_minutes(self) -> None:
        assert parse_elapsed("9:59") == 599.0
    def test_large_hours(self) -> None:
        assert parse_elapsed("48:00:00") == 172800.0
    def test_malformed_returns_zero(self) -> None:
        assert parse_elapsed("not-a-time") == 0.0


class TestClassifyProcess:
    """classify_process: all six classification paths."""
    def test_absolute_max_age_killable(self) -> None:
        proc = OpenCodeProcess(
            pid=1001, ppid=1, elapsed_seconds=7200, cpu_percent=50.0, cmdline="opencode run",
        )
        reason, meta = classify_process(proc, silent_threshold_sec=1800, max_absolute_age_sec=3600)
        assert reason == "absolute-max-age"
        assert meta["cpu"] == 50.0

    def test_low_cpu_ghost_detected(self) -> None:
        proc = OpenCodeProcess(
            pid=1002, ppid=1, elapsed_seconds=2400, cpu_percent=0.3, cmdline="opencode run",
        )
        reason, meta = classify_process(proc, silent_threshold_sec=1800, max_absolute_age_sec=7200)
        assert reason == "low-cpu"
        assert meta["cpu"] == 0.3

    def test_output_inactive_ghost_detected(self, monkeypatch) -> None:
        monkeypatch.setattr("scripts.opencode_watchdog._get_process_state", lambda _pid: None)
        monkeypatch.setattr("scripts.opencode_watchdog._get_output_inactive_since", lambda _pid: 700.0)
        proc = OpenCodeProcess(
            pid=1003, ppid=1, elapsed_seconds=2400, cpu_percent=50.0, cmdline="opencode run",
        )
        reason, meta = classify_process(proc, silent_threshold_sec=1800, max_absolute_age_sec=7200)
        assert reason == "output-inactive"
        assert meta["cpu"] == 50.0

    def test_zombie_detected(self, monkeypatch) -> None:
        monkeypatch.setattr("scripts.opencode_watchdog._get_process_state", lambda _pid: "Z (zombie)")
        proc = OpenCodeProcess(
            pid=1004, ppid=1, elapsed_seconds=2400, cpu_percent=0.0, cmdline="opencode run",
        )
        reason, meta = classify_process(proc, silent_threshold_sec=1800, max_absolute_age_sec=7200)
        assert reason == "zombie"
        assert "Z" in meta["state"]

    def test_too_young_not_killable(self) -> None:
        proc = OpenCodeProcess(
            pid=1005, ppid=1, elapsed_seconds=300, cpu_percent=0.3, cmdline="opencode run",
        )
        reason, _ = classify_process(proc, silent_threshold_sec=1800, max_absolute_age_sec=7200)
        assert reason == "too-young"

    def test_active_not_killable(self, monkeypatch) -> None:
        monkeypatch.setattr("scripts.opencode_watchdog._get_process_state", lambda _pid: None)
        monkeypatch.setattr("scripts.opencode_watchdog._get_output_inactive_since", lambda _pid: 0.1)
        proc = OpenCodeProcess(
            pid=1006, ppid=1, elapsed_seconds=2400, cpu_percent=50.0, cmdline="opencode run",
        )
        reason, _ = classify_process(proc, silent_threshold_sec=1800, max_absolute_age_sec=7200)
        assert reason == "active"


class TestKillableReasons:
    """KILLABLE_REASONS frozenset correctness."""
    def test_contains_absolute_max_age(self) -> None:
        assert "absolute-max-age" in KILLABLE_REASONS
    def test_contains_low_cpu(self) -> None:
        assert "low-cpu" in KILLABLE_REASONS
    def test_contains_output_inactive(self) -> None:
        assert "output-inactive" in KILLABLE_REASONS
    def test_excludes_zombie(self) -> None:
        assert "zombie" not in KILLABLE_REASONS
    def test_excludes_too_young(self) -> None:
        assert "too-young" not in KILLABLE_REASONS
    def test_excludes_active(self) -> None:
        assert "active" not in KILLABLE_REASONS
    def test_frozenset_immutable(self) -> None:
        with pytest.raises(AttributeError):
            KILLABLE_REASONS.add("zombie")
    def test_exact_membership(self) -> None:
        assert KILLABLE_REASONS == {"low-cpu", "output-inactive", "absolute-max-age"}


class TestClassifyProcessEdgeCases:
    """Edge cases for classify_process."""
    def test_elapsed_equal_silent_threshold_not_too_young(self, monkeypatch) -> None:
        monkeypatch.setattr("scripts.opencode_watchdog._get_process_state", lambda _pid: None)
        proc = OpenCodeProcess(
            pid=1007, ppid=1, elapsed_seconds=1800, cpu_percent=0.5, cmdline="opencode run",
        )
        reason, _ = classify_process(proc, silent_threshold_sec=1800, max_absolute_age_sec=7200)
        assert reason != "too-young"

    def test_exactly_at_max_age_is_killable(self) -> None:
        proc = OpenCodeProcess(
            pid=1009, ppid=1, elapsed_seconds=3600, cpu_percent=0.0, cmdline="opencode run",
        )
        reason, _ = classify_process(proc, silent_threshold_sec=1800, max_absolute_age_sec=3600)
        assert reason == "absolute-max-age"


class TestOpenCodeProcessDataclass:
    """OpenCodeProcess dataclass construction."""
    def test_minimal_creation(self) -> None:
        proc = OpenCodeProcess(pid=1, ppid=0, elapsed_seconds=0.0, cpu_percent=0.0, cmdline="")
        assert proc.session_id is None
        assert proc.model is None

    def test_full_creation(self) -> None:
        proc = OpenCodeProcess(
            pid=1, ppid=0, elapsed_seconds=100.0, cpu_percent=5.0, cmdline="opencode run",
            session_id="ses-abc", model="gpt-4",
        )
        assert proc.session_id == "ses-abc"
        assert proc.model == "gpt-4"


class TestConstants:
    """Watchdog constants sanity checks."""
    def test_silent_threshold_default(self) -> None:
        assert DEFAULT_SILENT_THRESHOLD_SEC == 1800
    def test_max_absolute_age_default(self) -> None:
        assert DEFAULT_MAX_ABSOLUTE_AGE_SEC == 3600
    def test_output_inactive_window(self) -> None:
        assert OUTPUT_INACTIVE_WINDOW_SEC == 600
    def test_max_age_greater_than_silent_threshold(self) -> None:
        assert DEFAULT_MAX_ABSOLUTE_AGE_SEC > DEFAULT_SILENT_THRESHOLD_SEC
