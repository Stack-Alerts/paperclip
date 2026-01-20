"""
Tests for Optimizer V3 Resource Monitor
"""

import pytest
import time
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from threading import Thread

from src.optimizer_v3.core.resource_monitor import (
    ResourceMonitor,
    ResourceSnapshot,
    ResourceType,
    ResourceStatus
)
from src.optimizer_v3.core.logger import OptimizerLogger


@pytest.fixture
def logger():
    """Create test logger."""
    return OptimizerLogger('test_resource_monitor', log_dir='logs/test')


@pytest.fixture
def monitor(logger):
    """Create test resource monitor."""
    return ResourceMonitor(
        logger=logger,
        cpu_threshold=90.0,
        memory_threshold=85.0,
        disk_threshold=90.0,
        check_interval=0.5,
        history_length=10
    )


class TestResourceSnapshot:
    """Test ResourceSnapshot dataclass."""
    
    def test_initialization(self):
        """Test ResourceSnapshot initialization."""
        snapshot = ResourceSnapshot(
            timestamp=datetime.now(),
            cpu_percent=50.0,
            memory_percent=60.0,
            memory_available_mb=8192.0,
            disk_percent=70.0,
            disk_available_gb=100.0
        )
        
        assert snapshot.cpu_percent == 50.0
        assert snapshot.memory_percent == 60.0
        assert snapshot.memory_available_mb == 8192.0
        assert snapshot.disk_percent == 70.0
        assert snapshot.disk_available_gb == 100.0
        assert snapshot.network_sent_mb == 0.0
        assert snapshot.network_recv_mb == 0.0
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        timestamp = datetime.now()
        snapshot = ResourceSnapshot(
            timestamp=timestamp,
            cpu_percent=50.0,
            memory_percent=60.0,
            memory_available_mb=8192.0,
            disk_percent=70.0,
            disk_available_gb=100.0,
            network_sent_mb=10.5,
            network_recv_mb=20.3,
            metadata={'test': True}
        )
        
        result = snapshot.to_dict()
        
        assert result['timestamp'] == timestamp.isoformat()
        assert result['cpu_percent'] == 50.0
        assert result['memory_percent'] == 60.0
        assert result['memory_available_mb'] == 8192.0
        assert result['disk_percent'] == 70.0
        assert result['disk_available_gb'] == 100.0
        assert result['network_sent_mb'] == 10.5
        assert result['network_recv_mb'] == 20.3
        assert result['metadata'] == {'test': True}


class TestResourceMonitor:
    """Test ResourceMonitor class."""
    
    def test_initialization(self, monitor, logger):
        """Test initialization."""
        assert monitor.logger == logger
        assert monitor.cpu_threshold == 90.0
        assert monitor.memory_threshold == 85.0
        assert monitor.disk_threshold == 90.0
        assert monitor.check_interval == 0.5
        assert monitor.history_length == 10
        assert not monitor.is_running()
        assert len(monitor._history) == 0
        assert len(monitor._callbacks) == 0
    
    def test_get_current_usage(self, monitor):
        """Test getting current resource usage."""
        snapshot = monitor.get_current_usage()
        
        assert isinstance(snapshot, ResourceSnapshot)
        assert isinstance(snapshot.timestamp, datetime)
        assert 0 <= snapshot.cpu_percent <= 100
        assert 0 <= snapshot.memory_percent <= 100
        assert snapshot.memory_available_mb >= 0
        assert 0 <= snapshot.disk_percent <= 100
        assert snapshot.disk_available_gb >= 0
    
    def test_get_current_usage_network(self, monitor):
        """Test network metrics in current usage."""
        # First call initializes network tracking
        snapshot1 = monitor.get_current_usage()
        assert snapshot1.network_sent_mb == 0.0
        assert snapshot1.network_recv_mb == 0.0
        
        # Second call should have network delta
        time.sleep(0.1)
        snapshot2 = monitor.get_current_usage()
        assert isinstance(snapshot2.network_sent_mb, float)
        assert isinstance(snapshot2.network_recv_mb, float)
    
    def test_get_status_normal(self, monitor):
        """Test status when all resources normal."""
        with patch('psutil.cpu_percent', return_value=50.0):
            with patch('psutil.virtual_memory') as mock_mem:
                mock_mem.return_value.percent = 50.0
                mock_mem.return_value.available = 8192 * 1024 * 1024
                
                with patch('psutil.disk_usage') as mock_disk:
                    mock_disk.return_value.percent = 50.0
                    mock_disk.return_value.free = 100 * 1024 * 1024 * 1024
                    
                    status = monitor.get_status()
                    assert status == ResourceStatus.NORMAL
    
    def test_get_status_warning(self, monitor):
        """Test status when resources at warning level."""
        with patch('psutil.cpu_percent', return_value=75.0):  # 75% > 72% (80% of 90%)
            with patch('psutil.virtual_memory') as mock_mem:
                mock_mem.return_value.percent = 50.0
                mock_mem.return_value.available = 8192 * 1024 * 1024
                
                with patch('psutil.disk_usage') as mock_disk:
                    mock_disk.return_value.percent = 50.0
                    mock_disk.return_value.free = 100 * 1024 * 1024 * 1024
                    
                    status = monitor.get_status()
                    assert status == ResourceStatus.WARNING
    
    def test_get_status_critical(self, monitor):
        """Test status when resources critical."""
        with patch('psutil.cpu_percent', return_value=95.0):
            with patch('psutil.virtual_memory') as mock_mem:
                mock_mem.return_value.percent = 50.0
                mock_mem.return_value.available = 8192 * 1024 * 1024
                
                with patch('psutil.disk_usage') as mock_disk:
                    mock_disk.return_value.percent = 50.0
                    mock_disk.return_value.free = 100 * 1024 * 1024 * 1024
                    
                    status = monitor.get_status()
                    assert status == ResourceStatus.CRITICAL
    
    def test_get_history_empty(self, monitor):
        """Test getting empty history."""
        history = monitor.get_history()
        assert history == []
    
    def test_get_average_usage_empty(self, monitor):
        """Test average usage with no history."""
        avg = monitor.get_average_usage()
        
        assert avg['cpu_percent'] == 0.0
        assert avg['memory_percent'] == 0.0
        assert avg['disk_percent'] == 0.0
        assert avg['samples'] == 0
    
    def test_get_average_usage(self, monitor):
        """Test average usage calculation."""
        # Add some snapshots to history
        for i in range(5):
            snapshot = ResourceSnapshot(
                timestamp=datetime.now(),
                cpu_percent=50.0 + i * 10,
                memory_percent=40.0 + i * 5,
                memory_available_mb=8192.0,
                disk_percent=60.0 + i * 2,
                disk_available_gb=100.0
            )
            monitor._history.append(snapshot)
        
        avg = monitor.get_average_usage()
        
        assert avg['cpu_percent'] == pytest.approx(70.0)  # (50+60+70+80+90)/5
        assert avg['memory_percent'] == pytest.approx(50.0)  # (40+45+50+55+60)/5
        assert avg['disk_percent'] == pytest.approx(64.0)  # (60+62+64+66+68)/5
        assert avg['samples'] == 5
    
    def test_get_peak_usage_empty(self, monitor):
        """Test peak usage with no history."""
        peak = monitor.get_peak_usage()
        
        assert peak['cpu_percent'] == 0.0
        assert peak['memory_percent'] == 0.0
        assert peak['disk_percent'] == 0.0
    
    def test_get_peak_usage(self, monitor):
        """Test peak usage calculation."""
        # Add some snapshots to history
        for i in range(5):
            snapshot = ResourceSnapshot(
                timestamp=datetime.now(),
                cpu_percent=50.0 + i * 10,
                memory_percent=40.0 + i * 5,
                memory_available_mb=8192.0,
                disk_percent=60.0 + i * 2,
                disk_available_gb=100.0
            )
            monitor._history.append(snapshot)
        
        peak = monitor.get_peak_usage()
        
        assert peak['cpu_percent'] == 90.0
        assert peak['memory_percent'] == 60.0
        assert peak['disk_percent'] == 68.0
    
    def test_register_callback(self, monitor):
        """Test callback registration."""
        def test_callback(snapshot, status):
            pass
        
        monitor.register_callback(test_callback)
        assert test_callback in monitor._callbacks
        
        # Try registering same callback again
        monitor.register_callback(test_callback)
        assert monitor._callbacks.count(test_callback) == 1  # Should only be once
    
    def test_unregister_callback(self, monitor):
        """Test callback unregistration."""
        def test_callback(snapshot, status):
            pass
        
        monitor.register_callback(test_callback)
        assert test_callback in monitor._callbacks
        
        monitor.unregister_callback(test_callback)
        assert test_callback not in monitor._callbacks
    
    def test_clear_history(self, monitor):
        """Test clearing history."""
        # Add some snapshots
        for i in range(5):
            snapshot = ResourceSnapshot(
                timestamp=datetime.now(),
                cpu_percent=50.0,
                memory_percent=60.0,
                memory_available_mb=8192.0,
                disk_percent=70.0,
                disk_available_gb=100.0
            )
            monitor._history.append(snapshot)
        
        assert len(monitor._history) == 5
        
        monitor.clear_history()
        assert len(monitor._history) == 0
    
    def test_start_stop(self, monitor):
        """Test starting and stopping monitor."""
        assert not monitor.is_running()
        
        monitor.start()
        assert monitor.is_running()
        assert monitor._monitor_thread is not None
        
        # Try starting again (should not create new thread)
        monitor.start()
        assert monitor.is_running()
        
        monitor.stop()
        assert not monitor.is_running()
        time.sleep(0.1)  # Let thread finish
        assert monitor._monitor_thread is None
    
    def test_start_stop_multiple_times(self, monitor):
        """Test starting and stopping multiple times."""
        for i in range(3):
            monitor.start()
            assert monitor.is_running()
            time.sleep(0.2)
            
            monitor.stop()
            assert not monitor.is_running()
    
    def test_monitoring_loop_collects_history(self, monitor):
        """Test that monitoring loop collects history."""
        monitor.start()
        time.sleep(1.5)  # Wait for 3 snapshots (0.5s interval)
        monitor.stop()
        
        history = monitor.get_history()
        assert len(history) >= 2  # Should have at least 2 snapshots
    
    def test_monitoring_loop_trims_history(self, logger):
        """Test that history is trimmed to max length."""
        monitor = ResourceMonitor(
            logger=logger,
            check_interval=0.1,
            history_length=3
        )
        
        monitor.start()
        time.sleep(0.6)  # Wait for > 3 snapshots
        monitor.stop()
        
        history = monitor.get_history()
        assert len(history) <= 3  # Should be trimmed
    
    def test_monitoring_loop_calls_callbacks(self, monitor):
        """Test that monitoring loop calls callbacks."""
        callback_calls = []
        
        def test_callback(snapshot, status):
            callback_calls.append((snapshot, status))
        
        monitor.register_callback(test_callback)
        monitor.start()
        time.sleep(0.7)  # Wait for at least one callback
        monitor.stop()
        
        assert len(callback_calls) > 0
        assert all(isinstance(s, ResourceSnapshot) for s, _ in callback_calls)
        assert all(isinstance(st, ResourceStatus) for _, st in callback_calls)
    
    def test_monitoring_loop_handles_callback_errors(self, monitor):
        """Test that callback errors don't crash monitor."""
        def failing_callback(snapshot, status):
            raise ValueError("Test error")
        
        monitor.register_callback(failing_callback)
        monitor.start()
        time.sleep(0.7)
        monitor.stop()
        
        # Monitor should still be running despite callback error
        # (well, was running until we stopped it)
        assert len(monitor._history) > 0
    
    def test_monitoring_loop_handles_monitoring_errors(self, monitor):
        """Test that monitoring errors don't crash loop."""
        monitor.start()
        
        # Simulate an error in get_current_usage by breaking psutil
        with patch('psutil.cpu_percent', side_effect=Exception("Test error")):
            time.sleep(0.7)
        
        monitor.stop()
        # Monitor should have handled the error gracefully
    
    def test_monitoring_loop_warning_log(self, logger):
        """Test that WARNING status is logged in monitoring loop."""
        # Create monitor with low threshold
        monitor = ResourceMonitor(
            logger=logger,
            cpu_threshold=70.0,  # Low threshold
            memory_threshold=70.0,
            check_interval=0.2
        )
        
        # Mock to return 60% CPU (which is 86% of 70, above 80% warning threshold)
        with patch('psutil.cpu_percent', return_value=60.0):
            with patch('psutil.virtual_memory') as mock_mem:
                mock_mem.return_value.percent = 45.0
                mock_mem.return_value.available = 8192 * 1024 * 1024
                
                with patch('psutil.disk_usage') as mock_disk:
                    mock_disk.return_value.percent = 45.0
                    mock_disk.return_value.free = 100 * 1024 * 1024 * 1024
                    
                    with patch('psutil.net_io_counters') as mock_net:
                        mock_net.return_value.bytes_sent = 0
                        mock_net.return_value.bytes_recv = 0
                        
                        monitor.start()
                        time.sleep(0.5)
                        monitor.stop()
        
        # Verify monitor ran
        assert len(monitor._history) > 0
    
    def test_stop_when_not_running(self, monitor):
        """Test stopping when not running."""
        assert not monitor.is_running()
        monitor.stop()  # Should not crash
        assert not monitor.is_running()


class TestResourceMonitorIntegration:
    """Integration tests for ResourceMonitor."""
    
    def test_full_monitoring_cycle(self, logger):
        """Test complete monitoring cycle."""
        monitor = ResourceMonitor(
            logger=logger,
            cpu_threshold=90.0,
            memory_threshold=85.0,
            check_interval=0.2,
            history_length=10
        )
        
        updates = []
        
        def track_updates(snapshot, status):
            updates.append((snapshot, status))
        
        monitor.register_callback(track_updates)
        monitor.start()
        
        # Let it run for a bit
        time.sleep(0.7)
        
        monitor.stop()
        
        # Verify we got updates
        assert len(updates) > 0
        
        # Verify history was populated
        history = monitor.get_history()
        assert len(history) > 0
        
        # Verify statistics
        avg = monitor.get_average_usage()
        assert avg['samples'] > 0
        assert avg['cpu_percent'] >= 0
        
        peak = monitor.get_peak_usage()
        assert peak['cpu_percent'] >= 0
    
    def test_threshold_detection_critical(self, logger):
        """Test critical threshold detection with mocked high usage."""
        monitor = ResourceMonitor(
            logger=logger,
            cpu_threshold=50.0,  # Low threshold for testing
            memory_threshold=50.0,
            check_interval=0.2
        )
        
        critical_detected = []
        
        def check_critical(snapshot, status):
            if status == ResourceStatus.CRITICAL:
                critical_detected.append(snapshot)
        
        monitor.register_callback(check_critical)
        
        with patch('psutil.cpu_percent', return_value=95.0):
            with patch('psutil.virtual_memory') as mock_mem:
                mock_mem.return_value.percent = 50.0
                mock_mem.return_value.available = 8192 * 1024 * 1024
                
                with patch('psutil.disk_usage') as mock_disk:
                    mock_disk.return_value.percent = 50.0
                    mock_disk.return_value.free = 100 * 1024 * 1024 * 1024
                    
                    monitor.start()
                    time.sleep(0.5)
                    monitor.stop()
        
        # Should have detected critical status
        assert len(critical_detected) > 0
    
    def test_threshold_detection_warning(self, logger):
        """Test warning threshold detection with mocked moderate usage."""
        monitor = ResourceMonitor(
            logger=logger,
            cpu_threshold=90.0,
            memory_threshold=85.0,
            check_interval=0.2
        )
        
        warning_detected = []
        
        def check_warning(snapshot, status):
            if status == ResourceStatus.WARNING:
                warning_detected.append(snapshot)
        
        monitor.register_callback(check_warning)
        
        # Set CPU at 75% (above 72% warning threshold)
        with patch('psutil.cpu_percent', return_value=75.0):
            with patch('psutil.virtual_memory') as mock_mem:
                mock_mem.return_value.percent = 50.0
                mock_mem.return_value.available = 8192 * 1024 * 1024
                
                with patch('psutil.disk_usage') as mock_disk:
                    mock_disk.return_value.percent = 50.0
                    mock_disk.return_value.free = 100 * 1024 * 1024 * 1024
                    
                    monitor.start()
                    time.sleep(0.5)
                    monitor.stop()
        
        # Should have detected warning status
        assert len(warning_detected) > 0
    
    def test_thread_safety(self, monitor):
        """Test thread-safe operations."""
        def writer_thread():
            for i in range(10):
                snapshot = ResourceSnapshot(
                    timestamp=datetime.now(),
                    cpu_percent=50.0,
                    memory_percent=60.0,
                    memory_available_mb=8192.0,
                    disk_percent=70.0,
                    disk_available_gb=100.0
                )
                monitor._history.append(snapshot)
                time.sleep(0.01)
        
        def reader_thread():
            for i in range(10):
                _ = monitor.get_history()
                _ = monitor.get_average_usage()
                _ = monitor.get_peak_usage()
                time.sleep(0.01)
        
        threads = []
        for i in range(3):
            threads.append(Thread(target=writer_thread))
            threads.append(Thread(target=reader_thread))
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # Should not crash due to thread safety


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
