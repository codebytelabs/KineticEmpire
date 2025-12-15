"""Enhanced Trailing Stop Optimizer.

Implements standardized trailing stop activation at 1.5% profit with
dynamic tightening at 3%+ profit.
"""

from dataclasses import dataclass
from typing import Optional

from .config import TrailingOptConfig


@dataclass
class EnhancedTrailingState:
    """State for enhanced trailing stop management."""
    is_active: bool = False
    peak_price: float = 0.0
    peak_profit_pct: float = 0.0
    trail_multiplier: float = 1.5
    tp1_done: bool = False
    tp2_done: bool = False
    remaining_pct: float = 1.0  # Remaining position percentage


class TrailingOptimizer:
    """Optimized trailing stop manager with earlier activation.
    
    Key improvements over base trailing:
    - Activates at 1.5% profit (vs 2.5% default)
    - Tightens to 1.0x ATR at 3%+ profit
    - Integrates with partial profit taking
    """
    
    def __init__(self, config: Optional[TrailingOptConfig] = None):
        """Initialize trailing optimizer.
        
        Args:
            config: Trailing configuration. Uses defaults if None.
        """
        self.config = config or TrailingOptConfig()
    
    def should_activate(self, profit_pct: float) -> bool:
        """Check if trailing stop should be activated.
        
        Activates when profit >= 1.5% (configurable).
        
        Args:
            profit_pct: Current unrealized profit as decimal (0.015 = 1.5%)
            
        Returns:
            True if profit >= activation threshold
        """
        return profit_pct >= self.config.activation_pct
    
    def get_trail_multiplier(self, profit_pct: float) -> float:
        """Get ATR multiplier based on profit level.
        
        Returns tighter trail (1.0x) when profit >= 3%.
        
        Args:
            profit_pct: Current unrealized profit as decimal
            
        Returns:
            ATR multiplier (1.5x normal, 1.0x when profit >= 3%)
        """
        if profit_pct >= self.config.tight_threshold_pct:
            return self.config.tight_trail_mult
        return self.config.normal_trail_mult
    
    def calculate_trail_stop(
        self,
        peak_price: float,
        atr: float,
        profit_pct: float,
        direction: str = "long"
    ) -> float:
        """Calculate trailing stop price.
        
        Args:
            peak_price: Highest price since entry (for long)
            atr: Average True Range value
            profit_pct: Current unrealized profit as decimal
            direction: Trade direction ("long" or "short")
            
        Returns:
            Trailing stop price
        """
        if atr < 0:
            atr = 0
        
        multiplier = self.get_trail_multiplier(profit_pct)
        trail_distance = multiplier * atr
        
        if direction == "long":
            return peak_price - trail_distance
        else:
            return peak_price + trail_distance
    
    def update_state(
        self,
        state: EnhancedTrailingState,
        current_price: float,
        entry_price: float,
        atr: float,
        direction: str = "long"
    ) -> EnhancedTrailingState:
        """Update trailing state with current price.
        
        Args:
            state: Current trailing state
            current_price: Current market price
            entry_price: Position entry price
            atr: Average True Range value
            direction: Trade direction
            
        Returns:
            Updated trailing state
        """
        if entry_price == 0:
            return state
        
        # Calculate profit
        if direction == "long":
            profit_pct = (current_price - entry_price) / entry_price
        else:
            profit_pct = (entry_price - current_price) / entry_price
        
        # Check activation
        if not state.is_active and self.should_activate(profit_pct):
            state.is_active = True
            state.peak_price = current_price
            state.peak_profit_pct = profit_pct
        
        # Update peak if active
        if state.is_active:
            if direction == "long" and current_price > state.peak_price:
                state.peak_price = current_price
                state.peak_profit_pct = profit_pct
            elif direction == "short" and current_price < state.peak_price:
                state.peak_price = current_price
                state.peak_profit_pct = profit_pct
            
            # Update multiplier based on profit
            state.trail_multiplier = self.get_trail_multiplier(state.peak_profit_pct)
        
        return state
    
    def should_exit(
        self,
        state: EnhancedTrailingState,
        current_price: float,
        atr: float,
        direction: str = "long"
    ) -> bool:
        """Check if trailing stop is hit.
        
        Args:
            state: Current trailing state
            current_price: Current market price
            atr: Average True Range value
            direction: Trade direction
            
        Returns:
            True if trailing stop is hit
        """
        if not state.is_active:
            return False
        
        stop_price = self.calculate_trail_stop(
            state.peak_price, atr, state.peak_profit_pct, direction
        )
        
        if direction == "long":
            return current_price <= stop_price
        else:
            return current_price >= stop_price
