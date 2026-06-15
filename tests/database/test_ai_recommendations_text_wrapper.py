"""
Unit tests for AI Recommendations Manager text() wrapper fix
Sprint 1.6.1 - Task 0.1

Tests verify that all SQL queries use text() wrapper to eliminate
SQLAlchemy deprecation warnings.
"""

import pytest
import inspect
import re
import importlib
from sqlalchemy import text
from src.optimizer_v3.database.ai_recommendations_manager import AIRecommendationsManager


class TestTextWrapperImplementation:
    """Test that all SQL queries use text() wrapper"""
    
    def test_text_import_exists(self):
        """Verify text() is imported from sqlalchemy"""
        from src.optimizer_v3.database import ai_recommendations_manager
        
        assert hasattr(ai_recommendations_manager, 'text'), \
            "text() not imported from sqlalchemy"
    
    def test_all_methods_use_text_wrapper(self):
        """Verify all SQL queries use text() wrapper"""
        source = inspect.getsource(AIRecommendationsManager)
        
        # Count occurrences of text( in the source (simple but effective)
        text_wrapper_count = source.count('text(')

        # Live SQL-emit paths use text(): create_recommendation (2: INSERT +
        # strategy_versions version_number lookup), get_recommendation (1),
        # get_strategy_recommendations (1), mark_applied (1) = 5.
        # P2.2 removed the dead ORM-in-text() duplicates that had inflated
        # the count to 8; the live count is 5.
        assert text_wrapper_count >= 5, \
            f"Expected at least 5 text() wrappers in live code paths, found {text_wrapper_count}"
        
        # Verify no raw SQL strings without text() wrapper
        # Look for execute with quoted SQL (should all have text() now)
        raw_sql_pattern = r'self\.session\.execute\(\s*["\'](?!.*text\()'
        raw_sql_matches = re.findall(raw_sql_pattern, source)
        
        assert len(raw_sql_matches) == 0, \
            f"Found {len(raw_sql_matches)} execute() calls without text() wrapper"
    
    def test_create_recommendation_uses_text(self):
        """Verify create_recommendation() uses text() wrapper"""
        source = inspect.getsource(AIRecommendationsManager.create_recommendation)
        
        # Should have text() wrapper for INSERT query
        assert 'text(' in source, "create_recommendation() doesn't use text()"
        assert 'INSERT INTO ai_recommendations' in source
        assert 'text("""' in source or 'text("' in source
    
    def test_get_recommendation_uses_text(self):
        """Verify get_recommendation() uses text() wrapper"""
        source = inspect.getsource(AIRecommendationsManager.get_recommendation)
        
        assert 'text(' in source, "get_recommendation() doesn't use text()"
        assert 'SELECT * FROM ai_recommendations' in source
    
    def test_get_strategy_recommendations_uses_text(self):
        """Verify get_strategy_recommendations() uses text() wrapper"""
        source = inspect.getsource(AIRecommendationsManager.get_strategy_recommendations)
        
        assert 'text(' in source, "get_strategy_recommendations() doesn't use text()"
    
    def test_mark_applied_uses_text(self):
        """Verify mark_applied() uses text() wrapper"""
        source = inspect.getsource(AIRecommendationsManager.mark_applied)
        
        assert 'text(' in source, "mark_applied() doesn't use text()"
        assert 'UPDATE ai_recommendations' in source
    
    def test_record_impact_uses_text(self):
        """Verify record_impact() uses text() wrapper"""
        source = inspect.getsource(AIRecommendationsManager.record_impact)
        
        assert 'text(' in source, "record_impact() doesn't use text()"
        assert 'UPDATE ai_recommendations' in source
    
    def test_get_recommendations_by_type_uses_text(self):
        """Verify get_recommendations_by_type() uses text() wrapper"""
        source = inspect.getsource(AIRecommendationsManager.get_recommendations_by_type)
        
        assert 'text(' in source, "get_recommendations_by_type() doesn't use text()"
    
    def test_get_high_confidence_pending_uses_text(self):
        """Verify get_high_confidence_pending() uses text() wrapper"""
        source = inspect.getsource(AIRecommendationsManager.get_high_confidence_pending)
        
        assert 'text(' in source, "get_high_confidence_pending() doesn't use text()"
    
    def test_get_effectiveness_stats_uses_text(self):
        """Verify get_effectiveness_stats() uses text() wrapper"""
        source = inspect.getsource(AIRecommendationsManager.get_effectiveness_stats)
        
        assert 'text(' in source, "get_effectiveness_stats() doesn't use text()"
        assert 'SELECT' in source and 'COUNT' in source


class TestNoDeprecationWarnings:
    """Test that no deprecation warnings are generated"""
    
    @pytest.fixture
    def manager(self, db_session):
        """Create AI recommendations manager"""
        return AIRecommendationsManager(db_session)
    
    def test_no_warnings_on_import(self):
        """Test that importing module doesn't generate warnings"""
        import warnings
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            from src.optimizer_v3.database import ai_recommendations_manager
            importlib.reload(ai_recommendations_manager)
            
            # Should not have any deprecation warnings
            deprecation_warnings = [
                warning for warning in w
                if issubclass(warning.category, DeprecationWarning)
            ]
            
            assert len(deprecation_warnings) == 0, \
                f"Found {len(deprecation_warnings)} deprecation warnings on import"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
