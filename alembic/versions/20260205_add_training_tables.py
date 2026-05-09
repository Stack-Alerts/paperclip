"""Add training tables

Revision ID: 20260205_001
Revises: 
Create Date: 2026-02-05 12:22:00

Sprint 2.1, Task 2.1.15: Database migration for training events
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260205_001'
down_revision = '20260131_validation'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create training_events table with all indexes
    
    Table stores historical signal analysis for optimal parameter calculation.
    """
    # Create training_events table
    op.create_table(
        'training_events',
        
        # Primary Key
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        
        # Signal Identification
        sa.Column('block_name', sa.String(length=100), nullable=False),
        sa.Column('signal_name', sa.String(length=100), nullable=False),
        sa.Column('timeframe', sa.String(length=10), nullable=False),
        
        # Timestamp
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        
        # Signal Entry Data
        sa.Column('entry_price', sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column('instrument', sa.String(length=20), nullable=False, server_default='BTC-USD'),
        
        # Forward Analysis Results
        sa.Column('max_favorable_move', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('max_adverse_move', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('final_move', sa.Numeric(precision=10, scale=6), nullable=True),
        
        # Volatility & Position Sizing
        sa.Column('volatility_atr', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('position_size', sa.Numeric(precision=18, scale=8), nullable=True),
        
        # Trade Outcome
        sa.Column('simulated_pnl', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('is_winning_trade', sa.Boolean(), nullable=True),
        
        # Price Impact
        sa.Column('price_impact_usd', sa.Numeric(precision=18, scale=2), nullable=True),
        
        # Analysis Window
        sa.Column('forward_bars', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('bars_to_max_favorable', sa.Integer(), nullable=True),
        sa.Column('bars_to_max_adverse', sa.Integer(), nullable=True),
        
        # Validation Flags
        sa.Column('is_valid_signal', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('has_sufficient_data', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('meets_min_criteria', sa.Boolean(), nullable=False, server_default='true'),
        
        # Statistical Metadata
        sa.Column('sample_group', sa.String(length=50), nullable=True),
        sa.Column('training_mode', sa.String(length=20), nullable=False),
        sa.Column('analysis_version', sa.String(length=20), nullable=True),
        
        # Additional Metadata
        sa.Column('notes', sa.Text(), nullable=True),
    )
    
    # Create indexes for performance
    
    # Single column indexes
    op.create_index('idx_training_block_name', 'training_events', ['block_name'])
    op.create_index('idx_training_signal_name', 'training_events', ['signal_name'])
    op.create_index('idx_training_timeframe', 'training_events', ['timeframe'])
    op.create_index('idx_training_timestamp', 'training_events', ['timestamp'])
    op.create_index('idx_training_created_at', 'training_events', ['created_at'])
    
    # Composite indexes for common queries
    op.create_index('idx_signal_timeframe', 'training_events', ['signal_name', 'timeframe'])
    op.create_index('idx_block_timeframe', 'training_events', ['block_name', 'timeframe'])
    op.create_index('idx_timestamp_signal', 'training_events', ['timestamp', 'signal_name'])
    
    # Index for validation queries
    op.create_index('idx_valid_signals', 'training_events', ['is_valid_signal', 'has_sufficient_data'])
    
    print("✅ Created training_events table with 9 indexes")


def downgrade() -> None:
    """
    Drop training_events table
    
    WARNING: This will delete all training data!
    """
    # Drop indexes first (implicit when dropping table, but explicit for clarity)
    op.drop_index('idx_valid_signals', table_name='training_events')
    op.drop_index('idx_timestamp_signal', table_name='training_events')
    op.drop_index('idx_block_timeframe', table_name='training_events')
    op.drop_index('idx_signal_timeframe', table_name='training_events')
    op.drop_index('idx_training_created_at', table_name='training_events')
    op.drop_index('idx_training_timestamp', table_name='training_events')
    op.drop_index('idx_training_timeframe', table_name='training_events')
    op.drop_index('idx_training_signal_name', table_name='training_events')
    op.drop_index('idx_training_block_name', table_name='training_events')
    
    # Drop table
    op.drop_table('training_events')
    
    print("⚠️ Dropped training_events table and all associated data")
