"""add exit conditions support

Revision ID: 20260127_exit_conditions
Revises: 20260124_add_strategy_versioning
Create Date: 2026-01-27 05:32:00

Sprint 1.8 Task 1.8.22: Database Schema for Exit Conditions
Adds columns for exit condition tracking and results
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260127_exit_conditions'
down_revision = 'add_strategy_versioning'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add exit condition support to database schema
    
    Changes:
    1. strategy_variations.exit_condition_triggers - Track exit condition trigger count (if table exists)
    2. strategy_test_results.exit_condition_results - Store detailed exit condition results
    
    Note: strategy_variations is optional (Sprint 0 optimizer tables)
    """
    
    # Check if strategy_variations table exists (Sprint 0 optimizer table)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    if 'strategy_variations' in tables:
        # Add exit_condition_triggers to strategy_variations
        op.add_column(
            'strategy_variations',
            sa.Column('exit_condition_triggers', sa.Integer(), nullable=True, server_default='0')
        )
        
        # Update existing rows to have default value for exit_condition_triggers
        op.execute("UPDATE strategy_variations SET exit_condition_triggers = 0 WHERE exit_condition_triggers IS NULL")
        
        # Make exit_condition_triggers non-nullable after setting defaults
        op.alter_column('strategy_variations', 'exit_condition_triggers', nullable=False)
    
    # Add exit_condition_results to strategy_test_results (Sprint 1.6.1 table)
    if 'strategy_test_results' in tables:
        op.add_column(
            'strategy_test_results',
            sa.Column('exit_condition_results', postgresql.JSONB(astext_type=sa.Text()), nullable=True)
        )


def downgrade():
    """
    Remove exit condition support from database schema
    """
    
    # Check if tables exist before dropping columns
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    # Remove columns in reverse order
    if 'strategy_test_results' in tables:
        op.drop_column('strategy_test_results', 'exit_condition_results')
    
    if 'strategy_variations' in tables:
        op.drop_column('strategy_variations', 'exit_condition_triggers')
