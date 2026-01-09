#!/usr/bin/env python3
"""
Strategy Builder CLI - Command Line Interface

Simple CLI for creating, validating, and generating strategies
without writing Python code.

Usage:
    python scripts/strategy_builder_cli.py create
    python scripts/strategy_builder_cli.py list
    python scripts/strategy_builder_cli.py generate 1
    python scripts/strategy_builder_cli.py validate 1

Author: Strategy Builder v2.0
Date: 2026-01-09
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.Strategy_Builder import (
    StrategyRegistry,
    StrategyValidator,
    StrategyGenerator,
    StrategyConfiguration,
    BlockSelection,
    SignalConfiguration,
    StrategyCategory,
    SignalRole,
    BlockType
)


def cmd_create(args):
    """Create a new strategy interactively"""
    print("\n🎯 Strategy Builder - Create New Strategy\n")
    
    registry = StrategyRegistry()
    
    # Get next strategy number
    try:
        strategy_number = registry.get_next_strategy_number()
    except ValueError:
        print("❌ All 150 strategy slots are filled!")
        return 1
    
    print(f"Strategy Number: {strategy_number}")
    
    # Get basic info
    name = input("Strategy Name (e.g., 'reversal_m_pattern'): ").strip()
    if not name:
        print("❌ Strategy name is required")
        return 1
    
    # TODO: Add interactive block selection
    # For now, just show how to create programmatically
    print("\n📝 To create a complete strategy, use the programmatic API:")
    print(f"""
from src.utils.Strategy_Builder import *

config = StrategyConfiguration(
    strategy_name="{name}",
    strategy_number={strategy_number},
    strategy_category=StrategyCategory.REVERSAL,
    blocks=[
        BlockSelection(
            block_name="double_top",
            block_display_name="Double Top",
            block_category="PATTERNS",
            block_type=BlockType.EVENT,
            weight=30,
            weight_range=(20, 40),
            is_main_signal=True,
            signals=[SignalConfiguration(signal_name="BEARISH_BREAKDOWN", role=SignalRole.SIGNAL)]
        )
    ]
)

registry = StrategyRegistry()
registry.save_strategy(config)
""")
    
    return 0


def cmd_list(args):
    """List all strategies"""
    print("\n📋 Strategy Builder - List All Strategies\n")
    
    registry = StrategyRegistry()
    strategies = registry.list_strategies()
    
    if not strategies:
        print("No strategies found.")
        return 0
    
    # Group by category
    by_category = {}
    for s in strategies:
        cat = s.category
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(s)
    
    # Display
    total = 0
    for category in sorted(by_category.keys()):
        strats = by_category[category]
        print(f"\n{category}:")
        for s in sorted(strats, key=lambda x: x.number):
            print(f"  {s.number:03d}. {s.name}")
            total += 1
    
    print(f"\n📊 Total: {total} strategies")
    print(f"📊 Available slots: {150 - total}")
    
    return 0


def cmd_validate(args):
    """Validate a strategy"""
    print(f"\n✅ Strategy Builder - Validate Strategy #{args.number}\n")
    
    registry = StrategyRegistry()
    config = registry.load_strategy(args.number)
    
    if not config:
        print(f"❌ Strategy {args.number} not found")
        return 1
    
    # Validate
    validator = StrategyValidator()
    result = validator.validate(config)
    
    # Display results
    print(f"Strategy: {config.strategy_name}")
    print(f"Category: {config.strategy_category}")
    print(f"Blocks: {len(config.blocks)}")
    print("")
    
    if result.is_valid:
        print("✅ Strategy is VALID")
    else:
        print("❌ Strategy is INVALID")
    
    if result.errors:
        print("\n🔴 Errors:")
        for error in result.errors:
            print(f"  - {error}")
    
    if result.warnings:
        print("\n🟡 Warnings:")
        for warning in result.warnings:
            print(f"  - {warning}")
    
    if result.suggestions:
        print("\n💡 Suggestions:")
        for suggestion in result.suggestions:
            print(f"  - {suggestion}")
    
    return 0 if result.is_valid else 1


def cmd_generate(args):
    """Generate strategy files"""
    print(f"\n🔧 Strategy Builder - Generate Strategy #{args.number}\n")
    
    registry = StrategyRegistry()
    
    # Generate files
    try:
        files = registry.generate_strategy_files(args.number)
        
        if not files:
            print(f"❌ Strategy {args.number} not found")
            return 1
        
        print("✅ Generated successfully!")
        print(f"\nStrategy: {files['strategy']}")
        print(f"Test:     {files['test']}")
        print(f"Config:   {files['optimizer']}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Generation failed: {e}")
        return 1


def cmd_info(args):
    """Show strategy info"""
    print(f"\n📖 Strategy Builder - Strategy #{args.number} Info\n")
    
    registry = StrategyRegistry()
    config = registry.load_strategy(args.number)
    
    if not config:
        print(f"❌ Strategy {args.number} not found")
        return 1
    
    # Display info
    print(f"Name:         {config.strategy_name}")
    print(f"Number:       {config.strategy_number}")
    print(f"Category:     {config.strategy_category}")
    print(f"Description:  {config.description or 'N/A'}")
    print(f"Min Confluence: {config.min_confluence}")
    print(f"Risk:Reward:  {config.risk_reward_ratio}")
    print(f"\nBuilding Blocks ({len(config.blocks)}):")
    
    for block in config.blocks:
        main = " ⭐" if block.is_main_signal else ""
        enabled = "✓" if block.enabled else "✗"
        print(f"  [{enabled}] {block.block_display_name} (weight: {block.weight}){main}")
        for signal in block.signals:
            print(f"      - {signal.signal_display_name} ({signal.role})")
    
    return 0


def cmd_stats(args):
    """Show statistics"""
    print("\n📊 Strategy Builder - Statistics\n")
    
    registry = StrategyRegistry()
    
    total = registry.get_strategy_count()
    by_category = registry.get_category_counts()
    
    print(f"Total Strategies: {total}/150")
    print(f"Available Slots:  {150 - total}")
    print(f"\nBy Category:")
    
    for category, count in sorted(by_category.items()):
        pct = (count / total * 100) if total > 0 else 0
        bar = "█" * int(pct / 5)
        print(f"  {category:20s} {count:3d} {bar} {pct:.1f}%")
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Strategy Builder CLI - Create and manage trading strategies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/strategy_builder_cli.py list
  python scripts/strategy_builder_cli.py validate 1
  python scripts/strategy_builder_cli.py generate 1
  python scripts/strategy_builder_cli.py info 1
  python scripts/strategy_builder_cli.py stats
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create command
    parser_create = subparsers.add_parser('create', help='Create new strategy (interactive)')
    parser_create.set_defaults(func=cmd_create)
    
    # List command
    parser_list = subparsers.add_parser('list', help='List all strategies')
    parser_list.set_defaults(func=cmd_list)
    
    # Validate command
    parser_validate = subparsers.add_parser('validate', help='Validate a strategy')
    parser_validate.add_argument('number', type=int, help='Strategy number')
    parser_validate.set_defaults(func=cmd_validate)
    
    # Generate command
    parser_generate = subparsers.add_parser('generate', help='Generate strategy files')
    parser_generate.add_argument('number', type=int, help='Strategy number')
    parser_generate.set_defaults(func=cmd_generate)
    
    # Info command
    parser_info = subparsers.add_parser('info', help='Show strategy info')
    parser_info.add_argument('number', type=int, help='Strategy number')
    parser_info.set_defaults(func=cmd_info)
    
    # Stats command
    parser_stats = subparsers.add_parser('stats', help='Show statistics')
    parser_stats.set_defaults(func=cmd_stats)
    
    # Parse args
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute command
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())