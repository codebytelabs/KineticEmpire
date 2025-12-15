"""Momentum Analyzer for the Enhanced TA System.

Analyzes RSI and MACD for momentum confirmation.
"""

from typing import Optional

from .models import MomentumAnalysis


class MomentumAnalyzer:
    """Analyzes momentum using RSI and MACD.
    
    RSI Ranges:
    - LONG: 40-65
    - SHORT: 35-60
    
    MACD Scoring:
    - Positive and increasing histogram: +10 for LONG
    - Negative and decreasing histogram: +10 for SHORT
    
    Divergence:
    - RSI divergence from price: -15 points
    """
    
    # RSI ranges
    LONG_RSI_MIN = 40
    LONG_RSI_MAX = 65
    SHORT_RSI_MIN = 35
    SHORT_RSI_MAX = 60
    
    # Scoring
    MACD_BONUS = 10
    DIVERGENCE_PENALTY = 15
    
    def analyze(
        self,
        rsi: float,
        macd_histogram: float,
        prev_macd_histogram: Optional[float],
        signal_direction: str,
        has_divergence: bool = False,
    ) -> MomentumAnalysis:
        """Analyze momentum indicators.
        
        Args:
            rsi: Current RSI value
            macd_histogram: Current MACD histogram value
            prev_macd_histogram: Previous MACD histogram value
            signal_direction: "LONG" or "SHORT"
            has_divergence: Whether RSI divergence detected

        Returns:
            MomentumAnalysis with RSI validity and MACD score
        """
        # Check RSI validity for signal direction
        rsi_valid = self._is_rsi_valid(rsi, signal_direction)
        
        # Calculate MACD score
        macd_score = self._calculate_macd_score(
            macd_histogram, prev_macd_histogram, signal_direction
        )
        
        # Calculate total momentum score
        momentum_score = macd_score
        if has_divergence:
            momentum_score -= self.DIVERGENCE_PENALTY
        
        return MomentumAnalysis(
            rsi_valid=rsi_valid,
            macd_score=macd_score,
            has_divergence=has_divergence,
            momentum_score=momentum_score,
        )
    
    def _is_rsi_valid(self, rsi: float, signal_direction: str) -> bool:
        """Check if RSI is in valid range for signal direction.
        
        Args:
            rsi: Current RSI value
            signal_direction: "LONG" or "SHORT"
            
        Returns:
            True if RSI is in valid range
        """
        if signal_direction == "LONG":
            return self.LONG_RSI_MIN <= rsi <= self.LONG_RSI_MAX
        else:
            return self.SHORT_RSI_MIN <= rsi <= self.SHORT_RSI_MAX
    
    def _calculate_macd_score(
        self,
        macd_histogram: float,
        prev_macd_histogram: Optional[float],
        signal_direction: str,
    ) -> int:
        """Calculate MACD contribution to momentum score.
        
        Args:
            macd_histogram: Current MACD histogram
            prev_macd_histogram: Previous MACD histogram
            signal_direction: "LONG" or "SHORT"
            
        Returns:
            Points from MACD analysis
        """
        if prev_macd_histogram is None:
            return 0
        
        if signal_direction == "LONG":
            # Positive and increasing histogram = bullish
            if macd_histogram > 0 and macd_histogram > prev_macd_histogram:
                return self.MACD_BONUS
        else:
            # Negative and decreasing histogram = bearish
            if macd_histogram < 0 and macd_histogram < prev_macd_histogram:
                return self.MACD_BONUS
        
        return 0
    
    def get_rsi_range(self, signal_direction: str) -> tuple:
        """Get valid RSI range for signal direction.
        
        Args:
            signal_direction: "LONG" or "SHORT"
            
        Returns:
            Tuple of (min, max) RSI values
        """
        if signal_direction == "LONG":
            return (self.LONG_RSI_MIN, self.LONG_RSI_MAX)
        return (self.SHORT_RSI_MIN, self.SHORT_RSI_MAX)
