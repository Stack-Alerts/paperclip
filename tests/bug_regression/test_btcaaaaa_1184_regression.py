"""
Regression tests for BTCAAAAA-1184.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1184

Verifies that comment_extractor correctly extracts backtick-wrapped
file paths with line-number suffixes (e.g. `file.py:229-332`).
"""
from __future__ import annotations

import pytest

from touch_index.comment_extractor import extract_files_from_text

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1184"),
    pytest.mark.regression,
]


class TestBTCAAAAA1184Regression:
    """Regression tests for BTCAAAAA-1184."""

    def test_backtick_path_with_line_range(self) -> None:
        files = extract_files_from_text("See `src/foo.py:229-332` for details")
        assert files == ["src/foo.py"]

    def test_backtick_path_with_single_line(self) -> None:
        files = extract_files_from_text("Fixed in `src/bar.py:42`")
        assert files == ["src/bar.py"]

    def test_backtick_path_with_line_number_and_prefix(self) -> None:
        files = extract_files_from_text("Changed `BTC_Engine_v3/src/foo.py:10-20`")
        assert files == ["src/foo.py"]

    def test_backtick_path_without_line_number_still_works(self) -> None:
        files = extract_files_from_text("Changed `src/foo.py` to fix X")
        assert files == ["src/foo.py"]

    def test_multiple_files_mixed_line_numbers(self) -> None:
        files = extract_files_from_text("`src/a.py:10-20` and `src/b.py:30`")
        assert files == ["src/a.py", "src/b.py"]

    def test_non_matching_suffix_is_not_extracted(self) -> None:
        files = extract_files_from_text("Not a path: `src/foo.py:abc`")
        assert files == []

    def test_only_colon_with_no_digits_is_not_matched(self) -> None:
        files = extract_files_from_text("Edge `src/foo.py:` case")
        assert files == []
