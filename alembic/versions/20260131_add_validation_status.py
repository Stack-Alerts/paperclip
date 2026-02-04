"""Add validation status to strategy versions

Revision ID: 20260131_validation
Revises: 20260129_enhance_test_results
Create Date: 2026-01-31

Sprint 1.9 - Validation status persistence
Adds validation_status and validation_timestamp columns to strategy_versions
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260131_validation'
down_revision = '20260129_enhance_test_results'
branch_labels = None
depends_on = None


def upgrade():
    # Add validation_status column with default 'Un-Validated'
    op.add_column('strategy_versions', 
                  sa.Column('validation_status', sa.String(20), 
                           server_default='Un-Validated'))
    
    # Add validation_timestamp column
    op.add_column('strategy_versions', 
                  sa.Column('validation_timestamp', sa.DateTime(), nullable=True))


def downgrade():
    # Remove columns if migration is rolled back
    op.drop_column('strategy_versions', 'validation_timestamp')
    op.drop_column('strategy_versions', 'validation_status')
