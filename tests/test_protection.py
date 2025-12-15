"""Property-based tests for flash crash protection.

Tests validate:
- Property 30: Flash Crash Detection
- Property 31: Flash Crash Response
- Property 32: Market Stability Recovery
"""

from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings, assume
import pytest

from kinetic_empire.models import PricePoint
from kinetic_empire.risk.protection import FlashCrashProtection, ProtectionConfig


@st.composite
def price_sequence_with_drop(draw, drop_pct: float, window_hours: int = 1):
    """Generate price sequence with specific drop percentage."""
    base_price = draw(st.floats(min_value=10000, max_value=50000, allow_nan=False))
    num_points = draw(st.integers(min_value=window_hours + 1, max_value=window_hours + 10))
    
    start_time = datetime(2023, 1, 1)
    prices = []
    
    # Create rising or stable prices
    for i in range(num_points - 1):
        timestamp = start_time + timedelta(hours=i)
        price = base_price * draw(st.floats(min_value=0.98, max_value=1.02, allow_nan=False))
        prices.append(PricePoint(timestamp=timestamp, price=price))
    
    # Create final price with specified drop
    final_timestamp = start_time + timedelta(hours=num_points - 1)
    highest = max(p.price for p in prices)
    final_price = highest * (1 - drop_pct / 100)
    prices.append(PricePoint(timestamp=final_timestamp, price=final_price))
    
    return prices


class TestFlashCrashDetection:
    """Tests for Property 30: Flash Crash Detection."""

    def test_flash_crash_detected_on_5_percent_drop(self):
        """
        **Feature: kinetic-empire, Property 30: Flash Crash Detection**
        
        *For any* BTC price series where price dropped > 5% within 1 hour, 
        flash crash SHALL be detected.
        **Validates: Requirements 14.1**
        """
        protection = FlashCrashProtection()
        
        # Create price sequence with 6% drop
        start_time = datetime(2023, 1, 1)
        prices = [
            PricePoint(timestamp=start_time, price=50000),
            PricePoint(timestamp=start_time + timedelta(minutes=30), price=49000),
            PricePoint(timestamp=start_time + timedelta(hours=1), price=47000),  # 6% drop
        ]
        
        is_crash = protection.detect_flash_crash(prices)
        
        assert is_crash is True

    def test_no_crash_on_small_drop(self):
        """No crash should be detected for drops < 5%."""
        protection = FlashCrashProtection()
        
        start_time = datetime(2023, 1, 1)
        prices = [
            PricePoint(timestamp=start_time, price=50000),
            PricePoint(timestamp=start_time + timedelta(hours=1), price=48000),  # 4% drop
        ]
        
        is_crash = protection.detect_flash_crash(prices)
        
        assert is_crash is False

    @given(
        drop_pct=st.floats(min_value=5.1, max_value=20.0, allow_nan=False)
    )
    @settings(max_examples=50)
    def test_crash_detected_for_drops_above_threshold(self, drop_pct):
        """Crash should be detected for any drop > 5%."""
        protection = FlashCrashProtection()
        
        start_time = datetime(2023, 1, 1)
        base_price = 50000
        dropped_price = base_price * (1 - drop_pct / 100)
        
        prices = [
            PricePoint(timestamp=start_time, price=base_price),
            PricePoint(timestamp=start_time + timedelta(hours=1), price=dropped_price),
        ]
        
        is_crash = protection.detect_flash_crash(prices)
        
        assert is_crash is True

    @given(
        drop_pct=st.floats(min_value=0.0, max_value=4.9, allow_nan=False)
    )
    @settings(max_examples=50)
    def test_no_crash_for_drops_below_threshold(self, drop_pct):
        """No crash for drops <= 5%."""
        protection = FlashCrashProtection()
        
        start_time = datetime(2023, 1, 1)
        base_price = 50000
        dropped_price = base_price * (1 - drop_pct / 100)
        
        prices = [
            PricePoint(timestamp=start_time, price=base_price),
            PricePoint(timestamp=start_time + timedelta(hours=1), price=dropped_price),
        ]
        
        is_crash = protection.detect_flash_crash(prices)
        
        assert is_crash is False

    def test_crash_detection_window(self):
        """Crash should only consider prices within window."""
        protection = FlashCrashProtection()
        
        start_time = datetime(2023, 1, 1)
        prices = [
            PricePoint(timestamp=start_time, price=50000),  # 3 hours ago
            PricePoint(timestamp=start_time + timedelta(hours=2), price=48000),  # 1 hour ago
            PricePoint(timestamp=start_time + timedelta(hours=3), price=47400),  # Now
        ]
        
        # Within 1 hour window: 48000 -> 47400 = 1.25% drop (no crash)
        is_crash = protection.detect_flash_crash(prices, window_hours=1)
        assert is_crash is False
        
        # Within 3 hour window: 50000 -> 47400 = 5.2% drop (crash)
        is_crash = protection.detect_flash_crash(prices, window_hours=3)
        assert is_crash is True


class TestFlashCrashResponse:
    """Tests for Property 31: Flash Crash Response."""

    def test_emergency_max_trades_during_crash(self):
        """
        **Feature: kinetic-empire, Property 31: Flash Crash Response**
        
        *For any* detected flash crash, max_trades SHALL be reduced to 3 
        AND new BUY signals SHALL be halted.
        **Validates: Requirements 14.1, 14.2**
        """
        protection = FlashCrashProtection()
        
        # Create crash scenario
        start_time = datetime(2023, 1, 1)
        prices = [
            PricePoint(timestamp=start_time, price=50000),
            PricePoint(timestamp=start_time + timedelta(hours=1), price=47000),  # 6% drop
        ]
        
        # Detect crash
        protection.detect_flash_crash(prices)
        
        # Emergency max trades should be 3
        assert protection.get_emergency_max_trades() == 3
        assert protection.is_crash_active() is True

    def test_get_max_trades_returns_emergency_during_crash(self):
        """get_max_trades should return emergency limit during crash."""
        protection = FlashCrashProtection()
        
        start_time = datetime(2023, 1, 1)
        prices = [
            PricePoint(timestamp=start_time, price=50000),
            PricePoint(timestamp=start_time + timedelta(hours=1), price=47000),
        ]
        
        normal_max = 20
        btc_ema50 = 48000
        
        max_trades = protection.get_max_trades(prices, btc_ema50, normal_max)
        
        assert max_trades == 3


class TestMarketStabilityRecovery:
    """Tests for Property 32: Market Stability Recovery."""

    def test_market_stable_after_recovery_period(self):
        """
        **Feature: kinetic-empire, Property 32: Market Stability Recovery**
        
        *For any* state where BTC has been above EMA50 for 4 consecutive hours 
        after a flash crash, normal regime-based limits SHALL be restored.
        **Validates: Requirements 14.3**
        """
        protection = FlashCrashProtection()
        
        start_time = datetime(2023, 1, 1)
        
        # First detect crash
        crash_prices = [
            PricePoint(timestamp=start_time, price=50000),
            PricePoint(timestamp=start_time + timedelta(hours=1), price=47000),
        ]
        protection.detect_flash_crash(crash_prices)
        assert protection.is_crash_active() is True
        
        # Create recovery: 4 hours above EMA50
        recovery_start = start_time + timedelta(hours=2)
        recovery_prices = [
            PricePoint(timestamp=recovery_start + timedelta(hours=i), price=49000)
            for i in range(5)
        ]
        
        btc_ema50 = 48000
        is_stable = protection.is_market_stable(recovery_prices, btc_ema50, recovery_hours=4)
        
        assert is_stable is True
        assert protection.is_crash_active() is False

    def test_not_stable_if_below_ema_in_window(self):
        """Market not stable if any price below EMA in recovery window."""
        protection = FlashCrashProtection()
        
        start_time = datetime(2023, 1, 1)
        
        # Prices with one dip below EMA
        prices = [
            PricePoint(timestamp=start_time, price=49000),
            PricePoint(timestamp=start_time + timedelta(hours=1), price=49000),
            PricePoint(timestamp=start_time + timedelta(hours=2), price=47500),  # Below EMA
            PricePoint(timestamp=start_time + timedelta(hours=3), price=49000),
            PricePoint(timestamp=start_time + timedelta(hours=4), price=49000),
        ]
        
        btc_ema50 = 48000
        is_stable = protection.is_market_stable(prices, btc_ema50, recovery_hours=4)
        
        assert is_stable is False

    def test_insufficient_recovery_time(self):
        """Market not stable if insufficient time above EMA."""
        protection = FlashCrashProtection()
        
        start_time = datetime(2023, 1, 1)
        
        # Only 2 hours above EMA (need 4)
        prices = [
            PricePoint(timestamp=start_time, price=49000),
            PricePoint(timestamp=start_time + timedelta(hours=1), price=49000),
        ]
        
        btc_ema50 = 48000
        is_stable = protection.is_market_stable(prices, btc_ema50, recovery_hours=4)
        
        assert is_stable is False

    def test_normal_max_trades_after_recovery(self):
        """Normal max trades should be restored after recovery."""
        protection = FlashCrashProtection()
        
        start_time = datetime(2023, 1, 1)
        
        # Crash
        crash_prices = [
            PricePoint(timestamp=start_time, price=50000),
            PricePoint(timestamp=start_time + timedelta(hours=1), price=47000),
        ]
        protection.detect_flash_crash(crash_prices)
        
        # Recovery
        recovery_start = start_time + timedelta(hours=2)
        recovery_prices = crash_prices + [
            PricePoint(timestamp=recovery_start + timedelta(hours=i), price=49000)
            for i in range(5)
        ]
        
        btc_ema50 = 48000
        normal_max = 20
        
        max_trades = protection.get_max_trades(recovery_prices, btc_ema50, normal_max)
        
        # Should return normal max after recovery
        assert max_trades == normal_max


class TestProtectionConfig:
    """Tests for custom configuration."""

    def test_custom_crash_threshold(self):
        """Protection should use custom crash threshold."""
        config = ProtectionConfig(crash_threshold_pct=10.0)
        protection = FlashCrashProtection(config)
        
        start_time = datetime(2023, 1, 1)
        
        # 7% drop (below 10% threshold)
        prices = [
            PricePoint(timestamp=start_time, price=50000),
            PricePoint(timestamp=start_time + timedelta(hours=1), price=46500),
        ]
        
        is_crash = protection.detect_flash_crash(prices)
        assert is_crash is False
        
        # 11% drop (above 10% threshold)
        prices[-1] = PricePoint(
            timestamp=start_time + timedelta(hours=1),
            price=44500
        )
        
        is_crash = protection.detect_flash_crash(prices)
        assert is_crash is True

    def test_reset_clears_state(self):
        """Reset should clear crash detection state."""
        protection = FlashCrashProtection()
        
        start_time = datetime(2023, 1, 1)
        prices = [
            PricePoint(timestamp=start_time, price=50000),
            PricePoint(timestamp=start_time + timedelta(hours=1), price=47000),
        ]
        
        protection.detect_flash_crash(prices)
        assert protection.is_crash_active() is True
        
        protection.reset()
        assert protection.is_crash_active() is False
