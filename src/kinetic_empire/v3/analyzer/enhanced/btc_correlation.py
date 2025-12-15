"""BTC Correlation Engine for the Enhanced TA System.

Adjusts altcoin signals based on BTC market conditions.
"""

from typing import Optional

from .models import TrendDirection, TrendStrength, TimeframeAnalysis


class BTCCorrelationEngine:
    """Analyzes BTC trend for altcoin correlation adjustments.
    
    Adjustments:
    - BTC strongly DOWN: -20 points for LONG altcoin signals
    - BTC strongly UP: -20 points for SHORT altcoin signals
    - BTC extreme volatility (ATR > 200%): pause all altcoin signals
    """
    
    CORRELATION_ADJUSTMENT = 20
    EXTREME_VOL_THRESHOLD = 2.0  # 200% of average
    
    def __init__(self):
        self._btc_analysis: Optional[TimeframeAnalysis] = None
    
    def update_btc_analysis(self, analysis: TimeframeAnalysis):
        """Update BTC 4H analysis.
        
        Args:
            analysis: BTC 4H timeframe analysis
        """
        self._btc_analysis = analysis
    
    def get_confidence_adjustment(
        self,
        signal_direction: str,
        is_altcoin: bool = True,
    ) -> int:
        """Get confidence adjustment based on BTC correlation.
        
        Args:
            signal_direction: "LONG" or "SHORT"
            is_altcoin: Whether the symbol is an altcoin
            
        Returns:
            Points to add/subtract from confidence
        """
        if not is_altcoin or not self._btc_analysis:
            return 0

        btc_trend = self._btc_analysis.trend_direction
        btc_strength = self._btc_analysis.trend_strength
        
        # Only adjust for strong BTC trends
        if btc_strength != TrendStrength.STRONG:
            return 0
        
        # BTC strongly DOWN reduces LONG confidence
        if btc_trend == TrendDirection.DOWN and signal_direction == "LONG":
            return -self.CORRELATION_ADJUSTMENT
        
        # BTC strongly UP reduces SHORT confidence
        if btc_trend == TrendDirection.UP and signal_direction == "SHORT":
            return -self.CORRELATION_ADJUSTMENT
        
        return 0
    
    def should_pause_altcoin_signals(self) -> bool:
        """Check if altcoin signals should be paused due to BTC volatility.
        
        Returns:
            True if BTC ATR > 200% of average
        """
        if not self._btc_analysis:
            return False
        
        if self._btc_analysis.atr_average <= 0:
            return False
        
        atr_ratio = self._btc_analysis.atr / self._btc_analysis.atr_average
        return atr_ratio > self.EXTREME_VOL_THRESHOLD
    
    def get_btc_trend(self) -> Optional[TrendDirection]:
        """Get current BTC trend direction.
        
        Returns:
            BTC trend direction or None if not available
        """
        if not self._btc_analysis:
            return None
        return self._btc_analysis.trend_direction
    
    def is_btc_data_available(self) -> bool:
        """Check if BTC data is available.
        
        Returns:
            True if BTC analysis is available
        """
        return self._btc_analysis is not None
