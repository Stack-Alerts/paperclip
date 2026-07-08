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