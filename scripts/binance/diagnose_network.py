"""
Binance Network Diagnostics - Identify Connection Issues

This script performs comprehensive network diagnostics to identify
why fapi.binance.com might not be accessible.

Tests:
1. DNS resolution
2. Ping connectivity
3. HTTP/HTTPS connection
4. API endpoints
5. Compare spot vs futures

Author: BTC_Engine_v3
Date: January 8, 2026
"""

import socket
import requests
import sys
from urllib.parse import urlparse
import subprocess


def test_dns(hostname):
    """Test DNS resolution"""
    print(f"\n{'='*70}")
    print(f"TEST 1: DNS RESOLUTION - {hostname}")
    print('='*70)
    
    try:
        ip_address = socket.gethostbyname(hostname)
        print(f"✅ DNS Resolution: SUCCESS")
        print(f"   Hostname: {hostname}")
        print(f"   IP Address: {ip_address}")
        return True, ip_address
    except socket.gaierror as e:
        print(f"❌ DNS Resolution: FAILED")
        print(f"   Error: {e}")
        print(f"   Possible causes:")
        print(f"   - DNS server cannot resolve this hostname")
        print(f"   - Network firewall blocking DNS queries")
        print(f"   - Hostname does not exist")
        return False, None


def test_tcp_connection(hostname, port=443):
    """Test TCP connection"""
    print(f"\n{'='*70}")
    print(f"TEST 2: TCP CONNECTION - {hostname}:{port}")
    print('='*70)
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((hostname, port))
        sock.close()
        
        if result == 0:
            print(f"✅ TCP Connection: SUCCESS")
            print(f"   Can establish TCP connection on port {port}")
            return True
        else:
            print(f"❌ TCP Connection: FAILED")
            print(f"   Error code: {result}")
            print(f"   Possible causes:")
            print(f"   - Port {port} is filtered/blocked")
            print(f"   - Firewall preventing connection")
            return False
    except Exception as e:
        print(f"❌ TCP Connection: ERROR")
        print(f"   Error: {e}")
        return False


def test_http_request(url, label=""):
    """Test HTTP/HTTPS request"""
    print(f"\n{'='*70}")
    print(f"TEST 3: HTTP REQUEST - {label if label else url}")
    print('='*70)
    
    try:
        print(f"   URL: {url}")
        response = requests.get(url, timeout=10)
        print(f"✅ HTTP Request: SUCCESS")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response Time: {response.elapsed.total_seconds():.2f}s")
        
        if response.status_code == 200:
            print(f"   Response preview: {str(response.text)[:100]}...")
        
        return True, response
    except requests.exceptions.ConnectionError as e:
        print(f"❌ HTTP Request: CONNECTION ERROR")
        print(f"   Error: {e}")
        print(f"   Possible causes:")
        print(f"   - Server is down")
        print(f"   - Network blocking HTTPS traffic")
        print(f"   - SSL/TLS issues")
        return False, None
    except requests.exceptions.Timeout as e:
        print(f"❌ HTTP Request: TIMEOUT")
        print(f"   Error: {e}")
        return False, None
    except Exception as e:
        print(f"❌ HTTP Request: ERROR")
        print(f"   Error: {e}")
        return False, None


def test_api_endpoint(url, label=""):
    """Test specific API endpoint"""
    print(f"\n{'='*70}")
    print(f"TEST 4: API ENDPOINT - {label if label else url}")
    print('='*70)
    
    try:
        print(f"   URL: {url}")
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ API Endpoint: SUCCESS")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")
            return True, response
        else:
            print(f"⚠️  API Endpoint: ACCESSIBLE but returned {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return True, response
            
    except Exception as e:
        print(f"❌ API Endpoint: FAILED")
        print(f"   Error: {e}")
        return False, None


def run_diagnostics():
    """Run complete diagnostics"""
    print("\n" + "="*70)
    print("BINANCE NETWORK DIAGNOSTICS")
    print("="*70)
    print()
    print("Testing Binance API connectivity...")
    print("This will help identify why fapi.binance.com may not be accessible")
    print()
    
    results = {
        'spot': {},
        'futures': {}
    }
    
    # Test SPOT API
    print("\n" + "#"*70)
    print("# TESTING SPOT API (api.binance.com)")
    print("#"*70)
    
    spot_hostname = 'api.binance.com'
    
    # DNS
    success, ip = test_dns(spot_hostname)
    results['spot']['dns'] = success
    results['spot']['ip'] = ip
    
    # TCP
    if success:
        results['spot']['tcp'] = test_tcp_connection(spot_hostname)
    
    # HTTP Ping
    results['spot']['ping'], _ = test_http_request(
        'https://api.binance.com/api/v3/ping',
        'Spot API Ping'
    )
    
    # HTTP Get Time
    results['spot']['time'], _ = test_http_request(
        'https://api.binance.com/api/v3/time',
        'Spot API Server Time'
    )
    
    # HTTP Get Ticker
    results['spot']['ticker'], _ = test_api_endpoint(
        'https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT',
        'Spot API Ticker'
    )
    
    # Test FUTURES API
    print("\n" + "#"*70)
    print("# TESTING FUTURES API (fapi.binance.com)")
    print("#"*70)
    
    futures_hostname = 'fapi.binance.com'
    
    # DNS
    success, ip = test_dns(futures_hostname)
    results['futures']['dns'] = success
    results['futures']['ip'] = ip
    
    # TCP
    if success:
        results['futures']['tcp'] = test_tcp_connection(futures_hostname)
    
    # HTTP Ping
    results['futures']['ping'], _ = test_http_request(
        'https://fapi.binance.com/fapi/v1/ping',
        'Futures API Ping'
    )
    
    # HTTP Get Time
    results['futures']['time'], _ = test_http_request(
        'https://fapi.binance.com/fapi/v1/time',
        'Futures API Server Time'
    )
    
    # HTTP Get Exchange Info
    results['futures']['info'], _ = test_api_endpoint(
        'https://fapi.binance.com/fapi/v1/exchangeInfo',
        'Futures API Exchange Info'
    )
    
    # Summary
    print("\n" + "="*70)
    print("DIAGNOSTIC SUMMARY")
    print("="*70)
    
    print("\n📊 SPOT API (api.binance.com):")
    print(f"   DNS Resolution: {'✅ PASS' if results['spot'].get('dns') else '❌ FAIL'}")
    if results['spot'].get('ip'):
        print(f"   IP Address: {results['spot']['ip']}")
    print(f"   TCP Connection: {'✅ PASS' if results['spot'].get('tcp') else '❌ FAIL'}")
    print(f"   Ping Endpoint: {'✅ PASS' if results['spot'].get('ping') else '❌ FAIL'}")
    print(f"   Time Endpoint: {'✅ PASS' if results['spot'].get('time') else '❌ FAIL'}")
    print(f"   Ticker Endpoint: {'✅ PASS' if results['spot'].get('ticker') else '❌ FAIL'}")
    
    spot_pass = all([
        results['spot'].get('dns'),
        results['spot'].get('tcp'),
        results['spot'].get('ping')
    ])
    
    print("\n📊 FUTURES API (fapi.binance.com):")
    print(f"   DNS Resolution: {'✅ PASS' if results['futures'].get('dns') else '❌ FAIL'}")
    if results['futures'].get('ip'):
        print(f"   IP Address: {results['futures']['ip']}")
    print(f"   TCP Connection: {'✅ PASS' if results['futures'].get('tcp') else '❌ FAIL'}")
    print(f"   Ping Endpoint: {'✅ PASS' if results['futures'].get('ping') else '❌ FAIL'}")
    print(f"   Time Endpoint: {'✅ PASS' if results['futures'].get('time') else '❌ FAIL'}")
    print(f"   Info Endpoint: {'✅ PASS' if results['futures'].get('info') else '❌ FAIL'}")
    
    futures_pass = all([
        results['futures'].get('dns'),
        results['futures'].get('tcp'),
        results['futures'].get('ping')
    ])
    
    # Diagnosis
    print("\n" + "="*70)
    print("DIAGNOSIS")
    print("="*70)
    
    if spot_pass and futures_pass:
        print("\n✅ BOTH APIs ARE ACCESSIBLE!")
        print("   No network issues detected.")
        print("   You can use both Spot and Futures APIs.")
        print()
        print("Next step: Run backfill script to get December 2025 data")
        print("  python scripts/binance/backfill_december.py")
        
    elif spot_pass and not futures_pass:
        print("\n⚠️  SPOT API WORKS, BUT FUTURES API HAS ISSUES")
        
        if not results['futures'].get('dns'):
            print("\n   Issue: DNS Resolution Failed")
            print("   Possible solutions:")
            print("   1. Check /etc/resolv.conf")
            print("   2. Try different DNS server (8.8.8.8)")
            print("   3. Check if hostname exists: nslookup fapi.binance.com")
            
        elif not results['futures'].get('tcp'):
            print("\n   Issue: Cannot establish TCP connection")
            print("   Possible solutions:")
            print("   1. Check firewall rules")
            print("   2. Check if port 443 is open: telnet fapi.binance.com 443")
            print("   3. Try from different network")
            
        else:
            print("\n   Issue: HTTP/HTTPS request failed")
            print("   Possible solutions:")
            print("   1. Check SSL/TLS certificates")
            print("   2. Check proxy settings")
            print("   3. Try: curl -v https://fapi.binance.com/fapi/v1/ping")
    
    elif not spot_pass and not futures_pass:
        print("\n❌ BOTH APIs ARE INACCESSIBLE")
        print("\n   Issue: Complete network connectivity problem")
        print("   Possible solutions:")
        print("   1. Check internet connection")
        print("   2. Check firewall/proxy settings")
        print("   3. Try: ping 8.8.8.8")
        print("   4. Try: curl https://www.google.com")
    
    else:
        print("\n⚠️  FUTURES API WORKS, BUT SPOT API HAS ISSUES")
        print("   Unexpected - usually spot is more reliable")
    
    print("\n" + "="*70)
    print()


if __name__ == "__main__":
    run_diagnostics()