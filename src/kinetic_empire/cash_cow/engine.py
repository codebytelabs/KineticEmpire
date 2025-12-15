"""Cash Cow Trading Engine Integration.

Integrates all Cash Cow components into a cohesive trading system.
"""

from dataclasses import dataclass
from typing import Optional, Dict, List
from datetime import datetime

from .config import CashCowConfig, DEFAULT_CONFIG
from .sizer import ConfidenceBasedSizer, SizingConfig, SizingResult
from .loss_tracker import ConsecutiveLossTracker
from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from .scorer import OpportunityScorer, ScoringFeatures
from .upside import UpsideAnalyzer
from .stop_enforcer import StopDistanceEnforcer, StopEnforcerConfig
from .aligner import MultiTimeframeAligner, AlignmentResult
from .crypto import FundingRateAnalyzer, BTCCorrelationAdjuster, CorrelationConfig
from .models import MarketRegime, OpportunityScore, UpsideAnalysis


@dataclass
class TradeEvaluation:
    """Complete evaluation of a trading opportunity."""
    symbol: str
    direction: str
    opportunity_score: OpportunityScore
    upside_analysis: UpsideAnalysis
    alignment_result: AlignmentResult
    sizing_result: SizingResult
    funding_bonus: int
    btc_adjustment: float
    final_confidence: int
    should_trade: bool
    rejection_reasons: List[str]


class CashCowEngine:
    """Integrated Cash Cow Trading Engine.
    
    Combines all Cash Cow components:
    - Confidence-based position sizing
    - Consecutive loss protection
    - Circuit breaker
    - 130-point opportunity scoring
    - Upside potential analysis
    - Multi-timeframe alignment
    - Funding rate analysis
    - BTC correlation adjustment
    """

    def __init__(self, config: Optional[CashCowConfig] = None):
        """Initialize Cash Cow Engine.
        
        Args:
            config: Cash Cow configuration (uses defaults if None)
        """
        self.config = config or DEFAULT_CONFIG
        
        # Initialize components
        self._init_sizer()
        self._init_risk_components()
        self._init_scoring_components()
        self._init_crypto_components()

    def _init_sizer(self):
        """Initialize position sizer."""
        sizer_config = SizingConfig(
            base_risk_pct=self.config.base_risk_pct,
            max_position_pct=self.config.max_position_pct,
            high_confidence_threshold=self.config.high_confidence_threshold,
            medium_confidence_threshold=self.config.medium_confidence_threshold,
            low_confidence_threshold=self.config.low_confidence_threshold,
            high_confidence_multiplier=self.config.high_confidence_multiplier,
            medium_confidence_multiplier=self.config.medium_confidence_multiplier,
            low_confidence_multiplier=self.config.low_confidence_multiplier,
        )
        self.sizer = ConfidenceBasedSizer(sizer_config)

    def _init_risk_components(self):
        """Initialize risk management components."""
        self.loss_tracker = ConsecutiveLossTracker()
        
        breaker_config = CircuitBreakerConfig(
            daily_loss_limit_pct=self.config.daily_loss_limit_pct
        )
        self.circuit_breaker = CircuitBreaker(breaker_config)
        
        stop_config = StopEnforcerConfig(
            minimum_stop_pct=self.config.minimum_stop_pct
        )
        self.stop_enforcer = StopDistanceEnforcer(stop_config)

    def _init_scoring_components(self):
        """Initialize scoring components."""
        self.scorer = OpportunityScorer()
        self.upside_analyzer = UpsideAnalyzer()
        self.aligner = MultiTimeframeAligner()

    def _init_crypto_components(self):
        """Initialize crypto-specific components."""
        self.funding_analyzer = FundingRateAnalyzer()
        
        correlation_config = CorrelationConfig(
            high_correlation_threshold=self.config.high_correlation_threshold,
            btc_volatility_threshold=self.config.btc_volatility_threshold,
            position_reduction_pct=self.config.correlation_position_reduction,
        )
        self.btc_adjuster = BTCCorrelationAdjuster(correlation_config)

    def evaluate_opportunity(
        self,
        symbol: str,
        direction: str,
        features: ScoringFeatures,
        price: float,
        resistance: float,
        support: float,
        timeframe_directions: Dict[str, str],
        funding_rate: float,
        btc_correlation: float,
        btc_volatility: float,
        regime: MarketRegime,
        portfolio_value: float,
    ) -> TradeEvaluation:
        """Evaluate a trading opportunity using all Cash Cow components.
        
        Args:
            symbol: Trading symbol
            direction: Trade direction ("long" or "short")
            features: Scoring features
            price: Current price
            resistance: Resistance level
            support: Support level
            timeframe_directions: Dict of timeframe -> direction
            funding_rate: Current funding rate
            btc_correlation: Correlation with BTC
            btc_volatility: BTC volatility
            regime: Current market regime
            portfolio_value: Total portfolio value
            
        Returns:
            Complete trade evaluation
        """
        rejection_reasons = []
        
        # Check circuit breaker first
        if not self.circuit_breaker.can_enter_new_trade():
            rejection_reasons.append("Circuit breaker is active")
        
        # Score the opportunity
        opportunity_score = self.scorer.calculate_total(features)
        
        # Analyze upside potential
        upside_analysis = self.upside_analyzer.analyze(price, resistance, support)
        
        # Check alignment
        alignment_result = self.aligner.check_alignment(timeframe_directions, direction)
        
        # Get funding bonus
        funding_bonus = self.funding_analyzer.get_funding_bonus(funding_rate, direction)
        
        # Get BTC correlation adjustment
        btc_adjustment = self.btc_adjuster.get_correlation_adjustment(
            btc_correlation, btc_volatility
        )
        
        # Calculate final confidence
        final_confidence = (
            opportunity_score.total_score +
            upside_analysis.upside_score +
            upside_analysis.rr_bonus -
            upside_analysis.penalty +
            alignment_result.alignment_bonus +
            funding_bonus
        )
        
        # Calculate position size
        sizing_result = self.sizer.calculate_size(
            confidence=final_confidence,
            regime=regime,
            consecutive_losses=self.loss_tracker.consecutive_losses,
            portfolio_value=portfolio_value,
        )
        
        # Apply BTC correlation adjustment
        if sizing_result.final_size > 0:
            sizing_result.final_size *= btc_adjustment
        
        # Check for rejection
        if sizing_result.is_rejected:
            rejection_reasons.append(sizing_result.rejection_reason or "Low confidence")
        
        if upside_analysis.penalty > 0:
            rejection_reasons.append("Poor upside potential (<1% room)")
        
        should_trade = len(rejection_reasons) == 0 and sizing_result.final_size > 0
        
        return TradeEvaluation(
            symbol=symbol,
            direction=direction,
            opportunity_score=opportunity_score,
            upside_analysis=upside_analysis,
            alignment_result=alignment_result,
            sizing_result=sizing_result,
            funding_bonus=funding_bonus,
            btc_adjustment=btc_adjustment,
            final_confidence=final_confidence,
            should_trade=should_trade,
            rejection_reasons=rejection_reasons,
        )

    def record_trade_result(self, is_winner: bool):
        """Record trade result for loss tracking.
        
        Args:
            is_winner: True if trade was profitable
        """
        if is_winner:
            self.loss_tracker.record_win()
        else:
            self.loss_tracker.record_loss()

    def update_daily_pnl(self, daily_pnl: float, portfolio_value: float):
        """Update circuit breaker with daily P&L.
        
        Args:
            daily_pnl: Daily P&L (negative for losses)
            portfolio_value: Total portfolio value
        """
        self.circuit_breaker.check_and_trigger(daily_pnl, portfolio_value)

    def reset_for_new_day(self):
        """Reset daily components for new trading day."""
        self.circuit_breaker.reset_for_new_day()

    def get_status(self) -> dict:
        """Get current engine status.
        
        Returns:
            Dictionary with component statuses
        """
        return {
            "circuit_breaker": self.circuit_breaker.get_status(),
            "consecutive_losses": self.loss_tracker.consecutive_losses,
            "loss_protection_multiplier": self.loss_tracker.get_protection_multiplier(),
            "can_trade": self.circuit_breaker.can_enter_new_trade(),
        }
