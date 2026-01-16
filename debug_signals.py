#!/usr/bin/env python
"""Debug script to check signal ui_visible attributes"""

from src.strategy_builder.core.block_registry_adapter import BlockRegistryAdapter

# Initialize adapter
adapter = BlockRegistryAdapter()

# Get cup_and_handle block
block = adapter.get_block("cup_and_handle")

print(f"Block type: {type(block)}")
print(f"Block: {block['name'] if isinstance(block, dict) else block.name}")

# Check if signals are dicts or objects
signals = block['signals'] if isinstance(block, dict) else block.signals
print(f"Total signals: {len(signals)}")
print(f"Signal type: {type(signals[0])}")

print("\nSignal Details:")
print("-" * 80)

for signal in signals:
    if isinstance(signal, dict):
        # It's a dict - use key access
        name = signal.get('name', 'UNKNOWN')
        ui_visible = signal.get('ui_visible', 'KEY_MISSING')
        print(f"{name:30} | ui_visible: {ui_visible}")
    else:
        # It's an object - use attribute access
        has_attr = hasattr(signal, 'ui_visible')
        if has_attr:
            value = signal.ui_visible
        else:
            value = "ATTRIBUTE MISSING"
        print(f"{signal.name:30} | ui_visible: {value:15} | hasattr: {has_attr}")

print("-" * 80)

# Test filtering if they're dicts
if isinstance(signals[0], dict):
    visible_signals = [s for s in signals if s.get('ui_visible', True) != False]
    print(f"\nVisible signals (dict filtering): {len(visible_signals)}")
    print("Hidden signals:")
    for s in signals:
        if s.get('ui_visible', True) == False:
            print(f"  - {s.get('name')}")
