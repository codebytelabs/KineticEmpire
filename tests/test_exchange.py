"""Property-based tests for exchange module.

Tests validate:
- Property 19: Rate Limiting Enforcement
- Property 20: Order Type Selection
- Property 21: Order Timeout Enforcement
- Property 22: FailSafe Mode Trigger
"""

import time
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings
import pytest

from kinetic_empire.exchange.client import (
    ExchangeModule, ExchangeConfig, RateLimiter, FailSafeManager,
    OrderType, OrderSide, Order
)


class TestRateLimitingEnforcement:
    """Tests for Property 19: Rate Limiting Enforcement."""

    def test_rate_limiter_enforces_minimum_interval(self):
        """
        **Feature: kinetic-empire, Property 19: Rate Limiting Enforcement**
        
        *For any* sequence of API requests, the time between consecutive 
        requests SHALL be >= 200ms.
        **Validates: Requirements 9.2**
        """
        limiter = RateLimiter(min_interval_ms=200)
        
        # First request - no wait
        limiter.wait()
        first_time = time.time()
        
        # Second request - should wait
        limiter.wait()
        second_time = time.time()
        
        elapsed_ms = (second_time - first_time) * 1000
        
        # Should have waited at least 200ms (with small tolerance)
        assert elapsed_ms >= 195  # 5ms tolerance for timing

    def test_rate_limiter_no_wait_after_interval(self):
        """No wait needed if enough time has passed."""
        limiter = RateLimiter(min_interval_ms=50)
        
        limiter.wait()
        time.sleep(0.1)  # Wait 100ms
        
        start = time.time()
        wait_time = limiter.wait()
        elapsed = (time.time() - start) * 1000
        
        # Should not have waited
        assert wait_time == 0.0
        assert elapsed < 10  # Very quick

    @given(interval=st.integers(min_value=50, max_value=150))
    @settings(max_examples=20, deadline=None)
    def test_rate_limiter_respects_custom_interval(self, interval):
        """Rate limiter should respect custom interval."""
        limiter = RateLimiter(min_interval_ms=interval)
        
        limiter.wait()
        start = time.time()
        limiter.wait()
        elapsed_ms = (time.time() - start) * 1000
        
        # Should have waited at least the interval (with tolerance)
        assert elapsed_ms >= interval - 10


class TestOrderTypeSelection:
    """Tests for Property 20: Order Type Selection."""

    @given(action=st.sampled_from(["entry", "exit"]))
    @settings(max_examples=20)
    def test_entry_exit_use_limit_orders(self, action):
        """
        **Feature: kinetic-empire, Property 20: Order Type Selection**
        
        *For any* order, entry and exit orders SHALL use limit type.
        **Validates: Requirements 9.3**
        """
        exchange = ExchangeModule()
        
        order_type = exchange.get_order_type_for_action(action)
        
        assert order_type == OrderType.LIMIT

    @given(action=st.sampled_from(["emergency_exit", "stoploss"]))
    @settings(max_examples=20)
    def test_emergency_stoploss_use_market_orders(self, action):
        """
        **Feature: kinetic-empire, Property 20: Order Type Selection**
        
        *For any* order, emergency_exit and stoploss orders SHALL use market type.
        **Validates: Requirements 9.3**
        """
        exchange = ExchangeModule()
        
        order_type = exchange.get_order_type_for_action(action)
        
        assert order_type == OrderType.MARKET

    def test_limit_order_creation(self):
        """Limit orders should have correct type."""
        exchange = ExchangeModule()
        
        order = exchange.place_limit_order(
            pair="BTC/USDT",
            side=OrderSide.BUY,
            amount=0.1,
            price=50000.0
        )
        
        assert order.order_type == OrderType.LIMIT
        assert order.price == 50000.0

    def test_market_order_creation(self):
        """Market orders should have correct type."""
        exchange = ExchangeModule()
        
        order = exchange.place_market_order(
            pair="BTC/USDT",
            side=OrderSide.SELL,
            amount=0.1
        )
        
        assert order.order_type == OrderType.MARKET
        assert order.status == "filled"

    def test_stop_loss_order_is_market(self):
        """Stop loss orders should be market type."""
        exchange = ExchangeModule()
        
        order = exchange.place_stop_loss_order(
            pair="BTC/USDT",
            amount=0.1,
            stop_price=48000.0
        )
        
        assert order.order_type == OrderType.MARKET
        assert order.side == OrderSide.SELL


class TestOrderTimeoutEnforcement:
    """Tests for Property 21: Order Timeout Enforcement."""

    def test_entry_order_timeout_10_minutes(self):
        """
        **Feature: kinetic-empire, Property 21: Order Timeout Enforcement**
        
        *For any* unfilled order, entry orders SHALL be cancelled after 10 minutes.
        **Validates: Requirements 9.4**
        """
        exchange = ExchangeModule()
        
        order = Order(
            id="test_order",
            pair="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            amount=0.1,
            price=50000.0,
            timestamp=datetime.now() - timedelta(minutes=11),
            status="open"
        )
        
        assert exchange.check_order_timeout(order) is True
        assert exchange.get_timeout_minutes(order) == 10

    def test_exit_order_timeout_30_minutes(self):
        """
        **Feature: kinetic-empire, Property 21: Order Timeout Enforcement**
        
        *For any* unfilled order, exit orders SHALL be cancelled after 30 minutes.
        **Validates: Requirements 9.4**
        """
        exchange = ExchangeModule()
        
        order = Order(
            id="test_order",
            pair="BTC/USDT",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            amount=0.1,
            price=51000.0,
            timestamp=datetime.now() - timedelta(minutes=31),
            status="open"
        )
        
        assert exchange.check_order_timeout(order) is True
        assert exchange.get_timeout_minutes(order) == 30

    def test_entry_order_not_timed_out(self):
        """Entry order within timeout should not be flagged."""
        exchange = ExchangeModule()
        
        order = Order(
            id="test_order",
            pair="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            amount=0.1,
            price=50000.0,
            timestamp=datetime.now() - timedelta(minutes=5),
            status="open"
        )
        
        assert exchange.check_order_timeout(order) is False

    def test_exit_order_not_timed_out(self):
        """Exit order within timeout should not be flagged."""
        exchange = ExchangeModule()
        
        order = Order(
            id="test_order",
            pair="BTC/USDT",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            amount=0.1,
            price=51000.0,
            timestamp=datetime.now() - timedelta(minutes=20),
            status="open"
        )
        
        assert exchange.check_order_timeout(order) is False

    def test_filled_order_not_timed_out(self):
        """Filled orders should not be flagged for timeout."""
        exchange = ExchangeModule()
        
        order = Order(
            id="test_order",
            pair="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            amount=0.1,
            price=50000.0,
            timestamp=datetime.now() - timedelta(minutes=60),
            status="filled"
        )
        
        assert exchange.check_order_timeout(order) is False


class TestFailSafeModeTrigger:
    """Tests for Property 22: FailSafe Mode Trigger."""

    def test_failsafe_triggers_after_5_minutes(self):
        """
        **Feature: kinetic-empire, Property 22: FailSafe Mode Trigger**
        
        *For any* sequence of API errors, if 5xx errors persist for > 5 minutes, 
        the system SHALL enter FailSafe mode and halt new signal processing.
        **Validates: Requirements 9.5**
        """
        failsafe = FailSafeManager(threshold_minutes=5)
        
        # Simulate first error
        failsafe._first_error_time = datetime.now() - timedelta(minutes=6)
        
        # Record another error - should trigger FailSafe
        is_active = failsafe.record_error(is_5xx=True)
        
        assert is_active is True
        assert failsafe.is_active() is True

    def test_failsafe_not_triggered_before_threshold(self):
        """FailSafe should not trigger before threshold."""
        failsafe = FailSafeManager(threshold_minutes=5)
        
        # Record error
        is_active = failsafe.record_error(is_5xx=True)
        
        assert is_active is False
        assert failsafe.is_active() is False

    def test_success_resets_error_tracking(self):
        """Successful call should reset error tracking."""
        failsafe = FailSafeManager(threshold_minutes=5)
        
        # Record error
        failsafe.record_error(is_5xx=True)
        assert failsafe._first_error_time is not None
        
        # Record success
        failsafe.record_success()
        assert failsafe._first_error_time is None

    def test_non_5xx_errors_dont_trigger_failsafe(self):
        """Non-5xx errors should not trigger FailSafe."""
        failsafe = FailSafeManager(threshold_minutes=5)
        
        # Simulate old error time
        failsafe._first_error_time = datetime.now() - timedelta(minutes=10)
        
        # Record non-5xx error
        is_active = failsafe.record_error(is_5xx=False)
        
        assert is_active is False

    def test_exchange_blocks_signals_in_failsafe(self):
        """Exchange should block new signals in FailSafe mode."""
        exchange = ExchangeModule()
        
        # Initially can process
        assert exchange.can_process_signals() is True
        
        # Trigger FailSafe
        exchange.failsafe._first_error_time = datetime.now() - timedelta(minutes=6)
        exchange.failsafe.record_error(is_5xx=True)
        
        # Should block signals
        assert exchange.can_process_signals() is False
        assert exchange.is_failsafe_active() is True

    def test_failsafe_reset(self):
        """FailSafe should be resettable."""
        failsafe = FailSafeManager(threshold_minutes=5)
        
        # Trigger FailSafe
        failsafe._first_error_time = datetime.now() - timedelta(minutes=6)
        failsafe.record_error(is_5xx=True)
        assert failsafe.is_active() is True
        
        # Reset
        failsafe.reset()
        assert failsafe.is_active() is False


class TestOrderManagement:
    """Tests for order management operations."""

    def test_cancel_open_order(self):
        """Open orders can be cancelled."""
        exchange = ExchangeModule()
        
        order = exchange.place_limit_order(
            pair="BTC/USDT",
            side=OrderSide.BUY,
            amount=0.1,
            price=50000.0
        )
        
        assert order.status == "open"
        
        cancelled = exchange.cancel_order(order.id)
        
        assert cancelled is True
        assert exchange.get_order(order.id).status == "cancelled"

    def test_cannot_cancel_filled_order(self):
        """Filled orders cannot be cancelled."""
        exchange = ExchangeModule()
        
        order = exchange.place_market_order(
            pair="BTC/USDT",
            side=OrderSide.SELL,
            amount=0.1
        )
        
        assert order.status == "filled"
        
        cancelled = exchange.cancel_order(order.id)
        
        assert cancelled is False

    def test_get_nonexistent_order(self):
        """Getting nonexistent order returns None."""
        exchange = ExchangeModule()
        
        order = exchange.get_order("nonexistent")
        
        assert order is None
