"""
Regression tests for BTCAAAAA-6877: reject bare filenames in source file extraction.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-6877
Fixed in commit: 94c08d75
Component: src/touch_index/git_extractor.py, src/touch_index/comment_extractor.py

Root cause: Bare filenames like ``backtest_config_panel.py`` from agent done-comments
were passing through because ``_is_source_file`` only had a blocklist (skip_prefixes,
skip_suffixes) but no allowlist.  Git-extracted paths are always repo-root-relative
(e.g. ``src/foo/bar.py``), so the allowlist only affects the comment-fallback and
description-fallback paths.

Impact: BTCAAAAA-1212 was adding 7 junk rows (bare filenames without directory
prefix) on every re-ingest.  After this fix those comments produce no file rows,
falling back to description/git instead.

Note: BTCAAAAA-7235 later moved the allowlist from ``_is_source_file`` (in
git_extractor.py) to ``_has_allowed_prefix`` (in comment_extractor.py) so that
git-extracted root-level ``.py`` files are not incorrectly rejected.
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-6877"),
    pytest.mark.regression,
]


# ---------------------------------------------------------------------------
# Bare filename rejection
# ---------------------------------------------------------------------------


class TestBareFilenameRejection:
    """Verify bare filenames (no directory prefix) are rejected from
    comment-extracted paths."""

    def test_bare_filename_backtick_rejected(self) -> None:
        """`backtest_config_panel.py` in backticks must not be extracted."""
        from touch_index.comment_extractor import extract_files_from_text

        paths = extract_files_from_text("Changed `backtest_config_panel.py`")
        assert paths == []

    def test_bare_filename_with_underscores_rejected(self) -> None:
        """`strategy_builder_panel.py` with underscores must not be extracted."""
        from touch_index.comment_extractor import extract_files_from_text

        paths = extract_files_from_text("Updated `strategy_builder_panel.py`")
        assert paths == []

    def test_bare_filename_with_numbers_rejected(self) -> None:
        """`config_v2.py` bare filename must not be extracted."""
        from touch_index.comment_extractor import extract_files_from_text

        paths = extract_files_from_text("Fixed `config_v2.py`")
        assert paths == []

    def test_bare_js_filename_rejected(self) -> None:
        """`.js` bare filenames must also be rejected."""
        from touch_index.comment_extractor import extract_files_from_text

        paths = extract_files_from_text("Updated `app.js`")
        assert paths == []

    def test_bare_ts_filename_rejected(self) -> None:
        """`.ts` bare filenames must also be rejected."""
        from touch_index.comment_extractor import extract_files_from_text

        paths = extract_files_from_text("Refactored `utils.ts`")
        assert paths == []

    def test_mixed_bare_and_valid_paths(self) -> None:
        """When text contains both bare filenames and valid prefixed paths,
        only the valid paths are extracted."""
        from touch_index.comment_extractor import extract_files_from_text

        text = (
            "Fixed `src/engine.py` and also checked `backtest_config_panel.py`"
        )
        paths = extract_files_from_text(text)
        assert paths == ["src/engine.py"]

    def test_multiple_bare_filenames_all_rejected(self) -> None:
        """Multiple bare filenames in one comment must all be rejected —
        this simulates the BTCAAAAA-1212 issue where 7 junk rows were created."""
        from touch_index.comment_extractor import extract_files_from_text

        text = (
            "Files: `backtest_config_panel.py`, `strategy_builder_panel.py`, "
            "`signal_config_panel.py`, `optimizer_config_panel.py`, "
            "`data_config_panel.py`, `trade_config_panel.py`, "
            "`report_config_panel.py`"
        )
        paths = extract_files_from_text(text)
        assert paths == [], (
            f"Expected 0 paths from bare filenames, got {paths}"
        )


# ---------------------------------------------------------------------------
# _has_allowed_prefix
# ---------------------------------------------------------------------------


class TestHasAllowedPrefix:
    """Direct unit tests for the ``_has_allowed_prefix`` guard that
    implements the allowlist originally added by BTCAAAAA-6877 and
    refactored by BTCAAAAA-7235."""

    def test_src_prefix_accepted(self) -> None:
        from touch_index.comment_extractor import _has_allowed_prefix

        assert _has_allowed_prefix("src/foo/bar.py") is True

    def test_tests_prefix_accepted(self) -> None:
        from touch_index.comment_extractor import _has_allowed_prefix

        assert _has_allowed_prefix("tests/test_foo.py") is True

    def test_scripts_prefix_accepted(self) -> None:
        from touch_index.comment_extractor import _has_allowed_prefix

        assert _has_allowed_prefix("scripts/run_worker.py") is True

    def test_bare_filename_rejected(self) -> None:
        from touch_index.comment_extractor import _has_allowed_prefix

        assert _has_allowed_prefix("backtest_config_panel.py") is False

    def test_alembic_prefix_rejected(self) -> None:
        """alembic/ is not in the allowlist — rejected by _has_allowed_prefix
        even before _is_source_file handles it."""
        from touch_index.comment_extractor import _has_allowed_prefix

        assert _has_allowed_prefix("alembic/versions/abc.py") is False

    def test_root_py_rejected(self) -> None:
        """A .py file at repo root without a src/ tests/ scripts/ prefix."""
        from touch_index.comment_extractor import _has_allowed_prefix

        assert _has_allowed_prefix("conftest.py") is False

    def test_docs_prefix_rejected(self) -> None:
        from touch_index.comment_extractor import _has_allowed_prefix

        assert _has_allowed_prefix("docs/conf.py") is False

    def test_github_prefix_rejected(self) -> None:
        from touch_index.comment_extractor import _has_allowed_prefix

        assert _has_allowed_prefix(".github/workflows/ci.py") is False


# ---------------------------------------------------------------------------
# _is_source_file does NOT reject bare filenames
# ---------------------------------------------------------------------------


class TestIsSourceFileBareFilename:
    """Verify that ``_is_source_file`` (as of BTCAAAAA-7235) no longer
    rejects bare filenames — the allowlist lives in ``comment_extractor``
    to avoid breaking git-extracted root-level ``.py`` files."""

    def test_bare_py_filename_passes_is_source_file(self) -> None:
        """A bare ``.py`` filename passes ``_is_source_file`` because the
        allowlist was moved out by BTCAAAAA-7235."""
        from touch_index.git_extractor import _is_source_file

        assert _is_source_file("backtest_config_panel.py") is True

    def test_root_level_py_passes_is_source_file(self) -> None:
        """Root-level .py files like ``conftest.py`` must pass
        ``_is_source_file`` so git extraction works correctly."""
        from touch_index.git_extractor import _is_source_file

        assert _is_source_file("conftest.py") is True


# ---------------------------------------------------------------------------
# Comment-extraction end-to-end
# ---------------------------------------------------------------------------


class TestCommentExtractionEndToEnd:
    """End-to-end tests: bare filenames are rejected but valid prefixed
    paths are still extracted correctly."""

    def test_valid_prefixed_paths_extracted(self) -> None:
        from touch_index.comment_extractor import extract_files_from_text

        text = "Changed `src/touch_index/git_extractor.py` to add allowlist"
        paths = extract_files_from_text(text)
        assert paths == ["src/touch_index/git_extractor.py"]

    def test_real_world_comment_pattern(self) -> None:
        """Simulates a real agent done-comment: valid paths extracted,
        bare filenames dropped."""
        from touch_index.comment_extractor import extract_files_from_text

        text = (
            "Done implementing the fix.\n\n"
            "Changed `src/touch_index/git_extractor.py` to add allowlist "
            "and also verified `backtest_config_panel.py` behavior.\n"
            "See `tests/test_touch_index/test_git_extractor.py` for tests."
        )
        paths = extract_files_from_text(text)
        assert "src/touch_index/git_extractor.py" in paths
        assert "tests/test_touch_index/test_git_extractor.py" in paths
        assert "backtest_config_panel.py" not in paths

    def test_bare_path_in_backtick_with_line_number_rejected(self) -> None:
        """Bare filename with line-number suffix in backticks is rejected."""
        from touch_index.comment_extractor import extract_files_from_text

        paths = extract_files_from_text("See `backtest_config_panel.py:42`")
        assert paths == []
