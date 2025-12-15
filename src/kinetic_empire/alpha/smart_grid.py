"""Smart Grid Strategy - Volatility-adjusted grid trading.

Adapts grid spacing based on ATR and applies trend bias to grid placement.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
from pandas import DataFrame

from .models import GridLevel, GridState, TrendStrength


@dataclass
class SmartGridConfig:
    """Configuration for smart grid strategy."""
    grid_count: int = 10
    atr_spacing_multiplier: float = 0.5  # Grid spacing = ATR * multiplier
    trend_bias: float = 0.6  # 60% of grids on trend side
    max_orders_per_pair: int = 10
    profit_target_pct: float = 0.05  # Close grid at 5% profit
    rebalance_threshold_atr: float = 2.0  # Rebalance if price moves 2 ATR


class SmartGridStrategy:
    """Volatility-adjusted, trend-biased grid trading."""
    
    def __init__(self, config: Optional[SmartGridConfig] = None):
        self.config = config or SmartGridConfig()
        self.active_grids: Dict[str, GridState] = {}
    
    def calculate_grid_spacing(self, atr: float) -> float:
        """Calculate grid spacing based on ATR.
        
        Args:
            atr: Current ATR value
            
        Returns:
            Grid spacing in price units
        """
        return atr * self.config.atr_spacing_multiplier
    
    def calculate_grid_levels(self, center_price: float, spacing: float,
                             trend: TrendStrength) -> List[GridLevel]:
        """Calculate grid levels with trend bias.
        
        Args:
            center_price: Price to center grid around
            spacing: Grid spacing
            trend: Current trend for bias
            
        Returns:
            List of GridLevel objects
        """
        levels = []
        
        # Determine distribution based on trend
        if trend in [TrendStrength.STRONG_UPTREND, TrendStrength.WEAK_UPTREND]:
            # More buy levels below (60% below, 40% above)
            below_count = int(self.config.grid_count * self.config.trend_bias)
            above_count = self.config.grid_count - below_count
        elif trend in [TrendStrength.STRONG_DOWNTREND, TrendStrength.WEAK_DOWNTREND]:
            # More sell levels above (60% above, 40% below)
            above_count = int(self.config.grid_count * self.config.trend_bias)
            below_count = self.config.grid_count - above_count
        else:
            # Neutral: equal distribution
            below_count = self.config.grid_count // 2
            above_count = self.config.grid_count - below_count
        
        # Create buy levels below center
        for i in range(1, below_count + 1):
            price = center_price - (i * spacing)
            if price > 0:
                levels.append(GridLevel(price=price, side='BUY'))
        
        # Create sell levels above center
        for i in range(1, above_count + 1):
            price = center_price + (i * spacing)
            levels.append(GridLevel(price=price, side='SELL'))
        
        return levels
    
    def create_grid(self, pair: str, center_price: float, atr: float,
                   trend: TrendStrength, allocated_capital: float) -> GridState:
        """Create a new grid for a pair.
        
        Args:
            pair: Trading pair
            center_price: Price to center grid around
            atr: Current ATR
            trend: Current trend
            allocated_capital: Capital allocated to this grid
            
        Returns:
            GridState object
        """
        spacing = self.calculate_grid_spacing(atr)
        levels = self.calculate_grid_levels(center_price, spacing, trend)
        
        # Calculate quantity per level
        capital_per_level = allocated_capital / len(levels) if levels else 0
        for level in levels:
            level.quantity = capital_per_level / level.price if level.price > 0 else 0
        
        grid = GridState(
            pair=pair,
            center_price=center_price,
            levels=levels,
            allocated_capital=allocated_capital,
            atr_at_creation=atr,
            trend_at_creation=trend
        )
        
        self.active_grids[pair] = grid
        return grid
    
    def should_rebalance(self, pair: str, current_price: float, 
                        current_atr: float) -> bool:
        """Check if grid should be rebalanced.
        
        Args:
            pair: Trading pair
            current_price: Current market price
            current_atr: Current ATR
            
        Returns:
            True if rebalance needed
        """
        if pair not in self.active_grids:
            return False
        
        grid = self.active_grids[pair]
        distance = abs(current_price - grid.center_price)
        threshold = current_atr * self.config.rebalance_threshold_atr
        
        return distance > threshold
    
    def check_profit_target(self, pair: str) -> bool:
        """Check if grid profit target is reached.
        
        Args:
            pair: Trading pair
            
        Returns:
            True if profit target reached
        """
        if pair not in self.active_grids:
            return False
        
        grid = self.active_grids[pair]
        return grid.profit_pct() >= self.config.profit_target_pct * 100
    
    def record_fill(self, pair: str, level_price: float, 
                   fill_price: float) -> Optional[float]:
        """Record a grid level fill.
        
        Args:
            pair: Trading pair
            level_price: Price of the filled level
            fill_price: Actual fill price
            
        Returns:
            Profit if completing a round trip, None otherwise
        """
        if pair not in self.active_grids:
            return None
        
        grid = self.active_grids[pair]
        
        for level in grid.levels:
            if abs(level.price - level_price) < 0.01 and not level.filled:
                level.filled = True
                level.fill_price = fill_price
                level.fill_time = datetime.now()
                
                # Check for completed round trip
                profit = self._check_round_trip(grid, level)
                if profit:
                    grid.total_profit += profit
                    grid.completed_trades += 1
                
                return profit
        
        return None
    
    def _check_round_trip(self, grid: GridState, filled_level: GridLevel) -> Optional[float]:
        """Check if a fill completes a round trip trade."""
        # Find matching opposite level that was filled
        for level in grid.levels:
            if level.filled and level != filled_level:
                if level.side != filled_level.side:
                    # Calculate profit
                    if filled_level.side == 'SELL':
                        profit = (filled_level.fill_price - level.fill_price) * level.quantity
                    else:
                        profit = (level.fill_price - filled_level.fill_price) * filled_level.quantity
                    
                    # Reset both levels
                    level.filled = False
                    level.fill_price = None
                    level.fill_time = None
                    filled_level.filled = False
                    filled_level.fill_price = None
                    filled_level.fill_time = None
                    
                    return profit
        
        return None
    
    def close_grid(self, pair: str) -> Optional[GridState]:
        """Close and remove a grid.
        
        Args:
            pair: Trading pair
            
        Returns:
            Closed GridState or None
        """
        grid = self.active_grids.pop(pair, None)
        if grid:
            grid.active = False
        return grid
    
    def get_grid(self, pair: str) -> Optional[GridState]:
        """Get grid for a pair."""
        return self.active_grids.get(pair)
    
    def get_all_grids(self) -> Dict[str, GridState]:
        """Get all active grids."""
        return self.active_grids.copy()
    
    def get_grid_summary(self, pair: str) -> Optional[dict]:
        """Get summary of a grid."""
        grid = self.active_grids.get(pair)
        if not grid:
            return None
        
        return {
            "pair": pair,
            "center_price": grid.center_price,
            "total_levels": len(grid.levels),
            "filled_levels": len(grid.get_filled_levels()),
            "active_orders": len(grid.get_active_orders()),
            "total_profit": grid.total_profit,
            "profit_pct": grid.profit_pct(),
            "completed_trades": grid.completed_trades,
            "allocated_capital": grid.allocated_capital,
        }
