"""Binance Futures Demo API Client.

Provides interface for futures trading with leverage, long/short positions,
and grid trading capabilities.
"""
import hashlib
import hmac
import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Optional
from urllib.parse import urlencode

import requests

logger = logging.getLogger(__name__)


@dataclass
class FuturesPosition:
    """Represents an open futures position."""
    symbol: str
    side: str  # LONG or SHORT
    entry_price: float
    mark_price: float
    quantity: float
    unrealized_pnl: float
    leverage: int
    liquidation_price: float


@dataclass
class FuturesOrder:
    """Represents a futures order."""
    order_id: str
    symbol: str
    side: str  # BUY or SELL
    position_side: str  # LONG or SHORT
    order_type: str  # LIMIT or MARKET
    price: float
    quantity: float
    status: str
    timestamp: int


class BinanceFuturesClient:
    """Client for Binance Futures Demo Trading API."""
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret
        
        if testnet:
            self.base_url = "https://testnet.binancefuture.com"
        else:
            self.base_url = "https://fapi.binance.com"
        
        self.public_url = "https://fapi.binance.com"  # Public data
        
    def _sign(self, params: dict) -> str:
        """Sign request parameters."""
        query = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode(),
            query.encode(),
            hashlib.sha256
        ).hexdigest()
        return query + '&signature=' + signature
    
    def _headers(self) -> dict:
        return {'X-MBX-APIKEY': self.api_key}
    
    def _get_price_precision(self, symbol: str) -> int:
        """Get price precision for a symbol."""
        # Common precision values for major pairs
        precision_map = {
            'BTCUSDT': 1, 'ETHUSDT': 2, 'BNBUSDT': 2, 'SOLUSDT': 3,
            'XRPUSDT': 4, 'ADAUSDT': 5, 'DOGEUSDT': 5, 'DOTUSDT': 3,
            'AVAXUSDT': 3, 'LINKUSDT': 3, 'MATICUSDT': 4, 'LTCUSDT': 2,
            'ATOMUSDT': 3, 'UNIUSDT': 3, 'APTUSDT': 3, 'ARBUSDT': 4,
            'OPUSDT': 4, 'NEARUSDT': 3, 'FILUSDT': 3, 'INJUSDT': 3,
        }
        return precision_map.get(symbol, 4)  # Default to 4 decimal places
    
    def _get_quantity_precision(self, symbol: str) -> int:
        """Get quantity precision for a symbol."""
        # Common quantity precision values
        precision_map = {
            'BTCUSDT': 3, 'ETHUSDT': 3, 'BNBUSDT': 2, 'SOLUSDT': 1,
            'XRPUSDT': 1, 'ADAUSDT': 0, 'DOGEUSDT': 0, 'DOTUSDT': 1,
            'AVAXUSDT': 1, 'LINKUSDT': 2, 'MATICUSDT': 0, 'LTCUSDT': 3,
            'ATOMUSDT': 2, 'UNIUSDT': 1, 'APTUSDT': 1, 'ARBUSDT': 1,
            'OPUSDT': 1, 'NEARUSDT': 1, 'FILUSDT': 1, 'INJUSDT': 1,
        }
        return precision_map.get(symbol, 3)  # Default to 3 decimal places
    
    def _request(self, method: str, endpoint: str, params: dict = None, 
                 signed: bool = True, use_public: bool = False,
                 max_retries: int = 3) -> dict:
        """Make API request with retry logic for rate limiting.
        
        Handles 418 (I'm a teapot) and 429 (Too Many Requests) errors
        with exponential backoff.
        """
        params = params or {}
        
        for attempt in range(max_retries + 1):
            try:
                # Regenerate timestamp for each attempt (important for signed requests)
                request_params = params.copy()
                if signed:
                    request_params['timestamp'] = int(time.time() * 1000)
                    request_params['recvWindow'] = 10000
                    query = self._sign(request_params)
                else:
                    query = urlencode(request_params) if request_params else ""
                
                base = self.public_url if use_public else self.base_url
                url = f"{base}{endpoint}?{query}" if query else f"{base}{endpoint}"
                
                if method == 'GET':
                    response = requests.get(url, headers=self._headers())
                elif method == 'POST':
                    response = requests.post(url, headers=self._headers())
                elif method == 'DELETE':
                    response = requests.delete(url, headers=self._headers())
                else:
                    raise ValueError(f"Unknown method: {method}")
                
                # Check for rate limiting (418 or 429)
                if response.status_code in (418, 429):
                    if attempt < max_retries:
                        # Exponential backoff: 1s, 2s, 4s (capped at 10s max)
                        wait_time = min(2 ** attempt, 10)
                        # Only log on first retry to reduce noise
                        if attempt == 0:
                            logger.debug(f"Rate limited ({response.status_code}), retrying...")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.warning(f"Rate limit exceeded after {max_retries} retries")
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.HTTPError as e:
                # Re-raise non-rate-limit errors immediately
                if hasattr(e, 'response') and e.response is not None:
                    if e.response.status_code not in (418, 429):
                        raise
                raise
        
        # Should not reach here, but just in case
        raise requests.exceptions.HTTPError(f"Request failed after {max_retries} retries")
    
    # Account Methods
    def get_account(self) -> dict:
        """Get futures account information."""
        return self._request('GET', '/fapi/v2/account')
    
    def get_balance(self) -> Dict[str, float]:
        """Get account balances."""
        data = self.get_account()
        balances = {}
        for asset in data.get('assets', []):
            balance = float(asset.get('walletBalance', 0))
            if balance > 0:
                balances[asset['asset']] = balance
        return balances
    
    def get_usdt_balance(self) -> float:
        """Get available USDT balance (free, not in positions)."""
        data = self.get_account()
        return float(data.get('availableBalance', 0))
    
    def get_total_wallet_balance(self) -> float:
        """Get total wallet balance (including margin in positions)."""
        data = self.get_account()
        return float(data.get('totalWalletBalance', 0))
    
    def get_total_margin_balance(self) -> float:
        """Get total margin balance (wallet + unrealized PnL)."""
        data = self.get_account()
        return float(data.get('totalMarginBalance', 0))
    
    # Position Methods
    def get_positions(self) -> List[FuturesPosition]:
        """Get all open positions."""
        data = self._request('GET', '/fapi/v2/positionRisk')
        positions = []
        for p in data:
            qty = float(p.get('positionAmt', 0))
            if qty != 0:
                positions.append(FuturesPosition(
                    symbol=p['symbol'],
                    side='LONG' if qty > 0 else 'SHORT',
                    entry_price=float(p.get('entryPrice', 0)),
                    mark_price=float(p.get('markPrice', 0)),
                    quantity=abs(qty),
                    unrealized_pnl=float(p.get('unRealizedProfit', 0)),
                    leverage=int(p.get('leverage', 1)),
                    liquidation_price=float(p.get('liquidationPrice', 0))
                ))
        return positions
    
    def get_position(self, symbol: str) -> Optional[FuturesPosition]:
        """Get position for specific symbol."""
        positions = self.get_positions()
        for p in positions:
            if p.symbol == symbol:
                return p
        return None
    
    # Leverage Methods
    def set_leverage(self, symbol: str, leverage: int) -> dict:
        """Set leverage for a symbol."""
        return self._request('POST', '/fapi/v1/leverage', {
            'symbol': symbol,
            'leverage': leverage
        })
    
    def set_margin_type(self, symbol: str, margin_type: str = 'CROSSED') -> dict:
        """Set margin type (ISOLATED or CROSSED)."""
        try:
            return self._request('POST', '/fapi/v1/marginType', {
                'symbol': symbol,
                'marginType': margin_type
            })
        except requests.exceptions.HTTPError as e:
            # Ignore if already set
            if 'No need to change margin type' in str(e):
                return {'msg': 'Already set'}
            raise
    
    # Order Methods
    def place_order(self, symbol: str, side: str, order_type: str,
                    quantity: float, price: float = None,
                    position_side: str = 'BOTH', 
                    reduce_only: bool = False) -> dict:
        """Place a futures order.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            side: 'BUY' or 'SELL'
            order_type: 'LIMIT' or 'MARKET'
            quantity: Order quantity
            price: Limit price (required for LIMIT orders)
            position_side: 'LONG', 'SHORT', or 'BOTH' (for one-way mode)
            reduce_only: If True, only reduce position
        """
        # Get quantity precision for symbol
        qty_precision = self._get_quantity_precision(symbol)
        
        params = {
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'quantity': f"{quantity:.{qty_precision}f}",
            'positionSide': position_side,
        }
        
        if reduce_only:
            params['reduceOnly'] = 'true'
        
        if order_type == 'LIMIT':
            # Format price with appropriate precision based on symbol
            price_precision = self._get_price_precision(symbol)
            params['price'] = f"{price:.{price_precision}f}"
            params['timeInForce'] = 'GTC'
        
        return self._request('POST', '/fapi/v1/order', params)
    
    def place_market_order(self, symbol: str, side: str, quantity: float,
                           position_side: str = 'BOTH', reduce_only: bool = False) -> dict:
        """Place market order."""
        return self.place_order(symbol, side, 'MARKET', quantity, 
                               position_side=position_side, reduce_only=reduce_only)
    
    def place_limit_order(self, symbol: str, side: str, quantity: float,
                          price: float, position_side: str = 'BOTH') -> dict:
        """Place limit order."""
        return self.place_order(symbol, side, 'LIMIT', quantity, price,
                               position_side=position_side)
    
    def cancel_order(self, symbol: str, order_id: str) -> dict:
        """Cancel an order."""
        return self._request('DELETE', '/fapi/v1/order', {
            'symbol': symbol,
            'orderId': order_id
        })
    
    def cancel_all_orders(self, symbol: str) -> dict:
        """Cancel all open orders for a symbol."""
        return self._request('DELETE', '/fapi/v1/allOpenOrders', {
            'symbol': symbol
        })
    
    def get_open_orders(self, symbol: str = None) -> List[dict]:
        """Get all open orders."""
        params = {}
        if symbol:
            params['symbol'] = symbol
        return self._request('GET', '/fapi/v1/openOrders', params)
    
    # Market Data Methods
    def get_ticker(self, symbol: str) -> dict:
        """Get ticker for a symbol."""
        data = self._request('GET', '/fapi/v1/ticker/24hr', 
                            {'symbol': symbol}, signed=False, use_public=True)
        return {
            'symbol': symbol,
            'last': float(data.get('lastPrice', 0)),
            'bid': float(data.get('bidPrice', data.get('lastPrice', 0))),
            'ask': float(data.get('askPrice', data.get('lastPrice', 0))),
            'high': float(data.get('highPrice', 0)),
            'low': float(data.get('lowPrice', 0)),
            'volume': float(data.get('volume', 0)),
            'change_pct': float(data.get('priceChangePercent', 0))
        }
    
    def get_klines(self, symbol: str, interval: str = '5m', 
                   limit: int = 100) -> List[list]:
        """Get candlestick data."""
        data = self._request('GET', '/fapi/v1/klines', {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }, signed=False, use_public=True)
        
        return [[
            int(k[0]),      # timestamp
            float(k[1]),    # open
            float(k[2]),    # high
            float(k[3]),    # low
            float(k[4]),    # close
            float(k[5])     # volume
        ] for k in data]
    
    def get_mark_price(self, symbol: str) -> float:
        """Get mark price for a symbol."""
        data = self._request('GET', '/fapi/v1/premiumIndex',
                            {'symbol': symbol}, signed=False, use_public=True)
        return float(data['markPrice'])
    
    def get_funding_rate(self, symbol: str) -> float:
        """Get current funding rate."""
        data = self._request('GET', '/fapi/v1/premiumIndex',
                            {'symbol': symbol}, signed=False, use_public=True)
        return float(data['lastFundingRate'])
