"""Tests for Wave Rider Position Sizer.

Includes property-based tests for:
- Property 8: Position Size and Leverage Tiers
- Property 9: Alignment Leverage Bonus
- Property 10: Loss Protection Size Reduction
"""

import pytest
from hypothesis import given, strategies as st, settings

from src.kinetic_empire.wave_rider.position_sizer import WaveRiderPositionSizer, PositionSizeResult
from src.kinetic_empire.wave_rider.models import WaveRiderConfig


class TestWaveRiderPositionSizer:
    """Unit tests for WaveRiderPositionSizer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.sizer = WaveRiderPositionSizer()
    
    def test_tier1_params(self):
        """Test tier 1 parameters (2.0-3.0)."""
        result = self.sizer.calculate(
            volume_ratio=2.5,
            alignment_score=70,
            consecutive_losses=0,
            available_capital=10000,
            current_exposure=0.0,
        )
        assert result.size_pct == 0.05
        assert result.leverage == 3
        assert result.tier == "tier1"
        assert result.size_usd == 500
    
    def test_tier2_params(self):
        """Test tier 2 parameters (3.0-5.0)."""
        result = self.sizer.calculate(
            volume_ratio=4.0,
            alignment_score=70,
            consecutive_losses=0,
            available_capital=10000,
            current_exposure=0.0,
        )
        assert result.size_pct == pytest.approx(0.07)
        assert result.leverage == 5
        assert result.tier == "tier2"
        assert result.size_usd == pytest.approx(700)
    
    def test_tier3_params(self):
        """Test tier 3 parameters (5.0+)."""
        result = self.sizer.calculate(
            volume_ratio=6.0,
            alignment_score=70,
            consecutive_losses=0,
            available_capital=10000,
            current_exposure=0.0,
        )
        assert result.size_pct == 0.10
        assert result.leverage == 7
        assert result.tier == "tier3"
        assert result.size_usd == 1000
    
    def test_alignment_bonus_adds_leverage(self):
        """Test alignment score 100 adds 1x leverage."""
        result = self.sizer.calculate(
            volume_ratio=2.5,
            alignment_score=100,  # Perfect alignment
            consecutive_losses=0,
            available_capital=10000,
            current_exposure=0.0,
        )
        # Base leverage 3 + 1 bonus = 4
        assert result.leverage == 4
    
    def test_alignment_bonus_capped_at_10x(self):
        """Test leverage is capped at 10x with alignment bonus."""
        result = self.sizer.calculate(
            volume_ratio=10.0,  # Tier 3 = 7x base
            alignment_score=100,  # +1 bonus
            consecutive_losses=0,
            available_capital=10000,
            current_exposure=0.0,
        )
        # 7 + 1 = 8, which is under cap
        assert result.leverage == 8
    
    def test_loss_protection_reduces_size(self):
        """Test consecutive losses reduce position size by 50%."""
        result = self.sizer.calculate(
            volume_ratio=2.5,
            alignment_score=70,
            consecutive_losses=3,  # > 2 threshold
            available_capital=10000,
            current_exposure=0.0,
        )
        # Base 5% * 0.5 = 2.5%
        assert result.size_pct == 0.025
        assert result.is_reduced is True
    
    def test_loss_protection_not_applied_at_threshold(self):
        """Test loss protection not applied at exactly 2 losses."""
        result = self.sizer.calculate(
            volume_ratio=2.5,
            alignment_score=70,
            consecutive_losses=2,  # At threshold, not over
            available_capital=10000,
            current_exposure=0.0,
        )
        assert result.size_pct == 0.05
        assert result.is_reduced is False
    
    def test_exposure_cap_reduces_size(self):
        """Test exposure cap reduces position size."""
        result = self.sizer.calculate(
            volume_ratio=6.0,  # 10% base
            alignment_score=70,
            consecutive_losses=0,
            available_capital=10000,
            current_exposure=0.40,  # 40% already used, 5% remaining
        )
        # Max exposure 45%, current 40%, so max new = 5%
        assert result.size_pct == pytest.approx(0.05)
        assert result.is_capped is True
    
    def test_exposure_cap_blocks_new_position(self):
        """Test no new position when at max exposure."""
        result = self.sizer.calculate(
            volume_ratio=6.0,
            alignment_score=70,
            consecutive_losses=0,
            available_capital=10000,
            current_exposure=0.45,  # At max
        )
        assert result.size_pct == 0.0
        assert result.leverage == 0
        assert result.is_capped is True
    
    def test_below_minimum_ratio(self):
        """Test volume ratio below minimum returns zero."""
        result = self.sizer.calculate(
            volume_ratio=1.5,  # Below 2.0
            alignment_score=70,
            consecutive_losses=0,
            available_capital=10000,
            current_exposure=0.0,
        )
        assert result.size_pct == 0.0
        assert result.leverage == 0
        assert result.tier == "none"


class TestPositionSizeTiersProperty:
    """Property-based tests for Position Size and Leverage Tiers.
    
    Property 8: Position Size and Leverage Tiers
    For any volume_ratio:
    - If 2.0 <= volume_ratio < 3.0: size=5%, leverage=3x
    - If 3.0 <= volume_ratio < 5.0: size=7%, leverage=5x
    - If volume_ratio >= 5.0: size=10%, leverage=7x
    
    Validates: Requirements 5.1, 5.2, 5.3
    """
    
    def setup_method(self):
        """Set up test fixtures."""
        self.sizer = WaveRiderPositionSizer()
    
    @given(st.floats(min_value=2.0, max_value=2.999, allow_nan=False, allow_infinity=False))
    def test_property_tier1_size_5_percent(self, volume_ratio: float):
        """Property: Tier 1 (2.0-3.0) has 5% size."""
        size_pct = self.sizer.get_base_size_pct(volume_ratio)
        assert size_pct == 0.05
    
    @given(st.floats(min_value=2.0, max_value=2.999, allow_nan=False, allow_infinity=False))
    def test_property_tier1_leverage_3x(self, volume_ratio: float):
        """Property: Tier 1 (2.0-3.0) has 3x leverage."""
        leverage = self.sizer.get_base_leverage(volume_ratio)
        assert leverage == 3
    
    @given(st.floats(min_value=3.0, max_value=4.999, allow_nan=False, allow_infinity=False))
    def test_property_tier2_size_7_percent(self, volume_ratio: float):
        """Property: Tier 2 (3.0-5.0) has 7% size."""
        size_pct = self.sizer.get_base_size_pct(volume_ratio)
        assert size_pct == 0.07
    
    @given(st.floats(min_value=3.0, max_value=4.999, allow_nan=False, allow_infinity=False))
    def test_property_tier2_leverage_5x(self, volume_ratio: float):
        """Property: Tier 2 (3.0-5.0) has 5x leverage."""
        leverage = self.sizer.get_base_leverage(volume_ratio)
        assert leverage == 5
    
    @given(st.floats(min_value=5.0, max_value=100.0, allow_nan=False, allow_infinity=False))
    def test_property_tier3_size_10_percent(self, volume_ratio: float):
        """Property: Tier 3 (5.0+) has 10% size."""
        size_pct = self.sizer.get_base_size_pct(volume_ratio)
        assert size_pct == 0.10
    
    @given(st.floats(min_value=5.0, max_value=100.0, allow_nan=False, allow_infinity=False))
    def test_property_tier3_leverage_7x(self, volume_ratio: float):
        """Property: Tier 3 (5.0+) has 7x leverage."""
        leverage = self.sizer.get_base_leverage(volume_ratio)
        assert leverage == 7


class TestAlignmentLeverageBonusProperty:
    """Property-based tests for Alignment Leverage Bonus.
    
    Property 9: Alignment Leverage Bonus
    For any signal with alignment_score of 100, leverage SHALL be
    increased by 1x (up to maximum 10x).
    
    Validates: Requirements 5.4
    """
    
    def setup_method(self):
        """Set up test fixtures."""
        self.sizer = WaveRiderPositionSizer()
    
    @given(st.floats(min_value=2.0, max_value=100.0, allow_nan=False, allow_infinity=False))
    def test_property_alignment_100_adds_leverage(self, volume_ratio: float):
        """Property: Alignment 100 adds 1x leverage."""
        base_leverage = self.sizer.get_base_leverage(volume_ratio)
        
        result = self.sizer.calculate(
            volume_ratio=volume_ratio,
            alignment_score=100,
            consecutive_losses=0,
            available_capital=10000,
            current_exposure=0.0,
        )
        
        expected = min(base_leverage + 1, 10)
        assert result.leverage == expected
    
    @given(
        volume_ratio=st.floats(min_value=2.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        alignment_score=st.sampled_from([40, 70]),
    )
    def test_property_non_100_alignment_no_bonus(self, volume_ratio: float, alignment_score: int):
        """Property: Alignment < 100 does not add leverage."""
        base_leverage = self.sizer.get_base_leverage(volume_ratio)
        
        result = self.sizer.calculate(
            volume_ratio=volume_ratio,
            alignment_score=alignment_score,
            consecutive_losses=0,
            available_capital=10000,
            current_exposure=0.0,
        )
        
        assert result.leverage == base_leverage
    
    @given(st.floats(min_value=2.0, max_value=100.0, allow_nan=False, allow_infinity=False))
    def test_property_leverage_never_exceeds_10(self, volume_ratio: float):
        """Property: Leverage is always <= 10x."""
        result = self.sizer.calculate(
            volume_ratio=volume_ratio,
            alignment_score=100,
            consecutive_losses=0,
            available_capital=10000,
            current_exposure=0.0,
        )
        
        assert result.leverage <= 10


class TestLossProtectionProperty:
    """Property-based tests for Loss Protection Size Reduction.
    
    Property 10: Loss Protection Size Reduction
    For any position sizing calculation where consecutive_losses > 2,
    the position size SHALL be reduced by 50%.
    
    Validates: Requirements 5.5
    """
    
    def setup_method(self):
        """Set up test fixtures."""
        self.sizer = WaveRiderPositionSizer()
    
    @given(
        volume_ratio=st.floats(min_value=2.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        consecutive_losses=st.integers(min_value=3, max_value=20),
    )
    def test_property_losses_over_2_reduce_size(self, volume_ratio: float, consecutive_losses: int):
        """Property: > 2 consecutive losses reduces size by 50%."""
        base_size = self.sizer.get_base_size_pct(volume_ratio)
        
        result = self.sizer.calculate(
            volume_ratio=volume_ratio,
            alignment_score=70,
            consecutive_losses=consecutive_losses,
            available_capital=10000,
            current_exposure=0.0,
        )
        
        expected_size = base_size * 0.5
        assert abs(result.size_pct - expected_size) < 1e-10
        assert result.is_reduced is True
    
    @given(
        volume_ratio=st.floats(min_value=2.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        consecutive_losses=st.integers(min_value=0, max_value=2),
    )
    def test_property_losses_at_or_below_2_no_reduction(self, volume_ratio: float, consecutive_losses: int):
        """Property: <= 2 consecutive losses does not reduce size."""
        base_size = self.sizer.get_base_size_pct(volume_ratio)
        
        result = self.sizer.calculate(
            volume_ratio=volume_ratio,
            alignment_score=70,
            consecutive_losses=consecutive_losses,
            available_capital=10000,
            current_exposure=0.0,
        )
        
        assert result.size_pct == base_size
        assert result.is_reduced is False
