"""Property-based tests for Regime Multipliers and Stop Distance Enforcement.

Uses Hypothesis for property-based testing to verify correctness properties
defined in the design document.
"""

import pytest
from hypothesis import given, strategies as st, settings

from src.kinetic_empire.cash_cow.sizer import ConfidenceBasedSizer
from src.kinetic_empire.cash_cow.stop_enforcer import StopDistanceEnforcer, StopEnforcerConfig
from src.kinetic_empire.cash_cow.models import MarketRegime


class TestRegimeMultiplierCorrectness:
    """Tests for Property 13: Regime multiplier correctness."""

    # **Feature: cash-cow-upgrade, Property 13: Regime multiplier correctness**
    # *For any* market regime, the regime multiplier SHALL be:
    # 1.0 for trending, 0.5 for bear, 0.75 for choppy, 0.85 for high volatility.
    # **Validates: Requirements 6.1, 6.2, 6.3, 6.4**

    def test_trending_regime_multiplier(self):
        """Trending regime should have 1.0x multiplier."""
        sizer = ConfidenceBasedSizer()
        assert sizer.get_regime_multiplier(MarketRegime.TRENDING) == 1.0

    def test_bear_regime_multiplier(self):
        """Bear regime should have 0.5x multiplier."""
        sizer = ConfidenceBasedSizer()
        assert sizer.get_regime_multiplier(MarketRegime.BEAR) == 0.5

    def test_choppy_regime_multiplier(self):
        """Choppy regime should have 0.75x multiplier."""
        sizer = ConfidenceBasedSizer()
        assert sizer.get_regime_multiplier(MarketRegime.CHOPPY) == 0.75

    def test_high_volatility_regime_multiplier(self):
        """High volatility regime should have 0.85x multiplier."""
        sizer = ConfidenceBasedSizer()
        assert sizer.get_regime_multiplier(MarketRegime.HIGH_VOLATILITY) == 0.85

    @given(regime=st.sampled_from(list(MarketRegime)))
    @settings(max_examples=100)
    def test_all_regimes_have_valid_multipliers(self, regime):
        """All regimes should have multipliers in valid range."""
        sizer = ConfidenceBasedSizer()
        mult = sizer.get_regime_multiplier(regime)
        assert 0 < mult <= 1.0, f"Regime {regime} has invalid multiplier {mult}"


class TestConservativeMultiplierSelection:
    """Tests for Property 14: Conservative multiplier selection."""

    # **Feature: cash-cow-upgrade, Property 14: Conservative multiplier selection**
    # *For any* combination of regime conditions, the final regime multiplier
    # SHALL be the minimum of all applicable multipliers.
    # **Validates: Requirements 6.5**

    @given(
        regimes=st.lists(
            st.sampled_from(list(MarketRegime)),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=100)
    def test_minimum_multiplier_selected(self, regimes):
        """When multiple regimes apply, minimum multiplier should be used."""
        sizer = ConfidenceBasedSizer()
        
        individual = [sizer.get_regime_multiplier(r) for r in regimes]
        expected = min(individual)
        actual = sizer.get_minimum_regime_multiplier(regimes)
        
        assert actual == expected

    def test_bear_and_choppy_uses_bear(self):
        """Bear (0.5) and Choppy (0.75) should use Bear's 0.5."""
        sizer = ConfidenceBasedSizer()
        regimes = [MarketRegime.BEAR, MarketRegime.CHOPPY]
        assert sizer.get_minimum_regime_multiplier(regimes) == 0.5

    def test_all_regimes_uses_bear(self):
        """All regimes combined should use Bear's 0.5 (minimum)."""
        sizer = ConfidenceBasedSizer()
        regimes = list(MarketRegime)
        assert sizer.get_minimum_regime_multiplier(regimes) == 0.5


class TestMinimumStopDistanceEnforcement:
    """Tests for Property 15: Minimum stop distance enforcement."""

    # **Feature: cash-cow-upgrade, Property 15: Minimum stop distance enforcement**
    # *For any* calculated stop loss, the stop distance SHALL be at least
    # 1.5% from entry price.
    # **Validates: Requirements 7.1, 7.2, 7.3**

    @given(
        entry_price=st.floats(min_value=10, max_value=100000, allow_nan=False),
        stop_distance_pct=st.floats(min_value=0.1, max_value=1.4, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_enforces_minimum_for_close_stops_long(self, entry_price, stop_distance_pct):
        """Stops closer than 1.5% should be moved to 1.5% for longs."""
        enforcer = StopDistanceEnforcer()
        
        # Calculate a stop that's too close
        close_stop = entry_price * (1 - stop_distance_pct / 100)
        
        enforced_stop = enforcer.enforce_minimum_stop(entry_price, close_stop, "long")
        
        # Enforced stop should be at least 1.5% away
        distance = enforcer.calculate_stop_distance_pct(entry_price, enforced_stop)
        assert distance >= 1.5 - 0.001, f"Stop distance {distance}% < 1.5%"

    @given(
        entry_price=st.floats(min_value=10, max_value=100000, allow_nan=False),
        stop_distance_pct=st.floats(min_value=0.1, max_value=1.4, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_enforces_minimum_for_close_stops_short(self, entry_price, stop_distance_pct):
        """Stops closer than 1.5% should be moved to 1.5% for shorts."""
        enforcer = StopDistanceEnforcer()
        
        # Calculate a stop that's too close (above entry for shorts)
        close_stop = entry_price * (1 + stop_distance_pct / 100)
        
        enforced_stop = enforcer.enforce_minimum_stop(entry_price, close_stop, "short")
        
        # Enforced stop should be at least 1.5% away
        distance = enforcer.calculate_stop_distance_pct(entry_price, enforced_stop)
        assert distance >= 1.5 - 0.001, f"Stop distance {distance}% < 1.5%"

    @given(
        entry_price=st.floats(min_value=10, max_value=100000, allow_nan=False),
        stop_distance_pct=st.floats(min_value=2.0, max_value=10.0, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_preserves_wider_stops_long(self, entry_price, stop_distance_pct):
        """Stops wider than 1.5% should be preserved for longs."""
        enforcer = StopDistanceEnforcer()
        
        # Calculate a stop that's already wide enough
        wide_stop = entry_price * (1 - stop_distance_pct / 100)
        
        enforced_stop = enforcer.enforce_minimum_stop(entry_price, wide_stop, "long")
        
        # Should preserve the original wider stop
        assert abs(enforced_stop - wide_stop) < 0.01

    @given(
        entry_price=st.floats(min_value=10, max_value=100000, allow_nan=False),
        stop_distance_pct=st.floats(min_value=0.1, max_value=1.4, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_validation_rejects_close_stops(self, entry_price, stop_distance_pct):
        """Validation should reject stops closer than 1.5%."""
        enforcer = StopDistanceEnforcer()
        
        close_stop = entry_price * (1 - stop_distance_pct / 100)
        
        is_valid, reason = enforcer.validate_stop_distance(entry_price, close_stop)
        
        assert not is_valid
        assert reason is not None
        assert "below minimum" in reason

    @given(
        entry_price=st.floats(min_value=10, max_value=100000, allow_nan=False),
        stop_distance_pct=st.floats(min_value=1.51, max_value=10.0, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_validation_accepts_valid_stops(self, entry_price, stop_distance_pct):
        """Validation should accept stops beyond 1.5%."""
        enforcer = StopDistanceEnforcer()
        
        valid_stop = entry_price * (1 - stop_distance_pct / 100)
        
        is_valid, reason = enforcer.validate_stop_distance(entry_price, valid_stop)
        
        assert is_valid
        assert reason is None


class TestCustomMinimumStop:
    """Tests for custom minimum stop configuration."""

    @given(
        min_pct=st.floats(min_value=0.5, max_value=5.0, allow_nan=False),
        entry_price=st.floats(min_value=100, max_value=10000, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_custom_minimum_respected(self, min_pct, entry_price):
        """Custom minimum stop percentage should be respected."""
        config = StopEnforcerConfig(minimum_stop_pct=min_pct)
        enforcer = StopDistanceEnforcer(config)
        
        # Try a stop that's too close
        close_stop = entry_price * 0.999  # 0.1% away
        
        enforced = enforcer.enforce_minimum_stop(entry_price, close_stop, "long")
        distance = enforcer.calculate_stop_distance_pct(entry_price, enforced)
        
        assert distance >= min_pct - 0.001
