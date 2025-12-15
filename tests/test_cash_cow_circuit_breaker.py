"""Property-based tests for Circuit Breaker.

Uses Hypothesis for property-based testing to verify correctness properties
defined in the design document.
"""

import pytest
from hypothesis import given, strategies as st, settings

from src.kinetic_empire.cash_cow.circuit_breaker import CircuitBreaker, CircuitBreakerConfig


class TestCircuitBreakerActivation:
    """Tests for Property 5: Circuit breaker activation."""

    # **Feature: cash-cow-upgrade, Property 5: Circuit breaker activation**
    # *For any* daily P&L and portfolio value where daily loss exceeds 2%,
    # the circuit breaker SHALL be triggered and new entries SHALL be blocked.
    # **Validates: Requirements 3.1, 3.4**

    @given(
        portfolio_value=st.floats(min_value=1000, max_value=1_000_000, allow_nan=False),
        loss_pct=st.floats(min_value=2.01, max_value=50.0, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_triggers_at_2_percent_loss(self, portfolio_value: float, loss_pct: float):
        """Circuit breaker should trigger when loss >= 2%."""
        breaker = CircuitBreaker()
        
        daily_pnl = -portfolio_value * (loss_pct / 100)
        
        triggered = breaker.check_and_trigger(daily_pnl, portfolio_value)
        
        assert triggered, f"Should trigger at {loss_pct}% loss"
        assert breaker.is_triggered
        assert not breaker.can_enter_new_trade()

    @given(
        portfolio_value=st.floats(min_value=1000, max_value=1_000_000, allow_nan=False),
        loss_pct=st.floats(min_value=0.0, max_value=1.99, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_does_not_trigger_below_2_percent(self, portfolio_value: float, loss_pct: float):
        """Circuit breaker should not trigger when loss < 2%."""
        breaker = CircuitBreaker()
        
        daily_pnl = -portfolio_value * (loss_pct / 100)
        
        triggered = breaker.check_and_trigger(daily_pnl, portfolio_value)
        
        assert not triggered, f"Should not trigger at {loss_pct}% loss"
        assert not breaker.is_triggered
        assert breaker.can_enter_new_trade()

    @given(
        portfolio_value=st.floats(min_value=1000, max_value=1_000_000, allow_nan=False),
        profit_pct=st.floats(min_value=0.0, max_value=50.0, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_does_not_trigger_on_profit(self, portfolio_value: float, profit_pct: float):
        """Circuit breaker should not trigger on positive P&L."""
        breaker = CircuitBreaker()
        
        daily_pnl = portfolio_value * (profit_pct / 100)  # Positive
        
        triggered = breaker.check_and_trigger(daily_pnl, portfolio_value)
        
        assert not triggered
        assert breaker.can_enter_new_trade()


class TestCircuitBreakerReset:
    """Tests for Property 6: Circuit breaker reset."""

    # **Feature: cash-cow-upgrade, Property 6: Circuit breaker reset**
    # *For any* triggered circuit breaker, after a new trading day begins,
    # the circuit breaker SHALL be reset and trading SHALL be allowed.
    # **Validates: Requirements 3.3**

    @given(
        portfolio_value=st.floats(min_value=1000, max_value=1_000_000, allow_nan=False),
        loss_pct=st.floats(min_value=2.01, max_value=50.0, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_reset_allows_trading(self, portfolio_value: float, loss_pct: float):
        """After reset, trading should be allowed."""
        breaker = CircuitBreaker()
        
        # Trigger the breaker
        daily_pnl = -portfolio_value * (loss_pct / 100)
        breaker.check_and_trigger(daily_pnl, portfolio_value)
        
        assert breaker.is_triggered
        assert not breaker.can_enter_new_trade()
        
        # Reset for new day
        breaker.reset_for_new_day()
        
        assert not breaker.is_triggered
        assert breaker.can_enter_new_trade()
        assert breaker.trigger_time is None
        assert breaker.trigger_loss_pct is None


class TestExitAllowed:
    """Tests for exit behavior when circuit breaker is active."""

    @given(
        portfolio_value=st.floats(min_value=1000, max_value=1_000_000, allow_nan=False),
        loss_pct=st.floats(min_value=2.01, max_value=50.0, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_exits_allowed_when_triggered(self, portfolio_value: float, loss_pct: float):
        """Exits should always be allowed, even when triggered."""
        breaker = CircuitBreaker()
        
        # Trigger the breaker
        daily_pnl = -portfolio_value * (loss_pct / 100)
        breaker.check_and_trigger(daily_pnl, portfolio_value)
        
        assert breaker.is_triggered
        assert breaker.can_exit_position(), "Exits should always be allowed"

    def test_exits_allowed_when_not_triggered(self):
        """Exits should be allowed when not triggered."""
        breaker = CircuitBreaker()
        assert breaker.can_exit_position()


class TestCustomThreshold:
    """Tests for custom threshold configuration."""

    @given(
        threshold=st.floats(min_value=0.5, max_value=10.0, allow_nan=False),
        portfolio_value=st.floats(min_value=1000, max_value=100000, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_custom_threshold_respected(self, threshold: float, portfolio_value: float):
        """Custom threshold should be respected."""
        config = CircuitBreakerConfig(daily_loss_limit_pct=threshold)
        breaker = CircuitBreaker(config)
        
        # Loss slightly above threshold should trigger (add small buffer for float precision)
        daily_pnl = -portfolio_value * ((threshold + 0.01) / 100)
        triggered = breaker.check_and_trigger(daily_pnl, portfolio_value)
        
        assert triggered, f"Should trigger at {threshold}% threshold"

    @given(
        threshold=st.floats(min_value=1.0, max_value=10.0, allow_nan=False),
        portfolio_value=st.floats(min_value=1000, max_value=100000, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_below_custom_threshold_no_trigger(self, threshold: float, portfolio_value: float):
        """Loss below custom threshold should not trigger."""
        config = CircuitBreakerConfig(daily_loss_limit_pct=threshold)
        breaker = CircuitBreaker(config)
        
        # Loss below threshold
        daily_pnl = -portfolio_value * ((threshold - 0.5) / 100)
        triggered = breaker.check_and_trigger(daily_pnl, portfolio_value)
        
        assert not triggered


class TestStatusReporting:
    """Tests for status reporting."""

    def test_status_contains_required_fields(self):
        """Status should contain all required fields."""
        breaker = CircuitBreaker()
        status = breaker.get_status()
        
        required_fields = [
            "is_triggered",
            "trigger_time",
            "trigger_loss_pct",
            "daily_loss_limit_pct",
            "can_enter",
            "can_exit"
        ]
        
        for field in required_fields:
            assert field in status, f"Missing field: {field}"

    def test_status_reflects_state(self):
        """Status should accurately reflect current state."""
        breaker = CircuitBreaker()
        
        # Initial state
        status = breaker.get_status()
        assert status["is_triggered"] is False
        assert status["can_enter"] is True
        
        # After trigger
        breaker.check_and_trigger(-300, 10000)  # 3% loss
        status = breaker.get_status()
        assert status["is_triggered"] is True
        assert status["can_enter"] is False
        assert status["trigger_loss_pct"] is not None
