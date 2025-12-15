"""Data models for optimized trading parameters."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class MarketRegime(Enum):
    """Market regime classification."""
    TRENDING = "trending"
    SIDEWAYS = "sideways"
    CHOPPY = "choppy"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"


@dataclass
class StopResult:
    """Result from ATR stop calculation."""
    stop_price: float
    multiplier_used: float
    adjusted_position_size: Optional[float]
    max_loss_exceeded: bool
    distance_percent: float


@dataclass
class RSIResult:
    """Result from RSI filter evaluation."""
    signal_valid: bool
    requires_confirmation: bool
    confidence_bonus: int
    reason: str


@dataclass
class ADXResult:
    """Result from ADX filter evaluation."""
    regime: MarketRegime
    position_size_multiplier: float
    confidence_bonus: int
    is_trending: bool


@dataclass
class VolumeResult:
    """Result from volume confirmation."""
    confirmed: bool
    position_size_multiplier: float
    confidence_bonus: int
    is_spike: bool


@dataclass
class RiskCheckResult:
    """Result from portfolio risk check."""
    can_open: bool
    reason: Optional[str]
    position_size_multiplier: float
    is_paused: bool = False
