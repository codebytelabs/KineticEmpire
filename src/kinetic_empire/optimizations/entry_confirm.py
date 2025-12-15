"""Entry Confirmation Manager.

Implements entry confirmation delay to avoid chasing price spikes.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional, Tuple

from .config import EntryConfirmConfig


logger = logging.getLogger(__name__)


@dataclass
class PendingEntry:
    """A pending entry awaiting confirmation."""
    symbol: str
    direction: str  # "long" or "short"
    signal_price: float
    timestamp: datetime
    candles_waited: int = 0


class EntryConfirmationManager:
    """Manages entry confirmation delays.
    
    Entry confirmation process:
    1. Signal generated → create pending entry
    2. Wait 1 candle
    3. If price moved > 0.3% against signal → cancel
    4. If confirmation passes → execute entry
    """
    
    def __init__(self, config: Optional[EntryConfirmConfig] = None):
        """Initialize entry confirmation manager.
        
        Args:
            config: Entry confirmation configuration. Uses defaults if None.
        """
        self.config = config or EntryConfirmConfig()
        self._pending: Dict[str, PendingEntry] = {}
    
    def create_pending(
        self,
        symbol: str,
        direction: str,
        price: float,
        timestamp: Optional[datetime] = None
    ) -> PendingEntry:
        """Create a pending entry for confirmation.
        
        Args:
            symbol: Trading symbol
            direction: Trade direction ("long" or "short")
            price: Signal price
            timestamp: Signal timestamp (defaults to now)
            
        Returns:
            Created PendingEntry
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        entry = PendingEntry(
            symbol=symbol,
            direction=direction.lower(),
            signal_price=price,
            timestamp=timestamp,
            candles_waited=0
        )
        
        self._pending[symbol] = entry
        logger.info(f"Created pending entry for {symbol} at {price}")
        
        return entry
    
    def check_confirmation(
        self,
        symbol: str,
        current_price: float,
        candles_elapsed: int = 1
    ) -> Tuple[bool, str]:
        """Check if pending entry should be executed or cancelled.
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            candles_elapsed: Number of candles since signal
            
        Returns:
            Tuple of (should_execute, reason)
        """
        if symbol not in self._pending:
            return (False, "No pending entry")
        
        entry = self._pending[symbol]
        entry.candles_waited = candles_elapsed
        
        # Check for adverse price movement
        if entry.direction == "long":
            price_change = (current_price - entry.signal_price) / entry.signal_price
            adverse = price_change < -self.config.adverse_threshold_pct
        else:  # short
            price_change = (entry.signal_price - current_price) / entry.signal_price
            adverse = price_change < -self.config.adverse_threshold_pct
        
        if adverse:
            # Cancel entry
            del self._pending[symbol]
            reason = (
                f"Entry cancelled: price moved {abs(price_change)*100:.2f}% "
                f"against {entry.direction} signal"
            )
            logger.info(reason)
            return (False, reason)
        
        # Check if confirmation period complete
        if candles_elapsed >= self.config.confirmation_candles:
            # Execute entry
            del self._pending[symbol]
            reason = f"Entry confirmed after {candles_elapsed} candle(s)"
            logger.info(f"{symbol}: {reason}")
            return (True, reason)
        
        # Still waiting
        return (False, f"Waiting for confirmation ({candles_elapsed}/{self.config.confirmation_candles})")
    
    def cancel_pending(self, symbol: str) -> bool:
        """Cancel a pending entry.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            True if entry was cancelled
        """
        if symbol in self._pending:
            del self._pending[symbol]
            logger.info(f"Cancelled pending entry for {symbol}")
            return True
        return False
    
    def get_pending(self, symbol: str) -> Optional[PendingEntry]:
        """Get pending entry for symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            PendingEntry or None
        """
        return self._pending.get(symbol)
    
    def has_pending(self, symbol: str) -> bool:
        """Check if symbol has pending entry.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            True if pending entry exists
        """
        return symbol in self._pending
    
    def get_all_pending(self) -> Dict[str, PendingEntry]:
        """Get all pending entries.
        
        Returns:
            Dictionary of symbol -> PendingEntry
        """
        return dict(self._pending)
    
    def cleanup_stale(
        self,
        max_candles: int = 5,
        current_time: Optional[datetime] = None
    ) -> int:
        """Remove stale pending entries.
        
        Args:
            max_candles: Maximum candles to wait before cleanup
            current_time: Current timestamp
            
        Returns:
            Number of entries removed
        """
        stale = [
            symbol for symbol, entry in self._pending.items()
            if entry.candles_waited >= max_candles
        ]
        
        for symbol in stale:
            del self._pending[symbol]
            logger.info(f"Cleaned up stale pending entry for {symbol}")
        
        return len(stale)
