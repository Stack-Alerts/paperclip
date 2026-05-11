"""phase2_touch_index_deps

Revision ID: 20260511_phase2_touch_index_deps
Revises: 20260511_add_touch_index_tables
Create Date: 2026-05-11

Phase 2 schema additions for the Touch Index dependency graph.

Changes
-------
1. touch_index_file_deps — ADD COLUMN is_internal BOOLEAN NOT NULL DEFAULT FALSE
   The Phase 1 placeholder created this table without the is_internal flag that
   the Phase 2 extractor needs to distinguish intra-repo edges.  A DEFAULT FALSE
   is used so the ALTER is safe on any existing placeholder rows; after Phase 2
   starts, all rows are truncated+reinserted with the correct value.

   NOTE: The existing table uses a surrogate UUID PK + unique index on
   (source_file, dep_file).  The composite-PK form in the issue spec was the
   logical intent; the surrogate key is preserved here to avoid a full table
   rewrite and because JOIN patterns use file path columns, not the PK.

2. touch_index_file_deps — ADD partial index idx_tifd_dep_file_internal
   Filters to is_internal = TRUE edges only.  Blast-radius queries that want
   internal dep propagation use this index exclusively.

3. touch_index_file_deps_transitive — CREATE TABLE
   Materialised transitive closure table.  Truncated+reinserted by the Phase 2
   extractor on each refresh, so no append workload.  Composite PK on
   (source_file, dep_file) as spec'd; no surrogate key needed here because
   referential integrity to this table is not required.

Migration is idempotent (IF NOT EXISTS / IF EXISTS).
"""
import sqlalchemy as sa
from alembic import op

revision = "20260511_phase2_touch_index_deps"
down_revision = "20260511_add_touch_index_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ------------------------------------------------------------------
    # 1. Add is_internal to touch_index_file_deps
    #    DEFAULT FALSE handles any existing placeholder rows safely.
    # ------------------------------------------------------------------
    conn.execute(sa.text("""
        ALTER TABLE touch_index_file_deps
            ADD COLUMN IF NOT EXISTS is_internal BOOLEAN NOT NULL DEFAULT FALSE;
    """))

    # ------------------------------------------------------------------
    # 2. Partial index for internal-only dep lookups
    # ------------------------------------------------------------------
    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_tifd_dep_file_internal
            ON touch_index_file_deps(dep_file)
            WHERE is_internal = TRUE;
    """))

    # ------------------------------------------------------------------
    # 3. touch_index_file_deps_transitive
    #    Materialised transitive closure; composite PK is safe because
    #    the Phase 2 extractor owns this table exclusively.
    # ------------------------------------------------------------------
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS touch_index_file_deps_transitive (
            source_file   TEXT        NOT NULL,
            dep_file      TEXT        NOT NULL,
            min_depth     INT         NOT NULL,
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (source_file, dep_file)
        );
    """))

    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_tifdtr_dep_file
            ON touch_index_file_deps_transitive(dep_file);
    """))


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("DROP INDEX IF EXISTS idx_tifdtr_dep_file;"))
    conn.execute(sa.text("DROP TABLE IF EXISTS touch_index_file_deps_transitive;"))

    conn.execute(sa.text("DROP INDEX IF EXISTS idx_tifd_dep_file_internal;"))
    conn.execute(sa.text(
        "ALTER TABLE touch_index_file_deps DROP COLUMN IF EXISTS is_internal;"
    ))
