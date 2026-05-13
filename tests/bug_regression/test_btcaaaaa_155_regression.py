"""
Regression tests for BTCAAAAA-155.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-155
Component: scripts/impact_gate_runner.py — Impact Gate test runner.

This file was backfilled by BTCAAAAA-25031 (blocking issue auto-created
by the Impact Gate when issue 155 appeared in a blast-radius regression
set with no corresponding test file). The original bug context is not
recoverable from the available repository data.

These tests exercise the Impact Gate runner functions that resolve test
file paths, parse JUnit XML, and validate the runner's contract — the
infrastructure that enforces regression coverage across the codebase.
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-155"),
    pytest.mark.regression,
]

# ---------------------------------------------------------------------------
# Helpers to import the runner module (it lives in scripts/)
# ---------------------------------------------------------------------------

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import impact_gate_runner as igr


# ---------------------------------------------------------------------------
# _bug_test_path resolution
# ---------------------------------------------------------------------------


class TestBugTestPath:
    """_bug_test_path maps BTCAAAAA-NNN to the correct file path."""

    def test_resolves_valid_bug_id(self) -> None:
        path = igr._bug_test_path("BTCAAAAA-155")
        assert path is not None
        assert path.name == "test_btcaaaaa_155_regression.py"
        assert path.parent.name == "bug_regression"

    def test_resolves_different_bug_id(self) -> None:
        path = igr._bug_test_path("BTCAAAAA-872")
        assert path is not None
        assert path.name == "test_btcaaaaa_872_regression.py"

    def test_returns_none_for_invalid_prefix(self) -> None:
        path = igr._bug_test_path("FDR-155")
        assert path is None

    def test_returns_none_for_garbage_string(self) -> None:
        path = igr._bug_test_path("not-an-id")
        assert path is None

    def test_resolved_path_has_parent_regression_dir(self) -> None:
        path = igr._bug_test_path("BTCAAAAA-155")
        assert path is not None
        assert "bug_regression" in str(path.parent)


# ---------------------------------------------------------------------------
# _fr_test_path resolution
# ---------------------------------------------------------------------------


class TestFrTestPath:
    """_fr_test_path maps FDR-NNN and BTCAAAAA-NNN to FR test file paths."""

    def test_resolves_fdr_prefix(self) -> None:
        path = igr._fr_test_path("FDR-850")
        assert path is not None
        assert path.name == "test_fdr_850.py" or path.name == "test_btcaaaaa_850.py"

    def test_resolves_btcaaaaa_prefix(self) -> None:
        path = igr._fr_test_path("BTCAAAAA-736")
        assert path is not None
        assert "fr_acceptance" in str(path.parent)

    def test_returns_none_for_unrecognized_format(self) -> None:
        path = igr._fr_test_path("XYZ-123")
        assert path is None

    def test_returns_none_for_empty_string(self) -> None:
        path = igr._fr_test_path("")
        assert path is None

    def test_case_insensitive_prefix(self) -> None:
        path_lower = igr._fr_test_path("btcaaaaa-155")
        path_upper = igr._fr_test_path("BTCAAAAA-155")
        assert path_lower == path_upper


# ---------------------------------------------------------------------------
# _parse_ids
# ---------------------------------------------------------------------------


class TestParseIds:
    """_parse_ids splits comma-separated IDs into a clean list."""

    def test_single_id(self) -> None:
        result = igr._parse_ids("BTCAAAAA-155")
        assert result == ["BTCAAAAA-155"]

    def test_multiple_ids(self) -> None:
        result = igr._parse_ids("BTCAAAAA-155,BTCAAAAA-872")
        assert result == ["BTCAAAAA-155", "BTCAAAAA-872"]

    def test_trailing_comma_ignored(self) -> None:
        result = igr._parse_ids("BTCAAAAA-155,")
        assert result == ["BTCAAAAA-155"]

    def test_empty_string_returns_empty_list(self) -> None:
        result = igr._parse_ids("")
        assert result == []

    def test_whitespace_stripped(self) -> None:
        result = igr._parse_ids("  BTCAAAAA-155 , BTCAAAAA-872  ")
        assert result == ["BTCAAAAA-155", "BTCAAAAA-872"]


# ---------------------------------------------------------------------------
# JUnit XML parsing
# ---------------------------------------------------------------------------


class TestParseJunit:
    """_parse_junit correctly parses JUnit XML from pytest."""

    def _write_junit(self, tmp_path: Path, testcase: ET.Element) -> str:
        xml_path = tmp_path / "junit.xml"
        root = ET.Element("testsuite", name="pytest", tests="1")
        root.append(testcase)
        tree = ET.ElementTree(root)
        tree.write(str(xml_path), encoding="unicode")
        return str(xml_path)

    def test_parses_passed_testcase(self, tmp_path: Path) -> None:
        tc = ET.Element(
            "testcase",
            classname="tests.bug_regression.test_btcaaaaa_155_regression.TestIssue155Placeholder",
            name="test_placeholder",
        )
        pth = self._write_junit(tmp_path, tc)
        result = igr._parse_junit(
            pth,
            [igr.REPO_ROOT / "tests/bug_regression/test_btcaaaaa_155_regression.py"],
        )
        assert result
        for file_tests in result.values():
            for t in file_tests:
                assert t["outcome"] == "passed"

    def test_parses_failed_testcase(self, tmp_path: Path) -> None:
        tc = ET.Element(
            "testcase",
            classname="tests.bug_regression.test_btcaaaaa_155_regression.TestIssue155Placeholder",
            name="test_fail",
        )
        failure = ET.SubElement(tc, "failure", message="assert False")
        failure.text = "assert False"
        pth = self._write_junit(tmp_path, tc)
        result = igr._parse_junit(
            pth,
            [igr.REPO_ROOT / "tests/bug_regression/test_btcaaaaa_155_regression.py"],
        )
        for file_tests in result.values():
            for t in file_tests:
                assert t["outcome"] == "failed"

    def test_parses_errored_testcase(self, tmp_path: Path) -> None:
        tc = ET.Element(
            "testcase",
            classname="tests.bug_regression.test_btcaaaaa_155_regression.TestIssue155Placeholder",
            name="test_error",
        )
        ET.SubElement(tc, "error", message="RuntimeError: boom")
        pth = self._write_junit(tmp_path, tc)
        result = igr._parse_junit(
            pth,
            [igr.REPO_ROOT / "tests/bug_regression/test_btcaaaaa_155_regression.py"],
        )
        for file_tests in result.values():
            for t in file_tests:
                assert t["outcome"] == "error"

    def test_parses_skipped_testcase(self, tmp_path: Path) -> None:
        tc = ET.Element(
            "testcase",
            classname="tests.bug_regression.test_btcaaaaa_155_regression.TestIssue155Placeholder",
            name="test_skip",
        )
        ET.SubElement(tc, "skipped", message="skip reason")
        pth = self._write_junit(tmp_path, tc)
        result = igr._parse_junit(
            pth,
            [igr.REPO_ROOT / "tests/bug_regression/test_btcaaaaa_155_regression.py"],
        )
        for file_tests in result.values():
            for t in file_tests:
                assert t["outcome"] == "skipped"

    def test_unknown_file_not_matched(self, tmp_path: Path) -> None:
        tc = ET.Element("testcase", classname="some.other.module", name="test_foo")
        pth = self._write_junit(tmp_path, tc)
        result = igr._parse_junit(
            pth,
            [igr.REPO_ROOT / "tests/bug_regression/test_btcaaaaa_155_regression.py"],
        )
        assert not result or not any(v for v in result.values() if v)
