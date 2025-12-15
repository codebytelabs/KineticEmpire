"""Partial Profit Taking System - DayTraderAI style R-factor exits.

Books partial profits at predetermined R-factor milestones:
- 25% at 1R (move stop to breakeven)
- 25% at 2R
- 25% at 3R
- Trail remaining 25%
"""

from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Set
from datetime import datetime

from .models import RFactorPosition, PartialExit


@dataclass
class ProfitTakeLevel:
    """A profit-taking level configuration."""
    r_level: float
    percentage: float  # Percentage of ORIGINAL position to close


@dataclass
class ProfitTakeConfig:
    """Configuration for partial profit taking."""
    levels: List[ProfitTakeLevel] = field(default_factory=lambda: [
        ProfitTakeLevel(r_level=1.0, percentage=0.25),
        ProfitTakeLevel(r_level=2.0, percentage=0.25),
        ProfitTakeLevel(r_level=3.0, percentage=0.25),
    ])
    move_stop_to_breakeven_at: float = 1.0
    trail_remaining: bool = True


class PartialProfitTaker:
    """Manages partial profit taking at R-factor milestones."""
    
    def __init__(self, config: Optional[ProfitTakeConfig] = None):
        self.config = config or ProfitTakeConfig()
        self.taken_levels: dict[str, Set[float]] = {}
    
    def check_profit_levels(self, position: RFactorPosition) -> Optional[ProfitTakeLevel]:
        """Check if any profit level should be taken.
        
        Args:
            position: Current position with R-factor tracking
            
        Returns:
            ProfitTakeLevel to execute, or None
        """
        pair = position.pair
        if pair not in self.taken_levels:
            self.taken_levels[pair] = set()
        
        # Check levels in order (ascending R)
        sorted_levels = sorted(self.config.levels, key=lambda x: x.r_level)
        
        for level in sorted_levels:
            if level.r_level in self.taken_levels[pair]:
                continue
            if position.current_r >= level.r_level:
                return level
        
        return None

    
    def mark_level_taken(self, pair: str, r_level: float) -> None:
        """Mark a profit level as taken."""
        if pair not in self.taken_levels:
            self.taken_levels[pair] = set()
        self.taken_levels[pair].add(r_level)
    
    def should_move_stop_to_breakeven(self, position: RFactorPosition) -> bool:
        """Check if stop should be moved to breakeven.
        
        Args:
            position: Current position
            
        Returns:
            True if stop should move to breakeven
        """
        return position.current_r >= self.config.move_stop_to_breakeven_at
    
    def get_remaining_position_pct(self, position: RFactorPosition) -> float:
        """Calculate remaining position percentage after partial exits.
        
        Args:
            position: Current position
            
        Returns:
            Remaining percentage (0.0 to 1.0)
        """
        return position.get_remaining_pct()
    
    def calculate_partial_exit_size(self, position: RFactorPosition, 
                                    level: ProfitTakeLevel) -> float:
        """Calculate the size to exit for a partial take.
        
        Args:
            position: Current position
            level: Profit take level
            
        Returns:
            Size to exit in base currency
        """
        return position.original_size * level.percentage
    
    def calculate_partial_profit(self, position: RFactorPosition,
                                 exit_price: float, exit_size: float) -> float:
        """Calculate profit from a partial exit.
        
        Args:
            position: Current position
            exit_price: Exit price
            exit_size: Size being exited
            
        Returns:
            Profit in quote currency
        """
        if position.side == "LONG":
            return (exit_price - position.entry_price) * exit_size
        return (position.entry_price - exit_price) * exit_size
    
    def execute_partial_exit(self, position: RFactorPosition, 
                            level: ProfitTakeLevel,
                            exit_price: float) -> PartialExit:
        """Execute a partial exit and record it.
        
        Args:
            position: Current position
            level: Profit take level being executed
            exit_price: Exit price
            
        Returns:
            PartialExit record
        """
        exit_size = self.calculate_partial_exit_size(position, level)
        profit = self.calculate_partial_profit(position, exit_price, exit_size)
        
        partial_exit = PartialExit(
            r_level=level.r_level,
            percentage=level.percentage,
            exit_price=exit_price,
            exit_time=datetime.now(),
            profit=profit,
        )
        
        position.partial_exits.append(partial_exit)
        position.position_size = position.original_size * position.get_remaining_pct()
        self.mark_level_taken(position.pair, level.r_level)
        
        return partial_exit
    
    def get_next_target_r(self, position: RFactorPosition) -> Optional[float]:
        """Get the next R target for the position.
        
        Args:
            position: Current position
            
        Returns:
            Next R target or None if all taken
        """
        pair = position.pair
        taken = self.taken_levels.get(pair, set())
        
        for level in sorted(self.config.levels, key=lambda x: x.r_level):
            if level.r_level not in taken:
                return level.r_level
        
        return None
    
    def reset_position(self, pair: str) -> None:
        """Reset tracking for a position (when closed)."""
        self.taken_levels.pop(pair, None)
    
    def get_total_taken_pct(self, pair: str) -> float:
        """Get total percentage taken for a position."""
        taken = self.taken_levels.get(pair, set())
        total = 0.0
        for level in self.config.levels:
            if level.r_level in taken:
                total += level.percentage
        return total
