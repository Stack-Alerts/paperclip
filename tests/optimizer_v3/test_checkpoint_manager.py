"""
Tests for Optimizer V3 Checkpoint Manager
"""

import pytest
import json
import gzip
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from src.optimizer_v3.core.checkpoint_manager import (
    CheckpointManager,
    CheckpointData
)
from src.optimizer_v3.core.logger import OptimizerLogger


@pytest.fixture
def logger():
    """Create test logger."""
    return OptimizerLogger('test_checkpoint', log_dir='logs/test')


@pytest.fixture
def temp_checkpoint_dir():
    """Create temporary checkpoint directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def checkpoint_manager(logger, temp_checkpoint_dir):
    """Create test checkpoint manager."""
    return CheckpointManager(
        logger=logger,
        checkpoint_dir=temp_checkpoint_dir,
        interval=5,
        compression=True,
        retention_count=3
    )


class TestCheckpointData:
    """Test CheckpointData dataclass."""
    
    def test_initialization(self):
        """Test CheckpointData initialization."""
        data = CheckpointData(
            timestamp=datetime.now().isoformat(),
            strategy_id='test',
            total_configs=10,
            completed_count=5,
            results=[{'id': 1}, {'id': 2}],
            best_config={'id': 2},
            best_metric=1.5,
            metadata={'test': True}
        )
        
        assert data.strategy_id == 'test'
        assert data.total_configs == 10
        assert data.completed_count == 5
        assert len(data.results) == 2
        assert data.best_config == {'id': 2}
        assert data.best_metric == 1.5


class TestCheckpointManager:
    """Test CheckpointManager class."""
    
    def test_initialization(self, checkpoint_manager, temp_checkpoint_dir):
        """Test initialization."""
        assert checkpoint_manager.checkpoint_dir == Path(temp_checkpoint_dir)
        assert checkpoint_manager.interval == 5
        assert checkpoint_manager.compression is True
        assert checkpoint_manager.retention_count == 3
        assert checkpoint_manager.checkpoint_dir.exists()
    
    def test_save_checkpoint(self, checkpoint_manager):
        """Test saving checkpoint."""
        results = [{'id': 1, 'sharpe': 1.5}, {'id': 2, 'sharpe': 2.0}]
        
        filepath = checkpoint_manager.save_checkpoint(
            strategy_id='test_strategy',
            completed_count=5,
            total_configs=10,
            results=results,
            best_config={'id': 2},
            best_metric=2.0
        )
        
        assert filepath.exists()
        assert 'test_strategy' in filepath.name
        assert filepath.suffix == '.gz'
    
    def test_load_checkpoint(self, checkpoint_manager):
        """Test loading checkpoint."""
        results = [{'id': 1}, {'id': 2}]
        
        # Save first
        filepath = checkpoint_manager.save_checkpoint(
            strategy_id='test_strategy',
            completed_count=3,
            total_configs=10,
            results=results,
            best_config={'id': 2},
            best_metric=1.5
        )
        
        # Load
        data = checkpoint_manager.load_checkpoint(filepath)
        
        assert data is not None
        assert data.strategy_id == 'test_strategy'
        assert data.completed_count == 3
        assert data.total_configs == 10
        assert len(data.results) == 2
        assert data.best_metric == 1.5
    
    def test_load_nonexistent_checkpoint(self, checkpoint_manager):
        """Test loading nonexistent checkpoint."""
        data = checkpoint_manager.load_checkpoint(Path('/nonexistent/path.json.gz'))
        assert data is None
    
    def test_get_latest_checkpoint(self, checkpoint_manager):
        """Test getting latest checkpoint."""
        import time
        # Save multiple checkpoints
        for i in range(3):
            checkpoint_manager.save_checkpoint(
                strategy_id='test_strategy',
                completed_count=i + 1,
                total_configs=10,
                results=[]
            )
            time.sleep(0.01)  # Ensure different timestamps
        
        latest = checkpoint_manager.get_latest_checkpoint('test_strategy')
        assert latest is not None
        assert 'test_strategy_3' in latest.name
    
    def test_get_latest_checkpoint_no_exists(self, checkpoint_manager):
        """Test getting latest when none exist."""
        latest = checkpoint_manager.get_latest_checkpoint('nonexistent')
        assert latest is None
    
    def test_should_save(self, checkpoint_manager):
        """Test should_save logic."""
        assert not checkpoint_manager.should_save(0)
        assert not checkpoint_manager.should_save(1)
        assert checkpoint_manager.should_save(5)  # interval=5
        assert checkpoint_manager.should_save(10)
        assert not checkpoint_manager.should_save(11)
    
    def test_export_results_csv(self, checkpoint_manager, temp_checkpoint_dir):
        """Test CSV export."""
        results = [
            {'id': 1, 'sharpe': 1.5, 'pnl': 100},
            {'id': 2, 'sharpe': 2.0, 'pnl': 200}
        ]
        
        output_path = Path(temp_checkpoint_dir) / 'results.csv'
        success = checkpoint_manager.export_results(results, output_path, format='csv')
        
        assert success is True
        assert output_path.exists()
        
        # Verify content
        with open(output_path, 'r') as f:
            content = f.read()
            assert 'id,sharpe,pnl' in content
            assert '1,1.5,100' in content
    
    def test_export_results_json(self, checkpoint_manager, temp_checkpoint_dir):
        """Test JSON export."""
        results = [{'id': 1}, {'id': 2}]
        
        output_path = Path(temp_checkpoint_dir) / 'results.json'
        success = checkpoint_manager.export_results(results, output_path, format='json')
        
        assert success is True
        assert output_path.exists()
        
        # Verify content
        with open(output_path, 'r') as f:
            loaded = json.load(f)
            assert len(loaded) == 2
    
    def test_export_empty_results(self, checkpoint_manager, temp_checkpoint_dir):
        """Test exporting empty results."""
        output_path = Path(temp_checkpoint_dir) / 'empty.csv'
        success = checkpoint_manager.export_results([], output_path, format='csv')
        assert success is False
    
    def test_rollback(self, checkpoint_manager):
        """Test rollback functionality."""
        # Save checkpoint
        checkpoint_manager.save_checkpoint(
            strategy_id='test',
            completed_count=5,
            total_configs=10,
            results=[{'id': i} for i in range(5)]
        )
        
        # Rollback
        data = checkpoint_manager.rollback('test')
        
        assert data is not None
        assert data.completed_count == 5
        assert len(data.results) == 5
    
    def test_rollback_no_checkpoint(self, checkpoint_manager):
        """Test rollback when no checkpoint exists."""
        data = checkpoint_manager.rollback('nonexistent')
        assert data is None
    
    def test_retention_policy(self, checkpoint_manager):
        """Test checkpoint retention."""
        # Save more checkpoints than retention count
        for i in range(5):
            checkpoint_manager.save_checkpoint(
                strategy_id='test',
                completed_count=i + 1,
                total_configs=10,
                results=[]
            )
        
        # Should only keep 3 (retention_count)
        checkpoints = list(checkpoint_manager.checkpoint_dir.glob('checkpoint_test_*.json.gz'))
        assert len(checkpoints) <= 3
    
    def test_clear_all_checkpoints(self, checkpoint_manager):
        """Test clearing all checkpoints."""
        # Save some checkpoints
        for i in range(3):
            checkpoint_manager.save_checkpoint(
                strategy_id='test',
                completed_count=i + 1,
                total_configs=10,
                results=[]
            )
        
        count = checkpoint_manager.clear_all_checkpoints('test')
        assert count == 3
        
        # Verify they're gone
        checkpoints = list(checkpoint_manager.checkpoint_dir.glob('checkpoint_test_*.json.gz'))
        assert len(checkpoints) == 0
    
    def test_checksum_validation(self, checkpoint_manager):
        """Test checksum validation."""
        # Save checkpoint
        filepath = checkpoint_manager.save_checkpoint(
            strategy_id='test',
            completed_count=1,
            total_configs=10,
            results=[{'id': 1}]
        )
        
        # Corrupt the checkpoint
        with gzip.open(filepath, 'rt') as f:
            data = json.load(f)
        
        data['results'].append({'id': 999})  # Corrupt data
        
        with gzip.open(filepath, 'wt') as f:
            json.dump(data, f)
        
        # Should fail to load
        loaded = checkpoint_manager.load_checkpoint(filepath)
        assert loaded is None


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
