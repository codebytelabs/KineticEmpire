"""Core enums and data models for the Enhanced TA System.

This module defines all the data structures used throughout the enhanced
technical analysis system, including enums for classifications and
dataclasses for structured data.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict


class TrendDirection(Enum):
    """Direction of price trend."""
    UP = "UP"
    DOWN = "DOWN"
    SIDEWAYS = "SIDEWAYS"


class TrendStrength(Enum):
    """Strength classification of a trend based on EMA separation."""
    STRONG = "STRONG"      # EMA separation > 1%
    MODERATE = "MODERATE"  # EMA separation 0.3% - 1%
    WEAK = "WEAK"          # EMA separation < 0.3%


class MarketRegime(Enum):
    """Current market condition classification."""
    TRENDING = "TRENDING"              # Strong aligned trends
    SIDEWAYS = "SIDEWAYS"              # Price ranging within 2% for 20 candles
    HIGH_VOLATILITY = "HIGH_VOLATILITY"  # ATR > 150% of average
    LOW_VOLATILITY = "LOW_VOLATILITY"    # ATR < 50% of average
    CHOPPY = "CHOPPY"                  # Frequent EMA crossings


class SignalConfidence(Enum):
    """Confidence level classification for trading signals."""
    HIGH = "HIGH"      # Score > 80
    MEDIUM = "MEDIUM"  # Score 65-80
    LOW = "LOW"        # Score < 65 (no signal generated)


@dataclass
class TimeframeAnalysis:
    """Analysis results for a single timeframe.
    
    Contains all technical indicators and derived classifications
    for one timeframe (4H, 1H, or 15M).
    """
    timeframe: str
    ema_9: float
    ema_21: float
    ema_50: float
    rsi: float
    macd_line: float
    macd_signal: float
    macd_histogram: float
    atr: float
    atr_average: float
    volume_ratio: float
    trend_direction: TrendDirection
    trend_strength: TrendStrength


@dataclass
class TrendAlignment:
    """Result of multi-timeframe trend alignment analysis.
    
    Captures how well trends align across 4H, 1H, and 15M timeframes,
    including any penalties for conflicts and bonuses for alignment.
    """
    alignment_score: float  # 0.0 to 1.0
    is_aligned: bool
    dominant_direction: TrendDirection
    conflict_penalty: int  # Points deducted for conflicts
    alignment_bonus: int   # Points added for full alignment (25 when all aligned)


@dataclass
class VolumeConfirmation:
    """Volume analysis results for confirming price movements.
    
    Validates that price movements are supported by corresponding volume.
    """
    is_confirmed: bool      # Volume >= 80% of average
    volume_score: int       # Points contribution to confidence
    is_declining: bool      # 5 consecutive declining candles
    is_false_move: bool     # Significant price move with low volume


@dataclass
class SupportResistance:
    """Support and resistance level detection results.
    
    Identifies key price levels and proximity to them.
    """
    nearest_support: float
    nearest_resistance: float
    at_support: bool        # Within 0.5% of support
    at_resistance: bool     # Within 0.5% of resistance
    is_breakout: bool       # Breaking through with volume
    sr_score: int           # Points contribution to confidence


@dataclass
class MomentumAnalysis:
    """Momentum indicator analysis results.
    
    Combines RSI and MACD analysis for momentum confirmation.
    """
    rsi_valid: bool         # RSI in valid range for signal direction
    macd_score: int         # Points from MACD confirmation
    has_divergence: bool    # RSI divergence from price detected
    momentum_score: int     # Total momentum contribution to confidence


@dataclass
class MarketContext:
    """Aggregated market context from all analysis components.
    
    This is the central data structure that combines all analysis
    results for the context-weighted scoring system.
    """
    trend_alignment: TrendAlignment
    trend_strength_4h: TrendStrength
    market_regime: MarketRegime
    volume_confirmation: VolumeConfirmation
    support_resistance: SupportResistance
    momentum: MomentumAnalysis
    is_choppy: bool
    btc_correlation_adjustment: int  # +/- 20 points for altcoins
    # Individual timeframe trends for hierarchical alignment
    trend_4h: Optional[TrendDirection] = None
    trend_1h: Optional[TrendDirection] = None
    trend_15m: Optional[TrendDirection] = None


@dataclass
class ConfidenceScore:
    """Final confidence score with component breakdown.
    
    Contains the weighted total score and individual component
    contributions for transparency and logging.
    """
    total_score: int
    component_scores: Dict[str, int] = field(default_factory=dict)
    confidence_level: SignalConfidence = SignalConfidence.LOW
    critical_factors_passed: bool = False
    veto_reason: Optional[str] = None


@dataclass
class EnhancedSignal:
    """Complete trading signal with full market context.
    
    The final output of the enhanced TA system, containing
    the signal direction, confidence, price levels, and
    all supporting context for analysis and logging.
    """
    symbol: str
    direction: str  # "LONG" or "SHORT"
    confidence: int
    confidence_level: SignalConfidence
    entry_price: float
    stop_loss: float
    take_profit: float
    market_context: MarketContext
    component_scores: Dict[str, int] = field(default_factory=dict)


# Timeframe weight constants for trend alignment calculation
# These weights are used by TrendAlignmentEngine
TIMEFRAME_WEIGHTS = {
    "4h": 0.50,  # 50% weight for 4H timeframe
    "1h": 0.30,  # 30% weight for 1H timeframe
    "15m": 0.20, # 20% weight for 15M timeframe
}

# Confidence scoring weights
# These weights are used by ContextWeightedScorer
CONFIDENCE_WEIGHTS = {
    "trend_alignment": 0.30,      # 30%
    "trend_strength": 0.20,       # 20%
    "volume_confirmation": 0.15,  # 15%
    "momentum": 0.15,             # 15%
    "support_resistance": 0.10,   # 10%
    "market_regime": 0.10,        # 10%
}
