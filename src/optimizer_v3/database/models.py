"""
Database Models for Optimizer V3
Task 0.4: Database Models with NautilusTrader Integration

All models use NautilusTrader types stored as strings for precision:
- Quantity -> String
- Price -> String  
- Money -> String
- Enums -> Native PostgreSQL Enums
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class OptimizationRun(Base):
    """
    Record of optimizer execution runs
    Tracks each optimization session with configuration and results
    """
    __tablename__ = 'optimization_runs'
    
    run_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id = Column(String(255), nullable=False, index=True)
    strategy_name = Column(String(255), nullable=False)
    strategy_config = Column(JSONB, nullable=False)
    
    # Execution metadata
    start_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_time = Column(DateTime)
    status = Column(String(50), nullable=False, default='running')  # running, completed, failed, cancelled
    error_message = Column(Text)
    
    # Configuration used
    backtest_config = Column(JSONB, nullable=False)
    optimization_params = Column(JSONB, nullable=False)
    
    # Results summary
    total_variations = Column(Integer)
    completed_variations = Column(Integer, default=0)
    failed_variations = Column(Integer, default=0)
    
    # Performance metrics
    best_sharpe_ratio = Column(Float)
    best_profit_factor = Column(Float)
    best_win_rate = Column(Float)
    best_total_pnl = Column(String(50))  # Money type stored as string
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_opt_runs_strategy_status', 'strategy_id', 'status'),
        Index('idx_opt_runs_start_time', 'start_time'),
    )


class StrategyVariation(Base):
    """
    Individual strategy variations tested during optimization
    Each row represents one parameter combination tested
    """
    __tablename__ = 'strategy_variations'
    
    variation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    variation_number = Column(Integer, nullable=False)
    
    # Parameter combination
    parameters = Column(JSONB, nullable=False)
    parameter_hash = Column(String(64), nullable=False, index=True)  # MD5 hash for deduplication
    
    # Execution status
    status = Column(String(50), nullable=False, default='pending')  # pending, running, completed, failed
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    execution_time_seconds = Column(Float)
    error_message = Column(Text)
    
    # Performance Results (all NautilusTrader types as strings)
    total_pnl = Column(String(50))  # Money
    total_return_pct = Column(Float)
    sharpe_ratio = Column(Float)
    sortino_ratio = Column(Float)
    profit_factor = Column(Float)
    win_rate = Column(Float)
    max_drawdown = Column(String(50))  # Money
    max_drawdown_pct = Column(Float)
    
    # Trade statistics
    total_trades = Column(Integer)
    winning_trades = Column(Integer)
    losing_trades = Column(Integer)
    avg_win = Column(String(50))  # Money
    avg_loss = Column(String(50))  # Money
    largest_win = Column(String(50))  # Money
    largest_loss = Column(String(50))  # Money
    
    # Risk metrics
    var_95 = Column(Float)
    cvar_95 = Column(Float)
    calmar_ratio = Column(Float)
    
    # Ranking score (composite metric for sorting)
    ranking_score = Column(Float, index=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_variations_run_ranking', 'run_id', 'ranking_score'),
        Index('idx_variations_status', 'status'),
    )


class SignalEvent(Base):
    """
    Signal events recorded during strategy execution
    For signal intelligence and pattern analysis
    """
    __tablename__ = 'signal_events'
    
    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    variation_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Event details
    timestamp = Column(DateTime, nullable=False, index=True)
    signal_name = Column(String(255), nullable=False, index=True)
    signal_type = Column(String(50), nullable=False)  # entry, exit, filter
    signal_direction = Column(String(20))  # long, short, neutral
    
    # Market context
    instrument_id = Column(String(100), nullable=False)
    price = Column(String(50), nullable=False)  # Price type
    bar_number = Column(Integer)
    
    # Signal metadata
    signal_strength = Column(Float)
    confidence = Column(Float)
    metadata = Column(JSONB)
    
    # Outcome tracking (filled after trade completes)
    led_to_trade = Column(Boolean, default=False)
    trade_result = Column(String(20))  # win, loss, breakeven
    trade_pnl = Column(String(50))  # Money type
    
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index('idx_signal_events_signal_timestamp', 'signal_name', 'timestamp'),
        Index('idx_signal_events_trade_result', 'led_to_trade', 'trade_result'),
    )


class SignalMetrics(Base):
    """
    Aggregated metrics for signal performance analysis
    Updated periodically to track signal effectiveness
    """
    __tablename__ = 'signal_metrics'
    
    metric_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    signal_name = Column(String(255), nullable=False, index=True)
    
    # Time window for metrics
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    
    # Occurrence statistics
    total_occurrences = Column(Integer, nullable=False, default=0)
    trades_triggered = Column(Integer, nullable=False, default=0)
    trigger_rate = Column(Float)  # trades_triggered / total_occurrences
    
    # Performance statistics
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float)
    avg_pnl = Column(String(50))  # Money
    total_pnl = Column(String(50))  # Money
    profit_factor = Column(Float)
    
    # Context
    best_market_condition = Column(String(100))
    worst_market_condition = Column(String(100))
    best_timeframe = Column(String(50))
    
    # Timestamps
    calculated_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_signal_metrics_name_dates', 'signal_name', 'start_date', 'end_date'),
        Index('idx_signal_metrics_win_rate', 'win_rate'),
    )


class TrainingSession(Base):
    """
    ML training sessions for signal generation
    Tracks training runs and model performance
    """
    __tablename__ = 'training_sessions'
    
    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_name = Column(String(255), nullable=False)
    
    # Training configuration
    model_type = Column(String(100), nullable=False)  # xgboost, lightgbm, etc.
    training_config = Column(JSONB, nullable=False)
    feature_set = Column(JSONB, nullable=False)
    
    # Data window
    training_start_date = Column(DateTime, nullable=False)
    training_end_date = Column(DateTime, nullable=False)
    validation_start_date = Column(DateTime)
    validation_end_date = Column(DateTime)
    
    # Training results
    training_accuracy = Column(Float)
    validation_accuracy = Column(Float)
    training_loss = Column(Float)
    validation_loss = Column(Float)
    
    # Model performance
    precision = Column(Float)
    recall = Column(Float)
    f1_score = Column(Float)
    auc_roc = Column(Float)
    
    # Model artifacts
    model_path = Column(String(500))
    feature_importance = Column(JSONB)
    
    # Status
    status = Column(String(50), nullable=False, default='pending')
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    training_time_seconds = Column(Float)
    error_message = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_training_sessions_status', 'status'),
        Index('idx_training_sessions_dates', 'training_start_date', 'training_end_date'),
    )


class SessionState(Base):
    """
    Persistent state for long-running optimization sessions
    Enables resume capability and progress tracking
    """
    __tablename__ = 'session_states'
    
    state_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    
    # Session state
    current_variation = Column(Integer, nullable=False, default=0)
    total_variations = Column(Integer, nullable=False)
    progress_percentage = Column(Float, default=0.0)
    
    # Checkpoint data
    checkpoint_data = Column(JSONB)  # Serialized state for resume
    last_processed_params = Column(JSONB)
    completed_param_hashes = Column(JSONB)  # list of completed parameter hashes
    
    # Resource usage tracking
    cpu_usage_avg = Column(Float)
    memory_usage_avg = Column(Float)
    disk_io_mb = Column(Float)
    
    # Timing estimates
    avg_variation_time_seconds = Column(Float)
    estimated_time_remaining_seconds = Column(Float)
    estimated_completion_time = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_checkpoint_at = Column(DateTime)


class BacktestResult(Base):
    """
    Detailed backtest results with full NautilusTrader integration
    One row per completed backtest execution
    """
    __tablename__ = 'backtest_results'
    
    result_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    variation_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    run_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Backtest metadata
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False)
    instrument_id = Column(String(100), nullable=False)
    
    # Configuration snapshot
    backtest_config = Column(JSONB, nullable=False)
    strategy_params = Column(JSONB, nullable=False)
    
    # Full performance statistics (NautilusTrader format)
    statistics = Column(JSONB, nullable=False)
    
    # Trade list
    trades = Column(JSONB)  # List of all trades with full details
    
    # Equity curve
    equity_curve = Column(JSONB)  # Time series of account value
    
    # Generated by Nautilus
    nautilus_report = Column(JSONB)
    
    # File references
    results_file_path = Column(String(500))
    chart_file_path = Column(String(500))
    
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index('idx_backtest_results_run_variation', 'run_id', 'variation_id'),
        Index('idx_backtest_results_dates', 'start_time', 'end_time'),
    )
