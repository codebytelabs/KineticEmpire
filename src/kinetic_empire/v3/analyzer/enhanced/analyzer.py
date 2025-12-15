"""Enhanced TA Analyzer - Main Orchestrator for the Enhanced TA System.

Integrates all component analyzers to provide comprehensive market analysis.
"""

import logging
from typing import List, Optional, Dict, Any

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
)
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


logger = logging.getLogger(__name__)


class EnhancedTAAnalyzer:
    """Main orchestrator for enhanced technical analysis.
    
    Integrates all component analyzers to provide comprehensive
    market context awareness and signal generation.
    """
    
    def __init__(self):
        self.trend_strength_calc = TrendStrengthCalculator()
        self.regime_detector = MarketRegimeDetector()
        self.alignment_engine = TrendAlignmentEngine()
        self.volume_analyzer = VolumeConfirmationAnalyzer()
        self.momentum_analyzer = MomentumAnalyzer()
        self.sr_detector = SupportResistanceDetector()
        self.choppy_detector = ChoppyMarketDetector()
        self.btc_engine = BTCCorrelationEngine()
        self.stop_calculator = AdaptiveStopCalculator()
        self.scorer = ContextWeightedScorer()
        self.validator = CriticalFactorValidator()

    def analyze(
        self,
        symbol: str,
        ohlcv_4h: List[OHLCV],
        ohlcv_1h: List[OHLCV],
        ohlcv_15m: List[OHLCV],
        indicators_4h: Dict[str, float],
        indicators_1h: Dict[str, float],
        indicators_15m: Dict[str, float],
        btc_indicators_4h: Optional[Dict[str, float]] = None,
        is_altcoin: bool = True,
    ) -> Optional[EnhancedSignal]:
        """Perform comprehensive market analysis and generate signal.
        
        Args:
            symbol: Trading symbol
            ohlcv_4h: 4H OHLCV data
            ohlcv_1h: 1H OHLCV data
            ohlcv_15m: 15M OHLCV data
            indicators_4h: 4H indicators dict
            indicators_1h: 1H indicators dict
            indicators_15m: 15M indicators dict
            btc_indicators_4h: BTC 4H indicators for correlation
            is_altcoin: Whether symbol is an altcoin
            
        Returns:
            EnhancedSignal if conditions met, None otherwise
        """
        # Build timeframe analyses
        analysis_4h = self._build_timeframe_analysis("4h", indicators_4h)
        analysis_1h = self._build_timeframe_analysis("1h", indicators_1h)
        analysis_15m = self._build_timeframe_analysis("15m", indicators_15m)
        
        # Update BTC correlation if available
        if btc_indicators_4h:
            btc_analysis = self._build_timeframe_analysis("4h", btc_indicators_4h)
            self.btc_engine.update_btc_analysis(btc_analysis)
        
        # Check for choppy conditions
        prices_15m = [c.close for c in ohlcv_15m] if ohlcv_15m else []
        ema_9_values = [indicators_15m.get("ema_9", 0)] * len(prices_15m)
        is_choppy = self.choppy_detector.is_choppy(prices_15m, ema_9_values)
        
        # Detect market regime
        regime = self.regime_detector.detect(analysis_4h, analysis_1h, ohlcv_4h, is_choppy)
        
        # Calculate trend alignment
        alignment = self.alignment_engine.calculate_alignment(
            analysis_4h.trend_direction,
            analysis_1h.trend_direction,
            analysis_15m.trend_direction,
        )
        
        # Determine signal direction - USE 15M TREND for entry timing!
        # The 15M trend shows actual current momentum, not just the bigger picture
        # This prevents "catching falling knives" when 4H is up but price is dropping
        if analysis_15m.trend_direction == TrendDirection.UP:
            signal_direction = "LONG"
        elif analysis_15m.trend_direction == TrendDirection.DOWN:
            signal_direction = "SHORT"
        else:
            # 15M is sideways - use 1H as tiebreaker
            if analysis_1h.trend_direction == TrendDirection.UP:
                signal_direction = "LONG"
            elif analysis_1h.trend_direction == TrendDirection.DOWN:
                signal_direction = "SHORT"
            else:
                # Both sideways - use 4H
                signal_direction = "LONG" if alignment.dominant_direction == TrendDirection.UP else "SHORT"
        
        # Analyze volume (using BTC as benchmark)
        volume_history = [c.volume for c in ohlcv_15m[-10:]] if ohlcv_15m else []
        price_change = self._calc_price_change(ohlcv_15m)
        btc_vol_ratio = btc_indicators_4h.get("volume_ratio", 1.0) if btc_indicators_4h else 1.0
        volume_conf = self.volume_analyzer.analyze(
            indicators_15m.get("volume_ratio", 1.0),
            volume_history,
            price_change,
            btc_volume_ratio=btc_vol_ratio,
        )
        
        # CRITICAL: Verify signal direction matches recent price momentum
        # Don't go LONG if price just dropped, don't go SHORT if price just rose
        if len(ohlcv_15m) >= 3:
            recent_change = (ohlcv_15m[-1].close - ohlcv_15m[-3].close) / ohlcv_15m[-3].close * 100
            if signal_direction == "LONG" and recent_change < -0.3:
                # Price dropped >0.3% in last 3 candles, flip to SHORT
                signal_direction = "SHORT"
                logger.debug(f"{symbol}: Flipped to SHORT due to recent drop ({recent_change:.2f}%)")
            elif signal_direction == "SHORT" and recent_change > 0.3:
                # Price rose >0.3% in last 3 candles, flip to LONG
                signal_direction = "LONG"
                logger.debug(f"{symbol}: Flipped to LONG due to recent rise ({recent_change:.2f}%)")

        # Analyze momentum
        momentum = self.momentum_analyzer.analyze(
            indicators_15m.get("rsi", 50),
            indicators_15m.get("macd_histogram", 0),
            indicators_15m.get("prev_macd_histogram"),
            signal_direction,
        )
        
        # Detect support/resistance
        sr = self.sr_detector.detect(
            ohlcv_4h,
            ohlcv_15m[-1].close if ohlcv_15m else 0,
            volume_conf.is_confirmed,
        )
        
        # Get BTC correlation adjustment
        btc_adjustment = self.btc_engine.get_confidence_adjustment(signal_direction, is_altcoin)
        
        # Build market context
        context = MarketContext(
            trend_alignment=alignment,
            trend_strength_4h=analysis_4h.trend_strength,
            market_regime=regime,
            volume_confirmation=volume_conf,
            support_resistance=sr,
            momentum=momentum,
            is_choppy=is_choppy,
            btc_correlation_adjustment=btc_adjustment,
            # Individual trends for hierarchical alignment validation
            trend_4h=analysis_4h.trend_direction,
            trend_1h=analysis_1h.trend_direction,
            trend_15m=analysis_15m.trend_direction,
        )
        
        # Validate critical factors
        validation = self.validator.validate(context)
        if not validation.passed:
            logger.info(f"{symbol}: Signal blocked - {validation.veto_reason}")
            return None
        
        # Check BTC volatility pause
        if is_altcoin and self.btc_engine.should_pause_altcoin_signals():
            logger.info(f"{symbol}: Altcoin signals paused due to BTC volatility")
            return None
        
        # Calculate confidence score
        score = self.scorer.calculate_score(context)
        score.critical_factors_passed = True
        
        # Check minimum confidence
        if score.confidence_level == SignalConfidence.LOW:
            logger.info(f"{symbol}: Score {score.total_score} below threshold")
            return None
        
        # Calculate adaptive stop loss
        entry_price = ohlcv_15m[-1].close if ohlcv_15m else 0
        atr = indicators_15m.get("atr", entry_price * 0.02)
        stop_loss = self.stop_calculator.calculate_stop_price(
            entry_price, atr, regime, analysis_4h.trend_strength, signal_direction
        )
        
        # Calculate take profit (2:1 R:R)
        risk = abs(entry_price - stop_loss)
        if signal_direction == "LONG":
            take_profit = entry_price + (risk * 2)
        else:
            take_profit = entry_price - (risk * 2)
        
        # Log component scores
        self._log_analysis(symbol, context, score)
        
        return EnhancedSignal(
            symbol=symbol,
            direction=signal_direction,
            confidence=score.total_score,
            confidence_level=score.confidence_level,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            market_context=context,
            component_scores=score.component_scores,
        )

    def _build_timeframe_analysis(
        self, timeframe: str, indicators: Dict[str, float]
    ) -> TimeframeAnalysis:
        """Build TimeframeAnalysis from indicators dict."""
        ema_9 = indicators.get("ema_9", 0)
        ema_21 = indicators.get("ema_21", 0)
        price = indicators.get("close", ema_9)
        
        # Determine trend direction
        if ema_9 > ema_21 * 1.001:
            trend_dir = TrendDirection.UP
        elif ema_9 < ema_21 * 0.999:
            trend_dir = TrendDirection.DOWN
        else:
            trend_dir = TrendDirection.SIDEWAYS
        
        # Calculate trend strength
        trend_strength = self.trend_strength_calc.calculate(ema_9, ema_21, price)
        
        # Check ADX override
        adx = indicators.get("adx", 25)
        adx_override = self.choppy_detector.get_trend_strength_override(adx)
        if adx_override:
            trend_strength = adx_override
        
        return TimeframeAnalysis(
            timeframe=timeframe,
            ema_9=ema_9,
            ema_21=ema_21,
            ema_50=indicators.get("ema_50", 0),
            rsi=indicators.get("rsi", 50),
            macd_line=indicators.get("macd_line", 0),
            macd_signal=indicators.get("macd_signal", 0),
            macd_histogram=indicators.get("macd_histogram", 0),
            atr=indicators.get("atr", 0),
            atr_average=indicators.get("atr_average", indicators.get("atr", 1)),
            volume_ratio=indicators.get("volume_ratio", 1),
            trend_direction=trend_dir,
            trend_strength=trend_strength,
        )
    
    def _calc_price_change(self, ohlcv: List[OHLCV]) -> float:
        """Calculate recent price change percentage."""
        if len(ohlcv) < 2:
            return 0
        return (ohlcv[-1].close - ohlcv[-2].close) / ohlcv[-2].close * 100
    
    def _log_analysis(self, symbol: str, context: MarketContext, score: ConfidenceScore):
        """Log comprehensive analysis results."""
        logger.info(
            f"{symbol} Analysis: "
            f"Score={score.total_score} ({score.confidence_level.value}), "
            f"Regime={context.market_regime.value}, "
            f"Alignment={context.trend_alignment.alignment_score:.2f}, "
            f"4H Strength={context.trend_strength_4h.value}"
        )
        logger.debug(f"{symbol} Components: {score.component_scores}")
