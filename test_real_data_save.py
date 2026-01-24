#!/usr/bin/env python3
"""Test save with REAL strategy data from JSON file"""
import os
import sys
import json

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment
from dotenv import load_dotenv
load_dotenv()

from pathlib import Path
from src.optimizer_v3.database import get_database_manager
from src.strategy_builder.persistence.strategy_persistence import StrategyPersistence

# Clean database first
db = get_database_manager()
from sqlalchemy import text
db.strategy.session.execute(text("DELETE FROM strategy_versions"))
db.strategy.session.execute(text("DELETE FROM strategies"))
db.strategy.session.commit()

print("Database cleaned\n")

# Load real strategy from JSON
persistence = StrategyPersistence()
json_file = Path("user_strategies/hod_rejection.json")

print(f"Loading strategy from {json_file}...")
result = persistence.load(json_file)

if not result.success:
    print(f"❌ Failed to load: {result.errors}")
    sys.exit(1)

print(f"✅ Loaded strategy: {result.config.name}")
print(f"   Blocks: {len(result.config.blocks)}")

# Convert to dict (SAME AS UI DOES)
config_dict = persistence._config_to_dict(result.config)

print(f"\n📦 Blocks data structure:")
print(f"   Type: {type(config_dict['blocks'])}")
print(f"   Length: {len(config_dict['blocks'])}")

# Try to JSON serialize the blocks (this is what database does)
try:
    blocks_json = json.dumps(config_dict['blocks'])
    print(f"   JSON serialization: ✅ SUCCESS ({len(blocks_json)} chars)")
except Exception as e:
    print(f"   JSON serialization: ❌ FAILED - {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Now test actual save
print(f"\nTesting database save...")
try:
    strategy_id = db.strategy.create_strategy(result.config.name)
    print(f"✅ Created strategy: {strategy_id}")
    
    version_data = {
        'strategy_id': strategy_id,
        'name': result.config.name,
        'description': result.config.description,
        'blocks': config_dict['blocks'],  # Pass as list (same as UI)
        'signals': {},
        'parameters': {},
        'entry_conditions': {},
        'exit_conditions': {},
        'risk_management': {},
        'backtest_config': {},
        'tags': []
    }
    
    version_id = db.strategy.create_strategy_version(version_data)
    print(f"✅ Version created: {version_id}")
    print(f"\n🎉 COMPLETE SUCCESS - Save works with real data!")
    
except Exception as e:
    print(f"\n❌ SAVE FAILED: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
