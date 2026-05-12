"""Unit tests for scripts/validate_touch_index_bug.py validation checks.

All I/O is mocked so tests run offline.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))
sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

import importlib

runner_path = Path(__file__).parents[2] / "scripts" / "validate_touch_index_bug.py"
_spec = importlib.util.spec_from_file_location("validate_touch_index_bug", runner_path)
_runner = importlib.util.module_from_spec(_spec)
sys.modules["validate_touch_index_bug"] = _runner
_spec.loader.exec_module(_runner)
_run_checks = _runner._run_checks


def _make_bug_quality_report(passed: bool = True):
    """Return a mock BugQualityReport with the given passed status."""
    report = MagicMock()
    report.passed = passed
    return report


class TestValidateBug:
    def test_returns_zero_on_clean(self):
        with (
            patch("validate_touch_index_bug.get_engine") as mock_get_engine,
            patch("validate_touch_index_bug.health_check", return_value=True),
            patch(
                "validate_touch_index_bug.run_bug_quality_checks",
                return_value=_make_bug_quality_report(passed=True),
            ) as mock_quality,
        ):
            engine = MagicMock()
            mock_get_engine.return_value = engine
            result = _run_checks(stale_days=30)

        assert result == 0
        mock_quality.assert_called_once_with(engine, stale_threshold_days=30)

    def test_returns_nonzero_on_failure(self):
        with (
            patch("validate_touch_index_bug.get_engine") as mock_get_engine,
            patch("validate_touch_index_bug.health_check", return_value=True),
            patch(
                "validate_touch_index_bug.run_bug_quality_checks",
                return_value=_make_bug_quality_report(passed=False),
            ) as mock_quality,
        ):
            engine = MagicMock()
            mock_get_engine.return_value = engine
            result = _run_checks(stale_days=30)

        assert result == 1
        mock_quality.assert_called_once()

    def test_stale_days_passed_to_quality(self):
        with (
            patch("validate_touch_index_bug.get_engine") as mock_get_engine,
            patch("validate_touch_index_bug.health_check", return_value=True),
            patch(
                "validate_touch_index_bug.run_bug_quality_checks",
                return_value=_make_bug_quality_report(passed=True),
            ) as mock_quality,
        ):
            engine = MagicMock()
            mock_get_engine.return_value = engine
            _run_checks(stale_days=7)

        mock_quality.assert_called_once_with(engine, stale_threshold_days=7)

    def test_health_check_failure_exits(self):
        with (
            patch("validate_touch_index_bug.get_engine"),
            patch("validate_touch_index_bug.health_check", return_value=False),
        ):
            with pytest.raises(SystemExit) as exc:
                _run_checks(stale_days=30)
        assert exc.value.code == 1

    def test_accepts_pre_configured_engine(self):
        """When an engine is passed directly, it is used instead of creating a new one."""
        engine = MagicMock()
        with (
            patch("validate_touch_index_bug.get_engine") as mock_get_engine,
            patch("validate_touch_index_bug.health_check") as mock_health,
            patch(
                "validate_touch_index_bug.run_bug_quality_checks",
                return_value=_make_bug_quality_report(passed=True),
            ) as mock_quality,
        ):
            result = _run_checks(stale_days=30, engine=engine)

        assert result == 0
        mock_get_engine.assert_not_called()
        mock_health.assert_not_called()
        mock_quality.assert_called_once_with(engine, stale_threshold_days=30)

    def test_main_exits_nonzero_on_failures(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["validate_touch_index_bug.py"])
        with (
            patch("validate_touch_index_bug.get_engine") as mock_get_engine,
            patch("validate_touch_index_bug.health_check", return_value=True),
            patch(
                "validate_touch_index_bug.run_bug_quality_checks",
                return_value=_make_bug_quality_report(passed=False),
            ),
        ):
            engine = MagicMock()
            mock_get_engine.return_value = engine
            with pytest.raises(SystemExit) as exc:
                from validate_touch_index_bug import main

                main()
        assert exc.value.code == 1

    def test_main_exits_zero_on_clean(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["validate_touch_index_bug.py"])
        with (
            patch("validate_touch_index_bug.get_engine") as mock_get_engine,
            patch("validate_touch_index_bug.health_check", return_value=True),
            patch(
                "validate_touch_index_bug.run_bug_quality_checks",
                return_value=_make_bug_quality_report(passed=True),
            ),
        ):
            engine = MagicMock()
            mock_get_engine.return_value = engine
            from validate_touch_index_bug import main

            main()
        assert True
