"""add_strategy_type

Revision ID: 20260215_add_strategy_type
Revises: 20260205_add_training_tables
Create Date: 2026-02-15

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260215_add_strategy_type'
down_revision = '20260205_001'
branch_labels = None
depends_on = None


def upgrade():
    """Add strategy_type column to strategy_versions table."""
    # Add strategy_type column with default 'Bullish'
    op.add_column('strategy_versions', 
                  sa.Column('strategy_type', sa.String(20), nullable=False, server_default='Bullish'))


def downgrade():
    """Remove strategy_type column from strategy_versions table."""
    op.drop_column('strategy_versions', 'strategy_type')
