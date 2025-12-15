"""Wave Rider Risk Management Components.

Implements:
- Circuit Breaker: Halts trading when daily loss > 3%
- Blacklist Manager: Blacklists symbols after 2 consecutive losses
- Position Limit: Enforces max 5 open positions
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Set, Optional
from .models import WaveRiderConfig


@dataclass
class CircuitBreakerState:
    """State of the circuit breaker."""
    is_active: bool = False
    trigger_time: Optional[datetime] = None
    daily_loss_pct: float = 0.0
    starting_balance: float = 0.0
    realized_pnl: float = 0.0


class WaveRiderCircuitBreaker:
    """Circuit breaker that halts trading on excessive daily loss.
    
    Property 15: Circuit Breaker Activation
    New trades SHALL be halted when daily_realized_loss > 3% of starting_balance.
    """
    
    def __init__(self, config: Optional[WaveRiderConfig] = None):
        """Initialize the circuit breaker.
        
        Args:
            config: Wave Rider configuration
        """
        self.config = config or WaveRiderConfig()
        self.daily_loss_limit = self.config.daily_loss_limit
        self._state = CircuitBreakerState()
        self._last_reset_date: Optional[datetime] = None
    
    def initialize(self, starting_balance: float) -> None:
        """Initialize with starting balance for the day.
        
        Args:
            starting_balance: Account balance at start of day
        """
        self._state.starting_balance = starting_balance
        self._state.realized_pnl = 0.0
        self._state.is_active = False
        self._state.trigger_time = None
        self._last_reset_date = datetime.now().date()
    
    def record_pnl(self, pnl: float) -> bool:
        """Record realized PnL and check circuit breaker.
        
        Args:
            pnl: Realized PnL (positive or negative)
        
        Returns:
            True if circuit breaker was triggered
        """
        # Auto-reset on new day
        today = datetime.now().date()
        if self._last_reset_date and self._last_reset_date != today:
            self._state.realized_pnl = 0.0
            self._state.is_active = False
            self._last_reset_date = today
        
        self._state.realized_pnl += pnl
        
        # Calculate loss percentage
        if self._state.starting_balance > 0:
            self._state.daily_loss_pct = -self._state.realized_pnl / self._state.starting_balance
        
        # Check if should trigger
        if self._state.daily_loss_pct > self.daily_loss_limit:
            self._state.is_active = True
            self._state.trigger_time = datetime.now()
            return True
        
        return False
    
    def can_trade(self) -> bool:
        """Check if trading is allowed.
        
        Returns:
            True if trading is allowed
        """
        return not self._state.is_active
    
    def get_state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        return self._state
    
    def check_would_trigger(self, loss_pct: float) -> bool:
        """Check if a given loss percentage would trigger the breaker.
        
        For testing Property 15.
        """
        return loss_pct > self.daily_loss_limit


@dataclass
class BlacklistEntry:
    """Entry in the blacklist."""
    symbol: str
    consecutive_losses: int
    blacklist_time: datetime
    expiry_time: datetime


class WaveRiderBlacklist:
    """Manages symbol blacklist after consecutive losses.
    
    Property 16: Blacklist After Losses
    Symbol SHALL be blacklisted for 30 minutes after 2 consecutive losses.
    """
    
    def __init__(self, config: Optional[WaveRiderConfig] = None):
        """Initialize the blacklist manager.
        
        Args:
            config: Wave Rider configuration
        """
        self.config = config or WaveRiderConfig()
        self.max_consecutive_losses = self.config.max_consecutive_losses
        self.blacklist_duration = timedelta(minutes=self.config.blacklist_duration_minutes)
        
        self._loss_counts: Dict[str, int] = {}
        self._blacklist: Dict[str, BlacklistEntry] = {}
    
    def record_loss(self, symbol: str) -> bool:
        """Record a loss for a symbol.
        
        Args:
            symbol: Trading pair symbol
        
        Returns:
            True if symbol was blacklisted
        """
        # Increment loss count
        self._loss_counts[symbol] = self._loss_counts.get(symbol, 0) + 1
        
        # Check if should blacklist
        if self._loss_counts[symbol] >= self.max_consecutive_losses:
            now = datetime.now()
            self._blacklist[symbol] = BlacklistEntry(
                symbol=symbol,
                consecutive_losses=self._loss_counts[symbol],
                blacklist_time=now,
                expiry_time=now + self.blacklist_duration,
            )
            return True
        
        return False
    
    def record_win(self, symbol: str) -> None:
        """Record a win for a symbol (resets loss count).
        
        Args:
            symbol: Trading pair symbol
        """
        self._loss_counts[symbol] = 0
    
    def is_blacklisted(self, symbol: str) -> bool:
        """Check if a symbol is currently blacklisted.
        
        Args:
            symbol: Trading pair symbol
        
        Returns:
            True if blacklisted
        """
        if symbol not in self._blacklist:
            return False
        
        entry = self._blacklist[symbol]
        now = datetime.now()
        
        # Check if expired
        if now >= entry.expiry_time:
            del self._blacklist[symbol]
            self._loss_counts[symbol] = 0
            return False
        
        return True
    
    def get_remaining_time(self, symbol: str) -> Optional[timedelta]:
        """Get remaining blacklist time for a symbol.
        
        Args:
            symbol: Trading pair symbol
        
        Returns:
            Remaining time or None if not blacklisted
        """
        if symbol not in self._blacklist:
            return None
        
        entry = self._blacklist[symbol]
        remaining = entry.expiry_time - datetime.now()
        
        if remaining.total_seconds() <= 0:
            return None
        
        return remaining
    
    def clear(self) -> None:
        """Clear all blacklist entries."""
        self._blacklist.clear()
        self._loss_counts.clear()
    
    def should_blacklist(self, consecutive_losses: int) -> bool:
        """Check if given loss count should trigger blacklist.
        
        For testing Property 16.
        """
        return consecutive_losses >= self.max_consecutive_losses


class WaveRiderPositionLimit:
    """Enforces maximum position limit.
    
    Property 17: Position Limit Enforcement
    New position opening SHALL be rejected when open_positions >= 5.
    """
    
    def __init__(self, config: Optional[WaveRiderConfig] = None):
        """Initialize the position limit enforcer.
        
        Args:
            config: Wave Rider configuration
        """
        self.config = config or WaveRiderConfig()
        self.max_positions = self.config.max_positions
        self._open_positions: Set[str] = set()
    
    def add_position(self, symbol: str) -> bool:
        """Add a position.
        
        Args:
            symbol: Trading pair symbol
        
        Returns:
            True if position was added, False if at limit
        """
        if len(self._open_positions) >= self.max_positions:
            return False
        
        self._open_positions.add(symbol)
        return True
    
    def remove_position(self, symbol: str) -> None:
        """Remove a position.
        
        Args:
            symbol: Trading pair symbol
        """
        self._open_positions.discard(symbol)
    
    def can_open_position(self) -> bool:
        """Check if a new position can be opened.
        
        Returns:
            True if under limit
        """
        return len(self._open_positions) < self.max_positions
    
    def get_open_count(self) -> int:
        """Get number of open positions."""
        return len(self._open_positions)
    
    def get_open_symbols(self) -> Set[str]:
        """Get set of open position symbols."""
        return self._open_positions.copy()
    
    def clear(self) -> None:
        """Clear all positions."""
        self._open_positions.clear()
    
    def would_exceed_limit(self, current_count: int) -> bool:
        """Check if current count would exceed limit.
        
        For testing Property 17.
        """
        return current_count >= self.max_positions
