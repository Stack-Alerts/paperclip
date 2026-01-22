"""
Unit Tests for Recommendation Engine
=====================================

Tests for the intelligent recommendation engine and building blocks intelligence.

Author: Optimizer v3 Team
Date: 2026-01-22
Sprint: 1.6 (Intelligent Recommendations - Task 1.6.13)
"""

import pytest
from src.optimizer_v3.core.recommendation_engine import RecommendationEngine, Recommendation
from src.optimizer_v3.core.building_blocks_intelligence import (
    BUILDING_BLOCK_IMPROVEMENTS,
    get_blocks_for_metric,
    get_block_intelligence,
    get_stats
)


class TestBuildingBlocksIntelligence:
    """Test building blocks intelligence database"""
    
    def test_intelligence_database_loaded(self):
        """Verify intelligence database is populated"""
        assert len(BUILDING_BLOCK_IMPROVEMENTS) > 0
        assert len(BUILDING_BLOCK_IMPROVEMENTS) >= 50  # At least 50 blocks
    
    def test_block_structure(self):
        """Verify each block has required fields"""
        required_fields = ['type', 'improves_metrics', 'average_improvement', 
                          'category', 'block_registry_name', 'description', 'use_case']
        
        for block_name, intel in BUILDING_BLOCK_IMPROVEMENTS.items():
            for field in required_fields:
                assert field in intel, f"Block '{block_name}' missing field: {field}"
    
    def test_improvement_values(self):
        """Verify improvement values are within reasonable ranges"""
        for block_name, intel in BUILDING_BLOCK_IMPROVEMENTS.items():
            improvements = intel['average_improvement']
            for metric, value in improvements.items():
                # Improvements should be between -1.0 and 1.0 (100% range)
                assert -1.0 <= value <= 1.0, \
                    f"Block '{block_name}' has unrealistic improvement for '{metric}': {value}"
    
    def test_get_blocks_for_metric(self):
        """Test getting blocks that improve specific metrics"""
        # Test win_rate improvements
        blocks = get_blocks_for_metric('win_rate')
        assert len(blocks) > 0
        assert all('win_rate' in b['block_name'] or 'improvement' in b for b in blocks)
        
        # Verify sorted by improvement potential
        improvements = [abs(b['improvement']) for b in blocks]
        assert improvements == sorted(improvements, reverse=True)
    
    def test_get_block_intelligence(self):
        """Test getting intelligence for specific block"""
        # Test known block
        intel = get_block_intelligence('rsi_divergence')
        assert intel is not None
        assert intel['type'] == 'ENTRY_FILTER'
        assert 'win_rate' in intel['improves_metrics']
        
        # Test unknown block
        intel = get_block_intelligence('nonexistent_block')
        assert intel is None
    
    def test_get_stats(self):
        """Test statistics generation"""
        stats = get_stats()
        assert 'total_blocks' in stats
        assert 'by_type' in stats
        assert 'by_category' in stats
        assert stats['total_blocks'] > 0


class TestRecommendationEngine:
    """Test recommendation engine functionality"""
    
    def test_engine_initialization(self):
        """Test engine initializes correctly"""
        engine = RecommendationEngine()
        assert engine.intelligence == BUILDING_BLOCK_IMPROVEMENTS
        assert isinstance(engine.current_blocks, set)
    
    def test_generate_recommendation_for_poor_metric(self):
        """Test generating recommendation for poor metric"""
        engine = RecommendationEngine()
        
        # Test poor win rate
        rec = engine.generate_recommendation('win_rate', 45.0, '✗ Poor')
        assert rec is not None
        assert isinstance(rec, Recommendation)
        assert rec.metric == 'win_rate'
        assert rec.current_value == 45.0
        assert rec.rating == '✗ Poor'
        assert rec.action_type == 'ADD_BLOCK'
        assert rec.block_name is not None
        assert rec.expected_improvement != 0
    
    def test_no_recommendation_for_good_metric(self):
        """Test no recommendation for good metrics"""
        engine = RecommendationEngine()
        
        # Test good win rate
        rec = engine.generate_recommendation('win_rate', 65.0, '✓ Good')
        assert rec is None
    
    def test_format_recommendation_text(self):
        """Test recommendation text formatting"""
        engine = RecommendationEngine()
        
        rec = engine.generate_recommendation('win_rate', 45.0, '✗ Poor')
        if rec:
            text = engine.format_recommendation_text(rec)
            assert isinstance(text, str)
            assert len(text) > 0
            assert "Add '" in text  # Should start with "Add '"
            assert rec.block_name in text
    
    def test_analyze_strategy_gaps(self):
        """Test strategy gap analysis"""
        engine = RecommendationEngine()
        
        gaps = engine.analyze_strategy_gaps()
        assert 'entry_filters' in gaps
        assert 'trend_filters' in gaps
        assert 'exit_optimization' in gaps
        assert 'risk_management' in gaps
        assert all(isinstance(v, list) for v in gaps.values())
    
    def test_get_top_recommendations(self):
        """Test getting top N recommendations"""
        engine = RecommendationEngine()
        
        metrics = {
            'win_rate': 45.0,
            'sharpe_ratio': 0.8,
            'profit_factor': 1.3,
            'max_drawdown_pct': 25.0
        }
        
        # Manually create ratings dict
        metrics_with_ratings = {
            'win_rate': {'value': 45.0, 'rating': '✗ Poor'},
            'sharpe_ratio': {'value': 0.8, 'rating': '✗ Poor'},
            'profit_factor': {'value': 1.3, 'rating': '✗ Poor'},
            'max_drawdown_pct': {'value': 25.0, 'rating': '✗ High'}
        }
        
        top_recs = engine.get_top_recommendations(metrics_with_ratings, limit=3)
        assert len(top_recs) <= 3
        assert all(isinstance(rec, Recommendation) for rec in top_recs)
        
        # Verify sorted by improvement
        if len(top_recs) > 1:
            improvements = [abs(rec.expected_improvement) for rec in top_recs]
            assert improvements == sorted(improvements, reverse=True)
    
    def test_validate_recommendation(self):
        """Test recommendation validation"""
        engine = RecommendationEngine()
        
        rec = engine.generate_recommendation('win_rate', 45.0, '✗ Poor')
        if rec:
            # Valid recommendation
            assert engine.validate_recommendation(rec) is True
    
    def test_get_blocks_for_specific_issue(self):
        """Test getting blocks for specific issues"""
        engine = RecommendationEngine()
        
        # Test low win rate issue
        blocks = engine.get_blocks_for_specific_issue('low_win_rate')
        assert len(blocks) > 0
        assert all('block_name' in b for b in blocks)
        
        # Test high drawdown issue
        blocks = engine.get_blocks_for_specific_issue('high_drawdown')
        assert len(blocks) > 0
        
        # Test invalid issue
        blocks = engine.get_blocks_for_specific_issue('invalid_issue')
        assert len(blocks) == 0
    
    def test_get_summary_stats(self):
        """Test getting summary statistics"""
        engine = RecommendationEngine()
        
        stats = engine.get_summary_stats()
        assert 'total_blocks_in_database' in stats
        assert 'blocks_in_strategy' in stats
        assert 'available_blocks' in stats
        assert 'gaps' in stats
        assert stats['total_blocks_in_database'] > 0


class TestRecommendationDataClass:
    """Test Recommendation dataclass"""
    
    def test_recommendation_creation(self):
        """Test creating recommendation object"""
        rec = Recommendation(
            metric='win_rate',
            current_value=45.0,
            rating='✗ Poor',
            action_type='ADD_BLOCK',
            block_name='rsi_divergence',
            description='RSI divergence filter',
            expected_improvement=0.10,
            expected_new_value=49.5,
            confidence=0.75,
            category='OSCILLATORS',
            use_case='Add when win rate < 60%'
        )
        
        assert rec.metric == 'win_rate'
        assert rec.current_value == 45.0
        assert rec.rating == '✗ Poor'
        assert rec.action_type == 'ADD_BLOCK'
        assert rec.block_name == 'rsi_divergence'
        assert rec.expected_improvement == 0.10
        assert rec.confidence == 0.75


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
