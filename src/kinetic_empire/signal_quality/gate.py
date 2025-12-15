"""Signal Quality Gate - Main Orchestrator.

Validates signals through all quality gates before execution.
"""

import logging
from typing import List, Optional
from datetime import datetime

from .config import QualityGateConfig, DEFAULT_QUALITY_GATE_CONFIG
from .models import QualityGateResult, ConfidenceTier, MicroAnalysisResult, BreakoutResult
from .confidence_filter import ConfidenceFilter
from .direction_aligner import DirectionAligner
from .momentum_validator import MomentumValidator, OHLCV
from .blacklist_manager import BlacklistManager
from .risk_adjuster import RiskAdjuster, MarketRegime
from .micro_analyzer import MicroTimeframeAnalyzer
from .breakout_detector import BreakoutDetector


logger = logging.getLogger(__name__)


class SignalQualityGate:
    """Main orchestrator for signal quality validation.
    
    Chains all quality gates:
    1. Confidence Filter - reject low confidence signals
    2. Direction Aligner - enforce Enhanced TA direction
    3. Momentum Validator - check price/RSI conditions
    4. Blacklist Manager - skip blacklisted symbols
    5. Micro Analyzer - check 1M/5M alignment
    6. Breakout Detector - detect volume surges
    7. Risk Adjuster - calculate stop loss and leverage
    """
    
    def __init__(self, config: QualityGateConfig = None):
        """Initialize with configuration.
        
        Args:
            config: Quality gate configuration (uses defaults if None)
        """
        self.config = config or DEFAULT_QUALITY_GATE_CONFIG
        
        # Initialize all components
        self.confidence_filter = ConfidenceFilter(self.config)
        self.direction_aligner = DirectionAligner()
        self.momentum_validator = MomentumValidator(self.config)
        self.blacklist_manager = BlacklistManager(self.config)
        self.risk_adjuster = RiskAdjuster(self.config)
        self.micro_analyzer = MicroTimeframeAnalyzer(self.config)
        self.breakout_detector = BreakoutDetector(self.config)
    
    def evaluate(
        self,
        symbol: str,
        enhanced_confidence: int,
        enhanced_direction: str,
        cash_cow_direction: str,
        ohlcv_15m: List[OHLCV],
        rsi_15m: float,
        regime: MarketRegime,
        ohlcv_1m: List[OHLCV] = None,
        ohlcv_5m: List[OHLCV] = None,
        current_price: float = 0.0,
        resistance_level: float = 0.0,
        support_level: float = 0.0,
        volume_ratio: float = 1.0,
        cash_cow_score: int = 0,
    ) -> QualityGateResult:
        """Evaluate signal through all quality gates.
        
        Args:
            symbol: Trading symbol
            enhanced_confidence: Enhanced TA confidence score (0-100)
            enhanced_direction: Direction from Enhanced TA
            cash_cow_direction: Direction from Cash Cow scorer
            ohlcv_15m: 15M OHLCV candles
            rsi_15m: 15M RSI value
            regime: Current market regime
            ohlcv_1m: 1M OHLCV candles (optional)
            ohlcv_5m: 5M OHLCV candles (optional)
            current_price: Current price for breakout detection
            resistance_level: Nearest resistance level
            support_level: Nearest support level
            volume_ratio: Current volume / average volume
            
        Returns:
            QualityGateResult with pass/fail and adjusted parameters
        """
        # 1. Check blacklist first
        if self.blacklist_manager.is_blacklisted(symbol):
            logger.info(f"{symbol}: Rejected - symbol is blacklisted")
            return QualityGateResult(
                passed=False,
                direction=enhanced_direction,
                rejection_reason="Symbol is blacklisted",
            )
        
        # 2. STRICT REGIME CHECK - Reject CHOPPY/SIDEWAYS unconditionally
        # Per profitable-trading-overhaul spec: no directional trades in unfavorable regimes
        if regime in (MarketRegime.CHOPPY, MarketRegime.SIDEWAYS):
            logger.info(
                f"{symbol}: Rejected - unfavorable regime {regime.value}. "
                f"No directional trades allowed in CHOPPY/SIDEWAYS markets."
            )
            return QualityGateResult(
                passed=False,
                direction=enhanced_direction,
                rejection_reason=f"Unfavorable regime: {regime.value} - no directional trades allowed",
            )
        
        # 3. Filter by confidence
        conf_passed, conf_tier, size_mult = self.confidence_filter.filter(enhanced_confidence)
        if not conf_passed:
            logger.info(f"{symbol}: Rejected - confidence {enhanced_confidence} below minimum")
            return QualityGateResult(
                passed=False,
                direction=enhanced_direction,
                rejection_reason=f"Confidence {enhanced_confidence} below minimum {self.config.min_confidence}",
                confidence_tier=conf_tier,
            )
        
        # 4. Align direction (Enhanced TA always wins)
        final_direction = self.direction_aligner.align(enhanced_direction, cash_cow_direction)
        
        # 5. Validate momentum
        mom_valid, mom_reason = self.momentum_validator.validate(
            final_direction, ohlcv_15m, rsi_15m
        )
        if not mom_valid:
            logger.info(f"{symbol}: Rejected - {mom_reason}")
            return QualityGateResult(
                passed=False,
                direction=final_direction,
                rejection_reason=mom_reason,
                confidence_tier=conf_tier,
                position_size_multiplier=size_mult,
            )
        
        # 6. Analyze micro-timeframes (if data available)
        micro_bonus = 0
        micro_aligned = False
        if ohlcv_1m and ohlcv_5m:
            micro_result = self.micro_analyzer.analyze(ohlcv_1m, ohlcv_5m, final_direction)
            if micro_result.should_reject:
                logger.info(f"{symbol}: Rejected - micro-timeframe contradiction")
                return QualityGateResult(
                    passed=False,
                    direction=final_direction,
                    rejection_reason=f"Micro-timeframe contradiction: 1M={micro_result.trend_1m}, 5M={micro_result.trend_5m}",
                    confidence_tier=conf_tier,
                    position_size_multiplier=size_mult,
                )
            micro_bonus = micro_result.micro_bonus
            micro_aligned = micro_result.micro_aligned
        
        # Note: CHOPPY/SIDEWAYS regimes are already rejected at step 2
        # No high-quality bypass - strict regime enforcement per profitable-trading-overhaul spec
        
        # 7. Detect breakouts
        breakout_bonus = 0
        use_tight_trailing = False
        if current_price > 0 and resistance_level > 0:
            if final_direction == "LONG":
                breakout_result = self.breakout_detector.detect(
                    current_price, resistance_level, volume_ratio, final_direction
                )
            else:
                breakout_result = self.breakout_detector.detect_support_breakdown(
                    current_price, support_level, volume_ratio
                )
            breakout_bonus = breakout_result.breakout_bonus
            use_tight_trailing = breakout_result.use_tight_trailing
        
        # 8. Calculate risk parameters
        stop_loss_pct = self.risk_adjuster.calculate_stop_loss(regime)
        max_leverage = self.risk_adjuster.calculate_max_leverage(regime, enhanced_confidence)
        
        logger.info(
            f"{symbol}: PASSED - direction={final_direction}, "
            f"confidence={enhanced_confidence} ({conf_tier.value}), "
            f"size_mult={size_mult}, stop={stop_loss_pct}%, "
            f"max_lev={max_leverage}x, micro_bonus={micro_bonus}, "
            f"breakout_bonus={breakout_bonus}"
        )
        
        return QualityGateResult(
            passed=True,
            direction=final_direction,
            rejection_reason=None,
            confidence_tier=conf_tier,
            position_size_multiplier=size_mult,
            stop_loss_pct=stop_loss_pct,
            max_leverage=max_leverage,
            micro_bonus=micro_bonus,
            breakout_bonus=breakout_bonus,
            use_tight_trailing=use_tight_trailing,
        )
    
    def record_loss(self, symbol: str, timestamp: datetime = None) -> bool:
        """Record a stop-loss for blacklist tracking.
        
        Args:
            symbol: Trading symbol
            timestamp: When the loss occurred
            
        Returns:
            True if symbol was blacklisted as a result
        """
        return self.blacklist_manager.record_loss(symbol, timestamp)
    
    def is_blacklisted(self, symbol: str) -> bool:
        """Check if symbol is blacklisted.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            True if symbol is blacklisted
        """
        return self.blacklist_manager.is_blacklisted(symbol)
    
    def cleanup_expired_blacklists(self) -> int:
        """Clean up expired blacklist entries.
        
        Returns:
            Number of entries removed
        """
        return self.blacklist_manager.cleanup_expired()
