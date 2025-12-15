"""Property-based tests for trailing stop management.

Tests validate:
- Property 15: Trailing Stop Activation Threshold
- Property 16: Trailing Stop Calculation
- Property 17: Trailing Stop Monotonicity
"""

from hypothesis import given, strategies as st, settings, assume
import pytest

from kinetic_empire.risk.trailing import TrailingStopManager, TrailingConfig


class TestTrailingStopActivation:
    """Tests for Property 15: Trailing Stop Activation Threshold."""

    @given(
        unrealized_profit_pct=st.floats(min_value=-50, max_value=100, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_activation_threshold(self, unrealized_profit_pct):
        """
        **Feature: kinetic-empire, Property 15: Trailing Stop Activation Threshold**
        
        *For any* position, trailing stop mode SHALL activate if and only if 
        unrealized_profit_pct >= 1.5% (optimized from 2.5%).
        **Validates: Requirements 7.1**
        """
        manager = TrailingStopManager()
        
        should_activate = manager.should_activate(unrealized_profit_pct)
        
        # Optimized threshold is 1.5% (0.015 as decimal internally)
        # The optimizer converts percentage to decimal, so 1.5% = 0.015
        if unrealized_profit_pct >= 1.5:
            assert should_activate is True
        else:
            assert should_activate is False

    @given(
        unrealized_profit_pct=st.floats(min_value=-50, max_value=100, allow_nan=False),
        threshold=st.floats(min_value=0.5, max_value=10.0, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_activation_custom_threshold(self, unrealized_profit_pct, threshold):
        """Activation should respect custom threshold when optimizer disabled."""
        # Disable optimizer to test legacy behavior
        config = TrailingConfig(
            activation_profit_pct=threshold,
            use_optimizer=False
        )
        manager = TrailingStopManager(config)
        
        should_activate = manager.should_activate(unrealized_profit_pct, threshold)
        
        if unrealized_profit_pct > threshold:
            assert should_activate is True
        else:
            assert should_activate is False


class TestTrailingStopCalculation:
    """Tests for Property 16: Trailing Stop Calculation."""

    @given(
        current_price=st.floats(min_value=0.01, max_value=100000, allow_nan=False),
        atr=st.floats(min_value=0.01, max_value=1000, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_trailing_stop_formula(self, current_price, atr):
        """
        **Feature: kinetic-empire, Property 16: Trailing Stop Calculation**
        
        *For any* active trailing stop with current_price and ATR, 
        new_stop_level SHALL equal current_price - (1.5 * ATR).
        **Validates: Requirements 7.2**
        """
        manager = TrailingStopManager()
        
        expected = current_price - (1.5 * atr)
        actual = manager.calculate_trailing_stop(current_price, atr)
        
        assert abs(actual - expected) < 1e-10

    @given(
        current_price=st.floats(min_value=0.01, max_value=100000, allow_nan=False),
        atr=st.floats(min_value=0.01, max_value=1000, allow_nan=False),
        multiplier=st.floats(min_value=0.5, max_value=5.0, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_trailing_stop_custom_multiplier(self, current_price, atr, multiplier):
        """Trailing stop should respect custom multiplier."""
        manager = TrailingStopManager()
        
        expected = current_price - (multiplier * atr)
        actual = manager.calculate_trailing_stop(current_price, atr, multiplier)
        
        assert abs(actual - expected) < 1e-10

    @given(
        current_price=st.floats(min_value=0.01, max_value=100000, allow_nan=False),
        atr=st.floats(min_value=0.01, max_value=1000, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_trailing_stop_below_current_price(self, current_price, atr):
        """Trailing stop should always be below current price."""
        manager = TrailingStopManager()
        
        trailing_stop = manager.calculate_trailing_stop(current_price, atr)
        
        assert trailing_stop < current_price


class TestTrailingStopMonotonicity:
    """Tests for Property 17: Trailing Stop Monotonicity."""

    @given(
        new_stop=st.floats(min_value=0.01, max_value=100000, allow_nan=False),
        current_stop=st.floats(min_value=0.01, max_value=100000, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_stop_never_decreases(self, new_stop, current_stop):
        """
        **Feature: kinetic-empire, Property 17: Trailing Stop Monotonicity**
        
        *For any* sequence of trailing stop updates, the stop level SHALL 
        only increase or stay the same, never decrease.
        **Validates: Requirements 7.3, 7.4**
        """
        manager = TrailingStopManager()
        
        updated_stop = manager.update_stop_if_higher(new_stop, current_stop)
        
        # Updated stop should be at least as high as current stop
        assert updated_stop >= current_stop
        
        # Updated stop should be the maximum of the two
        assert updated_stop == max(new_stop, current_stop)

    @given(
        price_sequence=st.lists(
            st.floats(min_value=100, max_value=10000, allow_nan=False),
            min_size=2,
            max_size=20
        ),
        atr=st.floats(min_value=1, max_value=100, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_stop_monotonic_over_sequence(self, price_sequence, atr):
        """Trailing stop should be monotonically increasing over price sequence."""
        manager = TrailingStopManager()
        
        # Start with initial stop
        current_stop = manager.calculate_trailing_stop(price_sequence[0], atr)
        previous_stop = current_stop
        
        # Update stop for each price in sequence
        for price in price_sequence[1:]:
            new_stop = manager.calculate_trailing_stop(price, atr)
            current_stop = manager.update_stop_if_higher(new_stop, current_stop)
            
            # Stop should never decrease
            assert current_stop >= previous_stop
            
            previous_stop = current_stop

    def test_stop_increases_with_rising_price(self):
        """Stop should increase as price rises."""
        manager = TrailingStopManager()
        
        atr = 10.0
        prices = [1000, 1050, 1100, 1150, 1200]
        
        current_stop = manager.calculate_trailing_stop(prices[0], atr)
        
        for price in prices[1:]:
            new_stop = manager.calculate_trailing_stop(price, atr)
            updated_stop = manager.update_stop_if_higher(new_stop, current_stop)
            
            # Stop should increase
            assert updated_stop > current_stop
            
            current_stop = updated_stop

    def test_stop_unchanged_with_falling_price(self):
        """Stop should remain unchanged as price falls."""
        manager = TrailingStopManager()
        
        atr = 10.0
        
        # Price rises then falls
        initial_price = 1000
        high_price = 1200
        falling_price = 1100
        
        # Calculate stop at high
        stop_at_high = manager.calculate_trailing_stop(high_price, atr)
        
        # Calculate stop at falling price
        stop_at_fall = manager.calculate_trailing_stop(falling_price, atr)
        
        # Update should keep higher stop
        final_stop = manager.update_stop_if_higher(stop_at_fall, stop_at_high)
        
        assert final_stop == stop_at_high
        assert final_stop > stop_at_fall


class TestTrailingStopConfig:
    """Tests for configuration handling."""

    def test_custom_config(self):
        """Manager should use custom config values."""
        config = TrailingConfig(
            activation_profit_pct=5.0,
            atr_multiplier=2.0,
            use_optimizer=False  # Disable optimizer to test legacy behavior
        )
        manager = TrailingStopManager(config)
        
        # Test activation threshold
        assert manager.should_activate(4.9) is False
        assert manager.should_activate(5.1) is True
        
        # Test multiplier
        price = 1000.0
        atr = 10.0
        expected = 1000.0 - (2.0 * 10.0)
        actual = manager.calculate_trailing_stop(price, atr)
        
        assert abs(actual - expected) < 1e-10
    
    def test_optimizer_enabled_by_default(self):
        """Optimizer should be enabled by default with 1.5% threshold."""
        manager = TrailingStopManager()
        
        # Should activate at 1.5% (optimized threshold)
        assert manager.should_activate(1.4) is False
        assert manager.should_activate(1.5) is True
        assert manager.should_activate(2.0) is True
