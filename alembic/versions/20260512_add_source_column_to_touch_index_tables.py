"""add_source_column_to_touch_index_tables

Revision ID: 20260512_add_source_column_to_touch_index_tables
Revises: 20260511_phase2_touch_index_deps
Create Date: 2026-05-12

Fixes a schema bug in the original 20260511_add_touch_index_tables
migration: both touch_index_fr_files and touch_index_bug_files were
created without a `source` TEXT column, but the ingestion workers
(and the documented schema) expect it.

Changes:
  - touch_index_fr_files  → ADD COLUMN source TEXT NOT NULL DEFAULT 'unknown'
  - touch_index_bug_files → ADD COLUMN source TEXT NOT NULL DEFAULT 'unknown'

The default 'unknown' ensures existing rows (if any) are backfilled
correctly.  After this migration, the application always sets source
explicitly on INSERT/upsert, so the default is only a safety net.
"""
from alembic import op
import sqlalchemy as sa

revision = "20260512_add_source_column_to_touch_index_tables"
down_revision = "20260511_phase2_touch_index_deps"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("""
        ALTER TABLE touch_index_fr_files
            ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'unknown';
    """))

    conn.execute(sa.text("""
        ALTER TABLE touch_index_bug_files
            ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'unknown';
    """))


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("""
        ALTER TABLE touch_index_fr_files DROP COLUMN IF EXISTS source;
    """))

    conn.execute(sa.text("""
        ALTER TABLE touch_index_bug_files DROP COLUMN IF EXISTS source;
    """))

