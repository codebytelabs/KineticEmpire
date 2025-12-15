"""Pyramiding Module - Add to winning positions at key levels.

Allows adding to profitable positions while managing risk through
proper stop placement and size constraints.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional, Tuple

from .models import RFactorPosition, TrendStrength


@dataclass
class PyramidConfig:
    """Configuration for position pyramiding."""
    entry_r_level: float = 1.0  # Add at 1R profit
    add_size_pct: float = 0.5  # Add 50% of original size
    max_pyramids: int = 2  # Maximum pyramid additions
    pyramid_stop_at_entry: bool = True  # Stop for pyramid at original entry


@dataclass
class PyramidRecord:
    """Record of a pyramid addition."""
    pyramid_number: int
    add_price: float
    add_size: float
    add_time: datetime
    stop_loss: float


class PyramidingModule:
    """Manages position pyramiding (adding to winners)."""
    
    def __init__(self, config: Optional[PyramidConfig] = None):
        self.config = config or PyramidConfig()
        self.pyramid_counts: Dict[str, int] = {}
        self.pyramid_records: Dict[str, list] = {}
    
    def should_pyramid(self, position: RFactorPosition, 
                       trend: TrendStrength) -> bool:
        """Check if position should be pyramided.
        
        Args:
            position: Current position
            trend: Current trend strength
            
        Returns:
            True if pyramid conditions are met
        """
        pair = position.pair
        count = self.pyramid_counts.get(pair, 0)
        
        # Check max pyramids
        if count >= self.config.max_pyramids:
            return False
        
        # Check R-level requirement
        if position.current_r < self.config.entry_r_level:
            return False
        
        # Check trend alignment
        if position.side == "LONG":
            if trend not in [TrendStrength.STRONG_UPTREND, TrendStrength.WEAK_UPTREND]:
                return False
        else:  # SHORT
            if trend not in [TrendStrength.STRONG_DOWNTREND, TrendStrength.WEAK_DOWNTREND]:
                return False
        
        return True
    
    def calculate_pyramid_size(self, original_size: float) -> float:
        """Calculate size for pyramid addition.
        
        Args:
            original_size: Original position size
            
        Returns:
            Size to add
        """
        return original_size * self.config.add_size_pct
    
    def calculate_pyramid_stop(self, position: RFactorPosition) -> float:
        """Calculate stop loss for pyramid portion.
        
        Args:
            position: Current position
            
        Returns:
            Stop loss price for pyramid
        """
        if self.config.pyramid_stop_at_entry:
            return position.entry_price
        return position.stop_loss
    
    def execute_pyramid(self, position: RFactorPosition, 
                       current_price: float) -> PyramidRecord:
        """Execute pyramid addition.
        
        Args:
            position: Current position
            current_price: Current market price
            
        Returns:
            PyramidRecord of the addition
        """
        pair = position.pair
        count = self.pyramid_counts.get(pair, 0)
        
        add_size = self.calculate_pyramid_size(position.original_size)
        stop_loss = self.calculate_pyramid_stop(position)
        
        record = PyramidRecord(
            pyramid_number=count + 1,
            add_price=current_price,
            add_size=add_size,
            add_time=datetime.now(),
            stop_loss=stop_loss
        )
        
        # Update tracking
        self.pyramid_counts[pair] = count + 1
        if pair not in self.pyramid_records:
            self.pyramid_records[pair] = []
        self.pyramid_records[pair].append(record)
        
        return record
    
    def update_average_entry(self, position: RFactorPosition,
                            pyramid_price: float,
                            pyramid_size: float) -> float:
        """Recalculate average entry after pyramid.
        
        Args:
            position: Current position
            pyramid_price: Price of pyramid addition
            pyramid_size: Size of pyramid addition
            
        Returns:
            New average entry price
        """
        total_size = position.position_size + pyramid_size
        total_cost = (position.entry_price * position.position_size + 
                     pyramid_price * pyramid_size)
        
        return total_cost / total_size if total_size > 0 else position.entry_price
    
    def get_pyramid_count(self, pair: str) -> int:
        """Get number of pyramids for a position."""
        return self.pyramid_counts.get(pair, 0)
    
    def get_total_pyramid_size(self, pair: str) -> float:
        """Get total size added through pyramiding."""
        records = self.pyramid_records.get(pair, [])
        return sum(r.add_size for r in records)
    
    def can_pyramid(self, pair: str) -> bool:
        """Check if more pyramids are allowed."""
        return self.get_pyramid_count(pair) < self.config.max_pyramids
    
    def reset_position(self, pair: str) -> None:
        """Reset pyramid tracking for a position."""
        self.pyramid_counts.pop(pair, None)
        self.pyramid_records.pop(pair, None)
    
    def get_pyramid_summary(self, pair: str) -> Dict:
        """Get summary of pyramiding for a position."""
        count = self.get_pyramid_count(pair)
        records = self.pyramid_records.get(pair, [])
        
        return {
            "pair": pair,
            "pyramid_count": count,
            "max_pyramids": self.config.max_pyramids,
            "can_pyramid": self.can_pyramid(pair),
            "total_added_size": self.get_total_pyramid_size(pair),
            "records": [
                {
                    "number": r.pyramid_number,
                    "price": r.add_price,
                    "size": r.add_size,
                    "stop": r.stop_loss,
                    "time": r.add_time.isoformat()
                }
                for r in records
            ]
        }
