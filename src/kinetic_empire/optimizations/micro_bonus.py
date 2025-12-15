"""Micro-Timeframe Alignment Bonus.

Rewards high-quality setups where micro-timeframes (1M, 5M) align with signal.
"""

from typing import Optional, Tuple

from .config import MicroBonusConfig


class MicroAlignmentBonus:
    """Provides bonuses for micro-timeframe alignment.
    
    When 1M and 5M trends both align with signal direction:
    - Position size bonus: +5%
    - Stop distance reduction: -0.5x ATR
    
    When micro-timeframes contradict signal:
    - Signal is rejected
    """
    
    def __init__(self, config: Optional[MicroBonusConfig] = None):
        """Initialize micro alignment bonus.
        
        Args:
            config: Micro bonus configuration. Uses defaults if None.
        """
        self.config = config or MicroBonusConfig()
    
    def check_alignment(
        self,
        trend_1m: str,
        trend_5m: str,
        signal_direction: str
    ) -> bool:
        """Check if micro-timeframes align with signal.
        
        Args:
            trend_1m: 1-minute trend direction ("up", "down", "neutral")
            trend_5m: 5-minute trend direction
            signal_direction: Signal direction ("long" or "short")
            
        Returns:
            True if both micro-timeframes align with signal
        """
        # Normalize inputs
        trend_1m = trend_1m.lower()
        trend_5m = trend_5m.lower()
        signal_direction = signal_direction.lower()
        
        # Determine expected trend direction
        if signal_direction in ("long", "buy"):
            expected = "up"
        elif signal_direction in ("short", "sell"):
            expected = "down"
        else:
            return False
        
        return trend_1m == expected and trend_5m == expected
    
    def should_reject(
        self,
        trend_1m: str,
        trend_5m: str,
        signal_direction: str
    ) -> bool:
        """Check if signal should be rejected due to contradiction.
        
        Rejects when micro-timeframes actively contradict signal.
        
        Args:
            trend_1m: 1-minute trend direction
            trend_5m: 5-minute trend direction
            signal_direction: Signal direction
            
        Returns:
            True if signal should be rejected
        """
        # Normalize inputs
        trend_1m = trend_1m.lower()
        trend_5m = trend_5m.lower()
        signal_direction = signal_direction.lower()
        
        # Determine opposite direction
        if signal_direction in ("long", "buy"):
            opposite = "down"
        elif signal_direction in ("short", "sell"):
            opposite = "up"
        else:
            return False
        
        # Reject if both micro-timeframes are opposite
        return trend_1m == opposite and trend_5m == opposite
    
    def get_size_bonus(self, is_aligned: bool) -> float:
        """Get position size bonus for alignment.
        
        Args:
            is_aligned: Whether micro-timeframes are aligned
            
        Returns:
            Size bonus as decimal (0.05 = 5% increase)
        """
        if is_aligned:
            return self.config.size_bonus
        return 0.0
    
    def get_stop_reduction(self, is_aligned: bool) -> float:
        """Get stop distance reduction for alignment.
        
        Args:
            is_aligned: Whether micro-timeframes are aligned
            
        Returns:
            ATR reduction (0.5 = reduce stop by 0.5x ATR)
        """
        if is_aligned:
            return self.config.stop_reduction
        return 0.0
    
    def adjust_position_size(
        self,
        base_size: float,
        trend_1m: str,
        trend_5m: str,
        signal_direction: str
    ) -> float:
        """Adjust position size based on micro alignment.
        
        Args:
            base_size: Base position size
            trend_1m: 1-minute trend direction
            trend_5m: 5-minute trend direction
            signal_direction: Signal direction
            
        Returns:
            Adjusted position size
        """
        is_aligned = self.check_alignment(trend_1m, trend_5m, signal_direction)
        bonus = self.get_size_bonus(is_aligned)
        return base_size * (1 + bonus)
    
    def adjust_stop_multiplier(
        self,
        base_mult: float,
        trend_1m: str,
        trend_5m: str,
        signal_direction: str
    ) -> float:
        """Adjust stop ATR multiplier based on micro alignment.
        
        Args:
            base_mult: Base ATR multiplier
            trend_1m: 1-minute trend direction
            trend_5m: 5-minute trend direction
            signal_direction: Signal direction
            
        Returns:
            Adjusted ATR multiplier
        """
        is_aligned = self.check_alignment(trend_1m, trend_5m, signal_direction)
        reduction = self.get_stop_reduction(is_aligned)
        return max(0.5, base_mult - reduction)  # Minimum 0.5x ATR
    
    def evaluate(
        self,
        trend_1m: str,
        trend_5m: str,
        signal_direction: str
    ) -> Tuple[bool, bool, str]:
        """Evaluate micro-timeframe alignment.
        
        Args:
            trend_1m: 1-minute trend direction
            trend_5m: 5-minute trend direction
            signal_direction: Signal direction
            
        Returns:
            Tuple of (is_aligned, should_reject, reason)
        """
        is_aligned = self.check_alignment(trend_1m, trend_5m, signal_direction)
        reject = self.should_reject(trend_1m, trend_5m, signal_direction)
        
        if reject:
            reason = f"Micro-timeframes ({trend_1m}, {trend_5m}) contradict {signal_direction}"
        elif is_aligned:
            reason = f"Micro-timeframes aligned with {signal_direction}"
        else:
            reason = "Micro-timeframes neutral"
        
        return (is_aligned, reject, reason)
