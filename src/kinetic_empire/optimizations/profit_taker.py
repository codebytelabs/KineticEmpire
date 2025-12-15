"""Partial Profit Taker.

Implements TP1/TP2 partial profit taking at ATR-based levels.
"""

from dataclasses import dataclass
from typing import Optional

from .config import PartialProfitConfig


@dataclass
class TPResult:
    """Result of take profit level check."""
    should_close: bool
    close_pct: float  # Percentage of position to close (0.0 to 1.0)
    tp_level: int  # 0=none, 1=TP1, 2=TP2
    reason: str


class PartialProfitTaker:
    """Manages partial profit taking at TP1 and TP2 levels.
    
    TP1: Close 25% at 1.5x ATR profit
    TP2: Close additional 25% at 2.5x ATR profit
    Remaining 50% managed by trailing stop
    """
    
    def __init__(self, config: Optional[PartialProfitConfig] = None):
        """Initialize partial profit taker.
        
        Args:
            config: Partial profit configuration. Uses defaults if None.
        """
        self.config = config or PartialProfitConfig()
    
    def calculate_profit_in_atr(
        self,
        entry_price: float,
        current_price: float,
        atr: float,
        direction: str = "long"
    ) -> float:
        """Calculate profit as multiple of ATR.
        
        Args:
            entry_price: Position entry price
            current_price: Current market price
            atr: Average True Range value
            direction: Trade direction ("long" or "short")
            
        Returns:
            Profit as ATR multiple (e.g., 1.5 = 1.5x ATR profit)
        """
        if atr <= 0 or entry_price <= 0:
            return 0.0
        
        if direction == "long":
            profit = current_price - entry_price
        else:
            profit = entry_price - current_price
        
        return profit / atr
    
    def check_tp_levels(
        self,
        entry_price: float,
        current_price: float,
        atr: float,
        direction: str = "long",
        tp1_done: bool = False,
        tp2_done: bool = False
    ) -> TPResult:
        """Check if any take profit level is reached.
        
        Args:
            entry_price: Position entry price
            current_price: Current market price
            atr: Average True Range value
            direction: Trade direction
            tp1_done: Whether TP1 has already been taken
            tp2_done: Whether TP2 has already been taken
            
        Returns:
            TPResult with action to take
        """
        profit_atr = self.calculate_profit_in_atr(
            entry_price, current_price, atr, direction
        )
        
        # Check TP2 first (higher level)
        if not tp2_done and profit_atr >= self.config.tp2_atr_mult:
            return TPResult(
                should_close=True,
                close_pct=self.config.tp2_close_pct,
                tp_level=2,
                reason=f"TP2 hit at {profit_atr:.2f}x ATR profit"
            )
        
        # Check TP1
        if not tp1_done and profit_atr >= self.config.tp1_atr_mult:
            return TPResult(
                should_close=True,
                close_pct=self.config.tp1_close_pct,
                tp_level=1,
                reason=f"TP1 hit at {profit_atr:.2f}x ATR profit"
            )
        
        return TPResult(
            should_close=False,
            close_pct=0.0,
            tp_level=0,
            reason="No TP level reached"
        )
    
    def get_close_percentage(self, tp_level: int) -> float:
        """Get close percentage for a TP level.
        
        Args:
            tp_level: Take profit level (1 or 2)
            
        Returns:
            Percentage of position to close (0.25 for both TP1 and TP2)
        """
        if tp_level == 1:
            return self.config.tp1_close_pct
        elif tp_level == 2:
            return self.config.tp2_close_pct
        return 0.0
    
    def get_tp_price(
        self,
        entry_price: float,
        atr: float,
        tp_level: int,
        direction: str = "long"
    ) -> float:
        """Calculate price at which TP level triggers.
        
        Args:
            entry_price: Position entry price
            atr: Average True Range value
            tp_level: Take profit level (1 or 2)
            direction: Trade direction
            
        Returns:
            Price at which TP triggers
        """
        if tp_level == 1:
            atr_mult = self.config.tp1_atr_mult
        elif tp_level == 2:
            atr_mult = self.config.tp2_atr_mult
        else:
            return entry_price
        
        profit_distance = atr_mult * atr
        
        if direction == "long":
            return entry_price + profit_distance
        else:
            return entry_price - profit_distance
