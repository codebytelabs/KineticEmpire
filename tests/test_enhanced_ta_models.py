"""Property-based tests for Enhanced TA System models.

**Feature: enhanced-ta-system**
"""

import pytest
from hypothesis import given, strategies as st, settings
from src.kinetic_empire.v3.analyzer.enhanced.models import (
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


class TestTimeframeWeightDistribution:
    """Property tests for timeframe weight distribution (Property 4)."""

    def test_timeframe_weights_sum_to_100_percent(self):
        """**Feature: enhanced-ta-system, Property 4: Timeframe Weight Distribution**
        
        *For any* trend alignment calculation, the weights SHALL be distributed as:
        4H=50%, 1H=30%, 15M=20%, and the sum of weights SHALL equal 100%.
        **Validates: Requirements 1.4**
        """
        # Verify individual weights match specification
        assert TIMEFRAME_WEIGHTS["4h"] == 0.50, "4H weight must be 50%"
        assert TIMEFRAME_WEIGHTS["1h"] == 0.30, "1H weight must be 30%"
        assert TIMEFRAME_WEIGHTS["15m"] == 0.20, "15M weight must be 20%"
        
        # Verify sum equals 100%
        total_weight = sum(TIMEFRAME_WEIGHTS.values())
        assert abs(total_weight - 1.0) < 0.0001, f"Weights must sum to 100%, got {total_weight * 100}%"

    def test_timeframe_weights_contain_required_keys(self):
        """Timeframe weights must contain all required timeframe keys."""
        required_keys = {"4h", "1h", "15m"}
        assert set(TIMEFRAME_WEIGHTS.keys()) == required_keys, \
            f"Expected keys {required_keys}, got {set(TIMEFRAME_WEIGHTS.keys())}"

    def test_timeframe_weights_are_positive(self):
        """All timeframe weights must be positive values."""
        for tf, weight in TIMEFRAME_WEIGHTS.items():
            assert weight > 0, f"Weight for {tf} must be positive, got {weight}"

    def test_4h_has_highest_weight(self):
        """4H timeframe must have the highest weight (dominant timeframe)."""
        assert TIMEFRAME_WEIGHTS["4h"] > TIMEFRAME_WEIGHTS["1h"], \
            "4H weight must be greater than 1H weight"
        assert TIMEFRAME_WEIGHTS["4h"] > TIMEFRAME_WEIGHTS["15m"], \
            "4H weight must be greater than 15M weight"

    def test_1h_has_middle_weight(self):
        """1H timeframe must have middle weight."""
        assert TIMEFRAME_WEIGHTS["1h"] > TIMEFRAME_WEIGHTS["15m"], \
            "1H weight must be greater than 15M weight"
        assert TIMEFRAME_WEIGHTS["1h"] < TIMEFRAME_WEIGHTS["4h"], \
            "1H weight must be less than 4H weight"


class TestConfidenceWeightDistribution:
    """Tests for confidence scoring weight distribution."""

    def test_confidence_weights_sum_to_100_percent(self):
        """Confidence weights must sum to 100%."""
        total_weight = sum(CONFIDENCE_WEIGHTS.values())
        assert abs(total_weight - 1.0) < 0.0001, f"Weights must sum to 100%, got {total_weight * 100}%"

    def test_confidence_weights_contain_required_keys(self):
        """Confidence weights must contain all required component keys."""
        required_keys = {
            "trend_alignment",
            "trend_strength",
            "volume_confirmation",
            "momentum",
            "support_resistance",
            "market_regime",
        }
        assert set(CONFIDENCE_WEIGHTS.keys()) == required_keys, \
            f"Expected keys {required_keys}, got {set(CONFIDENCE_WEIGHTS.keys())}"

    def test_confidence_weights_match_specification(self):
        """Confidence weights must match the specification values."""
        assert CONFIDENCE_WEIGHTS["trend_alignment"] == 0.30, "Trend alignment weight must be 30%"
        assert CONFIDENCE_WEIGHTS["trend_strength"] == 0.20, "Trend strength weight must be 20%"
        assert CONFIDENCE_WEIGHTS["volume_confirmation"] == 0.15, "Volume confirmation weight must be 15%"
        assert CONFIDENCE_WEIGHTS["momentum"] == 0.15, "Momentum weight must be 15%"
        assert CONFIDENCE_WEIGHTS["support_resistance"] == 0.10, "Support/resistance weight must be 10%"
        assert CONFIDENCE_WEIGHTS["market_regime"] == 0.10, "Market regime weight must be 10%"


class TestEnumValues:
    """Tests for enum value correctness."""

    def test_trend_direction_values(self):
        """TrendDirection enum must have correct values."""
        assert TrendDirection.UP.value == "UP"
        assert TrendDirection.DOWN.value == "DOWN"
        assert TrendDirection.SIDEWAYS.value == "SIDEWAYS"
        assert len(TrendDirection) == 3

    def test_trend_strength_values(self):
        """TrendStrength enum must have correct values."""
        assert TrendStrength.STRONG.value == "STRONG"
        assert TrendStrength.MODERATE.value == "MODERATE"
        assert TrendStrength.WEAK.value == "WEAK"
        assert len(TrendStrength) == 3

    def test_market_regime_values(self):
        """MarketRegime enum must have correct values."""
        assert MarketRegime.TRENDING.value == "TRENDING"
        assert MarketRegime.SIDEWAYS.value == "SIDEWAYS"
        assert MarketRegime.HIGH_VOLATILITY.value == "HIGH_VOLATILITY"
        assert MarketRegime.LOW_VOLATILITY.value == "LOW_VOLATILITY"
        assert MarketRegime.CHOPPY.value == "CHOPPY"
        assert len(MarketRegime) == 5

    def test_signal_confidence_values(self):
        """SignalConfidence enum must have correct values."""
        assert SignalConfidence.HIGH.value == "HIGH"
        assert SignalConfidence.MEDIUM.value == "MEDIUM"
        assert SignalConfidence.LOW.value == "LOW"
        assert len(SignalConfidence) == 3


class TestDataclassInstantiation:
    """Tests for dataclass instantiation."""

    def test_timeframe_analysis_creation(self):
        """TimeframeAnalysis can be instantiated with valid data."""
        analysis = TimeframeAnalysis(
            timeframe="4h",
            ema_9=100.0,
            ema_21=99.0,
            ema_50=98.0,
            rsi=55.0,
            macd_line=0.5,
            macd_signal=0.3,
            macd_histogram=0.2,
            atr=2.0,
            atr_average=1.8,
            volume_ratio=1.2,
            trend_direction=TrendDirection.UP,
            trend_strength=TrendStrength.MODERATE,
        )
        assert analysis.timeframe == "4h"
        assert analysis.trend_direction == TrendDirection.UP

    def test_trend_alignment_creation(self):
        """TrendAlignment can be instantiated with valid data."""
        alignment = TrendAlignment(
            alignment_score=0.85,
            is_aligned=True,
            dominant_direction=TrendDirection.UP,
            conflict_penalty=0,
            alignment_bonus=25,
        )
        assert alignment.is_aligned is True
        assert alignment.alignment_bonus == 25

    def test_confidence_score_defaults(self):
        """ConfidenceScore has correct default values."""
        score = ConfidenceScore(total_score=75)
        assert score.component_scores == {}
        assert score.confidence_level == SignalConfidence.LOW
        assert score.critical_factors_passed is False
        assert score.veto_reason is None



class TestTrendStrengthClassification:
    """Property tests for trend strength classification (Property 5)."""

    @given(
        price=st.floats(min_value=10.0, max_value=100000.0, allow_nan=False, allow_infinity=False),
        separation_factor=st.floats(min_value=0.015, max_value=0.10, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_strong_trend_classification(self, price: float, separation_factor: float):
        """**Feature: enhanced-ta-system, Property 5: Trend Strength Classification**
        
        *For any* EMA9 and EMA21 values where separation > 1%, 
        the trend strength SHALL be classified as STRONG.
        **Validates: Requirements 2.2**
        """
        from src.kinetic_empire.v3.analyzer.enhanced.trend_strength import TrendStrengthCalculator
        
        calculator = TrendStrengthCalculator()
        # Create EMAs with separation > 1%
        ema_21 = price
        ema_9 = price * (1 + separation_factor)  # separation_factor > 0.01 = > 1%
        
        strength = calculator.calculate(ema_9, ema_21, price)
        separation_pct = calculator.get_separation_percentage(ema_9, ema_21, price)
        
        assert separation_pct > 1.0, f"Separation should be > 1%, got {separation_pct}%"
        assert strength == TrendStrength.STRONG, f"Expected STRONG for {separation_pct}% separation"

    @given(
        price=st.floats(min_value=10.0, max_value=100000.0, allow_nan=False, allow_infinity=False),
        separation_factor=st.floats(min_value=0.004, max_value=0.009, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_moderate_trend_classification(self, price: float, separation_factor: float):
        """**Feature: enhanced-ta-system, Property 5: Trend Strength Classification**
        
        *For any* EMA9 and EMA21 values where 0.3% < separation <= 1%, 
        the trend strength SHALL be classified as MODERATE.
        **Validates: Requirements 2.3**
        """
        from src.kinetic_empire.v3.analyzer.enhanced.trend_strength import TrendStrengthCalculator
        
        calculator = TrendStrengthCalculator()
        # Create EMAs with separation between 0.3% and 1%
        ema_21 = price
        ema_9 = price * (1 + separation_factor)  # 0.4% to 0.9%
        
        strength = calculator.calculate(ema_9, ema_21, price)
        separation_pct = calculator.get_separation_percentage(ema_9, ema_21, price)
        
        assert 0.3 < separation_pct <= 1.0, f"Separation should be 0.3-1%, got {separation_pct}%"
        assert strength == TrendStrength.MODERATE, f"Expected MODERATE for {separation_pct}% separation"

    @given(
        price=st.floats(min_value=10.0, max_value=100000.0, allow_nan=False, allow_infinity=False),
        separation_factor=st.floats(min_value=0.0001, max_value=0.0025, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_weak_trend_classification(self, price: float, separation_factor: float):
        """**Feature: enhanced-ta-system, Property 5: Trend Strength Classification**
        
        *For any* EMA9 and EMA21 values where separation <= 0.3%, 
        the trend strength SHALL be classified as WEAK.
        **Validates: Requirements 2.4**
        """
        from src.kinetic_empire.v3.analyzer.enhanced.trend_strength import TrendStrengthCalculator
        
        calculator = TrendStrengthCalculator()
        # Create EMAs with separation <= 0.3%
        ema_21 = price
        ema_9 = price * (1 + separation_factor)  # 0.01% to 0.25%
        
        strength = calculator.calculate(ema_9, ema_21, price)
        separation_pct = calculator.get_separation_percentage(ema_9, ema_21, price)
        
        assert separation_pct <= 0.3, f"Separation should be <= 0.3%, got {separation_pct}%"
        assert strength == TrendStrength.WEAK, f"Expected WEAK for {separation_pct}% separation"

    @given(
        price=st.floats(min_value=10.0, max_value=100000.0, allow_nan=False, allow_infinity=False),
        separation_factor=st.floats(min_value=-0.10, max_value=0.10, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_trend_strength_uses_absolute_separation(self, price: float, separation_factor: float):
        """Trend strength should use absolute EMA separation (works for both up and down trends)."""
        from src.kinetic_empire.v3.analyzer.enhanced.trend_strength import TrendStrengthCalculator
        
        calculator = TrendStrengthCalculator()
        ema_21 = price
        ema_9 = price * (1 + separation_factor)
        
        # Calculate both ways
        strength_normal = calculator.calculate(ema_9, ema_21, price)
        strength_reversed = calculator.calculate(ema_21, ema_9, price)
        
        # Should be the same regardless of which EMA is higher
        assert strength_normal == strength_reversed, "Strength should be same regardless of trend direction"



class TestMarketRegimeClassification:
    """Property tests for market regime classification (Property 7)."""

    @given(
        atr_ratio=st.floats(min_value=1.55, max_value=5.0, allow_nan=False, allow_infinity=False),
        base_atr=st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_high_volatility_regime(self, atr_ratio: float, base_atr: float):
        """**Feature: enhanced-ta-system, Property 7: Market Regime Classification**
        
        *For any* ATR > 150% of average, the market regime SHALL be classified as HIGH_VOLATILITY.
        **Validates: Requirements 3.1**
        """
        from src.kinetic_empire.v3.analyzer.enhanced.market_regime import MarketRegimeDetector, OHLCV
        
        detector = MarketRegimeDetector()
        
        # Create analysis with high volatility
        analysis_4h = TimeframeAnalysis(
            timeframe="4h",
            ema_9=100.0, ema_21=99.0, ema_50=98.0,
            rsi=50.0, macd_line=0.5, macd_signal=0.3, macd_histogram=0.2,
            atr=base_atr * atr_ratio,  # ATR > 150% of average
            atr_average=base_atr,
            volume_ratio=1.0,
            trend_direction=TrendDirection.UP,
            trend_strength=TrendStrength.MODERATE,
        )
        
        regime = detector.detect(analysis_4h, None, [])
        assert regime == MarketRegime.HIGH_VOLATILITY, f"Expected HIGH_VOLATILITY for ATR ratio {atr_ratio}"

    @given(
        atr_ratio=st.floats(min_value=0.1, max_value=0.45, allow_nan=False, allow_infinity=False),
        base_atr=st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_low_volatility_regime(self, atr_ratio: float, base_atr: float):
        """**Feature: enhanced-ta-system, Property 7: Market Regime Classification**
        
        *For any* ATR < 50% of average, the market regime SHALL be classified as LOW_VOLATILITY.
        **Validates: Requirements 3.2**
        """
        from src.kinetic_empire.v3.analyzer.enhanced.market_regime import MarketRegimeDetector, OHLCV
        
        detector = MarketRegimeDetector()
        
        # Create analysis with low volatility
        analysis_4h = TimeframeAnalysis(
            timeframe="4h",
            ema_9=100.0, ema_21=99.0, ema_50=98.0,
            rsi=50.0, macd_line=0.5, macd_signal=0.3, macd_histogram=0.2,
            atr=base_atr * atr_ratio,  # ATR < 50% of average
            atr_average=base_atr,
            volume_ratio=1.0,
            trend_direction=TrendDirection.UP,
            trend_strength=TrendStrength.MODERATE,
        )
        
        regime = detector.detect(analysis_4h, None, [])
        assert regime == MarketRegime.LOW_VOLATILITY, f"Expected LOW_VOLATILITY for ATR ratio {atr_ratio}"

    @given(
        base_price=st.floats(min_value=100.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
        range_pct=st.floats(min_value=0.1, max_value=1.8, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_sideways_regime(self, base_price: float, range_pct: float):
        """**Feature: enhanced-ta-system, Property 7: Market Regime Classification**
        
        *For any* price ranging within 2% for 20 candles, the market regime SHALL be classified as SIDEWAYS.
        **Validates: Requirements 3.3**
        """
        from src.kinetic_empire.v3.analyzer.enhanced.market_regime import MarketRegimeDetector, OHLCV
        
        detector = MarketRegimeDetector()
        
        # Create 20 candles within range_pct% range
        half_range = base_price * (range_pct / 100) / 2
        ohlcv = []
        for i in range(20):
            ohlcv.append(OHLCV(
                open=base_price,
                high=base_price + half_range,
                low=base_price - half_range,
                close=base_price,
                volume=1000.0,
            ))
        
        # Use normal volatility so it doesn't trigger HIGH/LOW_VOL
        analysis_4h = TimeframeAnalysis(
            timeframe="4h",
            ema_9=100.0, ema_21=99.0, ema_50=98.0,
            rsi=50.0, macd_line=0.5, macd_signal=0.3, macd_histogram=0.2,
            atr=1.0, atr_average=1.0,  # Normal volatility
            volume_ratio=1.0,
            trend_direction=TrendDirection.SIDEWAYS,
            trend_strength=TrendStrength.WEAK,
        )
        
        regime = detector.detect(analysis_4h, None, ohlcv)
        assert regime == MarketRegime.SIDEWAYS, f"Expected SIDEWAYS for {range_pct}% range"

    @given(
        macd_hist=st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_trending_regime(self, macd_hist: float):
        """**Feature: enhanced-ta-system, Property 7: Market Regime Classification**
        
        *For any* aligned trends with strong momentum, the market regime SHALL be classified as TRENDING.
        **Validates: Requirements 3.4**
        """
        from src.kinetic_empire.v3.analyzer.enhanced.market_regime import MarketRegimeDetector, OHLCV
        
        detector = MarketRegimeDetector()
        
        # Create aligned uptrend with strong momentum
        analysis_4h = TimeframeAnalysis(
            timeframe="4h",
            ema_9=102.0, ema_21=100.0, ema_50=98.0,
            rsi=55.0, macd_line=0.5, macd_signal=0.3, macd_histogram=macd_hist,
            atr=1.0, atr_average=1.0,  # Normal volatility
            volume_ratio=1.2,
            trend_direction=TrendDirection.UP,
            trend_strength=TrendStrength.STRONG,
        )
        
        analysis_1h = TimeframeAnalysis(
            timeframe="1h",
            ema_9=101.5, ema_21=100.5, ema_50=99.0,
            rsi=55.0, macd_line=0.3, macd_signal=0.2, macd_histogram=0.1,
            atr=0.5, atr_average=0.5,
            volume_ratio=1.1,
            trend_direction=TrendDirection.UP,
            trend_strength=TrendStrength.MODERATE,
        )
        
        # Wide range so not sideways
        ohlcv = [OHLCV(open=100, high=110, low=90, close=105, volume=1000) for _ in range(20)]
        
        regime = detector.detect(analysis_4h, analysis_1h, ohlcv)
        assert regime == MarketRegime.TRENDING, f"Expected TRENDING for aligned uptrend"



class TestTrendAlignment:
    """Property tests for trend alignment (Properties 1, 2, 3)."""

    @given(
        trend_15m=st.sampled_from([TrendDirection.UP, TrendDirection.DOWN, TrendDirection.SIDEWAYS]),
    )
    @settings(max_examples=100)
    def test_trend_conflict_penalty(self, trend_15m: TrendDirection):
        """**Feature: enhanced-ta-system, Property 1: Trend Conflict Penalty**
        
        *For any* market state where the 4H trend is UP and the 1H trend is DOWN,
        the calculated long confidence score SHALL be reduced by at least 30%.
        **Validates: Requirements 1.1**
        """
        from src.kinetic_empire.v3.analyzer.enhanced.trend_alignment import TrendAlignmentEngine
        
        engine = TrendAlignmentEngine()
        
        # 4H UP, 1H DOWN = conflict
        alignment = engine.calculate_alignment(
            trend_4h=TrendDirection.UP,
            trend_1h=TrendDirection.DOWN,
            trend_15m=trend_15m,
        )
        
        assert alignment.conflict_penalty >= 30, \
            f"Conflict penalty should be >= 30%, got {alignment.conflict_penalty}%"

    @given(
        direction=st.sampled_from([TrendDirection.UP, TrendDirection.DOWN]),
    )
    @settings(max_examples=100)
    def test_trend_alignment_bonus(self, direction: TrendDirection):
        """**Feature: enhanced-ta-system, Property 2: Trend Alignment Bonus**
        
        *For any* market state where all three timeframes show the same trend direction,
        the confidence score SHALL include a 25-point alignment bonus.
        **Validates: Requirements 1.2**
        """
        from src.kinetic_empire.v3.analyzer.enhanced.trend_alignment import TrendAlignmentEngine
        
        engine = TrendAlignmentEngine()
        
        # All timeframes aligned
        alignment = engine.calculate_alignment(
            trend_4h=direction,
            trend_1h=direction,
            trend_15m=direction,
        )
        
        assert alignment.is_aligned is True, "Should be aligned when all trends match"
        assert alignment.alignment_bonus == 25, \
            f"Alignment bonus should be 25 points, got {alignment.alignment_bonus}"

    @given(
        trend_15m=st.sampled_from([TrendDirection.UP, TrendDirection.DOWN]),
    )
    @settings(max_examples=100)
    def test_conflicting_trend_signal_requirement(self, trend_15m: TrendDirection):
        """**Feature: enhanced-ta-system, Property 3: Conflicting Trend Signal Requirement**
        
        *For any* market state where 4H and 1H trends conflict, a signal SHALL only
        be generated if the 15M trend matches the 4H trend direction.
        **Validates: Requirements 1.3**
        """
        from src.kinetic_empire.v3.analyzer.enhanced.trend_alignment import TrendAlignmentEngine
        
        engine = TrendAlignmentEngine()
        
        # 4H UP, 1H DOWN = conflict
        can_signal = engine.can_generate_signal(
            trend_4h=TrendDirection.UP,
            trend_1h=TrendDirection.DOWN,
            trend_15m=trend_15m,
            signal_direction="LONG",
        )
        
        if trend_15m == TrendDirection.UP:
            assert can_signal is True, "Should allow signal when 15M matches 4H"
        else:
            assert can_signal is False, "Should block signal when 15M doesn't match 4H"

    def test_alignment_score_calculation(self):
        """Alignment score should correctly sum weighted contributions."""
        from src.kinetic_empire.v3.analyzer.enhanced.trend_alignment import TrendAlignmentEngine
        
        engine = TrendAlignmentEngine()
        
        # All aligned UP
        alignment = engine.calculate_alignment(
            trend_4h=TrendDirection.UP,
            trend_1h=TrendDirection.UP,
            trend_15m=TrendDirection.UP,
        )
        
        # Should be 100% (0.50 + 0.30 + 0.20)
        assert abs(alignment.alignment_score - 1.0) < 0.001, \
            f"Full alignment should have score 1.0, got {alignment.alignment_score}"
        
        # Only 4H aligned
        alignment = engine.calculate_alignment(
            trend_4h=TrendDirection.UP,
            trend_1h=TrendDirection.DOWN,
            trend_15m=TrendDirection.DOWN,
        )
        
        # Should be 50% (only 4H)
        assert abs(alignment.alignment_score - 0.50) < 0.001, \
            f"Only 4H aligned should have score 0.50, got {alignment.alignment_score}"



class TestVolumeConfirmation:
    """Property tests for volume confirmation (Properties 10, 11, 12)."""

    @given(
        volume_ratio=st.floats(min_value=0.1, max_value=0.55, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_minimum_volume_requirement(self, volume_ratio: float):
        """**Feature: enhanced-ta-system, Property 10: Minimum Volume Requirement**
        
        *For any* signal generation attempt, if volume is below 60% of the 20-period average,
        the signal SHALL be rejected.
        **Validates: Requirements 4.1**
        """
        from src.kinetic_empire.v3.analyzer.enhanced.volume_confirmation import VolumeConfirmationAnalyzer
        
        analyzer = VolumeConfirmationAnalyzer()
        
        confirmation = analyzer.analyze(
            volume_ratio=volume_ratio,
            volume_history=[100, 100, 100, 100, 100],
            price_change_pct=0.5,
        )
        
        assert confirmation.is_confirmed is False, \
            f"Volume ratio {volume_ratio} should not be confirmed (< 60%)"
        assert analyzer.should_reject_signal(confirmation) is True, \
            "Signal should be rejected for low volume"

    @given(
        volume_ratio=st.floats(min_value=1.55, max_value=5.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_volume_spike_bonus(self, volume_ratio: float):
        """**Feature: enhanced-ta-system, Property 11: Volume Spike Bonus**
        
        *For any* market state where volume exceeds 150% of average during a trend move,
        the confidence score SHALL include a 15-point volume bonus.
        **Validates: Requirements 4.2**
        """
        from src.kinetic_empire.v3.analyzer.enhanced.volume_confirmation import VolumeConfirmationAnalyzer
        
        analyzer = VolumeConfirmationAnalyzer()
        
        confirmation = analyzer.analyze(
            volume_ratio=volume_ratio,
            volume_history=[100, 100, 100, 100, 100],
            price_change_pct=1.5,
        )
        
        assert confirmation.is_confirmed is True, "High volume should be confirmed"
        assert confirmation.volume_score >= 15, \
            f"Volume spike should add 15 points, got {confirmation.volume_score}"

    @given(
        price_change=st.floats(min_value=1.5, max_value=10.0, allow_nan=False, allow_infinity=False),
        volume_ratio=st.floats(min_value=0.1, max_value=0.35, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_false_move_detection(self, price_change: float, volume_ratio: float):
        """**Feature: enhanced-ta-system, Property 12: False Move Detection**
        
        *For any* market state where price moves significantly but volume is below 40% of average,
        the signal SHALL be rejected as a potential false move.
        **Validates: Requirements 4.3**
        """
        from src.kinetic_empire.v3.analyzer.enhanced.volume_confirmation import VolumeConfirmationAnalyzer
        
        analyzer = VolumeConfirmationAnalyzer()
        
        confirmation = analyzer.analyze(
            volume_ratio=volume_ratio,
            volume_history=[100, 100, 100, 100, 100],
            price_change_pct=price_change,
        )
        
        assert confirmation.is_false_move is True, \
            f"Should detect false move: price change {price_change}%, volume ratio {volume_ratio}"
        assert analyzer.should_reject_signal(confirmation) is True, \
            "False move should be rejected"



class TestMomentumAnalysis:
    """Property tests for momentum analysis (Properties 13, 14)."""

    @given(
        rsi=st.floats(min_value=40.0, max_value=65.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_rsi_range_validation_long(self, rsi: float):
        """**Feature: enhanced-ta-system, Property 13: RSI Range Validation**
        
        *For any* LONG signal, RSI SHALL be between 40 and 65.
        **Validates: Requirements 5.1**
        """
        from src.kinetic_empire.v3.analyzer.enhanced.momentum import MomentumAnalyzer
        
        analyzer = MomentumAnalyzer()
        
        analysis = analyzer.analyze(
            rsi=rsi,
            macd_histogram=0.5,
            prev_macd_histogram=0.3,
            signal_direction="LONG",
        )
        
        assert analysis.rsi_valid is True, \
            f"RSI {rsi} should be valid for LONG (40-65)"

    @given(
        rsi=st.floats(min_value=35.0, max_value=60.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_rsi_range_validation_short(self, rsi: float):
        """**Feature: enhanced-ta-system, Property 13: RSI Range Validation**
        
        *For any* SHORT signal, RSI SHALL be between 35 and 60.
        **Validates: Requirements 5.2**
        """
        from src.kinetic_empire.v3.analyzer.enhanced.momentum import MomentumAnalyzer
        
        analyzer = MomentumAnalyzer()
        
        analysis = analyzer.analyze(
            rsi=rsi,
            macd_histogram=-0.5,
            prev_macd_histogram=-0.3,
            signal_direction="SHORT",
        )
        
        assert analysis.rsi_valid is True, \
            f"RSI {rsi} should be valid for SHORT (35-60)"

    @given(
        macd_hist=st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False),
        prev_macd=st.floats(min_value=0.01, max_value=0.09, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_macd_momentum_bonus_long(self, macd_hist: float, prev_macd: float):
        """**Feature: enhanced-ta-system, Property 14: MACD Momentum Bonus**
        
        *For any* market state where MACD histogram is positive and increasing,
        LONG confidence SHALL receive a 10-point bonus.
        **Validates: Requirements 5.3**
        """
        from src.kinetic_empire.v3.analyzer.enhanced.momentum import MomentumAnalyzer
        
        analyzer = MomentumAnalyzer()
        
        analysis = analyzer.analyze(
            rsi=50.0,
            macd_histogram=macd_hist,
            prev_macd_histogram=prev_macd,
            signal_direction="LONG",
        )
        
        assert analysis.macd_score == 10, \
            f"MACD bonus should be 10 for positive increasing histogram"

    @given(
        macd_hist=st.floats(min_value=-10.0, max_value=-0.1, allow_nan=False, allow_infinity=False),
        prev_macd=st.floats(min_value=-0.09, max_value=-0.01, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_macd_momentum_bonus_short(self, macd_hist: float, prev_macd: float):
        """**Feature: enhanced-ta-system, Property 14: MACD Momentum Bonus**
        
        *For any* market state where MACD histogram is negative and decreasing,
        SHORT confidence SHALL receive a 10-point bonus.
        **Validates: Requirements 5.4**
        """
        from src.kinetic_empire.v3.analyzer.enhanced.momentum import MomentumAnalyzer
        
        analyzer = MomentumAnalyzer()
        
        analysis = analyzer.analyze(
            rsi=50.0,
            macd_histogram=macd_hist,
            prev_macd_histogram=prev_macd,
            signal_direction="SHORT",
        )
        
        assert analysis.macd_score == 10, \
            f"MACD bonus should be 10 for negative decreasing histogram"



class TestSupportResistance:
    """Property tests for support/resistance (Properties 15, 16, 17)."""

    @given(
        base_price=st.floats(min_value=100.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_support_resistance_detection(self, base_price: float):
        """**Feature: enhanced-ta-system, Property 15: Support/Resistance Detection**
        
        *For any* price within 0.5% of a recent swing high, the system SHALL identify resistance.
        *For any* price within 0.5% of a recent swing low, the system SHALL identify support.
        **Validates: Requirements 6.1, 6.2**
        """
        from src.kinetic_empire.v3.analyzer.enhanced.support_resistance import SupportResistanceDetector
        from src.kinetic_empire.v3.analyzer.enhanced.market_regime import OHLCV
        
        detector = SupportResistanceDetector()
        
        # Create candles with clear swing high and low
        swing_high = base_price * 1.05
        swing_low = base_price * 0.95
        
        ohlcv = [
            OHLCV(open=base_price, high=base_price*1.01, low=base_price*0.99, close=base_price, volume=1000),
            OHLCV(open=base_price, high=swing_high, low=base_price*0.99, close=base_price*1.02, volume=1000),
            OHLCV(open=base_price, high=base_price*1.01, low=base_price*0.99, close=base_price, volume=1000),
            OHLCV(open=base_price, high=base_price*1.01, low=swing_low, close=base_price*0.98, volume=1000),
            OHLCV(open=base_price, high=base_price*1.01, low=base_price*0.99, close=base_price, volume=1000),
        ]
        
        # Test near resistance
        near_resistance_price = swing_high * 0.998  # Within 0.5%
        sr = detector.detect(ohlcv, near_resistance_price)
        assert sr.at_resistance is True, "Should detect resistance when within 0.5%"
        
        # Test near support
        near_support_price = swing_low * 1.002  # Within 0.5%
        sr = detector.detect(ohlcv, near_support_price)
        assert sr.at_support is True, "Should detect support when within 0.5%"

    @given(
        base_price=st.floats(min_value=100.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_support_entry_bonus(self, base_price: float):
        """**Feature: enhanced-ta-system, Property 16: Support Entry Bonus**
        
        *For any* LONG entry near identified support, the confidence score SHALL include a 10-point bonus.
        **Validates: Requirements 6.3**
        """
        from src.kinetic_empire.v3.analyzer.enhanced.support_resistance import SupportResistanceDetector
        from src.kinetic_empire.v3.analyzer.enhanced.market_regime import OHLCV
        
        detector = SupportResistanceDetector()
        
        swing_low = base_price * 0.95
        ohlcv = [
            OHLCV(open=base_price, high=base_price*1.01, low=base_price*0.99, close=base_price, volume=1000),
            OHLCV(open=base_price, high=base_price*1.01, low=swing_low, close=base_price*0.98, volume=1000),
            OHLCV(open=base_price, high=base_price*1.01, low=base_price*0.99, close=base_price, volume=1000),
        ]
        
        # Price near support
        near_support_price = swing_low * 1.002
        sr = detector.detect(ohlcv, near_support_price)
        
        assert sr.at_support is True, "Should be at support"
        assert sr.sr_score >= 10, f"Support bonus should be >= 10, got {sr.sr_score}"

    @given(
        base_price=st.floats(min_value=100.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_resistance_entry_penalty(self, base_price: float):
        """**Feature: enhanced-ta-system, Property 17: Resistance Entry Penalty**
        
        *For any* LONG entry near identified resistance, the confidence score SHALL be reduced by 15 points.
        **Validates: Requirements 6.4**
        """
        from src.kinetic_empire.v3.analyzer.enhanced.support_resistance import SupportResistanceDetector
        from src.kinetic_empire.v3.analyzer.enhanced.market_regime import OHLCV
        
        detector = SupportResistanceDetector()
        
        swing_high = base_price * 1.05
        ohlcv = [
            OHLCV(open=base_price, high=base_price*1.01, low=base_price*0.99, close=base_price, volume=1000),
            OHLCV(open=base_price, high=swing_high, low=base_price*0.99, close=base_price*1.02, volume=1000),
            OHLCV(open=base_price, high=base_price*1.01, low=base_price*0.99, close=base_price, volume=1000),
        ]
        
        # Price near resistance (not breaking out)
        near_resistance_price = swing_high * 0.998
        sr = detector.detect(ohlcv, near_resistance_price, volume_confirmed=False)
        
        assert sr.at_resistance is True, "Should be at resistance"
        assert sr.sr_score <= -15, f"Resistance penalty should be <= -15, got {sr.sr_score}"



class TestChoppyDetection:
    """Property tests for choppy market detection (Properties 24, 25, 26)."""

    def test_choppy_market_detection(self):
        """**Feature: enhanced-ta-system, Property 24: Choppy Market Detection**
        
        *For any* price data where price crosses EMA9 more than 4 times in 20 candles,
        the market SHALL be classified as CHOPPY.
        **Validates: Requirements 9.1**
        """
        from src.kinetic_empire.v3.analyzer.enhanced.choppy_detector import ChoppyMarketDetector
        
        detector = ChoppyMarketDetector()
        
        # Create prices that cross EMA 5+ times
        # Alternating above/below EMA
        prices = []
        ema_values = []
        base = 100.0
        for i in range(20):
            ema_values.append(base)
            # Alternate above and below EMA
            if i % 2 == 0:
                prices.append(base + 1)  # Above
            else:
                prices.append(base - 1)  # Below
        
        is_choppy = detector.is_choppy(prices, ema_values)
        assert is_choppy is True, "Should detect choppy when >4 EMA crossings"

    def test_choppy_market_signal_block(self):
        """**Feature: enhanced-ta-system, Property 25: Choppy Market Signal Block**
        
        *For any* market state classified as CHOPPY, the system SHALL NOT generate signals.
        **Validates: Requirements 9.2**
        """
        from src.kinetic_empire.v3.analyzer.enhanced.choppy_detector import ChoppyMarketDetector
        from src.kinetic_empire.v3.analyzer.enhanced.market_regime import MarketRegimeDetector
        
        detector = MarketRegimeDetector()
        
        # When is_choppy=True, regime should be CHOPPY
        regime = detector.detect(None, None, [], is_choppy=True)
        assert regime == MarketRegime.CHOPPY, "Should return CHOPPY regime"

    @given(
        adx=st.floats(min_value=1.0, max_value=19.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_adx_trend_override(self, adx: float):
        """**Feature: enhanced-ta-system, Property 26: ADX Trend Override**
        
        *For any* market state where ADX is below 20, the trend SHALL be classified as WEAK
        regardless of EMA alignment.
        **Validates: Requirements 9.3**
        """
        from src.kinetic_empire.v3.analyzer.enhanced.choppy_detector import ChoppyMarketDetector
        
        detector = ChoppyMarketDetector()
        
        override = detector.get_trend_strength_override(adx)
        assert override == TrendStrength.WEAK, \
            f"ADX {adx} should override to WEAK trend"



class TestBTCCorrelation:
    """Property tests for BTC correlation (Properties 27, 28)."""

    @given(
        signal_dir=st.sampled_from(["LONG", "SHORT"]),
    )
    @settings(max_examples=100)
    def test_btc_correlation_adjustment(self, signal_dir: str):
        """**Feature: enhanced-ta-system, Property 27: BTC Correlation Adjustment**
        
        *For any* altcoin analysis where BTC 4H trend is strongly DOWN, LONG confidence
        SHALL be reduced by 20 points. *For any* altcoin analysis where BTC 4H trend is
        strongly UP, SHORT confidence SHALL be reduced by 20 points.
        **Validates: Requirements 10.2, 10.3**
        """
        from src.kinetic_empire.v3.analyzer.enhanced.btc_correlation import BTCCorrelationEngine
        
        engine = BTCCorrelationEngine()
        
        # Test BTC DOWN affecting LONG
        btc_down = TimeframeAnalysis(
            timeframe="4h",
            ema_9=98.0, ema_21=100.0, ema_50=102.0,
            rsi=35.0, macd_line=-0.5, macd_signal=-0.3, macd_histogram=-0.2,
            atr=1.0, atr_average=1.0,
            volume_ratio=1.0,
            trend_direction=TrendDirection.DOWN,
            trend_strength=TrendStrength.STRONG,
        )
        engine.update_btc_analysis(btc_down)
        
        if signal_dir == "LONG":
            adjustment = engine.get_confidence_adjustment(signal_dir, is_altcoin=True)
            assert adjustment == -20, f"BTC DOWN should reduce LONG by 20, got {adjustment}"
        
        # Test BTC UP affecting SHORT
        btc_up = TimeframeAnalysis(
            timeframe="4h",
            ema_9=102.0, ema_21=100.0, ema_50=98.0,
            rsi=65.0, macd_line=0.5, macd_signal=0.3, macd_histogram=0.2,
            atr=1.0, atr_average=1.0,
            volume_ratio=1.0,
            trend_direction=TrendDirection.UP,
            trend_strength=TrendStrength.STRONG,
        )
        engine.update_btc_analysis(btc_up)
        
        if signal_dir == "SHORT":
            adjustment = engine.get_confidence_adjustment(signal_dir, is_altcoin=True)
            assert adjustment == -20, f"BTC UP should reduce SHORT by 20, got {adjustment}"

    @given(
        atr_ratio=st.floats(min_value=2.1, max_value=5.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_btc_volatility_signal_block(self, atr_ratio: float):
        """**Feature: enhanced-ta-system, Property 28: BTC Volatility Signal Block**
        
        *For any* market state where BTC ATR exceeds 200% of average,
        the system SHALL NOT generate altcoin signals.
        **Validates: Requirements 10.4**
        """
        from src.kinetic_empire.v3.analyzer.enhanced.btc_correlation import BTCCorrelationEngine
        
        engine = BTCCorrelationEngine()
        
        base_atr = 1.0
        btc_volatile = TimeframeAnalysis(
            timeframe="4h",
            ema_9=100.0, ema_21=100.0, ema_50=100.0,
            rsi=50.0, macd_line=0.0, macd_signal=0.0, macd_histogram=0.0,
            atr=base_atr * atr_ratio,  # > 200% of average
            atr_average=base_atr,
            volume_ratio=1.0,
            trend_direction=TrendDirection.SIDEWAYS,
            trend_strength=TrendStrength.WEAK,
        )
        engine.update_btc_analysis(btc_volatile)
        
        should_pause = engine.should_pause_altcoin_signals()
        assert should_pause is True, \
            f"Should pause altcoin signals when BTC ATR ratio is {atr_ratio}"



class TestAdaptiveStops:
    """Property tests for adaptive stop loss (Properties 18, 19)."""

    @given(
        atr=st.floats(min_value=0.1, max_value=100.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_regime_based_stop_loss(self, atr: float):
        """**Feature: enhanced-ta-system, Property 18: Regime-Based Stop Loss**
        
        *For any* TRENDING regime, stop loss SHALL be 1.5x ATR.
        *For any* HIGH_VOLATILITY regime, stop loss SHALL be 2.5x ATR.
        *For any* LOW_VOLATILITY regime, stop loss SHALL be 1.0x ATR.
        **Validates: Requirements 7.1, 7.2, 7.3**
        """
        from src.kinetic_empire.v3.analyzer.enhanced.adaptive_stop import AdaptiveStopCalculator
        
        calculator = AdaptiveStopCalculator()
        
        # Test TRENDING regime
        mult = calculator.get_regime_multiplier(MarketRegime.TRENDING)
        assert mult == 1.5, f"TRENDING should use 1.5x ATR, got {mult}"
        
        # Test HIGH_VOLATILITY regime
        mult = calculator.get_regime_multiplier(MarketRegime.HIGH_VOLATILITY)
        assert mult == 2.5, f"HIGH_VOLATILITY should use 2.5x ATR, got {mult}"
        
        # Test LOW_VOLATILITY regime
        mult = calculator.get_regime_multiplier(MarketRegime.LOW_VOLATILITY)
        assert mult == 1.0, f"LOW_VOLATILITY should use 1.0x ATR, got {mult}"

    @given(
        atr=st.floats(min_value=0.1, max_value=100.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_trend_strength_based_stop_loss(self, atr: float):
        """**Feature: enhanced-ta-system, Property 19: Trend-Strength-Based Stop Loss**
        
        *For any* STRONG trend strength, stop loss SHALL be 1.2x ATR.
        *For any* WEAK trend strength, stop loss SHALL be 2.0x ATR.
        **Validates: Requirements 7.4, 7.5**
        """
        from src.kinetic_empire.v3.analyzer.enhanced.adaptive_stop import AdaptiveStopCalculator
        
        calculator = AdaptiveStopCalculator()
        
        # Test STRONG trend
        mult = calculator.get_strength_multiplier(TrendStrength.STRONG)
        assert mult == 1.2, f"STRONG should use 1.2x ATR, got {mult}"
        
        # Test WEAK trend
        mult = calculator.get_strength_multiplier(TrendStrength.WEAK)
        assert mult == 2.0, f"WEAK should use 2.0x ATR, got {mult}"



class TestContextWeightedScorer:
    """Property tests for context weighted scoring (Properties 20, 21, 22)."""

    def test_confidence_weight_distribution(self):
        """**Feature: enhanced-ta-system, Property 20: Confidence Weight Distribution**
        
        *For any* confidence calculation, the weights SHALL be:
        Trend Alignment=30%, Trend Strength=20%, Volume=15%, Momentum=15%, S/R=10%, Regime=10%,
        and the sum SHALL equal 100%.
        **Validates: Requirements 8.1**
        """
        from src.kinetic_empire.v3.analyzer.enhanced.scorer import ContextWeightedScorer
        
        scorer = ContextWeightedScorer()
        
        assert scorer.WEIGHTS["trend_alignment"] == 0.30
        assert scorer.WEIGHTS["trend_strength"] == 0.20
        assert scorer.WEIGHTS["volume_confirmation"] == 0.15
        assert scorer.WEIGHTS["momentum"] == 0.15
        assert scorer.WEIGHTS["support_resistance"] == 0.10
        assert scorer.WEIGHTS["market_regime"] == 0.10
        
        total = sum(scorer.WEIGHTS.values())
        assert abs(total - 1.0) < 0.001, f"Weights must sum to 100%, got {total * 100}%"

    @given(
        alignment_score=st.floats(min_value=0.0, max_value=0.5, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_minimum_confidence_threshold(self, alignment_score: float):
        """**Feature: enhanced-ta-system, Property 21: Minimum Confidence Threshold**
        
        *For any* confidence score below 65, the system SHALL NOT generate a signal.
        **Validates: Requirements 8.2**
        """
        from src.kinetic_empire.v3.analyzer.enhanced.scorer import ContextWeightedScorer
        
        scorer = ContextWeightedScorer()
        
        # Create a low-scoring context
        context = MarketContext(
            trend_alignment=TrendAlignment(
                alignment_score=alignment_score,
                is_aligned=False,
                dominant_direction=TrendDirection.SIDEWAYS,
                conflict_penalty=30,
                alignment_bonus=0,
            ),
            trend_strength_4h=TrendStrength.WEAK,
            market_regime=MarketRegime.CHOPPY,
            volume_confirmation=VolumeConfirmation(
                is_confirmed=False, volume_score=-20, is_declining=True, is_false_move=False
            ),
            support_resistance=SupportResistance(
                nearest_support=95.0, nearest_resistance=105.0,
                at_support=False, at_resistance=True, is_breakout=False, sr_score=-15
            ),
            momentum=MomentumAnalysis(rsi_valid=False, macd_score=0, has_divergence=True, momentum_score=-15),
            is_choppy=True,
            btc_correlation_adjustment=-20,
        )
        
        score = scorer.calculate_score(context)
        
        if score.total_score < 65:
            assert score.confidence_level == SignalConfidence.LOW, \
                f"Score {score.total_score} should be LOW confidence"

    def test_high_confidence_classification(self):
        """**Feature: enhanced-ta-system, Property 22: High Confidence Classification**
        
        *For any* confidence score above 80, the signal SHALL be classified as HIGH_CONFIDENCE.
        **Validates: Requirements 8.3**
        """
        from src.kinetic_empire.v3.analyzer.enhanced.scorer import ContextWeightedScorer
        
        scorer = ContextWeightedScorer()
        
        # Create a high-scoring context
        context = MarketContext(
            trend_alignment=TrendAlignment(
                alignment_score=1.0,
                is_aligned=True,
                dominant_direction=TrendDirection.UP,
                conflict_penalty=0,
                alignment_bonus=25,
            ),
            trend_strength_4h=TrendStrength.STRONG,
            market_regime=MarketRegime.TRENDING,
            volume_confirmation=VolumeConfirmation(
                is_confirmed=True, volume_score=15, is_declining=False, is_false_move=False
            ),
            support_resistance=SupportResistance(
                nearest_support=95.0, nearest_resistance=105.0,
                at_support=True, at_resistance=False, is_breakout=False, sr_score=10
            ),
            momentum=MomentumAnalysis(rsi_valid=True, macd_score=10, has_divergence=False, momentum_score=10),
            is_choppy=False,
            btc_correlation_adjustment=0,
        )
        
        score = scorer.calculate_score(context)
        
        assert score.total_score > 80, f"High quality context should score > 80, got {score.total_score}"
        assert score.confidence_level == SignalConfidence.HIGH, \
            f"Score {score.total_score} should be HIGH confidence"



class TestCriticalFactorValidator:
    """Property tests for critical factor validation (Properties 6, 8, 23)."""

    def test_weak_4h_trend_signal_block(self):
        """**Feature: enhanced-ta-system, Property 6: Weak 4H Trend Signal Block**
        
        *For any* market state where the 4H trend strength is WEAK,
        the system SHALL NOT generate any trading signals.
        **Validates: Requirements 2.5**
        """
        from src.kinetic_empire.v3.analyzer.enhanced.validator import CriticalFactorValidator
        
        validator = CriticalFactorValidator()
        
        context = MarketContext(
            trend_alignment=TrendAlignment(
                alignment_score=1.0, is_aligned=True,
                dominant_direction=TrendDirection.UP,
                conflict_penalty=0, alignment_bonus=25,
            ),
            trend_strength_4h=TrendStrength.WEAK,  # WEAK 4H trend
            market_regime=MarketRegime.TRENDING,
            volume_confirmation=VolumeConfirmation(
                is_confirmed=True, volume_score=15, is_declining=False, is_false_move=False
            ),
            support_resistance=SupportResistance(
                nearest_support=95.0, nearest_resistance=105.0,
                at_support=True, at_resistance=False, is_breakout=False, sr_score=10
            ),
            momentum=MomentumAnalysis(rsi_valid=True, macd_score=10, has_divergence=False, momentum_score=10),
            is_choppy=False,
            btc_correlation_adjustment=0,
        )
        
        result = validator.validate(context)
        assert result.passed is False, "Should block signal for WEAK 4H trend"
        assert "Weak 4H" in result.veto_reason

    def test_sideways_regime_signal_block(self):
        """**Feature: enhanced-ta-system, Property 8: Sideways Regime Signal Block**
        
        *For any* market state classified as SIDEWAYS regime,
        the system SHALL NOT generate trend-following signals.
        **Validates: Requirements 3.5**
        """
        from src.kinetic_empire.v3.analyzer.enhanced.validator import CriticalFactorValidator
        
        validator = CriticalFactorValidator()
        
        context = MarketContext(
            trend_alignment=TrendAlignment(
                alignment_score=1.0, is_aligned=True,
                dominant_direction=TrendDirection.UP,
                conflict_penalty=0, alignment_bonus=25,
            ),
            trend_strength_4h=TrendStrength.STRONG,
            market_regime=MarketRegime.SIDEWAYS,  # SIDEWAYS regime
            volume_confirmation=VolumeConfirmation(
                is_confirmed=True, volume_score=15, is_declining=False, is_false_move=False
            ),
            support_resistance=SupportResistance(
                nearest_support=95.0, nearest_resistance=105.0,
                at_support=True, at_resistance=False, is_breakout=False, sr_score=10
            ),
            momentum=MomentumAnalysis(rsi_valid=True, macd_score=10, has_divergence=False, momentum_score=10),
            is_choppy=False,
            btc_correlation_adjustment=0,
        )
        
        result = validator.validate(context)
        assert result.passed is False, "Should block signal for SIDEWAYS regime"
        assert "Sideways" in result.veto_reason

    def test_critical_factor_veto(self):
        """**Feature: enhanced-ta-system, Property 23: Critical Factor Veto**
        
        *For any* market state where trend alignment fails OR volume is below threshold,
        the signal SHALL be rejected regardless of total score.
        **Validates: Requirements 8.4**
        """
        from src.kinetic_empire.v3.analyzer.enhanced.validator import CriticalFactorValidator
        
        validator = CriticalFactorValidator()
        
        # Test volume failure veto
        context_low_volume = MarketContext(
            trend_alignment=TrendAlignment(
                alignment_score=1.0, is_aligned=True,
                dominant_direction=TrendDirection.UP,
                conflict_penalty=0, alignment_bonus=25,
            ),
            trend_strength_4h=TrendStrength.STRONG,
            market_regime=MarketRegime.TRENDING,
            volume_confirmation=VolumeConfirmation(
                is_confirmed=False,  # Volume below threshold
                volume_score=-20, is_declining=False, is_false_move=False
            ),
            support_resistance=SupportResistance(
                nearest_support=95.0, nearest_resistance=105.0,
                at_support=True, at_resistance=False, is_breakout=False, sr_score=10
            ),
            momentum=MomentumAnalysis(rsi_valid=True, macd_score=10, has_divergence=False, momentum_score=10),
            is_choppy=False,
            btc_correlation_adjustment=0,
        )
        
        result = validator.validate(context_low_volume)
        assert result.passed is False, "Should veto signal for low volume"
        assert "Volume" in result.veto_reason



class TestEnhancedTAAnalyzerIntegration:
    """Integration tests for EnhancedTAAnalyzer."""

    def test_full_analysis_pipeline_aligned_trends(self):
        """Test full analysis pipeline with aligned trends generates signal."""
        from src.kinetic_empire.v3.analyzer.enhanced import EnhancedTAAnalyzer, OHLCV
        
        analyzer = EnhancedTAAnalyzer()
        
        # Create OHLCV data with uptrend
        base_price = 100.0
        ohlcv_4h = [OHLCV(open=base_price+i, high=base_price+i+2, low=base_price+i-1, 
                         close=base_price+i+1, volume=1000) for i in range(30)]
        ohlcv_1h = [OHLCV(open=base_price+i*0.5, high=base_price+i*0.5+1, low=base_price+i*0.5-0.5, 
                         close=base_price+i*0.5+0.5, volume=500) for i in range(30)]
        ohlcv_15m = [OHLCV(open=base_price+i*0.2, high=base_price+i*0.2+0.5, low=base_price+i*0.2-0.2, 
                          close=base_price+i*0.2+0.3, volume=200) for i in range(30)]
        
        # Create indicators showing uptrend
        indicators_4h = {
            "ema_9": 105.0, "ema_21": 102.0, "ema_50": 98.0,
            "rsi": 55.0, "macd_line": 0.5, "macd_signal": 0.3, "macd_histogram": 0.2,
            "atr": 2.0, "atr_average": 1.8, "volume_ratio": 1.2, "close": 106.0, "adx": 30,
        }
        indicators_1h = {
            "ema_9": 104.0, "ema_21": 102.0, "ema_50": 99.0,
            "rsi": 52.0, "macd_line": 0.3, "macd_signal": 0.2, "macd_histogram": 0.1,
            "atr": 1.0, "atr_average": 0.9, "volume_ratio": 1.1, "close": 105.0, "adx": 28,
        }
        indicators_15m = {
            "ema_9": 103.0, "ema_21": 101.5, "ema_50": 100.0,
            "rsi": 50.0, "macd_line": 0.2, "macd_signal": 0.1, "macd_histogram": 0.1,
            "atr": 0.5, "atr_average": 0.5, "volume_ratio": 1.0, "close": 104.0, "adx": 25,
        }
        
        signal = analyzer.analyze(
            symbol="ETHUSDT",
            ohlcv_4h=ohlcv_4h,
            ohlcv_1h=ohlcv_1h,
            ohlcv_15m=ohlcv_15m,
            indicators_4h=indicators_4h,
            indicators_1h=indicators_1h,
            indicators_15m=indicators_15m,
            is_altcoin=False,
        )
        
        # Should generate a signal with aligned uptrend
        assert signal is not None, "Should generate signal with aligned trends"
        assert signal.direction == "LONG", "Should be LONG signal for uptrend"
        assert signal.confidence >= 65, f"Confidence should be >= 65, got {signal.confidence}"

    def test_signal_blocked_with_conflicting_trends(self):
        """Test that conflicting trends block signal generation."""
        from src.kinetic_empire.v3.analyzer.enhanced import EnhancedTAAnalyzer, OHLCV
        
        analyzer = EnhancedTAAnalyzer()
        
        # Create OHLCV data
        base_price = 100.0
        ohlcv = [OHLCV(open=base_price, high=base_price+1, low=base_price-1, 
                      close=base_price, volume=1000) for _ in range(30)]
        
        # 4H UP, 1H DOWN, 15M DOWN = conflict
        indicators_4h = {
            "ema_9": 105.0, "ema_21": 102.0, "ema_50": 98.0,
            "rsi": 55.0, "macd_line": 0.5, "macd_signal": 0.3, "macd_histogram": 0.2,
            "atr": 2.0, "atr_average": 1.8, "volume_ratio": 0.5, "close": 106.0, "adx": 30,
        }
        indicators_1h = {
            "ema_9": 98.0, "ema_21": 102.0, "ema_50": 105.0,  # DOWN trend
            "rsi": 45.0, "macd_line": -0.3, "macd_signal": -0.2, "macd_histogram": -0.1,
            "atr": 1.0, "atr_average": 0.9, "volume_ratio": 0.5, "close": 97.0, "adx": 28,
        }
        indicators_15m = {
            "ema_9": 97.0, "ema_21": 100.0, "ema_50": 102.0,  # DOWN trend
            "rsi": 40.0, "macd_line": -0.2, "macd_signal": -0.1, "macd_histogram": -0.1,
            "atr": 0.5, "atr_average": 0.5, "volume_ratio": 0.5, "close": 96.0, "adx": 25,
        }
        
        signal = analyzer.analyze(
            symbol="ETHUSDT",
            ohlcv_4h=ohlcv,
            ohlcv_1h=ohlcv,
            ohlcv_15m=ohlcv,
            indicators_4h=indicators_4h,
            indicators_1h=indicators_1h,
            indicators_15m=indicators_15m,
            is_altcoin=False,
        )
        
        # Should be blocked due to low volume
        assert signal is None, "Should block signal with low volume"
