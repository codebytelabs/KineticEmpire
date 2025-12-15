"""Signal Quality Gate Module.

Provides signal quality validation to prevent trades against market direction
and reduce premature stop-outs.
"""

from .config import QualityGateConfig, DEFAULT_QUALITY_GATE_CONFIG
from .models import (
    QualityGateResult,
    ConfidenceTier,
    LossRecord,
    MicroAnalysisResult,
    BreakoutResult,
)
from .gate import SignalQualityGate
from .risk_adjuster import MarketRegime
from .momentum_validator import OHLCV

__all__ = [
    # Main gate
    "SignalQualityGate",
    # Configuration
    "QualityGateConfig",
    "DEFAULT_QUALITY_GATE_CONFIG",
    # Models
    "QualityGateResult",
    "ConfidenceTier",
    "LossRecord",
    "MicroAnalysisResult",
    "BreakoutResult",
    "MarketRegime",
    "OHLCV",
]
