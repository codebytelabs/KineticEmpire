"""Confidence-Based Position Sizer.

Implements aggressive position sizing per aggressive-capital-deployment spec:
- 90-100 confidence → 20% position
- 80-89 confidence → 18% position
- 70-79 confidence → 15% position
- 60-69 confidence → 12% position
- Regime-aware minimum confidence:
  - TRENDING: 60 minimum
  - SIDEWAYS/CHOPPY: 65 minimum (more selective)
"""

import logging
from typing import Optional

from .models import PositionSizeResult


logger = logging.getLogger(__name__)


class ConfidencePositionSizer:
    """Calculates position size based on confidence score with regime awareness.
    
    Per aggressive-capital-deployment Requirements 2.1-2.4, 4.1-4.2:
    - Position size scales with confidence (12-20%)
    - Regime-aware minimum confidence (60 trending, 65 sideways/choppy)
    """
    
    # Aggressive confidence to position size mapping
    CONFIDENCE_TO_SIZE = {
        (90, 100): 0.20,  # 20%
        (80, 89): 0.18,   # 18%
        (70, 79): 0.15,   # 15%
        (60, 69): 0.12,   # 12%
    }
    
    # Regime-aware minimum confidence thresholds
    MIN_CONFIDENCE_TRENDING = 60   # Trending markets: 60+
    MIN_CONFIDENCE_SIDEWAYS = 65   # Sideways/Choppy: 65+ (more selective)
    
    # Legacy default for backward compatibility
    MIN_CONFIDENCE = 60
    
    def calculate(
        self,
        confidence: int,
        available_capital: float,
        current_exposure: float = 0.0,
        max_exposure: float = 0.90,
        market_regime: str = "TRENDING",
    ) -> Optional[PositionSizeResult]:
        """Calculate position size based on confidence and market regime.
        
        Args:
            confidence: Signal confidence score (0-100)
            available_capital: Total portfolio value in USD
            current_exposure: Current exposure as decimal (0.0-1.0)
            max_exposure: Maximum allowed exposure (default 0.90 = 90%)
            market_regime: Market regime ("TRENDING", "SIDEWAYS", "CHOPPY")
            
        Returns:
            PositionSizeResult or None if rejected
        """
        # Get regime-specific minimum confidence
        min_confidence = self._get_min_confidence_for_regime(market_regime)
        
        # Reject low confidence based on regime
        if confidence < min_confidence:
            logger.info(
                f"Position rejected: confidence {confidence} < {min_confidence} "
                f"(regime: {market_regime})"
            )
            return PositionSizeResult(
                size_pct=0.0,
                size_usd=0.0,
                confidence_tier="rejected",
                is_rejected=True,
                rejection_reason=f"Confidence {confidence} below minimum {min_confidence} for {market_regime} regime",
            )
        
        # Get position size percentage from mapping
        size_pct = self._get_size_for_confidence(confidence)
        confidence_tier = self._get_tier_name(confidence)
        
        # Check exposure limit
        remaining_exposure = max_exposure - current_exposure
        if remaining_exposure <= 0:
            logger.info(f"Position rejected: exposure limit reached ({current_exposure:.1%} >= {max_exposure:.1%})")
            return PositionSizeResult(
                size_pct=0.0,
                size_usd=0.0,
                confidence_tier=confidence_tier,
                is_rejected=True,
                rejection_reason=f"Exposure limit reached: {current_exposure:.1%} >= {max_exposure:.1%}",
            )
        
        # Cap size at remaining exposure
        actual_size_pct = min(size_pct, remaining_exposure)
        size_usd = available_capital * actual_size_pct
        
        logger.debug(
            f"Position size calculated: {actual_size_pct:.1%} (${size_usd:.2f}) "
            f"for confidence {confidence} ({confidence_tier}, regime: {market_regime})"
        )
        
        return PositionSizeResult(
            size_pct=actual_size_pct,
            size_usd=size_usd,
            confidence_tier=confidence_tier,
        )
    
    def _get_min_confidence_for_regime(self, market_regime: str) -> int:
        """Get minimum confidence threshold based on market regime."""
        regime_upper = market_regime.upper() if market_regime else "TRENDING"
        if regime_upper == "TRENDING":
            return self.MIN_CONFIDENCE_TRENDING
        else:  # SIDEWAYS, CHOPPY, or unknown
            return self.MIN_CONFIDENCE_SIDEWAYS
    
    def _get_size_for_confidence(self, confidence: int) -> float:
        """Get position size percentage for confidence level."""
        for (min_conf, max_conf), size in self.CONFIDENCE_TO_SIZE.items():
            if min_conf <= confidence <= max_conf:
                return size
        # Default to minimum size (12%) for edge cases above threshold
        return 0.12
    
    def _get_tier_name(self, confidence: int) -> str:
        """Get tier name for confidence level."""
        if confidence >= 90:
            return "excellent"
        elif confidence >= 80:
            return "high"
        elif confidence >= 70:
            return "good"
        elif confidence >= 60:
            return "medium"
        else:
            return "rejected"
