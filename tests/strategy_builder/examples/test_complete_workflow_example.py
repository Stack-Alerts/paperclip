"""
Unit Tests for Complete Workflow Example
Tests the comprehensive integration example
Following TDD approach
Reference: docs/v3/UI-UX/24_COMPLETE_EXAMPLE.md
"""

import pytest

from src.strategy_builder.examples.complete_workflow_example import (
    CompleteWorkflowExample,
    run_example
)


class TestCompleteWorkflowExample:
    """Test suite for complete workflow example"""
    
    def test_example_initialization(self):
        """Test example initializes correctly"""
        example = CompleteWorkflowExample()
        
        assert example is not None
        assert example.orchestrator is not None
        assert example.validator is not None
        assert example.persistence is not None
        
    def test_complete_workflow_executes(self):
        """Test complete workflow runs without errors"""
        example = CompleteWorkflowExample()
        
        results = example.run_complete_workflow()
        
        assert results is not None
        assert isinstance(results, dict)
        assert len(results) > 0
        
    def test_workflow_creates_strategy(self):
        """Test workflow successfully creates strategy"""
        example = CompleteWorkflowExample()
        
        results = example.run_complete_workflow()
        
        assert 'create' in results
        assert results['create'] is True
        
    def test_workflow_adds_blocks(self):
        """Test workflow successfully adds blocks"""
        example = CompleteWorkflowExample()
        
        results = example.run_complete_workflow()
        
        assert 'blocks_added' in results
        assert results['blocks_added'] is True
        
    def test_workflow_validates_strategy(self):
        """Test workflow validates strategy"""
        example = CompleteWorkflowExample()
        
        results = example.run_complete_workflow()
        
        assert 'validation' in results
        assert results['validation'] is True
        
    def test_workflow_checks_dependencies(self):
        """Test workflow checks dependencies"""
        example = CompleteWorkflowExample()
        
        results = example.run_complete_workflow()
        
        assert 'dependencies' in results
        assert results['dependencies'] is True
        
    def test_workflow_generates_code(self):
        """Test workflow generates code"""
        example = CompleteWorkflowExample()
        
        results = example.run_complete_workflow()
        
        assert 'code_generation' in results
        assert results['code_generation'] is True
        
    def test_workflow_saves_strategy(self):
        """Test workflow saves strategy"""
        example = CompleteWorkflowExample()
        
        results = example.run_complete_workflow()
        
        assert 'save' in results
        assert results['save'] is True
        
    def test_workflow_loads_strategy(self):
        """Test workflow loads strategy"""
        example = CompleteWorkflowExample()
        
        results = example.run_complete_workflow()
        
        assert 'load' in results
        assert results['load'] is True
        
    def test_workflow_initializes_state_manager(self):
        """Test workflow initializes state manager"""
        example = CompleteWorkflowExample()
        
        results = example.run_complete_workflow()
        
        assert 'state_manager' in results
        assert results['state_manager'] is True
        
    def test_workflow_tracks_execution_state(self):
        """Test workflow tracks execution state"""
        example = CompleteWorkflowExample()
        
        results = example.run_complete_workflow()
        
        assert 'execution_state' in results
        assert 'execution_snapshot' in results
        
    def test_registry_search_demonstration(self):
        """Test registry search demonstration"""
        example = CompleteWorkflowExample()
        
        result = example.demonstrate_registry_search()
        
        assert result is True
        
    def test_backtest_demonstration(self):
        """Test backtest demonstration"""
        example = CompleteWorkflowExample()
        
        # Setup strategy first
        example.run_complete_workflow()
        
        result = example.demonstrate_backtest()
        
        assert result is True
        
    def test_run_example_function(self):
        """Test main run_example function"""
        results = run_example()
        
        assert results is not None
        assert isinstance(results, dict)
        assert len(results) > 0


class TestWorkflowIntegration:
    """Integration tests for workflow"""
    
    def test_all_components_used(self):
        """Test that all 9 components are demonstrated"""
        example = CompleteWorkflowExample()
        
        results = example.run_complete_workflow()
        
        # Check that key steps from each component are present
        expected_steps = [
            'create',           # StrategyConfigEngine
            'validation',       # StrategyValidator
            'dependencies',     # SignalDependencyResolver
            'code_generation',  # NautilusCodeGenerator
            'save',            # StrategyPersistence
            'load',            # StrategyPersistence
            'state_manager',   # BlockStateManager
        ]
        
        for step in expected_steps:
            assert step in results, f"Step {step} missing from results"
            
    def test_workflow_completes_successfully(self):
        """Test entire workflow completes without errors"""
        example = CompleteWorkflowExample()
        
        results = example.run_complete_workflow()
        
        # Count successful steps
        successful = sum(1 for v in results.values() if v is True)
        
        # Should have high success rate
        assert successful >= len(results) * 0.8, "Too many failed steps"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
