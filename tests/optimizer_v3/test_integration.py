"""
Optimizer V3 Integration Tests
Tests full workflow from strategy loading to optimization space generation.
"""

import pytest
import json
from decimal import Decimal
from pathlib import Path

from nautilus_trader.model.objects import Price, Quantity, Money
from nautilus_trader.model.enums import OrderSide

from src.optimizer_v3.core.logger import OptimizerLogger
from src.optimizer_v3.core.validator import DataValidator, ValidationError
from src.optimizer_v3.core.dependency_graph import DependencyGraph
from src.optimizer_v3.core.strategy_analyzer import StrategyAnalyzer
from src.optimizer_v3.core.optimization_space import OptimizationSpace


@pytest.fixture
def sample_strategy():
    """Sample strategy configuration for testing"""
    return {
        "name": "Test HOD Rejection Strategy",
        "blocks": [
            {
                "name": "hod_block",
                "signals": [
                    {
                        "name": "HOD_REJECTION",
                        "timing_constraint": {"max_candles": 20}
                    }
                ],
                "recheck": {
                    "enabled": True,
                    "max_bars": 10
                }
            },
            {
                "name": "rsi_block",
                "signals": [
                    {"name": "RSI_OVERBOUGHT"}
                ],
                "depends_on": ["hod_block"]
            }
        ],
        "risk_management": {
            "min_risk_reward": 2.0,
            "risk_percent": 1.0,
            "max_leverage": 1.0,
            "confluence_required": 2,
            "max_bars_held": 20
        }
    }


@pytest.fixture
def logger():
    """Create test logger"""
    return OptimizerLogger('integration_test')


class TestFullWorkflow:
    """Test complete strategy analysis workflow"""
    
    def test_strategy_to_optimization_space(self, sample_strategy, logger):
        """Test full workflow: strategy -> parameters -> optimization space"""
        # Step 1: Validate strategy
        validator = DataValidator(logger)
        assert validator.validate_strategy(sample_strategy)
        
        # Step 2: Build dependency graph
        dep_graph = DependencyGraph(logger, validator)
        dep_graph.build_from_strategy(sample_strategy)
        
        assert dep_graph.is_valid()
        assert len(dep_graph.get_anchors()) == 1
        assert 'hod_block' in dep_graph.get_anchors()
        
        # Step 3: Extract parameters
        analyzer = StrategyAnalyzer(logger, validator)
        analysis = analyzer.analyze_strategy(sample_strategy)
        
        assert analysis['strategy_name'] == "Test HOD Rejection Strategy"
        assert analysis['total_parameters'] > 0
        assert len(analysis['timing_parameters']) > 0
        assert len(analysis['recheck_parameters']) > 0
        assert len(analysis['risk_parameters']) > 0
        
        # Step 4: Generate optimization space
        params = analyzer.extract_all_parameters(sample_strategy)
        opt_space = OptimizationSpace(logger, validator, max_combinations=100)
        configs = opt_space.generate_optimization_space(params, 'grid')
        
        assert len(configs) > 0
        assert len(configs) <= 100
        
        # Step 5: Validate optimization space
        is_valid, errors = opt_space.validate_optimization_space(configs)
        assert is_valid, f"Validation errors: {errors}"
        assert len(errors) == 0
    
    def test_circular_dependency_detection(self, logger):
        """Test that circular dependencies are detected"""
        circular_strategy = {
            "name": "Circular Test",
            "blocks": [
                {
                    "name": "block_a",
                    "signals": [{"name": "SIGNAL_A"}],
                   "depends_on": ["block_b"]
                },
                {
                    "name": "block_b",
                    "signals": [{"name": "SIGNAL_B"}],
                    "depends_on": ["block_a"]
                }
            ]
        }
        
        dep_graph = DependencyGraph(logger)
        dep_graph.build_from_strategy(circular_strategy)
        
        assert dep_graph.has_cycles
        assert len(dep_graph.cycles) > 0
        assert not dep_graph.is_valid()
    
    def test_nautilus_type_validation(self, logger):
        """Test NautilusTrader type validation throughout workflow"""
        validator = DataValidator(logger)
        
        # Test Price validation
        price = validator.validate_price(50000.0)
        assert isinstance(price, Price)
        assert price.as_decimal() == Decimal('50000.0')
        
        # Test Quantity validation
        quantity = validator.validate_quantity(1.5)
        assert isinstance(quantity, Quantity)
        
        # Test Money validation
        money = validator.validate_money(1000, 'USD')
        assert isinstance(money, Money)
        assert money.currency.code == 'USD'
        
        # Test OrderSide validation
        side = validator.validate_order_side('BUY')
        assert isinstance(side, OrderSide)
        assert side == OrderSide.BUY
    
    def test_parameter_extraction_completeness(self, sample_strategy, logger):
        """Test that all parameter types are extracted"""
        analyzer = StrategyAnalyzer(logger)
        
        # Extract timing parameters
        timing = analyzer.extract_timing_parameters(sample_strategy)
        assert len(timing) > 0
        assert all('max_candles' in str(p['parameter']) for p in timing if 'max' in p['parameter'])
        
        # Extract recheck parameters
        recheck = analyzer.extract_recheck_parameters(sample_strategy)
        assert len(recheck) > 0
        assert any('max_bars' in p['parameter'] for p in recheck)
        
        # Extract risk parameters
        risk = analyzer.extract_risk_parameters(sample_strategy)
        assert len(risk) > 0
        assert any('min_risk_reward' in p['parameter'] for p in risk)
    
    def test_optimization_space_strategies(self, sample_strategy, logger):
        """Test different optimization space generation strategies"""
        analyzer = StrategyAnalyzer(logger)
        params = analyzer.extract_all_parameters(sample_strategy)
        opt_space = OptimizationSpace(logger, max_combinations=50)
        
        # Test grid strategy
        grid_configs = opt_space.generate_optimization_space(params, 'grid')
        assert len(grid_configs) > 0
        
        # Test random strategy
        opt_space.clear()
        random_configs = opt_space.generate_optimization_space(params, 'random')
        assert len(random_configs) > 0
        
        # Test adaptive strategy
        opt_space.clear()
        adaptive_configs = opt_space.generate_optimization_space(params, 'adaptive')
        assert len(adaptive_configs) > 0
    
    def test_error_handling(self, logger):
        """Test proper error handling throughout workflow"""
        validator = DataValidator(logger)
        
        # Test invalid strategy
        with pytest.raises(ValidationError):
            validator.validate_strategy({"name": "Invalid"})  # Missing blocks
        
        # Test invalid price
        with pytest.raises(ValidationError):
            validator.validate_price("invalid")
        
        # Test invalid order side
        with pytest.raises(ValidationError):
            validator.validate_order_side("INVALID_SIDE")
    
    def test_dependency_graph_execution_order(self, sample_strategy, logger):
        """Test that execution order respects dependencies"""
        dep_graph = DependencyGraph(logger)
        dep_graph.build_from_strategy(sample_strategy)
        
        execution_order = dep_graph.get_execution_order()
        
        # hod_block should come before rsi_block (since rsi depends on hod)
        hod_idx = execution_order.index('hod_block')
        rsi_idx = execution_order.index('rsi_block')
        
        assert hod_idx < rsi_idx, "Dependencies not respected in execution order"


class TestPerformance:
    """Test performance characteristics"""
    
    def test_large_optimization_space_handling(self, logger):
        """Test that large spaces are handled efficiently"""
        # Create strategy with many parameters
        large_strategy = {
            "name": "Large Strategy",
            "blocks": [
                {
                    "name": f"block_{i}",
                    "signals": [{"name": f"SIGNAL_{i}"}],
                    "timing_constraint": {"max_candles": 20},
                    "recheck": {"enabled": True, "max_bars": 10}
                }
                for i in range(5)  # 5 blocks with parameters
            ],
            "risk_management": {
                "min_risk_reward": 2.0,
                "risk_percent": 1.0,
                "max_leverage": 1.0
            }
        }
        
        analyzer = StrategyAnalyzer(logger)
        params = analyzer.extract_all_parameters(large_strategy)
        
        # This would create huge space, but should be limited
        opt_space = OptimizationSpace(logger, max_combinations=1000)
        configs = opt_space.generate_optimization_space(params, 'grid')
        
        # Should be limited to max_combinations
        assert len(configs) <= 1000
    
    def test_validation_speed(self, sample_strategy, logger):
        """Test that validation is fast enough"""
        import time
        
        validator = DataValidator(logger)
        
        start = time.time()
        for _ in range(100):
            validator.validate_strategy(sample_strategy)
        elapsed = time.time() - start
        
        # Should validate 100 strategies in less than 1 second
        assert elapsed < 1.0, f"Validation too slow: {elapsed:.3f}s for 100 validations"


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_empty_strategy(self, logger):
        """Test handling of empty/minimal strategies"""
        validator = DataValidator(logger)
        
        with pytest.raises(ValidationError):
            validator.validate_strategy({})
    
    def test_strategy_without_risk_management(self, logger):
        """Test strategy without risk management section"""
        strategy = {
            "name": "No Risk Management",
            "blocks": [
                {
                    "name": "test_block",
                    "signals": [{"name": "TEST_SIGNAL"}]
                }
            ]
        }
        
        analyzer = StrategyAnalyzer(logger)
        risk_params = analyzer.extract_risk_parameters(strategy)
        
        # Should return empty list, not error
        assert len(risk_params) == 0
    
    def test_parameter_range_boundaries(self, logger):
        """Test parameter values at boundaries"""
        validator = DataValidator(logger)
        
        # Test minimum price
        min_price = validator.validate_price(0.01)
        assert isinstance(min_price, Price)
        
        # Test large price
        large_price = validator.validate_price(100000000)
        assert isinstance(large_price, Price)
