"""Exposure Tracker - Tracks total portfolio exposure.

Implements portfolio exposure management per aggressive-capital-deployment spec:
- Maximum 90% total portfolio exposure (aggressive capital utilization)
- Track positions and recalculate on open/close
"""

import logging
from typing import Dict


logger = logging.getLogger(__name__)


class ExposureTracker:
    """Tracks total portfolio exposure across all positions.
    
    Per aggressive-capital-deployment Requirements 1.1-1.4:
    - Total exposure capped at 90% (aggressive)
    - Recalculate on position open/close
    """
    
    DEFAULT_MAX_EXPOSURE = 0.90  # 90% - aggressive capital utilization
    
    def __init__(self, max_exposure_pct: float = DEFAULT_MAX_EXPOSURE):
        """Initialize exposure tracker.
        
        Args:
            max_exposure_pct: Maximum allowed exposure (default 0.45 = 45%)
        """
        self.max_exposure_pct = max_exposure_pct
        self.positions: Dict[str, float] = {}  # symbol -> size_pct
    
    def get_current_exposure(self) -> float:
        """Get total exposure as percentage of portfolio.
        
        Returns:
            Total exposure as decimal (0.0-1.0)
        """
        return sum(self.positions.values())
    
    def get_available_exposure(self) -> float:
        """Get remaining exposure available for new positions.
        
        Returns:
            Available exposure as decimal
        """
        return max(0.0, self.max_exposure_pct - self.get_current_exposure())
    
    def can_open_position(self, size_pct: float) -> bool:
        """Check if new position would exceed exposure limit.
        
        Args:
            size_pct: Proposed position size as decimal
            
        Returns:
            True if position can be opened
        """
        return self.get_current_exposure() + size_pct <= self.max_exposure_pct
    
    def add_position(self, symbol: str, size_pct: float) -> bool:
        """Record new position.
        
        Args:
            symbol: Trading symbol
            size_pct: Position size as decimal
            
        Returns:
            True if position was added, False if would exceed limit
        """
        if not self.can_open_position(size_pct):
            logger.warning(
                f"Cannot add position {symbol}: would exceed exposure limit "
                f"({self.get_current_exposure():.1%} + {size_pct:.1%} > {self.max_exposure_pct:.1%})"
            )
            return False
        
        self.positions[symbol] = size_pct
        logger.info(
            f"Position added: {symbol} @ {size_pct:.1%}, "
            f"total exposure: {self.get_current_exposure():.1%}"
        )
        return True
    
    def remove_position(self, symbol: str) -> None:
        """Remove closed position.
        
        Args:
            symbol: Trading symbol
        """
        if symbol in self.positions:
            removed_size = self.positions.pop(symbol)
            logger.info(
                f"Position removed: {symbol} @ {removed_size:.1%}, "
                f"total exposure: {self.get_current_exposure():.1%}"
            )
    
    def update_position(self, symbol: str, new_size_pct: float) -> None:
        """Update existing position size (e.g., after partial close).
        
        Args:
            symbol: Trading symbol
            new_size_pct: New position size as decimal
        """
        if symbol in self.positions:
            old_size = self.positions[symbol]
            self.positions[symbol] = new_size_pct
            logger.debug(
                f"Position updated: {symbol} {old_size:.1%} → {new_size_pct:.1%}"
            )
    
    def clear(self) -> None:
        """Clear all tracked positions."""
        self.positions.clear()
        logger.info("All positions cleared from exposure tracker")
    
    def sync_with_positions(self, active_symbols: set, total_wallet: float, positions_data: list) -> None:
        """Sync tracker with actual exchange positions.
        
        This handles cases where positions are closed externally (manually or by exchange).
        
        Args:
            active_symbols: Set of symbols with active positions
            total_wallet: Total wallet balance for calculating exposure %
            positions_data: List of position objects with symbol, quantity, entry_price, leverage
        """
        # Remove positions that no longer exist
        tracked_symbols = set(self.positions.keys())
        for symbol in tracked_symbols - active_symbols:
            removed_size = self.positions.pop(symbol)
            logger.info(f"Synced: removed {symbol} @ {removed_size:.1%} (position closed externally)")
        
        # Update exposure for existing positions based on actual margin
        if total_wallet > 0:
            for pos in positions_data:
                if pos.symbol in self.positions:
                    # Recalculate actual exposure
                    margin = (pos.quantity * pos.entry_price) / pos.leverage if pos.leverage > 0 else 0
                    actual_exposure = margin / total_wallet
                    if abs(actual_exposure - self.positions[pos.symbol]) > 0.01:  # >1% difference
                        logger.debug(f"Synced: {pos.symbol} exposure {self.positions[pos.symbol]:.1%} → {actual_exposure:.1%}")
                        self.positions[pos.symbol] = actual_exposure
