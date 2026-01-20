"""
Tests for Optimizer V3 Progress Tracker
"""

import pytest
import time
from datetime import timedelta
from threading import Thread

from src.optimizer_v3.core.progress_tracker import (
    ProgressTracker,
    TaskProgress,
    TaskStatus
)
from src.optimizer_v3.core.logger import OptimizerLogger


@pytest.fixture
def logger():
    """Create test logger."""
    return OptimizerLogger('test_progress_tracker', log_dir='logs/test')


@pytest.fixture
def tracker(logger):
    """Create test progress tracker."""
    return ProgressTracker(total_tasks=10, logger=logger, update_interval=0.1)


class TestTaskProgress:
    """Test TaskProgress dataclass."""
    
    def test_initialization(self):
        """Test TaskProgress initialization."""
        task = TaskProgress(task_id="test_1")
        
        assert task.task_id == "test_1"
        assert task.status == TaskStatus.PENDING
        assert task.start_time is None
        assert task.end_time is None
        assert task.progress_percent == 0.0
        assert task.error_message is None
        assert task.metadata == {}
    
    def test_duration_not_started(self):
        """Test duration when task not started."""
        task = TaskProgress(task_id="test_1")
        assert task.duration is None
    
    def test_duration_in_progress(self):
        """Test duration for in-progress task."""
        from datetime import datetime
        
        task = TaskProgress(task_id="test_1")
        task.start_time = datetime.now()
        time.sleep(0.1)
        
        duration = task.duration
        assert duration is not None
        assert duration.total_seconds() >= 0.1
    
    def test_duration_completed(self):
        """Test duration for completed task."""
        from datetime import datetime
        
        task = TaskProgress(task_id="test_1")
        task.start_time = datetime.now()
        time.sleep(0.1)
        task.end_time = datetime.now()
        
        duration = task.duration
        assert duration is not None
        assert duration.total_seconds() >= 0.1
    
    def test_is_complete(self):
        """Test is_complete property."""
        task = TaskProgress(task_id="test_1")
        
        # Pending
        assert not task.is_complete
        
        # In progress
        task.status = TaskStatus.IN_PROGRESS
        assert not task.is_complete
        
        # Completed
        task.status = TaskStatus.COMPLETED
        assert task.is_complete
        
        # Failed
        task.status = TaskStatus.FAILED
        assert task.is_complete
        
        # Cancelled
        task.status = TaskStatus.CANCELLED
        assert task.is_complete


class TestProgressTracker:
    """Test ProgressTracker class."""
    
    def test_initialization(self, tracker, logger):
        """Test ProgressTracker initialization."""
        assert tracker.total_tasks == 10
        assert tracker.logger == logger
        assert tracker.update_interval == 0.1
        assert len(tracker._tasks) == 0
        assert len(tracker._callbacks) == 0
    
    def test_register_task(self, tracker):
        """Test task registration."""
        tracker.register_task("task_1", metadata={'test': True})
        
        assert "task_1" in tracker._tasks
        assert tracker._tasks["task_1"].task_id == "task_1"
        assert tracker._tasks["task_1"].metadata == {'test': True}
    
    def test_register_duplicate_task(self, tracker):
        """Test registering duplicate task."""
        tracker.register_task("task_1")
        tracker.register_task("task_1")  # Should log warning
        
        assert len(tracker._tasks) == 1
    
    def test_start_task(self, tracker):
        """Test starting a task."""
        tracker.start_task("task_1")
        
        assert "task_1" in tracker._tasks
        task = tracker._tasks["task_1"]
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.start_time is not None
    
    def test_complete_task(self, tracker):
        """Test completing a task."""
        tracker.start_task("task_1")
        time.sleep(0.1)
        tracker.complete_task("task_1", metadata={'result': 'success'})
        
        task = tracker._tasks["task_1"]
        assert task.status == TaskStatus.COMPLETED
        assert task.end_time is not None
        assert task.progress_percent == 100.0
        assert task.metadata['result'] == 'success'
    
    def test_fail_task(self, tracker):
        """Test failing a task."""
        tracker.start_task("task_1")
        tracker.fail_task("task_1", "Test error", metadata={'error_code': 500})
        
        task = tracker._tasks["task_1"]
        assert task.status == TaskStatus.FAILED
        assert task.end_time is not None
        assert task.error_message == "Test error"
        assert task.metadata['error_code'] == 500
    
    def test_update_task_progress(self, tracker):
        """Test updating task progress."""
        tracker.start_task("task_1")
        
        tracker.update_task_progress("task_1", 50.0)
        assert tracker._tasks["task_1"].progress_percent == 50.0
        
        tracker.update_task_progress("task_1", 75.5)
        assert tracker._tasks["task_1"].progress_percent == 75.5
    
    def test_update_task_progress_bounds(self, tracker):
        """Test progress bounds checking."""
        tracker.start_task("task_1")
        
        # Test maximum bound
        tracker.update_task_progress("task_1", 150.0)
        assert tracker._tasks["task_1"].progress_percent == 100.0
        
        # Test minimum bound
        tracker.update_task_progress("task_1", -10.0)
        assert tracker._tasks["task_1"].progress_percent == 0.0
    
    def test_get_progress(self, tracker):
        """Test overall progress calculation."""
        # No tasks
        assert tracker.get_progress() == 0.0
        
        # Start 5 tasks
        for i in range(5):
            tracker.start_task(f"task_{i}")
        
        # Complete 2 tasks
        tracker.complete_task("task_0")
        tracker.complete_task("task_1")
        
        # Update progress on others
        tracker.update_task_progress("task_2", 50.0)
        tracker.update_task_progress("task_3", 25.0)
        tracker.update_task_progress("task_4", 0.0)
        
        # Progress = (100 + 100 + 50 + 25 + 0) / 10 = 27.5%
        progress = tracker.get_progress()
        assert progress == 27.5
    
    def test_get_completed_count(self, tracker):
        """Test completed task count."""
        assert tracker.get_completed_count() == 0
        
        tracker.start_task("task_1")
        tracker.complete_task("task_1")
        assert tracker.get_completed_count() == 1
        
        tracker.start_task("task_2")
        tracker.complete_task("task_2")
        assert tracker.get_completed_count() == 2
    
    def test_get_failed_count(self, tracker):
        """Test failed task count."""
        assert tracker.get_failed_count() == 0
        
        tracker.start_task("task_1")
        tracker.fail_task("task_1", "Error 1")
        assert tracker.get_failed_count() == 1
        
        tracker.start_task("task_2")
        tracker.fail_task("task_2", "Error 2")
        assert tracker.get_failed_count() == 2
    
    def test_get_in_progress_count(self, tracker):
        """Test in-progress task count."""
        assert tracker.get_in_progress_count() == 0
        
        tracker.start_task("task_1")
        assert tracker.get_in_progress_count() == 1
        
        tracker.start_task("task_2")
        assert tracker.get_in_progress_count() == 2
        
        tracker.complete_task("task_1")
        assert tracker.get_in_progress_count() == 1
    
    def test_get_eta_no_completion(self, tracker):
        """Test ETA with no completed tasks."""
        tracker.start_task("task_1")
        assert tracker.get_eta() is None
    
    def test_get_eta_with_completion(self, tracker):
        """Test ETA calculation."""
        # Complete one task
        tracker.start_task("task_1")
        time.sleep(0.1)
        tracker.complete_task("task_1")
        
        # Start another
        tracker.start_task("task_2")
        
        eta = tracker.get_eta()
        assert eta is not None
        assert isinstance(eta, timedelta)
        # With 1 completed out of 10, should have ~9 tasks remaining
        # ETA should be reasonable
        assert eta.total_seconds() >= 0
    
    def test_get_rate(self, tracker):
        """Test completion rate calculation."""
        # No tasks completed
        assert tracker.get_rate() == 0.0
        
        # Complete tasks
        tracker.start_task("task_1")
        time.sleep(0.1)
        tracker.complete_task("task_1")
        
        rate = tracker.get_rate()
        assert rate > 0
        # Rate should be approximately 10 tasks/second (1 task in 0.1s)
        assert 5 < rate < 15  # Generous bounds
    
    def test_get_status_summary(self, tracker):
        """Test status summary."""
        # Start and complete some tasks
        tracker.start_task("task_1")
        tracker.complete_task("task_1")
        
        tracker.start_task("task_2")
        tracker.fail_task("task_2", "Error")
        
        tracker.start_task("task_3")
        
        summary = tracker.get_status_summary()
        
        assert summary['total_tasks'] == 10
        assert summary['completed'] == 1
        assert summary['failed'] == 1
        assert summary['in_progress'] == 1
        assert summary['pending'] == 7
        assert 'progress_percent' in summary
        assert 'eta_seconds' in summary
        assert 'rate_per_second' in summary
        assert 'elapsed_seconds' in summary
    
    def test_register_callback(self, tracker):
        """Test callback registration."""
        callback_called = []
        
        def test_callback(summary):
            callback_called.append(summary)
        
        tracker.register_callback(test_callback)
        assert test_callback in tracker._callbacks
        
        # Trigger update
        tracker.start_task("task_1")
        time.sleep(0.15)  # Wait for update interval
        tracker.complete_task("task_1")
        
        # Callback should have been called
        assert len(callback_called) > 0
    
    def test_unregister_callback(self, tracker):
        """Test callback unregistration."""
        callback_called = []
        
        def test_callback(summary):
            callback_called.append(summary)
        
        tracker.register_callback(test_callback)
        tracker.unregister_callback(test_callback)
        
        assert test_callback not in tracker._callbacks
        
        # Trigger update
        tracker.start_task("task_1")
        time.sleep(0.15)
        tracker.complete_task("task_1")
        
        # Callback should not have been called
        assert len(callback_called) == 0
    
    def test_callback_error_handling(self, tracker):
        """Test callback error handling."""
        def failing_callback(summary):
            raise ValueError("Test error")
        
        tracker.register_callback(failing_callback)
        
        # Should not crash when callback fails
        tracker.start_task("task_1")
        time.sleep(0.15)
        tracker.complete_task("task_1")
    
    def test_reset(self, tracker):
        """Test progress tracker reset."""
        # Add some tasks
        tracker.start_task("task_1")
        tracker.complete_task("task_1")
        tracker.start_task("task_2")
        
        # Reset
        tracker.reset()
        
        assert len(tracker._tasks) == 0
        assert tracker.get_completed_count() == 0
        assert tracker.get_in_progress_count() == 0
    
    def test_thread_safety(self, tracker):
        """Test thread-safe operations."""
        def worker(task_id):
            tracker.start_task(task_id)
            time.sleep(0.01)
            tracker.complete_task(task_id)
        
        # Create multiple threads
        threads = []
        for i in range(10):
            thread = Thread(target=worker, args=(f"task_{i}",))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify all tasks completed
        assert tracker.get_completed_count() == 10


class TestProgressTrackerIntegration:
    """Integration tests for ProgressTracker."""
    
    def test_complete_workflow(self, logger):
        """Test complete tracking workflow."""
        tracker = ProgressTracker(total_tasks=5, logger=logger, update_interval=0.1)
        
        # Track progress
        updates = []
        
        def track_updates(summary):
            updates.append(summary)
        
        tracker.register_callback(track_updates)
        
        # Process tasks
        for i in range(5):
            tracker.start_task(f"task_{i}")
            time.sleep(0.05)
            
            if i < 4:  # Complete first 4
                tracker.complete_task(f"task_{i}")
            else:  # Fail last one
                tracker.fail_task(f"task_{i}", "Test error")
        
        # Verify final state
        assert tracker.get_completed_count() == 4
        assert tracker.get_failed_count() == 1
        assert tracker.get_progress() == 80.0  # 400/5 = 80%
        
        # Verify updates were received
        assert len(updates) > 0
    
    def test_mixed_task_states(self, logger):
        """Test with mixed task states."""
        tracker = ProgressTracker(total_tasks=10, logger=logger)
        
        # Complete some
        for i in range(3):
            tracker.start_task(f"complete_{i}")
            tracker.complete_task(f"complete_{i}")
        
        # Fail some
        for i in range(2):
            tracker.start_task(f"fail_{i}")
            tracker.fail_task(f"fail_{i}", "Error")
        
        # Leave some in progress
        for i in range(2):
            tracker.start_task(f"progress_{i}")
            tracker.update_task_progress(f"progress_{i}", 50.0)
        
        # Verify counts
        summary = tracker.get_status_summary()
        assert summary['completed'] == 3
        assert summary['failed'] == 2
        assert summary['in_progress'] == 2
        assert summary['pending'] == 3


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
