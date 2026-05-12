"""Unit tests for scripts/validate_touch_index_bug.py validation checks.

All DB I/O is mocked so tests run offline.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))
sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

import importlib

runner_path = Path(__file__).parents[2] / "scripts" / "validate_touch_index_bug.py"
_spec = importlib.util.spec_from_file_location(
    "validate_touch_index_bug", runner_path
)
_runner = importlib.util.module_from_spec(_spec)
sys.modules["validate_touch_index_bug"] = _runner
_spec.loader.exec_module(_runner)
_run_checks = _runner._run_checks


def _mock_engine(scalars: dict | None = None):
    conn = MagicMock()
    execute = MagicMock()
    scalar_result = MagicMock()
    scalar_result.scalar = MagicMock(side_effect=lambda: scalars or 0)
    execute.return_value = scalar_result
    conn.execute = execute
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=conn)
    ctx.__exit__ = MagicMock(return_value=False)
    engine = MagicMock()
    engine.connect = MagicMock(return_value=ctx)
    return engine


class TestValidateBug:
    def test_returns_zero_on_clean(self):
        engine = _mock_engine()
        result = _run_checks(stale_days=30, engine=engine)
        assert result == 0

    def test_returns_nonzero_on_duplicates(self):
        engine = _mock_engine(scalars=5)
        result = _run_checks(stale_days=30, engine=engine)
        assert result == 1

    def test_stale_days_passed_to_stale_query(self):
        engine = _mock_engine()
        _run_checks(stale_days=7, engine=engine)
        conn = engine.connect.return_value.__enter__.return_value
        calls = conn.execute.call_args_list
        has_stale = any(
            len(c.args) >= 2 and "cutoff" in c.kwargs
            for c in calls
        )
        has_stale_pos = any(
            len(c.args) >= 2 and isinstance(c.args[1], dict) and "cutoff" in c.args[1]
            for c in calls
        )
        assert has_stale or has_stale_pos

    def test_health_check_failure_exits(self):
        with (
            patch("validate_touch_index_bug.get_engine", return_value=MagicMock()),
            patch("validate_touch_index_bug.health_check", return_value=False),
        ):
            with pytest.raises(SystemExit) as exc:
                _run_checks(stale_days=30)
        assert exc.value.code == 1

    def test_accepts_pre_configured_engine(self):
        engine = _mock_engine()
        result = _run_checks(stale_days=30, engine=engine)
        assert result == 0
        engine.connect.assert_called_once()

    def test_creates_engine_when_none_passed(self):
        engine = _mock_engine()
        with (
            patch("validate_touch_index_bug.get_engine", return_value=engine),
            patch("validate_touch_index_bug.health_check", return_value=True),
        ):
            result = _run_checks(stale_days=30)
        assert result == 0

    def test_main_exits_nonzero_on_failures(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["validate_touch_index_bug.py"])
        engine = _mock_engine(scalars=3)
        with (
            patch("validate_touch_index_bug.get_engine", return_value=engine),
            patch("validate_touch_index_bug.health_check", return_value=True),
        ):
            with pytest.raises(SystemExit) as exc:
                from validate_touch_index_bug import main
                main()
        assert exc.value.code == 1

    def test_main_exits_zero_on_clean(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["validate_touch_index_bug.py"])
        engine = _mock_engine()
        with (
            patch("validate_touch_index_bug.get_engine", return_value=engine),
            patch("validate_touch_index_bug.health_check", return_value=True),
        ):
            from validate_touch_index_bug import main
            main()
        assert True
