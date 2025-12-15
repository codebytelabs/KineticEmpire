"""Data Hub for Kinetic Empire v3.0.

Central data management with real-time feeds and shared state.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field

from src.kinetic_empire.v3.core.models import OHLCV, Ticker, Position

logger = logging.getLogger(__name__)


@dataclass
class AccountState:
    """Current account state."""
    balance: float = 0.0
    equity: float = 0.0
    margin_used: float = 0.0
    margin_total: float = 0.0
    unrealized_pnl: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


class DataHub:
    """Central data management with real-time feeds and shared state.
    
    Features:
    - WebSocket price feeds
    - OHLCV data caching
    - Position state tracking
    - Account balance management
    """

    def __init__(self, cache_ttl_seconds: int = 60):
        """Initialize data hub.
        
        Args:
            cache_ttl_seconds: Time-to-live for cached data
        """
        self.cache_ttl = cache_ttl_seconds
        
        # Price cache: symbol -> (price, timestamp)
        self._price_cache: Dict[str, tuple] = {}
        
        # OHLCV cache: (symbol, timeframe) -> (data, timestamp)
        self._ohlcv_cache: Dict[tuple, tuple] = {}
        
        # Ticker cache: symbol -> (ticker, timestamp)
        self._ticker_cache: Dict[str, tuple] = {}
        
        # Account state
        self._account: AccountState = AccountState()
        
        # Positions (managed by PositionManager, but accessible here)
        self._positions: Dict[str, Position] = {}
        
        # WebSocket state
        self._ws_connected: bool = False
        self._ws_subscriptions: set = set()
        
        # Callbacks for price updates
        self._price_callbacks: List[Callable] = []

    # ==================== Price Data ====================

    def get_price(self, symbol: str) -> Optional[float]:
        """Get cached price for symbol."""
        if symbol in self._price_cache:
            price, timestamp = self._price_cache[symbol]
            if self._is_cache_valid(timestamp):
                return price
        return None

    def update_price(self, symbol: str, price: float) -> None:
        """Update price cache and notify callbacks."""
        self._price_cache[symbol] = (price, datetime.now())
        
        # Notify callbacks
        for callback in self._price_callbacks:
            try:
                callback(symbol, price)
            except Exception as e:
                logger.error(f"Price callback error: {e}")

    def get_all_prices(self) -> Dict[str, float]:
        """Get all cached prices."""
        prices = {}
        for symbol, (price, timestamp) in self._price_cache.items():
            if self._is_cache_valid(timestamp):
                prices[symbol] = price
        return prices

    def register_price_callback(self, callback: Callable) -> None:
        """Register callback for price updates."""
        self._price_callbacks.append(callback)

    # ==================== OHLCV Data ====================

    def get_ohlcv(self, symbol: str, timeframe: str) -> Optional[List[OHLCV]]:
        """Get cached OHLCV data."""
        key = (symbol, timeframe)
        if key in self._ohlcv_cache:
            data, timestamp = self._ohlcv_cache[key]
            if self._is_cache_valid(timestamp):
                return data
        return None

    def update_ohlcv(self, symbol: str, timeframe: str, data: List[OHLCV]) -> None:
        """Update OHLCV cache."""
        key = (symbol, timeframe)
        self._ohlcv_cache[key] = (data, datetime.now())

    def clear_ohlcv_cache(self, symbol: Optional[str] = None) -> None:
        """Clear OHLCV cache for symbol or all."""
        if symbol:
            keys_to_remove = [k for k in self._ohlcv_cache if k[0] == symbol]
            for key in keys_to_remove:
                del self._ohlcv_cache[key]
        else:
            self._ohlcv_cache.clear()

    # ==================== Ticker Data ====================

    def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Get cached ticker data."""
        if symbol in self._ticker_cache:
            ticker, timestamp = self._ticker_cache[symbol]
            if self._is_cache_valid(timestamp):
                return ticker
        return None

    def update_ticker(self, symbol: str, ticker: Ticker) -> None:
        """Update ticker cache."""
        self._ticker_cache[symbol] = (ticker, datetime.now())
        # Also update price cache
        self.update_price(symbol, ticker.price)

    def get_all_tickers(self) -> List[Ticker]:
        """Get all cached tickers."""
        tickers = []
        for symbol, (ticker, timestamp) in self._ticker_cache.items():
            if self._is_cache_valid(timestamp):
                tickers.append(ticker)
        return tickers

    # ==================== Account State ====================

    def get_account(self) -> AccountState:
        """Get current account state."""
        return self._account

    def update_account(
        self,
        balance: Optional[float] = None,
        equity: Optional[float] = None,
        margin_used: Optional[float] = None,
        margin_total: Optional[float] = None,
        unrealized_pnl: Optional[float] = None,
    ) -> None:
        """Update account state."""
        if balance is not None:
            self._account.balance = balance
        if equity is not None:
            self._account.equity = equity
        if margin_used is not None:
            self._account.margin_used = margin_used
        if margin_total is not None:
            self._account.margin_total = margin_total
        if unrealized_pnl is not None:
            self._account.unrealized_pnl = unrealized_pnl
        self._account.timestamp = datetime.now()

    def sync_account(self, account_data: dict) -> None:
        """Sync account state from exchange data."""
        self.update_account(
            balance=account_data.get("balance", 0.0),
            equity=account_data.get("equity", 0.0),
            margin_used=account_data.get("margin_used", 0.0),
            margin_total=account_data.get("margin_total", 0.0),
            unrealized_pnl=account_data.get("unrealized_pnl", 0.0),
        )
        logger.debug(f"Account synced: equity={self._account.equity:.2f}")

    # ==================== Position State ====================

    def get_positions(self) -> Dict[str, Position]:
        """Get all positions."""
        return self._positions.copy()

    def update_position(self, symbol: str, position: Position) -> None:
        """Update position state."""
        self._positions[symbol] = position

    def remove_position(self, symbol: str) -> Optional[Position]:
        """Remove position."""
        return self._positions.pop(symbol, None)

    def sync_positions(self, positions: Dict[str, Position]) -> None:
        """Sync positions from PositionManager."""
        self._positions = positions.copy()

    # ==================== WebSocket ====================

    async def connect_websocket(self, symbols: List[str]) -> None:
        """Connect to WebSocket and subscribe to symbols.
        
        Note: This is a placeholder - actual implementation would use
        binance-futures-connector or similar library.
        """
        self._ws_subscriptions = set(symbols)
        self._ws_connected = True
        logger.info(f"WebSocket connected, subscribed to {len(symbols)} symbols")

    async def disconnect_websocket(self) -> None:
        """Disconnect WebSocket."""
        self._ws_connected = False
        self._ws_subscriptions.clear()
        logger.info("WebSocket disconnected")

    def is_ws_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self._ws_connected

    # ==================== Utility ====================

    def _is_cache_valid(self, timestamp: datetime) -> bool:
        """Check if cached data is still valid."""
        age = (datetime.now() - timestamp).total_seconds()
        return age < self.cache_ttl

    def clear_all_caches(self) -> None:
        """Clear all caches."""
        self._price_cache.clear()
        self._ohlcv_cache.clear()
        self._ticker_cache.clear()
        logger.debug("All caches cleared")

    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        return {
            "prices": len(self._price_cache),
            "ohlcv": len(self._ohlcv_cache),
            "tickers": len(self._ticker_cache),
            "positions": len(self._positions),
            "ws_connected": self._ws_connected,
            "ws_subscriptions": len(self._ws_subscriptions),
        }
