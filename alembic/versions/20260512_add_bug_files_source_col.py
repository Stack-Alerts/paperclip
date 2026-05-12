"""add_bug_files_source_col

Revision ID: 20260512_add_bug_files_source_col
Revises: 20260512_add_fr_files_source_col
Create Date: 2026-05-12

Add source column to touch_index_bug_files to track where file
references originated (git or comments). This improves data
provenance and debugging, mirroring the same column already
present on touch_index_fr_files.

Migration is idempotent (IF NOT EXISTS).
"""
import sqlalchemy as sa
from alembic import op

revision = "20260512_add_bug_files_source_col"
down_revision = "20260512_add_fr_files_source_col"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        ALTER TABLE touch_index_bug_files
            ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'unknown';
    """))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        ALTER TABLE touch_index_bug_files DROP COLUMN IF EXISTS source;
    """))
