#!/usr/bin/env python3
"""
Strategy Generator CLI — Entry point for the Strategy Factory.

Usage:
    python scripts/generate_strategy.py --config strategy_definitions/my_strategy.json
    python scripts/generate_strategy.py --config-dir strategy_definitions/ --start 1 --end 10
    python scripts/generate_strategy.py --list-blocks
"""

import argparse
import sys
import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

from src.strategy_builder.core.strategy_factory import (
    StrategyFactory,
    BLOCK_REGISTRY_MAP,
)


def setup_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Strategy Factory — Generate production NautilusTrader strategies from config",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--config", "-c", type=str, help="Path to a single JSON strategy definition file")
    group.add_argument("--config-dir", "-d", type=str, help="Directory containing JSON strategy definition files for batch generation")
    group.add_argument("--list-blocks", "-l", action="store_true", help="List all available building blocks in the registry")
    parser.add_argument("--start", type=int, default=0, help="Starting index for batch generation (inclusive)")
    parser.add_argument("--end", type=int, default=None, help="Ending index for batch generation (exclusive)")
    parser.add_argument("--output-dir", "-o", type=str, default=None, help="Output directory for generated strategy files (default: src/strategies/)")
    return parser


def list_blocks() -> None:
    categories: dict = {}
    for name, meta in BLOCK_REGISTRY_MAP.items():
        imp = meta["import_path"]
        parts = imp.split(".")
        cat = (parts[5].upper()) if len(parts) >= 6 else "UNKNOWN"
        categories.setdefault(cat, []).append((name, meta))

    print("=" * 72)
    print("  AVAILABLE BUILDING BLOCKS (Strategy Factory Registry)")
    print("=" * 72)
    for cat in sorted(categories):
        print(f"\n  [{cat}]")
        for name, _ in sorted(categories[cat]):
            print(f"    - {name}")
    print(f"\n  Total: {len(BLOCK_REGISTRY_MAP)} blocks")


def main() -> int:
    parser = setup_parser()
    args = parser.parse_args()

    if args.list_blocks:
        list_blocks()
        return 0

    factory = StrategyFactory()

    if args.config:
        if not os.path.exists(args.config):
            print(f"ERROR: Config file not found: {args.config}", file=sys.stderr)
            return 1
        print(f"Loading config: {args.config}")
        definition = factory.load_definition(args.config)
        output_path, validation = factory.generate_and_write(definition, args.output_dir)
        if not validation.valid:
            print("VALIDATION FAILED:", file=sys.stderr)
            for err in validation.errors:
                print(f"  - {err}", file=sys.stderr)
            return 1
        if validation.warnings:
            print("Warnings:")
            for w in validation.warnings:
                print(f"  - {w}")
        print(f"SUCCESS: {output_path}")
        return 0

    if args.config_dir:
        if not os.path.isdir(args.config_dir):
            print(f"ERROR: Config directory not found: {args.config_dir}", file=sys.stderr)
            return 1
        definitions = factory.load_definitions(args.config_dir, args.start, args.end)
        if not definitions:
            print("No definitions loaded. Check config directory and --start/--end range.")
            return 1
        print(f"Generating {len(definitions)} strategies...")
        results = factory.batch_generate(definitions, args.output_dir)
        successes = sum(1 for _, v in results if v.valid)
        failures = len(results) - successes
        print(f"\nBatch generation complete: {successes} success, {failures} failures")
        for path, validation in results:
            if validation.valid:
                print(f"  OK: {path}")
            else:
                print(f"  FAIL: {path}")
                for err in validation.errors:
                    print(f"    - {err}")
        return 0 if failures == 0 else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
