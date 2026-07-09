"""Tests for the centralized branch parser and ANSI stripper (BTCAAAAA-38473).

Gap 6 of the BTC-38306 merge-process checkup. The parser recognizes Paperclip
fix branches like ``fix/BTCAAAAA-38473-dispatch-polish`` and the stripper
removes CSI escape sequences from log text bound for Paperclip markdown.

Acceptance criteria:
- ``parse_branch`` returns the canonical dict shape for valid fix branches.
- ``parse_branch`` returns ``None`` for non-matching input (empty string, plain
  text, feature branches, chore/lock branches, malformed identifiers).
- ``parse_branch`` accepts an optional ``origin/`` prefix (from ``git branch -r
  --contains``).
- ``strip_ansi`` removes common CSI sequences used by Python ``logging`` color
  handlers without disturbing plain text.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import _merge_dispatch_branch_parser as bp  # noqa: E402


# ---------------------------------------------------------------------------
# parse_branch tests
# ---------------------------------------------------------------------------


def test_parse_branch_matches_canonical_fix_branch():
    result = bp.parse_branch("fix/BTCAAAAA-38473-dispatch-polish")
    assert result == {
        "identifier": "BTCAAAAA-38473",
        "slug": "dispatch-polish",
        "raw": "fix/BTCAAAAA-38473-dispatch-polish",
    }


def test_parse_branch_matches_identifier_only_no_slug():
    result = bp.parse_branch("fix/BTCAAAAA-12345")
    assert result == {
        "identifier": "BTCAAAAA-12345",
        "slug": "",
        "raw": "fix/BTCAAAAA-12345",
    }


def test_parse_branch_matches_single_word_slug():
    result = bp.parse_branch("fix/BTCAAAAA-38472-wait")
    assert result is not None
    assert result["identifier"] == "BTCAAAAA-38472"
    assert result["slug"] == "wait"


def test_parse_branch_accepts_origin_prefix():
    result = bp.parse_branch("origin/fix/BTCAAAAA-38473-dispatch-polish")
    assert result is not None
    assert result["identifier"] == "BTCAAAAA-38473"
    assert result["slug"] == "dispatch-polish"
    assert result["raw"] == "origin/fix/BTCAAAAA-38473-dispatch-polish"


def test_parse_branch_rejects_empty_string():
    assert bp.parse_branch("") is None


def test_parse_branch_rejects_feature_branch():
    assert bp.parse_branch("feat/BTCAAAAA-12345-thing") is None


def test_parse_branch_rejects_lock_branch():
    assert bp.parse_branch("lock/BTCAAAAA-12345-strategy-builder-lock") is None


def test_parse_branch_rejects_chore_branch():
    assert bp.parse_branch("chore/cleanup") is None


def test_parse_branch_rejects_malformed_identifier():
    assert bp.parse_branch("fix/BTC-12345") is None
    assert bp.parse_branch("fix/BTCAAAAA-abc") is None
    assert bp.parse_branch("fix/btcaaaaa-12345") is None


def test_parse_branch_rejects_plain_text():
    assert bp.parse_branch("hello world") is None
    assert bp.parse_branch("BTCAAAAA-12345") is None
    assert bp.parse_branch("main") is None


# ---------------------------------------------------------------------------
# strip_ansi tests
# ---------------------------------------------------------------------------


def test_strip_ansi_removes_color_code():
    assert bp.strip_ansi("\x1b[32mhello\x1b[0m") == "hello"


def test_strip_ansi_removes_multicolor_sequence():
    assert bp.strip_ansi("\x1b[31mred\x1b[0m and \x1b[34mblue\x1b[0m") == "red and blue"


def test_strip_ansi_removes_sequence_with_parameters():
    assert bp.strip_ansi("\x1b[1;33mbold-yellow\x1b[0m") == "bold-yellow"


def test_strip_ansi_passes_through_plain_text():
    assert bp.strip_ansi("no colors here") == "no colors here"


def test_strip_ansi_handles_empty_string():
    assert bp.strip_ansi("") == ""


def test_strip_ansi_removes_cursor_positioning():
    assert bp.strip_ansi("before\x1b[2Kafter") == "beforeafter"


# ---------------------------------------------------------------------------
# has_precompletion_marker tests (BTCAAAAA-39070)
# ---------------------------------------------------------------------------


def test_has_precompletion_marker_matches_anchor_line():
    body = (
        "## Pre-Completion Diff Warning\n"
        "\n"
        "Working tree in this issue's workspace has uncommitted changes..."
    )
    assert bp.has_precompletion_marker(body) is True


def test_has_precompletion_marker_matches_with_bold_wrapper():
    body = "**Pre-Completion Diff Warning** for issue BTCAAAAA-39070."
    assert bp.has_precompletion_marker(body) is True


def test_has_precompletion_marker_matches_with_underscore_wrapper():
    body = "_Pre-Completion Diff Warning_ — push your fix branch now."
    assert bp.has_precompletion_marker(body) is True


def test_has_precompletion_marker_matches_with_backtick_wrapper():
    body = "`Pre-Completion Diff Warning` posted by precompletion cron."
    assert bp.has_precompletion_marker(body) is True


def test_has_precompletion_marker_matches_leading_whitespace():
    body = "  Pre-Completion Diff Warning\n  Followed by body."
    assert bp.has_precompletion_marker(body) is True


def test_has_precompletion_marker_case_insensitive():
    body = "pre-completion diff warning — lowercase version."
    assert bp.has_precompletion_marker(body) is True


def test_has_precompletion_marker_rejects_mid_line_prose():
    body = "I posted a Pre-Completion Diff Warning earlier today."
    assert bp.has_precompletion_marker(body) is False


def test_has_precompletion_marker_rejects_unrelated_content():
    assert bp.has_precompletion_marker("nothing to see here") is False


def test_has_precompletion_marker_rejects_empty_or_none():
    assert bp.has_precompletion_marker("") is False
    assert bp.has_precompletion_marker(None) is False