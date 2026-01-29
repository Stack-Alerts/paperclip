"""Enhance strategy_test_results with additional columns

Revision ID: enhance_test_results
Revises: add_exit_conditions
Create Date: 2026-01-29

SPRINT 1.6.1 - Task 3.1: Test Results Manager ORM Enhancement

Adds missing columns to strategy_test_results table to support:
1. Test configuration tracking (test_config, start_date, end_date)
2. Fast metric queries (individual metric columns)
3. Extended tracking (risk_metrics, errors, warnings, notes)

Background:
- ORM model had these columns but they were never migrated
- Raw SQL in test_results_manager.py references these columns
- This migration aligns DB schema with ORM model and usage

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260129_enhance_test_results'
down_revision = '20260127_exit_conditions'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add missing columns to strategy_test_results
    
    Safe operation - all columns are nullable to allow existing rows
    """
    
    # ===================================================================
    # GROUP 1: Test Configuration and Period
    # ===================================================================
    
    op.add_column(
        'strategy_test_results',
        sa.Column(
            'test_config',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment='Test configuration (timeframe, symbols, etc.)'
        )
    )
    
    op.add_column(
        'strategy_test_results',
        sa.Column(
            'start_date',
            sa.DateTime(),
            nullable=True,
            comment='Test period start date'
        )
    )
    
    op.add_column(
        'strategy_test_results',
        sa.Column(
            'end_date',
            sa.DateTime(),
            nullable=True,
            comment='Test period end date'
        )
    )
    
    # ===================================================================
    # GROUP 2: Performance Metrics (for fast querying without parsing JSONB)
    # ===================================================================
    
    op.add_column(
        'strategy_test_results',
        sa.Column(
            'total_return_pct',
            sa.Float(),
            nullable=True,
            comment='Total return percentage'
        )
    )
    
    op.add_column(
        'strategy_test_results',
        sa.Column(
            'sharpe_ratio',
            sa.Float(),
            nullable=True,
            comment='Sharpe ratio'
        )
    )
    
    op.add_column(
        'strategy_test_results',
        sa.Column(
            'max_drawdown_pct',
            sa.Float(),
            nullable=True,
            comment='Maximum drawdown percentage'
        )
    )
    
    op.add_column(
        'strategy_test_results',
        sa.Column(
            'win_rate',
            sa.Float(),
            nullable=True,
            comment='Win rate (0.0 to 1.0)'
        )
    )
    
    op.add_column(
        'strategy_test_results',
        sa.Column(
            'profit_factor',
            sa.Float(),
            nullable=True,
            comment='Profit factor'
        )
    )
    
    op.add_column(
        'strategy_test_results',
        sa.Column(
            'total_trades',
            sa.Integer(),
            nullable=True,
            comment='Total number of trades'
        )
    )
    
    # ===================================================================
    # GROUP 3: Extended Tracking
    # ===================================================================
    
    op.add_column(
        'strategy_test_results',
        sa.Column(
            'risk_metrics',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment='Risk metrics (VaR, CVaR, etc.)'
        )
    )
    
    op.add_column(
        'strategy_test_results',
        sa.Column(
            'errors',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment='Error log during test execution'
        )
    )
    
    op.add_column(
        'strategy_test_results',
        sa.Column(
            'warnings',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment='Warning log during test execution'
        )
    )
    
    op.add_column(
        'strategy_test_results',
        sa.Column(
            'notes',
            sa.Text(),
            nullable=True,
            comment='Additional notes about test'
        )
    )
    
    # ===================================================================
    # INDEXES: For fast metric-based queries
    # ===================================================================
    
    # Index for filtering by performance
    op.create_index(
        'idx_test_results_sharpe',
        'strategy_test_results',
        ['sharpe_ratio'],
        postgresql_where=sa.text('sharpe_ratio IS NOT NULL')
    )
    
    op.create_index(
        'idx_test_results_return',
        'strategy_test_results',
        ['total_return_pct'],
        postgresql_where=sa.text('total_return_pct IS NOT NULL')
    )
    
    # Index for date range queries
    op.create_index(
        'idx_test_results_dates',
        'strategy_test_results',
        ['start_date', 'end_date']
    )
    
    # Composite index for version + metrics
    op.create_index(
        'idx_test_results_version_metrics',
        'strategy_test_results',
        ['version_id', 'sharpe_ratio', 'total_return_pct']
    )
    
    print("✅ Migration complete: strategy_test_results table enhanced")
    print("   - Added 14 new columns")
    print("   - Created 4 performance indexes")
    print("   - All columns nullable (safe for existing data)")


def downgrade():
    """
    Remove enhanced columns from strategy_test_results
    
    WARNING: This will delete data in these columns!
    """
    
    # Drop indexes first
    op.drop_index('idx_test_results_version_metrics', table_name='strategy_test_results')
    op.drop_index('idx_test_results_dates', table_name='strategy_test_results')
    op.drop_index('idx_test_results_return', table_name='strategy_test_results')
    op.drop_index('idx_test_results_sharpe', table_name='strategy_test_results')
    
    # Drop columns in reverse order
    op.drop_column('strategy_test_results', 'notes')
    op.drop_column('strategy_test_results', 'warnings')
    op.drop_column('strategy_test_results', 'errors')
    op.drop_column('strategy_test_results', 'risk_metrics')
    
    op.drop_column('strategy_test_results', 'total_trades')
    op.drop_column('strategy_test_results', 'profit_factor')
    op.drop_column('strategy_test_results', 'win_rate')
    op.drop_column('strategy_test_results', 'max_drawdown_pct')
    op.drop_column('strategy_test_results', 'sharpe_ratio')
    op.drop_column('strategy_test_results', 'total_return_pct')
    
    op.drop_column('strategy_test_results', 'end_date')
    op.drop_column('strategy_test_results', 'start_date')
    op.drop_column('strategy_test_results', 'test_config')
    
    print("⚠️ Downgrade complete: Removed 14 columns from strategy_test_results")
