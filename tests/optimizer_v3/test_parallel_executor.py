"""
Tests for Optimizer V3 Parallel Executor
"""

import pytest
import time
import multiprocessing as mp
from unittest.mock import Mock, patch
from datetime import datetime

from src.optimizer_v3.core.parallel_executor import ParallelExecutor, ProcessMonitor
from src.optimizer_v3.core.logger import OptimizerLogger


# Module-level worker functions (required for ProcessPoolExecutor pickling)
def simple_worker(config):
    """Simple worker function."""
    return {
        'config_id': config['id'],
        'result': config['value'] * 2
    }


def worker_with_multiplier(config, multiplier=1):
    """Worker function with kwargs."""
    return {
        'config_id': config['id'],
        'result': config['value'] * multiplier
    }


def error_worker(config):
    """Worker function that raises error on config 2."""
    if config['id'] == 2:
        raise ValueError("Test error")
    return {
        'config_id': config['id'],
        'result': 'success'
    }


def cpu_intensive_worker(config):
    """Simulate CPU-intensive work."""
    result = 0
    for i in range(1000000):
        result += i
    return {
        'config_id': config['id'],
        'result': result
    }


def empty_worker(config):
    """Simple worker that returns config_id."""
    return {'config_id': config['id']}


def delay_worker(config):
    """Worker with small delay."""
    time.sleep(0.01)
    return {'config_id': config['id']}


def success_worker(config):
    """Worker that always succeeds."""
    return {'config_id': config['id'], 'result': 'success'}


def realistic_worker(config):
    """Realistic worker that does some computation."""
    data = config.get('data', [])
    result = sum(data) / len(data) if data else 0
    return {
        'config_id': config['id'],
        'mean': result,
        'n_points': len(data),
        'status': 'success'
    }


def mixed_worker(config):
    """Worker that fails on specific configs (divisible by 3)."""
    if config['id'] % 3 == 0:
        raise RuntimeError(f"Config {config['id']} failed")
    return {
        'config_id': config['id'],
        'value': config['id'] * 10,
        'status': 'success'
    }


def square_worker(config):
    """Worker that squares a value."""
    time.sleep(0.01)
    return {'config_id': config['id'], 'result': config['value'] ** 2}


def slow_worker(config):
    """Worker with configurable duration."""
    time.sleep(config.get('duration', 0.1))
    return {'config_id': config['id'], 'status': 'completed'}


@pytest.fixture
def logger():
    """Create test logger."""
    return OptimizerLogger('test_parallel_executor', log_dir='logs/test')


@pytest.fixture
def executor(logger):
    """Create test parallel executor."""
    return ParallelExecutor(logger, max_workers=2)


@pytest.fixture
def monitor(logger):
    """Create test process monitor."""
    return ProcessMonitor(logger)


class TestProcessMonitor:
    """Test ProcessMonitor class."""
    
    def test_initialization(self, monitor, logger):
        """Test ProcessMonitor initialization."""
        assert monitor.logger == logger
        assert monitor.min_cpu_util == 1.0
        assert monitor.restart_threshold == 30
        assert monitor.max_workers == mp.cpu_count()
        assert len(monitor.processes) == 0
        assert len(monitor.utilization_history) == 0
    
    def test_register_process(self, monitor):
        """Test process registration."""
        # Get current process PID
        current_pid = mp.current_process().pid
        
        monitor.register_process(current_pid)
        
        assert current_pid in monitor.processes
        assert current_pid in monitor.utilization_history
        assert len(monitor.utilization_history[current_pid]) == 0
    
    def test_register_nonexistent_process(self, monitor):
        """Test registration of non-existent process."""
        fake_pid = 999999
        
        monitor.register_process(fake_pid)
        
        # Should not be registered
        assert fake_pid not in monitor.processes
    
    def test_cleanup_process(self, monitor):
        """Test process cleanup."""
        current_pid = mp.current_process().pid
        
        monitor.register_process(current_pid)
        assert current_pid in monitor.processes
        
        monitor.cleanup_process(current_pid)
        assert current_pid not in monitor.processes
        assert current_pid not in monitor.utilization_history
    
    def test_cleanup_all(self, monitor):
        """Test cleanup of all processes."""
        current_pid = mp.current_process().pid
        
        monitor.register_process(current_pid)
        assert len(monitor.processes) > 0
        
        monitor.cleanup_all()
        assert len(monitor.processes) == 0
        assert len(monitor.utilization_history) == 0
    
    def test_detect_zombies(self, monitor):
        """Test zombie process detection."""
        # This test is difficult without actually creating zombie processes
        # We test the method doesn't crash
        zombies = monitor.detect_zombies()
        assert isinstance(zombies, list)
    
    def test_kill_zombies(self, monitor):
        """Test zombie process killing."""
        # Test that kill_zombies doesn't crash with no zombies
        killed = monitor.kill_zombies()
        assert killed == 0


class TestParallelExecutor:
    """Test ParallelExecutor class."""
    
    def test_initialization(self, executor, logger):
        """Test ParallelExecutor initialization."""
        assert executor.logger == logger
        assert executor.max_workers == 2
        assert executor.worker_timeout == 3600
        assert executor.enable_monitoring is True
        assert executor.monitor is not None
        assert executor.active is False
    
    def test_initialization_no_monitoring(self, logger):
        """Test initialization with monitoring disabled."""
        executor = ParallelExecutor(logger, enable_monitoring=False)
        assert executor.monitor is None
    
    def test_initialization_auto_workers(self, logger):
        """Test initialization with auto-detected workers."""
        executor = ParallelExecutor(logger)
        assert executor.max_workers == mp.cpu_count()
    
    def test_is_active(self, executor):
        """Test is_active method."""
        assert executor.is_active() is False
        executor.active = True
        assert executor.is_active() is True
        executor.active = False
        assert executor.is_active() is False
    
    def test_get_max_workers(self, executor):
        """Test get_max_workers method."""
        assert executor.get_max_workers() == 2
    
    def test_set_max_workers(self, executor):
        """Test set_max_workers method."""
        executor.set_max_workers(4)
        assert executor.get_max_workers() == 4
        assert executor.monitor.max_workers == 4
    
    def test_set_max_workers_invalid(self, executor):
        """Test set_max_workers with invalid value."""
        with pytest.raises(ValueError):
            executor.set_max_workers(0)
        
        with pytest.raises(ValueError):
            executor.set_max_workers(-1)
    
    def test_execute_configs_simple(self, executor):
        """Test simple parallel execution."""
        configs = [
            {'id': 1, 'value': 10},
            {'id': 2, 'value': 20},
            {'id': 3, 'value': 30},
        ]
        
        results = executor.execute_configs(configs, simple_worker)
        
        assert len(results) == 3
        assert executor.active is False
        
        # Check results
        result_dict = {r['config_id']: r['result'] for r in results}
        assert result_dict[1] == 20
        assert result_dict[2] == 40
        assert result_dict[3] == 60
    
    def test_execute_configs_with_kwargs(self, executor):
        """Test parallel execution with kwargs."""
        configs = [
            {'id': 1, 'value': 10},
            {'id': 2, 'value': 20},
        ]
        
        results = executor.execute_configs(configs, worker_with_multiplier, multiplier=3)
        
        assert len(results) == 2
        result_dict = {r['config_id']: r['result'] for r in results}
        assert result_dict[1] == 30
        assert result_dict[2] == 60
    
    def test_execute_configs_with_error(self, executor):
        """Test parallel execution with worker errors."""
        configs = [
            {'id': 1},
            {'id': 2},  # Will fail
            {'id': 3},
        ]
        
        results = executor.execute_configs(configs, error_worker)
        
        assert len(results) == 3
        
        # Check successful results
        successful = [r for r in results if r.get('status') != 'failed']
        assert len(successful) == 2
        
        # Check failed result
        failed = [r for r in results if r.get('status') == 'failed']
        assert len(failed) == 1
        assert failed[0]['config_id'] == 2
        assert 'Test error' in failed[0]['error']
    
    def test_execute_configs_cpu_intensive(self, executor):
        """Test with CPU-intensive worker."""
        configs = [{'id': i} for i in range(5)]
        
        start_time = datetime.now()
        results = executor.execute_configs(configs, cpu_intensive_worker)
        elapsed = (datetime.now() - start_time).total_seconds()
        
        assert len(results) == 5
        assert all(isinstance(r['result'], int) for r in results)
        
        # Should complete in reasonable time with parallelism
        # (5 configs on 2 workers should be faster than sequential)
        assert elapsed < 10.0  # Generous timeout
    
    def test_execute_configs_empty_list(self, executor):
        """Test execution with empty config list."""
        results = executor.execute_configs([], empty_worker)
        
        assert len(results) == 0
        assert executor.active is False
    
    def test_execute_configs_progress_logging(self, executor):
        """Test that progress logging occurs."""
        # Create 15 configs to trigger progress logging (every 10)
        configs = [{'id': i} for i in range(15)]
        
        results = executor.execute_configs(configs, delay_worker)
        
        assert len(results) == 15
    
    def test_execute_configs_no_monitoring(self, logger):
        """Test execution with monitoring disabled."""
        executor = ParallelExecutor(logger, enable_monitoring=False)
        
        configs = [{'id': 1}, {'id': 2}]
        results = executor.execute_configs(configs, success_worker)
        
        assert len(results) == 2
        assert executor.monitor is None


class TestParallelExecutorIntegration:
    """Integration tests for ParallelExecutor."""
    
    def test_full_workflow(self, executor):
        """Test complete workflow: submit, monitor, results."""
        configs = [
            {'id': 1, 'data': [1, 2, 3, 4, 5]},
            {'id': 2, 'data': [10, 20, 30, 40, 50]},
            {'id': 3, 'data': [100, 200, 300]},
        ]
        
        results = executor.execute_configs(configs, realistic_worker)
        
        assert len(results) == 3
        assert all(r['status'] == 'success' for r in results)
        
        # Verify calculations
        result_dict = {r['config_id']: r for r in results}
        assert result_dict[1]['mean'] == 3.0
        assert result_dict[2]['mean'] == 30.0
        assert result_dict[3]['mean'] == 200.0
    
    def test_error_recovery(self, executor):
        """Test error recovery with mixed success/failure."""
        configs = [{'id': i} for i in range(1, 11)]  # 1-10
        
        results = executor.execute_configs(configs, mixed_worker)
        
        assert len(results) == 10
        
        # Configs 3, 6, 9 should fail
        successful = [r for r in results if r.get('status') == 'success']
        failed = [r for r in results if r.get('status') == 'failed']
        
        assert len(successful) == 7
        assert len(failed) == 3
        
        # Verify failed configs
        failed_ids = {r['config_id'] for r in failed}
        assert failed_ids == {3, 6, 9}
    
    def test_resource_cleanup(self, executor):
        """Test that resources are properly cleaned up."""
        configs = [{'id': i} for i in range(5)]
        
        # Execute
        results = executor.execute_configs(configs, empty_worker)
        
        # Verify cleanup
        assert executor.active is False
        assert len(executor.monitor.processes) == 0
        assert len(executor.monitor.utilization_history) == 0


@pytest.mark.slow
class TestParallelExecutorLoad:
    """Load tests for ParallelExecutor (marked as slow)."""
    
    def test_many_configs(self, logger):
        """Test with many configs (load test)."""
        executor = ParallelExecutor(logger, max_workers=4)
        
        configs = [{'id': i, 'value': i} for i in range(50)]
        
        start_time = datetime.now()
        results = executor.execute_configs(configs, square_worker)
        elapsed = (datetime.now() - start_time).total_seconds()
        
        assert len(results) == 50
        
        # Should complete faster than sequential
        # Sequential would be 50 * 0.01 = 0.5s minimum
        # With 4 workers should be ~0.125s minimum
        assert elapsed < 1.0  # Generous timeout
        
        # Verify results
        result_dict = {r['config_id']: r['result'] for r in results}
        for i in range(50):
            assert result_dict[i] == i ** 2
    
    def test_long_running_configs(self, logger):
        """Test with longer-running configs."""
        executor = ParallelExecutor(logger, max_workers=2, worker_timeout=10)
        
        configs = [{'id': i, 'duration': 0.2} for i in range(10)]
        
        results = executor.execute_configs(configs, slow_worker)
        
        assert len(results) == 10
        assert all(r['status'] == 'completed' for r in results)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
