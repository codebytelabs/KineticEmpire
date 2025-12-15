"""Property-based tests for Pyramiding Module.

**Feature: kinetic-empire-alpha, Property 7: Pyramid Size Constraint**
**Validates: Requirements 6.2, 6.5**
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from datetime import datetime

from kinetic_empire.alpha.pyramiding import PyramidingModule, PyramidConfig
from kinetic_empire.alpha.models import RFactorPosition, TrendStrength


class TestPyramidingProperties:
    """Property-based tests for pyramiding module."""
    
    @given(
        original_size=st.floats(min_value=0.1, max_value=100.0, allow_nan=False),
        add_size_pct=st.floats(min_value=0.1, max_value=1.0, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_pyramid_size_constraint(self, original_size: float, add_size_pct: float):
        """**Feature: kinetic-empire-alpha, Property 7: Pyramid Size Constraint**
        
        Pyramid addition size SHALL equal original_size × add_size_pct.
        **Validates: Requirements 6.2**
        """
        config = PyramidConfig(add_size_pct=add_size_pct)
        module = PyramidingModule(config)
        
        calculated_size = module.calculate_pyramid_size(original_size)
        expected_size = original_size * add_size_pct
        
        assert abs(calculated_size - expected_size) < 1e-10, (
            f"Pyramid size mismatch: expected {expected_size}, got {calculated_size}"
        )
    
    @given(
        max_pyramids=st.integers(min_value=1, max_value=5),
        pyramid_attempts=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=50)
    def test_max_pyramid_limit_enforced(self, max_pyramids: int, pyramid_attempts: int):
        """**Feature: kinetic-empire-alpha, Property 7: Pyramid Size Constraint**
        
        WHEN maximum pyramid count is reached THEN no more pyramids SHALL be allowed.
        **Validates: Requirements 6.5**
        """
        config = PyramidConfig(max_pyramids=max_pyramids, entry_r_level=0.5)
        module = PyramidingModule(config)
        
        position = RFactorPosition(
            pair="BTC/USDT",
            side="LONG",
            entry_price=100.0,
            stop_loss=95.0,
            position_size=1.0,
            original_size=1.0,
            strategy="test"
        )
        position.current_r = 1.0  # Above entry threshold
        
        successful_pyramids = 0
        
        for _ in range(pyramid_attempts):
            if module.should_pyramid(position, TrendStrength.STRONG_UPTREND):
                module.execute_pyramid(position, 105.0)
                successful_pyramids += 1
        
        # Property: Should never exceed max_pyramids
        assert successful_pyramids <= max_pyramids, (
            f"Exceeded max pyramids: {successful_pyramids} > {max_pyramids}"
        )
        
        # Property: Should reach exactly max_pyramids if enough attempts
        if pyramid_attempts >= max_pyramids:
            assert successful_pyramids == max_pyramids, (
                f"Should have {max_pyramids} pyramids, got {successful_pyramids}"
            )
    
    @given(
        entry_price=st.floats(min_value=10.0, max_value=10000.0, allow_nan=False),
        stop_distance_pct=st.floats(min_value=0.01, max_value=0.1, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_pyramid_stop_at_entry(self, entry_price: float, stop_distance_pct: float):
        """**Feature: kinetic-empire-alpha, Property 7: Pyramid Size Constraint**
        
        WHEN pyramid_stop_at_entry is True THEN pyramid stop SHALL be at original entry.
        **Validates: Requirements 6.3**
        """
        config = PyramidConfig(pyramid_stop_at_entry=True)
        module = PyramidingModule(config)
        
        stop_loss = entry_price * (1 - stop_distance_pct)
        
        position = RFactorPosition(
            pair="BTC/USDT",
            side="LONG",
            entry_price=entry_price,
            stop_loss=stop_loss,
            position_size=1.0,
            original_size=1.0,
            strategy="test"
        )
        
        pyramid_stop = module.calculate_pyramid_stop(position)
        
        assert pyramid_stop == entry_price, (
            f"Pyramid stop should be at entry: expected {entry_price}, got {pyramid_stop}"
        )
    
    @given(
        entry_price=st.floats(min_value=10.0, max_value=10000.0, allow_nan=False),
        stop_distance_pct=st.floats(min_value=0.01, max_value=0.1, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_pyramid_stop_at_original_stop(self, entry_price: float, stop_distance_pct: float):
        """Test pyramid stop at original stop when configured."""
        config = PyramidConfig(pyramid_stop_at_entry=False)
        module = PyramidingModule(config)
        
        stop_loss = entry_price * (1 - stop_distance_pct)
        
        position = RFactorPosition(
            pair="BTC/USDT",
            side="LONG",
            entry_price=entry_price,
            stop_loss=stop_loss,
            position_size=1.0,
            original_size=1.0,
            strategy="test"
        )
        
        pyramid_stop = module.calculate_pyramid_stop(position)
        
        assert pyramid_stop == stop_loss, (
            f"Pyramid stop should be at original stop: expected {stop_loss}, got {pyramid_stop}"
        )


class TestPyramidingConditions:
    """Tests for pyramid entry conditions."""
    
    def test_no_pyramid_below_r_threshold(self):
        """Test that no pyramid occurs below R threshold."""
        config = PyramidConfig(entry_r_level=1.0)
        module = PyramidingModule(config)
        
        position = RFactorPosition(
            pair="BTC/USDT",
            side="LONG",
            entry_price=100.0,
            stop_loss=95.0,
            position_size=1.0,
            original_size=1.0,
            strategy="test"
        )
        position.current_r = 0.5  # Below threshold
        
        assert not module.should_pyramid(position, TrendStrength.STRONG_UPTREND)
    
    def test_pyramid_allowed_above_r_threshold(self):
        """Test that pyramid is allowed above R threshold."""
        config = PyramidConfig(entry_r_level=1.0)
        module = PyramidingModule(config)
        
        position = RFactorPosition(
            pair="BTC/USDT",
            side="LONG",
            entry_price=100.0,
            stop_loss=95.0,
            position_size=1.0,
            original_size=1.0,
            strategy="test"
        )
        position.current_r = 1.5  # Above threshold
        
        assert module.should_pyramid(position, TrendStrength.STRONG_UPTREND)
    
    def test_no_pyramid_wrong_trend_long(self):
        """Test that long position doesn't pyramid in downtrend."""
        module = PyramidingModule()
        
        position = RFactorPosition(
            pair="BTC/USDT",
            side="LONG",
            entry_price=100.0,
            stop_loss=95.0,
            position_size=1.0,
            original_size=1.0,
            strategy="test"
        )
        position.current_r = 2.0
        
        # Should not pyramid in downtrend
        assert not module.should_pyramid(position, TrendStrength.STRONG_DOWNTREND)
        assert not module.should_pyramid(position, TrendStrength.WEAK_DOWNTREND)
        assert not module.should_pyramid(position, TrendStrength.NEUTRAL)
    
    def test_no_pyramid_wrong_trend_short(self):
        """Test that short position doesn't pyramid in uptrend."""
        module = PyramidingModule()
        
        position = RFactorPosition(
            pair="BTC/USDT",
            side="SHORT",
            entry_price=100.0,
            stop_loss=105.0,
            position_size=1.0,
            original_size=1.0,
            strategy="test"
        )
        position.current_r = 2.0
        
        # Should not pyramid in uptrend
        assert not module.should_pyramid(position, TrendStrength.STRONG_UPTREND)
        assert not module.should_pyramid(position, TrendStrength.WEAK_UPTREND)
        assert not module.should_pyramid(position, TrendStrength.NEUTRAL)


class TestAverageEntryCalculation:
    """Tests for average entry calculation after pyramid."""
    
    @given(
        entry_price=st.floats(min_value=10.0, max_value=1000.0, allow_nan=False),
        position_size=st.floats(min_value=0.1, max_value=10.0, allow_nan=False),
        pyramid_price=st.floats(min_value=10.0, max_value=1000.0, allow_nan=False),
        pyramid_size=st.floats(min_value=0.1, max_value=10.0, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_average_entry_calculation(
        self, entry_price: float, position_size: float,
        pyramid_price: float, pyramid_size: float
    ):
        """Test that average entry is calculated correctly."""
        module = PyramidingModule()
        
        position = RFactorPosition(
            pair="BTC/USDT",
            side="LONG",
            entry_price=entry_price,
            stop_loss=entry_price * 0.95,
            position_size=position_size,
            original_size=position_size,
            strategy="test"
        )
        
        new_avg = module.update_average_entry(position, pyramid_price, pyramid_size)
        
        # Calculate expected average
        total_size = position_size + pyramid_size
        total_cost = entry_price * position_size + pyramid_price * pyramid_size
        expected_avg = total_cost / total_size
        
        assert abs(new_avg - expected_avg) < 1e-10, (
            f"Average entry mismatch: expected {expected_avg}, got {new_avg}"
        )
        
        # Property: Average should be between original and pyramid price (with tolerance)
        min_price = min(entry_price, pyramid_price)
        max_price = max(entry_price, pyramid_price)
        assert min_price - 1e-10 <= new_avg <= max_price + 1e-10, (
            f"Average {new_avg} not between {min_price} and {max_price}"
        )


class TestPyramidTracking:
    """Tests for pyramid tracking functionality."""
    
    def test_pyramid_count_tracking(self):
        """Test that pyramid count is tracked correctly."""
        module = PyramidingModule()
        
        position = RFactorPosition(
            pair="BTC/USDT",
            side="LONG",
            entry_price=100.0,
            stop_loss=95.0,
            position_size=1.0,
            original_size=1.0,
            strategy="test"
        )
        position.current_r = 2.0
        
        assert module.get_pyramid_count("BTC/USDT") == 0
        
        module.execute_pyramid(position, 105.0)
        assert module.get_pyramid_count("BTC/USDT") == 1
        
        module.execute_pyramid(position, 110.0)
        assert module.get_pyramid_count("BTC/USDT") == 2
    
    def test_reset_clears_tracking(self):
        """Test that reset clears all tracking."""
        module = PyramidingModule()
        
        position = RFactorPosition(
            pair="BTC/USDT",
            side="LONG",
            entry_price=100.0,
            stop_loss=95.0,
            position_size=1.0,
            original_size=1.0,
            strategy="test"
        )
        
        module.execute_pyramid(position, 105.0)
        assert module.get_pyramid_count("BTC/USDT") == 1
        
        module.reset_position("BTC/USDT")
        assert module.get_pyramid_count("BTC/USDT") == 0
        assert module.get_total_pyramid_size("BTC/USDT") == 0
    
    def test_total_pyramid_size_tracking(self):
        """Test that total pyramid size is tracked correctly."""
        config = PyramidConfig(add_size_pct=0.5, max_pyramids=3)
        module = PyramidingModule(config)
        
        position = RFactorPosition(
            pair="BTC/USDT",
            side="LONG",
            entry_price=100.0,
            stop_loss=95.0,
            position_size=1.0,
            original_size=1.0,
            strategy="test"
        )
        
        # Execute 2 pyramids
        module.execute_pyramid(position, 105.0)
        module.execute_pyramid(position, 110.0)
        
        # Each pyramid adds 0.5 of original size (1.0)
        expected_total = 0.5 + 0.5
        assert module.get_total_pyramid_size("BTC/USDT") == expected_total


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
