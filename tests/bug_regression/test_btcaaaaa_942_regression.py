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
