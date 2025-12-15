"""Exchange client module with rate limiting and order management.

Provides unified interface for exchange operations with built-in
rate limiting, error handling, and FailSafe mode.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Any
from threading import Lock


class OrderType(Enum):
    """Order type enumeration."""
    LIMIT = "limit"
    MARKET = "market"


class OrderSide(Enum):
    """Order side enumeration."""
    BUY = "buy"
    SELL = "sell"


@dataclass
class Order:
    """Order data structure."""
    id: str
    pair: str
    side: OrderSide
    order_type: OrderType
    amount: float
    price: Optional[float]
    timestamp: datetime
    status: str = "open"
    filled: float = 0.0


@dataclass
class ExchangeConfig:
    """Configuration for exchange module."""
    api_key: str = ""
    api_secret: str = ""
    rate_limit_ms: int = 200  # Minimum ms between requests
    entry_timeout_minutes: int = 10
    exit_timeout_minutes: int = 30
    failsafe_threshold_minutes: int = 5


class RateLimiter:
    """Thread-safe rate limiter for API requests."""
    
    def __init__(self, min_interval_ms: int = 200):
        """Initialize rate limiter.
        
        Args:
            min_interval_ms: Minimum milliseconds between requests
        """
        self.min_interval_ms = min_interval_ms
        self._last_request_time: Optional[float] = None
        self._lock = Lock()
    
    def wait(self) -> float:
        """Wait if necessary to respect rate limit.
        
        Returns:
            Actual wait time in milliseconds
        """
        with self._lock:
            current_time = time.time() * 1000  # Convert to ms
            
            if self._last_request_time is None:
                self._last_request_time = current_time
                return 0.0
            
            elapsed = current_time - self._last_request_time
            
            if elapsed < self.min_interval_ms:
                wait_time = self.min_interval_ms - elapsed
                time.sleep(wait_time / 1000)  # Convert to seconds
                self._last_request_time = time.time() * 1000
                return wait_time
            
            self._last_request_time = current_time
            return 0.0
    
    def get_time_since_last_request(self) -> Optional[float]:
        """Get time since last request in milliseconds.
        
        Returns:
            Time in ms or None if no previous request
        """
        if self._last_request_time is None:
            return None
        return (time.time() * 1000) - self._last_request_time


class FailSafeManager:
    """Manages FailSafe mode for exchange errors."""
    
    def __init__(self, threshold_minutes: int = 5):
        """Initialize FailSafe manager.
        
        Args:
            threshold_minutes: Minutes of continuous errors to trigger FailSafe
        """
        self.threshold_minutes = threshold_minutes
        self._first_error_time: Optional[datetime] = None
        self._is_failsafe_active = False
        self._lock = Lock()
    
    def record_error(self, is_5xx: bool = True) -> bool:
        """Record an API error.
        
        Args:
            is_5xx: Whether error is a 5xx server error
            
        Returns:
            True if FailSafe mode is now active
        """
        if not is_5xx:
            return self._is_failsafe_active
        
        with self._lock:
            now = datetime.now()
            
            if self._first_error_time is None:
                self._first_error_time = now
            
            # Check if threshold exceeded
            error_duration = now - self._first_error_time
            if error_duration >= timedelta(minutes=self.threshold_minutes):
                self._is_failsafe_active = True
            
            return self._is_failsafe_active
    
    def record_success(self) -> None:
        """Record a successful API call, resetting error tracking."""
        with self._lock:
            self._first_error_time = None
            # Note: FailSafe stays active until manually reset
    
    def is_active(self) -> bool:
        """Check if FailSafe mode is active.
        
        Returns:
            True if FailSafe mode is active
        """
        return self._is_failsafe_active
    
    def reset(self) -> None:
        """Reset FailSafe mode."""
        with self._lock:
            self._is_failsafe_active = False
            self._first_error_time = None


class ExchangeModule:
    """Exchange integration with rate limiting and error handling.
    
    Provides methods for:
    - Placing limit and market orders
    - Managing stop loss orders
    - Rate-limited API access
    - FailSafe mode for persistent errors
    """
    
    def __init__(self, config: Optional[ExchangeConfig] = None):
        """Initialize exchange module.
        
        Args:
            config: Exchange configuration
        """
        self.config = config or ExchangeConfig()
        self.rate_limiter = RateLimiter(self.config.rate_limit_ms)
        self.failsafe = FailSafeManager(self.config.failsafe_threshold_minutes)
        self._orders: dict[str, Order] = {}
        self._order_counter = 0
        self._lock = Lock()
    
    def _generate_order_id(self) -> str:
        """Generate unique order ID."""
        with self._lock:
            self._order_counter += 1
            return f"order_{self._order_counter}_{int(time.time() * 1000)}"
    
    def get_order_type_for_action(self, action: str) -> OrderType:
        """Get appropriate order type for action.
        
        Entry and exit use limit orders.
        Emergency exit and stop loss use market orders.
        
        Args:
            action: Order action (entry, exit, emergency_exit, stoploss)
            
        Returns:
            Appropriate OrderType
        """
        if action in ("emergency_exit", "stoploss"):
            return OrderType.MARKET
        return OrderType.LIMIT
    
    def place_limit_order(
        self,
        pair: str,
        side: OrderSide,
        amount: float,
        price: float
    ) -> Order:
        """Place a limit order.
        
        Args:
            pair: Trading pair
            side: Buy or sell
            amount: Order amount
            price: Limit price
            
        Returns:
            Created order
        """
        self.rate_limiter.wait()
        
        order = Order(
            id=self._generate_order_id(),
            pair=pair,
            side=side,
            order_type=OrderType.LIMIT,
            amount=amount,
            price=price,
            timestamp=datetime.now()
        )
        
        self._orders[order.id] = order
        return order
    
    def place_market_order(
        self,
        pair: str,
        side: OrderSide,
        amount: float
    ) -> Order:
        """Place a market order.
        
        Args:
            pair: Trading pair
            side: Buy or sell
            amount: Order amount
            
        Returns:
            Created order
        """
        self.rate_limiter.wait()
        
        order = Order(
            id=self._generate_order_id(),
            pair=pair,
            side=side,
            order_type=OrderType.MARKET,
            amount=amount,
            price=None,
            timestamp=datetime.now(),
            status="filled",  # Market orders fill immediately
            filled=amount
        )
        
        self._orders[order.id] = order
        return order
    
    def place_stop_loss_order(
        self,
        pair: str,
        amount: float,
        stop_price: float
    ) -> Order:
        """Place a stop loss order (market type).
        
        Args:
            pair: Trading pair
            amount: Order amount
            stop_price: Stop trigger price
            
        Returns:
            Created order
        """
        self.rate_limiter.wait()
        
        order = Order(
            id=self._generate_order_id(),
            pair=pair,
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            amount=amount,
            price=stop_price,  # Stop price stored here
            timestamp=datetime.now(),
            status="pending"  # Pending until stop triggered
        )
        
        self._orders[order.id] = order
        return order
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order.
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            True if cancelled successfully
        """
        self.rate_limiter.wait()
        
        if order_id in self._orders:
            order = self._orders[order_id]
            if order.status == "open":
                order.status = "cancelled"
                return True
        return False
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID.
        
        Args:
            order_id: Order ID
            
        Returns:
            Order or None if not found
        """
        return self._orders.get(order_id)
    
    def check_order_timeout(self, order: Order) -> bool:
        """Check if order should be cancelled due to timeout.
        
        Entry orders timeout after 10 minutes.
        Exit orders timeout after 30 minutes.
        
        Args:
            order: Order to check
            
        Returns:
            True if order has timed out
        """
        if order.status != "open":
            return False
        
        elapsed = datetime.now() - order.timestamp
        
        if order.side == OrderSide.BUY:
            timeout = timedelta(minutes=self.config.entry_timeout_minutes)
        else:
            timeout = timedelta(minutes=self.config.exit_timeout_minutes)
        
        return elapsed > timeout
    
    def get_timeout_minutes(self, order: Order) -> int:
        """Get timeout duration for order type.
        
        Args:
            order: Order to check
            
        Returns:
            Timeout in minutes
        """
        if order.side == OrderSide.BUY:
            return self.config.entry_timeout_minutes
        return self.config.exit_timeout_minutes
    
    def is_failsafe_active(self) -> bool:
        """Check if FailSafe mode is active.
        
        Returns:
            True if FailSafe mode is active
        """
        return self.failsafe.is_active()
    
    def can_process_signals(self) -> bool:
        """Check if new signals can be processed.
        
        Returns:
            False if FailSafe mode is active
        """
        return not self.failsafe.is_active()
