"""Entry Confirmer - Implements confirmation delay before entry.

Per profitable-trading-overhaul spec:
- Wait 2 candle closes (30 seconds on 15s timeframe)
- Cancel if price moves > 0.5% against signal
"""

import logging
from datetime import datetime
from typing import Dict, Optional, Tuple

from .models import PendingEntry


logger = logging.getLogger(__name__)


class EntryConfirmer:
    """Implements confirmation delay before trade entry.
    
    Per Requirements 10.1-10.4:
    - Wait for 2 candle closes before execution
    - Cancel if price moves > 0.5% against signal direction
    """
    
    DEFAULT_CONFIRMATION_CANDLES = 2
    DEFAULT_ADVERSE_THRESHOLD = 0.005  # 0.5%
    
    def __init__(self):
        """Initialize entry confirmer."""
        self._pending: Dict[str, PendingEntry] = {}
    
    def create_pending(
        self,
        symbol: str,
        direction: str,
        current_price: float,
        confirmation_candles: int = DEFAULT_CONFIRMATION_CANDLES,
    ) -> PendingEntry:
        """Create a pending entry awaiting confirmation.
        
        Args:
            symbol: Trading symbol
            direction: "LONG" or "SHORT"
            current_price: Price when signal was generated
            confirmation_candles: Number of candles to wait (default 2)
            
        Returns:
            PendingEntry object
        """
        pending = PendingEntry(
            symbol=symbol,
            direction=direction,
            signal_price=current_price,
            signal_time=datetime.now(),
            confirmation_candles=confirmation_candles,
            candles_elapsed=0,
        )
        
        self._pending[symbol] = pending
        logger.info(
            f"{symbol}: Pending entry created - {direction} @ ${current_price:.4f}, "
            f"waiting {confirmation_candles} candles"
        )
        
        return pending
    
    def check_confirmation(
        self,
        symbol: str,
        current_price: float,
        candles_elapsed: int,
        adverse_threshold: float = DEFAULT_ADVERSE_THRESHOLD,
    ) -> Tuple[bool, str]:
        """Check if pending entry should execute or cancel.
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            candles_elapsed: Number of candles since signal
            adverse_threshold: Max adverse movement (default 0.5%)
            
        Returns:
            (should_execute, reason) tuple
        """
        pending = self._pending.get(symbol)
        if pending is None:
            return False, "No pending entry found"
        
        # Update candles elapsed
        pending.candles_elapsed = candles_elapsed
        
        # Calculate price movement
        price_change = (current_price - pending.signal_price) / pending.signal_price
        
        # Check for adverse movement
        if pending.direction.upper() == "LONG":
            # For LONG, adverse is price falling
            if price_change < -adverse_threshold:
                self._cancel_pending(symbol)
                reason = (
                    f"Entry cancelled: price fell {abs(price_change):.2%} "
                    f"against LONG signal (threshold: {adverse_threshold:.2%})"
                )
                logger.info(f"{symbol}: {reason}")
                return False, reason
        else:
            # For SHORT, adverse is price rising
            if price_change > adverse_threshold:
                self._cancel_pending(symbol)
                reason = (
                    f"Entry cancelled: price rose {price_change:.2%} "
                    f"against SHORT signal (threshold: {adverse_threshold:.2%})"
                )
                logger.info(f"{symbol}: {reason}")
                return False, reason
        
        # Check if confirmation period complete
        if candles_elapsed >= pending.confirmation_candles:
            self._cancel_pending(symbol)
            logger.info(
                f"{symbol}: Entry CONFIRMED after {candles_elapsed} candles, "
                f"executing at ${current_price:.4f}"
            )
            return True, "Confirmation complete"
        
        # Still waiting
        remaining = pending.confirmation_candles - candles_elapsed
        return False, f"Waiting for {remaining} more candles"
    
    def _cancel_pending(self, symbol: str) -> None:
        """Remove pending entry."""
        if symbol in self._pending:
            del self._pending[symbol]
    
    def get_pending(self, symbol: str) -> Optional[PendingEntry]:
        """Get pending entry for symbol."""
        return self._pending.get(symbol)
    
    def has_pending(self, symbol: str) -> bool:
        """Check if symbol has pending entry."""
        return symbol in self._pending
    
    def cancel_all(self) -> int:
        """Cancel all pending entries.
        
        Returns:
            Number of entries cancelled
        """
        count = len(self._pending)
        self._pending.clear()
        return count
