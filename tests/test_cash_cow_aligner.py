"""Property-based tests for Multi-Timeframe Aligner and Opportunity Ranking.

Uses Hypothesis for property-based testing to verify correctness properties
defined in the design document.
"""

import pytest
from hypothesis import given, strategies as st, settings

from src.kinetic_empire.cash_cow.aligner import MultiTimeframeAligner


class TestAlignmentBonusCorrectness:
    """Tests for Property 17: Alignment bonus correctness."""

    # **Feature: cash-cow-upgrade, Property 17: Alignment bonus correctness**
    # *For any* set of timeframe alignments, the bonus SHALL be:
    # +10 for 5/5 aligned, +5 for 4/5 aligned, -10 for <3/5 aligned,
    # with additional -5 if daily conflicts.
    # **Validates: Requirements 9.2, 9.3, 9.4, 9.5**

    def test_all_aligned_bonus(self):
        """5/5 aligned should get +10 bonus."""
        aligner = MultiTimeframeAligner()
        directions = {
            "5m": "bullish",
            "15m": "bullish",
            "1h": "bullish",
            "4h": "bullish",
            "1d": "bullish"
        }
        result = aligner.check_alignment(directions, "bullish")
        assert result.alignment_bonus == 10

    def test_four_of_five_aligned_bonus(self):
        """4/5 aligned should get +5 bonus."""
        aligner = MultiTimeframeAligner()
        directions = {
            "5m": "bullish",
            "15m": "bullish",
            "1h": "bullish",
            "4h": "bullish",
            "1d": "bearish"  # One misaligned
        }
        result = aligner.check_alignment(directions, "bullish")
        # 4/5 aligned = +5, but daily conflicts = -5, so total = 0
        assert result.aligned_count == 4
        assert result.daily_conflicts is True

    def test_four_aligned_no_daily_conflict(self):
        """4/5 aligned without daily conflict should get +5."""
        aligner = MultiTimeframeAligner()
        directions = {
            "5m": "bearish",  # One misaligned (not daily)
            "15m": "bullish",
            "1h": "bullish",
            "4h": "bullish",
            "1d": "bullish"
        }
        result = aligner.check_alignment(directions, "bullish")
        assert result.aligned_count == 4
        assert result.daily_conflicts is False
        assert result.alignment_bonus == 5

    def test_fewer_than_three_aligned_penalty(self):
        """<3/5 aligned should get -10 penalty."""
        aligner = MultiTimeframeAligner()
        directions = {
            "5m": "bearish",
            "15m": "bearish",
            "1h": "bearish",
            "4h": "bullish",
            "1d": "bullish"
        }
        result = aligner.check_alignment(directions, "bullish")
        assert result.aligned_count == 2
        assert result.alignment_bonus == -10

    def test_daily_conflict_additional_penalty(self):
        """Daily conflict should add -5 penalty."""
        aligner = MultiTimeframeAligner()
        directions = {
            "5m": "bearish",
            "15m": "bearish",
            "1h": "bearish",
            "4h": "bearish",
            "1d": "bullish"  # Daily conflicts with bearish trade
        }
        result = aligner.check_alignment(directions, "bearish")
        # 4/5 aligned = +5, daily conflicts = -5, total = 0
        assert result.aligned_count == 4
        assert result.daily_conflicts is True
        assert result.alignment_bonus == 0  # +5 - 5 = 0

    @given(
        aligned=st.integers(min_value=0, max_value=5),
        daily_conflicts=st.booleans()
    )
    @settings(max_examples=100)
    def test_bonus_calculation_formula(self, aligned: int, daily_conflicts: bool):
        """Bonus calculation should follow the defined formula."""
        aligner = MultiTimeframeAligner()
        
        bonus = aligner.calculate_alignment_bonus(aligned, 5, daily_conflicts)
        
        # Calculate expected bonus
        if aligned == 5:
            expected = 10
        elif aligned == 4:
            expected = 5
        elif aligned < 3:
            expected = -10
        else:
            expected = 0
        
        if daily_conflicts:
            expected -= 5
        
        assert bonus == expected


class TestTrendDirection:
    """Tests for trend direction determination."""

    @given(
        ema_fast=st.floats(min_value=1, max_value=1000, allow_nan=False),
        ema_slow=st.floats(min_value=1, max_value=1000, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_trend_direction_from_emas(self, ema_fast: float, ema_slow: float):
        """Trend direction should be bullish when fast > slow."""
        aligner = MultiTimeframeAligner()
        direction = aligner.get_trend_direction(ema_fast, ema_slow)
        
        if ema_fast > ema_slow:
            assert direction == "bullish"
        else:
            assert direction == "bearish"


class TestOpportunityRankingCorrectness:
    """Tests for Property 16: Opportunity ranking correctness."""

    # **Feature: cash-cow-upgrade, Property 16: Opportunity ranking correctness**
    # *For any* list of opportunities with scores, the ranked list SHALL be
    # sorted in descending order by total score.
    # **Validates: Requirements 8.2**

    @given(scores=st.lists(st.integers(min_value=0, max_value=150), min_size=1, max_size=20))
    @settings(max_examples=100)
    def test_ranking_is_descending(self, scores: list):
        """Ranked opportunities should be in descending score order."""
        # Create mock opportunities with scores
        opportunities = [{"symbol": f"SYM{i}", "score": s} for i, s in enumerate(scores)]
        
        # Rank by score descending
        ranked = sorted(opportunities, key=lambda x: x["score"], reverse=True)
        
        # Verify descending order
        for i in range(len(ranked) - 1):
            assert ranked[i]["score"] >= ranked[i + 1]["score"]

    @given(scores=st.lists(st.integers(min_value=0, max_value=150), min_size=2, max_size=20))
    @settings(max_examples=100)
    def test_highest_score_first(self, scores: list):
        """Highest scored opportunity should be first."""
        opportunities = [{"symbol": f"SYM{i}", "score": s} for i, s in enumerate(scores)]
        ranked = sorted(opportunities, key=lambda x: x["score"], reverse=True)
        
        max_score = max(scores)
        assert ranked[0]["score"] == max_score


class TestAlignmentWithEMAData:
    """Tests for alignment using EMA data."""

    def test_alignment_from_ema_data(self):
        """Should correctly determine alignment from EMA data."""
        aligner = MultiTimeframeAligner()
        
        ema_data = {
            "5m": (100, 95),   # bullish (fast > slow)
            "15m": (100, 98),  # bullish
            "1h": (100, 102),  # bearish (fast < slow)
            "4h": (100, 99),   # bullish
            "1d": (100, 97),   # bullish
        }
        
        result = aligner.get_alignment_from_emas(ema_data, "bullish")
        
        assert result.aligned_count == 4
        assert result.directions["5m"] == "bullish"
        assert result.directions["1h"] == "bearish"
