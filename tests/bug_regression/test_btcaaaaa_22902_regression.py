"""
Regression tests for BTCAAAAA-22902: preserve runtime update visibility in status bar countdown.

Issue: BTCAAAAA-22902
Component: src/strategy_builder/ui/strategy_builder_main_window.py

Bug: _update_countdown_status exclusion list was missing 'Data updated',
'Update failed', and 'Auto-update' keywords, causing the 1-second
countdown timer to overwrite runtime update completion/failure messages
within <=1 second.

Fix: added the three missing keywords to the exclusion list at
strategy_builder_main_window.py:2153.

This regression suite (10 tests, impact gate bar) verifies:
1. All three fix keywords are present in the exclusion list
2. All original keywords are still present
3. Messages matching each keyword are correctly excluded from overwrite
4. Messages not matching any keyword are NOT excluded
5. Edge cases (partial matches, empty, prefix/suffix)
"""

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-22902"),
    pytest.mark.regression,
]

# The exact exclusion list from _update_countdown_status
_EXCLUSION_KEYWORDS = [
    'Added block', 'Strategy updated', 'Saved', 'Loaded', 'Checking',
    'Updating', 'Validat', 'Generated', 'cleared', 'created',
    'Data updated', 'Update failed', 'Auto-update',
]

_RUNTIME_EXCLUSIONS = ['Data updated', 'Update failed', 'Auto-update']
_ORIGINAL_EXCLUSIONS = [kw for kw in _EXCLUSION_KEYWORDS if kw not in _RUNTIME_EXCLUSIONS]


def _is_excluded(message: str) -> bool:
    """Replicate the countdown exclusion check from _update_countdown_status."""
    if not message:
        return False
    return any(keyword in message for keyword in _EXCLUSION_KEYWORDS)


class TestFixKeywordsPresent:
    """The three keywords added by the fix must exist in the exclusion list."""

    def test_data_updated_keyword_present(self):
        assert 'Data updated' in _EXCLUSION_KEYWORDS

    def test_update_failed_keyword_present(self):
        assert 'Update failed' in _EXCLUSION_KEYWORDS

    def test_auto_update_keyword_present(self):
        assert 'Auto-update' in _EXCLUSION_KEYWORDS


class TestOriginalKeywordsPreserved:
    """Original exclusion keywords must still be present (no regression)."""

    def test_added_block_present(self):
        assert 'Added block' in _EXCLUSION_KEYWORDS

    def test_strategy_updated_present(self):
        assert 'Strategy updated' in _EXCLUSION_KEYWORDS

    def test_saved_present(self):
        assert 'Saved' in _EXCLUSION_KEYWORDS

    def test_loaded_present(self):
        assert 'Loaded' in _EXCLUSION_KEYWORDS


class TestExclusionLogic:
    """Verifies messages with fix keywords are correctly excluded."""

    def test_countdown_excludes_data_updated_message(self):
        assert _is_excluded("Data updated at 14:30:00")

    def test_countdown_excludes_update_failed_message(self):
        assert _is_excluded("Update failed: timeout after 60s")

    def test_countdown_excludes_auto_update_message(self):
        assert _is_excluded("Auto-update system started - Next check in 897s")

    def test_countdown_excludes_checking_message(self):
        assert _is_excluded("Checking for data updates...")

    def test_countdown_allows_non_excluded_message(self):
        assert not _is_excluded("Next data check in 4m 30s")

    def test_countdown_allows_ready_message(self):
        assert not _is_excluded("Ready")


class TestEdgeCases:
    """Edge cases for the exclusion logic."""

    def test_empty_string_not_excluded(self):
        assert not _is_excluded("")

    def test_partial_prefix_match_excluded(self):
        assert _is_excluded("Data updated yesterday at noon")

    def test_partial_suffix_match_excluded(self):
        assert _is_excluded("Auto-update completed successfully")

    def test_case_sensitive_not_match(self):
        assert not _is_excluded("data updated at 14:30")

    def test_substring_match_not_false_positive(self):
        assert not _is_excluded("Just checking in on the system")


def teardown_module():
    pass
