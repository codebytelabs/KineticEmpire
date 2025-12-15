"""Confidence-based position sizing module.

Implements dynamic position sizing based on confidence scores,
market regime, and consecutive loss protection.
"""

from dataclasses import dataclass
from typing import Optional

from .models import MarketRegime


@dataclass
class SizingConfig:
    """Configuration for confidence-based position sizing."""
    base_risk_pct: float = 5.0           # Base risk per trade as % of portfolio (AGGRESSIVE)
    max_position_pct: float = 15.0       # Maximum position size as % of portfolio
    
    # Confidence thresholds and multipliers
    high_confidence_threshold: int = 85   # Score >= 85 gets 2.5x
    medium_confidence_threshold: int = 75 # Score >= 75 gets 2.0x
    low_confidence_threshold: int = 65    # Score >= 65 gets 1.5x
    # Score < 65 gets rejected (0.0x)
    
    high_confidence_multiplier: float = 2.5    # 85+ = 12.5% of portfolio
    medium_confidence_multiplier: float = 2.0  # 75-84 = 10% of portfolio
    low_confidence_multiplier: float = 1.5     # 65-74 = 7.5% of portfolio


@dataclass
class SizingResult:
    """Result of position size calculation."""
    base_size: float
    confidence_multiplier: float
    regime_multiplier: float
    loss_protection_multiplier: float
    final_size: float
    rejection_reason: Optional[str] = None
    
    @property
    def is_rejected(self) -> bool:
        """Check if trade was rejected."""
        return self.rejection_reason is not None or self.final_size == 0


class ConfidenceBasedSizer:
    """Calculates position sizes based on confidence scores.
    
    Position sizing formula:
    final_size = base_size * confidence_mult * regime_mult * loss_protection_mult
    
    Confidence multipliers (from Requirements 1.1-1.4):
    - Score >= 85: 2.0x (high confidence)
    - Score 75-84: 1.5x (medium confidence)
    - Score 65-74: 1.0x (low confidence)
    - Score < 65: 0.0x (rejected)
    
    Maximum position size is capped at 10% of portfolio (Requirement 1.5).
    """

    def __init__(self, config: Optional[SizingConfig] = None):
        """Initialize confidence-based sizer.
        
        Args:
            config: Sizing configuration. Uses defaults if None.
        """
        self.config = config or SizingConfig()

    def get_confidence_multiplier(self, confidence: int) -> float:
        """Get position size multiplier based on confidence score.
        
        Args:
            confidence: Confidence score (0-100)
            
        Returns:
            Multiplier: 2.0, 1.5, 1.0, or 0.0 based on confidence brackets
            
        Validates: Requirements 1.1, 1.2, 1.3, 1.4
        """
        if confidence >= self.config.high_confidence_threshold:
            return self.config.high_confidence_multiplier  # 2.0x
        elif confidence >= self.config.medium_confidence_threshold:
            return self.config.medium_confidence_multiplier  # 1.5x
        elif confidence >= self.config.low_confidence_threshold:
            return self.config.low_confidence_multiplier  # 1.0x
        else:
            return 0.0  # Rejected

    def get_regime_multiplier(self, regime: MarketRegime) -> float:
        """Get position size multiplier based on market regime.
        
        Args:
            regime: Current market regime
            
        Returns:
            Multiplier based on regime conditions
            
        Validates: Requirements 6.1, 6.2, 6.3, 6.4
        """
        multipliers = {
            MarketRegime.TRENDING: 1.0,
            MarketRegime.BEAR: 0.5,
            MarketRegime.CHOPPY: 0.75,
            MarketRegime.HIGH_VOLATILITY: 0.85,
            MarketRegime.LOW_VOLATILITY: 1.0,
        }
        return multipliers.get(regime, 1.0)

    def get_loss_protection_multiplier(self, consecutive_losses: int) -> float:
        """Get position size multiplier based on consecutive losses.
        
        Args:
            consecutive_losses: Number of consecutive losing trades
            
        Returns:
            Multiplier: 1.0, 0.5, or 0.25 based on loss count
            
        Validates: Requirements 2.3, 2.4, 2.5
        """
        if consecutive_losses >= 5:
            return 0.25  # 75% reduction
        elif consecutive_losses >= 3:
            return 0.5   # 50% reduction
        else:
            return 1.0   # No reduction

    def calculate_size(
        self,
        confidence: int,
        regime: MarketRegime,
        consecutive_losses: int,
        portfolio_value: float,
        base_risk_pct: Optional[float] = None
    ) -> SizingResult:
        """Calculate optimal position size.
        
        Args:
            confidence: Confidence score (0-100)
            regime: Current market regime
            consecutive_losses: Number of consecutive losing trades
            portfolio_value: Total portfolio value
            base_risk_pct: Base risk percentage (default from config)
            
        Returns:
            SizingResult with calculated position size and multipliers
            
        Validates: Requirements 1.1-1.5, 2.3-2.5, 6.1-6.5
        """
        base_risk = base_risk_pct if base_risk_pct is not None else self.config.base_risk_pct
        
        # Calculate base size
        base_size = portfolio_value * (base_risk / 100)
        
        # Get multipliers
        confidence_mult = self.get_confidence_multiplier(confidence)
        regime_mult = self.get_regime_multiplier(regime)
        loss_mult = self.get_loss_protection_multiplier(consecutive_losses)
        
        # Check for rejection
        rejection_reason = None
        if confidence_mult == 0.0:
            rejection_reason = f"Confidence score {confidence} below minimum threshold {self.config.low_confidence_threshold}"
        
        # Calculate final size
        if rejection_reason:
            final_size = 0.0
        else:
            final_size = base_size * confidence_mult * regime_mult * loss_mult
            
            # Enforce maximum position cap (Requirement 1.5)
            max_size = portfolio_value * (self.config.max_position_pct / 100)
            final_size = min(final_size, max_size)
        
        return SizingResult(
            base_size=base_size,
            confidence_multiplier=confidence_mult,
            regime_multiplier=regime_mult,
            loss_protection_multiplier=loss_mult,
            final_size=final_size,
            rejection_reason=rejection_reason
        )

    def get_minimum_regime_multiplier(self, regimes: list[MarketRegime]) -> float:
        """Get the most conservative multiplier when multiple regimes apply.
        
        Args:
            regimes: List of applicable market regimes
            
        Returns:
            Minimum (most conservative) multiplier
            
        Validates: Requirement 6.5
        """
        if not regimes:
            return 1.0
        
        multipliers = [self.get_regime_multiplier(r) for r in regimes]
        return min(multipliers)
