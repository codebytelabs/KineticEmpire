"""Property-based tests for ConfidenceFilter.

**Feature: signal-quality-fix, Property 1: Confidence-Based Signal Filtering**
**Validates: Requirements 1.1, 1.2, 1.3**
"""

import pytest
from hypothesis import given, strategies as st

from src.kinetic_empire.signal_quality.config import QualityGateConfig
from src.kinetic_empire.signal_quality.confidence_filter import ConfidenceFilter
from src.kinetic_empire.signal_quality.models import ConfidenceTier


class TestConfidenceFilterProperties:
    """Property-based tests for confidence filtering."""
    
    @given(confidence=st.integers(min_value=0, max_value=39))
    def test_low_confidence_rejected(self, confidence: int):
        """Property: Confidence < 40 SHALL be rejected (relaxed from 50).
        
        **Feature: signal-quality-fix, Property 1: Confidence-Based Signal Filtering**
        **Validates: Requirements 1.1**
        """
        config = QualityGateConfig()
        filter = ConfidenceFilter(config)
        
        passed, tier, multiplier = filter.filter(confidence)
        
        assert passed is False, f"Confidence {confidence} should be rejected"
        assert tier == ConfidenceTier.LOW
        assert multiplier == 0.0
    
    @given(confidence=st.integers(min_value=40, max_value=59))
    def test_medium_confidence_half_size(self, confidence: int):
        """Property: Confidence 40-59 SHALL use 0.5x position size (relaxed from 50-69).
        
        **Feature: signal-quality-fix, Property 1: Confidence-Based Signal Filtering**
        **Validates: Requirements 1.2**
        """
        config = QualityGateConfig()
        filter = ConfidenceFilter(config)
        
        passed, tier, multiplier = filter.filter(confidence)
        
        assert passed is True, f"Confidence {confidence} should pass"
        assert tier == ConfidenceTier.MEDIUM
        assert multiplier == 0.5
    
    @given(confidence=st.integers(min_value=60, max_value=100))
    def test_high_confidence_full_size(self, confidence: int):
        """Property: Confidence >= 60 SHALL use full position size (relaxed from 70).
        
        **Feature: signal-quality-fix, Property 1: Confidence-Based Signal Filtering**
        **Validates: Requirements 1.3**
        """
        config = QualityGateConfig()
        filter = ConfidenceFilter(config)
        
        passed, tier, multiplier = filter.filter(confidence)
        
        assert passed is True, f"Confidence {confidence} should pass"
        assert tier == ConfidenceTier.HIGH
        assert multiplier == 1.0


class TestConfidenceFilterEdgeCases:
    """Edge case tests for confidence boundaries (relaxed thresholds)."""
    
    def test_boundary_39(self):
        """Test confidence at 39 (just below threshold)."""
        filter = ConfidenceFilter(QualityGateConfig())
        passed, tier, _ = filter.filter(39)
        assert passed is False
        assert tier == ConfidenceTier.LOW
    
    def test_boundary_40(self):
        """Test confidence at 40 (exactly at minimum - relaxed from 50)."""
        filter = ConfidenceFilter(QualityGateConfig())
        passed, tier, multiplier = filter.filter(40)
        assert passed is True
        assert tier == ConfidenceTier.MEDIUM
        assert multiplier == 0.5
    
    def test_boundary_59(self):
        """Test confidence at 59 (just below high tier - relaxed from 69)."""
        filter = ConfidenceFilter(QualityGateConfig())
        passed, tier, multiplier = filter.filter(59)
        assert passed is True
        assert tier == ConfidenceTier.MEDIUM
        assert multiplier == 0.5
    
    def test_boundary_60(self):
        """Test confidence at 60 (exactly at high tier - relaxed from 70)."""
        filter = ConfidenceFilter(QualityGateConfig())
        passed, tier, multiplier = filter.filter(60)
        assert passed is True
        assert tier == ConfidenceTier.HIGH
        assert multiplier == 1.0
