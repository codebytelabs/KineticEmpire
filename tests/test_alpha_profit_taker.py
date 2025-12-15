"""Property-based tests for Partial Profit Taker.

**Feature: kinetic-empire-alpha, Property 3: Partial Profit Taking Sequence**
**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

Property: For any position, partial exits SHALL occur in ascending R-level order 
(1R before 2R before 3R) and total percentage exited SHALL never exceed 100%.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from datetime import datetime
from typing import List

from kinetic_empire.alpha.profit_taker import (
    PartialProfitTaker, 
    ProfitTakeConfig, 
    ProfitTakeLevel
)
from kinetic_empire.alpha.models import RFactorPosition, PartialExit


class TestPartialProfitTakerProperties:
    """Property-based tests for partial profit taking system."""
    
    @given(
        entry_price=st.floats(min_value=10.0, max_value=10000.0, allow_nan=False),
        stop_distance_pct=st.floats(min_value=0.01, max_value=0.2, allow_nan=False),
        position_size=st.floats(min_value=0.1, max_value=100.0, allow_nan=False),
        r_multiples=st.lists(
            st.floats(min_value=0.5, max_value=5.0, allow_nan=False),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=100)
    def test_partial_exits_ascending_order(
        self, entry_price: float, stop_distance_pct: float, 
        position_size: float, r_multiples: List[float]
    ):
        """**Feature: kinetic-empire-alpha, Property 3: Partial Profit Taking Sequence**
        
        For any position, partial exits SHALL occur in ascending R-level order.
        **Validates: Requirements 3.1, 3.2, 3.3**
        """
        profit_taker = PartialProfitTaker()
        stop_loss = entry_price * (1 - stop_distance_pct)
        
        position = RFactorPosition(
            pair="TEST/USDT",
            side="LONG",
            entry_price=entry_price,
            stop_loss=stop_loss,
            position_size=position_size,
            original_size=position_size,
            strategy="test"
        )
        
        taken_levels = []
        
        # Simulate price reaching various R multiples
        for r_mult in sorted(r_multiples):
            # Calculate price at this R multiple
            price_at_r = entry_price + (r_mult * position.r_value)
            position.update_current_r(price_at_r)
            
            # Check if profit level should be taken
            level = profit_taker.check_profit_levels(position)
            if level:
                # Execute the exit
                profit_taker.execute_partial_exit(position, level, price_at_r)
                taken_levels.append(level.r_level)
        
        # Property: Taken levels must be in ascending order
        for i in range(1, len(taken_levels)):
            assert taken_levels[i] > taken_levels[i-1], (
                f"Exits not in ascending order: {taken_levels}"
            )
    
    @given(
        levels=st.lists(
            st.tuples(
                st.floats(min_value=0.5, max_value=5.0, allow_nan=False),
                st.floats(min_value=0.05, max_value=0.4, allow_nan=False)
            ),
            min_size=1,
            max_size=8,
            unique_by=lambda x: round(x[0], 2)  # Unique R levels
        )
    )
    @settings(max_examples=100)
    def test_total_exits_never_exceed_100_percent(self, levels: List[tuple]):
        """**Feature: kinetic-empire-alpha, Property 3: Partial Profit Taking Sequence**
        
        Total percentage of partial exits SHALL never exceed 100%.
        **Validates: Requirements 3.1, 3.2, 3.3, 3.4**
        """
        # Filter to ensure total doesn't exceed 100%
        total_pct = sum(pct for _, pct in levels)
        if total_pct > 1.0:
            # Scale down proportionally
            scale = 0.95 / total_pct
            levels = [(r, pct * scale) for r, pct in levels]
        
        config = ProfitTakeConfig(
            levels=[ProfitTakeLevel(r_level=r, percentage=pct) for r, pct in levels]
        )
        profit_taker = PartialProfitTaker(config)
        
        position = RFactorPosition(
            pair="TEST/USDT",
            side="LONG",
            entry_price=100.0,
            stop_loss=95.0,
            position_size=1.0,
            original_size=1.0,
            strategy="test"
        )
        
        # Execute all profit levels
        for r_level, _ in sorted(levels, key=lambda x: x[0]):
            price_at_r = 100.0 + (r_level * position.r_value)
            position.update_current_r(price_at_r)
            
            level = profit_taker.check_profit_levels(position)
            if level:
                profit_taker.execute_partial_exit(position, level, price_at_r)
        
        # Property: Total taken percentage must not exceed 100%
        total_taken = profit_taker.get_total_taken_pct(position.pair)
        assert total_taken <= 1.0, f"Total exits exceeded 100%: {total_taken * 100}%"
        
        # Property: Remaining position must be non-negative
        remaining = position.get_remaining_pct()
        assert remaining >= 0.0, f"Remaining position negative: {remaining}"
        assert remaining == pytest.approx(1.0 - total_taken, abs=1e-10)
    
    @given(
        entry_price=st.floats(min_value=10.0, max_value=10000.0, allow_nan=False),
        stop_distance_pct=st.floats(min_value=0.01, max_value=0.2, allow_nan=False),
        position_size=st.floats(min_value=0.1, max_value=100.0, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_stop_moves_to_breakeven_at_1r(
        self, entry_price: float, stop_distance_pct: float, position_size: float
    ):
        """**Feature: kinetic-empire-alpha, Property 3: Partial Profit Taking Sequence**
        
        WHEN profit reaches 1R THEN stop SHALL move to breakeven.
        **Validates: Requirements 3.1**
        """
        profit_taker = PartialProfitTaker()
        stop_loss = entry_price * (1 - stop_distance_pct)
        
        position = RFactorPosition(
            pair="TEST/USDT",
            side="LONG",
            entry_price=entry_price,
            stop_loss=stop_loss,
            position_size=position_size,
            original_size=position_size,
            strategy="test"
        )
        
        # Before 1R - should not move to breakeven
        position.update_current_r(entry_price + (0.5 * position.r_value))
        assert not profit_taker.should_move_stop_to_breakeven(position)
        
        # At 1R (with small buffer for floating point) - should move to breakeven
        # Add 1.01R to ensure we're clearly above the threshold
        position.update_current_r(entry_price + (1.01 * position.r_value))
        assert profit_taker.should_move_stop_to_breakeven(position)
        
        # Above 1R - should still indicate move to breakeven
        position.update_current_r(entry_price + (2.0 * position.r_value))
        assert profit_taker.should_move_stop_to_breakeven(position)
    
    @given(
        entry_price=st.floats(min_value=10.0, max_value=10000.0, allow_nan=False),
        stop_distance_pct=st.floats(min_value=0.01, max_value=0.2, allow_nan=False),
        position_size=st.floats(min_value=0.1, max_value=100.0, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_position_becomes_risk_free_after_1r_exit(
        self, entry_price: float, stop_distance_pct: float, position_size: float
    ):
        """**Feature: kinetic-empire-alpha, Property 3: Partial Profit Taking Sequence**
        
        WHEN partial profit is taken at 1R THEN position SHALL be marked risk-free.
        **Validates: Requirements 3.1**
        """
        profit_taker = PartialProfitTaker()
        stop_loss = entry_price * (1 - stop_distance_pct)
        
        position = RFactorPosition(
            pair="TEST/USDT",
            side="LONG",
            entry_price=entry_price,
            stop_loss=stop_loss,
            position_size=position_size,
            original_size=position_size,
            strategy="test"
        )
        
        # Initially not risk-free
        assert not position.is_risk_free()
        
        # Move to 1R (with buffer for floating point) and take profit
        price_at_1r = entry_price + (1.01 * position.r_value)
        position.update_current_r(price_at_1r)
        
        level = profit_taker.check_profit_levels(position)
        assert level is not None, f"Expected level at current_r={position.current_r}"
        assert level.r_level == 1.0
        
        profit_taker.execute_partial_exit(position, level, price_at_1r)
        
        # Now should be risk-free
        assert position.is_risk_free()
    
    @given(
        entry_price=st.floats(min_value=10.0, max_value=10000.0, allow_nan=False),
        stop_distance_pct=st.floats(min_value=0.01, max_value=0.2, allow_nan=False),
        position_size=st.floats(min_value=0.1, max_value=100.0, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_remaining_position_trails_after_3r(
        self, entry_price: float, stop_distance_pct: float, position_size: float
    ):
        """**Feature: kinetic-empire-alpha, Property 3: Partial Profit Taking Sequence**
        
        WHILE remaining 25% position is active THEN it SHALL trail with advanced stops.
        **Validates: Requirements 3.4**
        """
        profit_taker = PartialProfitTaker()
        stop_loss = entry_price * (1 - stop_distance_pct)
        
        position = RFactorPosition(
            pair="TEST/USDT",
            side="LONG",
            entry_price=entry_price,
            stop_loss=stop_loss,
            position_size=position_size,
            original_size=position_size,
            strategy="test"
        )
        
        # Take profits at 1R, 2R, 3R (with buffer for floating point)
        for r_target in [1.01, 2.01, 3.01]:
            price_at_r = entry_price + (r_target * position.r_value)
            position.update_current_r(price_at_r)
            
            level = profit_taker.check_profit_levels(position)
            if level:
                profit_taker.execute_partial_exit(position, level, price_at_r)
        
        # After 3R exits, 25% should remain
        remaining = position.get_remaining_pct()
        assert remaining == pytest.approx(0.25, abs=0.01), (
            f"Expected 25% remaining, got {remaining * 100}%"
        )
        
        # Config should indicate trailing for remaining
        assert profit_taker.config.trail_remaining


class TestPartialProfitTakerEdgeCases:
    """Edge case tests for partial profit taker."""
    
    def test_no_exit_before_first_level(self):
        """Test that no exit occurs before reaching first R level."""
        profit_taker = PartialProfitTaker()
        
        position = RFactorPosition(
            pair="TEST/USDT",
            side="LONG",
            entry_price=100.0,
            stop_loss=95.0,
            position_size=1.0,
            original_size=1.0,
            strategy="test"
        )
        
        # At 0.5R - no exit
        position.update_current_r(102.5)  # 0.5R profit
        level = profit_taker.check_profit_levels(position)
        assert level is None
    
    def test_same_level_not_taken_twice(self):
        """Test that same R level is not taken twice."""
        profit_taker = PartialProfitTaker()
        
        position = RFactorPosition(
            pair="TEST/USDT",
            side="LONG",
            entry_price=100.0,
            stop_loss=95.0,
            position_size=1.0,
            original_size=1.0,
            strategy="test"
        )
        
        # Take 1R
        position.update_current_r(105.0)
        level = profit_taker.check_profit_levels(position)
        assert level is not None
        profit_taker.execute_partial_exit(position, level, 105.0)
        
        # Try to take 1R again - should return None
        level = profit_taker.check_profit_levels(position)
        assert level is None or level.r_level > 1.0
    
    def test_short_position_profit_calculation(self):
        """Test profit calculation for short positions."""
        profit_taker = PartialProfitTaker()
        
        position = RFactorPosition(
            pair="TEST/USDT",
            side="SHORT",
            entry_price=100.0,
            stop_loss=105.0,  # Stop above for short
            position_size=1.0,
            original_size=1.0,
            strategy="test"
        )
        
        # For short, profit when price goes down
        exit_price = 95.0  # 1R profit for short
        exit_size = 0.25
        
        profit = profit_taker.calculate_partial_profit(position, exit_price, exit_size)
        
        # Profit = (entry - exit) * size = (100 - 95) * 0.25 = 1.25
        assert profit == pytest.approx(1.25, abs=0.01)
    
    def test_reset_position_clears_tracking(self):
        """Test that reset_position clears all tracking."""
        profit_taker = PartialProfitTaker()
        
        position = RFactorPosition(
            pair="TEST/USDT",
            side="LONG",
            entry_price=100.0,
            stop_loss=95.0,
            position_size=1.0,
            original_size=1.0,
            strategy="test"
        )
        
        # Take 1R
        position.update_current_r(105.0)
        level = profit_taker.check_profit_levels(position)
        profit_taker.execute_partial_exit(position, level, 105.0)
        
        assert profit_taker.get_total_taken_pct("TEST/USDT") > 0
        
        # Reset
        profit_taker.reset_position("TEST/USDT")
        
        assert profit_taker.get_total_taken_pct("TEST/USDT") == 0
    
    def test_next_target_r_returns_correct_level(self):
        """Test that next_target_r returns the correct next level."""
        profit_taker = PartialProfitTaker()
        
        position = RFactorPosition(
            pair="TEST/USDT",
            side="LONG",
            entry_price=100.0,
            stop_loss=95.0,
            position_size=1.0,
            original_size=1.0,
            strategy="test"
        )
        
        # Initially, next target is 1R
        assert profit_taker.get_next_target_r(position) == 1.0
        
        # Take 1R
        position.update_current_r(105.0)
        level = profit_taker.check_profit_levels(position)
        profit_taker.execute_partial_exit(position, level, 105.0)
        
        # Next target is 2R
        assert profit_taker.get_next_target_r(position) == 2.0
        
        # Take 2R
        position.update_current_r(110.0)
        level = profit_taker.check_profit_levels(position)
        profit_taker.execute_partial_exit(position, level, 110.0)
        
        # Next target is 3R
        assert profit_taker.get_next_target_r(position) == 3.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
