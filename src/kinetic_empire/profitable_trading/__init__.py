"""Profitable Trading Overhaul Module.

Implements the comprehensive trading bot overhaul for profitability:
- Regime-based trade filtering (no CHOPPY/SIDEWAYS trades)
- Dynamic position sizing (5-15% based on confidence)
- Adaptive leverage (2x-10x based on regime and confidence)
- ATR-based risk management
- Direction validation with price momentum
"""

from .models import (
    MarketRegime,
    TrendDirection,
    RegimeAnalysis,
    RiskParameters,
    PositionSizeResult,
    StopLossResult,
    TrailingState,
    PendingEntry,
)
from .regime_detector import RegimeDetector
from .direction_validator import DirectionValidator
from .position_sizer import ConfidencePositionSizer
from .leverage_calculator import RegimeLeverageCalculator
from .atr_stop_calculator import ATRStopCalculator
from .trailing_stop_manager import ATRTrailingStopManager
from .exposure_tracker import ExposureTracker
from .entry_confirmer import EntryConfirmer

__all__ = [
    # Models
    "MarketRegime",
    "TrendDirection",
    "RegimeAnalysis",
    "RiskParameters",
    "PositionSizeResult",
    "StopLossResult",
    "TrailingState",
    "PendingEntry",
    # Components
    "RegimeDetector",
    "DirectionValidator",
    "ConfidencePositionSizer",
    "RegimeLeverageCalculator",
    "ATRStopCalculator",
    "ATRTrailingStopManager",
    "ExposureTracker",
    "EntryConfirmer",
]
