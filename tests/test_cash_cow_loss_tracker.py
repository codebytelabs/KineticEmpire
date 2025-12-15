"""Property-based tests for Consecutive Loss Tracker.

Uses Hypothesis for property-based testing to verify correctness properties
defined in the design document.
"""

import pytest
from hypothesis import given, strategies as st, settings

from src.kinetic_empire.cash_cow.loss_tracker import ConsecutiveLossTracker


class TestConsecutiveLossCounterCorrectness:
    """Tests for Property 3: Consecutive loss counter correctness."""

    # **Feature: cash-cow-upgrade, Property 3: Consecutive loss counter correctness**
    # *For any* sequence of trade results, the consecutive loss counter SHALL
    # equal the number of consecutive losses at the end of the sequence,
    # and SHALL reset to zero after any win.
    # **Validates: Requirements 2.1, 2.2**

    @given(num_losses=st.integers(min_value=0, max_value=20))
    @settings(max_examples=100)
    def test_loss_counter_increments_correctly(self, num_losses: int):
        """Recording N losses should result in counter = N."""
        tracker = ConsecutiveLossTracker()
        
        for _ in range(num_losses):
            tracker.record_loss()
        
        assert tracker.consecutive_losses == num_losses, (
            f"After {num_losses} losses, counter should be {num_losses}, "
            f"got {tracker.consecutive_losses}"
        )

    @given(
        losses_before=st.integers(min_value=1, max_value=10),
        losses_after=st.integers(min_value=0, max_value=10)
    )
    @settings(max_examples=100)
    def test_win_resets_counter_to_zero(self, losses_before: int, losses_after: int):
        """A win should reset counter to zero regardless of previous losses."""
        tracker = ConsecutiveLossTracker()
        
        # Record some losses
        for _ in range(losses_before):
            tracker.record_loss()
        
        # Record a win
        tracker.record_win()
        
        # Counter should be zero
        assert tracker.consecutive_losses == 0, (
            f"After win, counter should be 0, got {tracker.consecutive_losses}"
        )
        
        # Record more losses
        for _ in range(losses_after):
            tracker.record_loss()
        
        # Counter should equal losses_after
        assert tracker.consecutive_losses == losses_after, (
            f"After {losses_after} losses post-win, counter should be {losses_after}, "
            f"got {tracker.consecutive_losses}"
        )

    @given(sequence=st.lists(st.booleans(), min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_counter_equals_trailing_losses(self, sequence: list):
        """Counter should equal number of consecutive losses at end of sequence."""
        tracker = ConsecutiveLossTracker()
        
        for is_win in sequence:
            if is_win:
                tracker.record_win()
            else:
                tracker.record_loss()
        
        # Count trailing losses in sequence
        trailing_losses = 0
        for is_win in reversed(sequence):
            if is_win:
                break
            trailing_losses += 1
        
        assert tracker.consecutive_losses == trailing_losses, (
            f"Expected {trailing_losses} trailing losses, got {tracker.consecutive_losses}"
        )


class TestLossProtectionMultiplierCorrectness:
    """Tests for Property 4: Loss protection multiplier correctness."""

    # **Feature: cash-cow-upgrade, Property 4: Loss protection multiplier correctness**
    # *For any* consecutive loss count, the protection multiplier SHALL be
    # 1.0 for 0-2 losses, 0.5 for 3-4 losses, and 0.25 for 5+ losses.
    # **Validates: Requirements 2.3, 2.4, 2.5**

    @given(losses=st.integers(min_value=0, max_value=2))
    @settings(max_examples=100)
    def test_no_reduction_for_0_to_2_losses(self, losses: int):
        """0-2 consecutive losses should have 1.0x multiplier."""
        tracker = ConsecutiveLossTracker()
        for _ in range(losses):
            tracker.record_loss()
        
        assert tracker.get_protection_multiplier() == 1.0, (
            f"Expected 1.0 for {losses} losses, got {tracker.get_protection_multiplier()}"
        )

    @given(losses=st.integers(min_value=3, max_value=4))
    @settings(max_examples=100)
    def test_half_reduction_for_3_to_4_losses(self, losses: int):
        """3-4 consecutive losses should have 0.5x multiplier."""
        tracker = ConsecutiveLossTracker()
        for _ in range(losses):
            tracker.record_loss()
        
        assert tracker.get_protection_multiplier() == 0.5, (
            f"Expected 0.5 for {losses} losses, got {tracker.get_protection_multiplier()}"
        )

    @given(losses=st.integers(min_value=5, max_value=50))
    @settings(max_examples=100)
    def test_quarter_reduction_for_5_plus_losses(self, losses: int):
        """5+ consecutive losses should have 0.25x multiplier."""
        tracker = ConsecutiveLossTracker()
        for _ in range(losses):
            tracker.record_loss()
        
        assert tracker.get_protection_multiplier() == 0.25, (
            f"Expected 0.25 for {losses} losses, got {tracker.get_protection_multiplier()}"
        )

    @given(losses=st.integers(min_value=5, max_value=20))
    @settings(max_examples=100)
    def test_win_restores_normal_sizing(self, losses: int):
        """After consecutive losses, a win should restore 1.0x multiplier."""
        tracker = ConsecutiveLossTracker()
        
        # Build up losses
        for _ in range(losses):
            tracker.record_loss()
        
        # Verify reduced multiplier
        assert tracker.get_protection_multiplier() == 0.25
        
        # Record win
        tracker.record_win()
        
        # Verify restored multiplier
        assert tracker.get_protection_multiplier() == 1.0, (
            f"After win, multiplier should be 1.0, got {tracker.get_protection_multiplier()}"
        )


class TestResetBehavior:
    """Tests for reset functionality."""

    @given(losses=st.integers(min_value=1, max_value=20))
    @settings(max_examples=100)
    def test_reset_clears_counter(self, losses: int):
        """Reset should clear counter to zero."""
        tracker = ConsecutiveLossTracker()
        
        for _ in range(losses):
            tracker.record_loss()
        
        tracker.reset()
        
        assert tracker.consecutive_losses == 0
        assert tracker.get_protection_multiplier() == 1.0


class TestHaltTradingFlag:
    """Tests for trading halt recommendation."""

    @given(losses=st.integers(min_value=0, max_value=4))
    @settings(max_examples=100)
    def test_no_halt_under_5_losses(self, losses: int):
        """Should not recommend halt for fewer than 5 losses."""
        tracker = ConsecutiveLossTracker()
        for _ in range(losses):
            tracker.record_loss()
        
        assert not tracker.should_halt_trading

    @given(losses=st.integers(min_value=5, max_value=20))
    @settings(max_examples=100)
    def test_halt_at_5_plus_losses(self, losses: int):
        """Should recommend halt at 5+ losses."""
        tracker = ConsecutiveLossTracker()
        for _ in range(losses):
            tracker.record_loss()
        
        assert tracker.should_halt_trading
