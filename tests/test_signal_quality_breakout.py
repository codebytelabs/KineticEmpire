"""Property-based tests for BreakoutDetector.

**Feature: signal-quality-fix, Property 8: Volume Surge and Breakout Detection**
**Validates: Requirements 8.1, 8.2, 8.3**
"""

import pytest
from hypothesis import given, strategies as st

from src.kinetic_empire.signal_quality.config import QualityGateConfig
from src.kinetic_empire.signal_quality.breakout_detector import BreakoutDetector


class TestBreakoutDetectorProperties:
    """Property-based tests for volume surge and breakout detection."""
    
    @given(volume_ratio=st.floats(min_value=2.0, max_value=10.0))
    def test_volume_surge_detected(self, volume_ratio: float):
        """Property: Volume > 200% of average SHALL flag volume surge.
        
        **Feature: signal-quality-fix, Property 8: Volume Surge and Breakout Detection**
        **Validates: Requirements 8.1**
        """
        detector = BreakoutDetector(QualityGateConfig())
        
        result = detector.detect(
            current_price=100.0,
            resistance_level=105.0,  # Price below resistance
            volume_ratio=volume_ratio,
        )
        
        assert result.is_volume_surge is True
    
    @given(volume_ratio=st.floats(min_value=0.1, max_value=1.99))
    def test_no_volume_surge_below_threshold(self, volume_ratio: float):
        """Property: Volume < 200% of average SHALL NOT flag volume surge.
        
        **Feature: signal-quality-fix, Property 8: Volume Surge and Breakout Detection**
        **Validates: Requirements 8.1**
        """
        detector = BreakoutDetector(QualityGateConfig())
        
        result = detector.detect(
            current_price=100.0,
            resistance_level=105.0,
            volume_ratio=volume_ratio,
        )
        
        assert result.is_volume_surge is False
    
    @given(
        price_above_resistance=st.floats(min_value=0.01, max_value=10.0),
        volume_ratio=st.floats(min_value=2.0, max_value=10.0)
    )
    def test_breakout_with_volume_surge(self, price_above_resistance: float, volume_ratio: float):
        """Property: Price > resistance AND volume surge SHALL flag breakout with +15 bonus.
        
        **Feature: signal-quality-fix, Property 8: Volume Surge and Breakout Detection**
        **Validates: Requirements 8.2**
        """
        detector = BreakoutDetector(QualityGateConfig())
        
        resistance = 100.0
        current_price = resistance + price_above_resistance
        
        result = detector.detect(
            current_price=current_price,
            resistance_level=resistance,
            volume_ratio=volume_ratio,
            direction="LONG",
        )
        
        assert result.is_breakout is True
        assert result.breakout_bonus == 15
    
    @given(volume_ratio=st.floats(min_value=2.0, max_value=10.0))
    def test_breakout_uses_tight_trailing(self, volume_ratio: float):
        """Property: Breakout trades SHALL use tighter trailing stops.
        
        **Feature: signal-quality-fix, Property 8: Volume Surge and Breakout Detection**
        **Validates: Requirements 8.3**
        """
        detector = BreakoutDetector(QualityGateConfig())
        
        result = detector.detect(
            current_price=105.0,  # Above resistance
            resistance_level=100.0,
            volume_ratio=volume_ratio,
            direction="LONG",
        )
        
        assert result.is_breakout is True
        assert result.use_tight_trailing is True


class TestBreakoutDetectorEdgeCases:
    """Edge case tests for breakout detector."""
    
    def test_volume_exactly_at_threshold(self):
        """Volume exactly at 2.0x should trigger surge."""
        detector = BreakoutDetector(QualityGateConfig())
        
        result = detector.detect(
            current_price=100.0,
            resistance_level=105.0,
            volume_ratio=2.0,
        )
        
        assert result.is_volume_surge is True
    
    def test_volume_just_below_threshold(self):
        """Volume at 1.99x should not trigger surge."""
        detector = BreakoutDetector(QualityGateConfig())
        
        result = detector.detect(
            current_price=100.0,
            resistance_level=105.0,
            volume_ratio=1.99,
        )
        
        assert result.is_volume_surge is False
    
    def test_price_at_resistance_no_breakout(self):
        """Price exactly at resistance should not be breakout."""
        detector = BreakoutDetector(QualityGateConfig())
        
        result = detector.detect(
            current_price=100.0,
            resistance_level=100.0,
            volume_ratio=3.0,
        )
        
        assert result.is_breakout is False
    
    def test_price_above_resistance_no_volume_no_breakout(self):
        """Price above resistance without volume surge is not breakout."""
        detector = BreakoutDetector(QualityGateConfig())
        
        result = detector.detect(
            current_price=105.0,
            resistance_level=100.0,
            volume_ratio=1.5,  # Below 2.0 threshold
        )
        
        assert result.is_breakout is False
        assert result.breakout_bonus == 0
    
    def test_support_breakdown_detection(self):
        """Support breakdown should work for SHORT signals."""
        detector = BreakoutDetector(QualityGateConfig())
        
        result = detector.detect_support_breakdown(
            current_price=95.0,  # Below support
            support_level=100.0,
            volume_ratio=2.5,
        )
        
        assert result.is_volume_surge is True
        assert result.is_breakout is True
        assert result.breakout_bonus == 15
        assert result.use_tight_trailing is True
    
    def test_no_breakdown_without_volume(self):
        """Support breakdown without volume should not trigger."""
        detector = BreakoutDetector(QualityGateConfig())
        
        result = detector.detect_support_breakdown(
            current_price=95.0,
            support_level=100.0,
            volume_ratio=1.5,  # Below threshold
        )
        
        assert result.is_breakout is False
        assert result.breakout_bonus == 0
