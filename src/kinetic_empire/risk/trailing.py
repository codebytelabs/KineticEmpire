"""Trailing stop management module.

Implements trailing stops for profitable positions to protect gains while
allowing winners to run.

Enhanced with TrailingOptimizer for earlier activation (1.5% vs 2.5%)
and dynamic tightening at 3%+ profit.
"""

from dataclasses import dataclass
from typing import Optional

from kinetic_empire.optimizations import TrailingOptimizer
from kinetic_empire.optimizations.config import TrailingOptConfig


@dataclass
class TrailingConfig:
    """Configuration for trailing stop management."""
    activation_profit_pct: float = 1.5  # Profit % to activate trailing (optimized from 2.5%)
    atr_multiplier: float = 1.5         # ATR multiplier for trailing distance
    tight_multiplier: float = 1.0       # Tighter multiplier at 3%+ profit
    tight_threshold_pct: float = 3.0    # Profit % to tighten trail
    use_optimizer: bool = True          # Use enhanced optimizer


class TrailingStopManager:
    """Manages trailing stops for profitable positions.
    
    Activates trailing stops when profit exceeds threshold, then adjusts
    stop level as price moves up, never allowing it to decrease.
    
    Enhanced features (when use_optimizer=True):
    - Earlier activation at 1.5% profit (vs 2.5% default)
    - Dynamic tightening to 1.0x ATR at 3%+ profit
    """

    def __init__(self, config: Optional[TrailingConfig] = None):
        """Initialize trailing stop manager.
        
        Args:
            config: Trailing stop configuration. Uses defaults if None.
        """
        self.config = config or TrailingConfig()
        
        # Initialize optimizer if enabled
        if self.config.use_optimizer:
            opt_config = TrailingOptConfig(
                activation_pct=self.config.activation_profit_pct / 100,
                normal_trail_mult=self.config.atr_multiplier,
                tight_trail_mult=self.config.tight_multiplier,
                tight_threshold_pct=self.config.tight_threshold_pct / 100
            )
            self._optimizer = TrailingOptimizer(opt_config)
        else:
            self._optimizer = None

    def should_activate(
        self,
        unrealized_profit_pct: float,
        threshold: Optional[float] = None
    ) -> bool:
        """Check if trailing stop should be activated.
        
        Args:
            unrealized_profit_pct: Current unrealized profit percentage
            threshold: Activation threshold (default from config)
            
        Returns:
            True if profit exceeds threshold
        """
        # Use optimizer if available
        if self._optimizer is not None:
            return self._optimizer.should_activate(unrealized_profit_pct / 100)
        
        threshold = threshold if threshold is not None else self.config.activation_profit_pct
        return unrealized_profit_pct > threshold

    def calculate_trailing_stop(
        self,
        current_price: float,
        atr: float,
        multiplier: Optional[float] = None,
        profit_pct: Optional[float] = None
    ) -> float:
        """Calculate trailing stop level.
        
        Formula: trailing_stop = current_price - (atr_multiplier * atr)
        
        Args:
            current_price: Current market price
            atr: Average True Range value
            multiplier: ATR multiplier (default from config)
            profit_pct: Current profit percentage (for dynamic tightening)
            
        Returns:
            Trailing stop price
        """
        # Use optimizer for dynamic multiplier if profit_pct provided
        if self._optimizer is not None and profit_pct is not None:
            return self._optimizer.calculate_trail_stop(
                current_price, atr, profit_pct / 100, "long"
            )
        
        multiplier = multiplier if multiplier is not None else self.config.atr_multiplier
        return current_price - (multiplier * atr)

    def update_stop_if_higher(
        self,
        new_stop: float,
        current_stop: float
    ) -> float:
        """Update stop level only if new level is higher.
        
        Ensures trailing stop is monotonically increasing (never decreases).
        
        Args:
            new_stop: Newly calculated stop level
            current_stop: Current stop level
            
        Returns:
            Maximum of new_stop and current_stop
        """
        return max(new_stop, current_stop)

    def calculate_trailing_stop_percentage(
        self,
        current_price: float,
        atr: float,
        multiplier: Optional[float] = None
    ) -> float:
        """Calculate trailing stop as percentage below current price.
        
        Args:
            current_price: Current market price
            atr: Average True Range value
            multiplier: ATR multiplier (default from config)
            
        Returns:
            Trailing stop percentage (negative value)
        """
        if current_price == 0:
            return 0.0
        
        stop_price = self.calculate_trailing_stop(current_price, atr, multiplier)
        return ((stop_price - current_price) / current_price) * 100
