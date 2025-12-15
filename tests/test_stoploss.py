"""Property-based tests for stop loss management.

Tests validate:
- Property 14: Stop Loss Calculation
"""

from hypothesis import given, strategies as st, settings
import pytest

from kinetic_empire.risk.stoploss import StopLossManager, StopLossConfig


class TestStopLossCalculation:
    """Tests for Property 14: Stop Loss Calculation."""

    @given(
        entry_price=st.floats(min_value=0.01, max_value=100000, allow_nan=False),
        atr=st.floats(min_value=0.01, max_value=1000, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_stop_loss_formula(self, entry_price, atr):
        """
        **Feature: kinetic-empire, Property 14: Stop Loss Calculation**
        
        *For any* entry_price and ATR value, initial stop_loss SHALL equal 
        entry_price - (2.0 * ATR).
        **Validates: Requirements 6.1**
        """
        manager = StopLossManager()
        
        expected = entry_price - (2.0 * atr)
        actual = manager.calculate_stop_loss(entry_price, atr)
        
        assert abs(actual - expected) < 1e-10

    @given(
        entry_price=st.floats(min_value=0.01, max_value=100000, allow_nan=False),
        atr=st.floats(min_value=0.01, max_value=1000, allow_nan=False),
        multiplier=st.floats(min_value=0.5, max_value=5.0, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_stop_loss_with_custom_multiplier(self, entry_price, atr, multiplier):
        """Stop loss should respect custom multiplier."""
        manager = StopLossManager()
        
        expected = entry_price - (multiplier * atr)
        actual = manager.calculate_stop_loss(entry_price, atr, multiplier)
        
        assert abs(actual - expected) < 1e-10

    @given(
        entry_price=st.floats(min_value=0.01, max_value=100000, allow_nan=False),
        atr=st.floats(min_value=0.01, max_value=1000, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_stop_loss_below_entry(self, entry_price, atr):
        """Stop loss should always be below entry price."""
        manager = StopLossManager()
        
        stop_loss = manager.calculate_stop_loss(entry_price, atr)
        
        assert stop_loss < entry_price

    def test_stop_loss_with_config(self):
        """Stop loss should use config multiplier."""
        config = StopLossConfig(atr_multiplier=3.0)
        manager = StopLossManager(config)
        
        entry_price = 1000.0
        atr = 10.0
        
        expected = 1000.0 - (3.0 * 10.0)
        actual = manager.calculate_stop_loss(entry_price, atr)
        
        assert abs(actual - expected) < 1e-10

    def test_stop_loss_percentage(self):
        """Stop loss percentage should be negative."""
        manager = StopLossManager()
        
        entry_price = 1000.0
        atr = 10.0
        
        pct = manager.calculate_stop_loss_percentage(entry_price, atr)
        
        # Should be -2% (2.0 * 10 / 1000 * 100)
        assert pct < 0
        assert abs(pct - (-2.0)) < 1e-10
