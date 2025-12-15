"""Tests for data models.

**Feature: kinetic-empire, Property 25: Trade Serialization Round Trip**
**Validates: Requirements 10.4**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime, timedelta

from kinetic_empire.models import (
    Regime,
    ExitReason,
    PairData,
    Trade,
    TradeOpen,
    TradeClose,
    Position,
    BacktestResult,
    PricePoint,
)


# Custom strategies for generating test data
regime_strategy = st.sampled_from([Regime.BULL, Regime.BEAR])
exit_reason_strategy = st.sampled_from(list(ExitReason))

datetime_strategy = st.datetimes(
    min_value=datetime(2020, 1, 1),
    max_value=datetime(2030, 12, 31),
)

positive_float_strategy = st.floats(
    min_value=0.0001,
    max_value=1000000.0,
    allow_nan=False,
    allow_infinity=False,
)

trade_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
    min_size=1,
    max_size=36,
)

pair_strategy = st.sampled_from([
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "DOGE/USDT", "XRP/USDT",
    "ADA/USDT", "AVAX/USDT", "DOT/USDT", "MATIC/USDT", "LINK/USDT",
])


class TestTradeSerializationRoundTrip:
    """Property-based tests for trade serialization."""

    # **Feature: kinetic-empire, Property 25: Trade Serialization Round Trip**
    # **Validates: Requirements 10.4**
    @given(
        trade_id=trade_id_strategy,
        pair=pair_strategy,
        entry_timestamp=datetime_strategy,
        entry_price=positive_float_strategy,
        stake_amount=positive_float_strategy,
        regime=regime_strategy,
        stop_loss=positive_float_strategy,
        amount=positive_float_strategy,
    )
    @settings(max_examples=100)
    def test_open_trade_serialization_round_trip(
        self,
        trade_id: str,
        pair: str,
        entry_timestamp: datetime,
        entry_price: float,
        stake_amount: float,
        regime: Regime,
        stop_loss: float,
        amount: float,
    ):
        """For any valid open Trade, serialize then deserialize produces equivalent object."""
        assume(len(trade_id) > 0)
        
        original = Trade(
            id=trade_id,
            pair=pair,
            entry_timestamp=entry_timestamp,
            entry_price=entry_price,
            stake_amount=stake_amount,
            regime=regime,
            stop_loss=stop_loss,
            amount=amount,
        )

        # Round trip through JSON
        json_str = original.to_json()
        restored = Trade.from_json(json_str)

        assert restored.id == original.id
        assert restored.pair == original.pair
        assert restored.entry_timestamp == original.entry_timestamp
        assert restored.entry_price == original.entry_price
        assert restored.stake_amount == original.stake_amount
        assert restored.regime == original.regime
        assert restored.stop_loss == original.stop_loss
        assert restored.amount == original.amount
        assert restored.is_closed == original.is_closed

    # **Feature: kinetic-empire, Property 25: Trade Serialization Round Trip**
    # **Validates: Requirements 10.4**
    @given(
        trade_id=trade_id_strategy,
        pair=pair_strategy,
        entry_timestamp=datetime_strategy,
        entry_price=positive_float_strategy,
        stake_amount=positive_float_strategy,
        regime=regime_strategy,
        stop_loss=positive_float_strategy,
        amount=positive_float_strategy,
        exit_price=positive_float_strategy,
        profit_loss=st.floats(min_value=-100000, max_value=100000, allow_nan=False, allow_infinity=False),
        exit_reason=exit_reason_strategy,
    )
    @settings(max_examples=100)
    def test_closed_trade_serialization_round_trip(
        self,
        trade_id: str,
        pair: str,
        entry_timestamp: datetime,
        entry_price: float,
        stake_amount: float,
        regime: Regime,
        stop_loss: float,
        amount: float,
        exit_price: float,
        profit_loss: float,
        exit_reason: ExitReason,
    ):
        """For any valid closed Trade, serialize then deserialize produces equivalent object."""
        assume(len(trade_id) > 0)
        
        exit_timestamp = entry_timestamp + timedelta(hours=1)
        
        original = Trade(
            id=trade_id,
            pair=pair,
            entry_timestamp=entry_timestamp,
            entry_price=entry_price,
            stake_amount=stake_amount,
            regime=regime,
            stop_loss=stop_loss,
            amount=amount,
            exit_timestamp=exit_timestamp,
            exit_price=exit_price,
            profit_loss=profit_loss,
            exit_reason=exit_reason,
        )

        # Round trip through JSON
        json_str = original.to_json()
        restored = Trade.from_json(json_str)

        assert restored.id == original.id
        assert restored.pair == original.pair
        assert restored.entry_timestamp == original.entry_timestamp
        assert restored.entry_price == original.entry_price
        assert restored.stake_amount == original.stake_amount
        assert restored.regime == original.regime
        assert restored.stop_loss == original.stop_loss
        assert restored.amount == original.amount
        assert restored.exit_timestamp == original.exit_timestamp
        assert restored.exit_price == original.exit_price
        assert restored.profit_loss == original.profit_loss
        assert restored.exit_reason == original.exit_reason
        assert restored.is_closed == original.is_closed
        assert restored.is_winner == original.is_winner


class TestTradeOpenSerialization:
    """Tests for TradeOpen serialization."""

    @given(
        trade_id=trade_id_strategy,
        pair=pair_strategy,
        timestamp=datetime_strategy,
        entry_price=positive_float_strategy,
        stake_amount=positive_float_strategy,
        regime=regime_strategy,
        stop_loss=positive_float_strategy,
    )
    @settings(max_examples=100)
    def test_trade_open_round_trip(
        self,
        trade_id: str,
        pair: str,
        timestamp: datetime,
        entry_price: float,
        stake_amount: float,
        regime: Regime,
        stop_loss: float,
    ):
        """TradeOpen serialization round trip preserves all fields."""
        assume(len(trade_id) > 0)
        
        original = TradeOpen(
            id=trade_id,
            timestamp=timestamp,
            pair=pair,
            entry_price=entry_price,
            stake_amount=stake_amount,
            regime=regime,
            stop_loss=stop_loss,
        )

        data = original.to_dict()
        restored = TradeOpen.from_dict(data)

        assert restored.id == original.id
        assert restored.timestamp == original.timestamp
        assert restored.pair == original.pair
        assert restored.entry_price == original.entry_price
        assert restored.stake_amount == original.stake_amount
        assert restored.regime == original.regime
        assert restored.stop_loss == original.stop_loss


class TestTradeCloseSerialization:
    """Tests for TradeClose serialization."""

    @given(
        trade_id=trade_id_strategy,
        timestamp=datetime_strategy,
        exit_price=positive_float_strategy,
        profit_loss=st.floats(min_value=-100000, max_value=100000, allow_nan=False, allow_infinity=False),
        exit_reason=exit_reason_strategy,
    )
    @settings(max_examples=100)
    def test_trade_close_round_trip(
        self,
        trade_id: str,
        timestamp: datetime,
        exit_price: float,
        profit_loss: float,
        exit_reason: ExitReason,
    ):
        """TradeClose serialization round trip preserves all fields."""
        assume(len(trade_id) > 0)
        
        original = TradeClose(
            trade_id=trade_id,
            timestamp=timestamp,
            exit_price=exit_price,
            profit_loss=profit_loss,
            exit_reason=exit_reason,
        )

        data = original.to_dict()
        restored = TradeClose.from_dict(data)

        assert restored.trade_id == original.trade_id
        assert restored.timestamp == original.timestamp
        assert restored.exit_price == original.exit_price
        assert restored.profit_loss == original.profit_loss
        assert restored.exit_reason == original.exit_reason


class TestPairData:
    """Tests for PairData model."""

    def test_passes_filters_all_valid(self):
        """Pair with all valid metrics passes filters."""
        pair = PairData(
            symbol="BTC/USDT",
            quote_volume=1000000.0,
            spread_ratio=0.001,
            price=50000.0,
            volatility=0.10,
            return_60m=0.5,
        )
        assert pair.passes_filters() is True

    def test_fails_spread_filter(self):
        """Pair with high spread fails filter."""
        pair = PairData(
            symbol="BTC/USDT",
            quote_volume=1000000.0,
            spread_ratio=0.01,  # > 0.005
            price=50000.0,
            volatility=0.10,
            return_60m=0.5,
        )
        assert pair.passes_filters() is False

    def test_fails_price_filter(self):
        """Pair with low price fails filter."""
        pair = PairData(
            symbol="SHIB/USDT",
            quote_volume=1000000.0,
            spread_ratio=0.001,
            price=0.0001,  # < 0.001
            volatility=0.10,
            return_60m=0.5,
        )
        assert pair.passes_filters() is False

    def test_fails_volatility_too_low(self):
        """Pair with low volatility fails filter."""
        pair = PairData(
            symbol="USDT/USD",
            quote_volume=1000000.0,
            spread_ratio=0.001,
            price=1.0,
            volatility=0.01,  # < 0.02
            return_60m=0.5,
        )
        assert pair.passes_filters() is False

    def test_fails_volatility_too_high(self):
        """Pair with high volatility fails filter."""
        pair = PairData(
            symbol="MEME/USDT",
            quote_volume=1000000.0,
            spread_ratio=0.001,
            price=1.0,
            volatility=0.60,  # > 0.50
            return_60m=0.5,
        )
        assert pair.passes_filters() is False

    def test_fails_negative_return(self):
        """Pair with negative 60m return fails filter."""
        pair = PairData(
            symbol="BTC/USDT",
            quote_volume=1000000.0,
            spread_ratio=0.001,
            price=50000.0,
            volatility=0.10,
            return_60m=-0.5,  # <= 0
        )
        assert pair.passes_filters() is False


class TestPosition:
    """Tests for Position model."""

    def test_unrealized_profit_pct_positive(self):
        """Calculate positive unrealized profit percentage."""
        position = Position(
            pair="BTC/USDT",
            entry_price=50000.0,
            current_price=52500.0,
            amount=1.0,
            stop_loss=48000.0,
        )
        assert position.unrealized_profit_pct == 5.0

    def test_unrealized_profit_pct_negative(self):
        """Calculate negative unrealized profit percentage."""
        position = Position(
            pair="BTC/USDT",
            entry_price=50000.0,
            current_price=47500.0,
            amount=1.0,
            stop_loss=48000.0,
        )
        assert position.unrealized_profit_pct == -5.0

    def test_unrealized_profit_amount(self):
        """Calculate unrealized profit in quote currency."""
        position = Position(
            pair="BTC/USDT",
            entry_price=50000.0,
            current_price=52500.0,
            amount=0.5,
            stop_loss=48000.0,
        )
        assert position.unrealized_profit == 1250.0


class TestBacktestResult:
    """Tests for BacktestResult model."""

    def test_win_rate_calculation(self):
        """Calculate win rate from trade counts."""
        result = BacktestResult(
            total_trades=100,
            winning_trades=65,
            losing_trades=35,
            total_return_pct=25.5,
            max_drawdown_pct=8.2,
            sharpe_ratio=2.1,
        )
        assert result.win_rate == 65.0

    def test_win_rate_zero_trades(self):
        """Win rate is 0 when no trades."""
        result = BacktestResult(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            total_return_pct=0.0,
            max_drawdown_pct=0.0,
            sharpe_ratio=0.0,
        )
        assert result.win_rate == 0.0

    def test_to_dict_includes_all_metrics(self):
        """to_dict includes all required metrics."""
        result = BacktestResult(
            total_trades=100,
            winning_trades=65,
            losing_trades=35,
            total_return_pct=25.5,
            max_drawdown_pct=8.2,
            sharpe_ratio=2.1,
        )
        data = result.to_dict()
        
        assert "total_trades" in data
        assert "winning_trades" in data
        assert "losing_trades" in data
        assert "win_rate" in data
        assert "total_return_pct" in data
        assert "max_drawdown_pct" in data
        assert "sharpe_ratio" in data
