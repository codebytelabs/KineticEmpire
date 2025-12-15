"""Tests for Wave Rider Risk Management Components.

Includes property-based tests for:
- Property 15: Circuit Breaker Activation
- Property 16: Blacklist After Losses
- Property 17: Position Limit Enforcement
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime, timedelta

from src.kinetic_empire.wave_rider.risk_manager import (
    WaveRiderCircuitBreaker,
    WaveRiderBlacklist,
    WaveRiderPositionLimit,
)
from src.kinetic_empire.wave_rider.models import WaveRiderConfig


class TestWaveRiderCircuitBreaker:
    """Unit tests for WaveRiderCircuitBreaker."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.breaker = WaveRiderCircuitBreaker()
        self.breaker.initialize(10000.0)
    
    def test_can_trade_initially(self):
        """Test trading is allowed initially."""
        assert self.breaker.can_trade() is True
    
    def test_small_loss_no_trigger(self):
        """Test small loss doesn't trigger breaker."""
        triggered = self.breaker.record_pnl(-100.0)  # 1% loss
        assert triggered is False
        assert self.breaker.can_trade() is True
    
    def test_large_loss_triggers(self):
        """Test loss > 3% triggers breaker."""
        triggered = self.breaker.record_pnl(-350.0)  # 3.5% loss
        assert triggered is True
        assert self.breaker.can_trade() is False
    
    def test_cumulative_losses_trigger(self):
        """Test cumulative losses trigger breaker."""
        self.breaker.record_pnl(-100.0)  # 1%
        self.breaker.record_pnl(-100.0)  # 2%
        triggered = self.breaker.record_pnl(-150.0)  # 3.5% total
        
        assert triggered is True
        assert self.breaker.can_trade() is False
    
    def test_wins_offset_losses(self):
        """Test wins offset losses."""
        self.breaker.record_pnl(-200.0)  # 2% loss
        self.breaker.record_pnl(100.0)   # 1% win
        triggered = self.breaker.record_pnl(-100.0)  # Net 2% loss
        
        assert triggered is False
        assert self.breaker.can_trade() is True


class TestWaveRiderBlacklist:
    """Unit tests for WaveRiderBlacklist."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.blacklist = WaveRiderBlacklist()
    
    def test_not_blacklisted_initially(self):
        """Test symbol not blacklisted initially."""
        assert self.blacklist.is_blacklisted("BTCUSDT") is False
    
    def test_one_loss_no_blacklist(self):
        """Test one loss doesn't blacklist."""
        blacklisted = self.blacklist.record_loss("BTCUSDT")
        assert blacklisted is False
        assert self.blacklist.is_blacklisted("BTCUSDT") is False
    
    def test_two_losses_blacklists(self):
        """Test two consecutive losses blacklists."""
        self.blacklist.record_loss("BTCUSDT")
        blacklisted = self.blacklist.record_loss("BTCUSDT")
        
        assert blacklisted is True
        assert self.blacklist.is_blacklisted("BTCUSDT") is True
    
    def test_win_resets_count(self):
        """Test win resets loss count."""
        self.blacklist.record_loss("BTCUSDT")
        self.blacklist.record_win("BTCUSDT")
        blacklisted = self.blacklist.record_loss("BTCUSDT")
        
        assert blacklisted is False
        assert self.blacklist.is_blacklisted("BTCUSDT") is False
    
    def test_different_symbols_independent(self):
        """Test different symbols have independent counts."""
        self.blacklist.record_loss("BTCUSDT")
        self.blacklist.record_loss("BTCUSDT")  # Blacklisted
        
        self.blacklist.record_loss("ETHUSDT")  # First loss
        
        assert self.blacklist.is_blacklisted("BTCUSDT") is True
        assert self.blacklist.is_blacklisted("ETHUSDT") is False


class TestWaveRiderPositionLimit:
    """Unit tests for WaveRiderPositionLimit."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.limiter = WaveRiderPositionLimit()
    
    def test_can_open_initially(self):
        """Test can open positions initially."""
        assert self.limiter.can_open_position() is True
    
    def test_add_positions_up_to_limit(self):
        """Test can add positions up to limit."""
        for i in range(5):
            result = self.limiter.add_position(f"COIN{i}USDT")
            assert result is True
        
        assert self.limiter.get_open_count() == 5
    
    def test_cannot_exceed_limit(self):
        """Test cannot exceed position limit."""
        for i in range(5):
            self.limiter.add_position(f"COIN{i}USDT")
        
        result = self.limiter.add_position("EXTRAUSDT")
        assert result is False
        assert self.limiter.can_open_position() is False
    
    def test_remove_allows_new(self):
        """Test removing position allows new one."""
        for i in range(5):
            self.limiter.add_position(f"COIN{i}USDT")
        
        self.limiter.remove_position("COIN0USDT")
        
        assert self.limiter.can_open_position() is True
        result = self.limiter.add_position("NEWUSDT")
        assert result is True


class TestCircuitBreakerProperty:
    """Property-based tests for Circuit Breaker Activation.
    
    Property 15: Circuit Breaker Activation
    New trades SHALL be halted when daily_realized_loss > 3% of starting_balance.
    
    Validates: Requirements 9.1
    """
    
    def setup_method(self):
        """Set up test fixtures."""
        self.breaker = WaveRiderCircuitBreaker()
    
    @given(st.floats(min_value=0.0, max_value=0.03, allow_nan=False, allow_infinity=False))
    def test_property_no_trigger_at_or_below_3_percent(self, loss_pct: float):
        """Property: loss <= 3% => no trigger."""
        assert self.breaker.check_would_trigger(loss_pct) is False
    
    @given(st.floats(min_value=0.0301, max_value=1.0, allow_nan=False, allow_infinity=False))
    def test_property_trigger_above_3_percent(self, loss_pct: float):
        """Property: loss > 3% => trigger."""
        assert self.breaker.check_would_trigger(loss_pct) is True


class TestBlacklistProperty:
    """Property-based tests for Blacklist After Losses.
    
    Property 16: Blacklist After Losses
    Symbol SHALL be blacklisted for 30 minutes after 2 consecutive losses.
    
    Validates: Requirements 9.2
    """
    
    def setup_method(self):
        """Set up test fixtures."""
        self.blacklist = WaveRiderBlacklist()
    
    @given(st.integers(min_value=0, max_value=1))
    def test_property_no_blacklist_below_2_losses(self, losses: int):
        """Property: < 2 losses => no blacklist."""
        assert self.blacklist.should_blacklist(losses) is False
    
    @given(st.integers(min_value=2, max_value=10))
    def test_property_blacklist_at_or_above_2_losses(self, losses: int):
        """Property: >= 2 losses => blacklist."""
        assert self.blacklist.should_blacklist(losses) is True


class TestPositionLimitProperty:
    """Property-based tests for Position Limit Enforcement.
    
    Property 17: Position Limit Enforcement
    New position opening SHALL be rejected when open_positions >= 5.
    
    Validates: Requirements 9.3
    """
    
    def setup_method(self):
        """Set up test fixtures."""
        self.limiter = WaveRiderPositionLimit()
    
    @given(st.integers(min_value=0, max_value=4))
    def test_property_allow_below_5_positions(self, count: int):
        """Property: < 5 positions => allow new."""
        assert self.limiter.would_exceed_limit(count) is False
    
    @given(st.integers(min_value=5, max_value=20))
    def test_property_reject_at_or_above_5_positions(self, count: int):
        """Property: >= 5 positions => reject new."""
        assert self.limiter.would_exceed_limit(count) is True
