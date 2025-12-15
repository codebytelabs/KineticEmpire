"""Property-based tests for optimized trading parameters.

Tests all 23 correctness properties defined in the design document.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings

from src.kinetic_empire.optimized.models import MarketRegime
from src.kinetic_empire.optimized.config import OptimizedConfig, DEFAULT_CONFIG
from src.kinetic_empire.optimized.atr_stop import OptimizedATRStopCalculator
from src.kinetic_empire.optimized.leverage import OptimizedLeverageCalculator
from src.kinetic_empire.optimized.position_sizer import OptimizedPositionSizer
from src.kinetic_empire.optimized.trailing_stop import OptimizedTrailingStop
from src.kinetic_empire.optimized.rsi_filter import OptimizedRSIFilter
from src.kinetic_empire.optimized.adx_filter import OptimizedADXFilter
from src.kinetic_empire.optimized.volume_confirmer import OptimizedVolumeConfirmer
from src.kinetic_empire.optimized.portfolio_risk import OptimizedPortfolioRiskGuard
from src.kinetic_empire.optimized.parameter_adjuster import ParameterAdjuster


# Strategies for generating test data
regime_strategy = st.sampled_from(list(MarketRegime))
confidence_strategy = st.floats(min_value=0, max_value=100)
price_strategy = st.floats(min_value=0.01, max_value=100000)
atr_strategy = st.floats(min_value=0.001, max_value=1000)
position_strategy = st.floats(min_value=0.01, max_value=1000000)
rsi_strategy = st.floats(min_value=0, max_value=100)
adx_strategy = st.floats(min_value=0, max_value=100)
volume_strategy = st.floats(min_value=0.01, max_value=1000000000)
win_rate_strategy = st.floats(min_value=0, max_value=1)
direction_strategy = st.sampled_from(['long', 'short'])


class TestATRStopCalculator:
    """Tests for OptimizedATRStopCalculator - Properties 1-2."""
    
    @given(regime=regime_strategy, atr=atr_strategy)
    @settings(max_examples=100)
    def test_property_1_atr_multiplier_regime_adaptation(self, regime, atr):
        """Property 1: ATR multiplier adapts correctly to regime.
        
        **Feature: parameter-optimization-v4, Property 1: ATR Stop Multiplier Regime Adaptation**
        **Validates: Requirements 1.1, 1.2, 1.3, 9.2, 9.4**
        """
        calculator = OptimizedATRStopCalculator()
        multiplier = calculator.get_multiplier(regime)
        
        if regime == MarketRegime.HIGH_VOLATILITY:
            assert multiplier == 3.0
        elif regime in (MarketRegime.LOW_VOLATILITY, MarketRegime.SIDEWAYS):
            assert multiplier == 2.0
        else:  # TRENDING or CHOPPY
            assert multiplier == 2.5
    
    @given(
        entry_price=price_strategy,
        atr=atr_strategy,
        regime=regime_strategy,
        position_size=position_strategy,
        direction=direction_strategy
    )
    @settings(max_examples=100)
    def test_property_2_maximum_loss_invariant(
        self, entry_price, atr, regime, position_size, direction
    ):
        """Property 2: Maximum loss never exceeds 2% of position value.
        
        **Feature: parameter-optimization-v4, Property 2: Maximum Loss Invariant**
        **Validates: Requirements 1.4, 1.5**
        """
        assume(entry_price > 0 and atr > 0 and position_size > 0)
        
        calculator = OptimizedATRStopCalculator()
        result = calculator.calculate_stop(
            entry_price=entry_price,
            atr=atr,
            direction=direction,
            regime=regime,
            position_size=position_size
        )
        
        # If max loss exceeded, position size must be adjusted
        if result.max_loss_exceeded:
            assert result.adjusted_position_size is not None
            assert result.adjusted_position_size < position_size
            # Verify adjusted size meets max loss requirement
            adjusted_loss = result.distance_percent * (result.adjusted_position_size / position_size)
            assert adjusted_loss <= DEFAULT_CONFIG.MAX_LOSS_PERCENT + 0.001  # Small tolerance


class TestLeverageCalculator:
    """Tests for OptimizedLeverageCalculator - Properties 3-5."""
    
    @given(confidence=confidence_strategy, regime=regime_strategy)
    @settings(max_examples=100)
    def test_property_3_leverage_hard_cap_invariant(self, confidence, regime):
        """Property 3: Leverage never exceeds 8x hard cap.
        
        **Feature: parameter-optimization-v4, Property 3: Leverage Hard Cap Invariant**
        **Validates: Requirements 2.1**
        """
        calculator = OptimizedLeverageCalculator()
        leverage = calculator.calculate_leverage(confidence, regime)
        
        assert leverage <= DEFAULT_CONFIG.LEVERAGE_HARD_CAP
        assert leverage >= 1
    
    @given(confidence=confidence_strategy)
    @settings(max_examples=100)
    def test_property_4_leverage_confidence_tiers(self, confidence):
        """Property 4: Leverage follows confidence tiers.
        
        **Feature: parameter-optimization-v4, Property 4: Leverage Confidence Tiers**
        **Validates: Requirements 2.2, 2.3, 2.4, 2.5**
        """
        calculator = OptimizedLeverageCalculator()
        # Use TRENDING regime to avoid regime reduction
        leverage = calculator.calculate_leverage(confidence, MarketRegime.TRENDING)
        
        if confidence < 70:
            assert leverage <= 3
        elif confidence < 80:
            assert leverage <= 5
        elif confidence < 90:
            assert leverage <= 6
        else:
            assert leverage <= 8
    
    @given(confidence=confidence_strategy)
    @settings(max_examples=100)
    def test_property_5_leverage_regime_reduction(self, confidence):
        """Property 5: Leverage reduced by 50% for choppy/volatile regimes.
        
        **Feature: parameter-optimization-v4, Property 5: Leverage Regime Reduction**
        **Validates: Requirements 2.6, 9.3**
        """
        calculator = OptimizedLeverageCalculator()
        
        normal_leverage = calculator.calculate_leverage(confidence, MarketRegime.TRENDING)
        choppy_leverage = calculator.calculate_leverage(confidence, MarketRegime.CHOPPY)
        volatile_leverage = calculator.calculate_leverage(confidence, MarketRegime.HIGH_VOLATILITY)
        
        # Choppy and volatile should be reduced
        assert choppy_leverage <= normal_leverage
        assert volatile_leverage <= normal_leverage
        
        # Should be approximately 50% (accounting for integer rounding)
        if normal_leverage > 1:
            assert choppy_leverage <= (normal_leverage // 2) + 1


class TestPositionSizer:
    """Tests for OptimizedPositionSizer - Properties 6-8."""
    
    @given(win_rate=win_rate_strategy)
    @settings(max_examples=100)
    def test_property_6_kelly_fraction_consistency(self, win_rate):
        """Property 6: Kelly fraction is 0.25 for win_rate >= 40%, 0.15 otherwise.
        
        **Feature: parameter-optimization-v4, Property 6: Kelly Fraction Consistency**
        **Validates: Requirements 3.1, 3.5**
        """
        sizer = OptimizedPositionSizer()
        fraction = sizer.get_kelly_fraction(win_rate)
        
        if win_rate < 0.40:
            assert fraction == 0.15
        else:
            assert fraction == 0.25
    
    @given(
        win_rate=st.floats(min_value=0, max_value=0.3),
        avg_win=st.floats(min_value=0.01, max_value=100),
        avg_loss=st.floats(min_value=0.01, max_value=100)
    )
    @settings(max_examples=100)
    def test_property_7_kelly_non_negative_output(self, win_rate, avg_win, avg_loss):
        """Property 7: Position size is never negative.
        
        **Feature: parameter-optimization-v4, Property 7: Kelly Non-Negative Output**
        **Validates: Requirements 3.3**
        """
        sizer = OptimizedPositionSizer()
        position_size = sizer.calculate_position_size(
            capital=10000,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss
        )
        
        assert position_size >= 0
    
    @given(
        capital=st.floats(min_value=100, max_value=1000000),
        win_rate=st.floats(min_value=0.5, max_value=0.9),
        avg_win=st.floats(min_value=10, max_value=1000),
        avg_loss=st.floats(min_value=1, max_value=100)
    )
    @settings(max_examples=100)
    def test_property_8_position_size_cap_invariant(
        self, capital, win_rate, avg_win, avg_loss
    ):
        """Property 8: Position size never exceeds 25% of capital.
        
        **Feature: parameter-optimization-v4, Property 8: Position Size Cap Invariant**
        **Validates: Requirements 3.4**
        """
        sizer = OptimizedPositionSizer()
        position_size = sizer.calculate_position_size(
            capital=capital,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss
        )
        
        max_allowed = capital * DEFAULT_CONFIG.MAX_POSITION_PERCENT
        assert position_size <= max_allowed + 0.01  # Small tolerance for float


class TestTrailingStop:
    """Tests for OptimizedTrailingStop - Properties 9-10."""
    
    @given(
        profit_pct=st.floats(min_value=0, max_value=0.5),
        regime=regime_strategy
    )
    @settings(max_examples=100)
    def test_property_9_trailing_stop_activation_threshold(self, profit_pct, regime):
        """Property 9: Trailing stop activates at correct threshold per regime.
        
        **Feature: parameter-optimization-v4, Property 9: Trailing Stop Activation Threshold**
        **Validates: Requirements 4.1, 4.4, 4.5, 9.1**
        """
        trailing = OptimizedTrailingStop()
        threshold = trailing.get_activation_threshold(regime)
        should_activate = trailing.should_activate(profit_pct, regime)
        
        if regime == MarketRegime.TRENDING:
            assert threshold == 0.025
        elif regime == MarketRegime.SIDEWAYS:
            assert threshold == 0.015
        else:
            assert threshold == 0.02
        
        # Verify activation logic
        assert should_activate == (profit_pct >= threshold)
    
    @given(
        current_price=price_strategy,
        current_stop=price_strategy,
        direction=direction_strategy
    )
    @settings(max_examples=100)
    def test_property_10_trailing_stop_monotonicity(
        self, current_price, current_stop, direction
    ):
        """Property 10: Trailing stop only moves in favorable direction.
        
        **Feature: parameter-optimization-v4, Property 10: Trailing Stop Monotonicity**
        **Validates: Requirements 4.2, 4.3**
        """
        assume(current_price > 0 and current_stop > 0)
        
        trailing = OptimizedTrailingStop()
        new_stop = trailing.update_stop(
            current_price=current_price,
            current_stop=current_stop,
            direction=direction
        )
        
        if direction == 'long':
            # For longs, stop can only move up
            assert new_stop >= current_stop
        else:
            # For shorts, stop can only move down
            assert new_stop <= current_stop



class TestRSIFilter:
    """Tests for OptimizedRSIFilter - Properties 11-13."""
    
    @given(rsi=rsi_strategy, direction=direction_strategy)
    @settings(max_examples=100)
    def test_property_11_rsi_entry_thresholds(self, rsi, direction):
        """Property 11: RSI thresholds are 25 for longs, 75 for shorts.
        
        **Feature: parameter-optimization-v4, Property 11: RSI Entry Thresholds**
        **Validates: Requirements 5.1, 5.2**
        """
        rsi_filter = OptimizedRSIFilter()
        result = rsi_filter.evaluate_entry(rsi, direction)
        
        if direction == 'long':
            if rsi < 25:
                assert result.signal_valid is True
            elif rsi >= 75:
                assert result.signal_valid is False
        else:  # short
            if rsi > 75:
                assert result.signal_valid is True
            elif rsi <= 25:
                assert result.signal_valid is False
    
    @given(rsi=st.floats(min_value=25, max_value=75), direction=direction_strategy)
    @settings(max_examples=100)
    def test_property_12_rsi_confirmation_requirement(self, rsi, direction):
        """Property 12: RSI between 25-75 requires confirmation.
        
        **Feature: parameter-optimization-v4, Property 12: RSI Confirmation Requirement**
        **Validates: Requirements 5.3**
        """
        rsi_filter = OptimizedRSIFilter()
        result = rsi_filter.evaluate_entry(rsi, direction)
        
        # Mid-range RSI should require confirmation (unless it's invalid for other reasons)
        if not result.signal_valid:
            assert result.requires_confirmation is True or "invalid" in result.reason.lower()
    
    @given(rsi=rsi_strategy, direction=direction_strategy)
    @settings(max_examples=100)
    def test_property_13_rsi_divergence_bonus(self, rsi, direction):
        """Property 13: RSI divergence adds exactly 10 points to confidence.
        
        **Feature: parameter-optimization-v4, Property 13: RSI Divergence Bonus**
        **Validates: Requirements 5.5**
        """
        rsi_filter = OptimizedRSIFilter()
        
        result_no_div = rsi_filter.evaluate_entry(rsi, direction, has_divergence=False)
        result_with_div = rsi_filter.evaluate_entry(rsi, direction, has_divergence=True)
        
        # Divergence should add exactly 10 points
        assert result_with_div.confidence_bonus == result_no_div.confidence_bonus + 10


class TestADXFilter:
    """Tests for OptimizedADXFilter - Properties 14-15."""
    
    @given(adx=adx_strategy)
    @settings(max_examples=100)
    def test_property_14_adx_trend_classification(self, adx):
        """Property 14: ADX classifies market correctly.
        
        **Feature: parameter-optimization-v4, Property 14: ADX Trend Classification**
        **Validates: Requirements 6.1, 6.2**
        """
        adx_filter = OptimizedADXFilter()
        result = adx_filter.evaluate_trend(adx)
        
        if adx < 15:
            assert result.regime == MarketRegime.SIDEWAYS
            assert result.is_trending is False
        elif adx >= 20:
            assert result.is_trending is True
    
    @given(adx=adx_strategy)
    @settings(max_examples=100)
    def test_property_15_adx_position_adjustment(self, adx):
        """Property 15: ADX adjusts position size and confidence correctly.
        
        **Feature: parameter-optimization-v4, Property 15: ADX Position Adjustment**
        **Validates: Requirements 6.3, 6.4**
        """
        adx_filter = OptimizedADXFilter()
        result = adx_filter.evaluate_trend(adx)
        
        if 15 <= adx < 20:
            # Weak trend - 30% reduction
            assert result.position_size_multiplier == 0.70
        elif adx > 30:
            # Strong trend - 5 point bonus
            assert result.confidence_bonus == 5
        else:
            assert result.position_size_multiplier == 1.0


class TestVolumeConfirmer:
    """Tests for OptimizedVolumeConfirmer - Properties 16-17."""
    
    @given(
        current_volume=volume_strategy,
        average_volume=volume_strategy
    )
    @settings(max_examples=100)
    def test_property_16_volume_confirmation_threshold(
        self, current_volume, average_volume
    ):
        """Property 16: Volume confirmation requires 1.5x average.
        
        **Feature: parameter-optimization-v4, Property 16: Volume Confirmation Threshold**
        **Validates: Requirements 7.1**
        """
        assume(average_volume > 0)
        
        confirmer = OptimizedVolumeConfirmer()
        result = confirmer.confirm_volume(current_volume, average_volume)
        
        ratio = current_volume / average_volume
        if ratio >= 1.5:
            assert result.confirmed is True
        else:
            assert result.confirmed is False
    
    @given(
        current_volume=volume_strategy,
        average_volume=volume_strategy
    )
    @settings(max_examples=100)
    def test_property_17_volume_position_adjustment(
        self, current_volume, average_volume
    ):
        """Property 17: Volume adjusts position size and confidence.
        
        **Feature: parameter-optimization-v4, Property 17: Volume Position Adjustment**
        **Validates: Requirements 7.2, 7.3**
        """
        assume(average_volume > 0)
        
        confirmer = OptimizedVolumeConfirmer()
        result = confirmer.confirm_volume(current_volume, average_volume)
        
        ratio = current_volume / average_volume
        
        if ratio < 1.5:
            # Low volume - 40% reduction
            assert result.position_size_multiplier == 0.60
        elif ratio >= 2.5:
            # Volume spike - 10 point bonus
            assert result.confidence_bonus == 10
            assert result.is_spike is True


class TestPortfolioRiskGuard:
    """Tests for OptimizedPortfolioRiskGuard - Properties 18-22."""
    
    @given(current_positions=st.integers(min_value=0, max_value=20))
    @settings(max_examples=100)
    def test_property_18_portfolio_position_limit(self, current_positions):
        """Property 18: New entries rejected when positions >= 8.
        
        **Feature: parameter-optimization-v4, Property 18: Portfolio Position Limit**
        **Validates: Requirements 8.1**
        """
        guard = OptimizedPortfolioRiskGuard()
        result = guard.can_open_position(
            current_positions=current_positions,
            margin_usage=0.5,
            daily_loss=0.01
        )
        
        if current_positions >= 8:
            assert result.can_open is False
            assert "position limit" in result.reason.lower()
        else:
            # May still be rejected for other reasons, but not position limit
            if not result.can_open and result.reason:
                assert "position limit" not in result.reason.lower()
    
    @given(margin_usage=st.floats(min_value=0, max_value=1))
    @settings(max_examples=100)
    def test_property_19_portfolio_margin_limit(self, margin_usage):
        """Property 19: New entries rejected when margin > 80%.
        
        **Feature: parameter-optimization-v4, Property 19: Portfolio Margin Limit**
        **Validates: Requirements 8.2**
        """
        guard = OptimizedPortfolioRiskGuard()
        result = guard.can_open_position(
            current_positions=1,
            margin_usage=margin_usage,
            daily_loss=0.01
        )
        
        if margin_usage >= 0.80:
            assert result.can_open is False
            assert "margin" in result.reason.lower()
    
    @given(daily_loss=st.floats(min_value=0, max_value=0.2))
    @settings(max_examples=100)
    def test_property_20_daily_loss_circuit_breaker(self, daily_loss):
        """Property 20: Trading paused when daily loss >= 4%.
        
        **Feature: parameter-optimization-v4, Property 20: Daily Loss Circuit Breaker**
        **Validates: Requirements 8.3**
        """
        guard = OptimizedPortfolioRiskGuard()
        guard.clear_pause()  # Reset state
        
        result = guard.can_open_position(
            current_positions=1,
            margin_usage=0.5,
            daily_loss=daily_loss
        )
        
        if daily_loss >= 0.04:
            assert result.can_open is False
            assert result.is_paused is True
    
    def test_property_21_correlation_position_limit(self):
        """Property 21: Max 2 positions with correlation > 0.7.
        
        **Feature: parameter-optimization-v4, Property 21: Correlation Position Limit**
        **Validates: Requirements 8.4**
        """
        guard = OptimizedPortfolioRiskGuard()
        
        # Create correlation matrix with high correlations
        correlation_matrix = {
            "BTCUSDT": {"ETHUSDT": 0.85, "SOLUSDT": 0.75},
            "ETHUSDT": {"BTCUSDT": 0.85, "SOLUSDT": 0.80},
            "SOLUSDT": {"BTCUSDT": 0.75, "ETHUSDT": 0.80}
        }
        
        # Should reject when too many correlated positions
        result = guard.can_open_position(
            current_positions=2,
            margin_usage=0.5,
            daily_loss=0.01,
            correlation_matrix=correlation_matrix,
            new_symbol="BTCUSDT"
        )
        
        # BTCUSDT has 2 highly correlated positions, should be rejected
        assert result.can_open is False
        assert "correlated" in result.reason.lower()
    
    @given(weekly_loss=st.floats(min_value=0, max_value=0.2))
    @settings(max_examples=100)
    def test_property_22_weekly_loss_position_reduction(self, weekly_loss):
        """Property 22: Position sizes reduced 50% when weekly loss >= 8%.
        
        **Feature: parameter-optimization-v4, Property 22: Weekly Loss Position Reduction**
        **Validates: Requirements 8.6**
        """
        guard = OptimizedPortfolioRiskGuard()
        guard.clear_pause()
        
        result = guard.can_open_position(
            current_positions=1,
            margin_usage=0.5,
            daily_loss=0.01,
            weekly_loss=weekly_loss
        )
        
        if weekly_loss >= 0.08:
            assert result.position_size_multiplier == 0.50


class TestParameterAdjuster:
    """Tests for ParameterAdjuster - Property 23."""
    
    @given(
        regime=regime_strategy,
        regime_confidence=st.floats(min_value=0, max_value=1)
    )
    @settings(max_examples=100)
    def test_property_23_regime_conservative_defaults(self, regime, regime_confidence):
        """Property 23: Conservative defaults used when confidence < 60%.
        
        **Feature: parameter-optimization-v4, Property 23: Regime Conservative Defaults**
        **Validates: Requirements 9.6**
        """
        adjuster = ParameterAdjuster()
        params = adjuster.get_adjusted_parameters(regime, regime_confidence)
        
        if regime_confidence < 0.60:
            # Should use conservative defaults
            assert params.max_leverage == DEFAULT_CONFIG.LEVERAGE_TIER_LOW
            assert params.kelly_fraction == DEFAULT_CONFIG.KELLY_LOW_WINRATE_FRACTION
            assert params.max_positions == DEFAULT_CONFIG.MAX_POSITIONS // 2
