"""Property-based tests for RiskAdjuster.

**Feature: signal-quality-fix, Property 4: Regime-Based Stop Loss**
**Feature: signal-quality-fix, Property 6: Leverage Capping**
**Validates: Requirements 4.1, 4.2, 4.3, 6.1, 6.2, 6.3**
"""

import pytest
from hypothesis import given, strategies as st

from src.kinetic_empire.signal_quality.config import QualityGateConfig
from src.kinetic_empire.signal_quality.risk_adjuster import RiskAdjuster, MarketRegime


class TestRiskAdjusterStopLossProperties:
    """Property-based tests for regime-based stop loss."""
    
    def test_choppy_regime_5_percent_stop(self):
        """Property: CHOPPY regime SHALL use 5% stop loss.
        
        **Feature: signal-quality-fix, Property 4: Regime-Based Stop Loss**
        **Validates: Requirements 4.1**
        """
        adjuster = RiskAdjuster(QualityGateConfig())
        stop_pct = adjuster.calculate_stop_loss(MarketRegime.CHOPPY)
        assert stop_pct == 5.0
    
    def test_sideways_regime_4_percent_stop(self):
        """Property: SIDEWAYS regime SHALL use 4% stop loss.
        
        **Feature: signal-quality-fix, Property 4: Regime-Based Stop Loss**
        **Validates: Requirements 4.2**
        """
        adjuster = RiskAdjuster(QualityGateConfig())
        stop_pct = adjuster.calculate_stop_loss(MarketRegime.SIDEWAYS)
        assert stop_pct == 4.0
    
    def test_trending_regime_3_percent_stop(self):
        """Property: TRENDING regime SHALL use 3% stop loss.
        
        **Feature: signal-quality-fix, Property 4: Regime-Based Stop Loss**
        **Validates: Requirements 4.3**
        """
        adjuster = RiskAdjuster(QualityGateConfig())
        stop_pct = adjuster.calculate_stop_loss(MarketRegime.TRENDING)
        assert stop_pct == 3.0
    
    @given(regime=st.sampled_from([MarketRegime.HIGH_VOLATILITY, MarketRegime.LOW_VOLATILITY]))
    def test_other_regimes_use_trending_stop(self, regime: MarketRegime):
        """Other regimes should use trending (3%) stop loss."""
        adjuster = RiskAdjuster(QualityGateConfig())
        stop_pct = adjuster.calculate_stop_loss(regime)
        assert stop_pct == 3.0


class TestRiskAdjusterLeverageProperties:
    """Property-based tests for leverage capping."""
    
    @given(
        regime=st.sampled_from([MarketRegime.CHOPPY, MarketRegime.SIDEWAYS]),
        confidence=st.integers(min_value=0, max_value=100)
    )
    def test_unfavorable_regime_caps_at_10x(self, regime: MarketRegime, confidence: int):
        """Property: CHOPPY or SIDEWAYS regime SHALL cap leverage at 10x.
        
        **Feature: signal-quality-fix, Property 6: Leverage Capping**
        **Validates: Requirements 6.1**
        """
        adjuster = RiskAdjuster(QualityGateConfig())
        max_lev = adjuster.calculate_max_leverage(regime, confidence)
        assert max_lev <= 10
    
    @given(
        regime=st.sampled_from(list(MarketRegime)),
        confidence=st.integers(min_value=0, max_value=59)
    )
    def test_low_confidence_caps_at_10x(self, regime: MarketRegime, confidence: int):
        """Property: Confidence < 60 SHALL cap leverage at 10x.
        
        **Feature: signal-quality-fix, Property 6: Leverage Capping**
        **Validates: Requirements 6.2**
        """
        adjuster = RiskAdjuster(QualityGateConfig())
        max_lev = adjuster.calculate_max_leverage(regime, confidence)
        assert max_lev <= 10
    
    @given(confidence=st.integers(min_value=70, max_value=100))
    def test_favorable_conditions_allow_20x(self, confidence: int):
        """Property: TRENDING + confidence >= 70 SHALL allow up to 20x.
        
        **Feature: signal-quality-fix, Property 6: Leverage Capping**
        **Validates: Requirements 6.3**
        """
        adjuster = RiskAdjuster(QualityGateConfig())
        max_lev = adjuster.calculate_max_leverage(MarketRegime.TRENDING, confidence)
        assert max_lev <= 20
        assert max_lev == 20  # Should be exactly 20 for favorable


class TestRiskAdjusterEdgeCases:
    """Edge case tests for risk adjuster."""
    
    def test_confidence_59_caps_at_10x(self):
        """Confidence at 59 should cap at 10x."""
        adjuster = RiskAdjuster(QualityGateConfig())
        max_lev = adjuster.calculate_max_leverage(MarketRegime.TRENDING, 59)
        assert max_lev == 10
    
    def test_confidence_60_still_needs_trending(self):
        """Confidence at 60 without TRENDING should cap at 10x."""
        adjuster = RiskAdjuster(QualityGateConfig())
        max_lev = adjuster.calculate_max_leverage(MarketRegime.SIDEWAYS, 60)
        assert max_lev == 10
    
    def test_confidence_70_with_trending_allows_20x(self):
        """Confidence at 70 with TRENDING should allow 20x."""
        adjuster = RiskAdjuster(QualityGateConfig())
        max_lev = adjuster.calculate_max_leverage(MarketRegime.TRENDING, 70)
        assert max_lev == 20
    
    def test_is_favorable_true(self):
        """is_favorable should return True for TRENDING + high confidence."""
        adjuster = RiskAdjuster(QualityGateConfig())
        assert adjuster.is_favorable(MarketRegime.TRENDING, 70) is True
        assert adjuster.is_favorable(MarketRegime.TRENDING, 80) is True
    
    def test_is_favorable_false(self):
        """is_favorable should return False for unfavorable conditions."""
        adjuster = RiskAdjuster(QualityGateConfig())
        assert adjuster.is_favorable(MarketRegime.CHOPPY, 80) is False
        assert adjuster.is_favorable(MarketRegime.TRENDING, 60) is False
        assert adjuster.is_favorable(MarketRegime.SIDEWAYS, 70) is False
