"""Unit tests for touch_index.comment_extractor -- file path extraction from text.

All extraction logic is pure string processing; no external I/O needed.
"""

from __future__ import annotations

from touch_index.comment_extractor import (
    _normalise,
    extract_files_from_text,
)


# ---------------------------------------------------------------------------
# _normalise
# ---------------------------------------------------------------------------


class TestNormalise:
    def test_no_prefix(self):
        assert _normalise("src/foo.py") == "src/foo.py"

    def test_btc_engine_v3_prefix(self):
        assert _normalise("BTC_Engine_v3/src/foo.py") == "src/foo.py"

    def test_btc_trade_engine_prefix(self):
        assert _normalise("BTC-Trade-Engine-PaperClip/src/foo.py") == "src/foo.py"

    def test_projects_prefix(self):
        """projects/<name>/... must return the path after <name>."""
        assert _normalise("projects/my-project/src/foo.py") == "src/foo.py"

    def test_projects_deep_nesting(self):
        assert _normalise("projects/foo/bar/baz/src/x.py") == "bar/baz/src/x.py"

    def test_projects_no_nested_path(self):
        """projects/<name> alone returns just the name."""
        assert _normalise("projects/foo") == "foo"

    def test_unknown_prefix_unchanged(self):
        assert _normalise("some_random/src/foo.py") == "some_random/src/foo.py"

    def test_empty_string(self):
        assert _normalise("") == ""


# ---------------------------------------------------------------------------
# extract_files_from_text
# ---------------------------------------------------------------------------


class TestExtractFilesFromText:
    def test_backtick_path(self):
        files = extract_files_from_text("Changed `src/foo.py` to fix X")
        assert files == ["src/foo.py"]

    def test_backtick_with_project_prefix(self):
        """Backtick-wrapped paths with projects/ prefix are normalised."""
        files = extract_files_from_text(
            "Changed `projects/BTC-Engine/src/foo.py` in PR #12"
        )
        assert files == ["src/foo.py"]

    def test_bare_path(self):
        files = extract_files_from_text("Modified src/foo/bar.py")
        assert files == ["src/foo/bar.py"]

    def test_bare_path_with_project_prefix(self):
        """Bare paths with projects/ prefix are handled correctly."""
        files = extract_files_from_text("Modified projects/X/src/foo.py")
        assert files == ["src/foo.py"]

    def test_multiple_files_returned_sorted(self):
        files = extract_files_from_text(
            "Changed `src/b.py` and `src/a.py`"
        )
        assert files == ["src/a.py", "src/b.py"]

    def test_no_paths_returns_empty(self):
        files = extract_files_from_text("No file paths here")
        assert files == []

    def test_deduplicates(self):
        files = extract_files_from_text(
            "Changed `src/foo.py` and also `src/foo.py`"
        )
        assert files == ["src/foo.py"]

    def test_code_extensions_only(self):
        """Non-code extensions like .txt, .md should not be extracted."""
        files = extract_files_from_text("See `README.md` and `docs/guide.txt`")
        assert files == []

    def test_repo_prefix_in_backtick(self):
        files = extract_files_from_text("Fix in `BTC_Engine_v3/src/worker.py`")
        assert files == ["src/worker.py"]
