"""
Migrate existing strategies to include strategy_type field.

This script updates all existing strategy versions in the database
to include the strategy_type field by analyzing their signals.
"""

import os
import sys
import json

# Set up Python path to import from src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from src.optimizer_v3.database import get_database_manager
from sqlalchemy import text


def infer_strategy_type_from_signals(blocks):
    """
    Infer strategy type from signal names (Bullish vs Bearish).
    
    Args:
        blocks: List of block configurations
        
    Returns:
        'Bullish' or 'Bearish'
    """
    bullish_keywords = [
        'BULLISH', 'LONG', 'BUY', 'ABOVE', 'OVER', 'UP', 'HIGHER',
        'BREAKOUT', 'SUPPORT', 'BOUNCE', 'REVERSAL_UP', 'UPTREND',
        'ACCUMULATION', 'REACCUMULATION', 'SPRING', 'SOS', 'LPS'
    ]
    
    bearish_keywords = [
        'BEARISH', 'SHORT', 'SELL', 'BELOW', 'UNDER', 'DOWN', 'LOWER',
        'BREAKDOWN', 'RESISTANCE', 'REJECTION', 'REVERSAL_DOWN', 'DOWNTREND',
        'DISTRIBUTION', 'REDISTRIBUTION', 'UPTHRUST', 'SOW', 'LPSY'
    ]
    
    bullish_count = 0
    bearish_count = 0
    
    for block in blocks:
        for signal in block.get('signals', []):
            signal_name_upper = signal.get('name', '').upper()
            
            # Check for bullish keywords
            is_bullish = any(keyword in signal_name_upper for keyword in bullish_keywords)
            # Check for bearish keywords
            is_bearish = any(keyword in signal_name_upper for keyword in bearish_keywords)
            
            if is_bullish:
                bullish_count += 1
            if is_bearish:
                bearish_count += 1
    
    # Return type based on majority
    if bearish_count > bullish_count:
        return 'Bearish'
    else:
        return 'Bullish'  # Default to Bullish if tied or no signals


def migrate_strategy_types():
    """Update all existing strategy versions with strategy_type field."""
    db = get_database_manager()
    
    try:
        # Get all strategy versions
        result = db.strategy.session.execute(
            text("SELECT version_id, blocks FROM strategy_versions")
        )
        versions = result.fetchall()
        
        updated_count = 0
        
        for version_id, blocks_json in versions:
            # PostgreSQL returns JSONB as Python object already (list/dict)
            blocks = blocks_json if blocks_json else []
            
            # Infer strategy type
            strategy_type = infer_strategy_type_from_signals(blocks)
            
            # Update the record
            db.strategy.session.execute(
                text("UPDATE strategy_versions SET strategy_type = :stype WHERE version_id = :vid"),
                {'stype': strategy_type, 'vid': version_id}
            )
            
            updated_count += 1
            print(f"✅ Updated version {version_id}: {strategy_type}")
        
        # Commit all changes
        db.strategy.session.commit()
        
        print(f"\n{'='*80}")
        print(f"Migration Complete!")
        print(f"Updated {updated_count} strategy versions with strategy_type")
        print(f"{'='*80}")
        
    except Exception as e:
        db.strategy.session.rollback()
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    print("Starting strategy_type migration...")
    print(f"{'='*80}\n")
    migrate_strategy_types()
