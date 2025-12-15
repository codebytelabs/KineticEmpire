"""Regime Detector - ADX-based market regime classification.

Implements improved regime detection per profitable-trading-overhaul spec:
- ADX > 25 → TRENDING
- 15 <= ADX <= 25 → SIDEWAYS  
- ADX < 15 → CHOPPY
"""

import logging
from typing import Tuple

from .models import MarketRegime, TrendDirection, RegimeAnalysis


logger = logging.getLogger(__name__)


class RegimeDetector:
    """Detects market regime using ADX thresholds.
    
    ADX Thresholds (per Requirements 9.1-9.4):
    - ADX > 25: TRENDING (strong directional movement)
    - 15 <= ADX <= 25: SIDEWAYS (weak trend, range-bound)
    - ADX < 15: CHOPPY (no clear direction, avoid trading)
    """
    
    # ADX thresholds per spec
    TRENDING_THRESHOLD = 25.0
    SIDEWAYS_THRESHOLD = 15.0
    
    def detect(self, adx: float, price: float, ma_50: float) -> RegimeAnalysis:
        """Detect market regime based on ADX and price/MA relationship.
        
        Args:
            adx: 14-period ADX value
            price: Current price
            ma_50: 50-period moving average
            
        Returns:
            RegimeAnalysis with regime, direction, and metrics
        """
        # Determine regime from ADX
        regime = self._classify_regime(adx)
        
        # Determine trend direction from price vs MA
        trend_direction = self.get_trend_direction(price, ma_50)
        
        # Calculate price vs MA percentage
        price_vs_ma = ((price - ma_50) / ma_50 * 100) if ma_50 > 0 else 0.0
        
        analysis = RegimeAnalysis(
            regime=regime,
            trend_direction=trend_direction,
            adx_value=adx,
            price_vs_ma=price_vs_ma,
        )
        
        logger.debug(
            f"Regime detected: {regime.value} (ADX={adx:.1f}), "
            f"Direction: {trend_direction.value} (price vs MA: {price_vs_ma:+.2f}%)"
        )
        
        return analysis
    
    def _classify_regime(self, adx: float) -> MarketRegime:
        """Classify regime based on ADX value.
        
        Args:
            adx: ADX value
            
        Returns:
            MarketRegime enum
        """
        if adx > self.TRENDING_THRESHOLD:
            return MarketRegime.TRENDING
        elif adx >= self.SIDEWAYS_THRESHOLD:
            return MarketRegime.SIDEWAYS
        else:
            return MarketRegime.CHOPPY
    
    def get_trend_direction(self, price: float, ma_50: float) -> TrendDirection:
        """Determine trend direction based on price vs 50-MA.
        
        Args:
            price: Current price
            ma_50: 50-period moving average
            
        Returns:
            TrendDirection enum (BULLISH, BEARISH, or NEUTRAL)
        """
        if ma_50 <= 0:
            return TrendDirection.NEUTRAL
        
        # Use 0.1% threshold for neutral zone
        pct_diff = (price - ma_50) / ma_50 * 100
        
        if pct_diff > 0.1:
            return TrendDirection.BULLISH
        elif pct_diff < -0.1:
            return TrendDirection.BEARISH
        else:
            return TrendDirection.NEUTRAL
    
    def is_favorable_regime(self, regime: MarketRegime) -> bool:
        """Check if regime is favorable for directional trading.
        
        Args:
            regime: Market regime
            
        Returns:
            True only for TRENDING regime
        """
        return regime == MarketRegime.TRENDING
