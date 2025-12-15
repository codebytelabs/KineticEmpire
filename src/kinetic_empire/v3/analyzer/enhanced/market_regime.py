"""Market Regime Detector for the Enhanced TA System.

Classifies current market conditions based on volatility and price action.
"""

from typing import List, Optional
from dataclasses import dataclass

from .models import MarketRegime, TrendDirection, TrendStrength, TimeframeAnalysis


@dataclass
class OHLCV:
    """Simple OHLCV data structure."""
    open: float
    high: float
    low: float
    close: float
    volume: float


class MarketRegimeDetector:
    """Detects market regime from volatility and price action.
    
    Regime classifications:
    - HIGH_VOLATILITY: ATR > 150% of average
    - LOW_VOLATILITY: ATR < 50% of average
    - SIDEWAYS: Price ranging within 2% for 20 candles
    - TRENDING: Aligned trends with strong momentum
    - CHOPPY: Frequent EMA crossings (detected separately)
    """
    
    # Threshold constants
    HIGH_VOL_THRESHOLD = 1.50  # ATR > 150% of average
    LOW_VOL_THRESHOLD = 0.50   # ATR < 50% of average
    SIDEWAYS_RANGE_PCT = 2.0   # Price range within 2%
    SIDEWAYS_CANDLES = 20      # Number of candles to check for sideways
    
    def detect(
        self,
        analysis_4h: Optional[TimeframeAnalysis],
        analysis_1h: Optional[TimeframeAnalysis],
        ohlcv: List[OHLCV],
        is_choppy: bool = False,
    ) -> MarketRegime:
        """Detect market regime from volatility and price action.
        
        Args:
            analysis_4h: 4H timeframe analysis (optional)
            analysis_1h: 1H timeframe analysis (optional)
            ohlcv: List of OHLCV candles for range detection
            is_choppy: Whether choppy conditions were detected
            
        Returns:
            MarketRegime enum value
        """
        # Choppy takes precedence
        if is_choppy:
            return MarketRegime.CHOPPY
        
        # Check volatility from ATR
        if analysis_4h and analysis_4h.atr_average > 0:
            atr_ratio = analysis_4h.atr / analysis_4h.atr_average
            
            if atr_ratio > self.HIGH_VOL_THRESHOLD:
                return MarketRegime.HIGH_VOLATILITY
            elif atr_ratio < self.LOW_VOL_THRESHOLD:
                return MarketRegime.LOW_VOLATILITY
        
        # Check for sideways (ranging) market
        if self._is_sideways(ohlcv):
            return MarketRegime.SIDEWAYS
        
        # Check for trending market (aligned trends with strong momentum)
        if self._is_trending(analysis_4h, analysis_1h):
            return MarketRegime.TRENDING
        
        # Default to sideways if no clear regime
        return MarketRegime.SIDEWAYS

    
    def _is_sideways(self, ohlcv: List[OHLCV]) -> bool:
        """Check if price is ranging within 2% for recent candles.
        
        Args:
            ohlcv: List of OHLCV candles
            
        Returns:
            True if market is sideways/ranging
        """
        if len(ohlcv) < self.SIDEWAYS_CANDLES:
            return False
        
        recent = ohlcv[-self.SIDEWAYS_CANDLES:]
        
        highest = max(c.high for c in recent)
        lowest = min(c.low for c in recent)
        
        if lowest <= 0:
            return False
        
        range_pct = (highest - lowest) / lowest * 100
        return range_pct <= self.SIDEWAYS_RANGE_PCT
    
    def _is_trending(
        self,
        analysis_4h: Optional[TimeframeAnalysis],
        analysis_1h: Optional[TimeframeAnalysis],
    ) -> bool:
        """Check if market is in a trending state.
        
        Trending requires:
        - Aligned trends across timeframes
        - Strong or moderate trend strength
        - Positive MACD momentum
        
        Args:
            analysis_4h: 4H timeframe analysis
            analysis_1h: 1H timeframe analysis
            
        Returns:
            True if market is trending
        """
        if not analysis_4h or not analysis_1h:
            return False
        
        # Check trend alignment
        trends_aligned = (
            analysis_4h.trend_direction == analysis_1h.trend_direction and
            analysis_4h.trend_direction != TrendDirection.SIDEWAYS
        )
        
        if not trends_aligned:
            return False
        
        # Check trend strength (not weak)
        strong_enough = analysis_4h.trend_strength in (
            TrendStrength.STRONG, 
            TrendStrength.MODERATE
        )
        
        if not strong_enough:
            return False
        
        # Check MACD momentum alignment with trend
        if analysis_4h.trend_direction == TrendDirection.UP:
            momentum_aligned = analysis_4h.macd_histogram > 0
        else:
            momentum_aligned = analysis_4h.macd_histogram < 0
        
        return momentum_aligned
    
    def get_volatility_ratio(self, atr: float, atr_average: float) -> float:
        """Get the ATR to average ratio.
        
        Args:
            atr: Current ATR value
            atr_average: Average ATR value
            
        Returns:
            Ratio of current ATR to average (1.0 = normal)
        """
        if atr_average <= 0:
            return 1.0
        return atr / atr_average
    
    def get_stop_loss_multiplier(self, regime: MarketRegime) -> float:
        """Get stop loss multiplier based on regime.
        
        Args:
            regime: Current market regime
            
        Returns:
            Multiplier for ATR-based stop loss
        """
        multipliers = {
            MarketRegime.TRENDING: 1.5,
            MarketRegime.HIGH_VOLATILITY: 2.5,
            MarketRegime.LOW_VOLATILITY: 1.0,
            MarketRegime.SIDEWAYS: 1.5,
            MarketRegime.CHOPPY: 2.0,
        }
        return multipliers.get(regime, 1.5)
