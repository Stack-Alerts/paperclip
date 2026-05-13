"""
Regression tests for BTCAAAAA-142: Impact Gate runner — bug ID to file path
resolution and result aggregation.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-142
Component: scripts/impact_gate_runner.py

Root cause: The Impact Gate runner (impact_gate_runner.py:89-94) maps bug IDs to
test_btcaaaaa_{id}_regression.py. This file provides regression coverage for the
runner's ID resolution, JUnit parsing, and summary aggregation logic so that
fixes to the runner do not regress the bug regression gate itself.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-142"),
    pytest.mark.regression,
]

_runner_path = Path(__file__).resolve().parents[2] / "scripts" / "impact_gate_runner.py"
_spec = __import__("importlib.util").util.spec_from_file_location(
    "impact_gate_runner", _runner_path
)
_runner = __import__("importlib.util").util.module_from_spec(_spec)
sys.modules["impact_gate_runner"] = _runner
_spec.loader.exec_module(_runner)


class TestBugTestPathResolution:
    """Verify _bug_test_path maps IDs correctly."""

    def test_resolves_valid_bug_id(self):
        path = _runner._bug_test_path("BTCAAAAA-142")
        assert path is not None
        assert path.name == "test_btcaaaaa_142_regression.py"

    def test_resolves_another_valid_bug_id(self):
        path = _runner._bug_test_path("BTCAAAAA-33")
        assert path is not None
        assert path.name == "test_btcaaaaa_33_regression.py"

    def test_rejects_non_bug_prefix(self):
        path = _runner._bug_test_path("FDR-142")
        assert path is None

    def test_rejects_malformed_id(self):
        path = _runner._bug_test_path("BTCAAAAA-abc")
        assert path is None

    def test_rejects_empty_string(self):
        path = _runner._bug_test_path("")
        assert path is None

    def test_rejects_none_prefix(self):
        path = _runner._bug_test_path("BTC-142")
        assert path is None


class TestFRTestPathResolution:
    """Verify _fr_test_path maps IDs correctly."""

    def test_resolves_fdr_prefix(self):
        path = _runner._fr_test_path("FDR-850")
        assert path is not None
        assert path.name.startswith("test_fdr_")

    def test_resolves_btcaaaaa_prefix_fr(self):
        path = _runner._fr_test_path("BTCAAAAA-850")
        assert path.name.startswith(("test_fdr_", "test_btcaaaaa_"))

    def test_rejects_malformed_fr_id(self):
        path = _runner._fr_test_path("FDR-xyz")
        assert path is None

    def test_rejects_empty_fr_id(self):
        path = _runner._fr_test_path("")
        assert path is None


class TestRunEdgeCases:
    """Edge cases for the runner's run() function."""

    def test_empty_ids_returns_error(self):
        result = _runner.run([], [])
        assert result["status"] == "ERROR"
        assert result["summary"]["total"] == 0

    def test_all_missing_ids_reported(self):
        result = _runner.run(["FDR-99999"], ["BTCAAAAA-99999"])
        assert result["summary"]["missing_test_files"] == 2

    def test_output_has_expected_schema(self):
        result = _runner.run([], ["BTCAAAAA-140"])
        assert "timestamp" in result
        assert "status" in result
        assert "summary" in result
        assert "fr_results" in result
        assert "bug_results" in result

    def test_summary_counts_exist(self):
        result = _runner.run([], ["BTCAAAAA-140"])
        s = result["summary"]
        assert "total" in s
        assert "passed" in s
        assert "failed" in s
        assert "errors" in s
        assert isinstance(s["total"], int)
        assert isinstance(s["passed"], int)

    def test_fr_results_is_dict(self):
        result = _runner.run(["FDR-850"], [])
        assert isinstance(result["fr_results"], dict)

    def test_bug_results_is_dict(self):
        result = _runner.run([], ["BTCAAAAA-140"])
        assert isinstance(result["bug_results"], dict)

    def test_bug_result_has_status_and_tests(self):
        result = _runner.run([], ["BTCAAAAA-140"])
        entry = result["bug_results"].get("BTCAAAAA-140", {})
        assert "status" in entry
        assert "tests" in entry
        assert isinstance(entry["tests"], list)

    def test_fr_result_has_status_and_tests(self):
        result = _runner.run(["FDR-850"], [])
        entry = result["fr_results"].get("FDR-850", {})
        assert "status" in entry
        assert "tests" in entry
        assert isinstance(entry["tests"], list)
