"""Property-based tests for BlacklistManager.

**Feature: signal-quality-fix, Property 3: Blacklist Lifecycle**
**Validates: Requirements 3.1, 3.2, 3.3**

Updated for profitable-trading-overhaul spec:
- 1 loss triggers blacklist (was 2)
- 60-minute blacklist duration (was 30)
- 30-minute loss window (was 60)
"""

import pytest
from datetime import datetime, timedelta
from hypothesis import given, strategies as st

from src.kinetic_empire.signal_quality.config import QualityGateConfig
from src.kinetic_empire.signal_quality.blacklist_manager import BlacklistManager


# Strategy for generating symbol names
symbol_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('Lu',)),
    min_size=3, max_size=10
).map(lambda s: s + "USDT")


class TestBlacklistManagerProperties:
    """Property-based tests for blacklist lifecycle."""
    
    @given(symbol=symbol_strategy)
    def test_one_loss_triggers_blacklist(self, symbol: str):
        """Property: 1 loss within 30 minutes SHALL blacklist symbol.
        
        **Feature: profitable-trading-overhaul, Property 8: Blacklist trigger**
        **Validates: Requirements 7.1**
        """
        config = QualityGateConfig()  # max_consecutive_losses=1 per new config
        manager = BlacklistManager(config)
        
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        
        # Record 1 loss - should trigger blacklist with new config
        was_blacklisted = manager.record_loss(symbol, base_time)
        
        assert was_blacklisted is True
        assert manager.is_blacklisted(symbol, base_time + timedelta(minutes=1)) is True
    
    @given(symbol=symbol_strategy)
    def test_blacklisted_symbol_returns_true(self, symbol: str):
        """Property: While blacklisted, is_blacklisted SHALL return True.
        
        **Feature: profitable-trading-overhaul, Property 8: Blacklist trigger**
        **Validates: Requirements 7.2**
        """
        config = QualityGateConfig()
        manager = BlacklistManager(config)
        
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        
        # Trigger blacklist (1 loss with new config)
        manager.record_loss(symbol, base_time)
        
        # Check at various times during 60-minute blacklist period
        for minutes in [1, 10, 30, 59]:
            check_time = base_time + timedelta(minutes=minutes)
            assert manager.is_blacklisted(symbol, check_time) is True
    
    @given(symbol=symbol_strategy)
    def test_blacklist_expires_after_60_minutes(self, symbol: str):
        """Property: After 60 minutes, is_blacklisted SHALL return False.
        
        **Feature: profitable-trading-overhaul, Property 8: Blacklist expiration**
        **Validates: Requirements 7.2**
        """
        config = QualityGateConfig()  # blacklist_duration_minutes=60 per new config
        manager = BlacklistManager(config)
        
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        
        # Trigger blacklist - 1 loss
        manager.record_loss(symbol, base_time)
        
        # Check after 60 minutes from blacklist time
        check_time = base_time + timedelta(minutes=60)
        assert manager.is_blacklisted(symbol, check_time) is False


class TestBlacklistManagerEdgeCases:
    """Edge case tests for blacklist manager."""
    
    def test_one_loss_triggers_blacklist(self):
        """One loss should trigger blacklist with new config (max_consecutive_losses=1)."""
        manager = BlacklistManager(QualityGateConfig())
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        
        was_blacklisted = manager.record_loss("BTCUSDT", base_time)
        
        assert was_blacklisted is True
        assert manager.is_blacklisted("BTCUSDT", base_time + timedelta(minutes=1)) is True
    
    def test_losses_outside_window_not_counted(self):
        """Losses outside 30-minute window should not count."""
        manager = BlacklistManager(QualityGateConfig())
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        
        # First loss at time 0 - triggers blacklist
        manager.record_loss("BTCUSDT", base_time)
        
        # Wait for blacklist to expire (60 min)
        # Then record another loss at time 70 (first loss is now outside 30-min window)
        was_blacklisted = manager.record_loss("BTCUSDT", base_time + timedelta(minutes=70))
        
        # Should be blacklisted again (new loss in new window)
        assert was_blacklisted is True
    
    def test_blacklist_exactly_at_60_minutes(self):
        """Blacklist should expire exactly at 60 minutes."""
        manager = BlacklistManager(QualityGateConfig())
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        
        # Trigger blacklist at base_time (1 loss)
        manager.record_loss("BTCUSDT", base_time)
        
        # At 59:59, still blacklisted
        assert manager.is_blacklisted("BTCUSDT", base_time + timedelta(minutes=59, seconds=59)) is True
        
        # At exactly 60:00, no longer blacklisted
        assert manager.is_blacklisted("BTCUSDT", base_time + timedelta(minutes=60)) is False
    
    def test_cleanup_expired(self):
        """cleanup_expired should remove expired entries."""
        manager = BlacklistManager(QualityGateConfig())
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        
        # Blacklist two symbols (1 loss each)
        manager.record_loss("BTCUSDT", base_time)
        manager.record_loss("ETHUSDT", base_time)
        
        assert len(manager.get_blacklisted_symbols()) == 2
        
        # Cleanup after 60 minutes
        removed = manager.cleanup_expired(base_time + timedelta(minutes=60))
        
        assert removed == 2
        assert len(manager.get_blacklisted_symbols()) == 0
    
    def test_different_symbols_independent(self):
        """Losses for different symbols should be tracked independently."""
        manager = BlacklistManager(QualityGateConfig())
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        
        # 1 loss for BTC - triggers blacklist with new config
        manager.record_loss("BTCUSDT", base_time)
        
        # 1 loss for ETH - also triggers blacklist
        manager.record_loss("ETHUSDT", base_time + timedelta(minutes=1))
        
        # Both should be blacklisted
        assert manager.is_blacklisted("BTCUSDT", base_time + timedelta(minutes=10)) is True
        assert manager.is_blacklisted("ETHUSDT", base_time + timedelta(minutes=10)) is True
        
        # After 60 min from BTC loss, BTC should be unblacklisted
        assert manager.is_blacklisted("BTCUSDT", base_time + timedelta(minutes=60)) is False
        # ETH still blacklisted (only 59 min since its loss)
        assert manager.is_blacklisted("ETHUSDT", base_time + timedelta(minutes=60)) is True
