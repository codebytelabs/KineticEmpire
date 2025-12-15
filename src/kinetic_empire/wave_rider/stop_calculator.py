"""Wave Rider Stop Calculator.

Calculates ATR-based stop losses with bounds:
- Initial stop at 1.5x ATR from entry
- Minimum 0.5% stop distance
- Maximum 3% stop distance
- Direction-aware placement (LONG: below, SHORT: above)
"""

from dataclasses import dataclass
from typing import Optional
from .models import WaveRiderConfig


@dataclass
class StopResult:
    """Result of stop loss calculation."""
    stop_price: float
    stop_pct: float  # As decimal (0.02 = 2%)
    atr_multiplier: float
    is_min_bounded: bool  # True if hit minimum bound
    is_max_bounded: bool  # True if hit maximum bound


class WaveRiderStopCalculator:
    """Calculates ATR-based stop losses with bounds.
    
    Property 11: Stop Loss Bounds
    - stop_pct >= 0.5% (minimum)
    - stop_pct <= 3.0% (maximum)
    
    Property 12: Stop Loss Direction
    - LONG positions have stop_price < entry_price
    - SHORT positions have stop_price > entry_price
    """
    
    ATR_MULTIPLIER = 1.5
    MIN_STOP_PCT = 0.005  # 0.5%
    MAX_STOP_PCT = 0.03   # 3%
    
    def __init__(self, config: Optional[WaveRiderConfig] = None):
        """Initialize the stop calculator.
        
        Args:
            config: Wave Rider configuration
        """
        self.config = config or WaveRiderConfig()
        self.atr_multiplier = self.config.stop_atr_multiplier
        self.min_stop_pct = self.config.min_stop_pct
        self.max_stop_pct = self.config.max_stop_pct
    
    def calculate(
        self,
        entry_price: float,
        direction: str,
        atr_14: float,
    ) -> StopResult:
        """Calculate stop loss price and percentage.
        
        Args:
            entry_price: Entry price
            direction: "LONG" or "SHORT"
            atr_14: 14-period ATR value
        
        Returns:
            StopResult with stop price and metadata
        """
        # Calculate raw stop distance
        raw_stop_distance = atr_14 * self.atr_multiplier
        raw_stop_pct = raw_stop_distance / entry_price if entry_price > 0 else 0.02
        
        # Apply bounds
        is_min_bounded = False
        is_max_bounded = False
        
        if raw_stop_pct < self.min_stop_pct:
            stop_pct = self.min_stop_pct
            is_min_bounded = True
        elif raw_stop_pct > self.max_stop_pct:
            stop_pct = self.max_stop_pct
            is_max_bounded = True
        else:
            stop_pct = raw_stop_pct
        
        # Calculate stop price based on direction
        stop_distance = entry_price * stop_pct
        
        if direction == "LONG":
            stop_price = entry_price - stop_distance
        else:  # SHORT
            stop_price = entry_price + stop_distance
        
        return StopResult(
            stop_price=stop_price,
            stop_pct=stop_pct,
            atr_multiplier=self.atr_multiplier,
            is_min_bounded=is_min_bounded,
            is_max_bounded=is_max_bounded,
        )
    
    def is_stop_hit(
        self,
        current_price: float,
        stop_price: float,
        direction: str,
    ) -> bool:
        """Check if stop loss has been hit.
        
        Args:
            current_price: Current market price
            stop_price: Stop loss price
            direction: "LONG" or "SHORT"
        
        Returns:
            True if stop is hit
        """
        if direction == "LONG":
            return current_price <= stop_price
        else:  # SHORT
            return current_price >= stop_price
