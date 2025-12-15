"""Regime-Adaptive Stop Loss Manager.

Adjusts stop loss distances based on market regime and trend type.
"""

from dataclasses import dataclass
from typing import Optional

from kinetic_empire.models import Regime
from .config import RegimeStopConfig


class RegimeAdaptiveStops:
    """Calculates regime-aware stop loss distances.
    
    ATR multipliers by regime:
    - BULL + TRENDING: 1.5x ATR (tighter, capture more profit)
    - BULL + SIDEWAYS: 2.0x ATR (wider, avoid whipsaws)
    - BEAR: 2.5x ATR (widest, high volatility protection)
    
    Note: Existing position stops are NOT modified on regime change.
    """
    
    def __init__(self, config: Optional[RegimeStopConfig] = None):
        """Initialize regime-adaptive stops.
        
        Args:
            config: Regime stop configuration. Uses defaults if None.
        """
        self.config = config or RegimeStopConfig()
    
    def get_atr_multiplier(
        self,
        regime: Regime,
        trend_type: str = "trending"
    ) -> float:
        """Get ATR multiplier for regime and trend.
        
        Args:
            regime: Current market regime (BULL or BEAR)
            trend_type: Trend classification ("trending" or "sideways")
            
        Returns:
            ATR multiplier for stop loss calculation
        """
        if regime == Regime.BEAR:
            return self.config.bear_mult
        
        # BULL regime
        if trend_type.lower() == "trending":
            return self.config.bull_trending_mult
        elif trend_type.lower() == "sideways":
            return self.config.bull_sideways_mult
        else:
            return self.config.default_mult
    
    def calculate_stop_loss(
        self,
        entry_price: float,
        atr: float,
        regime: Regime,
        trend_type: str = "trending",
        direction: str = "long"
    ) -> float:
        """Calculate stop loss price for new position.
        
        Args:
            entry_price: Position entry price
            atr: Average True Range value
            regime: Current market regime
            trend_type: Trend classification
            direction: Trade direction ("long" or "short")
            
        Returns:
            Stop loss price
        """
        if atr < 0:
            atr = 0
        
        multiplier = self.get_atr_multiplier(regime, trend_type)
        stop_distance = multiplier * atr
        
        if direction == "long":
            return entry_price - stop_distance
        else:
            return entry_price + stop_distance
    
    def calculate_stop_percentage(
        self,
        entry_price: float,
        atr: float,
        regime: Regime,
        trend_type: str = "trending"
    ) -> float:
        """Calculate stop loss as percentage from entry.
        
        Args:
            entry_price: Position entry price
            atr: Average True Range value
            regime: Current market regime
            trend_type: Trend classification
            
        Returns:
            Stop loss percentage (negative for long positions)
        """
        if entry_price <= 0:
            return 0.0
        
        stop_price = self.calculate_stop_loss(
            entry_price, atr, regime, trend_type, "long"
        )
        return ((stop_price - entry_price) / entry_price) * 100
    
    def should_update_stop(
        self,
        existing_stop: float,
        new_stop: float,
        direction: str = "long"
    ) -> bool:
        """Check if stop should be updated (only if more favorable).
        
        For existing positions, we only tighten stops, never widen.
        
        Args:
            existing_stop: Current stop loss price
            new_stop: Newly calculated stop price
            direction: Trade direction
            
        Returns:
            True if new stop is more favorable (tighter)
        """
        if direction == "long":
            return new_stop > existing_stop
        else:
            return new_stop < existing_stop
