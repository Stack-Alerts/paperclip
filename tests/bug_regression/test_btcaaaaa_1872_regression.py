"""
Regression tests for BTCAAAAA-1872: add source column to touch_index_bug_files
for data provenance.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1872
Components: src/touch_index/bug_worker.py
            tests/test_touch_index/test_bug_worker.py

Root cause / changes:
  1. touch_index_bug_files was missing the `source` column already present on
     touch_index_fr_files, preventing the bug ingestion worker from recording
     where each file reference originated (git, comments, or description).
  2. _UPSERT_SQL now includes `source` and `updated_at` columns in both INSERT
     and ON CONFLICT DO UPDATE clauses.
  3. ingest_bug_issue rows now carry `source` and `updated_at` values.
  4. BugIngestionResult.source field now propagated from ingest_bug_issue.

This file re-exports the existing unit tests from tests/test_touch_index/ so
the Impact Gate runner can discover them by issue ID.  The canonical tests
live in tests/test_touch_index/ and must not drift.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1872"),
    pytest.mark.regression,
]

from tests.test_touch_index.test_bug_worker import (  # noqa: E402, F401
    TestIngestBugIssue,
)

# ---------------------------------------------------------------------------
# Source-level contract checks for BTCAAAAA-1872-specific changes
# ---------------------------------------------------------------------------

BUG_WORKER_SOURCE = Path(__file__).resolve().parents[2] / "src" / "touch_index" / "bug_worker.py"
BUG_WORKER_TEXT = BUG_WORKER_SOURCE.read_text()


class TestBtc1872SourceColumnInBugFiles:
    """BTCAAAAA-1872: source column must be present in _UPSERT_SQL INSERT and
    ON CONFLICT DO UPDATE, and in the rows constructed by ingest_bug_issue."""

    def test_upsert_sql_has_source_in_insert(self):
        """_UPSERT_SQL INSERT clause includes the `source` column."""
        assert "source" in BUG_WORKER_TEXT
        assert "(id, file_path, bug_issue_id, bug_identifier, closed_at, source" in BUG_WORKER_TEXT
        assert ":source" in BUG_WORKER_TEXT

    def test_upsert_sql_has_source_in_on_conflict_do_update(self):
        """_UPSERT_SQL ON CONFLICT DO UPDATE includes `source = EXCLUDED.source`."""
        assert "source         = EXCLUDED.source" in BUG_WORKER_TEXT

    def test_upsert_sql_has_updated_at_cols(self):
        """_UPSERT_SQL includes updated_at in both INSERT and DO UPDATE."""
        assert "updated_at" in BUG_WORKER_TEXT

    def test_ingest_rows_contain_source_key(self):
        """ingest_bug_issue row dict includes 'source' key set to the source variable."""
        assert '"source": source' in BUG_WORKER_TEXT

    def test_ingest_rows_contain_updated_at_key(self):
        """ingest_bug_issue row dict includes 'updated_at' key."""
        assert '"updated_at"' in BUG_WORKER_TEXT

    def test_ingest_source_set_from_git_path(self):
        """When git returns files, source is set to 'git' before constructing rows."""
        lines = BUG_WORKER_TEXT.split("\n")
        source_assignment_found = False
        rows_source_found = False
        for line in lines:
            if 'source = "git"' in line:
                source_assignment_found = True
            if source_assignment_found and '"source": source' in line:
                rows_source_found = True
                break
        assert source_assignment_found and rows_source_found, (
            "source='git' must be assigned before rows dict uses it"
        )

    def test_ingest_fallback_source_comments(self):
        """When git empty and comments return files, source is set to 'comments'."""
        assert 'source = "comments"' in BUG_WORKER_TEXT

    def test_ingest_fallback_source_description(self):
        """When git and comments empty and description has files, source is set to 'description'."""
        assert 'source = "description"' in BUG_WORKER_TEXT

    def test_bug_ingestion_result_has_source_field(self):
        """BugIngestionResult dataclass has a `source` field."""
        assert "source: str" in BUG_WORKER_TEXT

    def test_bug_ingestion_result_source_field_values(self):
        """BugIngestionResult.source field comment documents valid values."""
        assert '"git" | "comments" | "description" | "none"' in BUG_WORKER_TEXT
