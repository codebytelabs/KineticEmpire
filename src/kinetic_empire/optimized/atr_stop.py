"""Optimized ATR-based stop loss calculator."""

from typing import Optional
from .models import MarketRegime, StopResult
from .config import OptimizedConfig, DEFAULT_CONFIG


class OptimizedATRStopCalculator:
    """Calculate stop loss levels using regime-adaptive ATR multipliers."""
    
    def __init__(self, config: OptimizedConfig = DEFAULT_CONFIG):
        self.config = config
    
    def get_multiplier(self, regime: MarketRegime) -> float:
        """Get ATR multiplier based on market regime.
        
        Returns:
            3.0x for HIGH_VOLATILITY
            2.0x for LOW_VOLATILITY or SIDEWAYS
            2.5x for TRENDING or CHOPPY
        """
        if regime == MarketRegime.HIGH_VOLATILITY:
            return self.config.ATR_HIGH_VOL_MULTIPLIER
        elif regime in (MarketRegime.LOW_VOLATILITY, MarketRegime.SIDEWAYS):
            return self.config.ATR_LOW_VOL_MULTIPLIER
        else:  # TRENDING or CHOPPY
            return self.config.ATR_BASE_MULTIPLIER
    
    def calculate_stop(
        self,
        entry_price: float,
        atr: float,
        direction: str,
        regime: MarketRegime,
        position_size: float,
        position_value: Optional[float] = None
    ) -> StopResult:
        """Calculate stop loss with regime-adaptive multiplier.
        
        Args:
            entry_price: Entry price of the position
            atr: Current ATR value
            direction: 'long' or 'short'
            regime: Current market regime
            position_size: Size of the position in units
            position_value: Total value of position (optional, calculated if not provided)
        
        Returns:
            StopResult with stop price and any adjustments
        """
        if entry_price <= 0 or atr <= 0 or position_size <= 0:
            raise ValueError("entry_price, atr, and position_size must be positive")
        
        if direction not in ('long', 'short'):
            raise ValueError("direction must be 'long' or 'short'")
        
        multiplier = self.get_multiplier(regime)
        stop_distance = atr * multiplier
        
        if direction == 'long':
            stop_price = entry_price - stop_distance
        else:
            stop_price = entry_price + stop_distance
        
        # Calculate distance as percentage
        distance_percent = stop_distance / entry_price
        
        # Check if max loss would be exceeded
        if position_value is None:
            position_value = position_size * entry_price
        
        potential_loss_percent = distance_percent
        max_loss_exceeded = potential_loss_percent > self.config.MAX_LOSS_PERCENT
        
        adjusted_position_size = None
        if max_loss_exceeded:
            # Reduce position size to meet max loss requirement
            reduction_factor = self.config.MAX_LOSS_PERCENT / potential_loss_percent
            adjusted_position_size = position_size * reduction_factor
        
        return StopResult(
            stop_price=stop_price,
            multiplier_used=multiplier,
            adjusted_position_size=adjusted_position_size,
            max_loss_exceeded=max_loss_exceeded,
            distance_percent=distance_percent
        )
