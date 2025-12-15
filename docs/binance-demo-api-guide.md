# Binance Demo API Integration Guide

## Overview

Kinetic Empire v3.0 uses the Binance Futures Demo (Testnet) API for paper trading. This guide covers the API integration approach since CCXT doesn't natively support Binance's testnet.

## API Endpoints

### Base URLs

```
# Demo/Testnet
REST API: https://testnet.binancefuture.com
WebSocket: wss://stream.binancefuture.com

# Production (Live)
REST API: https://fapi.binance.com
WebSocket: wss://fstream.binance.com
```

## Authentication

### API Key Setup

1. Go to [Binance Futures Testnet](https://testnet.binancefuture.com/)
2. Log in with your Binance account
3. Generate API keys from the API Management section
4. Copy both API Key and Secret

### Request Signing

All authenticated endpoints require HMAC SHA256 signature:

```python
import hmac
import hashlib
import time

def sign_request(params: dict, secret: str) -> str:
    """Sign request parameters with API secret."""
    query_string = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
    signature = hmac.new(
        secret.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature

# Example usage
params = {
    'symbol': 'BTCUSDT',
    'side': 'BUY',
    'type': 'MARKET',
    'quantity': 0.001,
    'timestamp': int(time.time() * 1000),
}
params['signature'] = sign_request(params, API_SECRET)
```

### Headers

```python
headers = {
    'X-MBX-APIKEY': API_KEY,
    'Content-Type': 'application/x-www-form-urlencoded',
}
```

## Key Endpoints

### Account Information

```
GET /fapi/v2/account
```

Response includes:
- `totalWalletBalance`: Total balance
- `availableBalance`: Available for trading
- `totalUnrealizedProfit`: Unrealized P&L
- `positions`: Array of open positions

### Get Positions

```
GET /fapi/v2/positionRisk
```

Returns all positions with:
- `symbol`: Trading pair
- `positionAmt`: Position size (negative = short)
- `entryPrice`: Average entry price
- `markPrice`: Current mark price
- `unRealizedProfit`: Unrealized P&L
- `leverage`: Current leverage

### Place Order

```
POST /fapi/v1/order
```

Parameters:
- `symbol`: Trading pair (e.g., "BTCUSDT")
- `side`: "BUY" or "SELL"
- `type`: "MARKET", "LIMIT", "STOP_MARKET", etc.
- `quantity`: Order size
- `timestamp`: Current timestamp in milliseconds
- `signature`: HMAC SHA256 signature

### Set Leverage

```
POST /fapi/v1/leverage
```

Parameters:
- `symbol`: Trading pair
- `leverage`: 1-125
- `timestamp`: Current timestamp
- `signature`: HMAC SHA256 signature

### Get Klines (OHLCV)

```
GET /fapi/v1/klines
```

Parameters:
- `symbol`: Trading pair
- `interval`: "1m", "5m", "15m", "1h", "4h", "1d"
- `limit`: Number of candles (max 1500)

### Get Ticker

```
GET /fapi/v1/ticker/24hr
```

Returns 24h statistics including:
- `lastPrice`: Current price
- `priceChangePercent`: 24h change %
- `volume`: 24h volume
- `highPrice`: 24h high
- `lowPrice`: 24h low

## WebSocket Streams

### User Data Stream

```python
# Get listen key
POST /fapi/v1/listenKey

# Connect to WebSocket
wss://stream.binancefuture.com/ws/<listenKey>
```

Events:
- `ACCOUNT_UPDATE`: Balance/position changes
- `ORDER_TRADE_UPDATE`: Order fills
- `MARGIN_CALL`: Margin warnings

### Market Data Streams

```python
# Individual symbol ticker
wss://stream.binancefuture.com/ws/btcusdt@ticker

# All tickers
wss://stream.binancefuture.com/ws/!ticker@arr

# Kline/candlestick
wss://stream.binancefuture.com/ws/btcusdt@kline_1m
```

## Implementation in Kinetic Empire

### BinanceFuturesClient

Located at `src/kinetic_empire/futures/client.py`:

```python
class BinanceFuturesClient:
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = (
            "https://testnet.binancefuture.com"
            if testnet
            else "https://fapi.binance.com"
        )
    
    def get_usdt_balance(self) -> float:
        """Get available USDT balance."""
        account = self._request("GET", "/fapi/v2/account")
        for asset in account.get("assets", []):
            if asset["asset"] == "USDT":
                return float(asset["availableBalance"])
        return 0.0
    
    def get_positions(self) -> List[FuturesPosition]:
        """Get all open positions."""
        data = self._request("GET", "/fapi/v2/positionRisk")
        positions = []
        for pos in data:
            if float(pos["positionAmt"]) != 0:
                positions.append(FuturesPosition(
                    symbol=pos["symbol"],
                    side="LONG" if float(pos["positionAmt"]) > 0 else "SHORT",
                    quantity=abs(float(pos["positionAmt"])),
                    entry_price=float(pos["entryPrice"]),
                    mark_price=float(pos["markPrice"]),
                    unrealized_pnl=float(pos["unRealizedProfit"]),
                    leverage=int(pos["leverage"]),
                ))
        return positions
    
    def place_market_order(
        self, symbol: str, side: str, quantity: float
    ) -> dict:
        """Place a market order."""
        params = {
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
            "quantity": quantity,
        }
        return self._request("POST", "/fapi/v1/order", params)
```

## Rate Limits

### REST API
- 1200 requests per minute (weight-based)
- Order endpoints: 10 weight
- Account endpoints: 5 weight
- Market data: 1-5 weight

### WebSocket
- 5 messages per second per connection
- Max 10 connections per IP

## Error Handling

Common error codes:
- `-1000`: Unknown error
- `-1003`: Too many requests
- `-1021`: Timestamp outside recvWindow
- `-2010`: New order rejected
- `-2011`: Cancel order rejected
- `-4003`: Quantity less than minimum

```python
def handle_error(response: dict):
    if "code" in response:
        code = response["code"]
        msg = response.get("msg", "Unknown error")
        
        if code == -1003:
            # Rate limited - wait and retry
            time.sleep(60)
        elif code == -1021:
            # Timestamp issue - sync time
            pass
        elif code == -2010:
            # Order rejected - check balance/limits
            pass
        
        raise BinanceAPIError(code, msg)
```

## Best Practices

1. **Always use testnet first** - Test all strategies on demo before live
2. **Handle rate limits** - Implement exponential backoff
3. **Sync timestamps** - Use server time for signing
4. **Validate orders** - Check min notional, quantity precision
5. **Monitor WebSocket** - Reconnect on disconnect
6. **Log everything** - Keep audit trail of all API calls

## Environment Configuration

```env
# .env file
BINANCE_API_KEY=your_testnet_api_key
BINANCE_API_SECRET=your_testnet_api_secret
BINANCE_TESTNET=true
```

## Testing Connection

```python
# Quick connection test
from src.kinetic_empire.futures.client import BinanceFuturesClient

client = BinanceFuturesClient(
    api_key=os.getenv("BINANCE_API_KEY"),
    api_secret=os.getenv("BINANCE_API_SECRET"),
    testnet=True,
)

# Test connection
balance = client.get_usdt_balance()
print(f"Connected! Balance: ${balance:.2f}")

positions = client.get_positions()
print(f"Open positions: {len(positions)}")
```

## Resources

- [Binance Futures API Documentation](https://binance-docs.github.io/apidocs/futures/en/)
- [Binance Futures Testnet](https://testnet.binancefuture.com/)
- [API Error Codes](https://binance-docs.github.io/apidocs/futures/en/#error-codes)
