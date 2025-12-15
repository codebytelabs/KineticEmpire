"""Micro Timeframe Analyzer for Signal Quality Gate.

Analyzes 1M and 5M charts for precise entry timing.
"""

import logging
from typing import List

from .config import QualityGateConfig
from .models import MicroAnalysisResult
from .momentum_validator import OHLCV


logger = logging.getLogger(__name__)


class MicroTimeframeAnalyzer:
    """Analyzes 1M and 5M timeframes for entry timing.
    
    Calculates EMA9/EMA21 crossover on both timeframes to determine
    micro-trend direction. Adds bonus when aligned, rejects when contradicting.
    """
    
    def __init__(self, config: QualityGateConfig):
        """Initialize with configuration.
        
        Args:
            config: Quality gate configuration
        """
        self.config = config
    
    def analyze(
        self,
        ohlcv_1m: List[OHLCV],
        ohlcv_5m: List[OHLCV],
        signal_direction: str,
    ) -> MicroAnalysisResult:
        """Analyze 1M and 5M trends for entry timing.
        
        Args:
            ohlcv_1m: List of 1M OHLCV candles
            ohlcv_5m: List of 5M OHLCV candles
            signal_direction: Signal direction ("LONG" or "SHORT")
            
        Returns:
            MicroAnalysisResult with trend info and bonus/rejection
        """
        signal_direction = signal_direction.upper()
        
        # Calculate trends
        trend_1m = self._calculate_trend(ohlcv_1m)
        trend_5m = self._calculate_trend(ohlcv_5m)
        
        # Check alignment
        expected_trend = "UP" if signal_direction == "LONG" else "DOWN"
        
        aligned_1m = trend_1m == expected_trend
        aligned_5m = trend_5m == expected_trend
        
        micro_aligned = aligned_1m and aligned_5m
        
        # Check for contradiction (against signal)
        contradicts_1m = (
            (signal_direction == "LONG" and trend_1m == "DOWN") or
            (signal_direction == "SHORT" and trend_1m == "UP")
        )
        contradicts_5m = (
            (signal_direction == "LONG" and trend_5m == "DOWN") or
            (signal_direction == "SHORT" and trend_5m == "UP")
        )
        
        # RELAXED: Only reject if BOTH timeframes contradict (configurable)
        if self.config.require_both_micro_contradict:
            # Both must contradict to reject - more permissive
            should_reject = contradicts_1m and contradicts_5m
        else:
            # Either contradicting rejects - more strict (old behavior)
            should_reject = contradicts_1m or contradicts_5m
        
        # Calculate bonus
        micro_bonus = self.config.micro_alignment_bonus if micro_aligned else 0
        
        if should_reject:
            logger.debug(
                f"Micro-timeframe contradiction: 1M={trend_1m}, 5M={trend_5m}, "
                f"signal={signal_direction}"
            )
        elif micro_aligned:
            logger.debug(
                f"Micro-timeframe aligned: 1M={trend_1m}, 5M={trend_5m}, "
                f"bonus={micro_bonus}"
            )
        
        return MicroAnalysisResult(
            trend_1m=trend_1m,
            trend_5m=trend_5m,
            micro_aligned=micro_aligned,
            micro_bonus=micro_bonus,
            should_reject=should_reject,
        )
    
    def _calculate_trend(self, ohlcv: List[OHLCV]) -> str:
        """Calculate trend direction using EMA9/EMA21 crossover.
        
        Args:
            ohlcv: List of OHLCV candles
            
        Returns:
            Trend direction: "UP", "DOWN", or "SIDEWAYS"
        """
        if len(ohlcv) < 21:
            return "SIDEWAYS"
        
        closes = [c.close for c in ohlcv]
        
        ema_9 = self._calculate_ema(closes, 9)
        ema_21 = self._calculate_ema(closes, 21)
        
        # Determine trend based on EMA relationship
        diff_pct = (ema_9 - ema_21) / ema_21 * 100 if ema_21 > 0 else 0
        
        if diff_pct > 0.1:  # EMA9 > EMA21 by 0.1%
            return "UP"
        elif diff_pct < -0.1:  # EMA9 < EMA21 by 0.1%
            return "DOWN"
        else:
            return "SIDEWAYS"
    
    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average.
        
        Args:
            prices: List of prices
            period: EMA period
            
        Returns:
            EMA value
        """
        if len(prices) < period:
            return prices[-1] if prices else 0
        
        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period  # Start with SMA
        
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
