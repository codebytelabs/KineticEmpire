"""Property-based tests for Kinetic Empire v3.0 models.

**Feature: kinetic-empire-v3**
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from datetime import datetime
from src.kinetic_empire.v3.core.models import Signal, Position, Indicators


# Strategies for generating test data
price_strategy = st.floats(min_value=0.01, max_value=100000.0, allow_nan=False, allow_infinity=False)
confidence_strategy = st.integers(min_value=60, max_value=100)
leverage_strategy = st.integers(min_value=1, max_value=20)


@st.composite
def valid_indicators(draw):
    """Generate valid Indicators."""
    ema_21 = draw(st.floats(min_value=10.0, max_value=10000.0, allow_nan=False, allow_infinity=False))
    ema_9 = draw(st.floats(min_value=10.0, max_value=10000.0, allow_nan=False, allow_infinity=False))
    return Indicators(
        ema_9=ema_9,
        ema_21=ema_21,
        rsi=draw(st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False)),
        macd_line=draw(st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False)),
        macd_signal=draw(st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False)),
        macd_histogram=draw(st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False)),
        atr=draw(st.floats(min_value=0.01, max_value=100.0, allow_nan=False, allow_infinity=False)),
        volume_ratio=draw(st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False)),
    )


@st.composite
def valid_signal(draw):
    """Generate a valid Signal with stop loss capped at 3%."""
    entry_price = draw(st.floats(min_value=10.0, max_value=10000.0, allow_nan=False, allow_infinity=False))
    direction = draw(st.sampled_from(["LONG", "SHORT"]))
    confidence = draw(confidence_strategy)
    
    # Calculate stop loss within 3% limit (use 2.99% max to avoid floating point issues)
    stop_distance_pct = draw(st.floats(min_value=0.5, max_value=2.99, allow_nan=False, allow_infinity=False))
    stop_distance = entry_price * (stop_distance_pct / 100)
    
    if direction == "LONG":
        stop_loss = entry_price - stop_distance
        take_profit = entry_price + (stop_distance * 1.5)  # 1:1.5 R:R
    else:
        stop_loss = entry_price + stop_distance
        take_profit = entry_price - (stop_distance * 1.5)
    
    indicators = {
        "4h": draw(valid_indicators()),
        "1h": draw(valid_indicators()),
        "15m": draw(valid_indicators()),
    }
    
    return Signal(
        symbol="BTCUSDT",
        direction=direction,
        confidence=confidence,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        atr=draw(st.floats(min_value=0.01, max_value=100.0, allow_nan=False, allow_infinity=False)),
        timeframe_alignment=draw(st.booleans()),
        indicators=indicators,
    )


class TestSignalModel:
    """Property tests for Signal model."""

    @given(signal=valid_signal())
    @settings(max_examples=100)
    def test_stop_loss_bounds(self, signal: Signal):
        """**Feature: kinetic-empire-v3, Property 6: Stop Loss Bounds**
        
        For any generated Signal, the stop loss distance from entry 
        SHALL not exceed 3% regardless of ATR value.
        **Validates: Requirements 3.3**
        """
        risk_distance = signal.risk_distance
        # Allow small floating point tolerance
        assert risk_distance <= 3.001, f"Stop loss distance {risk_distance:.4f}% exceeds 3% limit"

    @given(signal=valid_signal())
    @settings(max_examples=100)
    def test_signal_validation(self, signal: Signal):
        """Valid signals should pass validation."""
        assert signal.validate(), f"Signal should be valid: {signal}"

    @given(signal=valid_signal())
    @settings(max_examples=100)
    def test_signal_direction_consistency(self, signal: Signal):
        """Stop loss and take profit must be on correct side of entry."""
        if signal.direction == "LONG":
            assert signal.stop_loss < signal.entry_price, "LONG stop loss must be below entry"
            assert signal.take_profit > signal.entry_price, "LONG take profit must be above entry"
        else:
            assert signal.stop_loss > signal.entry_price, "SHORT stop loss must be above entry"
            assert signal.take_profit < signal.entry_price, "SHORT take profit must be below entry"

    @given(signal=valid_signal())
    @settings(max_examples=100)
    def test_risk_reward_ratio_positive(self, signal: Signal):
        """Risk-reward ratio should be positive for valid signals."""
        assert signal.risk_reward_ratio > 0, f"R:R ratio should be positive, got {signal.risk_reward_ratio}"


class TestPositionModel:
    """Property tests for Position model."""

    @given(
        entry_price=price_strategy,
        size=st.floats(min_value=0.001, max_value=1000.0, allow_nan=False, allow_infinity=False),
        leverage=leverage_strategy,
        current_price=price_strategy,
    )
    @settings(max_examples=100)
    def test_pnl_calculation_long(self, entry_price: float, size: float, leverage: int, current_price: float):
        """P&L calculation for LONG positions should be correct."""
        assume(entry_price > 0)
        
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=entry_price,
            size=size,
            leverage=leverage,
            stop_loss=entry_price * 0.97,
            take_profit=entry_price * 1.05,
        )
        
        pnl_pct = position.calc_pnl_pct(current_price)
        expected_pnl = (current_price - entry_price) / entry_price * 100
        
        assert abs(pnl_pct - expected_pnl) < 0.0001, f"P&L mismatch: {pnl_pct} vs {expected_pnl}"

    @given(
        entry_price=price_strategy,
        size=st.floats(min_value=0.001, max_value=1000.0, allow_nan=False, allow_infinity=False),
        leverage=leverage_strategy,
        current_price=price_strategy,
    )
    @settings(max_examples=100)
    def test_pnl_calculation_short(self, entry_price: float, size: float, leverage: int, current_price: float):
        """P&L calculation for SHORT positions should be correct."""
        assume(entry_price > 0)
        
        position = Position(
            symbol="BTCUSDT",
            side="SHORT",
            entry_price=entry_price,
            size=size,
            leverage=leverage,
            stop_loss=entry_price * 1.03,
            take_profit=entry_price * 0.95,
        )
        
        pnl_pct = position.calc_pnl_pct(current_price)
        expected_pnl = (entry_price - current_price) / entry_price * 100
        
        assert abs(pnl_pct - expected_pnl) < 0.0001, f"P&L mismatch: {pnl_pct} vs {expected_pnl}"

    @given(
        entry_price=st.floats(min_value=100.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
        size=st.floats(min_value=0.001, max_value=100.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_stop_loss_trigger_long(self, entry_price: float, size: float):
        """LONG position stop loss should trigger when price falls below stop."""
        stop_loss = entry_price * 0.97  # 3% below
        
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=entry_price,
            size=size,
            leverage=10,
            stop_loss=stop_loss,
            take_profit=entry_price * 1.05,
        )
        
        # Price at stop should trigger
        assert position.should_stop_loss(stop_loss)
        # Price below stop should trigger
        assert position.should_stop_loss(stop_loss * 0.99)
        # Price above stop should not trigger
        assert not position.should_stop_loss(stop_loss * 1.01)


class TestIndicatorsModel:
    """Property tests for Indicators model."""

    @given(indicators=valid_indicators())
    @settings(max_examples=100)
    def test_ema_trend_consistency(self, indicators: Indicators):
        """EMA trend should match EMA values."""
        if indicators.ema_9 > indicators.ema_21:
            assert indicators.ema_trend == "UP"
        else:
            assert indicators.ema_trend == "DOWN"

    @given(indicators=valid_indicators())
    @settings(max_examples=100)
    def test_ema_spread_calculation(self, indicators: Indicators):
        """EMA spread should be calculated correctly."""
        if indicators.ema_21 != 0:
            expected_spread = (indicators.ema_9 - indicators.ema_21) / indicators.ema_21 * 100
            assert abs(indicators.ema_spread - expected_spread) < 0.0001
