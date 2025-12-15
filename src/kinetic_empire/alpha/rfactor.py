"""R-Factor Calculator for systematic position management.

R-Factor is the risk unit defined as the distance from entry to stop loss.
All profits are measured in R-multiples for consistent risk management.
"""

from dataclasses import dataclass
from typing import Dict, Optional, List
from datetime import datetime

from .models import RFactorPosition, PartialExit


@dataclass
class RFactorConfig:
    """Configuration for R-Factor calculations."""
    default_reward_risk: float = 2.0  # Default R:R ratio for targets


class RFactorCalculator:
    """Calculator for R-Factor based position management.
    
    R = |entry_price - stop_loss|
    Current R = profit / R_value
    """
    
    def __init__(self, config: Optional[RFactorConfig] = None):
        self.config = config or RFactorConfig()
        self.positions: Dict[str, RFactorPosition] = {}
    
    def calculate_r_value(self, entry_price: float, stop_loss: float, 
                          side: str) -> float:
        """Calculate R value (risk per unit) for a position.
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            side: LONG or SHORT
            
        Returns:
            R value (always positive)
        """
        if side == "LONG":
            return abs(entry_price - stop_loss)
        return abs(stop_loss - entry_price)
    
    def calculate_current_r(self, entry_price: float, current_price: float,
                           r_value: float, side: str) -> float:
        """Calculate current profit in R-multiples.
        
        Args:
            entry_price: Entry price
            current_price: Current market price
            r_value: R value for the position
            side: LONG or SHORT
            
        Returns:
            Current R multiple (can be negative)
        """
        if r_value == 0:
            return 0.0
        
        if side == "LONG":
            profit = current_price - entry_price
        else:
            profit = entry_price - current_price
        
        return profit / r_value

    
    def create_position(self, pair: str, side: str, entry_price: float,
                       stop_loss: float, position_size: float,
                       strategy: str = "") -> RFactorPosition:
        """Create a new R-Factor tracked position.
        
        Args:
            pair: Trading pair
            side: LONG or SHORT
            entry_price: Entry price
            stop_loss: Stop loss price
            position_size: Position size in base currency
            strategy: Strategy name
            
        Returns:
            New RFactorPosition
        """
        r_value = self.calculate_r_value(entry_price, stop_loss, side)
        
        position = RFactorPosition(
            pair=pair,
            side=side,
            entry_price=entry_price,
            stop_loss=stop_loss,
            position_size=position_size,
            original_size=position_size,
            r_value=r_value,
            strategy=strategy,
        )
        
        self.positions[pair] = position
        return position
    
    def update_position(self, pair: str, current_price: float) -> Optional[float]:
        """Update position with current price and return current R.
        
        Args:
            pair: Trading pair
            current_price: Current market price
            
        Returns:
            Current R multiple or None if position not found
        """
        position = self.positions.get(pair)
        if not position:
            return None
        
        current_r = position.update_current_r(current_price)
        return current_r
    
    def update_peak_r(self, pair: str) -> Optional[float]:
        """Update and return peak R for a position.
        
        Args:
            pair: Trading pair
            
        Returns:
            Peak R multiple or None if position not found
        """
        position = self.positions.get(pair)
        if not position:
            return None
        
        # Peak is automatically updated in update_current_r
        return position.peak_r
    
    def is_risk_free(self, pair: str) -> bool:
        """Check if position is risk-free (took profit at 1R+).
        
        Args:
            pair: Trading pair
            
        Returns:
            True if position has taken profit at 1R or higher
        """
        position = self.positions.get(pair)
        if not position:
            return False
        
        return position.is_risk_free()
    
    def record_partial_exit(self, pair: str, r_level: float, percentage: float,
                           exit_price: float, profit: float) -> Optional[PartialExit]:
        """Record a partial exit for a position.
        
        Args:
            pair: Trading pair
            r_level: R level at which exit occurred
            percentage: Percentage of original position closed
            exit_price: Exit price
            profit: Profit from this partial exit
            
        Returns:
            PartialExit record or None if position not found
        """
        position = self.positions.get(pair)
        if not position:
            return None
        
        partial_exit = PartialExit(
            r_level=r_level,
            percentage=percentage,
            exit_price=exit_price,
            exit_time=datetime.now(),
            profit=profit,
        )
        
        position.partial_exits.append(partial_exit)
        position.position_size = position.original_size * position.get_remaining_pct()
        
        return partial_exit
    
    def get_position(self, pair: str) -> Optional[RFactorPosition]:
        """Get position by pair."""
        return self.positions.get(pair)
    
    def remove_position(self, pair: str) -> Optional[RFactorPosition]:
        """Remove and return position."""
        return self.positions.pop(pair, None)
    
    def get_all_positions(self) -> List[RFactorPosition]:
        """Get all tracked positions."""
        return list(self.positions.values())
    
    def calculate_target_price(self, entry_price: float, stop_loss: float,
                               side: str, r_multiple: float) -> float:
        """Calculate target price for a given R multiple.
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            side: LONG or SHORT
            r_multiple: Target R multiple (e.g., 2.0 for 2R)
            
        Returns:
            Target price
        """
        r_value = self.calculate_r_value(entry_price, stop_loss, side)
        
        if side == "LONG":
            return entry_price + (r_value * r_multiple)
        return entry_price - (r_value * r_multiple)
    
    def calculate_breakeven_stop(self, position: RFactorPosition) -> float:
        """Calculate breakeven stop price (entry price).
        
        Args:
            position: RFactorPosition
            
        Returns:
            Breakeven stop price
        """
        return position.entry_price
