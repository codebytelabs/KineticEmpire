"""Stop loss management module.

Implements ATR-based stop loss calculation for volatility-adjusted risk protection.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class StopLossConfig:
    """Configuration for stop loss management."""
    atr_multiplier: float = 2.0  # ATR multiplier for stop distance


class StopLossManager:
    """Manages stop loss calculation and placement.
    
    Uses ATR (Average True Range) to set volatility-adjusted stop losses,
    ensuring stops are placed at appropriate distances based on market conditions.
    """

    def __init__(self, config: Optional[StopLossConfig] = None):
        """Initialize stop loss manager.
        
        Args:
            config: Stop loss configuration. Uses defaults if None.
        """
        self.config = config or StopLossConfig()

    def calculate_stop_loss(
        self,
        entry_price: float,
        atr: float,
        multiplier: Optional[float] = None
    ) -> float:
        """Calculate stop loss price using ATR.
        
        Formula: stop_loss = entry_price - (atr_multiplier * atr)
        
        Args:
            entry_price: Entry price of the position
            atr: Average True Range value
            multiplier: ATR multiplier (default from config)
            
        Returns:
            Stop loss price
        """
        multiplier = multiplier if multiplier is not None else self.config.atr_multiplier
        
        return entry_price - (multiplier * atr)

    def calculate_stop_loss_percentage(
        self,
        entry_price: float,
        atr: float,
        multiplier: Optional[float] = None
    ) -> float:
        """Calculate stop loss as percentage below entry.
        
        Args:
            entry_price: Entry price of the position
            atr: Average True Range value
            multiplier: ATR multiplier (default from config)
            
        Returns:
            Stop loss percentage (negative value)
        """
        if entry_price == 0:
            return 0.0
        
        stop_price = self.calculate_stop_loss(entry_price, atr, multiplier)
        return ((stop_price - entry_price) / entry_price) * 100
