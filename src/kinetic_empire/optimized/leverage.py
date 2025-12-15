"""Optimized leverage calculator with hard caps and regime adjustments."""

from .models import MarketRegime
from .config import OptimizedConfig, DEFAULT_CONFIG


class OptimizedLeverageCalculator:
    """Calculate leverage with hard caps and regime adjustments."""
    
    def __init__(self, config: OptimizedConfig = DEFAULT_CONFIG):
        self.config = config
    
    def get_tier_leverage(self, confidence: float) -> int:
        """Get leverage based on confidence tier.
        
        Args:
            confidence: Confidence score 0-100
            
        Returns:
            Maximum leverage for the confidence tier
        """
        if confidence < 70:
            return self.config.LEVERAGE_TIER_LOW
        elif confidence < 80:
            return self.config.LEVERAGE_TIER_MID
        elif confidence < 90:
            return self.config.LEVERAGE_TIER_HIGH
        else:
            return self.config.LEVERAGE_TIER_MAX
    
    def calculate_leverage(
        self,
        confidence: float,
        regime: MarketRegime
    ) -> int:
        """Calculate leverage based on confidence and regime.
        
        Args:
            confidence: Confidence score 0-100
            regime: Current market regime
            
        Returns:
            Leverage value (integer), never exceeding hard cap
        """
        if confidence < 0 or confidence > 100:
            raise ValueError("confidence must be between 0 and 100")
        
        # Get base leverage from confidence tier
        base_leverage = self.get_tier_leverage(confidence)
        
        # Apply regime reduction for choppy/volatile markets
        if regime in (MarketRegime.CHOPPY, MarketRegime.HIGH_VOLATILITY):
            base_leverage = int(base_leverage * self.config.LEVERAGE_REGIME_REDUCTION)
            # Ensure at least 1x leverage
            base_leverage = max(1, base_leverage)
        
        # Enforce hard cap
        final_leverage = min(base_leverage, self.config.LEVERAGE_HARD_CAP)
        
        return final_leverage
