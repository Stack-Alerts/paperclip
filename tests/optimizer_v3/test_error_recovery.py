"""
Tests for Optimizer V3 Error Recovery System
"""

import pytest
import time
from datetime import datetime
from unittest.mock import Mock, patch

from src.optimizer_v3.core.error_recovery import (
    ErrorRecoveryStrategy,
    ErrorRecord,
    ErrorSeverity,
    RecoveryAction
)
from src.optimizer_v3.core.logger import OptimizerLogger


@pytest.fixture
def logger():
    """Create test logger."""
    return OptimizerLogger('test_error_recovery', log_dir='logs/test')


@pytest.fixture
def recovery_strategy(logger):
    """Create test error recovery strategy."""
    return ErrorRecoveryStrategy(
        logger=logger,
        max_retries=3,
        initial_backoff=0.1,
        max_backoff=1.0,
        backoff_factor=2.0
    )


class TestErrorRecord:
    """Test ErrorRecord dataclass."""
    
    def test_initialization(self):
        """Test ErrorRecord initialization."""
        record = ErrorRecord(
            error_id="test_1",
            timestamp=datetime.now(),
            error_type="ValueError",
            error_message="Test error",
            traceback_info="traceback info",
            severity=ErrorSeverity.HIGH,
            recovery_action=RecoveryAction.RETRY
        )
        
        assert record.error_id == "test_1"
        assert record.error_type == "ValueError"
        assert record.error_message == "Test error"
        assert record.severity == ErrorSeverity.HIGH
        assert record.recovery_action == RecoveryAction.RETRY
        assert record.retry_count == 0
        assert record.recovered is False
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        record = ErrorRecord(
            error_id="test_1",
            timestamp=datetime.now(),
            error_type="ValueError",
            error_message="Test error",
            traceback_info="traceback info",
            severity=ErrorSeverity.HIGH,
            recovery_action=RecoveryAction.RETRY,
            retry_count=2,
            recovered=True,
            metadata={'task_id': 'task_1'}
        )
        
        result = record.to_dict()
        
        assert result['error_id'] == "test_1"
        assert result['error_type'] == "ValueError"
        assert result['severity'] == 'high'
        assert result['recovery_action'] == 'retry'
        assert result['retry_count'] == 2
        assert result['recovered'] is True
        assert result['metadata'] == {'task_id': 'task_1'}


class TestErrorRecoveryStrategy:
    """Test ErrorRecoveryStrategy class."""
    
    def test_initialization(self, recovery_strategy, logger):
        """Test initialization."""
        assert recovery_strategy.logger == logger
        assert recovery_strategy.max_retries == 3
        assert recovery_strategy.initial_backoff == 0.1
        assert recovery_strategy.max_backoff == 1.0
        assert recovery_strategy.backoff_factor == 2.0
        assert len(recovery_strategy._error_history) == 0
        assert len(recovery_strategy._error_counts) == 0
    
    def test_execute_with_retry_success_first_attempt(self, recovery_strategy):
        """Test successful execution on first attempt."""
        def success_func():
            return "success"
        
        result = recovery_strategy.execute_with_retry(success_func, task_id="test_1")
        assert result == "success"
        assert len(recovery_strategy._error_history) == 0
    
    def test_execute_with_retry_success_after_retries(self, recovery_strategy):
        """Test successful execution after retries."""
        call_count = [0]
        
        def flaky_func():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError("Transient error")
            return "success"
        
        start = time.time()
        result = recovery_strategy.execute_with_retry(flaky_func, task_id="test_2")
        elapsed = time.time() - start
        
        assert result == "success"
        assert call_count[0] == 3
        assert elapsed >= 0.3  # Should have backoff delays
        
        # Check error history
        assert len(recovery_strategy._error_history) == 2  # Two failures before success
        assert all(r.error_type == "ValueError" for r in recovery_strategy._error_history)
    
    def test_execute_with_retry_final_failure(self, recovery_strategy):
        """Test execution fails after max retries."""
        def always_fail():
            raise ValueError("Permanent error")
        
        with pytest.raises(ValueError, match="Permanent error"):
            recovery_strategy.execute_with_retry(always_fail, task_id="test_3")
        
        # Check error history
        assert len(recovery_strategy._error_history) == 4  # max_retries + 1
        assert all(r.error_type == "ValueError" for r in recovery_strategy._error_history)
    
    def test_execute_with_retry_callbacks(self, recovery_strategy):
        """Test success and failure callbacks."""
        success_calls = []
        failure_calls = []
        
        def on_success(result, retry_count):
            success_calls.append((result, retry_count))
        
        def on_failure(error, retry_count, error_record):
            failure_calls.append((str(error), retry_count, error_record))
        
        # Test success callback
        def success_func():
            return "success"
        
        result = recovery_strategy.execute_with_retry(
            success_func,
            task_id="test_4",
            on_success=on_success
        )
        
        assert len(success_calls) == 1
        assert success_calls[0][0] == "success"
        assert success_calls[0][1] == 0
        
        # Test failure callback
        def fail_func():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            recovery_strategy.execute_with_retry(
                fail_func,
                task_id="test_5",
                on_failure=on_failure
            )
        
        assert len(failure_calls) == 1
        assert "Test error" in failure_calls[0][0]
        assert failure_calls[0][1] == 4  # max_retries + 1
    
    def test_categorize_error(self, recovery_strategy):
        """Test error categorization."""
        # Critical errors
        assert recovery_strategy._categorize_error(MemoryError()) == ErrorSeverity.CRITICAL
        assert recovery_strategy._categorize_error(SystemError()) == ErrorSeverity.CRITICAL
        
        # High severity
        assert recovery_strategy._categorize_error(ValueError()) == ErrorSeverity.HIGH
        assert recovery_strategy._categorize_error(TypeError()) == ErrorSeverity.HIGH
        assert recovery_strategy._categorize_error(RuntimeError()) == ErrorSeverity.HIGH
        
        # Medium severity
        assert recovery_strategy._categorize_error(IOError()) == ErrorSeverity.MEDIUM
        assert recovery_strategy._categorize_error(ConnectionError()) == ErrorSeverity.MEDIUM
        assert recovery_strategy._categorize_error(TimeoutError()) == ErrorSeverity.MEDIUM
        
        # Low severity (default)
        assert recovery_strategy._categorize_error(Exception()) == ErrorSeverity.LOW
    
    def test_determine_action(self, recovery_strategy):
        """Test recovery action determination."""
        # Critical errors should abort
        action = recovery_strategy._determine_action(
            MemoryError(),
            retry_count=1,
            severity=ErrorSeverity.CRITICAL
        )
        assert action == RecoveryAction.ABORT
        
        # All other errors should retry
        action = recovery_strategy._determine_action(
            ValueError(),
            retry_count=1,
            severity=ErrorSeverity.HIGH
        )
        assert action == RecoveryAction.RETRY
        
        action = recovery_strategy._determine_action(
            ValueError(),
            retry_count=1,
            severity=ErrorSeverity.MEDIUM
        )
        assert action == RecoveryAction.RETRY
    
    def test_calculate_backoff(self, recovery_strategy):
        """Test backoff calculation."""
        # First retry
        delay1 = recovery_strategy._calculate_backoff(1)
        assert 0.1 <= delay1 <= 0.2  # initial_backoff + jitter
        
        # Second retry
        delay2 = recovery_strategy._calculate_backoff(2)
        assert 0.2 <= delay2 <= 0.3  # 0.1 * 2 + jitter
        
        # Third retry
        delay3 = recovery_strategy._calculate_backoff(3)
        assert 0.4 <= delay3 <= 0.5  # 0.1 * 4 + jitter
        
        # Should not exceed max_backoff
        delay_large = recovery_strategy._calculate_backoff(10)
        assert delay_large <= recovery_strategy.max_backoff * 1.1  # max + jitter
    
    def test_record_error(self, recovery_strategy):
        """Test error recording."""
        error = ValueError("Test error")
        
        record = recovery_strategy._record_error(
            error=error,
            task_id="test_6",
            severity=ErrorSeverity.HIGH,
            action=RecoveryAction.RETRY,
            retry_count=1
        )
        
        assert record.error_id == "test_6_1"
        assert record.error_type == "ValueError"
        assert record.error_message == "Test error"
        assert record.severity == ErrorSeverity.HIGH
        assert record.recovery_action == RecoveryAction.RETRY
        assert record.retry_count == 1
        assert record.metadata['task_id'] == "test_6"
        
        # Check history
        assert len(recovery_strategy._error_history) == 1
        assert recovery_strategy._error_counts['ValueError'] == 1
    
    def test_mark_recovered(self, recovery_strategy):
        """Test marking task as recovered."""
        # Record some errors
        recovery_strategy._record_error(
            ValueError("Error 1"),
            task_id="test_7",
            severity=ErrorSeverity.HIGH,
            action=RecoveryAction.RETRY,
            retry_count=1
        )
        
        recovery_strategy._record_error(
            ValueError("Error 2"),
            task_id="test_7",
            severity=ErrorSeverity.HIGH,
            action=RecoveryAction.RETRY,
            retry_count=2
        )
        
        # Mark as recovered
        recovery_strategy._mark_recovered("test_7")
        
        # Check that last error for task is marked recovered
        task_errors = [r for r in recovery_strategy._error_history 
                      if r.metadata.get('task_id') == "test_7"]
        assert task_errors[-1].recovered is True
    
    def test_get_error_history(self, recovery_strategy):
        """Test getting error history."""
        # Add some errors
        for i in range(3):
            recovery_strategy._record_error(
                ValueError(f"Error {i}"),
                task_id=f"test_{i}",
                severity=ErrorSeverity.MEDIUM,
                action=RecoveryAction.RETRY,
                retry_count=1
            )
        
        history = recovery_strategy.get_error_history()
        assert len(history) == 3
        assert isinstance(history, list)
        assert all(isinstance(r, ErrorRecord) for r in history)
    
    def test_get_error_statistics(self, recovery_strategy):
        """Test getting error statistics."""
        # Add various errors
        recovery_strategy._record_error(
            ValueError("Error 1"),
            task_id="test_1",
            severity=ErrorSeverity.HIGH,
            action=RecoveryAction.RETRY,
            retry_count=1
        )
        
        recovery_strategy._record_error(
            TypeError("Error 2"),
            task_id="test_2",
            severity=ErrorSeverity.MEDIUM,
            action=RecoveryAction.RETRY,
            retry_count=1
        )
        
        recovery_strategy._record_error(
            ValueError("Error 3"),
            task_id="test_3",
            severity=ErrorSeverity.HIGH,
            action=RecoveryAction.RETRY,
            retry_count=1
        )
        
        # Mark one as recovered
        recovery_strategy._mark_recovered("test_1")
        
        stats = recovery_strategy.get_error_statistics()
        
        assert stats['total_errors'] == 3
        assert stats['recovered'] == 1
        assert stats['unrecovered'] == 2
        assert stats['recovery_rate'] == pytest.approx(1/3)
        assert stats['error_counts']['ValueError'] == 2
        assert stats['error_counts']['TypeError'] == 1
        assert stats['severity_counts']['high'] == 2
        assert stats['severity_counts']['medium'] == 1
    
    def test_clear_history(self, recovery_strategy):
        """Test clearing error history."""
        # Add some errors
        for i in range(3):
            recovery_strategy._record_error(
                ValueError(f"Error {i}"),
                task_id=f"test_{i}",
                severity=ErrorSeverity.MEDIUM,
                action=RecoveryAction.RETRY,
                retry_count=1
            )
        
        assert len(recovery_strategy._error_history) > 0
        assert len(recovery_strategy._error_counts) > 0
        
        recovery_strategy.clear_history()
        
        assert len(recovery_strategy._error_history) == 0
        assert len(recovery_strategy._error_counts) == 0


class TestErrorRecoveryIntegration:
    """Integration tests for error recovery."""
    
    def test_retry_with_exponential_backoff(self, logger):
        """Test retry with exponential backoff."""
        strategy = ErrorRecoveryStrategy(
            logger=logger,
            max_retries=3,
            initial_backoff=0.1,
            max_backoff=1.0,
            backoff_factor=2.0
        )
        
        attempts = []
        
        def flaky_function():
            attempts.append(time.time())
            if len(attempts) < 3:
                raise ConnectionError("Connection failed")
            return "success"
        
        result = strategy.execute_with_retry(flaky_function, task_id="integration_1")
        
        assert result == "success"
        assert len(attempts) == 3
        
        # Verify backoff delays
        if len(attempts) >= 2:
            delay1 = attempts[1] - attempts[0]
            assert delay1 >= 0.1  # At least initial_backoff
        
        if len(attempts) >= 3:
            delay2 = attempts[2] - attempts[1]
            assert delay2 >= 0.2  # At least initial_backoff * 2
    
    def test_critical_error_aborts_immediately(self, logger):
        """Test that critical errors abort without retries."""
        strategy = ErrorRecoveryStrategy(
            logger=logger,
            max_retries=3,
            initial_backoff=0.1
        )
        
        attempt_count = [0]
        
        def critical_function():
            attempt_count[0] += 1
            raise MemoryError("Out of memory")
        
        with pytest.raises(MemoryError):
            strategy.execute_with_retry(critical_function, task_id="integration_2")
        
        # Should only attempt once due to critical severity
        assert attempt_count[0] == 1
    
    def test_mixed_error_types(self, logger):
        """Test handling of mixed error types."""
        strategy = ErrorRecoveryStrategy(
            logger=logger,
            max_retries=5,
            initial_backoff=0.05
        )
        
        errors_to_raise = [
            ValueError("Error 1"),
            TypeError("Error 2"),
            ConnectionError("Error 3"),
        ]
        
        attempt_count = [0]
        
        def mixed_errors():
            if attempt_count[0] < len(errors_to_raise):
                error = errors_to_raise[attempt_count[0]]
                attempt_count[0] += 1
                raise error
            attempt_count[0] += 1
            return "success"
        
        result = strategy.execute_with_retry(mixed_errors, task_id="integration_3")
        
        assert result == "success"
        assert attempt_count[0] == 4
        
        # Check error history
        history = strategy.get_error_history()
        assert len(history) == 3
        assert history[0].error_type == "ValueError"
        assert history[1].error_type == "TypeError"
        assert history[2].error_type == "ConnectionError"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
