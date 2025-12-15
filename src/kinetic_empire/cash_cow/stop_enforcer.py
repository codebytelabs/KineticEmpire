"""Minimum Stop Distance Enforcement module.

Ensures stop losses maintain a minimum distance from entry price
to avoid being stopped out by normal market noise.
"""

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class StopEnforcerConfig:
    """Configuration for stop distance enforcement."""
    minimum_stop_pct: float = 1.5  # 1.5% minimum stop distance


class StopDistanceEnforcer:
    """Enforces minimum stop loss distances.
    
    From Requirements 7.1-7.3:
    - Minimum stop distance of 1.5% from entry price
    - Use 1.5% minimum when ATR-based stop is closer
    - Reject trades where stop distance is below minimum
    """

    def __init__(self, config: Optional[StopEnforcerConfig] = None):
        """Initialize stop distance enforcer.
        
        Args:
            config: Stop enforcer configuration
        """
        self.config = config or StopEnforcerConfig()

    def calculate_stop_distance_pct(self, entry_price: float, stop_price: float) -> float:
        """Calculate stop distance as percentage of entry price.
        
        Args:
            entry_price: Entry price
            stop_price: Stop loss price
            
        Returns:
            Stop distance as percentage
        """
        if entry_price <= 0:
            return 0.0
        return abs(entry_price - stop_price) / entry_price * 100

    def enforce_minimum_stop(
        self, 
        entry_price: float, 
        calculated_stop: float,
        direction: str = "long"
    ) -> float:
        """Enforce minimum stop distance.
        
        Args:
            entry_price: Entry price
            calculated_stop: Calculated stop price (e.g., from ATR)
            direction: Trade direction ("long" or "short")
            
        Returns:
            Stop price with minimum distance enforced
            
        Validates: Requirements 7.1, 7.2
        """
        if entry_price <= 0:
            return calculated_stop
        
        min_distance = entry_price * (self.config.minimum_stop_pct / 100)
        
        if direction.lower() == "long":
            # For longs, stop is below entry
            min_stop = entry_price - min_distance
            # Use the lower (further) stop
            return min(calculated_stop, min_stop)
        else:
            # For shorts, stop is above entry
            min_stop = entry_price + min_distance
            # Use the higher (further) stop
            return max(calculated_stop, min_stop)

    def validate_stop_distance(
        self, 
        entry_price: float, 
        stop_price: float
    ) -> Tuple[bool, Optional[str]]:
        """Validate that stop distance meets minimum requirement.
        
        Args:
            entry_price: Entry price
            stop_price: Stop loss price
            
        Returns:
            Tuple of (is_valid, rejection_reason)
            
        Validates: Requirement 7.3
        """
        if entry_price <= 0:
            return False, "Invalid entry price"
        
        distance_pct = self.calculate_stop_distance_pct(entry_price, stop_price)
        
        if distance_pct < self.config.minimum_stop_pct:
            return False, (
                f"Stop distance {distance_pct:.2f}% is below minimum "
                f"{self.config.minimum_stop_pct}%"
            )
        
        return True, None

    def get_minimum_stop_price(self, entry_price: float, direction: str = "long") -> float:
        """Get the minimum allowed stop price.
        
        Args:
            entry_price: Entry price
            direction: Trade direction ("long" or "short")
            
        Returns:
            Minimum stop price that meets the distance requirement
        """
        if entry_price <= 0:
            return 0.0
        
        min_distance = entry_price * (self.config.minimum_stop_pct / 100)
        
        if direction.lower() == "long":
            return entry_price - min_distance
        else:
            return entry_price + min_distance
