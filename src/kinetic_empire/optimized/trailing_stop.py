"""Optimized trailing stop with regime-adaptive parameters."""

from .models import MarketRegime
from .config import OptimizedConfig, DEFAULT_CONFIG


class OptimizedTrailingStop:
    """Manages trailing stops with regime-adaptive parameters."""
    
    def __init__(self, config: OptimizedConfig = DEFAULT_CONFIG):
        self.config = config
    
    def get_activation_threshold(self, regime: MarketRegime) -> float:
        """Get activation threshold based on regime.
        
        Args:
            regime: Current market regime
            
        Returns:
            Activation threshold as decimal (e.g., 0.02 for 2%)
        """
        if regime == MarketRegime.TRENDING:
            return self.config.TRAILING_TRENDING_ACTIVATION
        elif regime == MarketRegime.SIDEWAYS:
            return self.config.TRAILING_SIDEWAYS_ACTIVATION
        else:
            return self.config.TRAILING_BASE_ACTIVATION
    
    def should_activate(
        self,
        current_profit_pct: float,
        regime: MarketRegime
    ) -> bool:
        """Check if trailing stop should activate.
        
        Args:
            current_profit_pct: Current profit as decimal (e.g., 0.02 for 2%)
            regime: Current market regime
            
        Returns:
            True if trailing stop should activate
        """
        threshold = self.get_activation_threshold(regime)
        return current_profit_pct >= threshold
    
    def update_stop(
        self,
        current_price: float,
        current_stop: float,
        direction: str,
        highest_price: float = None,
        lowest_price: float = None
    ) -> float:
        """Update trailing stop level.
        
        The stop only moves in the favorable direction (never retreats).
        
        Args:
            current_price: Current market price
            current_stop: Current stop price
            direction: 'long' or 'short'
            highest_price: Highest price since entry (for longs)
            lowest_price: Lowest price since entry (for shorts)
            
        Returns:
            Updated stop price
        """
        if direction not in ('long', 'short'):
            raise ValueError("direction must be 'long' or 'short'")
        
        step = self.config.TRAILING_STEP_SIZE
        
        if direction == 'long':
            # For longs, stop trails below price
            reference_price = highest_price if highest_price else current_price
            new_stop = reference_price * (1 - step)
            # Stop can only move up, never down
            return max(current_stop, new_stop)
        else:
            # For shorts, stop trails above price
            reference_price = lowest_price if lowest_price else current_price
            new_stop = reference_price * (1 + step)
            # Stop can only move down, never up
            return min(current_stop, new_stop)
