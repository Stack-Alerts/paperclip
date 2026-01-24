#!/usr/bin/env python3
"""Delete orphaned strategy 967a7319"""
import os
import sys

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv()

from src.optimizer_v3.database import get_database_manager
from sqlalchemy import text

db = get_database_manager()

# Delete the orphan
db.strategy.session.execute(
    text("DELETE FROM strategies WHERE strategy_id = 'strategy_967a7319'")
)
db.strategy.session.commit()

print("✅ Deleted orphaned strategy_967a7319")

# Show remaining
result = db.strategy.session.execute(
    text("SELECT strategy_id, name FROM strategies ORDER BY updated_at DESC")
)
rows = result.fetchall()

print(f"\nRemaining strategies: {len(rows)}")
for row in rows:
    print(f"  - {row[0]}: {row[1]}")

db.close()
