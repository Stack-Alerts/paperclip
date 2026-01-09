#!/usr/bin/env python3
"""
Lake API S3 Bucket Scanner

Traverses the qnt.data S3 bucket and generates markdown documentation
of available data paths. Supports incremental updates and symbol filtering.

Usage:
    python3 lake_api_scanner.py                    # Scan all data
    python3 lake_api_scanner.py --symbol BTC       # Only BTC-* symbols
    python3 lake_api_scanner.py --symbol ETH --force  # Force full rescan
    python3 lake_api_scanner.py --symbol BTC --table trades  # Specific table
"""

import json
import gzip
import boto3
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict
from datetime import datetime
import argparse
import sys

# Configuration
S3_BUCKET = "qnt.data"
S3_PREFIX = "market-data/cryptofeed/"
CACHE_DIR = Path(".lake_cache")
CACHE_FILE = CACHE_DIR / "lake_inventory.json"
OUTPUT_DIR = Path(".")

# Available tables in Lake API
TABLES = [
    "book",
    "book_1m",
    "book_delta",
    "book_delta_v2",
    "book_old",
    "candles",
    "deep_book_1m",
    "funding",
    "level_1",
    "level1",
    "liquidations",
    "open_interest",
    "trades",
    "trades_mpid",
]


class LakeAPIScanner:
    def __init__(self, force_refresh: bool = False):
        """Initialize the scanner."""
        self.s3 = boto3.client("s3")
        self.cache_dir = CACHE_DIR
        self.cache_file = CACHE_FILE
        self.cache_dir.mkdir(exist_ok=True)
        self.force_refresh = force_refresh
        self.inventory: Dict = {"last_updated": None, "tables": {}}
        self.load_cache()

    def load_cache(self):
        """Load cached inventory if it exists."""
        if self.cache_file.exists() and not self.force_refresh:
            try:
                with open(self.cache_file, "r") as f:
                    self.inventory = json.load(f)
                print(f"✅ Loaded cache from {self.cache_file}")
                print(
                    f"   Last updated: {self.inventory.get('last_updated', 'Unknown')}"
                )
            except Exception as e:
                print(f"⚠️  Could not load cache: {e}")
                self.inventory = {"last_updated": None, "tables": {}}
        else:
            print("🔄 Starting fresh scan (cache disabled or forced refresh)")

    def save_cache(self):
        """Save inventory to cache."""
        self.inventory["last_updated"] = datetime.now().isoformat()
        with open(self.cache_file, "w") as f:
            json.dump(self.inventory, f, indent=2)
        print(f"💾 Cache saved to {self.cache_file}")

    def download_contents_file(self, table: str) -> Optional[List[Dict]]:
        """Download and decompress contents.json.gz file."""
        try:
            key = f"{S3_PREFIX}{table}/contents.json.gz"
            print(f"   📥 Downloading {table}/contents.json.gz...", end="", flush=True)

            response = self.s3.get_object(Bucket=S3_BUCKET, Key=key)
            compressed_data = response["Body"].read()
            decompressed_data = gzip.decompress(compressed_data)
            contents = json.loads(decompressed_data)

            print(f" ✅ ({len(contents)} entries)")
            return contents
        except self.s3.exceptions.NoSuchKey:
            print(f" ⚠️  File not found")
            return None
        except Exception as e:
            print(f" ❌ Error: {e}")
            return None

    def parse_s3_path(self, path: str) -> Dict[str, str]:
        """Parse S3 path to extract components."""
        # Format: exchange=BINANCE_FUTURES/symbol=BTC-USDT/dt=2022-12-09
        components = {}
        for part in path.split("/"):
            if "=" in part:
                key, value = part.split("=", 1)
                components[key] = value
        return components

    def scan_table(self, table: str) -> Dict:
        """Scan a table and extract available data."""
        print(f"\n🔍 Scanning table: {table}")

        # Check if we have cached data for this table
        if (
            table in self.inventory["tables"]
            and not self.force_refresh
        ):
            print(f"   ✅ Using cached data ({len(self.inventory['tables'][table])} entries)")
            return self.inventory["tables"][table]

        # Download contents file
        contents = self.download_contents_file(table)
        if not contents:
            return {}

        # Parse and organize data
        table_data = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))

        for entry in contents:
            exchange = entry.get("exchange", "UNKNOWN")
            symbol = entry.get("symbol", "UNKNOWN")
            dt = entry.get("dt", "UNKNOWN")

            table_data[exchange][symbol]["dates"].add(dt)

            # Extract quote currency from symbol (e.g., BTC-USDT -> USDT)
            if "-" in symbol:
                parts = symbol.split("-")
                base = parts[0]
                quote = parts[1] if len(parts) > 1 else ""
                table_data[exchange][symbol]["base"] = base
                table_data[exchange][symbol]["quote"] = quote

        # Convert sets to sorted lists for JSON serialization
        result = {}
        for exchange, symbols in table_data.items():
            result[exchange] = {}
            for symbol, data in symbols.items():
                dates = sorted(list(data["dates"]))
                result[exchange][symbol] = {
                    "dates": dates,
                    "count": len(dates),
                    "first_date": dates[0] if dates else None,
                    "last_date": dates[-1] if dates else None,
                    "base": data.get("base", ""),
                    "quote": data.get("quote", ""),
                }

        self.inventory["tables"][table] = result
        return result

    def scan_all_tables(self):
        """Scan all available tables."""
        print("=" * 80)
        print("LAKE API S3 BUCKET SCANNER")
        print("=" * 80)

        for table in TABLES:
            self.scan_table(table)

        self.save_cache()
        print("\n✅ Scan complete!")

    def filter_by_symbol(self, symbol_filter: Optional[str]) -> Dict:
        """Filter inventory by symbol."""
        if not symbol_filter:
            return self.inventory["tables"]

        filtered = {}
        symbol_upper = symbol_filter.upper()

        for table, exchanges in self.inventory["tables"].items():
            filtered_table = {}
            for exchange, symbols in exchanges.items():
                filtered_symbols = {}
                for symbol, data in symbols.items():
                    # Match if symbol starts with filter (e.g., BTC matches BTC-USDT)
                    if symbol.startswith(symbol_upper):
                        filtered_symbols[symbol] = data
                if filtered_symbols:
                    filtered_table[exchange] = filtered_symbols
            if filtered_table:
                filtered[table] = filtered_table

        return filtered

    def generate_markdown(self, symbol_filter: Optional[str] = None) -> str:
        """Generate markdown documentation."""
        filtered = self.filter_by_symbol(symbol_filter)

        if not filtered:
            return "No data found matching the filter."

        md = []
        md.append("# Lake API Data Availability\n")

        if symbol_filter:
            md.append(f"**Filter**: `{symbol_filter}`\n")

        md.append(
            f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
        )

        # Table of Contents
        md.append("## Table of Contents\n")
        for table in sorted(filtered.keys()):
            md.append(f"- [{table}](#{table})\n")
        md.append("\n")

        # Detailed section for each table
        for table in sorted(filtered.keys()):
            exchanges = filtered[table]
            md.append(f"## {table}\n\n")

            for exchange in sorted(exchanges.keys()):
                symbols = exchanges[exchange]
                md.append(f"### {exchange}\n\n")

                # Create table
                md.append("| Symbol | Quote | Date Range | Days | Path |\n")
                md.append("|--------|-------|------------|------|------|\n")

                for symbol in sorted(symbols.keys()):
                    data = symbols[symbol]
                    date_range = f"{data['first_date']} to {data['last_date']}"
                    count = data["count"]
                    quote = data.get("quote", "")
                    s3_path = (
                        f"`s3://{S3_BUCKET}/{S3_PREFIX}{table}/exchange={exchange}/symbol={symbol}/`"
                    )

                    md.append(
                        f"| {symbol} | {quote} | {date_range} | {count} | {s3_path} |\n"
                    )

                md.append("\n")

            md.append("\n---\n\n")

        return "".join(md)

    def write_markdown(
        self, filename: str, content: str
    ):
        """Write markdown to file."""
        filepath = OUTPUT_DIR / filename
        with open(filepath, "w") as f:
            f.write(content)
        print(f"✅ Written to {filepath}")

    def print_summary(self, symbol_filter: Optional[str] = None):
        """Print summary statistics."""
        filtered = self.filter_by_symbol(symbol_filter)

        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)

        total_tables = len(filtered)
        total_exchanges = sum(len(exch) for exch in filtered.values())
        total_symbols = sum(
            len(syms) for table in filtered.values() for syms in table.values()
        )
        total_days = sum(
            data["count"]
            for table in filtered.values()
            for exch in table.values()
            for data in exch.values()
        )

        print(f"Tables: {total_tables}")
        print(f"Exchanges: {total_exchanges}")
        print(f"Unique Symbols: {total_symbols}")
        print(f"Total Day-Symbols: {total_days}")

        # Show exchanges and symbols per table
        print("\nBreakdown by table:")
        for table in sorted(filtered.keys()):
            exchanges = filtered[table]
            symbols_in_table = sum(len(exch) for exch in exchanges.values())
            exchanges_in_table = len(exchanges)
            print(f"  {table}: {exchanges_in_table} exchanges, {symbols_in_table} symbols")


def main():
    parser = argparse.ArgumentParser(
        description="Scan Lake API S3 bucket and generate markdown documentation"
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default=None,
        help='Filter by symbol prefix (e.g., "BTC" for all BTC-* pairs)',
    )
    parser.add_argument(
        "--table",
        type=str,
        default=None,
        help="Specific table to scan (default: all tables)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force full rescan, ignore cache",
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Skip printing summary",
    )

    args = parser.parse_args()

    # Initialize scanner
    scanner = LakeAPIScanner(force_refresh=args.force)

    # Scan tables
    if args.table:
        scanner.scan_table(args.table)
    else:
        scanner.scan_all_tables()

    # Generate markdown
    print("\n" + "=" * 80)
    print("GENERATING MARKDOWN")
    print("=" * 80)

    markdown = scanner.generate_markdown(symbol_filter=args.symbol)

    # Determine output filename
    if args.symbol:
        filename = f"Lake_api_paths_{args.symbol.upper()}.md"
    else:
        filename = "Lake_api_paths.md"

    scanner.write_markdown(filename, markdown)

    # Print summary
    if not args.no_summary:
        scanner.print_summary(symbol_filter=args.symbol)

    print("\n✨ Done!")


if __name__ == "__main__":
    main()
