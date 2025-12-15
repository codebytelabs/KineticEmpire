"""Blacklist Manager for Signal Quality Gate.

Manages symbol blacklisting after consecutive losses.

Enhanced with DynamicBlacklistManager for loss-severity-based durations.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .config import QualityGateConfig
from kinetic_empire.optimizations import DynamicBlacklistManager as DynamicBL
from kinetic_empire.optimizations.config import BlacklistDurationConfig


logger = logging.getLogger(__name__)


class BlacklistManager:
    """Manages symbol blacklisting after consecutive stop-losses.
    
    Tracks losses per symbol and blacklists symbols that have
    3+ consecutive stop-losses within 1 hour.
    
    Enhanced with dynamic blacklist durations based on loss severity:
    - < 1% loss: 15 minutes
    - 1-2% loss: 30 minutes
    - > 2% loss: 60 minutes
    """
    
    def __init__(self, config: QualityGateConfig, use_dynamic: bool = True):
        """Initialize with configuration.
        
        Args:
            config: Quality gate configuration
            use_dynamic: Use dynamic loss-severity-based durations
        """
        self.config = config
        self._blacklist: Dict[str, datetime] = {}  # symbol -> blacklist_expiry
        self._loss_history: Dict[str, List[datetime]] = {}  # symbol -> list of loss timestamps
        
        # Initialize dynamic blacklist manager
        self._use_dynamic = use_dynamic
        if use_dynamic:
            self._dynamic_bl = DynamicBL()
        else:
            self._dynamic_bl = None
    
    def record_loss(
        self,
        symbol: str,
        timestamp: datetime = None,
        loss_pct: Optional[float] = None
    ) -> bool:
        """Record a stop-loss for a symbol.
        
        Args:
            symbol: Trading symbol
            timestamp: When the loss occurred (defaults to now)
            loss_pct: Loss percentage as decimal (for dynamic duration)
            
        Returns:
            True if symbol was blacklisted as a result
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # Initialize loss history for symbol if needed
        if symbol not in self._loss_history:
            self._loss_history[symbol] = []
        
        # Add this loss
        self._loss_history[symbol].append(timestamp)
        
        # Clean up old losses outside the window
        window_start = timestamp - timedelta(minutes=self.config.loss_window_minutes)
        self._loss_history[symbol] = [
            t for t in self._loss_history[symbol] if t >= window_start
        ]
        
        # Check if we should blacklist
        if len(self._loss_history[symbol]) >= self.config.max_consecutive_losses:
            # Use dynamic blacklist if enabled and loss_pct provided
            if self._dynamic_bl is not None and loss_pct is not None:
                self._dynamic_bl.record_loss(symbol, loss_pct, timestamp)
            else:
                self._blacklist_symbol(symbol, timestamp)
            return True
        
        return False
    
    def _blacklist_symbol(self, symbol: str, timestamp: datetime) -> None:
        """Add symbol to blacklist.
        
        Args:
            symbol: Trading symbol
            timestamp: Current timestamp
        """
        expiry = timestamp + timedelta(minutes=self.config.blacklist_duration_minutes)
        self._blacklist[symbol] = expiry
        logger.warning(
            f"Symbol {symbol} blacklisted until {expiry} "
            f"({self.config.max_consecutive_losses} losses in "
            f"{self.config.loss_window_minutes} minutes)"
        )
        
        # Clear loss history after blacklisting
        self._loss_history[symbol] = []
    
    def is_blacklisted(self, symbol: str, current_time: datetime = None) -> bool:
        """Check if symbol is currently blacklisted.
        
        Args:
            symbol: Trading symbol
            current_time: Current timestamp (defaults to now)
            
        Returns:
            True if symbol is blacklisted
        """
        if current_time is None:
            current_time = datetime.now()
        
        # Check dynamic blacklist first
        if self._dynamic_bl is not None:
            if self._dynamic_bl.is_blacklisted(symbol, current_time):
                return True
        
        # Fall back to legacy blacklist
        if symbol not in self._blacklist:
            return False
        
        expiry = self._blacklist[symbol]
        if current_time >= expiry:
            # Blacklist expired, remove it
            del self._blacklist[symbol]
            logger.info(f"Symbol {symbol} blacklist expired, resuming scanning")
            return False
        
        return True
    
    def cleanup_expired(self, current_time: datetime = None) -> int:
        """Remove expired blacklist entries.
        
        Args:
            current_time: Current timestamp (defaults to now)
            
        Returns:
            Number of entries removed
        """
        if current_time is None:
            current_time = datetime.now()
        
        expired = [
            symbol for symbol, expiry in self._blacklist.items()
            if current_time >= expiry
        ]
        
        for symbol in expired:
            del self._blacklist[symbol]
            logger.info(f"Cleaned up expired blacklist for {symbol}")
        
        return len(expired)
    
    def get_blacklisted_symbols(self) -> List[str]:
        """Get list of currently blacklisted symbols.
        
        Returns:
            List of blacklisted symbol names
        """
        return list(self._blacklist.keys())
    
    def get_loss_count(self, symbol: str) -> int:
        """Get current loss count for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Number of losses in the current window
        """
        return len(self._loss_history.get(symbol, []))
