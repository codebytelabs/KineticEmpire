#!/usr/bin/env python3
"""Test module for Binance Demo Trading API connection."""
import hashlib
import hmac
import time
import requests
import ccxt

# Binance Demo Trading credentials
API_KEY = 'lGdIQ3ve6XQJ32DIAbDdEBH5dCB2vQYLsHVTLHrgl9nJhzPc0MgV3C7Es7EUbH5E'
API_SECRET = 'GfrTAWwEcWoUKnP5a8FSxIk9rU8AN3yN9oVZBynpt5BDwM0sJ1Gxku5epjEQPR5o'

# Demo API endpoints
DEMO_SPOT_URL = 'https://demo-api.binance.com'
DEMO_FUTURES_URL = 'https://demo-fapi.binance.com'


def sign_request(params: dict, secret: str) -> str:
    """Create HMAC SHA256 signature."""
    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    signature = hmac.new(
        secret.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature


def test_demo_spot_public():
    """Test Demo Spot public endpoint (no auth)."""
    print("\n" + "="*60)
    print("TEST 1: Demo Spot Public API (No Auth)")
    print("="*60)
    
    url = f"{DEMO_SPOT_URL}/api/v3/ping"
    try:
        response = requests.get(url, timeout=10)
        print(f"URL: {url}")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_demo_spot_ticker():
    """Test Demo Spot ticker endpoint."""
    print("\n" + "="*60)
    print("TEST 2: Demo Spot Ticker (No Auth)")
    print("="*60)
    
    url = f"{DEMO_SPOT_URL}/api/v3/ticker/price"
    params = {'symbol': 'BTCUSDT'}
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"URL: {url}")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_demo_spot_account():
    """Test Demo Spot account endpoint (requires auth)."""
    print("\n" + "="*60)
    print("TEST 3: Demo Spot Account (With Auth)")
    print("="*60)
    
    timestamp = int(time.time() * 1000)
    params = {
        'timestamp': timestamp,
        'recvWindow': 60000
    }
    
    signature = sign_request(params, API_SECRET)
    params['signature'] = signature
    
    headers = {'X-MBX-APIKEY': API_KEY}
    url = f"{DEMO_SPOT_URL}/api/v3/account"
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        print(f"URL: {url}")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_demo_futures_public():
    """Test Demo Futures public endpoint."""
    print("\n" + "="*60)
    print("TEST 4: Demo Futures Public API (No Auth)")
    print("="*60)
    
    url = f"{DEMO_FUTURES_URL}/fapi/v1/ping"
    try:
        response = requests.get(url, timeout=10)
        print(f"URL: {url}")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_demo_futures_ticker():
    """Test Demo Futures ticker."""
    print("\n" + "="*60)
    print("TEST 5: Demo Futures Ticker (No Auth)")
    print("="*60)
    
    url = f"{DEMO_FUTURES_URL}/fapi/v1/ticker/price"
    params = {'symbol': 'BTCUSDT'}
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"URL: {url}")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_demo_futures_account():
    """Test Demo Futures account (requires auth)."""
    print("\n" + "="*60)
    print("TEST 6: Demo Futures Account (With Auth)")
    print("="*60)
    
    timestamp = int(time.time() * 1000)
    params = {
        'timestamp': timestamp,
        'recvWindow': 60000
    }
    
    signature = sign_request(params, API_SECRET)
    params['signature'] = signature
    
    headers = {'X-MBX-APIKEY': API_KEY}
    url = f"{DEMO_FUTURES_URL}/fapi/v2/account"
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        print(f"URL: {url}")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_demo_futures_balance():
    """Test Demo Futures balance."""
    print("\n" + "="*60)
    print("TEST 7: Demo Futures Balance (With Auth)")
    print("="*60)
    
    timestamp = int(time.time() * 1000)
    params = {
        'timestamp': timestamp,
        'recvWindow': 60000
    }
    
    signature = sign_request(params, API_SECRET)
    params['signature'] = signature
    
    headers = {'X-MBX-APIKEY': API_KEY}
    url = f"{DEMO_FUTURES_URL}/fapi/v2/balance"
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        print(f"URL: {url}")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_ccxt_demo_spot():
    """Test CCXT with Demo Spot."""
    print("\n" + "="*60)
    print("TEST 8: CCXT Demo Spot")
    print("="*60)
    
    try:
        exchange = ccxt.binance({
            'apiKey': API_KEY,
            'secret': API_SECRET,
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'},
        })
        
        # Override URLs for demo
        exchange.urls['api'] = {
            'public': 'https://demo-api.binance.com/api/v3',
            'private': 'https://demo-api.binance.com/api/v3',
        }
        
        balance = exchange.fetch_balance()
        print(f"✅ CCXT Demo Spot connected!")
        print(f"USDT: {balance.get('USDT', {})}")
        return True
    except Exception as e:
        print(f"❌ CCXT Error: {e}")
        return False


def test_ccxt_demo_futures():
    """Test CCXT with Demo Futures."""
    print("\n" + "="*60)
    print("TEST 9: CCXT Demo Futures")
    print("="*60)
    
    try:
        exchange = ccxt.binance({
            'apiKey': API_KEY,
            'secret': API_SECRET,
            'enableRateLimit': True,
            'options': {'defaultType': 'future'},
        })
        
        # Override URLs for demo futures
        exchange.urls['api'] = {
            'fapiPublic': 'https://demo-fapi.binance.com/fapi/v1',
            'fapiPrivate': 'https://demo-fapi.binance.com/fapi/v1',
            'fapiPublicV2': 'https://demo-fapi.binance.com/fapi/v2',
            'fapiPrivateV2': 'https://demo-fapi.binance.com/fapi/v2',
        }
        
        balance = exchange.fetch_balance()
        print(f"✅ CCXT Demo Futures connected!")
        print(f"USDT: {balance.get('USDT', {})}")
        return True
    except Exception as e:
        print(f"❌ CCXT Error: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "🔬 BINANCE DEMO API TEST SUITE 🔬")
    print("="*60)
    print(f"API Key: {API_KEY[:16]}...{API_KEY[-4:]}")
    print(f"Demo Spot URL: {DEMO_SPOT_URL}")
    print(f"Demo Futures URL: {DEMO_FUTURES_URL}")
    
    results = {}
    
    # Run all tests
    results['demo_spot_public'] = test_demo_spot_public()
    results['demo_spot_ticker'] = test_demo_spot_ticker()
    results['demo_spot_account'] = test_demo_spot_account()
    results['demo_futures_public'] = test_demo_futures_public()
    results['demo_futures_ticker'] = test_demo_futures_ticker()
    results['demo_futures_account'] = test_demo_futures_account()
    results['demo_futures_balance'] = test_demo_futures_balance()
    results['ccxt_demo_spot'] = test_ccxt_demo_spot()
    results['ccxt_demo_futures'] = test_ccxt_demo_futures()
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST RESULTS SUMMARY")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    passed_count = sum(results.values())
    total_count = len(results)
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    return all(results.values())


if __name__ == "__main__":
    main()
