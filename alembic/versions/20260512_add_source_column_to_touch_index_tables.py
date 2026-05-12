"""add_source_column_to_touch_index_tables (no-op)

This migration was superseded by the chain:
  20260512_add_fr_files_source_col -> 20260512_add_bug_files_source_col
which added source to each table individually.

This revision is preserved as a no-op so that databases which already
applied it (via the stale sibling chain) remain compatible.  New
databases will never reach this revision -- they follow the main chain.
"""
from alembic import op
import sqlalchemy as sa

revision = "20260512_add_source_column_to_touch_index_tables"
down_revision = "20260512_add_bug_files_source_col"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
