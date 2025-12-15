"""Dynamic Blacklist Manager.

Implements loss-severity-based blacklist durations.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional

from .config import BlacklistDurationConfig


logger = logging.getLogger(__name__)


@dataclass
class BlacklistEntry:
    """Entry in the blacklist."""
    symbol: str
    loss_pct: float
    timestamp: datetime
    expiry: datetime
    duration_minutes: int


class DynamicBlacklistManager:
    """Manages symbol blacklisting with loss-severity-based durations.
    
    Blacklist durations by loss severity:
    - < 1% loss: 15 minutes
    - 1-2% loss: 30 minutes
    - > 2% loss: 60 minutes
    """
    
    def __init__(self, config: Optional[BlacklistDurationConfig] = None):
        """Initialize dynamic blacklist manager.
        
        Args:
            config: Blacklist duration configuration. Uses defaults if None.
        """
        self.config = config or BlacklistDurationConfig()
        self._blacklist: Dict[str, BlacklistEntry] = {}
    
    def get_blacklist_duration(self, loss_pct: float) -> int:
        """Get blacklist duration based on loss severity.
        
        Args:
            loss_pct: Loss percentage as decimal (0.01 = 1%)
            
        Returns:
            Blacklist duration in minutes
        """
        # Ensure loss_pct is positive for comparison
        loss_pct = abs(loss_pct)
        
        if loss_pct < self.config.small_loss_threshold:
            return self.config.small_loss_duration
        elif loss_pct < self.config.medium_loss_threshold:
            return self.config.medium_loss_duration
        else:
            return self.config.large_loss_duration
    
    def record_loss(
        self,
        symbol: str,
        loss_pct: float,
        timestamp: Optional[datetime] = None
    ) -> BlacklistEntry:
        """Record a loss and blacklist the symbol.
        
        Args:
            symbol: Trading symbol
            loss_pct: Loss percentage as decimal
            timestamp: When the loss occurred (defaults to now)
            
        Returns:
            BlacklistEntry created
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        duration = self.get_blacklist_duration(loss_pct)
        expiry = timestamp + timedelta(minutes=duration)
        
        entry = BlacklistEntry(
            symbol=symbol,
            loss_pct=loss_pct,
            timestamp=timestamp,
            expiry=expiry,
            duration_minutes=duration
        )
        
        self._blacklist[symbol] = entry
        
        logger.warning(
            f"Symbol {symbol} blacklisted for {duration} minutes "
            f"(loss: {abs(loss_pct)*100:.2f}%)"
        )
        
        return entry
    
    def is_blacklisted(
        self,
        symbol: str,
        current_time: Optional[datetime] = None
    ) -> bool:
        """Check if symbol is currently blacklisted.
        
        Args:
            symbol: Trading symbol
            current_time: Current timestamp (defaults to now)
            
        Returns:
            True if symbol is blacklisted
        """
        if current_time is None:
            current_time = datetime.now()
        
        if symbol not in self._blacklist:
            return False
        
        entry = self._blacklist[symbol]
        
        if current_time >= entry.expiry:
            # Blacklist expired, remove it
            del self._blacklist[symbol]
            logger.info(f"Symbol {symbol} blacklist expired")
            return False
        
        return True
    
    def get_remaining_time(
        self,
        symbol: str,
        current_time: Optional[datetime] = None
    ) -> Optional[int]:
        """Get remaining blacklist time in minutes.
        
        Args:
            symbol: Trading symbol
            current_time: Current timestamp
            
        Returns:
            Remaining minutes, or None if not blacklisted
        """
        if current_time is None:
            current_time = datetime.now()
        
        if symbol not in self._blacklist:
            return None
        
        entry = self._blacklist[symbol]
        
        if current_time >= entry.expiry:
            return None
        
        remaining = entry.expiry - current_time
        return int(remaining.total_seconds() / 60)
    
    def cleanup_expired(
        self,
        current_time: Optional[datetime] = None
    ) -> int:
        """Remove expired blacklist entries.
        
        Args:
            current_time: Current timestamp
            
        Returns:
            Number of entries removed
        """
        if current_time is None:
            current_time = datetime.now()
        
        expired = [
            symbol for symbol, entry in self._blacklist.items()
            if current_time >= entry.expiry
        ]
        
        for symbol in expired:
            del self._blacklist[symbol]
            logger.info(f"Cleaned up expired blacklist for {symbol}")
        
        return len(expired)
    
    def get_blacklisted_symbols(self) -> list:
        """Get list of currently blacklisted symbols.
        
        Returns:
            List of blacklisted symbol names
        """
        return list(self._blacklist.keys())
