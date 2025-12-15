"""Support/Resistance Detector for the Enhanced TA System.

Identifies key price levels and proximity to them.
"""

from typing import List

from .models import SupportResistance
from .market_regime import OHLCV


class SupportResistanceDetector:
    """Detects support and resistance levels from price action.
    
    Thresholds:
    - Proximity: 0.5% of price
    - Support entry bonus: +10 points
    - Resistance entry penalty: -15 points
    """
    
    PROXIMITY_PCT = 0.5  # 0.5% threshold
    SUPPORT_BONUS = 10
    RESISTANCE_PENALTY = 15
    LOOKBACK_CANDLES = 20
    
    def detect(
        self,
        ohlcv: List[OHLCV],
        current_price: float,
        volume_confirmed: bool = False,
    ) -> SupportResistance:
        """Detect support and resistance levels.
        
        Args:
            ohlcv: List of OHLCV candles
            current_price: Current price
            volume_confirmed: Whether volume confirms breakout
            
        Returns:
            SupportResistance with levels and proximity flags
        """
        if len(ohlcv) < 3:
            return SupportResistance(
                nearest_support=current_price * 0.95,
                nearest_resistance=current_price * 1.05,
                at_support=False,
                at_resistance=False,
                is_breakout=False,
                sr_score=0,
            )

        # Find swing highs and lows
        swing_highs = self._find_swing_highs(ohlcv)
        swing_lows = self._find_swing_lows(ohlcv)
        
        # Find nearest levels
        nearest_resistance = self._find_nearest_above(swing_highs, current_price)
        nearest_support = self._find_nearest_below(swing_lows, current_price)
        
        # Check proximity
        at_support = self._is_near(current_price, nearest_support)
        at_resistance = self._is_near(current_price, nearest_resistance)
        
        # Check for breakout
        is_breakout = self._is_breakout(
            current_price, nearest_resistance, volume_confirmed
        )
        
        # Calculate score
        sr_score = self._calculate_score(at_support, at_resistance, is_breakout)
        
        return SupportResistance(
            nearest_support=nearest_support,
            nearest_resistance=nearest_resistance,
            at_support=at_support,
            at_resistance=at_resistance,
            is_breakout=is_breakout,
            sr_score=sr_score,
        )
    
    def _find_swing_highs(self, ohlcv: List[OHLCV]) -> List[float]:
        """Find swing high points."""
        highs = []
        for i in range(1, len(ohlcv) - 1):
            if ohlcv[i].high > ohlcv[i-1].high and ohlcv[i].high > ohlcv[i+1].high:
                highs.append(ohlcv[i].high)
        return highs if highs else [max(c.high for c in ohlcv)]
    
    def _find_swing_lows(self, ohlcv: List[OHLCV]) -> List[float]:
        """Find swing low points."""
        lows = []
        for i in range(1, len(ohlcv) - 1):
            if ohlcv[i].low < ohlcv[i-1].low and ohlcv[i].low < ohlcv[i+1].low:
                lows.append(ohlcv[i].low)
        return lows if lows else [min(c.low for c in ohlcv)]
    
    def _find_nearest_above(self, levels: List[float], price: float) -> float:
        """Find nearest level above price."""
        above = [l for l in levels if l > price]
        return min(above) if above else price * 1.05
    
    def _find_nearest_below(self, levels: List[float], price: float) -> float:
        """Find nearest level below price."""
        below = [l for l in levels if l < price]
        return max(below) if below else price * 0.95
    
    def _is_near(self, price: float, level: float) -> bool:
        """Check if price is within proximity threshold of level."""
        if level <= 0:
            return False
        distance_pct = abs(price - level) / level * 100
        return distance_pct <= self.PROXIMITY_PCT
    
    def _is_breakout(
        self, price: float, resistance: float, volume_confirmed: bool
    ) -> bool:
        """Check if price is breaking through resistance with volume."""
        return price > resistance and volume_confirmed
    
    def _calculate_score(
        self, at_support: bool, at_resistance: bool, is_breakout: bool
    ) -> int:
        """Calculate S/R contribution to confidence score."""
        score = 0
        if at_support:
            score += self.SUPPORT_BONUS
        if at_resistance and not is_breakout:
            score -= self.RESISTANCE_PENALTY
        if is_breakout:
            score += self.SUPPORT_BONUS  # Breakout bonus
        return score
