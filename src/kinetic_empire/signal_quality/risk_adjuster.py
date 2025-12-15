"""Risk Adjuster for Signal Quality Gate.

Calculates regime-adaptive stop losses and leverage caps.
"""

import logging
from enum import Enum

from .config import QualityGateConfig


logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    """Market regime classification."""
    TRENDING = "TRENDING"
    SIDEWAYS = "SIDEWAYS"
    CHOPPY = "CHOPPY"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"


class RiskAdjuster:
    """Calculates regime-adaptive stop losses and leverage caps.
    
    Stop loss percentages:
    - TRENDING: 3%
    - SIDEWAYS: 4%
    - CHOPPY: 5%
    
    Leverage caps:
    - Unfavorable (CHOPPY/SIDEWAYS or confidence < 60): 10x
    - Favorable (TRENDING and confidence >= 70): 20x
    """
    
    def __init__(self, config: QualityGateConfig):
        """Initialize with configuration.
        
        Args:
            config: Quality gate configuration
        """
        self.config = config
    
    def calculate_stop_loss(self, regime: MarketRegime) -> float:
        """Calculate stop loss percentage based on market regime.
        
        Args:
            regime: Current market regime
            
        Returns:
            Stop loss percentage (e.g., 3.0 for 3%)
        """
        if regime == MarketRegime.CHOPPY:
            stop_pct = self.config.choppy_stop_pct
        elif regime == MarketRegime.SIDEWAYS:
            stop_pct = self.config.sideways_stop_pct
        else:
            # TRENDING, HIGH_VOLATILITY, LOW_VOLATILITY all use trending stop
            stop_pct = self.config.trending_stop_pct
        
        logger.debug(f"Regime {regime.value}: using {stop_pct}% stop loss")
        return stop_pct
    
    def calculate_max_leverage(self, regime: MarketRegime, confidence: int) -> int:
        """Calculate maximum allowed leverage.
        
        Args:
            regime: Current market regime
            confidence: Enhanced TA confidence score
            
        Returns:
            Maximum leverage multiplier (e.g., 10 or 20)
        """
        # Check unfavorable conditions
        is_unfavorable_regime = regime in (MarketRegime.CHOPPY, MarketRegime.SIDEWAYS)
        is_low_confidence = confidence < 60
        
        if is_unfavorable_regime or is_low_confidence:
            max_lev = self.config.max_leverage_unfavorable
            reason = "unfavorable regime" if is_unfavorable_regime else "low confidence"
            logger.debug(f"Capping leverage at {max_lev}x due to {reason}")
            return max_lev
        
        # Check favorable conditions
        is_trending = regime == MarketRegime.TRENDING
        is_high_confidence = confidence >= self.config.favorable_confidence_threshold
        
        if is_trending and is_high_confidence:
            max_lev = self.config.max_leverage_favorable
            logger.debug(f"Allowing {max_lev}x leverage (favorable conditions)")
            return max_lev
        
        # Default to unfavorable
        return self.config.max_leverage_unfavorable
    
    def is_favorable(self, regime: MarketRegime, confidence: int) -> bool:
        """Check if conditions are favorable for trading.
        
        Args:
            regime: Current market regime
            confidence: Enhanced TA confidence score
            
        Returns:
            True if conditions are favorable
        """
        return (
            regime == MarketRegime.TRENDING and
            confidence >= self.config.favorable_confidence_threshold
        )
