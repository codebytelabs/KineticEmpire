"""Direction Validator - Validates signal direction against price momentum.

Implements direction validation per profitable-trading-overhaul spec:
- LONG signals rejected if price fell > 0.3% in last 5 candles
- SHORT signals rejected if price rose > 0.3% in last 5 candles
"""

import logging
from dataclasses import dataclass
from typing import List, Tuple


logger = logging.getLogger(__name__)


@dataclass
class OHLCV:
    """Simple OHLCV candle data."""
    open: float
    high: float
    low: float
    close: float
    volume: float


class DirectionValidator:
    """Validates signal direction against recent price momentum.
    
    Per Requirements 5.1-5.4:
    - LONG: Reject if price fell > 0.3% in last 5 candles
    - SHORT: Reject if price rose > 0.3% in last 5 candles
    """
    
    DEFAULT_THRESHOLD_PCT = 0.3
    DEFAULT_CANDLE_COUNT = 5
    
    def validate(
        self,
        direction: str,
        recent_candles: List[OHLCV],
        threshold_pct: float = DEFAULT_THRESHOLD_PCT,
    ) -> Tuple[bool, str]:
        """Validate that price momentum supports signal direction.
        
        Args:
            direction: "LONG" or "SHORT"
            recent_candles: Last 5 candles (most recent last)
            threshold_pct: Max adverse movement allowed (default 0.3%)
            
        Returns:
            (is_valid, reason) tuple
        """
        if not recent_candles or len(recent_candles) < 2:
            return True, "Insufficient candle data for validation"
        
        # Use up to 5 candles
        candles = recent_candles[-self.DEFAULT_CANDLE_COUNT:]
        
        # Calculate price change from first to last candle
        start_price = candles[0].close
        end_price = candles[-1].close
        
        if start_price <= 0:
            return True, "Invalid start price"
        
        price_change_pct = ((end_price - start_price) / start_price) * 100
        
        # Validate based on direction
        if direction.upper() == "LONG":
            # For LONG, reject if price fell more than threshold
            if price_change_pct < -threshold_pct:
                reason = (
                    f"LONG signal rejected: price fell {abs(price_change_pct):.2f}% "
                    f"in last {len(candles)} candles (threshold: {threshold_pct}%)"
                )
                logger.info(reason)
                return False, reason
        elif direction.upper() == "SHORT":
            # For SHORT, reject if price rose more than threshold
            if price_change_pct > threshold_pct:
                reason = (
                    f"SHORT signal rejected: price rose {price_change_pct:.2f}% "
                    f"in last {len(candles)} candles (threshold: {threshold_pct}%)"
                )
                logger.info(reason)
                return False, reason
        
        logger.debug(
            f"Direction validation passed: {direction}, "
            f"price change: {price_change_pct:+.2f}%"
        )
        return True, "Direction validated"
    
    def get_price_momentum(self, recent_candles: List[OHLCV]) -> float:
        """Calculate price momentum as percentage change.
        
        Args:
            recent_candles: Recent candles
            
        Returns:
            Price change percentage (positive = up, negative = down)
        """
        if not recent_candles or len(recent_candles) < 2:
            return 0.0
        
        candles = recent_candles[-self.DEFAULT_CANDLE_COUNT:]
        start_price = candles[0].close
        end_price = candles[-1].close
        
        if start_price <= 0:
            return 0.0
        
        return ((end_price - start_price) / start_price) * 100
