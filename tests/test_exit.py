"""Property-based tests for exit signal generation.

Tests validate:
- Property 18: Exit Signal on Trend Break with Volume
"""

from hypothesis import given, strategies as st, settings
import pytest

from kinetic_empire.models import Position, Regime
from kinetic_empire.strategy.exit import ExitSignalGenerator, ExitSignal, ExitSignalType


class TestExitSignalTrendBreak:
    """Tests for Property 18: Exit Signal on Trend Break with Volume."""

    @given(
        close_5m=st.floats(min_value=0.01, max_value=100000, allow_nan=False),
        ema50_5m=st.floats(min_value=0.01, max_value=100000, allow_nan=False),
        volume=st.floats(min_value=0, max_value=1000000, allow_nan=False),
        mean_volume=st.floats(min_value=0.01, max_value=1000000, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_trend_break_with_volume_confirmation(
        self, close_5m, ema50_5m, volume, mean_volume
    ):
        """
        **Feature: kinetic-empire, Property 18: Exit Signal on Trend Break with Volume**
        
        *For any* position where (5m_close < 5m_ema50) AND (volume > mean_24h), 
        a SELL signal SHALL be generated.
        **Validates: Requirements 8.2, 8.3**
        """
        generator = ExitSignalGenerator()
        
        trend_break = generator.check_trend_break(
            close_5m, ema50_5m, volume, mean_volume
        )
        
        # Trend break should occur iff both conditions are met
        expected = (close_5m < ema50_5m) and (volume > mean_volume)
        assert trend_break == expected

    def test_trend_break_requires_both_conditions(self):
        """Trend break requires both price break AND volume confirmation."""
        generator = ExitSignalGenerator()
        
        # Price below EMA but low volume - no signal
        assert generator.check_trend_break(
            close_5m=95, ema50_5m=100, volume=50, mean_volume=100
        ) is False
        
        # Price above EMA but high volume - no signal
        assert generator.check_trend_break(
            close_5m=105, ema50_5m=100, volume=150, mean_volume=100
        ) is False
        
        # Both conditions met - signal
        assert generator.check_trend_break(
            close_5m=95, ema50_5m=100, volume=150, mean_volume=100
        ) is True


class TestStopLossCheck:
    """Tests for stop loss checking."""

    @given(
        current_price=st.floats(min_value=0.01, max_value=100000, allow_nan=False),
        stop_price=st.floats(min_value=0.01, max_value=100000, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_stop_loss_hit(self, current_price, stop_price):
        """Stop loss should trigger when current price <= stop price."""
        generator = ExitSignalGenerator()
        
        is_hit = generator.check_stop_loss(current_price, stop_price)
        
        expected = current_price <= stop_price
        assert is_hit == expected


class TestExitConditions:
    """Integration tests for exit condition checking."""

    def test_stop_loss_priority(self):
        """Stop loss should have priority over trend break."""
        generator = ExitSignalGenerator()
        
        position = Position(
            pair="BTC/USDT",
            entry_price=1000.0,
            current_price=950.0,
            amount=1.0,
            stop_loss=960.0,
            trailing_stop_active=False
        )
        
        # Both stop loss and trend break conditions met
        signal = generator.check_exit_conditions(
            position=position,
            close_5m=950.0,  # Below stop
            ema50_5m=1000.0,  # Trend break
            volume=200.0,
            mean_volume=100.0  # Volume confirmation
        )
        
        # Should exit with stop loss reason (higher priority)
        assert signal.should_exit is True
        assert signal.signal_type == ExitSignalType.STOP_LOSS

    def test_trend_break_exit(self):
        """Trend break should generate exit when stop not hit."""
        generator = ExitSignalGenerator()
        
        position = Position(
            pair="BTC/USDT",
            entry_price=1000.0,
            current_price=980.0,
            amount=1.0,
            stop_loss=950.0,  # Not hit
            trailing_stop_active=False
        )
        
        signal = generator.check_exit_conditions(
            position=position,
            close_5m=980.0,  # Below EMA
            ema50_5m=1000.0,
            volume=200.0,  # Above mean
            mean_volume=100.0
        )
        
        assert signal.should_exit is True
        assert signal.signal_type == ExitSignalType.TREND_BREAK

    def test_no_exit_signal(self):
        """No exit when conditions not met."""
        generator = ExitSignalGenerator()
        
        position = Position(
            pair="BTC/USDT",
            entry_price=1000.0,
            current_price=1050.0,
            amount=1.0,
            stop_loss=950.0,
            trailing_stop_active=False
        )
        
        signal = generator.check_exit_conditions(
            position=position,
            close_5m=1050.0,  # Above EMA
            ema50_5m=1000.0,
            volume=80.0,  # Below mean
            mean_volume=100.0
        )
        
        assert signal.should_exit is False
        assert signal.signal_type == ExitSignalType.NONE

    def test_trailing_stop_exit(self):
        """Trailing stop should trigger exit."""
        generator = ExitSignalGenerator()
        
        position = Position(
            pair="BTC/USDT",
            entry_price=1000.0,
            current_price=1080.0,
            amount=1.0,
            stop_loss=950.0,
            trailing_stop_active=True,
            trailing_stop_level=1070.0
        )
        
        signal = generator.check_exit_conditions(
            position=position,
            close_5m=1065.0,  # Below trailing stop
            ema50_5m=1000.0,
            volume=100.0,
            mean_volume=100.0
        )
        
        assert signal.should_exit is True
        # Should be stop loss type but with trailing stop reason
        assert signal.signal_type == ExitSignalType.STOP_LOSS

    def test_generate_exit_signal_boolean(self):
        """generate_exit_signal should return boolean."""
        generator = ExitSignalGenerator()
        
        position = Position(
            pair="BTC/USDT",
            entry_price=1000.0,
            current_price=950.0,
            amount=1.0,
            stop_loss=960.0,
            trailing_stop_active=False
        )
        
        # Should exit (stop loss hit)
        should_exit = generator.generate_exit_signal(
            position, 950.0, 1000.0, 100.0, 100.0
        )
        assert should_exit is True
        
        # Should not exit
        position.current_price = 1050.0
        should_exit = generator.generate_exit_signal(
            position, 1050.0, 1000.0, 80.0, 100.0
        )
        assert should_exit is False
