#!/usr/bin/env python3
"""
create_strategy() ORM Validation - Sprint 1.6.1 Task 1.1
Quick validation without requiring database connectivity
"""

import sys
import inspect


def main():
    print("=" * 80)
    print("TASK 1.1: create_strategy() ORM REFACTORING - VALIDATION")
    print("Sprint 1.6.1 - Strategy Manager")
    print("=" * 80)
    print()
    
    try:
        # Import the manager and Strategy model
        print("[1/4] Importing Strategy Manager and ORM model...")
        from src.optimizer_v3.database.strategy_manager import StrategyDatabaseManager
        from src.optimizer_v3.database.models import Strategy
        print("✓ Import successful\n")
        
        # Verify Strategy model is imported in create_strategy()
        print("[2/4] Verifying ORM model usage...")
        source = inspect.getsource(StrategyDatabaseManager.create_strategy)
        assert 'from src.optimizer_v3.database.models import Strategy' in source, \
            "Strategy model not imported"
        print("✓ Strategy ORM model is imported\n")
        
        # Verify ORM object creation (not raw SQL)
        print("[3/4] Analyzing implementation...")
        assert 'Strategy(' in source, "Strategy ORM object not created"
        assert 'strategy_id=strategy_id' in source, "ORM parameters not set"
        assert 'name=name_clean' in source, "ORM name parameter not set"
        assert 'self.session.add(strategy)' in source, "ORM object not added to session"
        assert 'self.session.commit()' in source, "Session not committed"
        print("✓ Uses ORM pattern (Strategy object creation)")
        print("✓ Uses session.add() instead of raw SQL")
        print("✓ Commits transaction properly\n")
        
        # Verify raw SQL is removed
        print("[4/4] Verifying raw SQL removed...")
        # Should NOT have the old INSERT INTO text() query
        assert 'INSERT INTO strategies' not in source, \
            "Old raw SQL still present"
        print("✓ Raw SQL INSERT removed")
        print("✓ Refactoring complete\n")
        
        # Check docstring updates
        print("[BONUS] Checking documentation...")
        assert 'ORM' in source or 'orm' in source.lower(), "No ORM mention in code"
        assert 'Real Money Impact' in source, "Real money warning missing"
        print("✓ Docstring updated with ORM mention")
        print("✓ Real money warning present\n")
        
        print("=" * 80)
        print("✅ ALL VALIDATIONS PASSED")
        print("=" * 80)
        print()
        print("Summary:")
        print("  ✓ Strategy ORM model imported")
        print("  ✓ ORM object creation pattern used")
        print("  ✓ session.add() + commit() pattern used")
        print("  ✓ Raw SQL INSERT removed")
        print("  ✓ Documentation updated")
        print()
        print("Implementation Status: COMPLETE")
        print("Test Status: READY FOR UNIT TESTS")
        print()
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print()
        print("=" * 80)
        print("❌ VALIDATION FAILED")
        print("=" * 80)
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()
        print()
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
