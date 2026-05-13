"""
Regression tests for BTCAAAAA-1167: Touch Index ingestion workers + 90-day backfill.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1167
Component: src/touch_index/, scripts/

Root cause: The Touch Index ingestion pipeline (FR worker, bug-close worker,
backfill, polling runners, git extractor, comment extractor, paperclip client,
and DB module) did not exist before this feature. BTCAAAAA-1167 introduced the
full stack.

These regression tests verify that all source files, scripts, and key
functions/constants are present and importable so the Impact Gate can confirm
the feature is intact.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1167"),
    pytest.mark.regression,
]

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# File existence — every file created by BTCAAAAA-1167 must exist
# ---------------------------------------------------------------------------

_SOURCE_FILES: list[tuple[str, str]] = [
    ("src/touch_index/__init__.py", "Package init"),
    ("src/touch_index/bug_worker.py", "Bug-close ingestion worker"),
    ("src/touch_index/fr_worker.py", "FR ingestion worker"),
    ("src/touch_index/comment_extractor.py", "Comment file-path extractor"),
    ("src/touch_index/db.py", "PostgreSQL engine factory"),
    ("src/touch_index/git_extractor.py", "Git history file extractor"),
    ("src/touch_index/paperclip_client.py", "Paperclip API client"),
]

_SCRIPT_FILES: list[tuple[str, str]] = [
    ("scripts/backfill_touch_index.py", "90-day backfill script"),
    ("scripts/run_touch_index_fr_worker.py", "FR polling runner"),
    ("scripts/run_touch_index_bug_worker.py", "Bug polling runner"),
]


class TestAllSourceFilesExist:
    @pytest.mark.parametrize("rel_path,_desc", _SOURCE_FILES)
    def test_source_file_exists(self, rel_path: str, _desc: str):
        path = REPO_ROOT / rel_path
        assert path.exists(), f"Source file missing: {rel_path}"

    @pytest.mark.parametrize("rel_path,_desc", _SCRIPT_FILES)
    def test_script_file_exists(self, rel_path: str, _desc: str):
        path = REPO_ROOT / rel_path
        assert path.exists(), f"Script file missing: {rel_path}"


# ---------------------------------------------------------------------------
# Module importability — every touch_index submodule must be importable
# ---------------------------------------------------------------------------

class TestModulesImportable:
    def test_touch_index_package_importable(self):
        import touch_index
        assert touch_index.__doc__ is not None

    def test_bug_worker_importable(self):
        from touch_index.bug_worker import ingest_bug_issue
        assert callable(ingest_bug_issue)

    def test_fr_worker_importable(self):
        from touch_index.fr_worker import ingest_fr_issue
        assert callable(ingest_fr_issue)

    def test_comment_extractor_importable(self):
        from touch_index.comment_extractor import extract_files_from_text
        assert callable(extract_files_from_text)

    def test_db_importable(self):
        from touch_index.db import get_engine, health_check
        assert callable(get_engine)
        assert callable(health_check)

    def test_git_extractor_importable(self):
        from touch_index.git_extractor import (
            get_commit_hashes,
            get_files_for_issue,
            get_all_referenced_issue_ids,
            _is_source_file,
        )
        assert callable(get_commit_hashes)
        assert callable(get_files_for_issue)
        assert callable(get_all_referenced_issue_ids)
        assert callable(_is_source_file)

    def test_paperclip_client_importable(self):
        from touch_index.paperclip_client import (
            FDR_LABEL_ID,
            get_issue_by_id,
            get_fdr_issues,
            get_closed_non_fdr_issues,
            fetch_issue_comments,
        )
        assert isinstance(FDR_LABEL_ID, str)
        assert len(FDR_LABEL_ID) > 0
        assert callable(get_issue_by_id)
        assert callable(get_fdr_issues)
        assert callable(get_closed_non_fdr_issues)
        assert callable(fetch_issue_comments)


# ---------------------------------------------------------------------------
# Key function availability across all worker/ingestion modules
# ---------------------------------------------------------------------------

class TestBugWorkerPublicApi:
    def test_ingest_bug_issue_exists(self):
        from touch_index.bug_worker import ingest_bug_issue, BugIngestionResult
        assert callable(ingest_bug_issue)
        assert BugIngestionResult is not None

    def test_process_bug_issue_exists(self):
        from touch_index.bug_worker import process_bug_issue
        assert callable(process_bug_issue)

    def test_catch_up_eligible_bug_issues_exists(self):
        from touch_index.bug_worker import catch_up_eligible_bug_issues
        assert callable(catch_up_eligible_bug_issues)


class TestFRWorkerPublicApi:
    def test_ingest_fr_issue_exists(self):
        from touch_index.fr_worker import ingest_fr_issue, FRIngestionResult
        assert callable(ingest_fr_issue)
        assert FRIngestionResult is not None

    def test_process_fr_issue_exists(self):
        from touch_index.fr_worker import process_fr_issue
        assert callable(process_fr_issue)

    def test_catch_up_eligible_fr_issues_exists(self):
        from touch_index.fr_worker import catch_up_eligible_fr_issues
        assert callable(catch_up_eligible_fr_issues)


# ---------------------------------------------------------------------------
# Comment extractor — key constants and extraction logic
# ---------------------------------------------------------------------------

class TestCommentExtractorConstants:
    def test_allow_prefixes_are_correct(self):
        from touch_index.comment_extractor import _ALLOW_PREFIXES
        assert "src/" in _ALLOW_PREFIXES
        assert "tests/" in _ALLOW_PREFIXES
        assert "scripts/" in _ALLOW_PREFIXES

    def test_extract_backtick_path(self):
        from touch_index.comment_extractor import extract_files_from_text
        text = "Changed `src/touch_index/bug_worker.py` and `src/touch_index/fr_worker.py`"
        paths = extract_files_from_text(text)
        assert "src/touch_index/bug_worker.py" in paths
        assert "src/touch_index/fr_worker.py" in paths

    def test_extract_bare_path(self):
        from touch_index.comment_extractor import extract_files_from_text
        text = "Modified src/optimizer_v3/database/strategy_manager.py"
        paths = extract_files_from_text(text)
        assert "src/optimizer_v3/database/strategy_manager.py" in paths

    def test_extract_filters_non_source(self):
        from touch_index.comment_extractor import extract_files_from_text
        text = "Updated README.md and docs/guide.md"
        paths = extract_files_from_text(text)
        assert len(paths) == 0

    def test_fetch_and_extract_exists(self):
        from touch_index.comment_extractor import fetch_and_extract
        assert callable(fetch_and_extract)


# ---------------------------------------------------------------------------
# Git extractor — source-file classification
# ---------------------------------------------------------------------------

class TestGitExtractorSourceFileFilter:
    def test_py_is_source(self):
        from touch_index.git_extractor import _is_source_file
        assert _is_source_file("src/foo/bar.py") is True

    def test_md_is_not_source(self):
        from touch_index.git_extractor import _is_source_file
        assert _is_source_file("README.md") is False

    def test_alembic_is_not_source(self):
        from touch_index.git_extractor import _is_source_file
        assert _is_source_file("alembic/versions/abc123.py") is False

    def test_github_workflow_is_not_source(self):
        from touch_index.git_extractor import _is_source_file
        assert _is_source_file(".github/workflows/ci.yml") is False

    def test_docs_are_not_source(self):
        from touch_index.git_extractor import _is_source_file
        assert _is_source_file("docs/guide.md") is False


# ---------------------------------------------------------------------------
# DB module — engine factory signature
# ---------------------------------------------------------------------------

class TestDbModule:
    def test_get_engine_accepts_pool_size(self):
        from touch_index.db import get_engine
        import inspect
        sig = inspect.signature(get_engine)
        assert "pool_size" in sig.parameters
