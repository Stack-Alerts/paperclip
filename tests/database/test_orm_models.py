"""
Sprint 1.6.1 ORM Model Unit Tests
Task 1.6.1.ORM.12 - Comprehensive unit tests for ORM models

Tests:
- Model instantiation and defaults
- Relationship integrity
- JSONB column handling
- Index verification
- Cascade delete behavior

Coverage Target: 100%
"""

import pytest
import uuid
from datetime import datetime
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session, sessionmaker

from src.optimizer_v3.database.models import (
    Base,
    Strategy,
    StrategyVersion,
    StrategyBlockVersion,
    AIRecommendation,
    StrategyTestResult,
)


class TestORMModelDefinitions:
    """Test ORM model class definitions are correct"""
    
    def test_strategy_table_name(self):
        """Strategy model has correct table name"""
        assert Strategy.__tablename__ == 'strategies'
    
    def test_strategy_version_table_name(self):
        """StrategyVersion model has correct table name"""
        assert StrategyVersion.__tablename__ == 'strategy_versions'
    
    def test_strategy_block_version_table_name(self):
        """StrategyBlockVersion model has correct table name"""
        assert StrategyBlockVersion.__tablename__ == 'strategy_block_versions'
    
    def test_ai_recommendation_table_name(self):
        """AIRecommendation model has correct table name"""
        assert AIRecommendation.__tablename__ == 'ai_recommendations'
    
    def test_strategy_test_result_table_name(self):
        """StrategyTestResult model has correct table name"""
        assert StrategyTestResult.__tablename__ == 'strategy_test_results'


class TestStrategyModel:
    """Test Strategy ORM model"""
    
    def test_strategy_primary_key(self):
        """Strategy has strategy_id as primary key"""
        pk_cols = [c.name for c in Strategy.__table__.primary_key.columns]
        assert 'strategy_id' in pk_cols
    
    def test_strategy_required_fields(self):
        """Strategy has required fields"""
        columns = {c.name for c in Strategy.__table__.columns}
        assert 'strategy_id' in columns
        assert 'name' in columns
        assert 'created_at' in columns
        assert 'updated_at' in columns
    
    def test_strategy_relationships(self):
        """Strategy has proper relationships defined"""
        relationships = Strategy.__mapper__.relationships.keys()
        assert 'versions' in relationships
        assert 'recommendations' in relationships
        assert 'test_results' in relationships
    
    def test_strategy_repr(self):
        """Strategy __repr__ returns useful string"""
        s = Strategy(strategy_id='test123', name='Test Strategy')
        repr_str = repr(s)
        assert 'test123' in repr_str
        assert 'Test Strategy' in repr_str


class TestStrategyVersionModel:
    """Test StrategyVersion ORM model"""
    
    def test_strategy_version_primary_key(self):
        """StrategyVersion has version_id as primary key"""
        pk_cols = [c.name for c in StrategyVersion.__table__.primary_key.columns]
        assert 'version_id' in pk_cols
    
    def test_strategy_version_foreign_key(self):
        """StrategyVersion has foreign key to strategies"""
        fk_cols = [fk.column.table.name for fk in StrategyVersion.__table__.foreign_keys]
        assert 'strategies' in fk_cols
    
    def test_strategy_version_jsonb_columns(self):
        """StrategyVersion has JSONB columns for strategy data"""
        columns = {c.name for c in StrategyVersion.__table__.columns}
        jsonb_columns = ['blocks', 'signals', 'parameters', 'entry_conditions', 
                         'exit_conditions', 'risk_management', 'backtest_config',
                         'backtest_results', 'metrics', 'trades', 'equity_curve', 'tags']
        for col in jsonb_columns:
            assert col in columns, f"Missing JSONB column: {col}"
    
    def test_strategy_version_exit_conditions_exists(self):
        """Sprint 1.8 exit_conditions column exists"""
        columns = {c.name for c in StrategyVersion.__table__.columns}
        assert 'exit_conditions' in columns
    
    def test_strategy_version_unique_constraint(self):
        """StrategyVersion has unique constraint on (strategy_id, version_number)"""
        constraints = [c.name for c in StrategyVersion.__table__.constraints 
                       if hasattr(c, 'name') and c.name]
        assert 'uq_strategy_version' in constraints
    
    def test_strategy_version_relationships(self):
        """StrategyVersion has proper relationships"""
        relationships = StrategyVersion.__mapper__.relationships.keys()
        assert 'strategy' in relationships
        assert 'block_versions' in relationships
        assert 'recommendations' in relationships
        assert 'test_results' in relationships


class TestStrategyBlockVersionModel:
    """Test StrategyBlockVersion ORM model"""
    
    def test_block_version_primary_key(self):
        """StrategyBlockVersion has block_version_id as primary key"""
        pk_cols = [c.name for c in StrategyBlockVersion.__table__.primary_key.columns]
        assert 'block_version_id' in pk_cols
    
    def test_block_version_foreign_key(self):
        """StrategyBlockVersion has foreign key to strategy_versions"""
        fk_cols = [fk.column.table.name for fk in StrategyBlockVersion.__table__.foreign_keys]
        assert 'strategy_versions' in fk_cols
    
    def test_block_version_required_fields(self):
        """StrategyBlockVersion has required fields"""
        columns = {c.name for c in StrategyBlockVersion.__table__.columns}
        assert 'block_name' in columns
        assert 'block_type' in columns
        assert 'signals' in columns
        assert 'parameters' in columns
        assert 'logic_type' in columns


class TestAIRecommendationModel:
    """Test AIRecommendation ORM model"""
    
    def test_ai_recommendation_primary_key(self):
        """AIRecommendation has recommendation_id as primary key"""
        pk_cols = [c.name for c in AIRecommendation.__table__.primary_key.columns]
        assert 'recommendation_id' in pk_cols
    
    def test_ai_recommendation_foreign_keys(self):
        """AIRecommendation has foreign keys to strategies and versions"""
        fk_tables = [fk.column.table.name for fk in AIRecommendation.__table__.foreign_keys]
        assert 'strategies' in fk_tables
        assert 'strategy_versions' in fk_tables
    
    def test_ai_recommendation_required_fields(self):
        """AIRecommendation has required fields"""
        columns = {c.name for c in AIRecommendation.__table__.columns}
        assert 'recommendation_type' in columns
        assert 'reasoning' in columns
        assert 'applied' in columns
        assert 'timestamp' in columns
    
    def test_ai_recommendation_tracking_fields(self):
        """AIRecommendation has application tracking fields"""
        columns = {c.name for c in AIRecommendation.__table__.columns}
        assert 'applied' in columns
        assert 'applied_at' in columns
        assert 'metrics_before' in columns
        assert 'metrics_after' in columns


class TestStrategyTestResultModel:
    """Test StrategyTestResult ORM model"""
    
    def test_test_result_primary_key(self):
        """StrategyTestResult has result_id as primary key"""
        pk_cols = [c.name for c in StrategyTestResult.__table__.primary_key.columns]
        assert 'result_id' in pk_cols
    
    def test_test_result_foreign_keys(self):
        """StrategyTestResult has foreign keys to strategies and versions"""
        fk_tables = [fk.column.table.name for fk in StrategyTestResult.__table__.foreign_keys]
        assert 'strategies' in fk_tables
        assert 'strategy_versions' in fk_tables
    
    def test_test_result_metrics_fields(self):
        """StrategyTestResult has performance metric fields"""
        columns = {c.name for c in StrategyTestResult.__table__.columns}
        assert 'total_return_pct' in columns
        assert 'sharpe_ratio' in columns
        assert 'max_drawdown_pct' in columns
        assert 'win_rate' in columns
        assert 'profit_factor' in columns
        assert 'total_trades' in columns
    
    def test_test_result_jsonb_columns(self):
        """StrategyTestResult has JSONB columns for full results"""
        columns = {c.name for c in StrategyTestResult.__table__.columns}
        assert 'metrics' in columns
        assert 'trades' in columns
        assert 'equity_curve' in columns


class TestModelIndexes:
    """Test indexes are defined correctly"""
    
    def test_strategy_indexes(self):
        """Strategy has correct indexes"""
        index_names = [idx.name for idx in Strategy.__table__.indexes]
        assert 'idx_strategies_name' in index_names
        assert 'idx_strategies_created_at' in index_names
    
    def test_strategy_version_indexes(self):
        """StrategyVersion has correct indexes"""
        index_names = [idx.name for idx in StrategyVersion.__table__.indexes]
        assert 'idx_strategy_versions_strategy' in index_names
        assert 'idx_strategy_versions_timestamp' in index_names
        assert 'idx_strategy_versions_hash' in index_names
    
    def test_ai_recommendation_indexes(self):
        """AIRecommendation has correct indexes"""
        index_names = [idx.name for idx in AIRecommendation.__table__.indexes]
        assert 'idx_ai_recommendations_strategy' in index_names
        assert 'idx_ai_recommendations_type' in index_names
        assert 'idx_ai_recommendations_applied' in index_names
    
    def test_test_result_indexes(self):
        """StrategyTestResult has correct indexes"""
        index_names = [idx.name for idx in StrategyTestResult.__table__.indexes]
        assert 'idx_test_results_strategy' in index_names
        assert 'idx_test_results_version' in index_names
        assert 'idx_test_results_test_type' in index_names


class TestCascadeDeletes:
    """Test cascade delete relationships are defined"""
    
    def test_strategy_version_cascade(self):
        """StrategyVersion has cascade delete from Strategy"""
        fk = next(fk for fk in StrategyVersion.__table__.foreign_keys 
                  if fk.column.table.name == 'strategies')
        assert fk.ondelete == 'CASCADE'
    
    def test_block_version_cascade(self):
        """StrategyBlockVersion has cascade delete from StrategyVersion"""
        fk = next(fk for fk in StrategyBlockVersion.__table__.foreign_keys)
        assert fk.ondelete == 'CASCADE'
    
    def test_ai_recommendation_cascade(self):
        """AIRecommendation has cascade delete from Strategy"""
        fk = next(fk for fk in AIRecommendation.__table__.foreign_keys 
                  if fk.column.table.name == 'strategies')
        assert fk.ondelete == 'CASCADE'
    
    def test_test_result_cascade(self):
        """StrategyTestResult has cascade delete from Strategy"""
        fk = next(fk for fk in StrategyTestResult.__table__.foreign_keys 
                  if fk.column.table.name == 'strategies')
        assert fk.ondelete == 'CASCADE'


class TestModelDefaults:
    """Test model default values"""
    
    def test_strategy_version_jsonb_defaults(self):
        """StrategyVersion JSONB columns have correct defaults"""
        columns = {c.name: c for c in StrategyVersion.__table__.columns}
        
        # Check default values exist for required JSONB
        assert columns['blocks'].default is not None
        assert columns['signals'].default is not None
        assert columns['parameters'].default is not None
    
    def test_ai_recommendation_applied_default(self):
        """AIRecommendation.applied defaults to False"""
        columns = {c.name: c for c in AIRecommendation.__table__.columns}
        assert columns['applied'].default.arg == False


class TestModelRepr:
    """Test __repr__ methods return useful strings"""
    
    def test_strategy_repr(self):
        """Strategy repr contains id and name"""
        s = Strategy(strategy_id='s1', name='Test')
        assert 's1' in repr(s)
        assert 'Test' in repr(s)
    
    def test_strategy_version_repr(self):
        """StrategyVersion repr contains version info"""
        v = StrategyVersion(version_id=uuid.uuid4(), name='Test', version_number=1)
        r = repr(v)
        assert 'Test' in r
        assert 'v1' in r
    
    def test_block_version_repr(self):
        """StrategyBlockVersion repr contains block info"""
        b = StrategyBlockVersion(block_name='hod', block_type='entry')
        r = repr(b)
        assert 'hod' in r
        assert 'entry' in r
    
    def test_ai_recommendation_repr(self):
        """AIRecommendation repr contains type and applied status"""
        rec = AIRecommendation(recommendation_type='ADD_BLOCK', applied=False, reasoning='test')
        r = repr(rec)
        assert 'ADD_BLOCK' in r
        assert 'False' in r
    
    def test_test_result_repr(self):
        """StrategyTestResult repr contains type and metrics"""
        tr = StrategyTestResult(test_type='backtest', sharpe_ratio=1.5)
        r = repr(tr)
        assert 'backtest' in r
        assert '1.5' in r


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
