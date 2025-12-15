"""Wave Rider Module - Active Momentum Scalping System.

Transforms the Kinetic Empire trading bot from a conservative trend-follower
into an active momentum scalper that:
- Scans ALL futures pairs (~150+) for momentum opportunities
- Detects volume spikes (2x/3x/5x classification)
- Uses multi-timeframe analysis (1m/5m/15m)
- Enters both LONG and SHORT positions
- Rides price waves with ATR-based stops and trailing stops
"""

from .models import (
    # Enums
    SpikeClassification,
    TrendDirection,
    # Data classes
    OHLCV,
    MoverData,
    TimeframeAnalysis,
    MTFResult,
    WaveRiderSignal,
    TrailingState,
    WaveRiderConfig,
)
from .volume_spike_detector import VolumeSpikeDetector
from .momentum_scanner import MomentumScanner
from .mtf_analyzer import MTFAnalyzer
from .position_sizer import WaveRiderPositionSizer, PositionSizeResult
from .signal_generator import WaveRiderSignalGenerator
from .stop_calculator import WaveRiderStopCalculator, StopResult
from .trailing_stop import WaveRiderTrailingStop, TrailingUpdate
from .risk_manager import (
    WaveRiderCircuitBreaker,
    WaveRiderBlacklist,
    WaveRiderPositionLimit,
)

__all__ = [
    # Enums
    "SpikeClassification",
    "TrendDirection",
    # Data classes
    "OHLCV",
    "MoverData",
    "TimeframeAnalysis",
    "MTFResult",
    "WaveRiderSignal",
    "TrailingState",
    "WaveRiderConfig",
    "PositionSizeResult",
    "StopResult",
    "TrailingUpdate",
    # Components
    "VolumeSpikeDetector",
    "MomentumScanner",
    "MTFAnalyzer",
    "WaveRiderPositionSizer",
    "WaveRiderSignalGenerator",
    "WaveRiderStopCalculator",
    "WaveRiderTrailingStop",
    "WaveRiderCircuitBreaker",
    "WaveRiderBlacklist",
    "WaveRiderPositionLimit",
]
