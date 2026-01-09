
#!/usr/bin/env python3
"""
Simple test to check what data is actually available on Crypto Lake.
Bypasses the problematic available_symbols() call.
"""

import os
import lakeapi
from datetime import datetime, timedelta

# Set your Crypto Lake credentials
API_KEY = 'REDACTED_AWS_KEY'
API_SECRET = 'REDACTED_AWS_SECRET'

os.environ['AWS_ACCESS_KEY_ID'] = API_KEY
os.environ['AWS_SECRET_ACCESS_KEY'] = API_SECRET
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'

print("=" * 80)
print("CRYPTO LAKE DATA AVAILABILITY - DIRECT TEST")
print("=" * 80)

# Data types to test
DATA_TYPES = [
    'trades',
    'book',
    'book_delta_v2',
    'book_1m',
    'deep_book_1m',
    'level_1',
    'candles',
    'funding',
    'open_interest',
    'liquidations',
]

# Test symbols
TESTS = [
    ('BINANCE', 'BTC-USDT'),
    ('BINANCE_FUTURES', 'BTC-USDT-PERP'),
]

# Time range for testing
test_start = datetime.now() - timedelta(days=7)  # Last 7 days
test_end = datetime.now()

print(f"\nTest period: {test_start.strftime('%Y-%m-%d')} to {test_end.strftime('%Y-%m-%d')}")
print(f"Testing: BTC on both BINANCE and BINANCE_FUTURES\n")

results = {}

for data_type in DATA_TYPES:
    print(f"\n{'=' * 80}")
    print(f"Testing: {data_type.upper()}")
    print(f"{'=' * 80}")

    for exchange, symbol in TESTS:
        try:
            print(f"\n[{exchange}] {symbol} - ", end='', flush=True)

            df = lakeapi.load_data(
                table=data_type,
                start=test_start,
                end=test_end,
                symbols=[symbol],
                exchanges=[exchange]
            )

            # Check if we got data
            if df is not None:
                row_count = len(df)
                if row_count > 0:
                    print(f"✓ SUCCESS ({row_count:,} rows)")
                    print(f"   Columns: {list(df.columns)[:5]}...")  # Show first 5 columns

                    key = f"{data_type}_{exchange}"
                    results[key] = {'success': True, 'rows': row_count}
                else:
                    print(f"⚠ Empty (0 rows)")
                    results[f"{data_type}_{exchange}"] = {'success': False, 'reason': 'empty'}
            else:
                print(f"⚠ None returned")
                results[f"{data_type}_{exchange}"] = {'success': False, 'reason': 'none'}

        except Exception as e:
            error_str = str(e)
            # Show only first 80 chars of error
            if 'SignatureDoesNotMatch' in error_str:
                print(f"✗ SignatureDoesNotMatch (auth issue)")
            elif 'NoSuchKey' in error_str or '404' in error_str:
                print(f"✗ Data not found (404)")
            elif 'not found' in error_str.lower():
                print(f"✗ Data type not available")
            else:
                short_error = error_str[:60]
                print(f"✗ Error: {short_error}...")

            results[f"{data_type}_{exchange}"] = {'success': False, 'error': str(e)[:100]}

print("\n" + "=" * 80)
print("RESULTS SUMMARY")
print("=" * 80)

print("\nData Type Availability Matrix:\n")
print(f"{'Data Type':<20} {'BINANCE':<20} {'BINANCE_FUTURES':<20}")
print("-" * 60)

for data_type in DATA_TYPES:
    binance_key = f"{data_type}_BINANCE"
    futures_key = f"{data_type}_BINANCE_FUTURES"

    binance_result = results.get(binance_key, {})
    futures_result = results.get(futures_key, {})

    binance_status = "✓" if binance_result.get('success') else "✗"
    futures_status = "✓" if futures_result.get('success') else "✗"

    binance_detail = f"({binance_result.get('rows', 0):,} rows)" if binance_result.get('success') else ""
    futures_detail = f"({futures_result.get('rows', 0):,} rows)" if futures_result.get('success') else ""

    print(f"{data_type:<20} {binance_status} {binance_detail:<18} {futures_status} {futures_detail:<18}")

print("\n" + "=" * 80)
print("INTERPRETATION")
print("=" * 80)

working = [k for k, v in results.items() if v.get('success')]
print(f"\n✓ Working data types: {len(working)}")
for key in working:
    print(f"  • {key}")

if len(working) == 0:
    print("\n⚠ WARNING: No data types are working!")
    print("  Possible reasons:")
    print("  1. Your credentials are not fully activated yet (wait 10-15 minutes)")
    print("  2. Your subscription doesn't include Binance data")
    print("  3. Check your subscription tier at https://crypto-lake.com/account")

print("\n✗ Not available or failed:")
failed = [k for k, v in results.items() if not v.get('success')]
for key in failed:
    reason = results[key].get('reason', results[key].get('error', 'unknown'))
    print(f"  • {key}: {reason}")

print("\n" + "=" * 80)

