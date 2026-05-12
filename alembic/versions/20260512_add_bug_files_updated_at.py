"""add_bug_files_updated_at

Revision ID: 20260512_add_bug_files_updated_at
Revises: 20260512_add_bug_files_source_col
Create Date: 2026-05-12

Add updated_at column to touch_index_bug_files so the bug-close
ingestion worker can track when rows were last updated, mirroring
the updated_at column already present on touch_index_fr_files.
This enables proper freshness monitoring — without it, freshness
checks must rely on closed_at (the bug's closure date) rather than
when the row was actually updated by the worker.

Migration is idempotent (IF NOT EXISTS).
"""
import sqlalchemy as sa
from alembic import op

revision = "20260512_add_bug_files_updated_at"
down_revision = "20260512_add_source_column_to_touch_index_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        ALTER TABLE touch_index_bug_files
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
    """))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        ALTER TABLE touch_index_bug_files DROP COLUMN IF EXISTS updated_at;
    """))
