"""Tests for Profitable Trading Overhaul components.

Property-based tests using Hypothesis to validate correctness properties.
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime

from src.kinetic_empire.profitable_trading import (
    MarketRegime,
    TrendDirection,
    RegimeDetector,
    DirectionValidator,
    ConfidencePositionSizer,
    RegimeLeverageCalculator,
    ATRStopCalculator,
    ATRTrailingStopManager,
    ExposureTracker,
    EntryConfirmer,
)
from src.kinetic_empire.profitable_trading.direction_validator import OHLCV


# =============================================================================
# Property 9: ADX-based regime detection
# **Validates: Requirements 9.1, 9.2, 9.3, 9.4**
# =============================================================================

class TestRegimeDetector:
    """Tests for RegimeDetector - Property 9."""
    
    @given(
        adx=st.floats(min_value=25.01, max_value=100.0),
        price=st.floats(min_value=1.0, max_value=100000.0),
        ma_50=st.floats(min_value=1.0, max_value=100000.0),
    )
    @settings(max_examples=100)
    def test_adx_above_25_is_trending(self, adx, price, ma_50):
        """**Feature: profitable-trading-overhaul, Property 9: ADX-based regime detection**
        
        *For any* ADX > 25, regime SHALL be TRENDING.
        **Validates: Requirements 9.1, 9.2**
        """
        detector = RegimeDetector()
        result = detector.detect(adx, price, ma_50)
        assert result.regime == MarketRegime.TRENDING
    
    @given(
        adx=st.floats(min_value=15.0, max_value=25.0),
        price=st.floats(min_value=1.0, max_value=100000.0),
        ma_50=st.floats(min_value=1.0, max_value=100000.0),
    )
    @settings(max_examples=100)
    def test_adx_15_to_25_is_sideways(self, adx, price, ma_50):
        """**Feature: profitable-trading-overhaul, Property 9: ADX-based regime detection**
        
        *For any* 15 <= ADX <= 25, regime SHALL be SIDEWAYS.
        **Validates: Requirements 9.3**
        """
        detector = RegimeDetector()
        result = detector.detect(adx, price, ma_50)
        assert result.regime == MarketRegime.SIDEWAYS
    
    @given(
        adx=st.floats(min_value=0.0, max_value=14.99),
        price=st.floats(min_value=1.0, max_value=100000.0),
        ma_50=st.floats(min_value=1.0, max_value=100000.0),
    )
    @settings(max_examples=100)
    def test_adx_below_15_is_choppy(self, adx, price, ma_50):
        """**Feature: profitable-trading-overhaul, Property 9: ADX-based regime detection**
        
        *For any* ADX < 15, regime SHALL be CHOPPY.
        **Validates: Requirements 9.4**
        """
        detector = RegimeDetector()
        result = detector.detect(adx, price, ma_50)
        assert result.regime == MarketRegime.CHOPPY


# =============================================================================
# Property 2: Confidence-to-position-size mapping
# **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6**
# =============================================================================

class TestConfidencePositionSizer:
    """Tests for ConfidencePositionSizer - Property 2.
    
    Updated for aggressive-capital-deployment spec:
    - 90-100 → 20%
    - 80-89 → 18%
    - 70-79 → 15%
    - 60-69 → 12%
    - Below 60 → rejected (regime-aware: 60 trending, 65 sideways)
    """
    
    @given(confidence=st.integers(min_value=90, max_value=100))
    @settings(max_examples=100)
    def test_confidence_90_100_gives_20_percent(self, confidence):
        """**Feature: aggressive-capital-deployment, Property 2: Confidence-to-position-size mapping**
        
        *For any* confidence 90-100, position size SHALL be 20%.
        **Validates: Requirements 2.1**
        """
        sizer = ConfidencePositionSizer()
        result = sizer.calculate(confidence, 10000.0, market_regime="TRENDING")
        assert result.size_pct == 0.20
        assert result.confidence_tier == "excellent"
    
    @given(confidence=st.integers(min_value=80, max_value=89))
    @settings(max_examples=100)
    def test_confidence_80_89_gives_18_percent(self, confidence):
        """**Feature: aggressive-capital-deployment, Property 2: Confidence-to-position-size mapping**
        
        *For any* confidence 80-89, position size SHALL be 18%.
        **Validates: Requirements 2.2**
        """
        sizer = ConfidencePositionSizer()
        result = sizer.calculate(confidence, 10000.0, market_regime="TRENDING")
        assert result.size_pct == 0.18

    @given(confidence=st.integers(min_value=70, max_value=79))
    @settings(max_examples=100)
    def test_confidence_70_79_gives_15_percent(self, confidence):
        """**Feature: aggressive-capital-deployment, Property 2**
        **Validates: Requirements 2.3**
        """
        sizer = ConfidencePositionSizer()
        result = sizer.calculate(confidence, 10000.0, market_regime="TRENDING")
        assert result.size_pct == 0.15
    
    @given(confidence=st.integers(min_value=60, max_value=69))
    @settings(max_examples=100)
    def test_confidence_60_69_gives_12_percent(self, confidence):
        """**Feature: aggressive-capital-deployment, Property 2**
        **Validates: Requirements 2.4**
        """
        sizer = ConfidencePositionSizer()
        result = sizer.calculate(confidence, 10000.0, market_regime="TRENDING")
        assert result.size_pct == 0.12
    
    @given(confidence=st.integers(min_value=0, max_value=59))
    @settings(max_examples=100)
    def test_confidence_below_60_rejected_trending(self, confidence):
        """**Feature: aggressive-capital-deployment, Property 3: Regime-aware rejection**
        
        *For any* confidence below 60 in TRENDING regime, signal SHALL be rejected.
        **Validates: Requirements 4.1**
        """
        sizer = ConfidencePositionSizer()
        result = sizer.calculate(confidence, 10000.0, market_regime="TRENDING")
        assert result.is_rejected
        assert result.size_pct == 0.0
    
    @given(confidence=st.integers(min_value=60, max_value=64))
    @settings(max_examples=100)
    def test_confidence_60_64_rejected_sideways(self, confidence):
        """**Feature: aggressive-capital-deployment, Property 3: Regime-aware rejection**
        
        *For any* confidence 60-64 in SIDEWAYS regime, signal SHALL be rejected (needs 65+).
        **Validates: Requirements 4.2**
        """
        sizer = ConfidencePositionSizer()
        result = sizer.calculate(confidence, 10000.0, market_regime="SIDEWAYS")
        assert result.is_rejected
        assert result.size_pct == 0.0


# =============================================================================
# Property 3: Portfolio exposure cap invariant
# **Validates: Requirements 2.7, 8.1, 8.2, 8.3**
# =============================================================================

class TestExposureTracker:
    """Tests for ExposureTracker - Property 3."""
    
    @given(
        positions=st.lists(
            st.tuples(
                st.text(min_size=1, max_size=10, alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
                st.floats(min_value=0.01, max_value=0.15),
            ),
            min_size=0,
            max_size=10,
        )
    )
    @settings(max_examples=100)
    def test_exposure_never_exceeds_45_percent(self, positions):
        """**Feature: profitable-trading-overhaul, Property 3: Portfolio exposure cap invariant**
        
        *For any* set of positions, total exposure SHALL never exceed 45%.
        **Validates: Requirements 2.7, 8.1, 8.2, 8.3**
        """
        tracker = ExposureTracker(max_exposure_pct=0.45)
        
        for symbol, size in positions:
            tracker.add_position(symbol, size)
        
        # Invariant: exposure never exceeds max
        assert tracker.get_current_exposure() <= 0.45


# =============================================================================
# Property 4: Regime-confidence-to-leverage mapping
# **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**
# =============================================================================

class TestRegimeLeverageCalculator:
    """Tests for RegimeLeverageCalculator - Property 4."""
    
    @given(confidence=st.integers(min_value=90, max_value=100))
    @settings(max_examples=100)
    def test_trending_high_confidence_gives_10x(self, confidence):
        """**Feature: profitable-trading-overhaul, Property 4**
        **Validates: Requirements 3.1**
        """
        calc = RegimeLeverageCalculator()
        leverage = calc.calculate(MarketRegime.TRENDING, confidence)
        assert leverage == 10
    
    @given(confidence=st.integers(min_value=70, max_value=89))
    @settings(max_examples=100)
    def test_trending_medium_confidence_gives_7x(self, confidence):
        """**Feature: profitable-trading-overhaul, Property 4**
        **Validates: Requirements 3.2**
        """
        calc = RegimeLeverageCalculator()
        leverage = calc.calculate(MarketRegime.TRENDING, confidence)
        assert leverage == 7
    
    @given(confidence=st.integers(min_value=50, max_value=69))
    @settings(max_examples=100)
    def test_trending_low_confidence_gives_5x(self, confidence):
        """**Feature: profitable-trading-overhaul, Property 4**
        **Validates: Requirements 3.3**
        """
        calc = RegimeLeverageCalculator()
        leverage = calc.calculate(MarketRegime.TRENDING, confidence)
        assert leverage == 5
    
    @given(confidence=st.integers(min_value=50, max_value=100))
    @settings(max_examples=100)
    def test_sideways_gives_3x_max(self, confidence):
        """**Feature: profitable-trading-overhaul, Property 4**
        **Validates: Requirements 3.4**
        """
        calc = RegimeLeverageCalculator()
        leverage = calc.calculate(MarketRegime.SIDEWAYS, confidence)
        assert leverage == 3
    
    @given(confidence=st.integers(min_value=50, max_value=100))
    @settings(max_examples=100)
    def test_choppy_gives_2x_max(self, confidence):
        """**Feature: profitable-trading-overhaul, Property 4**
        **Validates: Requirements 3.5**
        """
        calc = RegimeLeverageCalculator()
        leverage = calc.calculate(MarketRegime.CHOPPY, confidence)
        assert leverage == 2
    
    @given(
        confidence=st.integers(min_value=90, max_value=100),
        losses=st.integers(min_value=2, max_value=10),
    )
    @settings(max_examples=100)
    def test_consecutive_losses_reduce_leverage_50_percent(self, confidence, losses):
        """**Feature: profitable-trading-overhaul, Property 4**
        **Validates: Requirements 3.6**
        """
        calc = RegimeLeverageCalculator()
        leverage = calc.calculate(MarketRegime.TRENDING, confidence, consecutive_losses=losses)
        # 10x reduced by 50% = 5x
        assert leverage == 5


# =============================================================================
# Property 5: ATR stop loss calculation with bounds
# **Validates: Requirements 4.2, 4.3, 4.4, 4.5, 4.6**
# =============================================================================

class TestATRStopCalculator:
    """Tests for ATRStopCalculator - Property 5."""
    
    @given(
        entry_price=st.floats(min_value=100.0, max_value=100000.0),
        atr=st.floats(min_value=0.1, max_value=1000.0),
    )
    @settings(max_examples=100)
    def test_stop_bounded_between_1_and_5_percent(self, entry_price, atr):
        """**Feature: profitable-trading-overhaul, Property 5: ATR stop loss with bounds**
        
        *For any* entry price and ATR, stop SHALL be bounded between 1% and 5%.
        **Validates: Requirements 4.5, 4.6**
        """
        calc = ATRStopCalculator()
        result = calc.calculate(entry_price, "LONG", atr, MarketRegime.TRENDING)
        
        assert 0.01 <= result.stop_pct <= 0.05
    
    @given(
        entry_price=st.floats(min_value=100.0, max_value=100000.0),
        atr=st.floats(min_value=0.1, max_value=100.0),
    )
    @settings(max_examples=100)
    def test_trending_uses_2x_multiplier(self, entry_price, atr):
        """**Feature: profitable-trading-overhaul, Property 5**
        **Validates: Requirements 4.2**
        """
        calc = ATRStopCalculator()
        result = calc.calculate(entry_price, "LONG", atr, MarketRegime.TRENDING)
        assert result.atr_multiplier == 2.0
    
    @given(
        entry_price=st.floats(min_value=100.0, max_value=100000.0),
        atr=st.floats(min_value=0.1, max_value=100.0),
    )
    @settings(max_examples=100)
    def test_sideways_uses_2_5x_multiplier(self, entry_price, atr):
        """**Feature: profitable-trading-overhaul, Property 5**
        **Validates: Requirements 4.3**
        """
        calc = ATRStopCalculator()
        result = calc.calculate(entry_price, "LONG", atr, MarketRegime.SIDEWAYS)
        assert result.atr_multiplier == 2.5
    
    @given(
        entry_price=st.floats(min_value=100.0, max_value=100000.0),
        atr=st.floats(min_value=0.1, max_value=100.0),
    )
    @settings(max_examples=100)
    def test_choppy_uses_3x_multiplier(self, entry_price, atr):
        """**Feature: profitable-trading-overhaul, Property 5**
        **Validates: Requirements 4.4**
        """
        calc = ATRStopCalculator()
        result = calc.calculate(entry_price, "LONG", atr, MarketRegime.CHOPPY)
        assert result.atr_multiplier == 3.0


# =============================================================================
# Property 6: Direction validation against price momentum
# **Validates: Requirements 5.1, 5.2, 5.3**
# =============================================================================

class TestDirectionValidator:
    """Tests for DirectionValidator - Property 6."""
    
    def test_long_rejected_if_price_fell_more_than_threshold(self):
        """**Feature: profitable-trading-overhaul, Property 6**
        **Validates: Requirements 5.1**
        """
        validator = DirectionValidator()
        # Price fell 0.5% (> 0.3% threshold)
        candles = [
            OHLCV(100, 101, 99, 100, 1000),
            OHLCV(100, 101, 99, 99.8, 1000),
            OHLCV(99.8, 100, 99, 99.6, 1000),
            OHLCV(99.6, 100, 99, 99.4, 1000),
            OHLCV(99.4, 100, 99, 99.5, 1000),  # -0.5% from start
        ]
        is_valid, reason = validator.validate("LONG", candles)
        assert not is_valid
        assert "rejected" in reason.lower()
    
    def test_short_rejected_if_price_rose_more_than_threshold(self):
        """**Feature: profitable-trading-overhaul, Property 6**
        **Validates: Requirements 5.2**
        """
        validator = DirectionValidator()
        # Price rose 0.5% (> 0.3% threshold)
        candles = [
            OHLCV(100, 101, 99, 100, 1000),
            OHLCV(100, 101, 99, 100.2, 1000),
            OHLCV(100.2, 101, 100, 100.4, 1000),
            OHLCV(100.4, 101, 100, 100.5, 1000),
            OHLCV(100.5, 101, 100, 100.5, 1000),  # +0.5% from start
        ]
        is_valid, reason = validator.validate("SHORT", candles)
        assert not is_valid
        assert "rejected" in reason.lower()
    
    def test_long_accepted_if_price_stable(self):
        """**Feature: profitable-trading-overhaul, Property 6**
        **Validates: Requirements 5.1**
        """
        validator = DirectionValidator()
        # Price stable (within 0.3%)
        candles = [
            OHLCV(100, 101, 99, 100, 1000),
            OHLCV(100, 101, 99, 100.1, 1000),
            OHLCV(100.1, 101, 99, 100.0, 1000),
            OHLCV(100.0, 101, 99, 99.9, 1000),
            OHLCV(99.9, 101, 99, 99.8, 1000),  # -0.2% from start
        ]
        is_valid, reason = validator.validate("LONG", candles)
        assert is_valid


# =============================================================================
# Property 7: Trailing stop activation and tightening
# **Validates: Requirements 6.1, 6.2, 6.3**
# =============================================================================

class TestATRTrailingStopManager:
    """Tests for ATRTrailingStopManager - Property 7."""
    
    def test_trailing_activates_at_2_percent_profit(self):
        """**Feature: profitable-trading-overhaul, Property 7**
        **Validates: Requirements 6.1**
        """
        manager = ATRTrailingStopManager()
        
        # Entry at 100, current at 102 = 2% profit
        state, should_close = manager.update(
            "BTCUSDT", 102.0, 100.0, "LONG", 1.0
        )
        assert state.is_active
        assert not should_close
    
    def test_trailing_uses_1_5x_atr_normally(self):
        """**Feature: profitable-trading-overhaul, Property 7**
        **Validates: Requirements 6.2**
        """
        manager = ATRTrailingStopManager()
        
        # Entry at 100, current at 103 = 3% profit (active but not tight)
        state, _ = manager.update("BTCUSDT", 103.0, 100.0, "LONG", 1.0)
        assert state.trail_multiplier == 1.5
    
    def test_trailing_tightens_to_1x_at_5_percent(self):
        """**Feature: profitable-trading-overhaul, Property 7**
        **Validates: Requirements 6.3**
        """
        manager = ATRTrailingStopManager()
        
        # Entry at 100, current at 106 = 6% profit (should tighten)
        state, _ = manager.update("BTCUSDT", 106.0, 100.0, "LONG", 1.0)
        assert state.trail_multiplier == 1.0


# =============================================================================
# Property 10: Entry confirmation with cancellation
# **Validates: Requirements 10.1, 10.2, 10.3, 10.4**
# =============================================================================

class TestEntryConfirmer:
    """Tests for EntryConfirmer - Property 10."""
    
    def test_entry_cancelled_if_price_moves_against_long(self):
        """**Feature: profitable-trading-overhaul, Property 10**
        **Validates: Requirements 10.3**
        """
        confirmer = EntryConfirmer()
        confirmer.create_pending("BTCUSDT", "LONG", 100.0)
        
        # Price fell 0.6% (> 0.5% threshold)
        should_execute, reason = confirmer.check_confirmation(
            "BTCUSDT", 99.4, candles_elapsed=1
        )
        assert not should_execute
        assert "cancelled" in reason.lower()
    
    def test_entry_cancelled_if_price_moves_against_short(self):
        """**Feature: profitable-trading-overhaul, Property 10**
        **Validates: Requirements 10.3**
        """
        confirmer = EntryConfirmer()
        confirmer.create_pending("BTCUSDT", "SHORT", 100.0)
        
        # Price rose 0.6% (> 0.5% threshold)
        should_execute, reason = confirmer.check_confirmation(
            "BTCUSDT", 100.6, candles_elapsed=1
        )
        assert not should_execute
        assert "cancelled" in reason.lower()
    
    def test_entry_executes_after_confirmation_period(self):
        """**Feature: profitable-trading-overhaul, Property 10**
        **Validates: Requirements 10.4**
        """
        confirmer = EntryConfirmer()
        confirmer.create_pending("BTCUSDT", "LONG", 100.0, confirmation_candles=2)
        
        # Price stable, 2 candles elapsed
        should_execute, reason = confirmer.check_confirmation(
            "BTCUSDT", 100.2, candles_elapsed=2
        )
        assert should_execute
        assert "complete" in reason.lower()
