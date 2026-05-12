"""
Regression tests for BTCAAAAA-1554: runId-based dedup for stale-run evaluation.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1554
Fixed in commits: 0dfa7db, 4fe515a
Component: scripts/patches/0002-add-stale-run-evaluation-dedup.py

Root cause: when a stale-run evaluation was marked done, findOpenStaleRunEvaluation()
returned null (filters out done/cancelled statuses), so the next recovery scan
tried to create a new evaluation for the same runId. If the database unique
constraint existed the create would crash the recovery scan; if it didn't exist
the duplicate would succeed, generating infinite review issues.

Fix: add a pre-creation query for ANY stale-run evaluation (including
done/cancelled) for the same runId. If one exists, return 'skipped'. Allows
one re-alert at critical (4h+) silence level.

This file tests the patch script logic: line-finding, file patching, idempotency.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1554"),
    pytest.mark.regression,
]

import importlib
import sys

_patch_path = (
    Path(__file__).resolve().parents[2] / "scripts" / "patches" / "0002-add-stale-run-evaluation-dedup.py"
)
_spec = importlib.util.spec_from_file_location(
    "patch_0002", _patch_path
)
_patch_mod = importlib.util.module_from_spec(_spec)
sys.modules["patch_0002"] = _patch_mod
_spec.loader.exec_module(_patch_mod)

_find_line_number = _patch_mod._find_line_number
patch_file = _patch_mod.patch_file
MARKER = _patch_mod.MARKER
MATCH_OWNER = _patch_mod.MATCH_OWNER
MATCH_DESC = _patch_mod.MATCH_DESC


_MOCK_JS_CONTENT = """\
    const level = determineStaleRunLevel(input.run);

    const ownerAgentId = await resolveStaleRunOwnerAgentId(
        input.run.companyId,
        input.run.id,
    );

    const description = buildStaleRunEvaluationDescription(
        input.run,
        level,
    );

    let evaluation;
"""


class TestFindLineNumber:
    def test_finds_exact_match(self):
        lines = ["foo\n", "bar\n", "baz\n"]
        assert _find_line_number(lines, "bar") == 2

    def test_returns_none_when_not_found(self):
        lines = ["foo\n", "bar\n"]
        assert _find_line_number(lines, "qux") is None

    def test_finds_match_on_first_line(self):
        lines = ["match this\n", "other\n"]
        assert _find_line_number(lines, "match") == 1

    def test_finds_match_on_last_line(self):
        lines = ["a\n", "b\n", "c\n"]
        assert _find_line_number(lines, "c") == 3

    def test_skips_partial_line_no_match(self):
        lines = ["abc\n", "def\n"]
        assert _find_line_number(lines, "xyz") is None

    def test_finds_owner_pattern(self):
        lines = _MOCK_JS_CONTENT.splitlines(keepends=True)
        assert _find_line_number(lines, MATCH_OWNER) == 3

    def test_finds_desc_pattern(self):
        lines = _MOCK_JS_CONTENT.splitlines(keepends=True)
        assert _find_line_number(lines, MATCH_DESC) == 8


class TestPatchFile:
    def test_patches_mock_js_file(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".js", delete=False
        ) as f:
            f.write(_MOCK_JS_CONTENT)
            tmp = Path(f.name)

        try:
            result = patch_file(tmp)
            assert result is True

            patched = tmp.read_text()
            assert MARKER in patched
            assert "priorEvals" in patched
            assert "critical" in patched
            assert "re-alert" in patched
        finally:
            os.unlink(tmp)

    def test_already_patched_is_idempotent(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".js", delete=False
        ) as f:
            f.write(_MOCK_JS_CONTENT)
            tmp = Path(f.name)

        try:
            patch_file(tmp)
            result = patch_file(tmp)
            assert result is False

            patched = tmp.read_text()
            assert MARKER in patched
        finally:
            os.unlink(tmp)

    def test_returns_false_for_nonexistent_file(self):
        result = patch_file(Path("/nonexistent/path.js"))
        assert result is False

    def test_returns_false_for_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = patch_file(Path(tmpdir))
            assert result is False

    def test_handles_missing_owner_pattern(self):
        content = "const x = 1;\nconst y = 2;\n"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".js", delete=False
        ) as f:
            f.write(content)
            tmp = Path(f.name)

        try:
            result = patch_file(tmp)
            assert result is False
        finally:
            os.unlink(tmp)

    def test_patched_file_contains_insert_blocks(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".js", delete=False
        ) as f:
            f.write(_MOCK_JS_CONTENT)
            tmp = Path(f.name)

        try:
            patch_file(tmp)
            text = tmp.read_text()
            assert "priorEvals" in text
            assert "skipped" in text
            assert "re-alert" in text
        finally:
            os.unlink(tmp)


class TestConstants:
    def test_marker_is_present(self):
        assert "paperclip-patch" in MARKER

    def test_match_owner_is_correct(self):
        assert "ownerAgentId" in MATCH_OWNER

    def test_match_desc_is_correct(self):
        assert "buildStaleRunEvaluationDescription" in MATCH_DESC
