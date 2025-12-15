"""Property-based tests for Opportunity Scorer.

Uses Hypothesis for property-based testing to verify correctness properties
defined in the design document.
"""

import pytest
from hypothesis import given, strategies as st, settings

from src.kinetic_empire.cash_cow.scorer import OpportunityScorer, ScoringFeatures
from src.kinetic_empire.cash_cow.models import MarketRegime


class TestComponentScoreBounds:
    """Tests for Property 7: Component score bounds."""

    # **Feature: cash-cow-upgrade, Property 7: Component score bounds**
    # *For any* set of trading features, each component score SHALL be within
    # its defined bounds: technical (0-40), momentum (0-25), volume (0-20),
    # volatility (0-15), regime (0-10), sentiment (0-10), growth (0-10).
    # **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7**

    @given(
        ema_diff=st.floats(min_value=-10, max_value=10, allow_nan=False),
        rsi=st.floats(min_value=0, max_value=100, allow_nan=False),
        macd=st.floats(min_value=-1, max_value=1, allow_nan=False),
        vwap_dist=st.floats(min_value=-10, max_value=10, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_technical_score_bounds(self, ema_diff, rsi, macd, vwap_dist):
        """Technical score must be in [0, 40]."""
        scorer = OpportunityScorer()
        features = ScoringFeatures(
            ema_diff_pct=ema_diff,
            rsi=rsi,
            macd_histogram=macd,
            vwap_distance_pct=vwap_dist
        )
        score = scorer.score_technical(features)
        assert 0 <= score <= 40, f"Technical score {score} out of bounds [0, 40]"

    @given(
        adx=st.floats(min_value=0, max_value=100, allow_nan=False),
        plus_di=st.floats(min_value=0, max_value=100, allow_nan=False),
        minus_di=st.floats(min_value=0, max_value=100, allow_nan=False),
        momentum=st.floats(min_value=-20, max_value=20, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_momentum_score_bounds(self, adx, plus_di, minus_di, momentum):
        """Momentum score must be in [0, 25]."""
        scorer = OpportunityScorer()
        features = ScoringFeatures(
            adx=adx,
            plus_di=plus_di,
            minus_di=minus_di,
            price_momentum=momentum
        )
        score = scorer.score_momentum(features)
        assert 0 <= score <= 25, f"Momentum score {score} out of bounds [0, 25]"

    @given(
        volume_ratio=st.floats(min_value=0, max_value=10, allow_nan=False),
        obv_trend=st.sampled_from([-1, 0, 1]),
        volume_surge=st.booleans()
    )
    @settings(max_examples=100)
    def test_volume_score_bounds(self, volume_ratio, obv_trend, volume_surge):
        """Volume score must be in [0, 20]."""
        scorer = OpportunityScorer()
        features = ScoringFeatures(
            volume_ratio=volume_ratio,
            obv_trend=obv_trend,
            volume_surge=volume_surge
        )
        score = scorer.score_volume(features)
        assert 0 <= score <= 20, f"Volume score {score} out of bounds [0, 20]"

    @given(atr_pct=st.floats(min_value=0, max_value=30, allow_nan=False))
    @settings(max_examples=100)
    def test_volatility_score_bounds(self, atr_pct):
        """Volatility score must be in [0, 15]."""
        scorer = OpportunityScorer()
        features = ScoringFeatures(atr_pct=atr_pct)
        score = scorer.score_volatility(features)
        assert 0 <= score <= 15, f"Volatility score {score} out of bounds [0, 15]"

    @given(regime=st.sampled_from(list(MarketRegime)))
    @settings(max_examples=100)
    def test_regime_score_bounds(self, regime):
        """Regime score must be in [0, 10]."""
        scorer = OpportunityScorer()
        score = scorer.score_regime(regime)
        assert 0 <= score <= 10, f"Regime score {score} out of bounds [0, 10]"

    @given(fear_greed=st.integers(min_value=0, max_value=100))
    @settings(max_examples=100)
    def test_sentiment_score_bounds(self, fear_greed):
        """Sentiment score must be in [0, 10]."""
        scorer = OpportunityScorer()
        score = scorer.score_sentiment(fear_greed)
        assert 0 <= score <= 10, f"Sentiment score {score} out of bounds [0, 10]"

    @given(
        atr_pct=st.floats(min_value=0, max_value=20, allow_nan=False),
        momentum_strength=st.floats(min_value=0, max_value=10, allow_nan=False),
        volume_surge=st.booleans()
    )
    @settings(max_examples=100)
    def test_growth_score_bounds(self, atr_pct, momentum_strength, volume_surge):
        """Growth score must be in [0, 10]."""
        scorer = OpportunityScorer()
        features = ScoringFeatures(
            atr_pct=atr_pct,
            momentum_strength=momentum_strength,
            volume_surge=volume_surge
        )
        score = scorer.score_growth_potential(features)
        assert 0 <= score <= 10, f"Growth score {score} out of bounds [0, 10]"


class TestTotalScoreSummation:
    """Tests for Property 8: Total score summation."""

    # **Feature: cash-cow-upgrade, Property 8: Total score summation**
    # *For any* opportunity score, the total score SHALL equal the sum of
    # all component scores plus bonuses minus penalties.
    # **Validates: Requirements 4.8**

    @given(
        ema_diff=st.floats(min_value=-5, max_value=5, allow_nan=False),
        rsi=st.floats(min_value=0, max_value=100, allow_nan=False),
        macd=st.floats(min_value=-0.5, max_value=0.5, allow_nan=False),
        vwap_dist=st.floats(min_value=-5, max_value=5, allow_nan=False),
        adx=st.floats(min_value=0, max_value=100, allow_nan=False),
        plus_di=st.floats(min_value=0, max_value=50, allow_nan=False),
        minus_di=st.floats(min_value=0, max_value=50, allow_nan=False),
        momentum=st.floats(min_value=-10, max_value=10, allow_nan=False),
        volume_ratio=st.floats(min_value=0.5, max_value=5, allow_nan=False),
        obv_trend=st.sampled_from([-1, 0, 1]),
        atr_pct=st.floats(min_value=0.5, max_value=15, allow_nan=False),
        regime=st.sampled_from(list(MarketRegime)),
        fear_greed=st.integers(min_value=0, max_value=100),
        momentum_strength=st.floats(min_value=0, max_value=10, allow_nan=False),
        volume_surge=st.booleans()
    )
    @settings(max_examples=100)
    def test_total_equals_sum_of_components(
        self, ema_diff, rsi, macd, vwap_dist, adx, plus_di, minus_di,
        momentum, volume_ratio, obv_trend, atr_pct, regime, fear_greed,
        momentum_strength, volume_surge
    ):
        """Total score must equal sum of all component scores."""
        scorer = OpportunityScorer()
        features = ScoringFeatures(
            ema_diff_pct=ema_diff,
            rsi=rsi,
            macd_histogram=macd,
            vwap_distance_pct=vwap_dist,
            adx=adx,
            plus_di=plus_di,
            minus_di=minus_di,
            price_momentum=momentum,
            volume_ratio=volume_ratio,
            obv_trend=obv_trend,
            atr_pct=atr_pct,
            regime=regime,
            fear_greed_index=fear_greed,
            momentum_strength=momentum_strength,
            volume_surge=volume_surge
        )
        
        result = scorer.calculate_total(features)
        
        expected_total = (
            result.technical_score +
            result.momentum_score +
            result.volume_score +
            result.volatility_score +
            result.regime_score +
            result.sentiment_score +
            result.growth_score +
            result.upside_score +
            result.alignment_bonus +
            result.rr_bonus
        )
        
        assert result.total_score == expected_total, (
            f"Total {result.total_score} != sum {expected_total}"
        )


class TestTotalScoreBounds:
    """Tests for total score being within reasonable bounds."""

    @given(
        ema_diff=st.floats(min_value=-5, max_value=5, allow_nan=False),
        rsi=st.floats(min_value=0, max_value=100, allow_nan=False),
        adx=st.floats(min_value=0, max_value=100, allow_nan=False),
        volume_ratio=st.floats(min_value=0.5, max_value=5, allow_nan=False),
        atr_pct=st.floats(min_value=0.5, max_value=15, allow_nan=False),
        regime=st.sampled_from(list(MarketRegime)),
        fear_greed=st.integers(min_value=0, max_value=100)
    )
    @settings(max_examples=100)
    def test_total_score_reasonable_bounds(
        self, ema_diff, rsi, adx, volume_ratio, atr_pct, regime, fear_greed
    ):
        """Total score should be within reasonable bounds (0-130 base)."""
        scorer = OpportunityScorer()
        features = ScoringFeatures(
            ema_diff_pct=ema_diff,
            rsi=rsi,
            adx=adx,
            volume_ratio=volume_ratio,
            atr_pct=atr_pct,
            regime=regime,
            fear_greed_index=fear_greed
        )
        
        result = scorer.calculate_total(features)
        
        # Base max is 130 (40+25+20+15+10+10+10)
        # With bonuses could go higher, with penalties could go negative
        assert result.total_score >= -15, f"Total score {result.total_score} too low"
        assert result.total_score <= 170, f"Total score {result.total_score} too high"
