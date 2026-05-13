"""
Regression tests for BTCAAAAA-1559: close HTTP sessions and deduplicate auth
in bug-close ingestion worker.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1559
Fixed in commits: d76216e, 2f1d3abf
Components: src/touch_index/paperclip_client.py
            src/touch_index/comment_extractor.py
            src/touch_index/bug_worker.py

Root cause: _session() usages in paperclip_client created one-shot
requests.Session objects without context-manager cleanup, leaving
connection pools unreleased after each API call.  Additionally,
comment_extractor.fetch_and_extract() used inline os.environ reads
and raw requests.get() instead of the shared paperclip_client session
factory, duplicating auth configuration.

This file verifies:
  1. paperclip_client functions use `with _session() as sess:` context
     manager pattern so sessions are properly released
  2. comment_extractor reuses paperclip_client imports (no inline env reads)
  3. bug_worker module docstring reflects broadened scope
"""
from __future__ import annotations

import ast
import dis
import inspect
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1559"),
    pytest.mark.regression,
]

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# paperclip_client — session cleanup via context manager pattern
# ---------------------------------------------------------------------------


class TestSessionContextManagerUsage:
    """Verify paperclip_client functions use `with _session()` context manager."""

    def test_paginate_uses_with_session(self) -> None:
        """_paginate must use `with _session() as sess:` context manager."""
        from touch_index.paperclip_client import _paginate

        instructions = [i.opname for i in dis.Bytecode(_paginate)]
        assert "SETUP_WITH" in instructions or "WITH_EXCEPT_START" in instructions, (
            "SETUP_WITH/WITH_EXCEPT_START not found — _paginate may not use context manager"
        )

    def test_get_issue_by_id_uses_with_session(self) -> None:
        """get_issue_by_id must use `with _session() as sess:`."""
        from touch_index.paperclip_client import get_issue_by_id

        instructions = [i.opname for i in dis.Bytecode(get_issue_by_id)]
        assert "SETUP_WITH" in instructions or "WITH_EXCEPT_START" in instructions, (
            "get_issue_by_id missing context manager — sessions may leak"
        )

    def test_transition_issue_status_uses_with_session(self) -> None:
        """transition_issue_status must use `with _session() as sess:`."""
        from touch_index.paperclip_client import transition_issue_status

        instructions = [i.opname for i in dis.Bytecode(transition_issue_status)]
        assert "SETUP_WITH" in instructions or "WITH_EXCEPT_START" in instructions, (
            "transition_issue_status missing context manager — sessions may leak"
        )

    def test_fetch_issue_comments_uses_with_session(self) -> None:
        """fetch_issue_comments must use `with _session() as sess:`."""
        from touch_index.paperclip_client import fetch_issue_comments

        instructions = [i.opname for i in dis.Bytecode(fetch_issue_comments)]
        assert "SETUP_WITH" in instructions or "WITH_EXCEPT_START" in instructions, (
            "fetch_issue_comments missing context manager"
        )

    def test_list_live_runs_uses_with_session(self) -> None:
        """list_live_runs must use `with _session() as sess:`."""
        from touch_index.paperclip_client import list_live_runs

        instructions = [i.opname for i in dis.Bytecode(list_live_runs)]
        assert "SETUP_WITH" in instructions or "WITH_EXCEPT_START" in instructions, (
            "list_live_runs missing context manager"
        )

    def test_cancel_heartbeat_run_uses_board_session(self) -> None:
        """cancel_heartbeat_run must use `with _board_session() as sess:`."""
        from touch_index.paperclip_client import cancel_heartbeat_run

        instructions = [i.opname for i in dis.Bytecode(cancel_heartbeat_run)]
        assert "SETUP_WITH" in instructions or "WITH_EXCEPT_START" in instructions, (
            "cancel_heartbeat_run missing context manager"
        )

    def test_list_issues_uses_with_session(self) -> None:
        """list_issues must use `with _session() as sess:`."""
        from touch_index.paperclip_client import list_issues

        instructions = [i.opname for i in dis.Bytecode(list_issues)]
        assert "SETUP_WITH" in instructions or "WITH_EXCEPT_START" in instructions, (
            "list_issues missing context manager"
        )

    def test_transition_issue_status_board_uses_board_session(self) -> None:
        """transition_issue_status_board must use `with _board_session()`."""
        from touch_index.paperclip_client import transition_issue_status_board

        instructions = [i.opname for i in dis.Bytecode(transition_issue_status_board)]
        assert "SETUP_WITH" in instructions or "WITH_EXCEPT_START" in instructions, (
            "transition_issue_status_board missing context manager"
        )

    def test_force_release_issue_uses_board_session(self) -> None:
        """force_release_issue must use `with _board_session() as sess:`."""
        from touch_index.paperclip_client import force_release_issue

        instructions = [i.opname for i in dis.Bytecode(force_release_issue)]
        assert "SETUP_WITH" in instructions or "WITH_EXCEPT_START" in instructions, (
            "force_release_issue missing context manager"
        )

    def test_fetch_issue_comments_uses_with_session_imported(self) -> None:
        """fetch_issue_comments uses `with _session() as sess:` (confirm)."""
        from touch_index.paperclip_client import fetch_issue_comments

        instructions = [i.opname for i in dis.Bytecode(fetch_issue_comments)]
        assert "SETUP_WITH" in instructions or "WITH_EXCEPT_START" in instructions


class TestPaperclipClientFunctionsExist:
    """All paperclip_client public functions must be importable and callable."""

    def test_session_factory_callable(self) -> None:
        from touch_index.paperclip_client import _session
        assert callable(_session)

    def test_board_session_factory_callable(self) -> None:
        from touch_index.paperclip_client import _board_session
        assert callable(_board_session)

    def test_paginate_callable(self) -> None:
        from touch_index.paperclip_client import _paginate
        assert callable(_paginate)

    def test_get_issue_by_id_callable(self) -> None:
        from touch_index.paperclip_client import get_issue_by_id
        assert callable(get_issue_by_id)

    def test_transition_issue_status_callable(self) -> None:
        from touch_index.paperclip_client import transition_issue_status
        assert callable(transition_issue_status)

    def test_fetch_issue_comments_callable(self) -> None:
        from touch_index.paperclip_client import fetch_issue_comments
        assert callable(fetch_issue_comments)


class TestSessionSupportsContextManager:
    """_session() / _board_session() return objects usable as context managers."""

    def test_session_supports_context_manager(self) -> None:
        """_session() result has __enter__ and __exit__ (context manager)."""
        from touch_index.paperclip_client import _session

        sess = _session()
        try:
            assert hasattr(sess, "__enter__")
            assert hasattr(sess, "__exit__")
            assert hasattr(sess, "close")
            assert callable(sess.close)
        finally:
            sess.close()

    def test_board_session_supports_context_manager(self) -> None:
        """_board_session() result has __enter__ and __exit__."""
        from touch_index.paperclip_client import _board_session

        sess = _board_session()
        try:
            assert hasattr(sess, "__enter__")
            assert hasattr(sess, "__exit__")
            assert hasattr(sess, "close")
            assert callable(sess.close)
        finally:
            sess.close()


# ---------------------------------------------------------------------------
# comment_extractor — deduplicated auth (no inline env reads)
# ---------------------------------------------------------------------------


class TestCommentExtractorAuthDedup:
    """fetch_and_extract must reuse paperclip_client, not inline env reads."""

    def test_fetch_and_extract_source_does_not_use_inline_os_environ(self) -> None:
        """fetch_and_extract must NOT contain inline os.environ reads."""
        from touch_index.comment_extractor import fetch_and_extract

        src = inspect.getsource(fetch_and_extract)
        assert "os.environ" not in src, (
            "fetch_and_extract contains inline os.environ — must import "
            "paperclip_client helpers instead"
        )

    def test_fetch_and_extract_imports_from_paperclip_client(self) -> None:
        """fetch_and_extract must import from paperclip_client."""
        from touch_index.comment_extractor import fetch_and_extract

        src = inspect.getsource(fetch_and_extract)
        assert "paperclip_client" in src, (
            "fetch_and_extract missing paperclip_client import"
        )

    def test_fetch_and_extract_callable(self) -> None:
        from touch_index.comment_extractor import fetch_and_extract
        assert callable(fetch_and_extract)

    def test_extract_files_from_text_callable(self) -> None:
        from touch_index.comment_extractor import extract_files_from_text
        assert callable(extract_files_from_text)

    def test_extract_files_from_comments_callable(self) -> None:
        from touch_index.comment_extractor import extract_files_from_comments
        assert callable(extract_files_from_comments)


# ---------------------------------------------------------------------------
# bug_worker — updated module docstring
# ---------------------------------------------------------------------------


class TestBugWorkerDocstring:
    """bug_worker module docstring must reflect broadened scope post-fix."""

    def test_docstring_mentions_all_done_non_fdr(self) -> None:
        """Docstring must mention 'all done non-FDR' (broadened scope)."""
        import touch_index.bug_worker as bw

        assert bw.__doc__ is not None
        assert "non-FDR" in bw.__doc__, (
            "bug_worker docstring must mention 'non-FDR' — scope broadened in fix"
        )

    def test_docstring_mentions_fix_type_commits(self) -> None:
        """Docstring must mention fix-type commits pattern."""
        import touch_index.bug_worker as bw

        assert bw.__doc__ is not None
        assert "fix" in bw.__doc__.lower(), (
            "bug_worker docstring must mention fix-type commits"
        )

    def test_bug_worker_module_importable(self) -> None:
        import touch_index.bug_worker as bw
        assert bw is not None

    def test_ingest_bug_issue_callable(self) -> None:
        from touch_index.bug_worker import ingest_bug_issue
        assert callable(ingest_bug_issue)

    def test_process_bug_issue_callable(self) -> None:
        from touch_index.bug_worker import process_bug_issue
        assert callable(process_bug_issue)

    def test_catch_up_eligible_bug_issues_callable(self) -> None:
        from touch_index.bug_worker import catch_up_eligible_bug_issues
        assert callable(catch_up_eligible_bug_issues)
