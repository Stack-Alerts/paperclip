"""Tests for scripts/validate_data_quality.py — REQ-DATA-002.

All external I/O (UnifiedDataManager, parquet files) is mocked or uses tmp_path.
No live network or real filesystem state is accessed.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import numpy as np
import pytest

from scripts.validate_data_quality import (
    _expected_bars,
    check_gaps,
    check_completeness,
    check_recency,
    run_validation,
    main,
    TIMEFRAMES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_bar_df(n: int, start: datetime, freq_minutes: int = 15) -> pd.DataFrame:
    timestamps = [start + timedelta(minutes=freq_minutes * i) for i in range(n)]
    return pd.DataFrame({
        "timestamp": pd.to_datetime(timestamps, utc=True),
        "open": np.full(n, 30000.0),
        "high": np.full(n, 30100.0),
        "low": np.full(n, 29900.0),
        "close": np.full(n, 30050.0),
        "volume": np.full(n, 10.0),
    })


def _write_month_file(base_dir: Path, tf: str, year: int, month: int,
                       n_bars: int, start: datetime | None = None) -> Path:
    month_str = f"{year:04d}-{month:02d}"
    freq = {"15m": 15, "1h": 60, "1d": 2880}[tf]
    if start is None:
        start = datetime(year, month, 1, tzinfo=timezone.utc)
    df = _make_bar_df(n_bars, start, freq_minutes=freq)
    file_path = base_dir / month_str / f"BTCUSDT_PERP_{tf}_{month_str}.parquet"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(file_path, compression="snappy", index=False)
    return file_path


def _write_recent_file(base_dir: Path, tf: str, n_bars: int | None = None) -> Path:
    now = datetime.now(timezone.utc)
    if n_bars is None:
        max_expected = (now.day - 1) * (96 if tf == "15m" else 24 if tf == "1h" else 1)
        max_expected += (now.hour * 60 + now.minute) // {"15m": 15, "1h": 60, "1d": 2880}[tf]
        n_bars = max(int(max_expected * 0.95) + 1, 10)
    start = now - timedelta(hours=2)
    return _write_month_file(base_dir, tf, now.year, now.month, n_bars, start=start)


# ---------------------------------------------------------------------------
# _expected_bars
# ---------------------------------------------------------------------------

class TestExpectedBars:
    def test_15m_january(self):
        assert _expected_bars("15m", 2026, 1) == 31 * 96

    def test_1h_february_non_leap(self):
        assert _expected_bars("1h", 2025, 2) == 28 * 24

    def test_1d_march(self):
        assert _expected_bars("1d", 2026, 3) == 31

    def test_1h_february_leap(self):
        assert _expected_bars("1h", 2024, 2) == 29 * 24

    def test_unknown_tf_returns_zero(self):
        assert _expected_bars("1w", 2026, 1) == 0


# ---------------------------------------------------------------------------
# check_gaps
# ---------------------------------------------------------------------------

class TestCheckGaps:
    def test_no_gaps(self):
        manager = MagicMock()
        manager.detect_gaps_in_binance_files.return_value = []
        result = check_gaps(manager, ["15m", "1h", "1d"])
        for tf in ["15m", "1h", "1d"]:
            assert result[tf]["gaps_found"] == 0
            assert result[tf]["total_missing_bars"] == 0

    def test_gaps_detected(self):
        manager = MagicMock()
        manager.detect_gaps_in_binance_files.return_value = [
            {
                "gap_start": pd.Timestamp("2026-05-01 12:00", tz="UTC"),
                "gap_end": pd.Timestamp("2026-05-01 13:00", tz="UTC"),
                "missing_bars": 4,
                "duration": timedelta(hours=1),
            }
        ]
        result = check_gaps(manager, ["15m"])
        assert result["15m"]["gaps_found"] == 1
        assert result["15m"]["total_missing_bars"] == 4
        assert len(result["15m"]["gaps"]) == 1

    def test_calls_manager_with_correct_args(self):
        manager = MagicMock()
        manager.detect_gaps_in_binance_files.return_value = []
        check_gaps(manager, ["1h"])
        call_args = manager.detect_gaps_in_binance_files.call_args
        assert call_args[0][0] == "1h"
        assert call_args[1]["start_date"] is not None


# ---------------------------------------------------------------------------
# check_completeness
# ---------------------------------------------------------------------------

class TestCheckCompleteness:
    def test_no_files_returns_empty(self, tmp_path):
        result = check_completeness(tmp_path, ["15m"])
        assert result == {"15m": {}}

    def test_complete_month_passes(self, tmp_path):
        _write_month_file(tmp_path, "15m", 2026, 1, 31 * 96)
        result = check_completeness(tmp_path, ["15m"])
        file_key = list(result["15m"].keys())[0]
        assert result["15m"][file_key]["pass"] is True
        assert result["15m"][file_key]["actual_bars"] == 31 * 96

    def test_incomplete_month_fails(self, tmp_path):
        _write_month_file(tmp_path, "15m", 2025, 6, 100)
        result = check_completeness(tmp_path, ["15m"])
        file_key = list(result["15m"].keys())[0]
        assert result["15m"][file_key]["pass"] is False
        assert result["15m"][file_key]["missing_bars"] > 0

    def test_corrupt_file_reports_error(self, tmp_path):
        bad_file = tmp_path / "2026-01" / "BTCUSDT_PERP_15m_2026-01.parquet"
        bad_file.parent.mkdir(parents=True, exist_ok=True)
        bad_file.write_bytes(b"not a parquet file")
        result = check_completeness(tmp_path, ["15m"])
        file_key = list(result["15m"].keys())[0]
        assert result["15m"][file_key]["pass"] is False
        assert "error" in result["15m"][file_key]

    def test_current_month_uses_relaxed_threshold(self, tmp_path):
        now = datetime.now(timezone.utc)
        expected_full = _expected_bars("1h", now.year, now.month)
        half_bars = max(expected_full // 2, 1)
        _write_month_file(tmp_path, "1h", now.year, now.month, half_bars)
        result = check_completeness(tmp_path, ["1h"])
        file_key = list(result["1h"].keys())[0]
        assert result["1h"][file_key]["is_current_month"] is True

    def test_all_timeframes(self, tmp_path):
        for tf in ["15m", "1h", "1d"]:
            _write_month_file(tmp_path, tf, 2026, 1, _expected_bars(tf, 2026, 1))
        result = check_completeness(tmp_path, ["15m", "1h", "1d"])
        assert len(result) == 3
        for tf in ["15m", "1h", "1d"]:
            file_key = list(result[tf].keys())[0]
            assert result[tf][file_key]["pass"] is True


# ---------------------------------------------------------------------------
# check_recency
# ---------------------------------------------------------------------------

class TestCheckRecency:
    def test_no_files_fails(self, tmp_path):
        result = check_recency(tmp_path, ["15m"])
        assert result["15m"]["pass"] is False
        assert "error" in result["15m"]

    def test_fresh_data_passes(self, tmp_path):
        _write_recent_file(tmp_path, "15m")
        result = check_recency(tmp_path, ["15m"])
        assert result["15m"]["pass"] is True
        assert result["15m"]["age_minutes"] <= 30

    def test_stale_data_fails(self, tmp_path):
        old = datetime(2025, 1, 1, tzinfo=timezone.utc)
        _write_month_file(tmp_path, "15m", 2025, 1, 10, start=old)
        result = check_recency(tmp_path, ["15m"])
        assert result["15m"]["pass"] is False

    def test_empty_parquet_fails(self, tmp_path):
        month_str = "2026-01"
        f = tmp_path / month_str / "BTCUSDT_PERP_15m_2026-01.parquet"
        f.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({"timestamp": []}).to_parquet(f)
        result = check_recency(tmp_path, ["15m"])
        assert result["15m"]["pass"] is False

    def test_corrupt_file_fails(self, tmp_path):
        bad_file = tmp_path / "2026-01" / "BTCUSDT_PERP_15m_2026-01.parquet"
        bad_file.parent.mkdir(parents=True, exist_ok=True)
        bad_file.write_bytes(b"garbage")
        result = check_recency(tmp_path, ["15m"])
        assert result["15m"]["pass"] is False
        assert "error" in result["15m"]


# ---------------------------------------------------------------------------
# run_validation
# ---------------------------------------------------------------------------

class TestRunValidation:
    def test_all_pass(self, tmp_path):
        manager = MagicMock()
        manager.detect_gaps_in_binance_files.return_value = []
        for tf in ["15m", "1h", "1d"]:
            _write_month_file(tmp_path, tf, 2026, 1, _expected_bars(tf, 2026, 1))
            _write_recent_file(tmp_path, tf)
        report = run_validation(manager, tmp_path, ["15m", "1h", "1d"])
        assert report["pass"] is True
        assert len(report["failures"]) == 0

    def test_gaps_cause_failure(self, tmp_path):
        manager = MagicMock()
        manager.detect_gaps_in_binance_files.return_value = [
            {"gap_start": pd.Timestamp("2026-05-01", tz="UTC"),
             "gap_end": pd.Timestamp("2026-05-02", tz="UTC"),
             "missing_bars": 96, "duration": timedelta(days=1)}
        ]
        _write_recent_file(tmp_path, "15m")
        report = run_validation(manager, tmp_path, ["15m"])
        assert report["pass"] is False
        assert any("gap" in f.lower() for f in report["failures"])

    def test_completeness_failure(self, tmp_path):
        manager = MagicMock()
        manager.detect_gaps_in_binance_files.return_value = []
        _write_month_file(tmp_path, "15m", 2025, 6, 10)
        _write_recent_file(tmp_path, "15m")
        report = run_validation(manager, tmp_path, ["15m"])
        assert report["pass"] is False
        assert any("bar" in f.lower() for f in report["failures"])

    def test_recency_failure(self, tmp_path):
        manager = MagicMock()
        manager.detect_gaps_in_binance_files.return_value = []
        _write_month_file(tmp_path, "15m", 2025, 1, _expected_bars("15m", 2025, 1))
        report = run_validation(manager, tmp_path, ["15m"])
        assert report["pass"] is False
        assert any("last bar" in f for f in report["failures"])

    def test_report_shape(self, tmp_path):
        manager = MagicMock()
        manager.detect_gaps_in_binance_files.return_value = []
        _write_recent_file(tmp_path, "15m")
        report = run_validation(manager, tmp_path, ["15m"])
        assert "timestamp" in report
        assert "duration_seconds" in report
        assert "pass" in report
        assert "failures" in report
        assert "gaps" in report
        assert "completeness" in report
        assert "recency" in report


# ---------------------------------------------------------------------------
# main() — CLI entry point
# ---------------------------------------------------------------------------

class TestMain:
    @pytest.fixture()
    def data_dir(self, tmp_path):
        return tmp_path / "data" / "binance"

    def test_pass_exit_code_zero(self, tmp_path, monkeypatch):
        manager = MagicMock()
        manager.detect_gaps_in_binance_files.return_value = []
        data_dir = tmp_path / "data" / "binance"
        data_dir.mkdir(parents=True, exist_ok=True)
        for tf in ["15m", "1h", "1d"]:
            _write_month_file(data_dir, tf, 2026, 1, _expected_bars(tf, 2026, 1))
            _write_recent_file(data_dir, tf)
        monkeypatch.setattr("scripts.validate_data_quality.PROJECT_ROOT", tmp_path)
        monkeypatch.setattr("scripts.validate_data_quality.UnifiedDataManager",
                            lambda **kw: manager)
        monkeypatch.setattr("sys.argv", ["validate_data_quality.py", "--json"])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    def test_fail_exit_code_one(self, tmp_path, monkeypatch):
        manager = MagicMock()
        manager.detect_gaps_in_binance_files.return_value = [
            {"gap_start": pd.Timestamp("2026-05-01", tz="UTC"),
             "gap_end": pd.Timestamp("2026-05-02", tz="UTC"),
             "missing_bars": 96, "duration": timedelta(days=1)}
        ]
        data_dir = tmp_path / "data" / "binance"
        data_dir.mkdir(parents=True, exist_ok=True)
        _write_recent_file(data_dir, "15m")
        monkeypatch.setattr("scripts.validate_data_quality.PROJECT_ROOT", tmp_path)
        monkeypatch.setattr("scripts.validate_data_quality.UnifiedDataManager",
                            lambda **kw: manager)
        monkeypatch.setattr("sys.argv", ["validate_data_quality.py", "--json"])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1

    def test_json_output_format(self, tmp_path, monkeypatch, capsys):
        manager = MagicMock()
        manager.detect_gaps_in_binance_files.return_value = []
        data_dir = tmp_path / "data" / "binance"
        data_dir.mkdir(parents=True, exist_ok=True)
        for tf in ["15m", "1h", "1d"]:
            _write_recent_file(data_dir, tf)
        monkeypatch.setattr("scripts.validate_data_quality.PROJECT_ROOT", tmp_path)
        monkeypatch.setattr("scripts.validate_data_quality.UnifiedDataManager",
                            lambda **kw: manager)
        monkeypatch.setattr("sys.argv", ["validate_data_quality.py", "--json"])
        with pytest.raises(SystemExit):
            main()
        captured = capsys.readouterr()
        report = json.loads(captured.out)
        assert "pass" in report
        assert "gaps" in report
        assert "completeness" in report
        assert "recency" in report

    def test_sla_mode_uses_two_timeframes(self, tmp_path, monkeypatch):
        manager = MagicMock()
        manager.detect_gaps_in_binance_files.return_value = []
        data_dir = tmp_path / "data" / "binance"
        data_dir.mkdir(parents=True, exist_ok=True)
        for tf in ["15m", "1h"]:
            _write_recent_file(data_dir, tf)
        monkeypatch.setattr("scripts.validate_data_quality.PROJECT_ROOT", tmp_path)
        monkeypatch.setattr("scripts.validate_data_quality.UnifiedDataManager",
                            lambda **kw: manager)
        monkeypatch.setattr("sys.argv",
                            ["validate_data_quality.py", "--sla", "--json"])
        with pytest.raises(SystemExit):
            main()

    def test_default_human_output(self, tmp_path, monkeypatch, capsys):
        manager = MagicMock()
        manager.detect_gaps_in_binance_files.return_value = []
        data_dir = tmp_path / "data" / "binance"
        data_dir.mkdir(parents=True, exist_ok=True)
        for tf in ["15m", "1h", "1d"]:
            _write_recent_file(data_dir, tf)
        monkeypatch.setattr("scripts.validate_data_quality.PROJECT_ROOT", tmp_path)
        monkeypatch.setattr("scripts.validate_data_quality.UnifiedDataManager",
                            lambda **kw: manager)
        monkeypatch.setattr("sys.argv", ["validate_data_quality.py"])
        with pytest.raises(SystemExit):
            main()
        captured = capsys.readouterr()
        assert "PASS" in captured.out or "FAIL" in captured.out
        assert "Data Quality Validation" in captured.out
