"""Property-based tests for Cash Cow position sizing.

Uses Hypothesis for property-based testing to verify correctness properties
defined in the design document.
"""

import pytest
from hypothesis import given, strategies as st, settings

from src.kinetic_empire.cash_cow.sizer import ConfidenceBasedSizer, SizingConfig
from src.kinetic_empire.cash_cow.models import MarketRegime


class TestConfidenceMultiplierBounds:
    """Tests for Property 1: Confidence multiplier bounds."""

    # **Feature: cash-cow-upgrade, Property 1: Confidence multiplier bounds**
    # *For any* confidence score, the confidence multiplier returned by the
    # Position Sizer SHALL be one of: 0.0 (rejected), 1.0, 1.5, or 2.0,
    # and SHALL correspond to the correct confidence bracket.
    # **Validates: Requirements 1.1, 1.2, 1.3, 1.4**

    @given(confidence=st.integers(min_value=0, max_value=100))
    @settings(max_examples=100)
    def test_multiplier_is_valid_value(self, confidence: int):
        """Multiplier must be one of the valid values: 0.0, 1.0, 1.5, or 2.0."""
        sizer = ConfidenceBasedSizer()
        multiplier = sizer.get_confidence_multiplier(confidence)
        
        valid_multipliers = {0.0, 1.0, 1.5, 2.0}
        assert multiplier in valid_multipliers, (
            f"Multiplier {multiplier} for confidence {confidence} "
            f"not in valid set {valid_multipliers}"
        )

    @given(confidence=st.integers(min_value=85, max_value=100))
    @settings(max_examples=100)
    def test_high_confidence_gets_2x(self, confidence: int):
        """Confidence >= 85 should get 2.0x multiplier (Requirement 1.1)."""
        sizer = ConfidenceBasedSizer()
        multiplier = sizer.get_confidence_multiplier(confidence)
        assert multiplier == 2.0, (
            f"Confidence {confidence} >= 85 should get 2.0x, got {multiplier}"
        )

    @given(confidence=st.integers(min_value=75, max_value=84))
    @settings(max_examples=100)
    def test_medium_confidence_gets_1_5x(self, confidence: int):
        """Confidence 75-84 should get 1.5x multiplier (Requirement 1.2)."""
        sizer = ConfidenceBasedSizer()
        multiplier = sizer.get_confidence_multiplier(confidence)
        assert multiplier == 1.5, (
            f"Confidence {confidence} in [75,84] should get 1.5x, got {multiplier}"
        )

    @given(confidence=st.integers(min_value=65, max_value=74))
    @settings(max_examples=100)
    def test_low_confidence_gets_1x(self, confidence: int):
        """Confidence 65-74 should get 1.0x multiplier (Requirement 1.3)."""
        sizer = ConfidenceBasedSizer()
        multiplier = sizer.get_confidence_multiplier(confidence)
        assert multiplier == 1.0, (
            f"Confidence {confidence} in [65,74] should get 1.0x, got {multiplier}"
        )

    @given(confidence=st.integers(min_value=0, max_value=64))
    @settings(max_examples=100)
    def test_below_threshold_gets_rejected(self, confidence: int):
        """Confidence < 65 should get 0.0x (rejected) (Requirement 1.4)."""
        sizer = ConfidenceBasedSizer()
        multiplier = sizer.get_confidence_multiplier(confidence)
        assert multiplier == 0.0, (
            f"Confidence {confidence} < 65 should get 0.0x (rejected), got {multiplier}"
        )


class TestPositionSizeCap:
    """Tests for Property 2: Position size cap enforcement."""

    # **Feature: cash-cow-upgrade, Property 2: Position size cap enforcement**
    # *For any* calculated position size and portfolio value, the final
    # position size SHALL NOT exceed 10% of portfolio value.
    # **Validates: Requirements 1.5**

    @given(
        confidence=st.integers(min_value=65, max_value=100),
        portfolio_value=st.floats(min_value=100, max_value=1_000_000, allow_nan=False),
        base_risk_pct=st.floats(min_value=0.1, max_value=20.0, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_position_never_exceeds_10_percent(
        self, confidence: int, portfolio_value: float, base_risk_pct: float
    ):
        """Final position size must never exceed 10% of portfolio value."""
        sizer = ConfidenceBasedSizer()
        result = sizer.calculate_size(
            confidence=confidence,
            regime=MarketRegime.TRENDING,
            consecutive_losses=0,
            portfolio_value=portfolio_value,
            base_risk_pct=base_risk_pct
        )
        
        max_allowed = portfolio_value * 0.10
        assert result.final_size <= max_allowed + 0.01, (  # Small epsilon for float comparison
            f"Position size {result.final_size} exceeds 10% cap {max_allowed} "
            f"for portfolio {portfolio_value}"
        )

    @given(portfolio_value=st.floats(min_value=1000, max_value=1_000_000, allow_nan=False))
    @settings(max_examples=100)
    def test_cap_applied_when_calculation_exceeds_limit(self, portfolio_value: float):
        """When calculated size exceeds cap, final size should equal cap."""
        sizer = ConfidenceBasedSizer()
        # Use high base risk to force cap to be hit
        result = sizer.calculate_size(
            confidence=90,  # 2.0x multiplier
            regime=MarketRegime.TRENDING,  # 1.0x
            consecutive_losses=0,  # 1.0x
            portfolio_value=portfolio_value,
            base_risk_pct=10.0  # 10% base * 2.0x = 20%, should be capped to 10%
        )
        
        expected_cap = portfolio_value * 0.10
        assert abs(result.final_size - expected_cap) < 0.01, (
            f"Expected capped size {expected_cap}, got {result.final_size}"
        )


class TestRejectedTrades:
    """Tests for trade rejection behavior."""

    @given(confidence=st.integers(min_value=0, max_value=64))
    @settings(max_examples=100)
    def test_low_confidence_trades_rejected(self, confidence: int):
        """Trades with confidence < 65 should be rejected with zero size."""
        sizer = ConfidenceBasedSizer()
        result = sizer.calculate_size(
            confidence=confidence,
            regime=MarketRegime.TRENDING,
            consecutive_losses=0,
            portfolio_value=10000
        )
        
        assert result.is_rejected, f"Confidence {confidence} should be rejected"
        assert result.final_size == 0.0, f"Rejected trade should have zero size"
        assert result.rejection_reason is not None, "Rejected trade should have reason"


class TestRegimeMultipliers:
    """Tests for regime multiplier correctness."""

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


class TestLossProtectionMultipliers:
    """Tests for loss protection multiplier correctness."""

    @given(losses=st.integers(min_value=0, max_value=2))
    @settings(max_examples=100)
    def test_no_reduction_for_0_to_2_losses(self, losses: int):
        """0-2 consecutive losses should have 1.0x multiplier."""
        sizer = ConfidenceBasedSizer()
        assert sizer.get_loss_protection_multiplier(losses) == 1.0

    @given(losses=st.integers(min_value=3, max_value=4))
    @settings(max_examples=100)
    def test_half_reduction_for_3_to_4_losses(self, losses: int):
        """3-4 consecutive losses should have 0.5x multiplier."""
        sizer = ConfidenceBasedSizer()
        assert sizer.get_loss_protection_multiplier(losses) == 0.5

    @given(losses=st.integers(min_value=5, max_value=100))
    @settings(max_examples=100)
    def test_quarter_reduction_for_5_plus_losses(self, losses: int):
        """5+ consecutive losses should have 0.25x multiplier."""
        sizer = ConfidenceBasedSizer()
        assert sizer.get_loss_protection_multiplier(losses) == 0.25


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
    def test_minimum_multiplier_selected(self, regimes: list):
        """When multiple regimes apply, minimum multiplier should be used."""
        sizer = ConfidenceBasedSizer()
        
        # Get individual multipliers
        individual_multipliers = [sizer.get_regime_multiplier(r) for r in regimes]
        expected_min = min(individual_multipliers)
        
        # Get combined multiplier
        actual = sizer.get_minimum_regime_multiplier(regimes)
        
        assert actual == expected_min, (
            f"Expected minimum {expected_min} from {individual_multipliers}, got {actual}"
        )

    def test_empty_regimes_returns_1(self):
        """Empty regime list should return 1.0 (no adjustment)."""
        sizer = ConfidenceBasedSizer()
        assert sizer.get_minimum_regime_multiplier([]) == 1.0
