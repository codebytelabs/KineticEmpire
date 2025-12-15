"""Cash Cow Upgrade - High-profit, low-risk trading system.

This module implements DayTraderAI-inspired trading enhancements:
- Confidence-based position sizing
- Consecutive loss protection
- Circuit breaker for daily loss limits
- 130-point opportunity scoring
- Upside potential analysis
- Regime-adaptive risk management
"""

from .sizer import ConfidenceBasedSizer, SizingResult, SizingConfig
from .loss_tracker import ConsecutiveLossTracker
from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from .scorer import OpportunityScorer, ScoringFeatures
from .upside import UpsideAnalyzer
from .stop_enforcer import StopDistanceEnforcer, StopEnforcerConfig
from .aligner import MultiTimeframeAligner, AlignmentResult
from .crypto import FundingRateAnalyzer, BTCCorrelationAdjuster, CorrelationConfig
from .config import CashCowConfig, DEFAULT_CONFIG
from .engine import CashCowEngine, TradeEvaluation
from .models import MarketRegime, UpsideQuality, OpportunityScore, UpsideAnalysis

__all__ = [
    # Engine
    "CashCowEngine",
    "TradeEvaluation",
    # Configuration
    "CashCowConfig",
    "DEFAULT_CONFIG",
    # Position Sizing
    "ConfidenceBasedSizer",
    "SizingResult",
    "SizingConfig",
    # Loss Protection
    "ConsecutiveLossTracker",
    "CircuitBreaker",
    "CircuitBreakerConfig",
    # Scoring
    "OpportunityScorer",
    "ScoringFeatures",
    "UpsideAnalyzer",
    # Risk Management
    "StopDistanceEnforcer",
    "StopEnforcerConfig",
    # Alignment
    "MultiTimeframeAligner",
    "AlignmentResult",
    # Crypto-Specific
    "FundingRateAnalyzer",
    "BTCCorrelationAdjuster",
    "CorrelationConfig",
    # Models
    "MarketRegime",
    "UpsideQuality",
    "OpportunityScore",
    "UpsideAnalysis",
]
