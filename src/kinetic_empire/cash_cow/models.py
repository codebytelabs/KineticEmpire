"""Data models for Cash Cow trading system."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class MarketRegime(Enum):
    """Market regime classification for adaptive sizing."""
    TRENDING = "trending"
    BEAR = "bear"
    CHOPPY = "choppy"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"


class UpsideQuality(Enum):
    """Quality classification for upside potential."""
    EXCELLENT = "excellent"  # >5% room to resistance
    GOOD = "good"            # 3-5% room
    LIMITED = "limited"      # 1-3% room
    POOR = "poor"            # <1% room


@dataclass
class OpportunityScore:
    """130-point opportunity scoring breakdown."""
    technical_score: int = 0      # 0-40 points
    momentum_score: int = 0       # 0-25 points
    volume_score: int = 0         # 0-20 points
    volatility_score: int = 0     # 0-15 points
    regime_score: int = 0         # 0-10 points
    sentiment_score: int = 0      # 0-10 points
    growth_score: int = 0         # 0-10 points
    upside_score: int = 0         # 0-25 points (bonus)
    alignment_bonus: int = 0      # -15 to +10 points
    rr_bonus: int = 0             # 0-5 points
    
    @property
    def total_score(self) -> int:
        """Calculate total opportunity score."""
        return (
            self.technical_score +
            self.momentum_score +
            self.volume_score +
            self.volatility_score +
            self.regime_score +
            self.sentiment_score +
            self.growth_score +
            self.upside_score +
            self.alignment_bonus +
            self.rr_bonus
        )
    
    @property
    def confidence(self) -> int:
        """Convert total score to confidence percentage (0-100)."""
        # Max possible score is 130 + 25 (upside) + 10 (alignment) + 5 (rr) = 170
        # But practical max is around 130-140
        # Normalize to 0-100 scale
        return min(100, max(0, int(self.total_score * 100 / 130)))


@dataclass
class UpsideAnalysis:
    """Analysis of upside potential for a trade."""
    distance_to_resistance_pct: float
    distance_to_support_pct: float
    risk_reward_ratio: float
    upside_quality: UpsideQuality
    upside_score: int    # 0-25 points
    rr_bonus: int        # 0-5 points
    penalty: int         # 0-15 points
