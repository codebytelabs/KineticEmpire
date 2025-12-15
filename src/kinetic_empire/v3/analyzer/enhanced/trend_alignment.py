"""Trend Alignment Engine for the Enhanced TA System.

Calculates weighted trend alignment across multiple timeframes.
"""

from .models import TrendDirection, TrendAlignment, TIMEFRAME_WEIGHTS


class TrendAlignmentEngine:
    """Calculates weighted trend alignment across timeframes.
    
    Weights:
    - 4H: 50%
    - 1H: 30%
    - 15M: 20%
    
    Bonuses/Penalties:
    - Full alignment bonus: +25 points
    - 4H/1H conflict penalty: -30% confidence
    """
    
    WEIGHTS = TIMEFRAME_WEIGHTS
    ALIGNMENT_BONUS = 25
    CONFLICT_PENALTY_PCT = 30
    
    def calculate_alignment(
        self,
        trend_4h: TrendDirection,
        trend_1h: TrendDirection,
        trend_15m: TrendDirection,
    ) -> TrendAlignment:
        """Calculate weighted trend alignment score.
        
        Args:
            trend_4h: 4H timeframe trend direction
            trend_1h: 1H timeframe trend direction
            trend_15m: 15M timeframe trend direction
            
        Returns:
            TrendAlignment with score, penalties, and bonuses
        """
        # Determine dominant direction (from 4H as it has highest weight)
        dominant = trend_4h
        
        # Calculate alignment score
        score = 0.0
        if trend_4h == dominant:
            score += self.WEIGHTS["4h"]
        if trend_1h == dominant:
            score += self.WEIGHTS["1h"]
        if trend_15m == dominant:
            score += self.WEIGHTS["15m"]

        # Check for full alignment
        all_aligned = (
            trend_4h == trend_1h == trend_15m and
            trend_4h != TrendDirection.SIDEWAYS
        )
        
        # Calculate conflict penalty
        conflict_penalty = 0
        has_4h_1h_conflict = (
            trend_4h != trend_1h and
            trend_4h != TrendDirection.SIDEWAYS and
            trend_1h != TrendDirection.SIDEWAYS
        )
        if has_4h_1h_conflict:
            conflict_penalty = self.CONFLICT_PENALTY_PCT
        
        # Calculate alignment bonus
        alignment_bonus = self.ALIGNMENT_BONUS if all_aligned else 0
        
        return TrendAlignment(
            alignment_score=score,
            is_aligned=all_aligned,
            dominant_direction=dominant,
            conflict_penalty=conflict_penalty,
            alignment_bonus=alignment_bonus,
        )
    
    def can_generate_signal(
        self,
        trend_4h: TrendDirection,
        trend_1h: TrendDirection,
        trend_15m: TrendDirection,
        signal_direction: str,
    ) -> bool:
        """Check if a signal can be generated given trend alignment.
        
        When 4H and 1H conflict, 15M must match 4H for signal generation.
        
        Args:
            trend_4h: 4H timeframe trend direction
            trend_1h: 1H timeframe trend direction
            trend_15m: 15M timeframe trend direction
            signal_direction: "LONG" or "SHORT"
            
        Returns:
            True if signal can be generated
        """
        # Map signal direction to trend direction
        required_trend = (
            TrendDirection.UP if signal_direction == "LONG" 
            else TrendDirection.DOWN
        )
        
        # 4H must support the signal direction
        if trend_4h != required_trend:
            return False
        
        # If 4H and 1H conflict, 15M must match 4H
        if trend_4h != trend_1h:
            return trend_15m == trend_4h
        
        return True
    
    def get_confidence_adjustment(self, alignment: TrendAlignment) -> int:
        """Get total confidence adjustment from alignment.
        
        Args:
            alignment: Calculated trend alignment
            
        Returns:
            Net points to add/subtract from confidence
        """
        adjustment = alignment.alignment_bonus
        if alignment.conflict_penalty > 0:
            # Penalty is a percentage reduction, convert to points
            # Assuming base confidence of 100, 30% = 30 points
            adjustment -= alignment.conflict_penalty
        return adjustment
