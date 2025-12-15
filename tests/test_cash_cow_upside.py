"""Property-based tests for Upside Analyzer.

Uses Hypothesis for property-based testing to verify correctness properties
defined in the design document.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume

from src.kinetic_empire.cash_cow.upside import UpsideAnalyzer
from src.kinetic_empire.cash_cow.models import UpsideQuality


class TestUpsideDistanceCalculation:
    """Tests for Property 9: Upside distance calculation."""

    # **Feature: cash-cow-upgrade, Property 9: Upside distance calculation**
    # *For any* price and resistance level where resistance > price, the
    # distance to resistance percentage SHALL equal ((resistance - price) / price) * 100.
    # **Validates: Requirements 5.1**

    @given(
        price=st.floats(min_value=1.0, max_value=100000, allow_nan=False),
        resistance_pct=st.floats(min_value=0.1, max_value=50, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_distance_calculation_formula(self, price: float, resistance_pct: float):
        """Distance should equal ((resistance - price) / price) * 100."""
        analyzer = UpsideAnalyzer()
        
        resistance = price * (1 + resistance_pct / 100)
        
        calculated = analyzer.calculate_distance_to_resistance(price, resistance)
        expected = ((resistance - price) / price) * 100
        
        assert abs(calculated - expected) < 0.0001, (
            f"Calculated {calculated} != expected {expected}"
        )

    @given(price=st.floats(min_value=1.0, max_value=100000, allow_nan=False))
    @settings(max_examples=100)
    def test_zero_distance_when_resistance_at_price(self, price: float):
        """Distance should be 0 when resistance equals price."""
        analyzer = UpsideAnalyzer()
        assert analyzer.calculate_distance_to_resistance(price, price) == 0.0

    @given(
        price=st.floats(min_value=1.0, max_value=100000, allow_nan=False),
        resistance=st.floats(min_value=0.1, max_value=0.99, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_zero_distance_when_resistance_below_price(self, price: float, resistance: float):
        """Distance should be 0 when resistance is below price."""
        analyzer = UpsideAnalyzer()
        actual_resistance = price * resistance  # Below price
        assert analyzer.calculate_distance_to_resistance(price, actual_resistance) == 0.0


class TestUpsideScoreAssignment:
    """Tests for Property 10: Upside score assignment."""

    # **Feature: cash-cow-upgrade, Property 10: Upside score assignment**
    # *For any* distance to resistance percentage, the upside score SHALL be:
    # 25 for >5%, 20 for 3-5%, 10 for 1-3%, 0 with -15 penalty for <1%.
    # **Validates: Requirements 5.2, 5.3, 5.4, 5.5**

    @given(distance=st.floats(min_value=5.01, max_value=50, allow_nan=False))
    @settings(max_examples=100)
    def test_excellent_upside_score(self, distance: float):
        """Distance >5% should get 25 points."""
        analyzer = UpsideAnalyzer()
        assert analyzer.get_upside_score(distance) == 25

    @given(distance=st.floats(min_value=3.0, max_value=5.0, allow_nan=False))
    @settings(max_examples=100)
    def test_good_upside_score(self, distance: float):
        """Distance 3-5% should get 20 points."""
        analyzer = UpsideAnalyzer()
        assert analyzer.get_upside_score(distance) == 20

    @given(distance=st.floats(min_value=1.0, max_value=2.99, allow_nan=False))
    @settings(max_examples=100)
    def test_limited_upside_score(self, distance: float):
        """Distance 1-3% should get 10 points."""
        analyzer = UpsideAnalyzer()
        assert analyzer.get_upside_score(distance) == 10

    @given(distance=st.floats(min_value=0.0, max_value=0.99, allow_nan=False))
    @settings(max_examples=100)
    def test_poor_upside_score(self, distance: float):
        """Distance <1% should get 0 points."""
        analyzer = UpsideAnalyzer()
        assert analyzer.get_upside_score(distance) == 0

    @given(distance=st.floats(min_value=0.0, max_value=0.99, allow_nan=False))
    @settings(max_examples=100)
    def test_poor_upside_penalty(self, distance: float):
        """Distance <1% should get 15 point penalty."""
        analyzer = UpsideAnalyzer()
        assert analyzer.get_upside_penalty(distance) == 15

    @given(distance=st.floats(min_value=1.0, max_value=50, allow_nan=False))
    @settings(max_examples=100)
    def test_no_penalty_above_1_percent(self, distance: float):
        """Distance >=1% should have no penalty."""
        analyzer = UpsideAnalyzer()
        assert analyzer.get_upside_penalty(distance) == 0


class TestRiskRewardCalculation:
    """Tests for Property 11: Risk/reward calculation."""

    # **Feature: cash-cow-upgrade, Property 11: Risk/reward calculation**
    # *For any* price, resistance, and support where support < price < resistance,
    # the R/R ratio SHALL equal (resistance - price) / (price - support).
    # **Validates: Requirements 5.6**

    @given(
        price=st.floats(min_value=100, max_value=10000, allow_nan=False),
        support_pct=st.floats(min_value=1, max_value=20, allow_nan=False),
        resistance_pct=st.floats(min_value=1, max_value=30, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_rr_calculation_formula(self, price: float, support_pct: float, resistance_pct: float):
        """R/R should equal (resistance - price) / (price - support)."""
        analyzer = UpsideAnalyzer()
        
        support = price * (1 - support_pct / 100)
        resistance = price * (1 + resistance_pct / 100)
        
        calculated = analyzer.calculate_risk_reward(price, resistance, support)
        expected = (resistance - price) / (price - support)
        
        assert abs(calculated - expected) < 0.0001, (
            f"Calculated R/R {calculated} != expected {expected}"
        )

    @given(price=st.floats(min_value=100, max_value=10000, allow_nan=False))
    @settings(max_examples=100)
    def test_zero_rr_when_invalid_levels(self, price: float):
        """R/R should be 0 when support >= price or resistance <= price."""
        analyzer = UpsideAnalyzer()
        
        # Support at price
        assert analyzer.calculate_risk_reward(price, price * 1.1, price) == 0.0
        # Resistance at price
        assert analyzer.calculate_risk_reward(price, price, price * 0.9) == 0.0


class TestRRBonusAssignment:
    """Tests for Property 12: R/R bonus assignment."""

    # **Feature: cash-cow-upgrade, Property 12: R/R bonus assignment**
    # *For any* R/R ratio, the bonus SHALL be: 5 for >3:1, 3 for >2:1, 0 otherwise.
    # **Validates: Requirements 5.7, 5.8**

    @given(rr=st.floats(min_value=3.01, max_value=20, allow_nan=False))
    @settings(max_examples=100)
    def test_excellent_rr_bonus(self, rr: float):
        """R/R >3:1 should get 5 point bonus."""
        analyzer = UpsideAnalyzer()
        assert analyzer.get_rr_bonus(rr) == 5

    @given(rr=st.floats(min_value=2.01, max_value=3.0, allow_nan=False))
    @settings(max_examples=100)
    def test_good_rr_bonus(self, rr: float):
        """R/R >2:1 (but <=3:1) should get 3 point bonus."""
        analyzer = UpsideAnalyzer()
        assert analyzer.get_rr_bonus(rr) == 3

    @given(rr=st.floats(min_value=0, max_value=2.0, allow_nan=False))
    @settings(max_examples=100)
    def test_no_rr_bonus(self, rr: float):
        """R/R <=2:1 should get no bonus."""
        analyzer = UpsideAnalyzer()
        assert analyzer.get_rr_bonus(rr) == 0


class TestFullAnalysis:
    """Tests for complete upside analysis."""

    @given(
        price=st.floats(min_value=100, max_value=10000, allow_nan=False),
        support_pct=st.floats(min_value=2, max_value=10, allow_nan=False),
        resistance_pct=st.floats(min_value=2, max_value=20, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_analyze_returns_consistent_results(
        self, price: float, support_pct: float, resistance_pct: float
    ):
        """Full analysis should return consistent results."""
        analyzer = UpsideAnalyzer()
        
        support = price * (1 - support_pct / 100)
        resistance = price * (1 + resistance_pct / 100)
        
        result = analyzer.analyze(price, resistance, support)
        
        # Verify consistency
        assert result.distance_to_resistance_pct == analyzer.calculate_distance_to_resistance(price, resistance)
        assert result.risk_reward_ratio == analyzer.calculate_risk_reward(price, resistance, support)
        assert result.upside_score == analyzer.get_upside_score(result.distance_to_resistance_pct)
        assert result.rr_bonus == analyzer.get_rr_bonus(result.risk_reward_ratio)
        assert result.penalty == analyzer.get_upside_penalty(result.distance_to_resistance_pct)
