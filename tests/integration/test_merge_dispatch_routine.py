#!/usr/bin/env python3
"""Tests for merge-dispatch routine (Phase 4a).

Verifies that the routine correctly:
1. Finds in_review issues
2. Extracts Fix-SHA from comments
3. Skips issues whose SHA is unpushed or already merged
4. Creates and merges PRs
5. Handles errors and escalates failures
"""

from unittest.mock import MagicMock, patch

import pytest


class TestFixSHAPattern:
    """Test Fix-SHA extraction pattern."""

    def test_extract_fix_sha_valid(self):
        """Test extracting valid Fix-SHA from comment."""
        import sys
        from pathlib import Path

        # Add scripts to path
        repo_root = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(repo_root / "scripts"))

        from merge_dispatch_routine import FIX_SHA_PATTERN

        comment = "Some text\nFix-SHA: abc123def456abc123def456abc123def456abc1\nMore text"
        match = FIX_SHA_PATTERN.search(comment)
        assert match is not None
        assert match.group(1) == "abc123def456abc123def456abc123def456abc1"

    def test_extract_fix_sha_invalid(self):
        """Test that invalid SHA doesn't match."""
        import sys
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(repo_root / "scripts"))

        from merge_dispatch_routine import FIX_SHA_PATTERN

        comment = "Fix-SHA: not-a-valid-sha"
        match = FIX_SHA_PATTERN.search(comment)
        assert match is None

    def test_extract_fix_sha_requires_line_anchor(self):
        """Test that Fix-SHA must be on its own line."""
        import sys
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(repo_root / "scripts"))

        from merge_dispatch_routine import FIX_SHA_PATTERN

        comment = "Some prefix Fix-SHA: abc123def456abc123def456abc123def456abc1"
        match = FIX_SHA_PATTERN.search(comment)
        assert match is None


class TestFixSHACommentOrdering:
    """Regression tests for BTCAAAAA-39402 / BTCAAAAA-39162.

    Paperclip's ``/comments`` endpoint returns comments in *reverse*
    chronological order (newest first). ``extract_fix_sha_from_comments``
    must therefore walk the candidates in list order (which is
    "latest first" under the live API contract), NOT via
    ``reversed(candidates)`` which would surface a stale SHA older than
    the branch the agent most recently pushed.
    """

    def _load(self):
        import sys
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(repo_root / "scripts"))
        import merge_dispatch_routine

        return merge_dispatch_routine

    def test_picks_latest_sha_on_descending_comments(self):
        """When /comments returns newest-first, picks the newest reachable SHA.

        Mirrors the BTC-39162 comment timeline: the agent posted v4 SHA
        six times before v3 squash and v1 original — the dispatch routine
        must pick v4 (latest, on branch), not v3 (older, only reachable
        via the squash on main, which the OLD ``reversed()`` code would
        surface first because it walks oldest-first).
        """
        mod = self._load()
        v4_sha = "2f9021fb5304207c57ce9c780508805b5945ea96"
        v3_squash_sha = "6fe12e069393ffcc253ebb2f43240c93db87b81e"
        v1_sha = "231162eab096fe14f2fbc38e2f993f070313cdf0"

        # Live API order: newest first
        comments = [
            {"body": f"Fix-SHA: {v4_sha}"},  # newest
            {"body": f"Fix-SHA: {v4_sha}"},
            {"body": f"Fix-SHA: {v4_sha}"},
            {"body": f"Fix-SHA: {v4_sha}"},
            {"body": f"Fix-SHA: {v4_sha}"},
            {"body": f"Fix-SHA: {v4_sha}"},  # oldest v4 mention
            {"body": f"Fix-SHA: {v3_squash_sha}"},
            {"body": "PR opened for v3"},
            {"body": "review path explanation"},
            {"body": "orphan sweep comment"},
            {"body": f"Fix-SHA: {v1_sha}"},  # oldest = first agent claim
        ]

        # v4 is on the fix branch (latest push). v3 squash is on main
        # and ``find_branch_for_sha`` treats main-as-branch as reachable.
        # v1 was force-pushed away — not reachable.
        #
        # OLD ``reversed()`` code walks candidates from oldest to newest
        # and returns v3 (the first reachable hit). NEW code walks
        # deduped candidates from newest to oldest and returns v4.
        with patch.object(mod, "find_branch_for_sha") as mock_find:
            mock_find.side_effect = lambda sha: {
                v4_sha: "fix/BTCAAAAA-39162",
                v3_squash_sha: "main",  # squash reachable via main
            }.get(sha)
            result = mod.extract_fix_sha_from_comments(comments)

        assert result == v4_sha, (
            f"Expected v4 ({v4_sha}) reachable on fix branch; got {result}"
        )

    def test_dedupes_repeated_sha_mentions(self):
        """Repeated Fix-SHA mentions collapse to a single candidate entry.

        Agents often re-post the same Fix-SHA in retry attempts. Iterating
        deduped (preserving first occurrence) keeps the loop linear in
        distinct SHAs and avoids ``re-checking the same branch 6×``.
        """
        mod = self._load()
        v4_sha = "a" * 40

        comments = [{"body": f"Fix-SHA: {v4_sha}"} for _ in range(6)]

        with patch.object(mod, "find_branch_for_sha", return_value=None) as mock_find:
            result = mod.extract_fix_sha_from_comments(comments)

        # No SHA reachable → fall back to first mention
        assert result == v4_sha
        # Single distinct SHA → single branch lookup
        assert mock_find.call_count == 1

    def test_falls_back_to_first_when_no_sha_reachable(self):
        """When no candidate SHA resolves to a branch, falls back to first mention.

        The first comment in list order (newest under the live API) is
        the "latest mention" — that is the legacy fallback semantics.
        """
        mod = self._load()
        newest_sha = "b" * 40
        older_sha = "c" * 40

        # Newest-first order: newest_sha appears first
        comments = [
            {"body": f"Fix-SHA: {newest_sha}"},
            {"body": f"Fix-SHA: {older_sha}"},
        ]

        with patch.object(mod, "find_branch_for_sha", return_value=None):
            result = mod.extract_fix_sha_from_comments(comments)

        assert result == newest_sha, (
            "Falls back to the FIRST entry in list order, which under the "
            "live API contract is the newest mention"
        )

    def test_picks_latest_reachable_over_earlier_unreachable(self):
        """Within descending-order comments, finds the latest reachable SHA.

        Picks the first occurrence (in list order) that resolves to a
        remote branch — not the oldest reachable, and not just the oldest
        candidate period (which would be the very last entry).
        """
        mod = self._load()
        v4_sha = "d" * 40
        orphan_sha = "e" * 40  # not on any branch
        v1_sha = "f" * 40      # not on any branch

        # Newest-first API order: v4 at index 0, v1 at index -1
        comments = [
            {"body": f"Fix-SHA: {v4_sha}"},  # newest, reachable
            {"body": f"Fix-SHA: {orphan_sha}"},  # middle, not reachable
            {"body": f"Fix-SHA: {v1_sha}"},  # oldest, not reachable
        ]

        with patch.object(mod, "find_branch_for_sha") as mock_find:
            mock_find.side_effect = lambda sha: (
                f"fix/BTCAAAAA-39162" if sha == v4_sha else None
            )
            result = mod.extract_fix_sha_from_comments(comments)

        assert result == v4_sha
        # Loop short-circuits at first reachable hit (v4 at index 0)
        assert mock_find.call_count == 1
        # The single lookup is for v4, not for the later orphan/v1 entries
        assert mock_find.call_args.args[0] == v4_sha


class TestMergeGate:
    """Test that the routine acts on Fix-SHA without an interaction gate."""

    def _load(self):
        import sys
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(repo_root / "scripts"))
        import merge_dispatch_routine

        return merge_dispatch_routine

    def test_skip_when_no_fix_sha(self):
        """An in_review issue with no Fix-SHA is skipped, not failed."""
        mod = self._load()
        issue = {"id": "id", "identifier": "BTCAAAAA-1", "status": "in_review"}
        with patch.object(mod, "fetch_issue_comments", return_value=[]):
            result = mod.process_issue(issue)
        assert result == {"issue": "BTCAAAAA-1", "action": "skip", "reason": "no_fix_sha"}

    def test_skip_when_sha_not_pushed(self):
        """A Fix-SHA that is neither local nor fetchable is skipped as push lag."""
        mod = self._load()
        sha = "a" * 40
        issue = {"id": "id", "identifier": "BTCAAAAA-2", "status": "in_review"}
        with patch.object(mod, "fetch_issue_comments", return_value=[{"body": f"Fix-SHA: {sha}"}]), \
            patch.object(mod, "sha_exists_locally", return_value=False), \
            patch.object(mod, "fetch_sha_from_remote", return_value=False):
            result = mod.process_issue(issue)
        assert result["action"] == "skip"
        assert result["reason"] == "sha_not_pushed"

    def test_skip_when_already_merged(self):
        """A Fix-SHA already on origin/main is skipped as already_merged."""
        mod = self._load()
        sha = "b" * 40
        issue = {"id": "id", "identifier": "BTCAAAAA-3", "status": "in_review"}
        with patch.object(mod, "fetch_issue_comments", return_value=[{"body": f"Fix-SHA: {sha}"}]), \
            patch.object(mod, "sha_exists_locally", return_value=True), \
            patch.object(mod, "is_ancestor_of_main", return_value=True):
            result = mod.process_issue(issue)
        assert result["action"] == "skip"
        assert result["reason"] == "already_merged"

    def test_skip_when_branch_not_pushed(self):
        """A Fix-SHA present locally but on no remote branch is skipped as push lag."""
        mod = self._load()
        sha = "c" * 40
        issue = {"id": "id", "identifier": "BTCAAAAA-4", "status": "in_review"}
        with patch.object(mod, "fetch_issue_comments", return_value=[{"body": f"Fix-SHA: {sha}"}]), \
            patch.object(mod, "sha_exists_locally", return_value=True), \
            patch.object(mod, "is_ancestor_of_main", return_value=False), \
            patch.object(mod, "find_branch_for_sha", return_value=None), \
            patch.object(mod, "find_branch_by_issue_id", return_value=None):
            result = mod.process_issue(issue, dry_run=False)
        assert result["action"] == "skip"
        assert result["reason"] == "branch_not_pushed"

    def test_closes_directly_when_squash_merged(self):
        """Squash-merged SHA (byte-identity match) closes the issue directly.

        Regression guard for BTCAAAAA-38602: the old code posted a comment
        saying 'closure-gate will flip to done' but the closure-gate only
        processes *done* issues, causing an infinite wake loop. The fix closes
        the issue here instead.
        """
        mod = self._load()
        sha = "d" * 40
        issue = {"id": "id", "identifier": "BTCAAAAA-9", "status": "in_review"}
        with patch.object(mod, "fetch_issue_comments", return_value=[{"body": f"Fix-SHA: {sha}"}]), \
            patch.object(mod, "sha_exists_locally", return_value=True), \
            patch.object(mod, "is_ancestor_of_main", return_value=False), \
            patch.object(mod, "pre_dispatch_already_merged_check", return_value=(True, "byte-identity: all 1 file(s) match")), \
            patch.object(mod, "comment_on_issue") as mock_comment, \
            patch.object(mod, "update_issue_status") as mock_status:
            result = mod.process_issue(issue)
        assert result["action"] == "closed_squash_detected"
        assert result["reason"] == "already_merged_squash"
        mock_status.assert_called_once_with("id", "done")
        mock_comment.assert_called_once()


class TestAgentFinishDispatch:
    """Test the --issue agent-finish single-issue dispatch path (board opt2)."""

    def _load(self):
        import sys
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(repo_root / "scripts"))
        import merge_dispatch_routine

        return merge_dispatch_routine

    def test_dispatch_skips_non_in_review_issue(self):
        """A single issue that is not in_review is skipped, not processed."""
        mod = self._load()
        issue = {"id": "x", "identifier": "BTCAAAAA-5", "status": "in_progress"}
        with patch.object(mod, "fetch_issue", return_value=issue), \
            patch.object(mod, "process_issue") as proc:
            rc = mod.dispatch_for_issue("x")
        assert rc == 0
        proc.assert_not_called()

    def test_dispatch_processes_in_review_issue(self):
        """A single in_review issue is routed through process_issue."""
        mod = self._load()
        issue = {"id": "x", "identifier": "BTCAAAAA-6", "status": "in_review"}
        with patch.object(mod, "fetch_issue", return_value=issue), \
            patch.object(mod, "fetch_issue_comments", return_value=[{"body": "Fix-SHA: " + "a" * 40}]), \
            patch.object(mod, "process_issue", return_value={"issue": "BTCAAAAA-6", "action": "skip", "reason": "sha_not_pushed"}) as proc:
            rc = mod.dispatch_for_issue("x")
        assert rc == 0
        proc.assert_called_once_with(issue, dry_run=False)

    def test_main_routes_issue_flag(self):
        """main(['--issue', id]) delegates to dispatch_for_issue."""
        mod = self._load()
        with patch.object(mod, "dispatch_for_issue", return_value=0) as disp:
            rc = mod.main(["--issue", "abc"])
        assert rc == 0
        disp.assert_called_once_with("abc", dry_run=False)


class TestSessionManagement:
    """Test HTTP session cleanup."""

    def test_http_session_closes_on_success(self):
        """Test that HTTP session is closed after successful request."""
        import sys
        from pathlib import Path
        from unittest.mock import patch, MagicMock

        repo_root = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(repo_root / "scripts"))

        from merge_dispatch_routine import fetch_issue_comments

        mock_response = MagicMock()
        mock_response.json.return_value = []

        mock_session = MagicMock()
        mock_session.get.return_value = mock_response
        mock_session.close = MagicMock()

        with patch("merge_dispatch_routine.os.environ", {"PAPERCLIP_API_URL": "http://test"}):
            with patch("merge_dispatch_routine._http_session", return_value=mock_session):
                fetch_issue_comments("test-id")

                # Verify close was called
                mock_session.close.assert_called_once()

    def test_http_session_closes_on_exception(self):
        """Test that HTTP session is closed even on exception."""
        import sys
        from pathlib import Path
        from unittest.mock import patch, MagicMock

        repo_root = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(repo_root / "scripts"))

        from merge_dispatch_routine import fetch_issue_comments

        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("Test error")
        mock_session.close = MagicMock()

        with patch("merge_dispatch_routine.os.environ", {"PAPERCLIP_API_URL": "http://test"}):
            with patch("merge_dispatch_routine._http_session", return_value=mock_session):
                result = fetch_issue_comments("test-id")

                # Verify close was called even on exception
                mock_session.close.assert_called_once()
                assert result == []


class TestOutputFormat:
    """Test routine output format."""

    def test_output_contains_summary(self):
        """Test that output JSON contains required summary fields."""
        import sys
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(repo_root / "scripts"))

        # Mock find_in_review_issues to return empty list
        with patch("merge_dispatch_routine.find_in_review_issues", return_value=[]):
            from merge_dispatch_routine import main

            # Pass argv=[] explicitly so argparse doesn't pick up pytest's argv.
            result = main([])
            assert result == 0

    def test_result_action_types(self):
        """Test that process_issue returns valid action types."""
        import sys
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(repo_root / "scripts"))

        from merge_dispatch_routine import process_issue

        # Minimal issue with no Fix-SHA comment → skip
        issue = {
            "id": "test-id",
            "identifier": "BTCAAAAA-999",
            "status": "in_review",
        }

        with patch("merge_dispatch_routine.fetch_issue_comments", return_value=[]):
            result = process_issue(issue)

        assert result["action"] in ["skip", "failed", "error", "merged"]
        assert "issue" in result


class TestEscalationRouting:
    """Regression test for BTCAAAAA-36598: escalation comments must go to source issue, not BTCAAAAA-30033."""

    def _load(self):
        import sys
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(repo_root / "scripts"))
        import merge_dispatch_routine

        return merge_dispatch_routine

    def test_escalation_posts_to_source_issue_not_30033(self):
        """escalate_failure must post to issue_id (source), never to BTCAAAAA-30033."""
        mod = self._load()
        source_issue_id = "test-source-uuid-1234"
        calls = []

        def capture_comment(issue_id: str, body: str, idempotency_key=None) -> bool:
            calls.append({"issue_id": issue_id, "body": body, "key": idempotency_key})
            return True

        with patch.object(mod, "comment_on_issue", side_effect=capture_comment):
            mod.escalate_failure(source_issue_id, "BTCAAAAA-99999", "a" * 40, "Failed to merge PR #99")

        assert len(calls) == 1
        assert calls[0]["issue_id"] == source_issue_id, (
            f"Escalation posted to '{calls[0]['issue_id']}' instead of source issue '{source_issue_id}'"
        )
        # Must never post to the token-gap routine
        assert "30033" not in calls[0]["issue_id"], (
            "Escalation must NOT post to BTCAAAAA-30033 (token-gap routine)"
        )

    def test_escalation_includes_idempotency_key(self):
        """escalate_failure must pass a non-empty idempotency_key to prevent double-posting."""
        mod = self._load()
        calls = []

        def capture_comment(issue_id: str, body: str, idempotency_key=None) -> bool:
            calls.append({"issue_id": issue_id, "key": idempotency_key})
            return True

        with patch.object(mod, "comment_on_issue", side_effect=capture_comment):
            mod.escalate_failure("uuid-abc", "BTCAAAAA-77777", "b" * 40, "No valid GitHub token")

        assert calls[0]["key"], "idempotency_key must be set to prevent duplicate escalation comments"

    def test_process_issue_escalation_routes_to_source_on_pr_failure(self):
        """process_issue must escalate to source issue when PR creation fails."""
        mod = self._load()
        sha = "c" * 40
        issue = {"id": "source-issue-uuid", "identifier": "BTCAAAAA-55555", "status": "in_review"}
        escalated_to = []

        def capture_escalation(issue_id, identifier, sha, reason):
            escalated_to.append(issue_id)

        with patch.object(mod, "fetch_issue_comments", return_value=[{"body": f"Fix-SHA: {sha}"}]), \
             patch.object(mod, "sha_exists_locally", return_value=True), \
             patch.object(mod, "is_ancestor_of_main", return_value=False), \
             patch.object(mod, "find_branch_for_sha", return_value="fix/BTCAAAAA-55555"), \
             patch.object(mod, "resolve_gh_token", return_value="fake-token"), \
             patch.object(mod, "find_existing_pr", return_value=None), \
             patch.object(mod, "create_pr", return_value=None), \
             patch.object(mod, "escalate_failure", side_effect=capture_escalation):
            result = mod.process_issue(issue)

        assert result["action"] == "failed"
        assert escalated_to == ["source-issue-uuid"], (
            f"Escalation went to '{escalated_to}' instead of source issue 'source-issue-uuid'"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
