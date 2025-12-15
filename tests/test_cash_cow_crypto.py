"""Property-based tests for Crypto-Specific Enhancements.

Uses Hypothesis for property-based testing to verify correctness properties
defined in the design document.
"""

import pytest
from hypothesis import given, strategies as st, settings

from src.kinetic_empire.cash_cow.crypto import (
    FundingRateAnalyzer,
    BTCCorrelationAdjuster,
    CorrelationConfig
)


class TestFundingRateBonusCorrectness:
    """Tests for Property 18: Funding rate bonus correctness."""

    # **Feature: cash-cow-upgrade, Property 18: Funding rate bonus correctness**
    # *For any* funding rate and trade direction, the bonus SHALL be:
    # +5 for long when funding < -0.1%, +5 for short when funding > 0.1%, 0 otherwise.
    # **Validates: Requirements 10.1, 10.2**

    @given(funding=st.floats(min_value=-1.0, max_value=-0.11, allow_nan=False))
    @settings(max_examples=100)
    def test_negative_funding_bonus_for_longs(self, funding: float):
        """Funding < -0.1% should give +5 bonus for longs."""
        analyzer = FundingRateAnalyzer()
        assert analyzer.get_funding_bonus(funding, "long") == 5

    @given(funding=st.floats(min_value=-1.0, max_value=-0.11, allow_nan=False))
    @settings(max_examples=100)
    def test_negative_funding_no_bonus_for_shorts(self, funding: float):
        """Funding < -0.1% should give 0 bonus for shorts."""
        analyzer = FundingRateAnalyzer()
        assert analyzer.get_funding_bonus(funding, "short") == 0

    @given(funding=st.floats(min_value=0.11, max_value=1.0, allow_nan=False))
    @settings(max_examples=100)
    def test_positive_funding_bonus_for_shorts(self, funding: float):
        """Funding > 0.1% should give +5 bonus for shorts."""
        analyzer = FundingRateAnalyzer()
        assert analyzer.get_funding_bonus(funding, "short") == 5

    @given(funding=st.floats(min_value=0.11, max_value=1.0, allow_nan=False))
    @settings(max_examples=100)
    def test_positive_funding_no_bonus_for_longs(self, funding: float):
        """Funding > 0.1% should give 0 bonus for longs."""
        analyzer = FundingRateAnalyzer()
        assert analyzer.get_funding_bonus(funding, "long") == 0

    @given(funding=st.floats(min_value=-0.1, max_value=0.1, allow_nan=False))
    @settings(max_examples=100)
    def test_neutral_funding_no_bonus(self, funding: float):
        """Funding between -0.1% and 0.1% should give 0 bonus."""
        analyzer = FundingRateAnalyzer()
        assert analyzer.get_funding_bonus(funding, "long") == 0
        assert analyzer.get_funding_bonus(funding, "short") == 0


class TestBTCCorrelationAdjustment:
    """Tests for Property 19: BTC correlation adjustment."""

    # **Feature: cash-cow-upgrade, Property 19: BTC correlation adjustment**
    # *For any* BTC correlation and volatility, position size SHALL be reduced
    # by 20% when correlation is high AND BTC is volatile.
    # **Validates: Requirements 10.3, 10.4**

    @given(
        correlation=st.floats(min_value=0.7, max_value=1.0, allow_nan=False),
        volatility=st.floats(min_value=3.0, max_value=20.0, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_high_correlation_volatile_btc_reduces_position(self, correlation, volatility):
        """High correlation + volatile BTC should reduce position by 20%."""
        adjuster = BTCCorrelationAdjuster()
        adjustment = adjuster.get_correlation_adjustment(correlation, volatility)
        assert adjustment == 0.8, f"Expected 0.8, got {adjustment}"

    @given(
        correlation=st.floats(min_value=-0.69, max_value=0.69, allow_nan=False),
        volatility=st.floats(min_value=0.1, max_value=20.0, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_low_correlation_allows_full_position(self, correlation, volatility):
        """Low correlation should allow full position sizing."""
        adjuster = BTCCorrelationAdjuster()
        adjustment = adjuster.get_correlation_adjustment(correlation, volatility)
        assert adjustment == 1.0, f"Expected 1.0, got {adjustment}"

    @given(
        correlation=st.floats(min_value=0.7, max_value=1.0, allow_nan=False),
        volatility=st.floats(min_value=0.1, max_value=2.99, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_high_correlation_low_volatility_allows_full_position(self, correlation, volatility):
        """High correlation but low BTC volatility should allow full position."""
        adjuster = BTCCorrelationAdjuster()
        adjustment = adjuster.get_correlation_adjustment(correlation, volatility)
        assert adjustment == 1.0

    @given(
        base_size=st.floats(min_value=100, max_value=10000, allow_nan=False),
        correlation=st.floats(min_value=0.7, max_value=1.0, allow_nan=False),
        volatility=st.floats(min_value=3.0, max_value=20.0, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_adjusted_size_is_80_percent(self, base_size, correlation, volatility):
        """Adjusted size should be 80% of base when conditions met."""
        adjuster = BTCCorrelationAdjuster()
        adjusted = adjuster.calculate_adjusted_size(base_size, correlation, volatility)
        expected = base_size * 0.8
        assert abs(adjusted - expected) < 0.01


class TestNegativeCorrelation:
    """Tests for negative BTC correlation handling."""

    @given(
        correlation=st.floats(min_value=-1.0, max_value=-0.7, allow_nan=False),
        volatility=st.floats(min_value=3.0, max_value=20.0, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_high_negative_correlation_also_reduces(self, correlation, volatility):
        """High negative correlation + volatile BTC should also reduce position."""
        adjuster = BTCCorrelationAdjuster()
        adjustment = adjuster.get_correlation_adjustment(correlation, volatility)
        # abs(correlation) >= 0.7, so should reduce
        assert adjustment == 0.8


class TestCustomCorrelationConfig:
    """Tests for custom correlation configuration."""

    @given(
        threshold=st.floats(min_value=0.5, max_value=0.9, allow_nan=False),
        reduction=st.floats(min_value=10, max_value=50, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_custom_config_respected(self, threshold, reduction):
        """Custom configuration should be respected."""
        config = CorrelationConfig(
            high_correlation_threshold=threshold,
            position_reduction_pct=reduction
        )
        adjuster = BTCCorrelationAdjuster(config)
        
        # Test with correlation above threshold and high volatility
        adjustment = adjuster.get_correlation_adjustment(threshold + 0.05, 5.0)
        expected = 1.0 - (reduction / 100)
        
        assert abs(adjustment - expected) < 0.001


class TestFundingFavorability:
    """Tests for funding favorability check."""

    def test_favorable_for_long_with_negative_funding(self):
        """Negative funding should be favorable for longs."""
        analyzer = FundingRateAnalyzer()
        assert analyzer.is_funding_favorable(-0.15, "long") is True
        assert analyzer.is_funding_favorable(-0.15, "short") is False

    def test_favorable_for_short_with_positive_funding(self):
        """Positive funding should be favorable for shorts."""
        analyzer = FundingRateAnalyzer()
        assert analyzer.is_funding_favorable(0.15, "short") is True
        assert analyzer.is_funding_favorable(0.15, "long") is False
