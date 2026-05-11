"""add_touch_index_tables

Revision ID: 20260511_add_touch_index_tables
Revises: 20260509_ai_consultant_audit
Create Date: 2026-05-11

Touch Index — three tables that track which files were touched by FRs, bugs,
and inter-file dependencies.  Migration is idempotent (CREATE TABLE IF NOT
EXISTS / CREATE INDEX IF NOT EXISTS) so it can be re-applied safely.

Schema decisions
----------------
* Every table gets a surrogate UUID PK via gen_random_uuid() for stable FK
  targets and row identity in audit trails.
* `updated_at` defaults to now() server-side; the application MUST update it
  on every upsert so stale-detection works correctly.
* `closed_at` on touch_index_bug_files is nullable — rows may be inserted
  before the bug is closed; the ingestion job sets this field on close.
* touch_index_file_deps is a Phase-2 placeholder.  The table is created now
  so the ingestion service has a stable join target.  An index on dep_file is
  added in addition to source_file for bidirectional dependency traversal
  (blast-radius queries need both directions).
* Composite UNIQUE constraints are modelled as unique indexes rather than
  inline table constraints so they can be created CONCURRENTLY in future
  if the table grows large.
"""
import sqlalchemy as sa
from alembic import op

revision = "20260511_add_touch_index_tables"
down_revision = "20260509_ai_consultant_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ------------------------------------------------------------------
    # 1. touch_index_fr_files
    #    Tracks which files were touched by each Feature Request issue.
    # ------------------------------------------------------------------
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS touch_index_fr_files (
            id                UUID        NOT NULL DEFAULT gen_random_uuid(),
            file_path         TEXT        NOT NULL,
            fr_issue_id       UUID        NOT NULL,
            fr_identifier     TEXT        NOT NULL,
            fr_owner_agent_id UUID        NOT NULL,
            updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (id)
        );
    """))

    conn.execute(sa.text("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_touch_fr_file_issue
            ON touch_index_fr_files (file_path, fr_issue_id);
    """))

    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_touch_fr_file_path
            ON touch_index_fr_files (file_path);
    """))

    # ------------------------------------------------------------------
    # 2. touch_index_bug_files
    #    Tracks which files were touched by each bug (closed issues).
    # ------------------------------------------------------------------
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS touch_index_bug_files (
            id             UUID        NOT NULL DEFAULT gen_random_uuid(),
            file_path      TEXT        NOT NULL,
            bug_issue_id   UUID        NOT NULL,
            bug_identifier TEXT        NOT NULL,
            closed_at      TIMESTAMPTZ,
            PRIMARY KEY (id)
        );
    """))

    conn.execute(sa.text("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_touch_bug_file_issue
            ON touch_index_bug_files (file_path, bug_issue_id);
    """))

    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_touch_bug_file_path
            ON touch_index_bug_files (file_path);
    """))

    # ------------------------------------------------------------------
    # 3. touch_index_file_deps  (Phase 2 placeholder)
    #    Will hold file-to-file dependency edges derived from import
    #    analysis.  Created now so ingestion service can join against it.
    # ------------------------------------------------------------------
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS touch_index_file_deps (
            id          UUID        NOT NULL DEFAULT gen_random_uuid(),
            source_file TEXT        NOT NULL,
            dep_file    TEXT        NOT NULL,
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (id)
        );
    """))

    conn.execute(sa.text("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_touch_dep_source_dep
            ON touch_index_file_deps (source_file, dep_file);
    """))

    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_touch_dep_source_file
            ON touch_index_file_deps (source_file);
    """))

    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_touch_dep_dep_file
            ON touch_index_file_deps (dep_file);
    """))


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("DROP INDEX IF EXISTS idx_touch_dep_dep_file;"))
    conn.execute(sa.text("DROP INDEX IF EXISTS idx_touch_dep_source_file;"))
    conn.execute(sa.text("DROP INDEX IF EXISTS uq_touch_dep_source_dep;"))
    conn.execute(sa.text("DROP TABLE IF EXISTS touch_index_file_deps;"))

    conn.execute(sa.text("DROP INDEX IF EXISTS idx_touch_bug_file_path;"))
    conn.execute(sa.text("DROP INDEX IF EXISTS uq_touch_bug_file_issue;"))
    conn.execute(sa.text("DROP TABLE IF EXISTS touch_index_bug_files;"))

    conn.execute(sa.text("DROP INDEX IF EXISTS idx_touch_fr_file_path;"))
    conn.execute(sa.text("DROP INDEX IF EXISTS uq_touch_fr_file_issue;"))
    conn.execute(sa.text("DROP TABLE IF EXISTS touch_index_fr_files;"))
