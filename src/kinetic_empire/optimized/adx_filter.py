"""Optimized ADX filter with enhanced thresholds."""

from .models import MarketRegime, ADXResult
from .config import OptimizedConfig, DEFAULT_CONFIG


class OptimizedADXFilter:
    """Evaluates trend strength with optimized thresholds."""
    
    def __init__(self, config: OptimizedConfig = DEFAULT_CONFIG):
        self.config = config
    
    def evaluate_trend(self, adx: float) -> ADXResult:
        """Evaluate ADX for trend classification.
        
        Args:
            adx: Current ADX value (0-100)
            
        Returns:
            ADXResult with regime classification and adjustments
        """
        if adx < 0:
            raise ValueError("adx must be non-negative")
        
        confidence_bonus = 0
        position_size_multiplier = 1.0
        
        # Classify regime based on ADX
        if adx < self.config.ADX_SIDEWAYS_THRESHOLD:
            regime = MarketRegime.SIDEWAYS
            is_trending = False
        elif adx < self.config.ADX_TRENDING_THRESHOLD:
            # Weak trend zone - reduce position size
            regime = MarketRegime.SIDEWAYS  # Treat as sideways for safety
            is_trending = False
            position_size_multiplier = 1.0 - self.config.ADX_WEAK_TREND_REDUCTION
        else:
            regime = MarketRegime.TRENDING
            is_trending = True
            
            # Strong trend bonus
            if adx > self.config.ADX_STRONG_TREND_THRESHOLD:
                confidence_bonus = self.config.ADX_STRONG_TREND_BONUS
        
        return ADXResult(
            regime=regime,
            position_size_multiplier=position_size_multiplier,
            confidence_bonus=confidence_bonus,
            is_trending=is_trending
        )
