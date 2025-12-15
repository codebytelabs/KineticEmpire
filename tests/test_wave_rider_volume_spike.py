"""Tests for Wave Rider Volume Spike Detector.

Includes property-based tests using hypothesis for Property 3: Volume Spike Classification.
"""

import pytest
from hypothesis import given, strategies as st

from src.kinetic_empire.wave_rider.volume_spike_detector import VolumeSpikeDetector
from src.kinetic_empire.wave_rider.models import SpikeClassification


class TestVolumeSpikeDetector:
    """Unit tests for VolumeSpikeDetector."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.detector = VolumeSpikeDetector()
    
    def test_no_spike_below_threshold(self):
        """Test no spike when volume_ratio < 2.0."""
        has_spike, classification = self.detector.detect_spike(1.5)
        assert has_spike is False
        assert classification == SpikeClassification.NONE
    
    def test_normal_spike_at_threshold(self):
        """Test normal spike at exactly 2.0."""
        has_spike, classification = self.detector.detect_spike(2.0)
        assert has_spike is True
        assert classification == SpikeClassification.NORMAL
    
    def test_normal_spike_in_range(self):
        """Test normal spike in 2.0-3.0 range."""
        has_spike, classification = self.detector.detect_spike(2.5)
        assert has_spike is True
        assert classification == SpikeClassification.NORMAL
    
    def test_strong_spike_at_threshold(self):
        """Test strong spike at exactly 3.0."""
        has_spike, classification = self.detector.detect_spike(3.0)
        assert has_spike is True
        assert classification == SpikeClassification.STRONG
    
    def test_strong_spike_in_range(self):
        """Test strong spike in 3.0-5.0 range."""
        has_spike, classification = self.detector.detect_spike(4.0)
        assert has_spike is True
        assert classification == SpikeClassification.STRONG
    
    def test_extreme_spike_at_threshold(self):
        """Test extreme spike at exactly 5.0."""
        has_spike, classification = self.detector.detect_spike(5.0)
        assert has_spike is True
        assert classification == SpikeClassification.EXTREME
    
    def test_extreme_spike_above_threshold(self):
        """Test extreme spike above 5.0."""
        has_spike, classification = self.detector.detect_spike(10.0)
        assert has_spike is True
        assert classification == SpikeClassification.EXTREME
    
    def test_spike_strength_no_spike(self):
        """Test spike strength returns 0 for no spike."""
        assert self.detector.get_spike_strength(1.0) == 0
        assert self.detector.get_spike_strength(1.99) == 0
    
    def test_spike_strength_normal(self):
        """Test spike strength for normal spike range."""
        # At 2.0, should be 25
        assert self.detector.get_spike_strength(2.0) == 25
        # At 2.5, should be ~37
        strength = self.detector.get_spike_strength(2.5)
        assert 35 <= strength <= 40
        # At 2.99, should be close to 50
        strength = self.detector.get_spike_strength(2.99)
        assert 45 <= strength <= 50
    
    def test_spike_strength_strong(self):
        """Test spike strength for strong spike range."""
        # At 3.0, should be 50
        assert self.detector.get_spike_strength(3.0) == 50
        # At 4.0, should be ~62
        strength = self.detector.get_spike_strength(4.0)
        assert 60 <= strength <= 65
        # At 4.99, should be close to 75
        strength = self.detector.get_spike_strength(4.99)
        assert 70 <= strength <= 75
    
    def test_spike_strength_extreme(self):
        """Test spike strength for extreme spike range."""
        # At 5.0, should be 75
        assert self.detector.get_spike_strength(5.0) == 75
        # At 10.0, should be 100 (capped)
        assert self.detector.get_spike_strength(10.0) == 100
        # At 20.0, should still be 100 (capped)
        assert self.detector.get_spike_strength(20.0) == 100


class TestVolumeSpikeProperty:
    """Property-based tests for Volume Spike Classification.
    
    Property 3: Volume Spike Classification
    For any volume_ratio, the spike classification SHALL be:
    - "extreme" if volume_ratio >= 5.0
    - "strong" if volume_ratio >= 3.0 and < 5.0
    - "normal" if volume_ratio >= 2.0 and < 3.0
    - "none" if volume_ratio < 2.0
    
    Validates: Requirements 2.2, 2.3, 2.4
    """
    
    def setup_method(self):
        """Set up test fixtures."""
        self.detector = VolumeSpikeDetector()
    
    @given(st.floats(min_value=0.0, max_value=1.999, allow_nan=False, allow_infinity=False))
    def test_property_no_spike_below_2(self, volume_ratio: float):
        """Property: volume_ratio < 2.0 => NONE classification."""
        classification = self.detector.classify(volume_ratio)
        assert classification == SpikeClassification.NONE
    
    @given(st.floats(min_value=2.0, max_value=2.999, allow_nan=False, allow_infinity=False))
    def test_property_normal_spike_2_to_3(self, volume_ratio: float):
        """Property: 2.0 <= volume_ratio < 3.0 => NORMAL classification."""
        classification = self.detector.classify(volume_ratio)
        assert classification == SpikeClassification.NORMAL
    
    @given(st.floats(min_value=3.0, max_value=4.999, allow_nan=False, allow_infinity=False))
    def test_property_strong_spike_3_to_5(self, volume_ratio: float):
        """Property: 3.0 <= volume_ratio < 5.0 => STRONG classification."""
        classification = self.detector.classify(volume_ratio)
        assert classification == SpikeClassification.STRONG
    
    @given(st.floats(min_value=5.0, max_value=100.0, allow_nan=False, allow_infinity=False))
    def test_property_extreme_spike_above_5(self, volume_ratio: float):
        """Property: volume_ratio >= 5.0 => EXTREME classification."""
        classification = self.detector.classify(volume_ratio)
        assert classification == SpikeClassification.EXTREME
    
    @given(st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False))
    def test_property_has_spike_iff_ratio_gte_2(self, volume_ratio: float):
        """Property: has_spike is True iff volume_ratio >= 2.0."""
        has_spike, _ = self.detector.detect_spike(volume_ratio)
        expected = volume_ratio >= 2.0
        assert has_spike == expected
    
    @given(st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False))
    def test_property_spike_strength_bounds(self, volume_ratio: float):
        """Property: spike strength is always 0-100."""
        strength = self.detector.get_spike_strength(volume_ratio)
        assert 0 <= strength <= 100
    
    @given(st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False))
    def test_property_spike_strength_monotonic(self, volume_ratio: float):
        """Property: spike strength is monotonically increasing with volume_ratio."""
        strength = self.detector.get_spike_strength(volume_ratio)
        # Test that a slightly higher ratio gives >= strength
        higher_ratio = volume_ratio + 0.1
        higher_strength = self.detector.get_spike_strength(higher_ratio)
        assert higher_strength >= strength
