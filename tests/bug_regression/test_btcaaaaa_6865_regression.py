"""
Regression tests for BTCAAAAA-6865: add missing bug regression test file for
BTCAAAAA-4892 (_emit_json_summary worker param requirement).

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-6865
Components: tests/test_touch_index/test_bug_worker.py
            tests/bug_regression/test_btcaaaaa_4892_regression.py
            src/touch_index/__main__.py

Root cause / changes:
  1. The _emit_json_summary function in __main__.py had a misleading default
     ``worker: str = "bug"`` on its worker parameter.  All callers always
     passed worker explicitly, but the default meant a future caller who
     forgot to pass it would silently produce output claiming to be the
     "bug" worker when it might be the FR worker (or vice versa).
     Fix (BTCAAAAA-4892): worker is now a required positional parameter with
     no default.
  2. BTCAAAAA-4892's regression test file was missing (no test shim in
     tests/bug_regression/).  Fix (BTCAAAAA-6865): created
     tests/bug_regression/test_btcaaaaa_4892_regression.py re-exporting the
     canonical TestEmitJsonSummaryRequiresWorker tests, and added that test
     class to tests/test_touch_index/test_bug_worker.py verifying that
     _emit_json_summary(args) without worker= raises TypeError.

This file re-exports the existing unit tests from tests/test_touch_index/ so
the Impact Gate runner can discover them by issue ID.  The canonical tests
live in tests/test_touch_index/ and must not drift.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-6865"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_bug_worker import (  # noqa: E402, F401
    TestEmitJsonSummaryRequiresWorker,
)

# ---------------------------------------------------------------------------
# Source-level contract checks for BTCAAAAA-6865-specific changes
# ---------------------------------------------------------------------------

REG_4892_PATH = (
    Path(__file__).resolve().parents[2]
    / "tests"
    / "bug_regression"
    / "test_btcaaaaa_4892_regression.py"
)
REG_4892_TEXT = REG_4892_PATH.read_text()

MAIN_SOURCE = Path(__file__).resolve().parents[2] / "src" / "touch_index" / "__main__.py"
MAIN_TEXT = MAIN_SOURCE.read_text()

BUG_WORKER_TEST = (
    Path(__file__).resolve().parents[2]
    / "tests"
    / "test_touch_index"
    / "test_bug_worker.py"
)
BUG_WORKER_TEST_TEXT = BUG_WORKER_TEST.read_text()


class TestBtc6865RegressionFileFor4892:
    """BTCAAAAA-6865: The regression shim for BTCAAAAA-4892 must exist and
    correctly re-export the canonical test class."""

    def test_regression_shim_4892_exists(self):
        """tests/bug_regression/test_btcaaaaa_4892_regression.py exists."""
        assert REG_4892_PATH.exists(), (
            "BTCAAAAA-4892 regression shim file must exist"
        )

    def test_regression_shim_4892_imports_worker_test_class(self):
        """The 4892 shim imports TestEmitJsonSummaryRequiresWorker."""
        assert "TestEmitJsonSummaryRequiresWorker" in REG_4892_TEXT

    def test_regression_shim_4892_has_bug_marker(self):
        """The 4892 shim is marked with pytest.mark.bug('BTCAAAAA-4892')."""
        assert 'pytest.mark.bug("BTCAAAAA-4892")' in REG_4892_TEXT

    def test_regression_shim_4892_has_regression_marker(self):
        """The 4892 shim is marked with pytest.mark.regression."""
        assert "pytest.mark.regression" in REG_4892_TEXT


class TestBtc6865EmitJsonSummaryWorkerParam:
    """BTCAAAAA-6865: _emit_json_summary worker param must have no default
    (the fix verified by TestEmitJsonSummaryRequiresWorker)."""

    def test_worker_param_has_no_default(self):
        """_emit_json_summary(..., worker: str, ...) has no default value."""
        lines = MAIN_TEXT.split("\n")
        in_sig = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("def _emit_json_summary("):
                in_sig = True
                continue
            if in_sig:
                if stripped.startswith("worker"):
                    assert stripped == "worker: str,", (
                        f"worker param must have no default, got: {stripped}"
                    )
                    return
                if stripped == ") -> None:":
                    break
        assert False, "worker param not found in _emit_json_summary signature"

    def test_worker_passed_explicitly_at_all_callsites(self):
        """Every _emit_json_summary call site (including multi-line) passes worker= explicitly."""
        import re

        flat = MAIN_TEXT.replace("\n", " ")
        calls = re.findall(r"(?<!def )_emit_json_summary\(.+?\)", flat, re.DOTALL)
        assert len(calls) > 0, "No _emit_json_summary call sites found"
        for call in calls:
            assert "worker=" in call, (
                f"_emit_json_summary call missing worker=: {call.strip()[:120]}"
            )


class TestBtc6865TestClassInBugWorker:
    """BTCAAAAA-6865: TestEmitJsonSummaryRequiresWorker must exist in
    tests/test_touch_index/test_bug_worker.py."""

    def test_class_defined(self):
        """The test class is defined in the canonical test file."""
        assert "class TestEmitJsonSummaryRequiresWorker:" in BUG_WORKER_TEST_TEXT

    def test_missing_worker_raises_type_error_test_exists(self):
        """test_missing_worker_raises_type_error is defined."""
        assert "def test_missing_worker_raises_type_error" in BUG_WORKER_TEST_TEXT

    def test_worker_bug_succeeds_test_exists(self):
        """test_worker_bug_succeeds is defined."""
        assert "def test_worker_bug_succeeds" in BUG_WORKER_TEST_TEXT

    def test_worker_fr_succeeds_test_exists(self):
        """test_worker_fr_succeeds is defined."""
        assert "def test_worker_fr_succeeds" in BUG_WORKER_TEST_TEXT
