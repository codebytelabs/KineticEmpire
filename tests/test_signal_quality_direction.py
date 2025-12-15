"""Property-based tests for DirectionAligner.

**Feature: signal-quality-fix, Property 2: Direction Enforcement**
**Validates: Requirements 2.1, 2.2, 2.3**
"""

import pytest
from hypothesis import given, strategies as st

from src.kinetic_empire.signal_quality.direction_aligner import DirectionAligner


# Strategy for generating direction strings
direction_strategy = st.sampled_from(["LONG", "SHORT", "long", "short", "Long", "Short"])


class TestDirectionAlignerProperties:
    """Property-based tests for direction enforcement."""
    
    @given(
        enhanced_direction=direction_strategy,
        cash_cow_direction=direction_strategy
    )
    def test_enhanced_direction_always_wins(
        self, enhanced_direction: str, cash_cow_direction: str
    ):
        """Property: Final direction SHALL always equal Enhanced TA direction.
        
        **Feature: signal-quality-fix, Property 2: Direction Enforcement**
        **Validates: Requirements 2.1, 2.2, 2.3**
        """
        aligner = DirectionAligner()
        
        result = aligner.align(enhanced_direction, cash_cow_direction)
        
        # Result should always be Enhanced TA direction (normalized to uppercase)
        assert result == enhanced_direction.upper()
    
    @given(enhanced_direction=direction_strategy)
    def test_long_enhanced_returns_long(self, enhanced_direction: str):
        """Property: LONG Enhanced TA direction SHALL result in LONG trade.
        
        **Feature: signal-quality-fix, Property 2: Direction Enforcement**
        **Validates: Requirements 2.1**
        """
        if enhanced_direction.upper() != "LONG":
            return  # Skip non-LONG cases
        
        aligner = DirectionAligner()
        
        # Test with conflicting Cash Cow direction
        result = aligner.align(enhanced_direction, "SHORT")
        
        assert result == "LONG"
    
    @given(enhanced_direction=direction_strategy)
    def test_short_enhanced_returns_short(self, enhanced_direction: str):
        """Property: SHORT Enhanced TA direction SHALL result in SHORT trade.
        
        **Feature: signal-quality-fix, Property 2: Direction Enforcement**
        **Validates: Requirements 2.2**
        """
        if enhanced_direction.upper() != "SHORT":
            return  # Skip non-SHORT cases
        
        aligner = DirectionAligner()
        
        # Test with conflicting Cash Cow direction
        result = aligner.align(enhanced_direction, "LONG")
        
        assert result == "SHORT"


class TestDirectionAlignerEdgeCases:
    """Edge case tests for direction alignment."""
    
    def test_same_direction_long(self):
        """Test when both systems agree on LONG."""
        aligner = DirectionAligner()
        result = aligner.align("LONG", "LONG")
        assert result == "LONG"
    
    def test_same_direction_short(self):
        """Test when both systems agree on SHORT."""
        aligner = DirectionAligner()
        result = aligner.align("SHORT", "SHORT")
        assert result == "SHORT"
    
    def test_conflict_enhanced_long(self):
        """Test conflict where Enhanced TA says LONG."""
        aligner = DirectionAligner()
        result = aligner.align("LONG", "SHORT")
        assert result == "LONG"
    
    def test_conflict_enhanced_short(self):
        """Test conflict where Enhanced TA says SHORT."""
        aligner = DirectionAligner()
        result = aligner.align("SHORT", "LONG")
        assert result == "SHORT"
    
    def test_case_insensitive(self):
        """Test that direction comparison is case-insensitive."""
        aligner = DirectionAligner()
        assert aligner.align("long", "SHORT") == "LONG"
        assert aligner.align("Long", "short") == "LONG"
        assert aligner.align("SHORT", "long") == "SHORT"
