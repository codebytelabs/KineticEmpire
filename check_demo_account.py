#!/usr/bin/env python3
"""Check Binance Demo Futures account and close all positions."""
import hashlib
import hmac
import time
import requests
import sys

API_KEY = 'lGdIQ3ve6XQJ32DIAbDdEBH5dCB2vQYLsHVTLHrgl9nJhzPc0MgV3C7Es7EUbH5E'
API_SECRET = 'GfrTAWwEcWoUKnP5a8FSxIk9rU8AN3yN9oVZBynpt5BDwM0sJ1Gxku5epjEQPR5o'
BASE_URL = 'https://demo-fapi.binance.com'

def sign(params):
    query = '&'.join([f'{k}={v}' for k, v in params.items()])
    return hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()

headers = {'X-MBX-APIKEY': API_KEY}

def get_account():
    params = {'timestamp': int(time.time() * 1000), 'recvWindow': 60000}
    params['signature'] = sign(params)
    resp = requests.get(f'{BASE_URL}/fapi/v2/account', params=params, headers=headers)
    return resp.json()

def get_balances():
    params = {'timestamp': int(time.time() * 1000), 'recvWindow': 60000}
    params['signature'] = sign(params)
    resp = requests.get(f'{BASE_URL}/fapi/v2/balance', params=params, headers=headers)
    return resp.json()

def get_positions():
    params = {'timestamp': int(time.time() * 1000), 'recvWindow': 60000}
    params['signature'] = sign(params)
    resp = requests.get(f'{BASE_URL}/fapi/v2/positionRisk', params=params, headers=headers)
    return resp.json()

def close_position(symbol, side, quantity):
    """Close a position by placing opposite order."""
    params = {
        'symbol': symbol,
        'side': 'SELL' if side == 'LONG' else 'BUY',
        'type': 'MARKET',
        'quantity': abs(quantity),
        'timestamp': int(time.time() * 1000),
        'recvWindow': 60000
    }
    params['signature'] = sign(params)
    resp = requests.post(f'{BASE_URL}/fapi/v1/order', params=params, headers=headers)
    return resp.json()

def main():
    print('='*60)
    print('💰 BINANCE DEMO USD-M FUTURES ACCOUNT')
    print('='*60)
    
    account = get_account()
    print(f"Total Wallet Balance: ${float(account.get('totalWalletBalance', 0)):,.2f}")
    print(f"Unrealized PnL: ${float(account.get('totalUnrealizedProfit', 0)):,.2f}")
    print(f"Margin Balance: ${float(account.get('totalMarginBalance', 0)):,.2f}")
    print(f"Available Balance: ${float(account.get('availableBalance', 0)):,.2f}")
    print()
    
    # Get balances
    balances = get_balances()
    print('📊 ASSET BREAKDOWN:')
    print('-'*60)
    for b in balances:
        bal = float(b.get('balance', 0))
        if bal > 0:
            print(f"  {b['asset']}: {bal:,.8f}")
    
    # Get positions
    positions = get_positions()
    print()
    print('📈 OPEN POSITIONS:')
    print('-'*60)
    
    open_positions = []
    for p in positions:
        amt = float(p.get('positionAmt', 0))
        if amt != 0:
            open_positions.append(p)
            pnl = float(p.get('unRealizedProfit', 0))
            entry = float(p.get('entryPrice', 0))
            mark = float(p.get('markPrice', 0))
            side = 'LONG' if amt > 0 else 'SHORT'
            print(f"  {p['symbol']}: {side} {abs(amt)} @ ${entry:.4f}")
            print(f"    Mark: ${mark:.4f}, PnL: ${pnl:.2f}")
    
    if not open_positions:
        print('  ✅ No open positions')
    
    print()
    print(f'Total open positions: {len(open_positions)}')
    
    # Close positions if requested
    if len(sys.argv) > 1 and sys.argv[1] == '--close':
        print()
        print('🔄 CLOSING ALL POSITIONS...')
        print('-'*60)
        for p in open_positions:
            amt = float(p.get('positionAmt', 0))
            side = 'LONG' if amt > 0 else 'SHORT'
            symbol = p['symbol']
            
            # Round quantity appropriately
            if 'BTC' in symbol:
                qty = round(abs(amt), 3)
            elif 'ETH' in symbol:
                qty = round(abs(amt), 2)
            else:
                qty = int(abs(amt))
            
            print(f"  Closing {symbol} {side} {qty}...")
            result = close_position(symbol, side, qty)
            if 'orderId' in result:
                print(f"    ✅ Closed! Order ID: {result['orderId']}")
            else:
                print(f"    ❌ Error: {result.get('msg', result)}")
        
        print()
        print('✅ All positions closed!')
        
        # Show updated balance
        time.sleep(1)
        account = get_account()
        print()
        print('💰 UPDATED BALANCE:')
        print(f"  Wallet Balance: ${float(account.get('totalWalletBalance', 0)):,.2f}")
        print(f"  Available: ${float(account.get('availableBalance', 0)):,.2f}")

if __name__ == '__main__':
    main()
