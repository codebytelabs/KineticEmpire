"""ATR-Based Stop Loss Calculator.

Implements volatility-normalized stops per profitable-trading-overhaul spec:
- TRENDING → 2.0x ATR
- SIDEWAYS → 2.5x ATR
- CHOPPY → 3.0x ATR
- Bounded between 1% and 5%
"""

import logging

from .models import MarketRegime, StopLossResult


logger = logging.getLogger(__name__)


class ATRStopCalculator:
    """Calculates stop loss based on ATR and regime.
    
    Per Requirements 4.1-4.6:
    - Stop loss = regime_multiplier × ATR
    - Bounded between 1% minimum and 5% maximum
    """
    
    # ATR multipliers by regime
    REGIME_MULTIPLIERS = {
        MarketRegime.TRENDING: 2.0,
        MarketRegime.SIDEWAYS: 2.5,
        MarketRegime.CHOPPY: 3.0,
    }
    
    # Stop loss bounds
    MIN_STOP_PCT = 0.01  # 1%
    MAX_STOP_PCT = 0.05  # 5%
    
    # Fallback stop if ATR unavailable
    FALLBACK_STOP_PCT = 0.03  # 3%
    
    def calculate(
        self,
        entry_price: float,
        direction: str,
        atr_14: float,
        regime: MarketRegime,
        min_stop_pct: float = MIN_STOP_PCT,
        max_stop_pct: float = MAX_STOP_PCT,
    ) -> StopLossResult:
        """Calculate ATR-based stop loss with min/max bounds.
        
        Args:
            entry_price: Entry price
            direction: "LONG" or "SHORT"
            atr_14: 14-period ATR value
            regime: Market regime
            min_stop_pct: Minimum stop as decimal (default 0.01 = 1%)
            max_stop_pct: Maximum stop as decimal (default 0.05 = 5%)
            
        Returns:
            StopLossResult with stop price and percentage
        """
        # Handle missing ATR
        if atr_14 <= 0:
            logger.warning("ATR unavailable, using fallback stop")
            return self._create_fallback_result(entry_price, direction)
        
        # Get multiplier for regime
        multiplier = self.REGIME_MULTIPLIERS.get(regime, 2.5)
        
        # Calculate raw stop distance
        stop_distance = atr_14 * multiplier
        raw_stop_pct = stop_distance / entry_price
        
        # Apply bounds
        bounded_stop_pct = max(min_stop_pct, min(max_stop_pct, raw_stop_pct))
        bounded_stop_distance = entry_price * bounded_stop_pct
        
        # Calculate stop price based on direction
        if direction.upper() == "LONG":
            stop_price = entry_price - bounded_stop_distance
        else:
            stop_price = entry_price + bounded_stop_distance
        
        result = StopLossResult(
            stop_price=stop_price,
            stop_pct=bounded_stop_pct,
            atr_multiplier=multiplier,
            atr_value=atr_14,
        )
        
        logger.debug(
            f"Stop calculated: {bounded_stop_pct:.2%} @ ${stop_price:.4f} "
            f"(ATR={atr_14:.4f}, mult={multiplier}x, regime={regime.value})"
        )
        
        return result
    
    def _create_fallback_result(self, entry_price: float, direction: str) -> StopLossResult:
        """Create fallback result when ATR is unavailable."""
        stop_distance = entry_price * self.FALLBACK_STOP_PCT
        
        if direction.upper() == "LONG":
            stop_price = entry_price - stop_distance
        else:
            stop_price = entry_price + stop_distance
        
        return StopLossResult(
            stop_price=stop_price,
            stop_pct=self.FALLBACK_STOP_PCT,
            atr_multiplier=0.0,
            atr_value=0.0,
        )
