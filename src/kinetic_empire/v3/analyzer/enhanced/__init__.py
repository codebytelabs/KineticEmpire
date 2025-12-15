"""Enhanced Multi-Timeframe Context-Aware Technical Analysis System.

This module provides comprehensive market context awareness through:
- Multi-timeframe trend alignment
- Trend strength quantification
- Market regime detection
- Volume confirmation
- Adaptive risk management
"""

from .models import (
    TrendDirection,
    TrendStrength,
    MarketRegime,
    SignalConfidence,
    TimeframeAnalysis,
    TrendAlignment,
    VolumeConfirmation,
    SupportResistance,
    MomentumAnalysis,
    MarketContext,
    ConfidenceScore,
    EnhancedSignal,
    TIMEFRAME_WEIGHTS,
    CONFIDENCE_WEIGHTS,
)
from .analyzer import EnhancedTAAnalyzer
from .trend_strength import TrendStrengthCalculator
from .market_regime import MarketRegimeDetector, OHLCV
from .trend_alignment import TrendAlignmentEngine
from .volume_confirmation import VolumeConfirmationAnalyzer
from .momentum import MomentumAnalyzer
from .support_resistance import SupportResistanceDetector
from .choppy_detector import ChoppyMarketDetector
from .btc_correlation import BTCCorrelationEngine
from .adaptive_stop import AdaptiveStopCalculator
from .scorer import ContextWeightedScorer
from .validator import CriticalFactorValidator

__all__ = [
    # Main Analyzer
    "EnhancedTAAnalyzer",
    # Enums
    "TrendDirection",
    "TrendStrength",
    "MarketRegime",
    "SignalConfidence",
    # Data Models
    "TimeframeAnalysis",
    "TrendAlignment",
    "VolumeConfirmation",
    "SupportResistance",
    "MomentumAnalysis",
    "MarketContext",
    "ConfidenceScore",
    "EnhancedSignal",
    "OHLCV",
    # Component Analyzers
    "TrendStrengthCalculator",
    "MarketRegimeDetector",
    "TrendAlignmentEngine",
    "VolumeConfirmationAnalyzer",
    "MomentumAnalyzer",
    "SupportResistanceDetector",
    "ChoppyMarketDetector",
    "BTCCorrelationEngine",
    "AdaptiveStopCalculator",
    "ContextWeightedScorer",
    "CriticalFactorValidator",
    # Constants
    "TIMEFRAME_WEIGHTS",
    "CONFIDENCE_WEIGHTS",
]
