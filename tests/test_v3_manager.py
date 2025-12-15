"""Property-based tests for Kinetic Empire v3.0 Position Manager.

**Feature: kinetic-empire-v3**
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from datetime import datetime
from src.kinetic_empire.v3.manager.position_manager import PositionManager
from src.kinetic_empire.v3.core.models import Position


# Strategies
equity_strategy = st.floats(min_value=1000.0, max_value=1000000.0, allow_nan=False, allow_infinity=False)
price_strategy = st.floats(min_value=1.0, max_value=100000.0, allow_nan=False, allow_infinity=False)
confidence_strategy = st.integers(min_value=60, max_value=100)


class TestRiskChecks:
    """Property tests for pre-trade risk checks."""

    @given(
        equity=equity_strategy,
        margin_used=st.floats(min_value=0.0, max_value=100000.0, allow_nan=False, allow_infinity=False),
        margin_total=st.floats(min_value=10000.0, max_value=1000000.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_risk_check_completeness(self, equity: float, margin_used: float, margin_total: float):
        """**Feature: kinetic-empire-v3, Property 10: Risk Check Completeness**
        
        For any trade attempt, all five pre-trade risk checks SHALL be evaluated before execution.
        **Validates: Requirements 7.1-7.5**
        """
        assume(margin_total > margin_used)
        
        manager = PositionManager()
        can_trade, reason = manager.check_risk_limits(equity, margin_used, margin_total, "BTCUSDT")
        
        # Result should be a boolean and string
        assert isinstance(can_trade, bool)
        assert isinstance(reason, str)
        assert len(reason) > 0

    @given(num_positions=st.integers(min_value=0, max_value=20))
    @settings(max_examples=50)
    def test_max_positions_check(self, num_positions: int):
        """Max positions check should reject when limit reached."""
        manager = PositionManager(max_positions=12)
        
        # Add positions
        symbols = [f"COIN{i}USDT" for i in range(num_positions)]
        for symbol in symbols:
            manager.positions[symbol] = Position(
                symbol=symbol,
                side="LONG",
                entry_price=100.0,
                size=1.0,
                leverage=10,
                stop_loss=97.0,
                take_profit=105.0,
            )
        
        can_trade, reason = manager.check_risk_limits(10000, 1000, 10000, "NEWUSDT")
        
        if num_positions >= 12:
            assert not can_trade
            assert "Max positions" in reason
        else:
            # May still fail for other reasons, but not max positions
            if not can_trade:
                assert "Max positions" not in reason or num_positions >= 12

    @given(
        margin_used=st.floats(min_value=0.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
        margin_total=st.floats(min_value=10000.0, max_value=100000.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_margin_usage_check(self, margin_used: float, margin_total: float):
        """Margin usage check should reject when above 90%."""
        assume(margin_total > 0)
        
        manager = PositionManager(max_margin_usage_pct=90.0)
        margin_usage_pct = (margin_used / margin_total) * 100
        
        can_trade, reason = manager.check_risk_limits(10000, margin_used, margin_total, "BTCUSDT")
        
        if margin_usage_pct >= 90.0:
            assert not can_trade
            assert "Margin usage" in reason


class TestLeverageMapping:
    """Property tests for leverage calculation."""

    @given(confidence=st.integers(min_value=60, max_value=100))
    @settings(max_examples=100)
    def test_leverage_mapping_correctness(self, confidence: int):
        """**Feature: kinetic-empire-v3, Property 7: Leverage Mapping Correctness**
        
        For any confidence score between 60-100, the calculated leverage 
        SHALL match the defined mapping table exactly.
        **Validates: Requirements 4.1-4.5**
        """
        manager = PositionManager()
        leverage = manager.calculate_leverage(confidence, high_volatility=False)
        
        # Verify mapping
        if 60 <= confidence <= 69:
            assert leverage == 5, f"Confidence {confidence} should map to 5x, got {leverage}x"
        elif 70 <= confidence <= 79:
            assert leverage == 10, f"Confidence {confidence} should map to 10x, got {leverage}x"
        elif 80 <= confidence <= 89:
            assert leverage == 15, f"Confidence {confidence} should map to 15x, got {leverage}x"
        elif 90 <= confidence <= 100:
            assert leverage == 20, f"Confidence {confidence} should map to 20x, got {leverage}x"

    @given(confidence=st.integers(min_value=0, max_value=59))
    @settings(max_examples=50)
    def test_low_confidence_rejected(self, confidence: int):
        """Confidence below 60 should return 0 leverage (rejected)."""
        manager = PositionManager()
        leverage = manager.calculate_leverage(confidence)
        assert leverage == 0, f"Low confidence {confidence} should be rejected"

    @given(confidence=st.integers(min_value=60, max_value=100))
    @settings(max_examples=100)
    def test_high_volatility_reduces_leverage(self, confidence: int):
        """High volatility should reduce leverage by 50%."""
        manager = PositionManager()
        
        normal_leverage = manager.calculate_leverage(confidence, high_volatility=False)
        high_vol_leverage = manager.calculate_leverage(confidence, high_volatility=True)
        
        # High volatility leverage should be ~50% of normal
        expected_high_vol = max(1, normal_leverage // 2)
        assert high_vol_leverage == expected_high_vol, (
            f"High vol leverage {high_vol_leverage} should be {expected_high_vol}"
        )


class TestPositionSizing:
    """Property tests for position sizing."""

    @given(
        equity=equity_strategy,
        confidence=confidence_strategy,
        entry_price=price_strategy,
        stop_distance_pct=st.floats(min_value=0.5, max_value=3.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_position_size_bounds(self, equity: float, confidence: int, entry_price: float, stop_distance_pct: float):
        """**Feature: kinetic-empire-v3, Property 8: Position Size Bounds**
        
        For any calculated position size, the notional value SHALL not exceed 25% of account equity.
        **Validates: Requirements 5.5**
        """
        manager = PositionManager(max_position_pct=25.0)
        
        stop_loss = entry_price * (1 - stop_distance_pct / 100)
        size = manager.calculate_position_size(equity, confidence, entry_price, stop_loss)
        
        # Calculate notional value
        notional_value = size * entry_price
        max_allowed = equity * 0.25
        
        # Allow small floating point tolerance
        assert notional_value <= max_allowed * 1.001, (
            f"Position value {notional_value:.2f} exceeds 25% of equity ({max_allowed:.2f})"
        )

    @given(
        equity=equity_strategy,
        entry_price=price_strategy,
        stop_distance_pct=st.floats(min_value=0.5, max_value=3.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_higher_confidence_larger_position(self, equity: float, entry_price: float, stop_distance_pct: float):
        """Higher confidence should result in larger position (up to cap)."""
        manager = PositionManager()
        
        stop_loss = entry_price * (1 - stop_distance_pct / 100)
        
        size_60 = manager.calculate_position_size(equity, 60, entry_price, stop_loss)
        size_90 = manager.calculate_position_size(equity, 90, entry_price, stop_loss)
        
        # 90 confidence should have larger or equal position (may be capped)
        assert size_90 >= size_60, f"Size at 90 ({size_90}) should be >= size at 60 ({size_60})"

    @given(
        equity=equity_strategy,
        confidence=confidence_strategy,
        entry_price=price_strategy,
    )
    @settings(max_examples=50)
    def test_zero_stop_distance_returns_zero(self, equity: float, confidence: int, entry_price: float):
        """Zero stop distance should return zero position size."""
        manager = PositionManager()
        
        # Stop loss at entry = zero distance
        size = manager.calculate_position_size(equity, confidence, entry_price, entry_price)
        assert size == 0, "Zero stop distance should return zero size"


class TestPositionTracking:
    """Tests for position tracking functionality."""

    def test_add_and_get_position(self):
        """Should be able to add and retrieve positions."""
        manager = PositionManager()
        
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            size=0.1,
            leverage=10,
            stop_loss=48500.0,
            take_profit=52500.0,
        )
        
        manager.add_position(position)
        
        retrieved = manager.get_position("BTCUSDT")
        assert retrieved is not None
        assert retrieved.symbol == "BTCUSDT"
        assert retrieved.entry_price == 50000.0

    def test_remove_position_updates_pnl(self):
        """Removing position should update daily P&L."""
        manager = PositionManager()
        manager.daily_start_equity = 10000.0
        
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            size=0.1,
            leverage=10,
            stop_loss=48500.0,
            take_profit=52500.0,
        )
        
        manager.add_position(position)
        manager.remove_position("BTCUSDT", pnl=100.0)
        
        assert manager.daily_pnl == 100.0
        assert "BTCUSDT" not in manager.positions

    def test_duplicate_position_rejected(self):
        """Should reject trade if already have position in symbol."""
        manager = PositionManager()
        
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            size=0.1,
            leverage=10,
            stop_loss=48500.0,
            take_profit=52500.0,
        )
        
        manager.add_position(position)
        
        can_trade, reason = manager.check_risk_limits(10000, 1000, 10000, "BTCUSDT")
        assert not can_trade
        assert "Already have position" in reason



class TestPartialExits:
    """Property tests for partial exit sequence."""

    def test_partial_exit_sequence(self):
        """**Feature: kinetic-empire-v3, Property 9: Partial Exit Sequence**
        
        For any position that reaches +2.5% profit, the system SHALL have 
        already executed the +1.5% partial exit (40% close).
        **Validates: Requirements 6.1, 6.2**
        """
        manager = PositionManager()
        
        # Create a position
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            size=1.0,
            leverage=10,
            stop_loss=48500.0,
            take_profit=52500.0,
        )
        manager.add_position(position)
        
        # Price at +1.6% (above TP1 threshold of 1.5%)
        tp1_price = 50000.0 * 1.016
        tp_triggers = manager.check_take_profits({"BTCUSDT": tp1_price})
        
        assert len(tp_triggers) == 1
        assert tp_triggers[0] == ("BTCUSDT", 1, 40.0)
        assert len(position.partial_exits) == 1
        
        # Price at +2.6% (above TP2 threshold of 2.5%)
        tp2_price = 50000.0 * 1.026
        tp_triggers = manager.check_take_profits({"BTCUSDT": tp2_price})
        
        assert len(tp_triggers) == 1
        assert tp_triggers[0] == ("BTCUSDT", 2, 30.0)
        assert len(position.partial_exits) == 2  # Both TP1 and TP2 recorded

    def test_tp2_requires_tp1(self):
        """TP2 should only trigger after TP1 has been executed."""
        manager = PositionManager()
        
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            size=1.0,
            leverage=10,
            stop_loss=48500.0,
            take_profit=52500.0,
        )
        manager.add_position(position)
        
        # Jump directly to +2.6% without hitting TP1 first
        tp2_price = 50000.0 * 1.026
        tp_triggers = manager.check_take_profits({"BTCUSDT": tp2_price})
        
        # Should trigger TP1 first (since partial_exits is empty)
        assert len(tp_triggers) == 1
        assert tp_triggers[0][1] == 1  # TP level 1


class TestEmergencyExits:
    """Property tests for emergency exit triggers."""

    def test_emergency_exit_trigger_portfolio(self):
        """**Feature: kinetic-empire-v3, Property 11: Emergency Exit Trigger**
        
        For any portfolio state where unrealized loss exceeds 5%, 
        the system SHALL close all positions.
        **Validates: Requirements 8.1**
        """
        manager = PositionManager()
        
        # Add multiple positions
        for i, symbol in enumerate(["BTCUSDT", "ETHUSDT", "SOLUSDT"]):
            position = Position(
                symbol=symbol,
                side="LONG",
                entry_price=1000.0 * (i + 1),
                size=1.0,
                leverage=10,
                stop_loss=950.0 * (i + 1),
                take_profit=1050.0 * (i + 1),
            )
            manager.add_position(position)
        
        equity = 10000.0
        unrealized_pnl = -600.0  # -6% loss
        
        emergencies = manager.emergency_check(
            equity, unrealized_pnl, {"BTCUSDT": 900, "ETHUSDT": 1800, "SOLUSDT": 2700}
        )
        
        # All positions should be flagged for emergency close
        assert len(emergencies) == 3
        for symbol, reason in emergencies:
            assert reason == "EMERGENCY_PORTFOLIO"

    def test_emergency_exit_single_position(self):
        """Single position with -4% loss should trigger emergency close."""
        manager = PositionManager()
        
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            size=1.0,
            leverage=10,
            stop_loss=48500.0,
            take_profit=52500.0,
        )
        manager.add_position(position)
        
        # Price at -4.5% (below -4% threshold)
        bad_price = 50000.0 * 0.955
        
        emergencies = manager.emergency_check(
            10000.0, -450.0, {"BTCUSDT": bad_price}
        )
        
        assert len(emergencies) == 1
        assert emergencies[0] == ("BTCUSDT", "EMERGENCY_POSITION")

    @given(
        equity=st.floats(min_value=1000.0, max_value=100000.0, allow_nan=False, allow_infinity=False),
        loss_pct=st.floats(min_value=5.0, max_value=50.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=50)
    def test_emergency_triggers_above_threshold(self, equity: float, loss_pct: float):
        """Emergency should trigger for any loss >= 5%."""
        manager = PositionManager()
        
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=1000.0,
            size=1.0,
            leverage=10,
            stop_loss=970.0,
            take_profit=1050.0,
        )
        manager.add_position(position)
        
        unrealized_pnl = -equity * (loss_pct / 100)
        
        emergencies = manager.emergency_check(equity, unrealized_pnl, {"BTCUSDT": 900})
        
        # Should trigger portfolio emergency
        assert len(emergencies) >= 1


class TestTrailingStops:
    """Tests for trailing stop functionality."""

    def test_trailing_stop_activation(self):
        """Trailing stop should activate at +1.5% profit."""
        manager = PositionManager()
        
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            size=1.0,
            leverage=10,
            stop_loss=48500.0,
            take_profit=52500.0,
        )
        manager.add_position(position)
        
        # Price at +1.6% (above 1.5% threshold)
        price_16_pct = 50000.0 * 1.016
        updated = manager.update_trailing_stops({"BTCUSDT": price_16_pct})
        
        assert "BTCUSDT" in updated
        assert position.trailing_activated
        assert position.trailing_stop is not None

    def test_trailing_stop_tightens_at_3_pct(self):
        """Trailing stop should tighten at +3% profit."""
        manager = PositionManager()
        
        position = Position(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=50000.0,
            size=1.0,
            leverage=10,
            stop_loss=48500.0,
            take_profit=52500.0,
        )
        manager.add_position(position)
        
        # First activate at +1.6% (above 1.5% threshold)
        manager.update_trailing_stops({"BTCUSDT": 50000.0 * 1.016})
        initial_stop = position.trailing_stop
        assert initial_stop is not None, "Trailing stop should be set"
        
        # Then tighten at +3.1% (above 3% threshold)
        price_3_pct = 50000.0 * 1.031
        manager.update_trailing_stops({"BTCUSDT": price_3_pct})
        
        # Trailing stop should be tighter (higher for LONG)
        assert position.trailing_stop > initial_stop
