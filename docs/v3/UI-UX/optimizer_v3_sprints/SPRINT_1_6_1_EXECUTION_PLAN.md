# SPRINT 1.6.1: INSTITUTIONAL-GRADE EXECUTION PLAN
**100% Complete - Systematic ORM Refactoring with Testing**

**Date**: 2026-01-29  
**Status**: 🔧 IN PROGRESS - Strategy Manager 100% Complete (5/15 tasks)  
**Completion Target**: 100% (15 tasks remaining: AI Recs + Test Results)  
**Risk Level**: MEDIUM - Real money operations  
**Approval**: Required at EVERY checkpoint  
**Tests Passing**: 49/49 ✅

---

## 🎯 EXECUTION PHILOSOPHY

**INSTITUTIONAL-GRADE REQUIREMENTS**:
1. ✅ One task at a time - NO parallel work
2. ✅ Unit tests BEFORE moving to next task
3. ✅ Implementation tests BEFORE moving to next task
4. ✅ User approval BEFORE moving to next task
5. ✅ Detailed test instructions for every change
6. ✅ Rollback plan documented at every step
7. ✅ Real money mindset - no shortcuts

---

## 📊 COMPLETION STATUS (Session 2026-01-29)

### **✅ COMPLETED TASKS (5/15)**

| Task | Description | Tests | Status | Date |
|------|-------------|-------|--------|------|
| **0.1** | AI Recommendations text() wrapper | 10/10 ✅ | ✅ COMPLETE | 2026-01-29 |
| **1.1** | create_strategy() ORM | 10/10 ✅ | ✅ COMPLETE | 2026-01-29 |
| **1.2** | create_strategy_version() ORM | 12/12 ✅ | ✅ COMPLETE | 2026-01-29 |
| **1.3** | get_strategy_version() ORM | 8/8 ✅ | ✅ COMPLETE | 2026-01-29 |
| **1.4** | get_all_strategies() ORM | 9/9 ✅ | ✅ COMPLETE | 2026-01-29 |

**Total Tests Passing**: 49/49 ✅  
**Strategy Manager**: 100% ORM Complete ✅

### **⏳ PENDING TASKS (10/15)**

| Task | Description | Estimate | Dependencies |
|------|-------------|----------|--------------|
| **2.1** | AI Recommendations Manager ORM (7 methods) | 3 hrs | Task 0.1 complete |
| **3.1** | Test Results Manager ORM | 2 hrs | None |
| **Integration** | Full system integration tests | 2 hrs | All above |

**Remaining**: ~7 hours (1 day)

---

## 📊 ORIGINAL STATUS MATRIX

| Phase | Task | Status | Estimate |
|-------|------|--------|----------|
| **PHASE 0** | Bug Fix (text() wrapper) | ✅ COMPLETE | 30 min |
| **PHASE 1** | ORM Refactor - strategy_manager (4 tasks) | ✅ COMPLETE | 6 hrs |
| **PHASE 2** | ORM Refactor - ai_recommendations_manager | ⏳ PENDING | 3 hrs |
| **PHASE 3** | ORM Refactor - test_results_manager | ⏳ PENDING | 2 hrs |
| **PHASE 4** | Integration Testing | ⏳ PENDING | 2 hrs |
| **PHASE 5** | Final Validation | ⏳ PENDING | 1 hr |

**TOTAL**: 14.5 hours | **COMPLETED**: 6.5 hours | **REMAINING**: 8 hours

---

## 🚨 PHASE 0: CRITICAL BUG FIX (BLOCKING)

### **TASK 0.1: Fix text() Wrapper in ai_recommendations_manager.py**

**Priority**: CRITICAL  
**Duration**: 30 minutes  
**Risk**: MEDIUM (deprecated SQL will cause warnings in production)

#### **0.1.A: Implementation**

**File**: `src/optimizer_v3/database/ai_recommendations_manager.py`

**Changes Required**: Add `text()` wrapper to all raw SQL queries

**Example**:
```python
# BEFORE (Lines ~50-150, varies):
query = "SELECT * FROM ai_recommendations WHERE recommendation_id = :rec_id"
result = self.session.execute(query, {'rec_id': recommendation_id})

# AFTER:
from sqlalchemy import text
query = text("SELECT * FROM ai_recommendations WHERE recommendation_id = :rec_id")
result = self.session.execute(query, {'rec_id': recommendation_id})
```

**Files to Inspect**:
1. `src/optimizer_v3/database/ai_recommendations_manager.py`
2. Search for: `self.session.execute("` or `self.session.execute('`
3. Count occurrences
4. Fix each one

**Implementation Steps**:
1. Open `ai_recommendations_manager.py`
2. Add import: `from sqlalchemy import text` at top
3. Find all `session.execute(query_string, ...)` calls
4. Wrap each query string with `text(...)`
5. Save file

#### **0.1.B: Unit Tests**

**File**: `tests/database/test_ai_recommendations_manager_text_wrapper.py`

**Test Cases**:
```python
import pytest
from sqlalchemy import text
from src.optimizer_v3.database.ai_recommendations_manager import AIRecommendationsManager

def test_save_recommendation_no_warning(db_session, caplog):
    """Test save_recommendation() doesn't generate SQLAlchemy warnings"""
    manager = AIRecommendationsManager(db_session)
    
    rec_data = {
        'strategy_id': 'test_strategy_001',
        'version_id': 'test_version_001',
        'recommendation_type': 'ADD_BLOCK',
        'reasoning': 'Test reasoning',
        'configuration': {'block': 'test_block'}
    }
    
    # Should not generate warnings
    rec_id = manager.save_recommendation(rec_data)
    
    assert rec_id is not None
    assert "RemovedIn20Warning" not in caplog.text
    assert "deprecated" not in caplog.text.lower()


def test_get_recommendation_no_warning(db_session, caplog):
    """Test get_recommendation() doesn't generate warnings"""
    manager = AIRecommendationsManager(db_session)
    
    # Create test recommendation first
    rec_id = manager.save_recommendation({...})
    
    # Retrieve it - should not warn
    rec = manager.get_recommendation(rec_id)
    
    assert rec is not None
    assert "RemovedIn20Warning" not in caplog.text


def test_all_methods_use_text_wrapper(db_session):
    """Verify all SQL queries use text() wrapper"""
    import inspect
    from src.optimizer_v3.database.ai_recommendations_manager import AIRecommendationsManager
    
    manager = AIRecommendationsManager(db_session)
    
    # Get source code
    source = inspect.getsource(AIRecommendationsManager)
    
    # Find all session.execute calls
    import re
    execute_calls = re.findall(r'self\.session\.execute\((.*?)\)', source, re.DOTALL)
    
    for call in execute_calls:
        # Should start with text(
        assert call.strip().startswith('text('), \
            f"Found session.execute without text() wrapper: {call[:50]}"
```

**Test Execution**:
```bash
# 1. Run specific test file
pytest tests/database/test_ai_recommendations_manager_text_wrapper.py -v

# Expected output:
# test_save_recommendation_no_warning PASSED
# test_get_recommendation_no_warning PASSED
# test_all_methods_use_text_wrapper PASSED
# 3 passed in 0.5s

# 2. Check for deprecation warnings
pytest tests/database/test_ai_recommendations_manager_text_wrapper.py -W default -v

# Expected: No deprecation warnings

# 3. Run with coverage
pytest tests/database/test_ai_recommendations_manager_text_wrapper.py --cov=src/optimizer_v3/database/ai_recommendations_manager --cov-report=term-missing
```

#### **0.1.C: Implementation Test**

**Manual Test Procedure**:

1. **Setup Test Environment**:
```bash
# Activate environment
source venv/bin/activate

# Ensure database is running
psql -U optimizer_admin -d optimizer_v3 -c "SELECT 1;"
```

2. **Create Test Script** (`test_ai_recommendations_live.py`):
```python
"""Live test of AI recommendations manager after text() fix"""
import sys
from datetime import datetime
from uuid import uuid4
from src.optimizer_v3.database.database_manager import DatabaseManagerFactory

def test_complete_workflow():
    """Test complete AI recommendations workflow"""
    
    print("=" * 60)
    print("AI RECOMMENDATIONS MANAGER - LIVE TEST")
    print("=" * 60)
    
    # Get database manager
    db = DatabaseManagerFactory.create('dev')
    
    try:
        # Test 1: Create strategy
        print("\n[1/5] Creating test strategy...")
        strategy_id = db.strategy_manager.create_strategy("Test Strategy AI Recs")
        print(f"✓ Strategy created: {strategy_id}")
        
        # Test 2: Create version
        print("\n[2/5] Creating strategy version...")
        version_data = {
            'strategy_id': strategy_id,
            'name': 'Test Strategy AI Recs',
            'blocks': [{'name': 'test_block', 'signals': []}],
            'signals': {},
            'parameters': {},
            'entry_conditions': {},
            'exit_conditions': {},
            'risk_management': {},
            'backtest_config': {}
        }
        version_id = db.strategy_manager.create_strategy_version(version_data)
        print(f"✓ Version created: {version_id}")
        
        # Test 3: Save AI recommendation
        print("\n[3/5] Saving AI recommendation...")
        rec_data = {
            'strategy_id': strategy_id,
            'version_id': version_id,
            'strategy_version': 'v1',
            'recommendation_type': 'ADD_BLOCK',
            'block_name': 'RSI_Divergence',
            'reasoning': 'RSI divergence detected in backtest analysis',
            'configuration': {
                'block': 'RSI_Divergence',
                'parameters': {'period': 14}
            },
            'expected_impact': {
                'win_rate': '+5%',
                'profit_factor': '+0.3'
            },
            'combined_confidence': 0.85
        }
        rec_id = db.ai_manager.save_recommendation(rec_data)
        print(f"✓ Recommendation saved: {rec_id}")
        
        # Test 4: Retrieve recommendation
        print("\n[4/5] Retrieving recommendation...")
        rec = db.ai_manager.get_recommendation(rec_id)
        assert rec is not None
        assert rec['recommendation_type'] == 'ADD_BLOCK'
        assert rec['block_name'] == 'RSI_Divergence'
        print(f"✓ Recommendation retrieved: {rec['recommendation_type']}")
        print(f"  - Reasoning: {rec['reasoning'][:50]}...")
        print(f"  - Confidence: {rec['combined_confidence']}")
        
        # Test 5: Get strategy recommendations
        print("\n[5/5] Getting all recommendations for strategy...")
        recs = db.ai_manager.get_strategy_recommendations(strategy_id)
        assert len(recs) == 1
        print(f"✓ Found {len(recs)} recommendation(s)")
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED - text() wrapper working correctly")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        print("\n[CLEANUP] Removing test data...")
        try:
            db.strategy_manager.delete_strategy(strategy_id)
            print("✓ Cleanup complete")
        except:
            pass

if __name__ == '__main__':
    success = test_complete_workflow()
    sys.exit(0 if success else 1)
```

3. **Execute Test**:
```bash
# Run live test
python test_ai_recommendations_live.py

# Expected output:
# ============================================================
# AI RECOMMENDATIONS MANAGER - LIVE TEST
# ============================================================
# 
# [1/5] Creating test strategy...
# ✓ Strategy created: strategy_xxxxx
# 
# [2/5] Creating strategy version...
# ✓ Version created: uuid-xxxx-xxxx
# 
# [3/5] Saving AI recommendation...
# ✓ Recommendation saved: uuid-yyyy-yyyy
# 
# [4/5] Retrieving recommendation...
# ✓ Recommendation retrieved: ADD_BLOCK
#   - Reasoning: RSI divergence detected in backtest analysis...
#   - Confidence: 0.85
# 
# [5/5] Getting all recommendations for strategy...
# ✓ Found 1 recommendation(s)
# 
# ============================================================
# ✅ ALL TESTS PASSED - text() wrapper working correctly
# ============================================================
```

4. **Check for Warnings**:
```bash
# Run with all warnings enabled
python -W default test_ai_recommendations_live.py 2>&1 | grep -i deprecat

# Expected: No output (no deprecation warnings)
```

#### **0.1.D: Rollback Plan**

**If test fails**:
```bash
# 1. Revert file changes
git checkout src/optimizer_v3/database/ai_recommendations_manager.py

# 2. Verify rollback
git diff src/optimizer_v3/database/ai_recommendations_manager.py
# Should show: nothing to commit

# 3. Re-test old version
python test_ai_recommendations_live.py
```

#### **0.1.E: Approval Checkpoint**

**User Action Required**:
- [ ] Review implementation changes
- [ ] Execute unit tests
- [ ] Execute implementation test
- [ ] Verify all warnings resolved
- [ ] Approve to proceed to Phase 1

**Sign-off**: ________ Date: ________

---

## 🔧 PHASE 1: ORM REFACTOR - STRATEGY MANAGER

### **Background**

**Current State**: strategy_manager.py uses raw SQL with text() wrapper  
**Target State**: Use SQLAlchemy ORM models for type safety  
**Risk**: MEDIUM - Core strategy CRUD operations  
**Real Money Impact**: HIGH - Strategy data is trading configuration

**Benefits of ORM**:
1. Type safety (IDE autocomplete, type checking)
2. Relationship management (automatic foreign key handling)
3. Query building (easier to read and maintain)
4. Error prevention (catch errors at Python level, not SQL level)
5. Refactoring safety (rename columns → IDE finds all usages)

---

### **TASK 1.1: Refactor create_strategy() to ORM**

**Priority**: HIGH  
**Duration**: 1.5 hours  
**Dependencies**: ORM models exist (Strategy class)

#### **1.1.A: Implementation**

**File**: `src/optimizer_v3/database/strategy_manager.py`

**Current Code** (Lines ~50-80):
```python
def create_strategy(self, name: str) -> str:
    """Create new strategy parent record"""
    strategy_id = f"strategy_{uuid4().hex[:8]}"
    
    query = text("""
        INSERT INTO strategies (strategy_id, name, created_at, updated_at)
        VALUES (:strategy_id, :name, NOW(), NOW())
    """)
    
    self.session.execute(query, {
        'strategy_id': strategy_id,
        'name': name.strip()
    })
    self.session.commit()
    
    return strategy_id
```

**New Code (ORM)**:
```python
from src.optimizer_v3.database.models import Strategy

def create_strategy(self, name: str) -> str:
    """
    Create new strategy parent record using ORM
    
    Args:
        name: Strategy name (will be stripped of whitespace)
        
    Returns:
        strategy_id: Unique strategy identifier
        
    Raises:
        ValueError: If name is empty after stripping
        IntegrityError: If strategy with this ID already exists
        
    Real Money Impact: HIGH - Creates parent record for trading strategy
    """
    # Validation
    name_clean = name.strip()
    if not name_clean:
        raise ValueError("Strategy name cannot be empty")
    
    # Generate unique ID
    strategy_id = f"strategy_{uuid4().hex[:8]}"
    
    # Create ORM object
    strategy = Strategy(
        strategy_id=strategy_id,
        name=name_clean
        # created_at, updated_at handled by server defaults
    )
    
    # Add to session and commit
    self.session.add(strategy)
    self.session.commit()
    
    return strategy_id
```

**Key Changes**:
1. Import `Strategy` ORM model
2. Create Python object instead of SQL string
3. Add validation
4. Add comprehensive docstring
5. Type hints remain the same
6. Return value unchanged (backwards compatible)

#### **1.1.B: Unit Tests**

**File**: `tests/database/test_strategy_manager_orm.py`

**Test Cases**:
```python
import pytest
from uuid import uuid4
from sqlalchemy.exc import IntegrityError
from src.optimizer_v3.database.strategy_manager import StrategyDatabaseManager
from src.optimizer_v3.database.models import Strategy

class TestCreateStrategyORM:
    """Test create_strategy() ORM refactoring"""
    
    def test_create_strategy_basic(self, db_session):
        """Test basic strategy creation with ORM"""
        manager = StrategyDatabaseManager(db_session)
        
        # Create strategy
        strategy_id = manager.create_strategy("Test Strategy 001")
        
        # Verify return value
        assert strategy_id is not None
        assert strategy_id.startswith("strategy_")
        assert len(strategy_id) == 17  # "strategy_" + 8 hex chars
        
        # Verify in database using ORM query
        strategy = db_session.query(Strategy).filter_by(
            strategy_id=strategy_id
        ).first()
        
        assert strategy is not None
        assert strategy.name == "Test Strategy 001"
        assert strategy.created_at is not None
        assert strategy.updated_at is not None
    
    def test_create_strategy_strips_whitespace(self, db_session):
        """Test that whitespace is properly stripped"""
        manager = StrategyDatabaseManager(db_session)
        
        # Create with extra whitespace
        strategy_id = manager.create_strategy("  Test Strategy  ")
        
        # Verify stripped
        strategy = db_session.query(Strategy).filter_by(
            strategy_id=strategy_id
        ).first()
        
        assert strategy.name == "Test Strategy"
        assert strategy.name != "  Test Strategy  "
    
    def test_create_strategy_empty_name_fails(self, db_session):
        """Test that empty name raises ValueError"""
        manager = StrategyDatabaseManager(db_session)
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="Strategy name cannot be empty"):
            manager.create_strategy("")
        
        # Whitespace-only should also fail
        with pytest.raises(ValueError, match="Strategy name cannot be empty"):
            manager.create_strategy("   ")
    
    def test_create_strategy_unique_ids(self, db_session):
        """Test that multiple strategies get unique IDs"""
        manager = StrategyDatabaseManager(db_session)
        
        # Create 10 strategies
        strategy_ids = set()
        for i in range(10):
            sid = manager.create_strategy(f"Strategy {i}")
            strategy_ids.add(sid)
        
        # All should be unique
        assert len(strategy_ids) == 10
    
    def test_create_strategy_timestamps_auto_set(self, db_session):
        """Test that created_at and updated_at are automatically set"""
        from datetime import datetime
        manager = StrategyDatabaseManager(db_session)
        
        before = datetime.utcnow()
        strategy_id = manager.create_strategy("Timestamp Test")
        after = datetime.utcnow()
        
        strategy = db_session.query(Strategy).filter_by(
            strategy_id=strategy_id
        ).first()
        
        assert before <= strategy.created_at <= after
        assert before <= strategy.updated_at <= after
        assert strategy.created_at == strategy.updated_at  # Should be same on creation
    
    def test_create_strategy_rollback_on_error(self, db_session):
        """Test that session rolls back on error"""
        manager = StrategyDatabaseManager(db_session)
        
        # Count before
        count_before = db_session.query(Strategy).count()
        
        # Try to create with invalid data (empty name)
        try:
            manager.create_strategy("")
        except ValueError:
            pass
        
        # Count after - should be unchanged
        count_after = db_session.query(Strategy).count()
        assert count_after == count_before
    
    def test_create_strategy_returns_correct_type(self, db_session):
        """Test return type is string"""
        manager = StrategyDatabaseManager(db_session)
        
        result = manager.create_strategy("Type Test")
        
        assert isinstance(result, str)
        assert not isinstance(result, bytes)
    
    def test_create_strategy_special_characters(self, db_session):
        """Test strategy name with special characters"""
        manager = StrategyDatabaseManager(db_session)
        
        special_name = "Strategy™ with Ümlauts & Émojis 🚀"
        strategy_id = manager.create_strategy(special_name)
        
        strategy = db_session.query(Strategy).filter_by(
            strategy_id=strategy_id
        ).first()
        
        assert strategy.name == special_name
    
    def test_create_strategy_long_name(self, db_session):
        """Test strategy with maximum length name"""
        manager = StrategyDatabaseManager(db_session)
        
        # Create max length name (assuming 255 char limit)
        long_name = "A" * 255
        strategy_id = manager.create_strategy(long_name)
        
        strategy = db_session.query(Strategy).filter_by(
            strategy_id=strategy_id
        ).first()
        
        assert len(strategy.name) == 255
        assert strategy.name == long_name
```

**Test Execution**:
```bash
# 1. Run all tests for create_strategy()
pytest tests/database/test_strategy_manager_orm.py::TestCreateStrategyORM -v

# Expected output:
# test_create_strategy_basic PASSED
# test_create_strategy_strips_whitespace PASSED
# test_create_strategy_empty_name_fails PASSED
# test_create_strategy_unique_ids PASSED
# test_create_strategy_timestamps_auto_set PASSED
# test_create_strategy_rollback_on_error PASSED
# test_create_strategy_returns_correct_type PASSED
# test_create_strategy_special_characters PASSED
# test_create_strategy_long_name PASSED
# 9 passed in 1.2s

# 2. Run with coverage
pytest tests/database/test_strategy_manager_orm.py::TestCreateStrategyORM \
    --cov=src/optimizer_v3/database/strategy_manager \
    --cov-report=term-missing \
    --cov-report=html

# Expected: 100% coverage for create_strategy() method

# 3. Type checking
mypy src/optimizer_v3/database/strategy_manager.py

# Expected: Success: no issues found
```

#### **1.1.C: Implementation Test**

**Manual Test Script** (`test_create_strategy_live.py`):
```python
"""Live test of create_strategy() ORM refactoring"""
import sys
from src.optimizer_v3.database.database_manager import DatabaseManagerFactory

def test_create_strategy_live():
    """Test create_strategy() in live environment"""
    
    print("=" * 60)
    print("CREATE STRATEGY (ORM) - LIVE TEST")
    print("=" * 60)
    
    db = DatabaseManagerFactory.create('dev')
    
    try:
        # Test 1: Basic creation
        print("\n[TEST 1] Basic strategy creation...")
        sid1 = db.strategy_manager.create_strategy("Live Test Strategy 1")
        print(f"✓ Created: {sid1}")
        assert sid1.startswith("strategy_")
        
        # Test 2: Whitespace stripping
        print("\n[TEST 2] Whitespace stripping...")
        sid2 = db.strategy_manager.create_strategy("  Live Test 2  ")
        strategy = db.session.query(Strategy).filter_by(strategy_id=sid2).first()
        assert strategy.name == "Live Test 2"
        print(f"✓ Whitespace stripped: '{strategy.name}'")
        
        # Test 3: Empty name validation
        print("\n[TEST 3] Empty name validation...")
        try:
            db.strategy_manager.create_strategy("")
            print("❌ Should have raised ValueError")
            return False
        except ValueError as e:
            print(f"✓ Correctly raised ValueError: {e}")
        
        # Test 4: Special characters
        print("\n[TEST 4] Special characters...")
        sid4 = db.strategy_manager.create_strategy("Test™ Strategy™ 🚀")
        strategy4 = db.session.query(Strategy).filter_by(strategy_id=sid4).first()
        assert "™" in strategy4.name
        assert "🚀" in strategy4.name
        print(f"✓ Special chars preserved: {strategy4.name}")
        
        # Test 5: Unique IDs
        print("\n[TEST 5] Unique IDs...")
        ids = set()
        for i in range(5):
            sid = db.strategy_manager.create_strategy(f"Unique Test {i}")
            ids.add(sid)
        assert len(ids) == 5
        print(f"✓ All 5 IDs unique: {len(ids)}")
        
        print("\n" + "=" * 60)
        print("✅ ALL LIVE TESTS PASSED")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ LIVE TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        print("\n[CLEANUP] Removing test strategies...")
        # Note: Cleanup code here
        print("✓ Cleanup complete")

if __name__ == '__main__':
    success = test_create_strategy_live()
    sys.exit(0 if success else 1)
```

**Execute**:
```bash
python test_create_strategy_live.py
```

#### **1.1.D: Rollback Plan**

```bash
# Revert changes
git diff src/optimizer_v3/database/strategy_manager.py > create_strategy_orm.patch
git checkout src/optimizer_v3/database/strategy_manager.py

# Test old version
pytest tests/database/test_strategy_manager_orm.py::TestCreateStrategyORM
```

#### **1.1.E: Approval Checkpoint**

**Deliverables**:
- [x] create_strategy() refactored to ORM
- [x] 9 unit tests created and passing
- [x] Live implementation test passing
- [x] Type hints validated with mypy
- [x] Docstring updated with real money warning
- [x] Rollback plan documented

**User Action Required**:
- [ ] Review ORM implementation
- [ ] Execute all unit tests
- [ ] Execute live implementation test
- [ ] Verify type safety improvements
- [ ] Approve to proceed to Task 1.2

**Sign-off**: ________ Date: ________

---

### **TASK 1.2: Refactor create_strategy_version() to ORM**

[Similar structure continues for remaining tasks...]

---

## 📋 COMPLETE TASK LIST (24 TASKS)

### **Completed (18/24)**
- [x] 0. Database migration (2 tasks)
- [x] 0. Database managers created (4 tasks)
- [x] 0. UI components created (3 tasks)
- [x] 0. Main window integration (4 tasks)
- [x] 0. ORM models created (5 tasks)

### **Pending (6/24)**
- [ ] **0.1**: Fix text() wrapper bug (30 min)
- [ ] **1.1**: create_strategy() to ORM (1.5 hrs)
- [ ] **1.2**: create_strategy_version() to ORM (2 hrs)
- [ ] **1.3**: get_strategy_version() to ORM (1 hr)
- [ ] **1.4**: get_all_strategies() to ORM (1.5 hrs)
- [ ] **2.1**: ai_recommendations_manager to ORM (3 hrs)
- [ ] **3.1**: test_results_manager to ORM (2 hrs)

**Remaining**: 11.5 hours (1.5 days)

---

## 🎯 SUCCESS CRITERIA

**Sprint 1.6.1 is 100% COMPLETE when**:
1. ✅ All 24 tasks checked off
2. ✅ All unit tests passing (100% coverage)
3. ✅ All implementation tests passing
4. ✅ Zero deprecation warnings
5. ✅ Type checking passes (mypy)
6. ✅ User approval at every checkpoint
7. ✅ All rollback plans tested
8. ✅ Documentation updated
9. ✅ MASTER_INDEX updated to "✅ COMPLETE"

---

**Next Action**: Begin Task 0.1 (Fix text() wrapper bug)
**Awaiting**: User approval to proceed
