"""Tests for BTCAAAAA-38472 Gap 4: require_fix_sha_for_done_status lint.

The lint lives in scripts/closure_gate_routine.py and is imported by routines
that PATCH an issue to `done` (merge-dispatch routine + handler). It checks the
MOST RECENT comment for a line-anchored Fix-SHA (40-hex) OR the legacy
`Fix-SHA: NONE` exemption marker. When neither is present, the lint logs
`defer_missing_fix_sha` and returns False so callers skip the done PATCH.

Coverage:
  - most_recent_fix_sha_present: empty list, no marker, Fix-SHA in last comment,
    Fix-SHA in older comment (must NOT count), NONE exemption, NONE in older
    comment, mixed comments
  - log_defer_missing_fix_sha: emits the structured marker with routine + issue
  - require_fix_sha_for_done_status: pass/fail wiring with marker emit
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import closure_gate_routine as cgr  # noqa: E402


_SHA_A = "a" * 40
_SHA_B = "b" * 40


def _comment(body: str) -> dict:
    return {"body": body}


class TestMostRecentFixShaPresent:
    def test_empty_list_returns_false(self) -> None:
        assert cgr.most_recent_fix_sha_present([]) is False

    def test_no_fix_sha_in_any_comment_returns_false(self) -> None:
        comments = [
            _comment("Just some chatter"),
            _comment("Another non-SHA comment"),
        ]
        assert cgr.most_recent_fix_sha_present(comments) is False

    def test_fix_sha_in_latest_comment_returns_true(self) -> None:
        comments = [
            _comment("Older unrelated comment"),
            _comment(f"Fix-SHA: {_SHA_A}"),
        ]
        assert cgr.most_recent_fix_sha_present(comments) is True

    def test_fix_sha_only_in_older_comment_returns_false(self) -> None:
        """Only the chronologically-OLDEST Fix-SHA — must NOT count.

        The lint deliberately rejects old Fix-SHAs because they can refer
        to commits that were force-pushed away. The closure-gate's own
        extract_fix_sha_from_comments picks the LATEST reachable SHA, but
        the lint is stricter: only the freshest comment counts.
        """
        comments = [
            _comment(f"Fix-SHA: {_SHA_A}"),
            _comment("Latest comment, no SHA"),
        ]
        assert cgr.most_recent_fix_sha_present(comments) is False

    def test_none_exemption_in_latest_returns_true(self) -> None:
        comments = [
            _comment("Old comment"),
            _comment("Fix-SHA: NONE\nReason: manual reauth"),
        ]
        assert cgr.most_recent_fix_sha_present(comments) is True

    def test_none_exemption_in_older_returns_false(self) -> None:
        comments = [
            _comment("Fix-SHA: NONE"),
            _comment("Latest without marker"),
        ]
        assert cgr.most_recent_fix_sha_present(comments) is False

    def test_mixed_sha_then_other(self) -> None:
        """Fix-SHA in middle, then a non-SHA later comment — must defer."""
        comments = [
            _comment("Before SHA"),
            _comment(f"Fix-SHA: {_SHA_A}"),
            _comment("Latest is just commentary"),
        ]
        assert cgr.most_recent_fix_sha_present(comments) is False

    def test_invalid_sha_format_returns_false(self) -> None:
        """Short or non-hex SHA must NOT satisfy the lint."""
        comments = [
            _comment("Fix-SHA: abc123"),
            _comment("Fix-SHA: " + "g" * 40),
        ]
        assert cgr.most_recent_fix_sha_present(comments) is False

    def test_sha_in_code_block_matches(self) -> None:
        """Behavior parity with extract_fix_sha_from_comments: line-anchored
        regex matches even when the SHA lives inside a fenced code block.
        We document this explicitly so future changes stay coordinated with
        the rest of the Fix-SHA parsing infrastructure in this module.
        """
        comments = [
            _comment(f"```\nFix-SHA: {_SHA_A}\n```"),
        ]
        assert cgr.most_recent_fix_sha_present(comments) is True

    def test_latest_comment_with_only_whitespace_body(self) -> None:
        comments = [
            _comment(f"Fix-SHA: {_SHA_A}"),
            _comment("   \n   \n"),
        ]
        assert cgr.most_recent_fix_sha_present(comments) is False

    def test_sha_must_be_line_anchored(self) -> None:
        """`Some prefix Fix-SHA: <hex>` must NOT count — line must start with it."""
        comments = [
            _comment(f"prefix Fix-SHA: {_SHA_A}"),
        ]
        assert cgr.most_recent_fix_sha_present(comments) is False


class TestLogDeferMissingFixSha:
    def test_emits_structured_marker(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.INFO, logger="closure_gate"):
            cgr.log_defer_missing_fix_sha("merge_dispatch_routine", "BTCAAAAA-99999")
        marker = [r.message for r in caplog.records if "defer_missing_fix_sha" in r.message]
        assert marker, "Expected defer_missing_fix_sha log marker"
        assert "routine=merge_dispatch_routine" in marker[0]
        assert "issue=BTCAAAAA-99999" in marker[0]


class TestRequireFixShaForDoneStatus:
    def test_returns_true_when_marker_present(self) -> None:
        comments = [_comment(f"Fix-SHA: {_SHA_A}")]
        assert cgr.require_fix_sha_for_done_status(
            "merge_dispatch_routine", "BTCAAAAA-1", comments,
        ) is True

    def test_returns_false_and_logs_when_absent(
        self, caplog: pytest.LogCaptureFixture,
    ) -> None:
        comments = [_comment("Latest without marker")]
        with caplog.at_level(logging.INFO, logger="closure_gate"):
            result = cgr.require_fix_sha_for_done_status(
                "merge_dispatch_execution_handler", "BTCAAAAA-2", comments,
            )
        assert result is False
        marker = [r.message for r in caplog.records if "defer_missing_fix_sha" in r.message]
        assert marker
        assert "routine=merge_dispatch_execution_handler" in marker[0]
        assert "issue=BTCAAAAA-2" in marker[0]

    def test_returns_false_for_empty_comments(
        self, caplog: pytest.LogCaptureFixture,
    ) -> None:
        with caplog.at_level(logging.INFO, logger="closure_gate"):
            result = cgr.require_fix_sha_for_done_status(
                "merge_dispatch_routine", "BTCAAAAA-3", [],
            )
        assert result is False

    def test_none_marker_also_passes(self) -> None:
        comments = [_comment("Fix-SHA: NONE\nReason: routine pause")]
        assert cgr.require_fix_sha_for_done_status(
            "merge_dispatch_routine", "BTCAAAAA-4", comments,
        ) is True


class TestLinterCallsiteWiring:
    """Smoke tests confirming the lint import succeeds from both call sites.

    The handlers import `require_fix_sha_for_done_status` lazily (try/except
    with a fallback no-op). These tests confirm the canonical implementation
    is reachable when sys.path is set up like the production routines see it.
    """

    def test_closure_gate_routine_exposes_lint(self) -> None:
        assert hasattr(cgr, "require_fix_sha_for_done_status")
        assert callable(cgr.require_fix_sha_for_done_status)
        assert hasattr(cgr, "most_recent_fix_sha_present")
        assert hasattr(cgr, "log_defer_missing_fix_sha")