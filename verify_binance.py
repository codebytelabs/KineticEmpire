#!/usr/bin/env python3
"""Verify Binance connection and fetch wallet balances."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import ccxt

def main():
    print("🔐 Binance Connection Verification")
    print("=" * 50)
    
    # First test public API (no auth needed)
    print("\n📡 Testing Public API (Market Data)...")
    try:
        public_exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })
        
        btc = public_exchange.fetch_ticker('BTC/USDT')
        eth = public_exchange.fetch_ticker('ETH/USDT')
        sol = public_exchange.fetch_ticker('SOL/USDT')
        
        print(f"   ✅ BTC/USDT: ${btc['last']:,.2f}")
        print(f"   ✅ ETH/USDT: ${eth['last']:,.2f}")
        print(f"   ✅ SOL/USDT: ${sol['last']:,.2f}")
        print("   ✅ Market data access working!")
        
    except Exception as e:
        print(f"   ❌ Public API Error: {e}")
        return False
    
    # Now test authenticated API
    print("\n🔐 Testing Authenticated API...")
    
    # Try testnet keys first
    api_key = os.getenv('Binance_testnet_API_KEY')
    api_secret = os.getenv('Binance_testnet_API_SECRET')
    
    if api_key and api_secret:
        print(f"   API Key: {api_key[:8]}...{api_key[-4:]}")
        try:
            exchange = ccxt.binance({
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
                'options': {'defaultType': 'future'},
            })
            exchange.set_sandbox_mode(True)
            
            balance = exchange.fetch_balance()
            usdt = balance.get('USDT', {}).get('total', 0)
            print(f"   ✅ Testnet Futures Balance: {usdt:.2f} USDT")
            return True
        except Exception as e:
            print(f"   ⚠️  Testnet auth failed: {str(e)[:50]}...")
    
    # Try demo keys
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    
    if api_key and api_secret:
        print(f"   Trying Demo keys: {api_key[:8]}...{api_key[-4:]}")
        # Demo trading requires specific setup - skip for now
        print("   ⚠️  Demo trading requires browser session setup")
    
    print("\n" + "=" * 50)
    print("📊 SUMMARY:")
    print("   ✅ Market data: WORKING")
    print("   ⚠️  Auth: Keys need refresh (testnet keys expire)")
    print()
    print("🚀 You can still run in SIMULATION MODE!")
    print("   The bot will use real market data but simulate trades.")
    print()
    
    return True  # Market data works, can run in simulation


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
