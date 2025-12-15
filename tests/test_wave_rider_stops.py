"""Tests for Wave Rider Stop Calculator and Trailing Stop.

Includes property-based tests for:
- Property 11: Stop Loss Bounds
- Property 12: Stop Loss Direction
- Property 13: Trailing Stop Activation
- Property 14: Trailing Stop Tightening
"""

import pytest
from hypothesis import given, strategies as st, settings

from src.kinetic_empire.wave_rider.stop_calculator import WaveRiderStopCalculator, StopResult
from src.kinetic_empire.wave_rider.trailing_stop import WaveRiderTrailingStop, TrailingUpdate
from src.kinetic_empire.wave_rider.models import WaveRiderConfig


class TestWaveRiderStopCalculator:
    """Unit tests for WaveRiderStopCalculator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = WaveRiderStopCalculator()
    
    def test_long_stop_below_entry(self):
        """Test LONG stop is below entry price."""
        result = self.calculator.calculate(
            entry_price=100.0,
            direction="LONG",
            atr_14=2.0,  # 2% ATR
        )
        assert result.stop_price < 100.0
    
    def test_short_stop_above_entry(self):
        """Test SHORT stop is above entry price."""
        result = self.calculator.calculate(
            entry_price=100.0,
            direction="SHORT",
            atr_14=2.0,
        )
        assert result.stop_price > 100.0
    
    def test_min_bound_applied(self):
        """Test minimum 0.5% bound is applied."""
        result = self.calculator.calculate(
            entry_price=100.0,
            direction="LONG",
            atr_14=0.1,  # Very small ATR
        )
        assert result.stop_pct >= 0.005
        assert result.is_min_bounded is True
    
    def test_max_bound_applied(self):
        """Test maximum 3% bound is applied."""
        result = self.calculator.calculate(
            entry_price=100.0,
            direction="LONG",
            atr_14=10.0,  # Very large ATR
        )
        assert result.stop_pct <= 0.03
        assert result.is_max_bounded is True
    
    def test_normal_atr_no_bounds(self):
        """Test normal ATR doesn't hit bounds."""
        result = self.calculator.calculate(
            entry_price=100.0,
            direction="LONG",
            atr_14=1.0,  # 1% ATR, 1.5x = 1.5%
        )
        assert result.stop_pct == pytest.approx(0.015)
        assert result.is_min_bounded is False
        assert result.is_max_bounded is False
    
    def test_stop_hit_long(self):
        """Test stop hit detection for LONG."""
        assert self.calculator.is_stop_hit(95.0, 96.0, "LONG") is True
        assert self.calculator.is_stop_hit(97.0, 96.0, "LONG") is False
    
    def test_stop_hit_short(self):
        """Test stop hit detection for SHORT."""
        assert self.calculator.is_stop_hit(105.0, 104.0, "SHORT") is True
        assert self.calculator.is_stop_hit(103.0, 104.0, "SHORT") is False


class TestStopLossBoundsProperty:
    """Property-based tests for Stop Loss Bounds.
    
    Property 11: Stop Loss Bounds
    - stop_pct >= 0.5% (minimum)
    - stop_pct <= 3.0% (maximum)
    
    Validates: Requirements 6.2, 6.3
    """
    
    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = WaveRiderStopCalculator()
    
    @given(
        entry_price=st.floats(min_value=1.0, max_value=100000.0, allow_nan=False, allow_infinity=False),
        atr_14=st.floats(min_value=0.001, max_value=1000.0, allow_nan=False, allow_infinity=False),
        direction=st.sampled_from(["LONG", "SHORT"]),
    )
    @settings(max_examples=100)
    def test_property_stop_pct_min_bound(self, entry_price: float, atr_14: float, direction: str):
        """Property: stop_pct >= 0.5%."""
        result = self.calculator.calculate(entry_price, direction, atr_14)
        assert result.stop_pct >= 0.005
    
    @given(
        entry_price=st.floats(min_value=1.0, max_value=100000.0, allow_nan=False, allow_infinity=False),
        atr_14=st.floats(min_value=0.001, max_value=1000.0, allow_nan=False, allow_infinity=False),
        direction=st.sampled_from(["LONG", "SHORT"]),
    )
    @settings(max_examples=100)
    def test_property_stop_pct_max_bound(self, entry_price: float, atr_14: float, direction: str):
        """Property: stop_pct <= 3.0%."""
        result = self.calculator.calculate(entry_price, direction, atr_14)
        assert result.stop_pct <= 0.03


class TestStopLossDirectionProperty:
    """Property-based tests for Stop Loss Direction.
    
    Property 12: Stop Loss Direction
    - LONG positions have stop_price < entry_price
    - SHORT positions have stop_price > entry_price
    
    Validates: Requirements 6.4, 6.5
    """
    
    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = WaveRiderStopCalculator()
    
    @given(
        entry_price=st.floats(min_value=1.0, max_value=100000.0, allow_nan=False, allow_infinity=False),
        atr_14=st.floats(min_value=0.001, max_value=100.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_property_long_stop_below_entry(self, entry_price: float, atr_14: float):
        """Property: LONG stop_price < entry_price."""
        result = self.calculator.calculate(entry_price, "LONG", atr_14)
        assert result.stop_price < entry_price
    
    @given(
        entry_price=st.floats(min_value=1.0, max_value=100000.0, allow_nan=False, allow_infinity=False),
        atr_14=st.floats(min_value=0.001, max_value=100.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_property_short_stop_above_entry(self, entry_price: float, atr_14: float):
        """Property: SHORT stop_price > entry_price."""
        result = self.calculator.calculate(entry_price, "SHORT", atr_14)
        assert result.stop_price > entry_price


class TestWaveRiderTrailingStop:
    """Unit tests for WaveRiderTrailingStop."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.trailing = WaveRiderTrailingStop()
    
    def test_not_active_below_1_percent(self):
        """Test trailing not active below 1% profit."""
        result = self.trailing.update(
            symbol="BTCUSDT",
            current_price=100.5,  # 0.5% profit
            entry_price=100.0,
            direction="LONG",
            atr_14=1.0,
        )
        assert result.state.is_active is False
    
    def test_activates_at_1_percent(self):
        """Test trailing activates at 1% profit."""
        result = self.trailing.update(
            symbol="BTCUSDT",
            current_price=101.0,  # 1% profit
            entry_price=100.0,
            direction="LONG",
            atr_14=1.0,
        )
        assert result.state.is_active is True
    
    def test_tp1_at_1_5_percent(self):
        """Test TP1 triggers at 1.5% profit."""
        result = self.trailing.update(
            symbol="BTCUSDT",
            current_price=101.5,  # 1.5% profit
            entry_price=100.0,
            direction="LONG",
            atr_14=1.0,
        )
        assert result.should_close is True
        assert result.close_pct == 0.30
        assert result.close_reason == "tp1"
    
    def test_tp2_after_tp1(self):
        """Test TP2 triggers after TP1."""
        # First trigger TP1
        self.trailing.update("BTCUSDT", 101.5, 100.0, "LONG", 1.0)
        
        # Then trigger TP2
        result = self.trailing.update(
            symbol="BTCUSDT",
            current_price=102.5,  # 2.5% profit
            entry_price=100.0,
            direction="LONG",
            atr_14=1.0,
        )
        assert result.should_close is True
        assert result.close_pct == 0.30
        assert result.close_reason == "tp2"
    
    def test_trail_tightens_at_3_percent(self):
        """Test trail multiplier tightens at 3% profit."""
        # Activate trailing
        self.trailing.update("BTCUSDT", 101.0, 100.0, "LONG", 1.0)
        # Trigger TP1
        self.trailing.update("BTCUSDT", 101.5, 100.0, "LONG", 1.0)
        # Trigger TP2
        self.trailing.update("BTCUSDT", 102.5, 100.0, "LONG", 1.0)
        # Go to 3%+ profit
        result = self.trailing.update("BTCUSDT", 103.0, 100.0, "LONG", 1.0)
        
        assert result.state.trail_multiplier == 0.5
    
    def test_trailing_stop_triggered(self):
        """Test trailing stop triggers on pullback."""
        # Activate and reach peak
        self.trailing.update("BTCUSDT", 101.0, 100.0, "LONG", 0.5)
        self.trailing.update("BTCUSDT", 101.5, 100.0, "LONG", 0.5)  # TP1
        self.trailing.update("BTCUSDT", 102.0, 100.0, "LONG", 0.5)  # New peak
        
        # Pullback below trail (peak 102, trail = 102 - 0.5*0.8 = 101.6)
        result = self.trailing.update("BTCUSDT", 101.5, 100.0, "LONG", 0.5)
        
        assert result.should_close is True
        assert result.close_reason == "trailing"


class TestTrailingStopActivationProperty:
    """Property-based tests for Trailing Stop Activation.
    
    Property 13: Trailing Stop Activation
    Trailing stop activates when unrealized_profit >= 1.0%
    
    Validates: Requirements 7.1
    """
    
    def setup_method(self):
        """Set up test fixtures."""
        self.trailing = WaveRiderTrailingStop()
    
    @given(st.floats(min_value=0.0, max_value=0.0099, allow_nan=False, allow_infinity=False))
    def test_property_not_active_below_1_percent(self, profit_pct: float):
        """Property: profit < 1% => not active."""
        assert self.trailing.is_trailing_active(profit_pct) is False
    
    @given(st.floats(min_value=0.01, max_value=0.5, allow_nan=False, allow_infinity=False))
    def test_property_active_at_or_above_1_percent(self, profit_pct: float):
        """Property: profit >= 1% => active."""
        assert self.trailing.is_trailing_active(profit_pct) is True


class TestTrailingStopTighteningProperty:
    """Property-based tests for Trailing Stop Tightening.
    
    Property 14: Trailing Stop Tightening
    - Trail multiplier is 0.8x ATR when profit < 3%
    - Trail multiplier is 0.5x ATR when profit >= 3%
    
    Validates: Requirements 7.2, 7.5
    """
    
    def setup_method(self):
        """Set up test fixtures."""
        self.trailing = WaveRiderTrailingStop()
    
    @given(st.floats(min_value=0.01, max_value=0.0299, allow_nan=False, allow_infinity=False))
    def test_property_initial_multiplier_below_3_percent(self, profit_pct: float):
        """Property: profit < 3% => 0.8x multiplier."""
        mult = self.trailing.get_trail_multiplier(profit_pct)
        assert mult == 0.8
    
    @given(st.floats(min_value=0.03, max_value=0.5, allow_nan=False, allow_infinity=False))
    def test_property_tight_multiplier_at_or_above_3_percent(self, profit_pct: float):
        """Property: profit >= 3% => 0.5x multiplier."""
        mult = self.trailing.get_trail_multiplier(profit_pct)
        assert mult == 0.5
