#!/usr/bin/env python
"""
Standalone test - no imports from our code
"""
import requests
from datetime import datetime

print('🔍 STANDALONE SCRIPT TEST:')
print('='*60)

# Test 1: Direct call
response = requests.get(
    'https://fapi.binance.com/fapi/v1/klines',
    params={'symbol': 'BTCUSDT', 'interval': '15m', 'limit': 3},
    timeout=10
)
data = response.json()

print('\\n1️⃣ Direct Call:')
for candle in data:
    ts = datetime.fromtimestamp(candle[0] / 1000)
    print(f'  {ts}')
latest1 = datetime.fromtimestamp(data[-1][0] / 1000)

# Test 2: Through our REST client
print('\\n2️⃣ Our REST Client:')
from src.data_manager.binance.rest_client import BinanceRestClient

client = BinanceRestClient()
bars = client.get_klines('15m', limit=3, futures=True)
for ts in bars['timestamp']:
    print(f'  {ts}')
latest2 = bars['timestamp'].iloc[-1]

# Compare
print(f'\\n📊 COMPARISON:')
print(f'Direct: {latest1} ({(datetime.now() - latest1).total_seconds() / 60:.1f} min)')
print(f'Client: {latest2} ({(datetime.now() - latest2).total_seconds() / 60:.1f} min)')

if latest1 == latest2:
    print('\\n✅ MATCH - No caching issue!')
else:
    print(f'\\n❌ MISMATCH - Client is {((latest1 - latest2).total_seconds() / 60):.0f} min behind!')
