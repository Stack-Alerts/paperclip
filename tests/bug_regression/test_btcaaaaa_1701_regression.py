"""
Regression tests for BTCAAAAA-1701: apply _is_source_file filter to
comment-extracted paths in bug-close ingestion worker.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1701
Component: src/touch_index/comment_extractor.py

Root cause: extract_files_from_text() did not filter extracted paths through
_is_source_file (from git_extractor), while get_files_for_commit() did.
This caused inconsistency — non-source files (.sql, alembic/ prefix, etc.)
would be indexed when the bug worker fell back to comment extraction but
excluded when found via git history.

Fix: import _is_source_file from .git_extractor inside extract_files_from_text
and gate each extracted path on both _is_source_file and _has_allowed_prefix.

These tests verify the _is_source_file filter is active in
extract_files_from_text and correctly excludes paths that git extraction
would also reject, while still admitting valid source files.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1701"),
    pytest.mark.regression,
]


# ---------------------------------------------------------------------------
# _is_source_file integration — filter applied inside extract_files_from_text
# ---------------------------------------------------------------------------


class TestIsSourceFileIntegration:
    """Verify extract_files_from_text applies _is_source_file so that
    comment-extracted paths are consistent with git-extracted paths."""

    def test_is_source_file_imported_in_module(self) -> None:
        """_is_source_file must be importable through the comment_extractor
        module chain, proving the filter is wired in."""
        from touch_index.git_extractor import _is_source_file
        from touch_index.comment_extractor import extract_files_from_text
        assert callable(_is_source_file)
        assert callable(extract_files_from_text)

    def test_scripts_lakeapi_excluded_by_is_source(self) -> None:
        """scripts/LakeAPI/... passes _has_allowed_prefix (starts with scripts/)
        but _is_source_file must reject it for consistency with git extraction."""
        from touch_index.comment_extractor import extract_files_from_text
        paths = extract_files_from_text("Changed `scripts/LakeAPI/loader.py` in PR")
        assert paths == []

    def test_scripts_archived_excluded_by_is_source(self) -> None:
        """scripts/archived/... passes _has_allowed_prefix (starts with scripts/)
        but _is_source_file must reject it."""
        from touch_index.comment_extractor import extract_files_from_text
        paths = extract_files_from_text("Changed `scripts/archived/old_worker.py`")
        assert paths == []

    def test_alembic_excluded(self) -> None:
        """alembic/ prefix paths (.py files) should be excluded by _is_source_file."""
        from touch_index.comment_extractor import extract_files_from_text
        paths = extract_files_from_text(
            "Ran migration in `alembic/versions/abc123_add_column.py`"
        )
        assert paths == []

    def test_github_workflows_excluded(self) -> None:
        """.github/ prefix should be excluded by _is_source_file."""
        from touch_index.comment_extractor import extract_files_from_text
        paths = extract_files_from_text(
            "Updated `.github/workflows/tool.py`"
        )
        assert paths == []

    def test_docs_excluded(self) -> None:
        """docs/ prefix should be excluded by _is_source_file."""
        from touch_index.comment_extractor import extract_files_from_text
        paths = extract_files_from_text("Added `docs/conf.py` for Sphinx")
        assert paths == []

    def test_archived_prefix_excluded(self) -> None:
        """archived/ prefix should be excluded by _is_source_file."""
        from touch_index.comment_extractor import extract_files_from_text
        paths = extract_files_from_text("Moved `archived/utils_strategy_builder_legacy/foo.py`")
        assert paths == []


# ---------------------------------------------------------------------------
# Positive cases — valid source files still pass both filters
# ---------------------------------------------------------------------------


class TestValidSourceFilesPassFilters:
    """Verify that standard source files in allowed directories still pass
    both _is_source_file and _has_allowed_prefix."""

    def test_src_py_file_included(self) -> None:
        from touch_index.comment_extractor import extract_files_from_text
        paths = extract_files_from_text("Changed `src/optimizer_v3/engine.py`")
        assert paths == ["src/optimizer_v3/engine.py"]

    def test_tests_py_file_included(self) -> None:
        from touch_index.comment_extractor import extract_files_from_text
        paths = extract_files_from_text("Added `tests/test_foo.py`")
        assert paths == ["tests/test_foo.py"]

    def test_scripts_py_file_included(self) -> None:
        """Regular scripts/... paths (not LakeAPI or archived) should be included."""
        from touch_index.comment_extractor import extract_files_from_text
        paths = extract_files_from_text("Created `scripts/run_worker.py`")
        assert paths == ["scripts/run_worker.py"]

    def test_js_file_included(self) -> None:
        from touch_index.comment_extractor import extract_files_from_text
        paths = extract_files_from_text("Updated `src/static/app.js`")
        assert paths == ["src/static/app.js"]

    def test_ts_file_included(self) -> None:
        from touch_index.comment_extractor import extract_files_from_text
        paths = extract_files_from_text("Refactored `src/lib/utils.ts`")
        assert paths == ["src/lib/utils.ts"]


# ---------------------------------------------------------------------------
# Backtick + bare path consistency — both match paths are filtered
# ---------------------------------------------------------------------------


class TestBacktickAndBarePathConsistency:
    """Verify _is_source_file is applied to both backtick-wrapped (`...`)
    and bare-path matches."""

    def test_backtick_lakeapi_excluded(self) -> None:
        from touch_index.comment_extractor import extract_files_from_text
        paths = extract_files_from_text("Fixed `scripts/LakeAPI/parser.py`")
        assert paths == []

    def test_bare_path_lakeapi_excluded(self) -> None:
        """Bare path matching scripts/LakeAPI should also be excluded."""
        from touch_index.comment_extractor import extract_files_from_text
        paths = extract_files_from_text("Fixed scripts/LakeAPI/parser.py")
        assert paths == []

    def test_backtick_valid_included(self) -> None:
        from touch_index.comment_extractor import extract_files_from_text
        paths = extract_files_from_text("Changed `src/foo/bar.py`")
        assert paths == ["src/foo/bar.py"]

    def test_bare_path_valid_included(self) -> None:
        from touch_index.comment_extractor import extract_files_from_text
        paths = extract_files_from_text("Changed src/foo/bar.py in the PR")
        assert paths == ["src/foo/bar.py"]

    def test_mixed_valid_and_excluded(self) -> None:
        """When text contains both valid and excluded paths, only valid
        paths are returned."""
        from touch_index.comment_extractor import extract_files_from_text
        text = (
            "Fixed `src/engine.py` and also touched "
            "`scripts/LakeAPI/loader.py` and `alembic/versions/abc.py`"
        )
        paths = extract_files_from_text(text)
        assert paths == ["src/engine.py"]


# ---------------------------------------------------------------------------
# Consistency with git_extractor._is_source_file
# ---------------------------------------------------------------------------


class TestConsistencyWithGitExtractor:
    """Verify that the same _is_source_file function used in git extraction
    is also used in comment extraction."""

    def test_git_and_comment_use_same_filter(self) -> None:
        """Both modules should reference the same _is_source_file function."""
        from touch_index.git_extractor import _is_source_file as git_filter
        assert git_filter("src/foo.py") is True
        assert git_filter("scripts/LakeAPI/loader.py") is False
        assert git_filter("scripts/archived/old.py") is False
        assert git_filter("alembic/versions/abc.py") is False

    def test_known_source_files_pass(self) -> None:
        """End-to-end: a comment mentioning known source files should
        extract those files."""
        from touch_index.comment_extractor import extract_files_from_text
        text = (
            "Modified `src/touch_index/comment_extractor.py` and "
            "`src/touch_index/git_extractor.py`"
        )
        paths = extract_files_from_text(text)
        assert "src/touch_index/comment_extractor.py" in paths
        assert "src/touch_index/git_extractor.py" in paths

    def test_lakeapi_excluded_as_in_git_extraction(self) -> None:
        """End-to-end: scripts/LakeAPI files are excluded from comment
        extraction, matching git extraction behavior."""
        from touch_index.git_extractor import _is_source_file
        from touch_index.comment_extractor import extract_files_from_text
        path = "scripts/LakeAPI/main.py"
        assert _is_source_file(path) is False, (
            "git_extractor._is_source_file must reject this path"
        )
        paths = extract_files_from_text(f"Changed `{path}`")
        assert paths == [], (
            "extract_files_from_text must exclude paths rejected by _is_source_file"
        )
