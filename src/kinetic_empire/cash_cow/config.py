"""Cash Cow Configuration module.

Centralized configuration for all Cash Cow trading components.
"""

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class CashCowConfig:
    """Complete configuration for Cash Cow trading system.
    
    This configuration brings together all component settings
    for easy management and customization.
    """
    
    # Confidence-Based Position Sizing (Requirements 1.1-1.5)
    high_confidence_threshold: int = 85      # Score >= 85 gets 2.0x
    medium_confidence_threshold: int = 75    # Score >= 75 gets 1.5x
    low_confidence_threshold: int = 65       # Score >= 65 gets 1.0x
    high_confidence_multiplier: float = 2.0
    medium_confidence_multiplier: float = 1.5
    low_confidence_multiplier: float = 1.0
    base_risk_pct: float = 1.0               # Base risk per trade
    max_position_pct: float = 10.0           # Maximum position size
    
    # Consecutive Loss Protection (Requirements 2.1-2.5)
    loss_protection_threshold_1: int = 3     # 3 losses = 0.5x
    loss_protection_threshold_2: int = 5     # 5 losses = 0.25x
    loss_protection_multiplier_1: float = 0.5
    loss_protection_multiplier_2: float = 0.25
    
    # Circuit Breaker (Requirements 3.1-3.4)
    daily_loss_limit_pct: float = 2.0        # 2% daily loss triggers halt
    
    # Regime Multipliers (Requirements 6.1-6.5)
    regime_multipliers: Dict[str, float] = field(default_factory=lambda: {
        "trending": 1.0,
        "bear": 0.5,
        "choppy": 0.75,
        "high_volatility": 0.85,
        "low_volatility": 1.0,
    })
    
    # Minimum Stop Distance (Requirements 7.1-7.3)
    minimum_stop_pct: float = 1.5            # 1.5% minimum stop distance
    
    # Multi-Timeframe Alignment (Requirements 9.1-9.5)
    timeframes: list = field(default_factory=lambda: ["5m", "15m", "1h", "4h", "1d"])
    alignment_bonus_all: int = 10            # All timeframes aligned
    alignment_bonus_4of5: int = 5            # 4 of 5 aligned
    alignment_penalty_low: int = -10         # <3 aligned
    daily_conflict_penalty: int = -5         # Daily conflicts
    
    # Funding Rate (Requirements 10.1-10.2)
    extreme_negative_funding: float = -0.1   # Threshold for long bonus
    extreme_positive_funding: float = 0.1    # Threshold for short bonus
    funding_bonus_points: int = 5
    
    # BTC Correlation (Requirements 10.3-10.4)
    high_correlation_threshold: float = 0.7
    btc_volatility_threshold: float = 3.0
    correlation_position_reduction: float = 20.0  # 20% reduction
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            "confidence": {
                "high_threshold": self.high_confidence_threshold,
                "medium_threshold": self.medium_confidence_threshold,
                "low_threshold": self.low_confidence_threshold,
                "high_multiplier": self.high_confidence_multiplier,
                "medium_multiplier": self.medium_confidence_multiplier,
                "low_multiplier": self.low_confidence_multiplier,
            },
            "position_sizing": {
                "base_risk_pct": self.base_risk_pct,
                "max_position_pct": self.max_position_pct,
            },
            "loss_protection": {
                "threshold_1": self.loss_protection_threshold_1,
                "threshold_2": self.loss_protection_threshold_2,
                "multiplier_1": self.loss_protection_multiplier_1,
                "multiplier_2": self.loss_protection_multiplier_2,
            },
            "circuit_breaker": {
                "daily_loss_limit_pct": self.daily_loss_limit_pct,
            },
            "regime_multipliers": self.regime_multipliers,
            "stop_distance": {
                "minimum_pct": self.minimum_stop_pct,
            },
            "alignment": {
                "timeframes": self.timeframes,
                "bonus_all": self.alignment_bonus_all,
                "bonus_4of5": self.alignment_bonus_4of5,
                "penalty_low": self.alignment_penalty_low,
                "daily_conflict_penalty": self.daily_conflict_penalty,
            },
            "funding_rate": {
                "extreme_negative": self.extreme_negative_funding,
                "extreme_positive": self.extreme_positive_funding,
                "bonus_points": self.funding_bonus_points,
            },
            "btc_correlation": {
                "high_threshold": self.high_correlation_threshold,
                "volatility_threshold": self.btc_volatility_threshold,
                "position_reduction": self.correlation_position_reduction,
            },
        }


# Default configuration instance
DEFAULT_CONFIG = CashCowConfig()
