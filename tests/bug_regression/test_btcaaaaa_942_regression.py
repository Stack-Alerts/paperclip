"""
Regression tests for BTCAAAAA-942: Remove --cov-fail-under=20 from global pytest addopts.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-942
Component: pyproject.toml

Root cause: [tool.pytest.ini_options] addopts included --cov-fail-under=20
globally, causing every partial test run (e.g. tests/ui_qt) to fail because
it only exercises a subset of src/ (~4% for the widget layer).

Fix: Remove --cov-fail-under=20 from addopts so isolated subset runs exit
with code 0. Coverage collection via --cov=src is preserved; the coverage
threshold gate now lives exclusively in the CI full-suite job.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-942"),
    pytest.mark.regression,
]

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PYPROJECT_TOML = REPO_ROOT / "pyproject.toml"


class TestCovFailUnderRemovedFromAddopts:
    """addopts in pyproject.toml must not contain --cov-fail-under."""

    def _read_addopts_line(self) -> str | None:
        content = PYPROJECT_TOML.read_text(encoding="utf-8")
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("addopts"):
                return stripped
        return None

    def test_addopts_line_exists(self):
        line = self._read_addopts_line()
        assert line is not None, "addopts line not found in pyproject.toml"

    def test_cov_fail_under_absent(self):
        addopts = self._read_addopts_line()
        assert addopts is not None, "addopts line not found"
        assert "--cov-fail-under" not in addopts, (
            "--cov-fail-under found in global addopts in pyproject.toml. "
            "BTCAAAAA-942 removed it so isolated subset runs (e.g. tests/ui_qt) "
            "do not fail due to low aggregate coverage. "
            "The threshold gate belongs exclusively in the CI full-suite job."
        )

    def test_cov_src_still_present(self):
        addopts = self._read_addopts_line()
        assert addopts is not None, "addopts line not found"
        assert "--cov=src" in addopts, (
            "--cov=src has been removed from addopts. "
            "BTCAAAAA-942 only removed --cov-fail-under; coverage collection "
            "via --cov=src must be preserved."
        )


class TestCovFailUnderCommentGate:
    """The threshold-documentation comment must remain in pyproject.toml."""

    def test_cov_fail_under_explained_in_comment(self):
        content = PYPROJECT_TOML.read_text(encoding="utf-8")
        assert "--cov-fail-under is intentionally absent" in content, (
            "The explanatory comment about --cov-fail-under being intentionally "
            "absent from global addopts has been removed. BTCAAAAA-942 added "
            "this comment to document that the threshold gate belongs in the "
            "CI full-suite coverage job, not as a global default."
        )


class TestPytestIniOptionsSection:
    """The [tool.pytest.ini_options] section must exist with its structural keys."""

    def _get_section_boundaries(self) -> tuple[int, int] | None:
        content = PYPROJECT_TOML.read_text(encoding="utf-8")
        lines = content.splitlines()
        start = None
        end = None
        for i, line in enumerate(lines):
            if line.strip().startswith("[tool.pytest.ini_options]"):
                start = i
            elif start is not None and line.strip().startswith("[") and i > start:
                end = i
                break
        if start is not None:
            return (start, end or len(lines))
        return None

    def test_section_exists(self):
        bounds = self._get_section_boundaries()
        assert bounds is not None, (
            "[tool.pytest.ini_options] section not found in pyproject.toml. "
            "BTCAAAAA-942 must preserve this section with addopts."
        )

    def test_minversion_configured(self):
        content = PYPROJECT_TOML.read_text(encoding="utf-8")
        assert 'minversion = "7.0"' in content, (
            "minversion must be set to at least 7.0 in [tool.pytest.ini_options]. "
            "This was not part of the BTCAAAAA-942 change and must not regress."
        )

    def test_addopts_line_is_after_comment(self):
        bounds = self._get_section_boundaries()
        assert bounds is not None
        content = PYPROJECT_TOML.read_text(encoding="utf-8")
        lines = content.splitlines()
        section_lines = lines[bounds[0] : bounds[1]]
        comment_idx = None
        addopts_idx = None
        for i, line in enumerate(section_lines):
            stripped = line.strip()
            if stripped.startswith("#") and "cov-fail-under" in stripped:
                comment_idx = i
            if stripped.startswith("addopts"):
                addopts_idx = i
        assert comment_idx is not None, (
            "Comment explaining --cov-fail-under absence not found above addopts. "
            "BTCAAAAA-942 added this comment as documentation."
        )
        assert addopts_idx is not None
        assert addopts_idx > comment_idx, (
            "The addopts line must follow the explanatory comment. "
            "BTCAAAAA-942 requires the comment directly above addopts."
        )


class TestAddoptsFlags:
    """Specific flags in addopts must be present and correct."""

    def _read_addopts_line(self) -> str | None:
        content = PYPROJECT_TOML.read_text(encoding="utf-8")
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("addopts"):
                return stripped
        return None

    def test_ra_flag_present(self):
        addopts = self._read_addopts_line()
        assert addopts is not None
        assert "-ra" in addopts, (
            "-ra flag missing from addopts. BTCAAAAA-942 did not remove "
            "this flag; it is needed for summary reporting."
        )

    def test_q_flag_present(self):
        addopts = self._read_addopts_line()
        assert addopts is not None
        assert "-q" in addopts, (
            "-q flag missing from addopts. BTCAAAAA-942 did not remove "
            "this flag; it is needed for quiet output."
        )

    def test_cov_config_flag_present(self):
        addopts = self._read_addopts_line()
        assert addopts is not None
        assert "--cov-config=.coveragerc" in addopts, (
            "--cov-config=.coveragerc missing from addopts. "
            "BTCAAAAA-942 preserved this flag alongside --cov=src."
        )

    def test_cov_report_term_missing_present(self):
        addopts = self._read_addopts_line()
        assert addopts is not None
        assert "--cov-report=term-missing" in addopts, (
            "--cov-report=term-missing missing from addopts. "
            "BTCAAAAA-942 preserved this flag alongside --cov=src."
        )


class TestTestpathsConfigured:
    """testpaths must be configured in [tool.pytest.ini_options]."""

    def test_testpaths_line_exists(self):
        content = PYPROJECT_TOML.read_text(encoding="utf-8")
        assert 'testpaths = ["tests"]' in content, (
            "testpaths configuration missing from pyproject.toml. "
            "BTCAAAAA-942 did not remove testpaths; it was preserved."
        )

    def test_testpaths_under_pytest_section(self):
        content = PYPROJECT_TOML.read_text(encoding="utf-8")
        lines = content.splitlines()
        pytest_section_start = None
        testpaths_line = -1
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("[tool.pytest.ini_options]"):
                pytest_section_start = i
            if stripped.startswith("testpaths"):
                testpaths_line = i
        assert pytest_section_start is not None
        assert testpaths_line > pytest_section_start, (
            "testpaths must appear within [tool.pytest.ini_options]. "
            "BTCAAAAA-942 did not relocate testpaths."
        )
