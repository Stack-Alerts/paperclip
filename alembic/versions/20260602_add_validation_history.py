"""Add validation_history column to strategy_versions

Revision ID: add_validation_history
Revises: 20260509_add_ai_readonly_role
Create Date: 2026-06-02

Persists the web-UI ValidationFixEvent audit trail so fix/undo history
survives across browser sessions (BTCAAAAA-33700).
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'add_validation_history'
down_revision = '20260509_add_ai_readonly_role'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'strategy_versions',
        sa.Column(
            'validation_history',
            postgresql.JSONB(),
            nullable=True,
            comment='Persisted fix/undo audit trail from ValidationReportWindow',
        ),
    )


def downgrade():
    op.drop_column('strategy_versions', 'validation_history')
