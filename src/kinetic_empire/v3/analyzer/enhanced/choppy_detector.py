"""Choppy Market Detector for the Enhanced TA System.

Detects choppy/whipsaw market conditions.
"""

from typing import List

from .models import TrendStrength
from .market_regime import OHLCV


class ChoppyMarketDetector:
    """Detects choppy market conditions.
    
    Criteria:
    - EMA crossings: >4 in 20 candles = CHOPPY
    - ADX < 20 = WEAK trend regardless of EMA alignment
    - Signal alternation: LONG/SHORT within 5 candles = pause
    """
    
    EMA_CROSSING_THRESHOLD = 4
    LOOKBACK_CANDLES = 20
    ADX_WEAK_THRESHOLD = 20
    SIGNAL_ALTERNATION_CANDLES = 5
    PAUSE_CANDLES = 10
    
    def __init__(self):
        self._recent_signals: List[str] = []
        self._pause_counter: int = 0
    
    def is_choppy(
        self,
        prices: List[float],
        ema_9_values: List[float],
    ) -> bool:
        """Check if market is choppy based on EMA crossings.
        
        Args:
            prices: Recent close prices
            ema_9_values: Recent EMA9 values
            
        Returns:
            True if market is choppy (>4 crossings in 20 candles)
        """
        if len(prices) < self.LOOKBACK_CANDLES or len(ema_9_values) < self.LOOKBACK_CANDLES:
            return False
        
        recent_prices = prices[-self.LOOKBACK_CANDLES:]
        recent_ema = ema_9_values[-self.LOOKBACK_CANDLES:]

        crossings = self._count_ema_crossings(recent_prices, recent_ema)
        return crossings > self.EMA_CROSSING_THRESHOLD
    
    def _count_ema_crossings(
        self,
        prices: List[float],
        ema_values: List[float],
    ) -> int:
        """Count number of times price crosses EMA.
        
        Args:
            prices: Close prices
            ema_values: EMA values
            
        Returns:
            Number of crossings
        """
        crossings = 0
        for i in range(1, len(prices)):
            prev_above = prices[i-1] > ema_values[i-1]
            curr_above = prices[i] > ema_values[i]
            if prev_above != curr_above:
                crossings += 1
        return crossings
    
    def get_trend_strength_override(self, adx: float) -> TrendStrength:
        """Get trend strength based on ADX override.
        
        Args:
            adx: ADX indicator value
            
        Returns:
            TrendStrength.WEAK if ADX < 20, else None for no override
        """
        if adx < self.ADX_WEAK_THRESHOLD:
            return TrendStrength.WEAK
        return None
    
    def should_pause_signals(self, new_signal: str) -> bool:
        """Check if signals should be paused due to alternation.
        
        Args:
            new_signal: "LONG" or "SHORT"
            
        Returns:
            True if signals should be paused
        """
        if self._pause_counter > 0:
            self._pause_counter -= 1
            return True
        
        self._recent_signals.append(new_signal)
        if len(self._recent_signals) > self.SIGNAL_ALTERNATION_CANDLES:
            self._recent_signals.pop(0)
        
        # Check for alternation
        if len(self._recent_signals) >= 2:
            alternations = 0
            for i in range(1, len(self._recent_signals)):
                if self._recent_signals[i] != self._recent_signals[i-1]:
                    alternations += 1
            
            if alternations >= 2:  # Multiple alternations
                self._pause_counter = self.PAUSE_CANDLES
                self._recent_signals.clear()
                return True
        
        return False
    
    def reset_pause(self):
        """Reset the pause counter."""
        self._pause_counter = 0
        self._recent_signals.clear()
