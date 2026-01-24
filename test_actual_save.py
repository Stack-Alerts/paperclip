#!/usr/bin/env python3
"""Test actual save operation to see real error"""
import os
import sys

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment
from dotenv import load_dotenv
load_dotenv()

from src.optimizer_v3.database import get_database_manager

# Clean database first
db = get_database_manager()
from sqlalchemy import text
db.strategy.session.execute(text("DELETE FROM strategy_versions"))
db.strategy.session.execute(text("DELETE FROM strategies"))
db.strategy.session.commit()

print("Database cleaned")

# Now test save
try:
    strategy_id = db.strategy.create_strategy("Test Strategy")
    print(f"Created strategy: {strategy_id}")
    
    version_data = {
        'strategy_id': strategy_id,
        'name': 'Test Strategy',
        'description': 'Test description',
        'blocks': [],  # Empty blocks
        'signals': {},
        'parameters': {},
        'entry_conditions': {},
        'exit_conditions': {},
        'risk_management': {},
        'backtest_config': {},
        'tags': []
    }
    
    print("Creating version...")
    version_id = db.strategy.create_strategy_version(version_data)
    print(f"SUCCESS! Version created: {version_id}")
    
except Exception as e:
    print(f"\n❌ ACTUAL ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
