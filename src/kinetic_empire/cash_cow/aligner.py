"""Multi-Timeframe Alignment module.

Checks trend alignment across multiple timeframes to ensure
trades are in the direction of the larger trend.
"""

from dataclasses import dataclass
from typing import List, Dict


@dataclass
class AlignmentResult:
    """Result of multi-timeframe alignment check."""
    timeframes_checked: List[str]
    aligned_count: int
    daily_conflicts: bool
    alignment_bonus: int
    directions: Dict[str, str]  # timeframe -> direction


class MultiTimeframeAligner:
    """Checks trend alignment across multiple timeframes.
    
    From Requirements 9.1-9.5:
    - Check 5m, 15m, 1h, 4h, daily timeframes
    - 5/5 aligned: +10 points
    - 4/5 aligned: +5 points
    - <3/5 aligned: -10 points
    - Daily conflict: additional -5 points
    """

    TIMEFRAMES = ["5m", "15m", "1h", "4h", "1d"]

    def get_trend_direction(self, ema_fast: float, ema_slow: float) -> str:
        """Determine trend direction from EMA values.
        
        Args:
            ema_fast: Fast EMA value (e.g., EMA9)
            ema_slow: Slow EMA value (e.g., EMA21)
            
        Returns:
            "bullish" if fast > slow, "bearish" otherwise
        """
        if ema_fast > ema_slow:
            return "bullish"
        return "bearish"

    def check_alignment(
        self,
        timeframe_directions: Dict[str, str],
        trade_direction: str
    ) -> AlignmentResult:
        """Check alignment of timeframes with trade direction.
        
        Args:
            timeframe_directions: Dict mapping timeframe to direction
                                  e.g., {"5m": "bullish", "15m": "bullish", ...}
            trade_direction: Intended trade direction ("bullish" or "bearish")
            
        Returns:
            AlignmentResult with alignment metrics and bonus
            
        Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5
        """
        timeframes_checked = list(timeframe_directions.keys())
        
        # Count aligned timeframes
        aligned_count = sum(
            1 for tf, direction in timeframe_directions.items()
            if direction == trade_direction
        )
        
        # Check daily conflict
        daily_direction = timeframe_directions.get("1d", trade_direction)
        daily_conflicts = daily_direction != trade_direction
        
        # Calculate alignment bonus
        alignment_bonus = self.calculate_alignment_bonus(
            aligned_count, 
            len(timeframes_checked),
            daily_conflicts
        )
        
        return AlignmentResult(
            timeframes_checked=timeframes_checked,
            aligned_count=aligned_count,
            daily_conflicts=daily_conflicts,
            alignment_bonus=alignment_bonus,
            directions=timeframe_directions
        )

    def calculate_alignment_bonus(
        self,
        aligned_count: int,
        total_timeframes: int,
        daily_conflicts: bool
    ) -> int:
        """Calculate alignment bonus/penalty.
        
        Args:
            aligned_count: Number of aligned timeframes
            total_timeframes: Total timeframes checked
            daily_conflicts: Whether daily timeframe conflicts
            
        Returns:
            Bonus points (+10, +5, or -10) with optional -5 for daily conflict
            
        Validates: Requirements 9.2, 9.3, 9.4, 9.5
        """
        # Base bonus based on alignment ratio
        if total_timeframes == 0:
            return 0
        
        if aligned_count == total_timeframes:
            bonus = 10  # All aligned
        elif aligned_count >= total_timeframes - 1:
            bonus = 5   # 4 of 5 aligned
        elif aligned_count < 3:
            bonus = -10  # Fewer than 3 aligned
        else:
            bonus = 0   # 3 of 5 aligned (neutral)
        
        # Additional penalty for daily conflict
        if daily_conflicts:
            bonus -= 5
        
        return bonus

    def get_alignment_from_emas(
        self,
        ema_data: Dict[str, tuple],
        trade_direction: str
    ) -> AlignmentResult:
        """Check alignment using EMA data for each timeframe.
        
        Args:
            ema_data: Dict mapping timeframe to (ema_fast, ema_slow) tuple
            trade_direction: Intended trade direction
            
        Returns:
            AlignmentResult
        """
        directions = {}
        for tf, (ema_fast, ema_slow) in ema_data.items():
            directions[tf] = self.get_trend_direction(ema_fast, ema_slow)
        
        return self.check_alignment(directions, trade_direction)
