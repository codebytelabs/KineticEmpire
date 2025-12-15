"""Signal Quality Gate Data Models.

Defines result dataclasses and enums for the Signal Quality Gate system.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class ConfidenceTier(Enum):
    """Confidence tier classification."""
    HIGH = "high"      # >= 70: full position size
    MEDIUM = "medium"  # 50-70: 0.5x position size
    LOW = "low"        # < 50: rejected


@dataclass
class QualityGateResult:
    """Result of signal quality evaluation.
    
    Attributes:
        passed: Whether the signal passed all quality gates
        direction: Final trade direction to use (from Enhanced TA)
        rejection_reason: Why signal was rejected (if applicable)
        confidence_tier: Classification of confidence level
        position_size_multiplier: Multiplier for position sizing (0.5 or 1.0)
        stop_loss_pct: Stop loss percentage based on regime
        max_leverage: Maximum allowed leverage
        micro_bonus: Bonus points from 1M/5M alignment
        breakout_bonus: Bonus points from breakout detection
        use_tight_trailing: Whether to use tighter trailing stops
    """
    passed: bool
    direction: str
    rejection_reason: Optional[str] = None
    confidence_tier: ConfidenceTier = ConfidenceTier.LOW
    position_size_multiplier: float = 1.0
    stop_loss_pct: float = 3.0
    max_leverage: int = 10
    micro_bonus: int = 0
    breakout_bonus: int = 0
    use_tight_trailing: bool = False


@dataclass
class LossRecord:
    """Record of a trading loss for blacklist tracking.
    
    Attributes:
        symbol: Trading symbol
        timestamp: When the loss occurred
        entry_price: Entry price of the trade
        exit_price: Exit price (stop loss hit)
        loss_pct: Percentage loss
    """
    symbol: str
    timestamp: datetime
    entry_price: float
    exit_price: float
    loss_pct: float


@dataclass
class MicroAnalysisResult:
    """Result of 1M and 5M timeframe analysis.
    
    Attributes:
        trend_1m: Trend direction on 1M chart
        trend_5m: Trend direction on 5M chart
        micro_aligned: Whether both align with signal direction
        micro_bonus: Points to add (10 if aligned, 0 otherwise)
        should_reject: Whether to reject due to contradiction
    """
    trend_1m: str  # "UP", "DOWN", "SIDEWAYS"
    trend_5m: str
    micro_aligned: bool
    micro_bonus: int
    should_reject: bool


@dataclass
class BreakoutResult:
    """Result of volume surge and breakout detection.
    
    Attributes:
        is_volume_surge: Whether volume exceeds 200% of average
        is_breakout: Whether price broke resistance with volume
        breakout_bonus: Points to add (15 for confirmed breakout)
        use_tight_trailing: Whether to use tighter trailing stops
    """
    is_volume_surge: bool
    is_breakout: bool
    breakout_bonus: int
    use_tight_trailing: bool
