"""
Optimizer V3 Unit Tests
Comprehensive unit tests for individual components (95%+ coverage target).
"""

import pytest
import os
import tempfile
from decimal import Decimal
from pathlib import Path

from nautilus_trader.model.objects import Price, Quantity, Money
from nautilus_trader.model.enums import OrderSide

from src.optimizer_v3.core.logger import OptimizerLogger
from src.optimizer_v3.core.validator import DataValidator, ValidationError
from src.optimizer_v3.core.dependency_graph import DependencyGraph
from src.optimizer_v3.core.strategy_analyzer import StrategyAnalyzer
from src.optimizer_v3.core.optimization_space import OptimizationSpace


class TestOptimizerLogger:
    """Unit tests for OptimizerLogger"""
    
    def test_logger_initialization(self):
        """Test logger creates properly"""
        logger = OptimizerLogger('test_component')
        assert logger.component == 'test_component'
        assert logger.session_id is not None
        assert logger.start_time is not None
    
    def test_logger_creates_log_file(self):
        """Test that logger creates log files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = OptimizerLogger('test', log_dir=tmpdir)
            logger.info("Test message")
            
            # Check log file was created
            log_files = list(Path(tmpdir).glob("optimizer_v3_test_*.log"))
            assert len(log_files) == 1
    
    def test_logger_levels(self):
        """Test all logging levels"""
        logger = OptimizerLogger('test')
        
        # Should not raise exceptions
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")
    
    def test_logger_with_metadata(self):
        """Test logging with metadata"""
        logger = OptimizerLogger('test')
        logger.info("Test", key1="value1", key2=123)
        # Should not raise exception
    
    def test_session_id_unique(self):
        """Test that each logger gets unique session ID"""
        logger1 = OptimizerLogger('test1')
        logger2 = OptimizerLogger('test2')
        assert logger1.session_id != logger2.session_id
    
    def test_get_session_duration(self):
        """Test session duration calculation"""
        import time
        logger = OptimizerLogger('test')
        time.sleep(0.1)
        duration = logger.get_session_duration()
        assert duration >= 0.1
    
    def test_logger_close(self):
        """Test logger cleanup"""
        logger = OptimizerLogger('test')
        logger.info("Test message")
        logger.close()
        # Should not raise exception


class TestDataValidator:
    """Unit tests for DataValidator"""
    
    @pytest.fixture
    def validator(self):
        return DataValidator(OptimizerLogger('test'))
    
    def test_validate_strategy_success(self, validator):
        """Test valid strategy passes validation"""
        strategy = {
            "name": "Test Strategy",
            "blocks": [{
                "name": "block1",
                "signals": [{"name": "SIGNAL1"}]
            }]
        }
        assert validator.validate_strategy(strategy)
    
    def test_validate_strategy_missing_name(self, validator):
        """Test strategy without name fails"""
        with pytest.raises(ValidationError, match="Missing required field: name"):
            validator.validate_strategy({"blocks": []})
    
    def test_validate_strategy_missing_blocks(self, validator):
        """Test strategy without blocks fails"""
        with pytest.raises(ValidationError, match="Missing required field: blocks"):
            validator.validate_strategy({"name": "Test"})
    
    def test_validate_strategy_empty_name(self, validator):
        """Test strategy with empty name fails"""
        with pytest.raises(ValidationError, match="name must be non-empty"):
            validator.validate_strategy({"name": "", "blocks": []})
    
    def test_validate_strategy_no_blocks(self, validator):
        """Test strategy with no blocks fails"""
        with pytest.raises(ValidationError, match="at least one block"):
            validator.validate_strategy({"name": "Test", "blocks": []})
    
    def test_validate_block_missing_fields(self, validator):
        """Test block validation with missing fields"""
        strategy = {
            "name": "Test",
            "blocks": [{"name": "block1"}]  # Missing signals
        }
        with pytest.raises(ValidationError, match="Missing required field 'signals'"):
            validator.validate_strategy(strategy)
    
    def test_validate_price_from_float(self, validator):
        """Test Price validation from float"""
        price = validator.validate_price(50000.0)
        assert isinstance(price, Price)
        assert price.as_decimal() == Decimal('50000.0')
    
    def test_validate_price_from_int(self, validator):
        """Test Price validation from int"""
        price = validator.validate_price(50000)
        assert isinstance(price, Price)
    
    def test_validate_price_from_string(self, validator):
        """Test Price validation from string"""
        price = validator.validate_price("50000.50")
        assert isinstance(price, Price)
    
    def test_validate_price_from_decimal(self, validator):
        """Test Price validation from Decimal"""
        price = validator.validate_price(Decimal('50000.50'))
        assert isinstance(price, Price)
    
    def test_validate_price_invalid_type(self, validator):
        """Test Price validation with invalid type"""
        with pytest.raises(ValidationError):
            validator.validate_price([1, 2, 3])
    
    def test_validate_quantity(self, validator):
        """Test Quantity validation"""
        quantity = validator.validate_quantity(1.5)
        assert isinstance(quantity, Quantity)
    
    def test_validate_money(self, validator):
        """Test Money validation"""
        money = validator.validate_money(1000, 'USD')
        assert isinstance(money, Money)
        assert money.currency.code == 'USD'
    
    def test_validate_order_side_buy(self, validator):
        """Test OrderSide BUY validation"""
        side = validator.validate_order_side('BUY')
        assert side == OrderSide.BUY
    
    def test_validate_order_side_sell(self, validator):
        """Test OrderSide SELL validation"""
        side = validator.validate_order_side('SELL')
        assert side == OrderSide.SELL
    
    def test_validate_order_side_invalid(self, validator):
        """Test OrderSide with invalid value"""
        with pytest.raises(ValidationError, match="Invalid OrderSide"):
            validator.validate_order_side('INVALID')
    
    def test_validate_training_event(self, validator):
        """Test training event validation"""
        event = {
            'timestamp': '2025-01-01',
            'signal_name': 'TEST_SIGNAL',
            'price': 50000,
            'position_side': 'BUY'
        }
        assert validator.validate_training_event(event)
    
    def test_validate_trade(self, validator):
        """Test trade validation"""
        trade = {
            'entry_price': 50000,
            'exit_price': 51000,
            'quantity': 1.0,
            'side': 'BUY',
            'pnl': 1000
        }
        assert validator.validate_trade(trade)
    
    def test_validate_position(self, validator):
        """Test position validation"""
        position = {
            'instrument_id': 'BTC/USD',
            'side': 'BUY',
            'quantity': 1.0,
            'entry_price': 50000
        }
        assert validator.validate_position(position)
    
    def test_validate_risk_parameters(self, validator):
        """Test risk parameters validation"""
        params = {
            'min_risk_reward': 2.0,
            'risk_percent': 1.0,
            'max_leverage': 1.0
        }
        assert validator.validate_risk_parameters(params)
    
    def test_validate_risk_parameters_invalid_rr(self, validator):
        """Test risk parameters with invalid min_risk_reward"""
        params = {
            'min_risk_reward': 0.5,  # Too low
            'risk_percent': 1.0,
            'max_leverage': 1.0
        }
        with pytest.raises(ValidationError, match="min_risk_reward must be"):
            validator.validate_risk_parameters(params)


class TestDependencyGraph:
    """Unit tests for DependencyGraph"""
    
    @pytest.fixture
    def logger(self):
        return OptimizerLogger('test')
    
    def test_empty_graph(self, logger):
        """Test empty dependency graph"""
        graph = DependencyGraph(logger)
        assert len(graph.nodes) == 0
        assert graph.is_valid()  # Empty graph is valid
    
    def test_single_node(self, logger):
        """Test graph with single node"""
        strategy = {
            "name": "Single Node",
            "blocks": [{
                "name": "block1",
                "signals": [{"name": "SIGNAL1"}]
            }]
        }
        graph = DependencyGraph(logger)
        graph.build_from_strategy(strategy)
        
        assert len(graph.nodes) == 1
        assert 'block1' in graph.nodes
        assert 'block1' in graph.get_anchors()
    
    def test_linear_dependency(self, logger):
        """Test linear dependency chain"""
        strategy = {
            "name": "Linear",
            "blocks": [
                {
                    "name": "block1",
                    "signals": [{"name": "S1"}]
                },
                {
                    "name": "block2",
                    "signals": [{"name": "S2"}],
                    "depends_on": ["block1"]
                }
            ]
        }
        graph = DependencyGraph(logger)
        graph.build_from_strategy(strategy)
        
        assert len(graph.nodes) == 2
        assert len(graph.get_anchors()) == 1
        assert 'block1' in graph.get_anchors()
        assert graph.is_valid()
    
    def test_circular_dependency(self, logger):
        """Test circular dependency detection"""
        strategy = {
            "name": "Circular",
            "blocks": [
                {
                    "name": "block1",
                    "signals": [{"name": "S1"}],
                    "depends_on": ["block2"]
                },
                {
                    "name": "block2",
                    "signals": [{"name": "S2"}],
                    "depends_on": ["block1"]
                }
            ]
        }
        graph = DependencyGraph(logger)
        graph.build_from_strategy(strategy)
        
        assert graph.has_cycles
        assert not graph.is_valid()
        assert len(graph.cycles) > 0
    
    def test_execution_order(self, logger):
        """Test execution order generation"""
        strategy = {
            "name": "Test",
            "blocks": [
                {"name": "block1", "signals": [{"name": "S1"}]},
                {"name": "block2", "signals": [{"name": "S2"}], "depends_on": ["block1"]},
                {"name": "block3", "signals": [{"name": "S3"}], "depends_on": ["block2"]}
            ]
        }
        graph = DependencyGraph(logger)
        graph.build_from_strategy(strategy)
        
        order = graph.get_execution_order()
        assert order.index('block1') < order.index('block2')
        assert order.index('block2') < order.index('block3')
    
    def test_get_dependencies(self, logger):
        """Test getting dependencies for a block"""
        strategy = {
            "name": "Test",
            "blocks": [
                {"name": "block1", "signals": [{"name": "S1"}]},
                {"name": "block2", "signals": [{"name": "S2"}], "depends_on": ["block1"]}
            ]
        }
        graph = DependencyGraph(logger)
        graph.build_from_strategy(strategy)
        
        deps = graph.get_dependencies('block2')
        assert 'block1' in deps
    
    def test_clear_graph(self, logger):
        """Test clearing graph data"""
        strategy = {
            "name": "Test",
            "blocks": [{"name": "block1", "signals": [{"name": "S1"}]}]
        }
        graph = DependencyGraph(logger)
        graph.build_from_strategy(strategy)
        
        assert len(graph.nodes) > 0
        graph.clear()
        assert len(graph.nodes) == 0


class TestStrategyAnalyzer:
    """Unit tests for StrategyAnalyzer"""
    
    @pytest.fixture
    def analyzer(self):
        return StrategyAnalyzer()
    
    def test_extract_timing_parameters(self, analyzer):
        """Test timing parameter extraction"""
        strategy = {
            "name": "Test",
            "blocks": [{
                "name": "block1",
                "signals": [{"name": "S1"}],
                "timing_constraint": {"max_candles": 20}
            }]
        }
        params = analyzer.extract_timing_parameters(strategy)
        assert len(params) > 0
        assert params[0]['parameter'] == 'max_candles'
        assert params[0]['base_value'] == 20
    
    def test_extract_recheck_parameters(self, analyzer):
        """Test recheck parameter extraction"""
        strategy = {
            "name": "Test",
            "blocks": [{
                "name": "block1",
                "signals": [{"name": "S1"}],
                "recheck": {"enabled": True, "max_bars": 10}
            }]
        }
        params = analyzer.extract_recheck_parameters(strategy)
        assert len(params) > 0
    
    def test_extract_risk_parameters(self, analyzer):
        """Test risk parameter extraction"""
        strategy = {
            "name": "Test",
            "blocks": [],
            "risk_management": {
                "min_risk_reward": 2.0,
                "risk_percent": 1.0,
                "max_leverage": 1.0
            }
        }
        params = analyzer.extract_risk_parameters(strategy)
        assert len(params) > 0
    
    def test_analyze_strategy(self, analyzer):
        """Test full strategy analysis"""
        strategy = {
            "name": "Complete Strategy",
            "blocks": [{
                "name": "block1",
                "signals": [{"name": "S1"}],
                "timing_constraint": {"max_candles": 20},
                "recheck": {"enabled": True, "max_bars": 10}
            }],
            "risk_management": {
                "min_risk_reward": 2.0,
                "risk_percent": 1.0,
                "max_leverage": 1.0
            }
        }
        analysis = analyzer.analyze_strategy(strategy)
        
        assert 'strategy_name' in analysis
        assert 'timing_parameters' in analysis
        assert 'recheck_parameters' in analysis
        assert 'risk_parameters' in analysis
        assert analysis['total_parameters'] > 0


class TestOptimizationSpace:
    """Unit tests for OptimizationSpace"""
    
    @pytest.fixture
    def opt_space(self):
        return OptimizationSpace(max_combinations=100)
    
    def test_empty_parameters(self, opt_space):
        """Test with no parameters"""
        configs = opt_space.generate_optimization_space({}, 'grid')
        assert len(configs) == 0
    
    def test_grid_generation(self, opt_space):
        """Test grid space generation"""
        params = {
            'timing': [{
                'block': 'test',
                'parameter': 'max_candles',
                'type': 'timing',
                'base_value': 20,
                'min': 10,
                'max': 30,
                'step': 5
            }]
        }
        configs = opt_space.generate_optimization_space(params, 'grid')
        assert len(configs) > 0
    
    def test_random_generation(self, opt_space):
        """Test random space generation"""
        params = {
            'timing': [{
                'block': 'test',
                'parameter': 'max_candles',
                'type': 'timing',
                'base_value': 20,
                'min': 10,
                'max': 30,
                'step': 5
            }]
        }
        configs = opt_space.generate_optimization_space(params, 'random')
        assert len(configs) > 0
    
    def test_adaptive_generation(self, opt_space):
        """Test adaptive space generation"""
        params = {
            'timing': [{
                'block': 'test',
                'parameter': 'max_candles',
                'type': 'timing',
                'base_value': 20,
                'min': 10,
                'max': 30,
                'step': 5
            }]
        }
        configs = opt_space.generate_optimization_space(params, 'adaptive')
        assert len(configs) > 0
    
    def test_max_combinations_limit(self, opt_space):
        """Test that max combinations are respected"""
        # Create many parameters to exceed limit
        params = {
            'timing': [{
                'block': f'block{i}',
                'parameter': 'max_candles',
                'type': 'timing',
                'base_value': 20,
                'min': 10,
                'max': 100,
                'step': 1
            } for i in range(3)]
        }
        configs = opt_space.generate_optimization_space(params, 'grid')
        assert len(configs) <= opt_space.max_combinations
    
    def test_validation_success(self, opt_space):
        """Test validation of valid configurations"""
        configs = [
            {'parameters': {'test.param': 10}},
            {'parameters': {'test.param': 20}}
        ]
        is_valid, errors = opt_space.validate_optimization_space(configs)
        assert is_valid
        assert len(errors) == 0
    
    def test_validation_empty_space(self, opt_space):
        """Test validation of empty space"""
        is_valid, errors = opt_space.validate_optimization_space([])
        assert not is_valid
        assert len(errors) > 0
    
    def test_get_space_statistics(self, opt_space):
        """Test statistics generation"""
        params = {
            'timing': [{
                'block': 'test',
                'parameter': 'max_candles',
                'type': 'timing',
                'base_value': 20,
                'min': 10,
                'max': 30,
                'step': 10
            }]
        }
        opt_space.generate_optimization_space(params, 'grid')
        stats = opt_space.get_space_statistics()
        
        assert 'total_configurations' in stats
        assert stats['total_configurations'] > 0
    
    def test_clear_space(self, opt_space):
        """Test clearing optimization space"""
        params = {
            'timing': [{
                'block': 'test',
                'parameter': 'max_candles',
                'type': 'timing',
                'base_value': 20,
                'min': 10,
                'max': 30,
                'step': 10
            }]
        }
        opt_space.generate_optimization_space(params, 'grid')
        assert len(opt_space.parameter_space) > 0
        
        opt_space.clear()
        assert len(opt_space.parameter_space) == 0
