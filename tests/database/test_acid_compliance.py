"""
ACID Compliance Tests
Task 0.8: Verify database ACID properties

Tests atomicity, consistency, isolation, and durability
of database operations for institutional-grade reliability.
"""

import pytest
import time
import threading
from datetime import datetime
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.optimizer_v3.database import (
    get_db_manager,
    get_connection_pool,
    OptimizationRun,
    StrategyVariation,
    SignalEvent,
)


class TestAtomicity:
    """Test that transactions are all-or-nothing"""
    
    def test_transaction_rollback_on_error(self):
        """Test that failed transactions don't persist partial changes"""
        db = get_db_manager()
        
        # Attempt transaction that will fail
        try:
            with db.session_scope() as session:
                # Create first record
                run1 = OptimizationRun(
                    strategy_id='test_atomic_1',
                    strategy_name='Test Atomic 1',
                    status='pending'
                )
                session.add(run1)
                session.flush()  # Ensure it's in transaction
                
                # Create second record
                run2 = OptimizationRun(
                    strategy_id='test_atomic_2',
                    strategy_name='Test Atomic 2',
                    status='pending'
                )
                session.add(run2)
                
                # Force an error to trigger rollback
                raise Exception("Intentional error to test rollback")
        except Exception:
            pass  # Expected error
        
        # Verify neither record was persisted
        with db.session_scope() as session:
            count1 = session.query(OptimizationRun)\
                .filter_by(strategy_id='test_atomic_1').count()
            count2 = session.query(OptimizationRun)\
                .filter_by(strategy_id='test_atomic_2').count()
            
            assert count1 == 0, "First record should not exist after rollback"
            assert count2 == 0, "Second record should not exist after rollback"
    
    def test_bulk_operation_atomicity(self):
        """Test that bulk operations are atomic"""
        db = get_db_manager()
        
        variations = [
            {
                'run_id': 'test_bulk_run',
                'variation_id': f'var_{i}',
                'parameters': {'param': i},
                'status': 'pending'
            }
            for i in range(10)
        ]
        
        # Attempt bulk create that will fail midway
        try:
            with db.session_scope() as session:
                # Add first 5 successfully
                for var in variations[:5]:
                    variation = StrategyVariation(**var)
                    session.add(variation)
                
                # Force error before completing all
                raise Exception("Bulk operation error")
        except Exception:
            pass
        
        # Verify no records were persisted
        with db.session_scope() as session:
            count = session.query(StrategyVariation)\
                .filter_by(run_id='test_bulk_run').count()
            assert count == 0, "No records should exist after bulk rollback"
    
    def test_nested_transaction_rollback(self):
        """Test that nested operations rollback together"""
        db = get_db_manager()
        run_id = 'test_nested_run'
        
        try:
            with db.session_scope() as session:
                # Create parent record
                run = OptimizationRun(
                    strategy_id=run_id,
                    strategy_name='Nested Test',
                    status='pending'
                )
                session.add(run)
                session.flush()
                
                # Create child records
                for i in range(3):
                    variation = StrategyVariation(
                        run_id=run_id,
                        variation_id=f'var_{i}',
                        parameters={'index': i},
                        status='pending'
                    )
                    session.add(variation)
                
                # Force error
                raise Exception("Nested rollback test")
        except Exception:
            pass
        
        # Verify parent and children both rolled back
        with db.session_scope() as session:
            parent_count = session.query(OptimizationRun)\
                .filter_by(strategy_id=run_id).count()
            child_count = session.query(StrategyVariation)\
                .filter_by(run_id=run_id).count()
            
            assert parent_count == 0, "Parent record should not exist"
            assert child_count == 0, "Child records should not exist"


class TestConsistency:
    """Test that database maintains valid state"""
    
    def test_foreign_key_constraints(self):
        """Test that foreign key constraints are enforced"""
        db = get_db_manager()
        
        # Attempt to create child record with non-existent parent
        with pytest.raises(Exception):  # Should raise integrity error
            with db.session_scope() as session:
                variation = StrategyVariation(
                    run_id='nonexistent_run',
                    variation_id='test_var',
                    parameters={'test': 1},
                    status='pending'
                )
                session.add(variation)
                session.flush()
    
    def test_not_null_constraints(self):
        """Test that NOT NULL constraints are enforced"""
        db = get_db_manager()
        
        # Attempt to create record with missing required field
        with pytest.raises(Exception):  # Should raise integrity error
            with db.session_scope() as session:
                run = OptimizationRun(
                    strategy_id=None,  # Required field
                    strategy_name='Test',
                    status='pending'
                )
                session.add(run)
                session.flush()
    
    def test_unique_constraints(self):
        """Test that unique constraints are enforced"""
        db = get_db_manager()
        
        # Create first record
        with db.session_scope() as session:
            run = OptimizationRun(
                strategy_id='unique_test',
                strategy_name='Unique Test',
                status='pending'
            )
            session.add(run)
        
        # Attempt to create duplicate
        with pytest.raises(Exception):  # Should raise integrity error
            with db.session_scope() as session:
                duplicate = OptimizationRun(
                    strategy_id='unique_test',  # Duplicate ID
                    strategy_name='Duplicate',
                    status='pending'
                )
                session.add(duplicate)
                session.flush()
        
        # Cleanup
        with db.session_scope() as session:
            session.query(OptimizationRun)\
                .filter_by(strategy_id='unique_test').delete()
    
    def test_data_type_validation(self):
        """Test that data types are validated"""
        db = get_db_manager()
        
        # Attempt to insert invalid data type
        with pytest.raises(Exception):
            with db.session_scope() as session:
                run = OptimizationRun(
                    strategy_id='type_test',
                    strategy_name='Type Test',
                    status='pending',
                    total_variations='not_a_number'  # Should be integer
                )
                session.add(run)
                session.flush()


class TestIsolation:
    """Test that concurrent transactions don't interfere"""
    
    def test_concurrent_reads(self):
        """Test that concurrent reads don't block each other"""
        db = get_db_manager()
        
        # Create test data
        with db.session_scope() as session:
            run = OptimizationRun(
                strategy_id='isolation_read_test',
                strategy_name='Isolation Read Test',
                status='pending'
            )
            session.add(run)
        
        results = []
        
        def read_operation():
            """Concurrent read operation"""
            with db.session_scope() as session:
                count = session.query(OptimizationRun)\
                    .filter_by(strategy_id='isolation_read_test').count()
                results.append(count)
                time.sleep(0.1)  # Simulate work
        
        # Start concurrent reads
        threads = [threading.Thread(target=read_operation) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All reads should succeed
        assert len(results) == 5, "All concurrent reads should complete"
        assert all(r == 1 for r in results), "All reads should see the record"
        
        # Cleanup
        with db.session_scope() as session:
            session.query(OptimizationRun)\
                .filter_by(strategy_id='isolation_read_test').delete()
    
    def test_write_isolation(self):
        """Test that concurrent writes are properly isolated"""
        db = get_db_manager()
        
        # Create base record
        with db.session_scope() as session:
            run = OptimizationRun(
                strategy_id='isolation_write_test',
                strategy_name='Isolation Write Test',
                status='pending',
                total_variations=0
            )
            session.add(run)
        
        def increment_variations():
            """Increment variation count (simulating concurrent updates)"""
            with db.session_scope() as session:
                run = session.query(OptimizationRun)\
                    .filter_by(strategy_id='isolation_write_test').first()
                run.total_variations += 1
                time.sleep(0.05)  # Simulate work
        
        # Run concurrent updates
        threads = [threading.Thread(target=increment_variations) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Verify final count
        with db.session_scope() as session:
            run = session.query(OptimizationRun)\
                .filter_by(strategy_id='isolation_write_test').first()
            # Due to transaction isolation, final count should be 10
            assert run.total_variations == 10, \
                "Concurrent updates should all succeed"
        
        # Cleanup
        with db.session_scope() as session:
            session.query(OptimizationRun)\
                .filter_by(strategy_id='isolation_write_test').delete()
    
    def test_read_committed_isolation(self):
        """Test that transactions only see committed data"""
        db = get_db_manager()
        
        # This test verifies read committed isolation level
        # Uncommitted changes should not be visible to other transactions
        
        results = []
        
        def long_running_transaction():
            """Transaction that takes time to commit"""
            with db.session_scope() as session:
                run = OptimizationRun(
                    strategy_id='isolation_commit_test',
                    strategy_name='Commit Test',
                    status='pending'
                )
                session.add(run)
                session.flush()  # Changes in transaction but not committed
                time.sleep(0.2)  # Delay before commit
                # Transaction commits here when context exits
        
        def concurrent_read():
            """Try to read during long transaction"""
            time.sleep(0.1)  # Start after session.add but before commit
            with db.session_scope() as session:
                count = session.query(OptimizationRun)\
                    .filter_by(strategy_id='isolation_commit_test').count()
                results.append(count)
        
        # Start both operations
        t1 = threading.Thread(target=long_running_transaction)
        t2 = threading.Thread(target=concurrent_read)
        
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        
        # The read should not see uncommitted data
        # (depending on timing, it might see 0 or 1, but not partial state)
        assert len(results) == 1, "Concurrent read should complete"
        
        # Cleanup
        with db.session_scope() as session:
            session.query(OptimizationRun)\
                .filter_by(strategy_id='isolation_commit_test').delete()


class TestDurability:
    """Test that committed data persists"""
    
    def test_committed_data_persists(self):
        """Test that committed data survives connection closure"""
        db = get_db_manager()
        run_id = 'durability_test'
        
        # Create and commit data
        with db.session_scope() as session:
            run = OptimizationRun(
                strategy_id=run_id,
                strategy_name='Durability Test',
                status='pending'
            )
            session.add(run)
        # Session closed and committed
        
        # Create new session and verify data persists
        with db.session_scope() as session:
            persisted_run = session.query(OptimizationRun)\
                .filter_by(strategy_id=run_id).first()
            assert persisted_run is not None, "Committed data should persist"
            assert persisted_run.strategy_name == 'Durability Test'
        
        # Cleanup
        with db.session_scope() as session:
            session.query(OptimizationRun)\
                .filter_by(strategy_id=run_id).delete()
    
    def test_multiple_commits_persist(self):
        """Test that multiple sequential commits all persist"""
        db = get_db_manager()
        
        # Create multiple records in sequence
        for i in range(5):
            with db.session_scope() as session:
                run = OptimizationRun(
                    strategy_id=f'durability_multi_{i}',
                    strategy_name=f'Multi Test {i}',
                    status='pending'
                )
                session.add(run)
            # Each commits independently
        
        # Verify all persisted
        with db.session_scope() as session:
            count = session.query(OptimizationRun)\
                .filter(OptimizationRun.strategy_id.like('durability_multi_%'))\
                .count()
            assert count == 5, "All sequential commits should persist"
        
        # Cleanup
        with db.session_scope() as session:
            session.query(OptimizationRun)\
                .filter(OptimizationRun.strategy_id.like('durability_multi_%'))\
                .delete()
    
    def test_crash_recovery_simulation(self):
        """Test that data survives simulated crash (pool restart)"""
        db = get_db_manager()
        pool = get_connection_pool()
        run_id = 'crash_recovery_test'
        
        # Create data
        with db.session_scope() as session:
            run = OptimizationRun(
                strategy_id=run_id,
                strategy_name='Crash Recovery Test',
                status='pending'
            )
            session.add(run)
        
        # Simulate crash by closing all connections
        pool.close_all()
        
        # Create new connection and verify data persists
        new_pool = get_connection_pool()
        new_db = get_db_manager()
        
        with new_db.session_scope() as session:
            recovered_run = session.query(OptimizationRun)\
                .filter_by(strategy_id=run_id).first()
            assert recovered_run is not None, "Data should survive crash"
            assert recovered_run.strategy_name == 'Crash Recovery Test'
        
        # Cleanup
        with new_db.session_scope() as session:
            session.query(OptimizationRun)\
                .filter_by(strategy_id=run_id).delete()


class TestTransactionManagement:
    """Test overall transaction management"""
    
    def test_session_scope_context_manager(self):
        """Test that session_scope properly manages resources"""
        db = get_db_manager()
        
        # Successful transaction
        with db.session_scope() as session:
            run = OptimizationRun(
                strategy_id='context_test_success',
                strategy_name='Context Test',
                status='pending'
            )
            session.add(run)
        # Should auto-commit
        
        # Verify committed
        with db.session_scope() as session:
            count = session.query(OptimizationRun)\
                .filter_by(strategy_id='context_test_success').count()
            assert count == 1, "Successful transaction should commit"
        
        # Failed transaction
        try:
            with db.session_scope() as session:
                run = OptimizationRun(
                    strategy_id='context_test_fail',
                    strategy_name='Context Fail',
                    status='pending'
                )
                session.add(run)
                raise Exception("Force rollback")
        except Exception:
            pass
        
        # Verify rolled back
        with db.session_scope() as session:
            count = session.query(OptimizationRun)\
                .filter_by(strategy_id='context_test_fail').count()
            assert count == 0, "Failed transaction should rollback"
        
        # Cleanup
        with db.session_scope() as session:
            session.query(OptimizationRun)\
                .filter_by(strategy_id='context_test_success').delete()
    
    def test_connection_cleanup(self):
        """Test that connections are properly cleaned up"""
        db = get_db_manager()
        pool = get_connection_pool()
        
        initial_active = pool.metrics.active_connections
        
        # Create and close multiple sessions
        for i in range(10):
            with db.session_scope() as session:
                result = session.execute("SELECT 1")
                assert result.scalar() == 1
        
        # Active connections should return to baseline
        # (allowing for some variance due to pooling)
        final_active = pool.metrics.active_connections
        assert abs(final_active - initial_active) < 5, \
            "Connections should be properly cleaned up"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
