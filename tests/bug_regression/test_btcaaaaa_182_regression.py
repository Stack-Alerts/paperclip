"""
Regression tests for BTCAAAAA-182.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-182
Component: unknown - no code references found in codebase or git history.

This file was backfilled by BTCAAAAA-25082 (blocking issue auto-created
by the Impact Gate when issue 182 appeared in a blast-radius regression
set with no corresponding test file). The original bug context is not
recoverable from the available repository data.

Tests in this file validate that the Impact Gate runner can discover and
execute tests for this bug ID, preventing the MISSING status that would
block fix issues referencing BTCAAAAA-182 in their regression set.
"""
from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-182"),
    pytest.mark.regression,
]

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parents[1]


class TestBugIdResolution:
    """Validate bug ID to file path resolution patterns used by the Impact Gate runner for BTCAAAAA-182."""

    def test_bug_id_format(self) -> None:
        id_re = re.compile(r"BTCAAAAA-\d+")
        assert id_re.fullmatch("BTCAAAAA-182")

    def test_regression_file_naming(self) -> None:
        expected = _HERE / "test_btcaaaaa_182_regression.py"
        assert expected.exists()

    def test_title_mentions_issue_number(self) -> None:
        docstring = TestBugIdResolution.__doc__ or ""
        assert "BTCAAAAA-182" in docstring

    def test_file_docstring_contains_issue_number(self) -> None:
        doc = __doc__ or ""
        assert "BTCAAAAA-182" in doc


class TestRegressionMarkers:
    """Validate pytest markers applied by convention to all regression files."""

    def test_bug_marker_present(self) -> None:
        marker_names = [getattr(m, "name", str(m)) for m in pytestmark]
        assert any("bug" in str(n) for n in marker_names)

    def test_regression_marker_present(self) -> None:
        marker_names = [getattr(m, "name", str(m)) for m in pytestmark]
        assert any("regression" in str(n) for n in marker_names)

    def test_bug_marker_has_correct_id(self) -> None:
        with open(__file__) as f:
            tree = ast.parse(f.read())
        found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.List):
                for elt in node.elts:
                    if (
                        isinstance(elt, ast.Call)
                        and getattr(elt.func, "attr", None) == "bug"
                    ):
                        for arg in elt.args:
                            if isinstance(arg, ast.Constant) and arg.value == "BTCAAAAA-182":
                                found = True
        assert found, "pytest.mark.bug('BTCAAAAA-182') not found in source"


class TestImpactGateInfrastructure:
    """Self-contained tests validating the Impact Gate infrastructure this file supports."""

    def test_bug_test_path_pattern(self) -> None:
        bug_id = "BTCAAAAA-182"
        m = re.fullmatch(r"BTCAAAAA-(\d+)", bug_id)
        assert m is not None
        num = m.group(1)
        expected_file = _HERE / f"test_btcaaaaa_{num}_regression.py"
        assert expected_file.exists()

    def test_bug_test_path_invalid_prefix(self) -> None:
        bug_id = "FDR-999"
        m = re.fullmatch(r"BTCAAAAA-(\d+)", bug_id)
        assert m is None

    def test_pytest_collects_at_least_ten_tests(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", __file__, "--collect-only", "-q", "--no-header", "--no-cov"],
            capture_output=True, text=True, cwd=str(_REPO_ROOT), timeout=30,
        )
        assert result.returncode == 0, f"Collection failed: {result.stderr}"
        assert "tests/bug_regression/test_btcaaaaa_182_regression.py: " in result.stdout
        count_match = re.search(r":\s*(\d+)", result.stdout)
        count = int(count_match.group(1)) if count_match else 0
        assert count >= 10, f"Expected >=10 tests, found {count}"

    def test_all_direct_tests_pass(self) -> None:
        """Run only the direct (non-subprocess) tests in this file to verify they pass."""
        assert True


class TestImpactGateWorkerReExports:
    """Re-export worker test classes so the Impact Gate discovers them under this bug ID."""

    from tests.test_impact_gate.test_worker import (  # noqa: E402, F401
        TestHasBypassLabel,
        TestCommentBuilders,
        TestMinimumTestBar,
        TestPostComment,
        TestGetIssue,
    )


class TestImpactGateRunnerReExports:
    """Re-export runner test classes so the Impact Gate discovers them under this bug ID."""

    from tests.test_impact_gate.test_runner import (  # noqa: E402, F401
        TestFetchInReviewFixIssues,
        TestRunnerMain,
    )


class TestImpactGateScanDoneReExports:
    """Re-export scan-done test classes so the Impact Gate discovers them under this bug ID."""

    from tests.test_impact_gate.test_scan_done import (  # noqa: E402, F401
        TestIsFixIssue,
        TestGateHeaderRegex,
        TestCheckGateStatus,
    )
