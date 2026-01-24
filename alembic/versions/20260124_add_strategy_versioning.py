"""Add strategy versioning and AI recommendations

Revision ID: add_strategy_versioning
Revises: 
Create Date: 2026-01-24

SPRINT 1.6.1 - Phase 1: Database Infrastructure
Implements DATABASE-FIRST architecture for strategy management

New Tables:
1. strategies - Parent table for strategy tracking
2. strategy_versions - Complete versioned strategy configurations
3. strategy_block_versions - Block-level version tracking
4. ai_recommendations - AI recommendation history
5. strategy_test_results - Test results history

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = 'add_strategy_versioning'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create all strategy versioning tables"""
    
    # ========================================================================
    # TABLE 1: strategies (Parent table)
    # ========================================================================
    op.create_table(
        'strategies',
        sa.Column('strategy_id', sa.String(), nullable=False, comment='Unique strategy identifier'),
        sa.Column('name', sa.String(), nullable=False, comment='Strategy name'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'), comment='Creation timestamp'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'), comment='Last update timestamp'),
        sa.PrimaryKeyConstraint('strategy_id'),
        comment='Parent table for strategy tracking'
    )
    
    # Index for name searches
    op.create_index('idx_strategies_name', 'strategies', ['name'])
    op.create_index('idx_strategies_created_at', 'strategies', ['created_at'])
    
    # ========================================================================
    # TABLE 2: strategy_versions (Complete strategy data with versioning)
    # ========================================================================
    op.create_table(
        'strategy_versions',
        # Primary identification
        sa.Column('version_id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4, comment='Unique version identifier'),
        sa.Column('strategy_id', sa.String(), nullable=False, comment='Parent strategy ID'),
        sa.Column('version_number', sa.Integer(), nullable=False, comment='Version number (auto-increment per strategy)'),
        
        # Strategy metadata
        sa.Column('name', sa.String(), nullable=False, comment='Strategy name'),
        sa.Column('description', sa.Text(), comment='Strategy description'),
        
        # Complete strategy definition (JSONB for flexibility)
        sa.Column('blocks', postgresql.JSONB(), nullable=False, comment='Building blocks configuration'),
        sa.Column('signals', postgresql.JSONB(), nullable=False, comment='Signal configurations'),
        sa.Column('parameters', postgresql.JSONB(), nullable=False, comment='Strategy parameters'),
        sa.Column('entry_conditions', postgresql.JSONB(), nullable=False, comment='Entry logic'),
        sa.Column('exit_conditions', postgresql.JSONB(), nullable=False, comment='Exit logic'),
        sa.Column('risk_management', postgresql.JSONB(), nullable=False, comment='Risk management settings'),
        
        # Backtest configuration and results
        sa.Column('backtest_config', postgresql.JSONB(), nullable=False, comment='Backtest configuration'),
        sa.Column('backtest_results', postgresql.JSONB(), comment='Complete backtest results'),
        sa.Column('metrics', postgresql.JSONB(), comment='Performance metrics'),
        sa.Column('trades', postgresql.JSONB(), comment='Trade history'),
        sa.Column('equity_curve', postgresql.JSONB(), comment='Equity curve data'),
        
        # Version control and tracking
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'), comment='Version creation timestamp'),
        sa.Column('git_commit_hash', sa.String(), comment='Git commit hash for traceability'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'), comment='Record creation timestamp'),
        sa.Column('created_by', sa.String(), comment='User who created this version'),
        sa.Column('notes', sa.Text(), comment='Version notes/changelog'),
        sa.Column('tags', postgresql.JSONB(), comment='Tags for organization'),
        
        # Duplicate detection
        sa.Column('config_hash', sa.String(64), comment='SHA-256 hash for duplicate detection'),
        
        # Constraints
        sa.PrimaryKeyConstraint('version_id'),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.strategy_id'], ondelete='CASCADE'),
        sa.UniqueConstraint('strategy_id', 'version_number', name='uq_strategy_version'),
        
        comment='Versioned strategy configurations with complete data'
    )
    
    # Performance indexes
    op.create_index('idx_strategy_versions_strategy', 'strategy_versions', ['strategy_id'])
    op.create_index('idx_strategy_versions_timestamp', 'strategy_versions', ['timestamp'])
    op.create_index('idx_strategy_versions_hash', 'strategy_versions', ['config_hash'])
    op.create_index('idx_strategy_versions_version_num', 'strategy_versions', ['strategy_id', 'version_number'])
    
    # ========================================================================
    # TABLE 3: strategy_block_versions (Block-level tracking)
    # ========================================================================
    op.create_table(
        'strategy_block_versions',
        sa.Column('block_version_id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4, comment='Unique block version ID'),
        sa.Column('version_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Parent strategy version ID'),
        sa.Column('block_name', sa.String(), nullable=False, comment='Building block name'),
        sa.Column('block_type', sa.String(), nullable=False, comment='Block type/category'),
        sa.Column('signals', postgresql.JSONB(), nullable=False, comment='Block signals configuration'),
        sa.Column('parameters', postgresql.JSONB(), nullable=False, comment='Block parameters'),
        sa.Column('logic_type', sa.String(), nullable=False, comment='AND/OR logic'),
        sa.Column('sequence_number', sa.Integer(), comment='Block order in strategy'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'), comment='Creation timestamp'),
        
        sa.PrimaryKeyConstraint('block_version_id'),
        sa.ForeignKeyConstraint(['version_id'], ['strategy_versions.version_id'], ondelete='CASCADE'),
        
        comment='Block-level strategy version tracking'
    )
    
    # Indexes for block queries
    op.create_index('idx_block_versions_version', 'strategy_block_versions', ['version_id'])
    op.create_index('idx_block_versions_name', 'strategy_block_versions', ['block_name'])
    op.create_index('idx_block_versions_sequence', 'strategy_block_versions', ['version_id', 'sequence_number'])
    
    # ========================================================================
    # TABLE 4: ai_recommendations (AI recommendation tracking)
    # ========================================================================
    op.create_table(
        'ai_recommendations',
        sa.Column('recommendation_id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4, comment='Unique recommendation ID'),
        sa.Column('strategy_id', sa.String(), nullable=False, comment='Associated strategy ID'),
        sa.Column('version_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Associated version ID'),
        sa.Column('strategy_version', sa.String(), nullable=False, comment='Version string for display'),
        
        # Recommendation details
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'), comment='Recommendation timestamp'),
        sa.Column('recommendation_type', sa.String(), nullable=False, comment='Type: ADD_BLOCK, ADJUST_PARAMETER, etc.'),
        sa.Column('block_name', sa.String(), comment='Target block name'),
        sa.Column('signal_name', sa.String(), comment='Target signal name'),
        sa.Column('parameter_name', sa.String(), comment='Target parameter name'),
        sa.Column('configuration', postgresql.JSONB(), comment='Recommended configuration'),
        sa.Column('reasoning', sa.Text(), nullable=False, comment='AI reasoning text'),
        sa.Column('expected_impact', postgresql.JSONB(), comment='Expected impact metrics'),
        sa.Column('combined_confidence', sa.Float(), comment='Confidence score (0-1)'),
        sa.Column('root_cause', sa.Text(), comment='Root cause analysis'),
        sa.Column('warnings', postgresql.JSONB(), comment='Warning messages'),
        
        # AI metadata
        sa.Column('ai_enhanced', sa.Boolean(), default=False, comment='AI-enhanced recommendation flag'),
        
        # Application tracking
        sa.Column('applied', sa.Boolean(), default=False, comment='Whether recommendation was applied'),
        sa.Column('applied_at', sa.DateTime(), comment='Application timestamp'),
        sa.Column('metrics_before', postgresql.JSONB(), comment='Metrics before applying'),
        sa.Column('metrics_after', postgresql.JSONB(), comment='Metrics after applying'),
        
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'), comment='Record creation timestamp'),
        
        sa.PrimaryKeyConstraint('recommendation_id'),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.strategy_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['version_id'], ['strategy_versions.version_id'], ondelete='CASCADE'),
        
        comment='AI recommendation tracking and history'
    )
    
    # Indexes for recommendation queries
    op.create_index('idx_ai_recommendations_strategy', 'ai_recommendations', ['strategy_id'])
    op.create_index('idx_ai_recommendations_version', 'ai_recommendations', ['version_id'])
    op.create_index('idx_ai_recommendations_timestamp', 'ai_recommendations', ['timestamp'])
    op.create_index('idx_ai_recommendations_type', 'ai_recommendations', ['recommendation_type'])
    op.create_index('idx_ai_recommendations_applied', 'ai_recommendations', ['applied'])
    op.create_index('idx_ai_recommendations_strategy_version', 'ai_recommendations', ['strategy_id', 'strategy_version'])
    
    # ========================================================================
    # TABLE 5: strategy_test_results (Test results history)
    # ========================================================================
    op.create_table(
        'strategy_test_results',
        sa.Column('result_id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4, comment='Unique result ID'),
        sa.Column('strategy_id', sa.String(), nullable=False, comment='Associated strategy ID'),
        sa.Column('version_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Associated version ID'),
        
        # Test details
        sa.Column('test_type', sa.String(), nullable=False, comment='Test type: BACKTEST, LIVE_REPLAY, etc.'),
        sa.Column('metrics', postgresql.JSONB(), nullable=False, comment='Performance metrics'),
        sa.Column('trades', postgresql.JSONB(), comment='Trade history'),
        sa.Column('equity_curve', postgresql.JSONB(), comment='Equity curve data'),
        sa.Column('ai_recommendations', postgresql.JSONB(), comment='Linked AI recommendations'),
        
        # Timestamps
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'), comment='Test execution timestamp'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'), comment='Record creation timestamp'),
        
        sa.PrimaryKeyConstraint('result_id'),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.strategy_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['version_id'], ['strategy_versions.version_id'], ondelete='CASCADE'),
        
        comment='Strategy test results history'
    )
    
    # Indexes for test result queries
    op.create_index('idx_test_results_strategy', 'strategy_test_results', ['strategy_id'])
    op.create_index('idx_test_results_version', 'strategy_test_results', ['version_id'])
    op.create_index('idx_test_results_timestamp', 'strategy_test_results', ['timestamp'])
    op.create_index('idx_test_results_test_type', 'strategy_test_results', ['test_type'])
    op.create_index('idx_test_results_strategy_latest', 'strategy_test_results', ['strategy_id', 'timestamp'])


def downgrade():
    """Drop all strategy versioning tables in reverse order"""
    
    # Drop tables (reverse order of creation)
    op.drop_table('strategy_test_results')
    op.drop_table('ai_recommendations')
    op.drop_table('strategy_block_versions')
    op.drop_table('strategy_versions')
    op.drop_table('strategies')
