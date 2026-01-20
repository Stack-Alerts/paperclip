"""
Tests for Optimizer V3 Early Stopping System
"""

import pytest
from datetime import datetime

from src.optimizer_v3.core.early_stopping import (
    EarlyStopping,
    ImprovementRecord,
    StoppingReason
)
from src.optimizer_v3.core.logger import OptimizerLogger


@pytest.fixture
def logger():
    """Create test logger."""
    return OptimizerLogger('test_early_stopping', log_dir='logs/test')


@pytest.fixture
def early_stopping(logger):
    """Create test early stopping instance."""
    return EarlyStopping(
        logger=logger,
        metric_name="sharpe_ratio",
        patience=3,
        min_delta=0.01,
        maximize=True
    )


class TestImprovementRecord:
    """Test ImprovementRecord dataclass."""
    
    def test_initialization(self):
        """Test ImprovementRecord initialization."""
        record = ImprovementRecord(
            timestamp=datetime.now(),
            iteration=1,
            metric_value=1.5,
            improvement=0.1,
            is_improvement=True
        )
        
        assert record.iteration == 1
        assert record.metric_value == 1.5
        assert record.improvement == 0.1
        assert record.is_improvement is True


class TestEarlyStopping:
    """Test EarlyStopping class."""
    
    def test_initialization(self, early_stopping, logger):
        """Test initialization."""
        assert early_stopping.logger == logger
        assert early_stopping.metric_name == "sharpe_ratio"
        assert early_stopping.patience == 3
        assert early_stopping.min_delta == 0.01
        assert early_stopping.maximize is True
        assert not early_stopping.should_stop()
        assert early_stopping.get_best_value() is None
        assert early_stopping.get_best_iteration() == 0
    
    def test_update_first_iteration(self, early_stopping):
        """Test first iteration update."""
        should_continue = early_stopping.update(1.5)
        
        assert should_continue is True
        assert early_stopping.get_best_value() == 1.5
        assert early_stopping.get_best_iteration() == 1
        assert early_stopping._iterations_without_improvement == 0
        assert len(early_stopping.get_history()) == 1
    
    def test_update_with_improvement(self, early_stopping):
        """Test update with improvement (maximize)."""
        early_stopping.update(1.5)
        should_continue = early_stopping.update(1.6)  # Improvement > 0.01
        
        assert should_continue is True
        assert early_stopping.get_best_value() == 1.6
        assert early_stopping.get_best_iteration() == 2
        assert early_stopping._iterations_without_improvement == 0
    
    def test_update_without_improvement(self, early_stopping):
        """Test update without improvement."""
        early_stopping.update(1.5)
        should_continue = early_stopping.update(1.505)  # Improvement < 0.01
        
        assert should_continue is True
        assert early_stopping.get_best_value() == 1.5
        assert early_stopping.get_best_iteration() == 1
        assert early_stopping._iterations_without_improvement == 1
    
    def test_update_triggers_patience_exceeded(self, early_stopping):
        """Test update triggers patience exceeded."""
        early_stopping.update(1.5)
        early_stopping.update(1.505)  # No improvement (1)
        early_stopping.update(1.506)  # No improvement (2)
        should_continue = early_stopping.update(1.507)  # No improvement (3) - triggers stop
        
        assert should_continue is False
        assert early_stopping.should_stop() is True
        assert early_stopping.get_stopping_reason() == StoppingReason.PATIENCE_EXCEEDED
        assert early_stopping._iterations_without_improvement == 3
    
    def test_minimize_mode(self, logger):
        """Test early stopping in minimize mode."""
        es = EarlyStopping(
            logger=logger,
            metric_name="loss",
            patience=3,
            min_delta=0.01,
            maximize=False
        )
        
        # Lower is better
        es.update(1.5)
        should_continue = es.update(1.4)  # Improvement
        
        assert should_continue is True
        assert es.get_best_value() == 1.4
        assert es._iterations_without_improvement == 0
    
    def test_minimize_no_improvement(self, logger):
        """Test minimize mode without improvement."""
        es = EarlyStopping(
            logger=logger,
            metric_name="loss",
            patience=2,
            min_delta=0.01,
            maximize=False
        )
        
        es.update(1.5)
        should_continue = es.update(1.495)  # No improvement (< 0.01)
        
        assert should_continue is True
        assert es.get_best_value() == 1.5
        assert es._iterations_without_improvement == 1
    
    def test_stop_method(self, early_stopping):
        """Test manual stop method."""
        assert not early_stopping.should_stop()
        
        early_stopping.stop(StoppingReason.USER_STOPPED)
        
        assert early_stopping.should_stop() is True
        assert early_stopping.get_stopping_reason() == StoppingReason.USER_STOPPED
    
    def test_stop_idempotent(self, early_stopping):
        """Test stop is idempotent."""
        early_stopping.stop(StoppingReason.USER_STOPPED)
        early_stopping.stop(StoppingReason.RESOURCE_LIMIT)  # Should not change
        
        assert early_stopping.get_stopping_reason() == StoppingReason.USER_STOPPED
    
    def test_register_stop_callback(self, early_stopping):
        """Test registering stop callback."""
        callback_called = []
        
        def callback(es):
            callback_called.append(es)
        
        early_stopping.register_stop_callback(callback)
        early_stopping.stop(StoppingReason.USER_STOPPED)
        
        assert len(callback_called) == 1
        assert callback_called[0] == early_stopping
    
    def test_register_callback_duplicate(self, early_stopping):
        """Test registering same callback twice."""
        callback_called = []
        
        def callback(es):
            callback_called.append(es)
        
        early_stopping.register_stop_callback(callback)
        early_stopping.register_stop_callback(callback)  # Duplicate
        early_stopping.stop(StoppingReason.USER_STOPPED)
        
        # Should only call once
        assert len(callback_called) == 1
    
    def test_unregister_stop_callback(self, early_stopping):
        """Test unregistering stop callback."""
        callback_called = []
        
        def callback(es):
            callback_called.append(es)
        
        early_stopping.register_stop_callback(callback)
        early_stopping.unregister_stop_callback(callback)
        early_stopping.stop(StoppingReason.USER_STOPPED)
        
        assert len(callback_called) == 0
    
    def test_callback_error_handling(self, early_stopping):
        """Test callback error doesn't crash stop."""
        def failing_callback(es):
            raise ValueError("Test error")
        
        early_stopping.register_stop_callback(failing_callback)
        early_stopping.stop(StoppingReason.USER_STOPPED)
        
        # Should still stop despite callback error
        assert early_stopping.should_stop() is True
    
    def test_get_history(self, early_stopping):
        """Test getting improvement history."""
        early_stopping.update(1.5)
        early_stopping.update(1.6)
        early_stopping.update(1.55)
        
        history = early_stopping.get_history()
        
        assert len(history) == 3
        assert all(isinstance(r, ImprovementRecord) for r in history)
        assert history[0].metric_value == 1.5
        assert history[1].metric_value == 1.6
        assert history[2].metric_value == 1.55
    
    def test_get_statistics(self, early_stopping):
        """Test getting statistics."""
        early_stopping.update(1.5)   # Iteration 1, improvement (first)
        early_stopping.update(1.6)   # Iteration 2, improvement
        early_stopping.update(1.55)  # Iteration 3, no improvement
        early_stopping.update(1.56)  # Iteration 4, no improvement
        
        stats = early_stopping.get_statistics()
        
        assert stats['total_iterations'] == 4
        assert stats['best_value'] == 1.6
        assert stats['best_iteration'] == 2
        assert stats['total_improvements'] == 2
        assert stats['improvement_rate'] == pytest.approx(0.5)
        assert stats['iterations_without_improvement'] == 2
        assert stats['should_stop'] is False
        assert stats['stopping_reason'] is None
    
    def test_get_statistics_after_stopping(self, early_stopping):
        """Test statistics after stopping."""
        early_stopping.update(1.5)
        early_stopping.update(1.505)
        early_stopping.update(1.506)
        early_stopping.update(1.507)  # Triggers stop
        
        stats = early_stopping.get_statistics()
        
        assert stats['should_stop'] is True
        assert stats['stopping_reason'] == 'patience_exceeded'
    
    def test_reset(self, early_stopping):
        """Test reset functionality."""
        early_stopping.update(1.5)
        early_stopping.update(1.6)
        early_stopping.stop(StoppingReason.USER_STOPPED)
        
        assert early_stopping.should_stop() is True
        
        early_stopping.reset()
        
        assert early_stopping.get_best_value() is None
        assert early_stopping.get_best_iteration() == 0
        assert early_stopping._iterations_without_improvement == 0
        assert early_stopping._current_iteration == 0
        assert early_stopping.should_stop() is False
        assert early_stopping.get_stopping_reason() is None
        assert len(early_stopping.get_history()) == 0
    
    def test_improvement_history_records(self, early_stopping):
        """Test improvement record details."""
        early_stopping.update(1.5)
        early_stopping.update(1.6)
        early_stopping.update(1.55)
        
        history = early_stopping.get_history()
        
        # First record - first iteration, always improvement
        assert history[0].is_improvement is True
        assert history[0].improvement == 0.0
        
        # Second record - improvement
        assert history[1].is_improvement is True
        assert history[1].improvement == pytest.approx(0.1)
        
        # Third record - no improvement
        assert history[2].is_improvement is False
        assert history[2].improvement == pytest.approx(-0.05)


class TestEarlyStoppingIntegration:
    """Integration tests for EarlyStopping."""
    
    def test_full_optimization_cycle(self, logger):
        """Test complete optimization cycle."""
        es = EarlyStopping(
            logger=logger,
            metric_name="sharpe_ratio",
            patience=5,
            min_delta=0.01,
            maximize=True
        )
        
        # Simulate improving metrics
        metrics = [1.0, 1.1, 1.25, 1.26, 1.27, 1.271, 1.272, 1.273, 1.274, 1.275]
        
        results = []
        for metric in metrics:
            should_continue = es.update(metric)
            results.append(should_continue)
            if not should_continue:
                break
        
        # Should stop after 5 iterations without significant improvement
        assert es.should_stop() is True
        assert es.get_best_value() == 1.27
        assert es.get_best_iteration() == 5
    
    def test_early_stopping_with_callbacks(self, logger):
        """Test early stopping with cleanup callbacks."""
        es = EarlyStopping(
            logger=logger,
            patience=3,
            min_delta=0.01
        )
        
        cleanup_called = []
        
        def cleanup_callback(early_stop):
            cleanup_called.append({
                'best_value': early_stop.get_best_value(),
                'iterations': early_stop._current_iteration,
                'reason': early_stop.get_stopping_reason()
            })
        
        es.register_stop_callback(cleanup_callback)
        
        # Simulate metrics that will trigger stop
        es.update(1.5)
        es.update(1.505)
        es.update(1.506)
        es.update(1.507)  # Triggers patience exceeded
        
        # Verify callback was called
        assert len(cleanup_called) == 1
        assert cleanup_called[0]['best_value'] == 1.5
        assert cleanup_called[0]['iterations'] == 4
        assert cleanup_called[0]['reason'] == StoppingReason.PATIENCE_EXCEEDED
    
    def test_minimize_convergence(self, logger):
        """Test minimization convergence detection."""
        es = EarlyStopping(
            logger=logger,
            metric_name="loss",
            patience=4,
            min_delta=0.01,
            maximize=False
        )
        
        # Simulate decreasing loss with convergence
        losses = [1.0, 0.8, 0.65, 0.55, 0.548, 0.547, 0.546, 0.545]
        
        for loss in losses:
            should_continue = es.update(loss)
            if not should_continue:
                break
        
        assert es.should_stop() is True
        assert es.get_best_value() == 0.55
        assert es.get_best_iteration() == 4
    
    def test_no_false_triggers(self, early_stopping):
        """Test that early stopping doesn't trigger prematurely."""
        # Update with continuous improvement
        early_stopping.update(1.0)
        early_stopping.update(1.1)
        early_stopping.update(1.2)
        early_stopping.update(1.3)
        early_stopping.update(1.4)
        
        assert not early_stopping.should_stop()
        assert early_stopping._iterations_without_improvement == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
