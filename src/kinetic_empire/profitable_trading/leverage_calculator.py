"""Regime-Based Leverage Calculator.

Implements adaptive leverage per profitable-trading-overhaul spec:
- TRENDING + 90-100 confidence → 10x
- TRENDING + 70-89 confidence → 7x
- TRENDING + 50-69 confidence → 5x
- SIDEWAYS → 3x max
- CHOPPY → 2x max
- After 2+ consecutive losses → reduce by 50%
"""

import logging

from .models import MarketRegime


logger = logging.getLogger(__name__)


class RegimeLeverageCalculator:
    """Calculates leverage based on regime and confidence.
    
    Per Requirements 3.1-3.6:
    - Leverage scales with regime and confidence
    - Reduced by 50% after 2+ consecutive losses
    """
    
    # Leverage limits
    MIN_LEVERAGE = 2
    MAX_LEVERAGE = 10
    
    # Regime-based max leverage
    REGIME_MAX_LEVERAGE = {
        MarketRegime.TRENDING: 10,
        MarketRegime.SIDEWAYS: 3,
        MarketRegime.CHOPPY: 2,
    }
    
    # Confidence thresholds for TRENDING regime
    HIGH_CONFIDENCE = 90
    MEDIUM_CONFIDENCE = 70
    
    # Loss reduction
    LOSS_THRESHOLD = 2
    LOSS_REDUCTION = 0.5  # 50% reduction
    
    def calculate(
        self,
        regime: MarketRegime,
        confidence: int,
        consecutive_losses: int = 0,
    ) -> int:
        """Calculate leverage based on regime and confidence.
        
        Args:
            regime: Current market regime
            confidence: Signal confidence (0-100)
            consecutive_losses: Number of consecutive losses
            
        Returns:
            Leverage multiplier (2-10)
        """
        # Get base leverage for regime
        base_leverage = self._get_base_leverage(regime, confidence)
        
        # Apply loss reduction if needed
        if consecutive_losses >= self.LOSS_THRESHOLD:
            reduced = int(base_leverage * self.LOSS_REDUCTION)
            final_leverage = max(self.MIN_LEVERAGE, reduced)
            logger.info(
                f"Leverage reduced due to {consecutive_losses} losses: "
                f"{base_leverage}x → {final_leverage}x"
            )
        else:
            final_leverage = base_leverage
        
        logger.debug(
            f"Leverage calculated: {final_leverage}x "
            f"(regime={regime.value}, confidence={confidence}, losses={consecutive_losses})"
        )
        
        return final_leverage
    
    def _get_base_leverage(self, regime: MarketRegime, confidence: int) -> int:
        """Get base leverage before loss reduction.
        
        Args:
            regime: Market regime
            confidence: Signal confidence
            
        Returns:
            Base leverage multiplier
        """
        max_for_regime = self.REGIME_MAX_LEVERAGE.get(regime, self.MIN_LEVERAGE)
        
        if regime == MarketRegime.TRENDING:
            # Scale leverage with confidence in trending markets
            if confidence >= self.HIGH_CONFIDENCE:
                return min(10, max_for_regime)
            elif confidence >= self.MEDIUM_CONFIDENCE:
                return min(7, max_for_regime)
            else:
                return min(5, max_for_regime)
        else:
            # Use regime max for non-trending
            return max_for_regime
