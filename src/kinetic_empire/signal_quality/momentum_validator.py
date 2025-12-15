"""Momentum Validator for Signal Quality Gate.

Validates that recent price momentum supports the signal direction.
"""

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .config import QualityGateConfig


logger = logging.getLogger(__name__)


@dataclass
class OHLCV:
    """Simple OHLCV candle data."""
    open: float
    high: float
    low: float
    close: float
    volume: float


class MomentumValidator:
    """Validates recent price momentum supports signal direction.
    
    Checks:
    - 3-candle price change doesn't contradict direction by >0.5%
    - RSI not overbought for LONG (>70)
    - RSI not oversold for SHORT (<30)
    """
    
    def __init__(self, config: QualityGateConfig):
        """Initialize with configuration.
        
        Args:
            config: Quality gate configuration
        """
        self.config = config
    
    def validate(
        self,
        direction: str,
        ohlcv_15m: List[OHLCV],
        rsi_15m: float,
    ) -> Tuple[bool, Optional[str]]:
        """Validate momentum supports signal direction.
        
        Args:
            direction: Signal direction ("LONG" or "SHORT")
            ohlcv_15m: List of 15M OHLCV candles (need at least 3)
            rsi_15m: Current 15M RSI value
            
        Returns:
            Tuple of (valid, rejection_reason):
            - valid: Whether momentum supports the signal
            - rejection_reason: Why signal was rejected (if applicable)
        """
        direction = direction.upper()
        
        # Check 3-candle price change
        if len(ohlcv_15m) >= 3:
            price_change = self._calculate_3_candle_change(ohlcv_15m)
            
            if direction == "LONG" and price_change < -self.config.contradiction_threshold_pct:
                reason = f"Price dropped {abs(price_change):.2f}% in last 3 candles, contradicts LONG"
                logger.debug(reason)
                return (False, reason)
            
            if direction == "SHORT" and price_change > self.config.contradiction_threshold_pct:
                reason = f"Price rose {price_change:.2f}% in last 3 candles, contradicts SHORT"
                logger.debug(reason)
                return (False, reason)
        
        # Check RSI overbought/oversold (can be disabled for trending markets)
        if not self.config.disable_rsi_extreme_filter:
            if direction == "LONG" and rsi_15m > self.config.overbought_rsi:
                reason = f"RSI {rsi_15m:.1f} is overbought (>{self.config.overbought_rsi}), rejecting LONG"
                logger.debug(reason)
                return (False, reason)
            
            if direction == "SHORT" and rsi_15m < self.config.oversold_rsi:
                reason = f"RSI {rsi_15m:.1f} is oversold (<{self.config.oversold_rsi}), rejecting SHORT"
                logger.debug(reason)
                return (False, reason)
        else:
            logger.debug(f"RSI extreme filter disabled, allowing RSI {rsi_15m:.1f}")
        
        return (True, None)
    
    def _calculate_3_candle_change(self, ohlcv: List[OHLCV]) -> float:
        """Calculate price change over last 3 candles.
        
        Args:
            ohlcv: List of OHLCV candles
            
        Returns:
            Percentage price change (positive = up, negative = down)
        """
        if len(ohlcv) < 3:
            return 0.0
        
        start_price = ohlcv[-3].close
        end_price = ohlcv[-1].close
        
        if start_price == 0:
            return 0.0
        
        return ((end_price - start_price) / start_price) * 100
