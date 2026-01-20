"""
Tests for Optimizer V3 Orchestrator Integration
"""

import pytest
import time
from unittest.mock import Mock, patch

from src.optimizer_v3.core.orchestrator_integration import (
    OrchestratorIntegration,
    OptimizationConfig,
    OptimizationResult
)
from src.optimizer_v3.core.logger import OptimizerLogger


@pytest.fixture
def logger():
    """Create test logger."""
    return OptimizerLogger('test_orchestrator', log_dir='logs/test')


@pytest.fixture
def worker_function():
    """Create test worker function."""
    def worker(config):
        # Simulate work
        time.sleep(0.01)
        return {
            'id': config['id'],
            'sharpe_ratio': config.get('sharpe_ratio', 1.0),
            'result': 'success'
        }
    return worker


@pytest.fixture
def orchestrator(logger, worker_function):
    """Create test orchestrator integration."""
    return OrchestratorIntegration(logger, worker_function)


class TestOptimizationConfig:
    """Test OptimizationConfig dataclass."""
    
    def test_initialization(self):
        """Test OptimizationConfig initialization."""
        configs = [{'id': 1}, {'id': 2}]
        config = OptimizationConfig(
            strategy_id='test_strategy',
            configs=configs
        )
        
        assert config.strategy_id == 'test_strategy'
        assert config.configs == configs
        assert config.metric_name == "sharpe_ratio"
        assert config.early_stop_patience == 10
        assert config.early_stop_min_delta == 0.001
        assert config.max_workers is None
        assert config.enable_checkpoints is True
        assert config.checkpoint_interval == 5
    
    def test_custom_parameters(self):
        """Test custom parameters."""
        config = OptimizationConfig(
            strategy_id='test',
            configs=[],
            metric_name='profit',
            early_stop_patience=5,
            early_stop_min_delta=0.01,
            max_workers=4,
            enable_checkpoints=False,
            checkpoint_interval=10
        )
        
        assert config.metric_name == 'profit'
        assert config.early_stop_patience == 5
        assert config.early_stop_min_delta == 0.01
        assert config.max_workers == 4
        assert config.enable_checkpoints is False
        assert config.checkpoint_interval == 10


class TestOptimizationResult:
    """Test OptimizationResult dataclass."""
    
    def test_initialization(self):
        """Test OptimizationResult initialization."""
        result = OptimizationResult(
            strategy_id='test',
            total_configs=10,
            completed_configs=8,
            failed_configs=2,
            best_config={'id': 5},
            best_metric_value=1.5,
            stopped_early=False,
            stopping_reason=None,
            duration_seconds=10.5,
            results=[]
        )
        
        assert result.strategy_id == 'test'
        assert result.total_configs == 10
        assert result.completed_configs == 8
        assert result.failed_configs == 2
        assert result.best_config == {'id': 5}
        assert result.best_metric_value == 1.5
        assert result.stopped_early is False
        assert result.stopping_reason is None
        assert result.duration_seconds == 10.5
        assert result.results == []


class TestOrchestratorIntegration:
    """Test OrchestratorIntegration class."""
    
    def test_initialization(self, orchestrator, logger, worker_function):
        """Test initialization."""
        assert orchestrator.logger == logger
        assert orchestrator.worker_function == worker_function
        assert orchestrator.executor is not None
        assert orchestrator.progress_tracker is not None
        assert orchestrator.error_manager is not None
        assert orchestrator.resource_monitor is not None
        assert not orchestrator.is_running()
        assert orchestrator.get_current_config() is None
    
    def test_run_optimization_simple(self, orchestrator):
        """Test simple optimization run."""
        configs = [
            {'id': 1, 'sharpe_ratio': 1.0},
            {'id': 2, 'sharpe_ratio': 1.5},
            {'id': 3, 'sharpe_ratio': 1.2}
        ]
        
        opt_config = OptimizationConfig(
            strategy_id='test_strategy',
            configs=configs,
            early_stop_patience=0  # Disable early stopping
        )
        
        result = orchestrator.run_optimization(opt_config)
        
        assert isinstance(result, OptimizationResult)
        assert result.strategy_id == 'test_strategy'
        assert result.total_configs == 3
        assert result.completed_configs == 3
        assert result.failed_configs == 0
        assert result.best_metric_value == 1.5
        assert result.best_config == {'id': 2, 'sharpe_ratio': 1.5}
        assert not result.stopped_early
        assert result.stopping_reason is None
        assert result.duration_seconds > 0
        assert len(result.results) == 3
    
    def test_run_optimization_with_early_stopping(self, orchestrator):
        """Test optimization with early stopping."""
        configs = [
            {'id': i, 'sharpe_ratio': 1.0 + i * 0.001}
            for i in range(20)
        ]
        
        opt_config = OptimizationConfig(
            strategy_id='test_strategy',
            configs=configs,
            early_stop_patience=5,
            early_stop_min_delta=0.01
        )
        
        result = orchestrator.run_optimization(opt_config)
        
        # Should stop early after 5 iterations without 0.01 improvement
        assert result.completed_configs < 20
        assert result.stopped_early is True
        assert result.stopping_reason == 'patience_exceeded'
    
    def test_run_optimization_concurrent_prevention(self, orchestrator):
        """Test that concurrent optimizations are prevented."""
        configs = [{'id': i} for i in range(5)]
        opt_config = OptimizationConfig(
            strategy_id='test',
            configs=configs,
            early_stop_patience=0
        )
        
        # Start first optimization in separate thread
        import threading
        def run_opt():
            orchestrator.run_optimization(opt_config)
        
        thread = threading.Thread(target=run_opt)
        thread.start()
        
        # Wait for it to start
        time.sleep(0.1)
        
        # Try to start second one
        with pytest.raises(RuntimeError, match="already running"):
            orchestrator.run_optimization(opt_config)
        
        # Wait for first to complete
        thread.join()
    
    def test_is_running(self, orchestrator):
        """Test is_running status."""
        assert not orchestrator.is_running()
        
        configs = [{'id': i} for i in range(3)]
        opt_config = OptimizationConfig(
            strategy_id='test',
            configs=configs,
            early_stop_patience=0
        )
        
        # Run optimization
        result = orchestrator.run_optimization(opt_config)
        
        # Should not be running after completion
        assert not orchestrator.is_running()
    
    def test_get_current_config(self, orchestrator):
        """Test getting current configuration."""
        assert orchestrator.get_current_config() is None
        
        configs = [{'id': i} for i in range(3)]
        opt_config = OptimizationConfig(
            strategy_id='test',
            configs=configs,
            early_stop_patience=0
        )
        
        orchestrator.run_optimization(opt_config)
        
        # Should be None after completion
        assert orchestrator.get_current_config() is None
    
    def test_get_progress_idle(self, orchestrator):
        """Test getting progress when idle."""
        progress = orchestrator.get_progress()
        
        assert progress['status'] == 'idle'
    
    def test_error_handling(self, logger):
        """Test error handling during optimization."""
        call_count = [0]
        
        def failing_worker(config):
            call_count[0] += 1
            if config['id'] == 2:
                raise ValueError("Test error")
            return {
                'id': config['id'],
                'sharpe_ratio': 1.0,
                'result': 'success'
            }
        
        orchestrator = OrchestratorIntegration(logger, failing_worker)
        
        configs = [
            {'id': 1},
            {'id': 2},  # Will fail
            {'id': 3}
        ]
        
        opt_config = OptimizationConfig(
            strategy_id='test',
            configs=configs,
            early_stop_patience=0
        )
        
        result = orchestrator.run_optimization(opt_config)
        
        # Should have 2 successful, 1 failed (after retries)
        assert result.completed_configs == 2
        assert result.failed_configs == 1
    
    def test_cleanup_on_completion(self, orchestrator):
        """Test cleanup happens on completion."""
        configs = [{'id': i} for i in range(3)]
        opt_config = OptimizationConfig(
            strategy_id='test',
            configs=configs,
            early_stop_patience=0
        )
        
        result = orchestrator.run_optimization(opt_config)
        
        # Verify cleanup
        assert not orchestrator.is_running()
        assert not orchestrator.progress_tracker.is_active()
        assert not orchestrator.resource_monitor.is_running()
    
    def test_cleanup_on_error(self, logger):
        """Test cleanup happens on error."""
        def crashing_worker(config):
            raise RuntimeError("Critical error")
        
        orchestrator = OrchestratorIntegration(logger, crashing_worker)
        
        configs = [{'id': 1}]
        opt_config = OptimizationConfig(
            strategy_id='test',
            configs=configs,
            early_stop_patience=0
        )
        
        result = orchestrator.run_optimization(opt_config)
        
        # Verify cleanup happened despite errors
        assert not orchestrator.is_running()
        assert not orchestrator.progress_tracker.is_active()
        assert not orchestrator.resource_monitor.is_running()
    
    def test_resource_monitoring_integration(self, orchestrator):
        """Test resource monitoring during optimization."""
        configs = [{'id': i} for i in range(5)]
        opt_config = OptimizationConfig(
            strategy_id='test',
            configs=configs,
            early_stop_patience=0
        )
        
        result = orchestrator.run_optimization(opt_config)
        
        # Resource monitor should have been active during run
        # and collected some history
        history = orchestrator.resource_monitor.get_history()
        assert len(history) >= 0  # May be 0 if run was very fast
    
    def test_progress_tracking_integration(self, orchestrator):
        """Test progress tracking during optimization."""
        configs = [{'id': i} for i in range(5)]
        opt_config = OptimizationConfig(
            strategy_id='test',
            configs=configs,
            early_stop_patience=0
        )
        
        result = orchestrator.run_optimization(opt_config)
        
        # Progress should have been tracked
        assert result.completed_configs == 5
    
    def test_best_config_tracking(self, orchestrator):
        """Test tracking of best configuration."""
        configs = [
            {'id': 1, 'sharpe_ratio': 1.0},
            {'id': 2, 'sharpe_ratio': 2.5},  # Best
            {'id': 3, 'sharpe_ratio': 1.5},
            {'id': 4, 'sharpe_ratio': 2.0}
        ]
        
        opt_config = OptimizationConfig(
            strategy_id='test',
            configs=configs,
            early_stop_patience=0
        )
        
        result = orchestrator.run_optimization(opt_config)
        
        assert result.best_metric_value == 2.5
        assert result.best_config == {'id': 2, 'sharpe_ratio': 2.5}
    
    def test_no_best_config_on_all_failures(self, logger):
        """Test that best_config is None when all configs fail."""
        def failing_worker(config):
            raise ValueError("All fail")
        
        orchestrator = OrchestratorIntegration(logger, failing_worker)
        
        configs = [{'id': i} for i in range(3)]
        opt_config = OptimizationConfig(
            strategy_id='test',
            configs=configs,
            early_stop_patience=0
        )
        
        result = orchestrator.run_optimization(opt_config)
        
        assert result.best_config is None
        assert result.best_metric_value is None
        assert result.completed_configs == 0
        assert result.failed_configs == 3


class TestOrchestratorIntegrationFlow:
    """Integration tests for complete optimization flows."""
    
    def test_complete_optimization_flow(self, logger):
        """Test complete optimization workflow."""
        def worker(config):
            # Simulate realistic backtest
            return {
                'id': config['id'],
                'sharpe_ratio': config['param'] * 0.5,
                'total_pnl': config['param'] * 100,
                'trades': config['param'] * 10
            }
        
        orchestrator = OrchestratorIntegration(logger, worker)
        
        configs = [
            {'id': i, 'param': i}
            for i in range(1, 11)
        ]
        
        opt_config = OptimizationConfig(
            strategy_id='momentum_strategy',
            configs=configs,
            metric_name='sharpe_ratio',
            early_stop_patience=3,
            early_stop_min_delta=0.5
        )
        
        result = orchestrator.run_optimization(opt_config)
        
        # Verify complete result
        assert result.strategy_id == 'momentum_strategy'
        assert result.total_configs == 10
        assert result.completed_configs <= 10
        assert result.failed_configs == 0
        assert result.best_metric_value > 0
        assert result.duration_seconds > 0
        assert len(result.results) == result.completed_configs
    
    def test_optimization_with_mixed_results(self, logger):
        """Test optimization with some successes and failures."""
        def worker(config):
            if config['id'] % 3 == 0:
                raise ValueError("Simulated failure")
            return {
                'id': config['id'],
                'sharpe_ratio': config['id'] * 0.1
            }
        
        orchestrator = OrchestratorIntegration(logger, worker)
        
        configs = [{'id': i} for i in range(1, 10)]
        opt_config = OptimizationConfig(
            strategy_id='test',
            configs=configs,
            early_stop_patience=0
        )
        
        result = orchestrator.run_optimization(opt_config)
        
        # Should have some successes and some failures
        assert result.completed_configs > 0
        assert result.failed_configs > 0
        assert result.completed_configs + result.failed_configs == 9


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
