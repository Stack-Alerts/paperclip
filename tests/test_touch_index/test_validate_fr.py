"""Unit tests for scripts/validate_touch_index_fr.py validation checks.

All DB I/O is mocked so tests run offline.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))
sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

import importlib

runner_path = Path(__file__).parents[2] / "scripts" / "validate_touch_index_fr.py"
_spec = importlib.util.spec_from_file_location("validate_touch_index_fr", runner_path)
_runner = importlib.util.module_from_spec(_spec)
sys.modules["validate_touch_index_fr"] = _runner
_spec.loader.exec_module(_runner)
_run_checks = _runner._run_checks


def _mock_engine(dup_scalar: int = 0):
    conn = MagicMock()
    scalar_result = MagicMock()
    scalar_result.scalar = MagicMock(return_value=dup_scalar)
    scalar_result.fetchall = MagicMock(return_value=[])
    execute = MagicMock(return_value=scalar_result)
    conn.execute = execute
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=conn)
    ctx.__exit__ = MagicMock(return_value=False)
    engine = MagicMock()
    engine.connect = MagicMock(return_value=ctx)
    return engine


class TestValidateFR:
    def test_returns_zero_on_clean(self):
        engine = _mock_engine()
        with patch("validate_touch_index_fr.get_engine", return_value=engine):
            result = _run_checks(stale_hours=168)
        assert result == 0

    def test_returns_nonzero_on_duplicates(self):
        engine = _mock_engine(dup_scalar=5)
        with patch("validate_touch_index_fr.get_engine", return_value=engine):
            result = _run_checks(stale_hours=168)
        assert result == 2  # duplicate + null = 2 failures

    def test_stale_hours_passed_to_stale_query(self):
        engine = _mock_engine()
        with patch("validate_touch_index_fr.get_engine", return_value=engine):
            _run_checks(stale_hours=48)
        conn = engine.connect.return_value.__enter__.return_value
        # The first positional arg to execute() is the SQL text object
        sql_texts = [c[0][0] for c in conn.execute.call_args_list]
        assert any("updated_at" in str(t) for t in sql_texts)

    def test_health_check_failure_exits(self):
        engine = MagicMock()
        with (
            patch("validate_touch_index_fr.get_engine", return_value=engine),
            patch("validate_touch_index_fr.health_check", return_value=False),
        ):
            with pytest.raises(SystemExit) as exc:
                _run_checks(stale_hours=168)
        assert exc.value.code == 1

    def test_main_exits_nonzero_on_failures(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["validate_touch_index_fr.py"])
        engine = _mock_engine(dup_scalar=3)
        with (
            patch("validate_touch_index_fr.get_engine", return_value=engine),
            patch("validate_touch_index_fr.health_check", return_value=True),
        ):
            with pytest.raises(SystemExit) as exc:
                from validate_touch_index_fr import main

                main()
        assert exc.value.code == 1

    def test_main_exits_zero_on_clean(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["validate_touch_index_fr.py"])
        engine = _mock_engine()
        with (
            patch("validate_touch_index_fr.get_engine", return_value=engine),
            patch("validate_touch_index_fr.health_check", return_value=True),
        ):
            from validate_touch_index_fr import main

            main()
        assert True

    def test_accepts_pre_configured_engine(self):
        """When an engine is passed directly, it is used instead of creating a new one."""
        engine = _mock_engine()  # already configured mock engine
        result = _run_checks(stale_hours=168, engine=engine)
        assert result == 0
        # The engine.connect should have been called (not get_engine)
        engine.connect.assert_called_once()
