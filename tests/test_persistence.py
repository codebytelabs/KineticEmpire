"""Property-based tests for trade persistence.

Tests validate:
- Property 23: Trade Persistence Completeness
- Property 24: Trade Query Filtering
"""

from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings
import pytest
import tempfile
import os

from kinetic_empire.models import Trade, TradeOpen, TradeClose, Regime, ExitReason
from kinetic_empire.persistence import TradePersistence


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    db = TradePersistence(path)
    
    yield db
    
    # Cleanup
    try:
        os.unlink(path)
    except:
        pass


@st.composite
def trade_open_strategy(draw):
    """Generate random TradeOpen."""
    return TradeOpen(
        id=draw(st.text(min_size=8, max_size=16, alphabet="abcdef0123456789")),
        timestamp=draw(st.datetimes(
            min_value=datetime(2020, 1, 1),
            max_value=datetime(2024, 1, 1)
        )),
        pair=draw(st.sampled_from(["BTC/USDT", "ETH/USDT", "SOL/USDT"])),
        entry_price=draw(st.floats(min_value=100, max_value=100000, allow_nan=False)),
        stake_amount=draw(st.floats(min_value=10, max_value=1000, allow_nan=False)),
        regime=draw(st.sampled_from(list(Regime))),
        stop_loss=draw(st.floats(min_value=90, max_value=99000, allow_nan=False)),
        amount=draw(st.floats(min_value=0.001, max_value=10, allow_nan=False))
    )


@st.composite
def trade_close_strategy(draw, trade_id: str):
    """Generate random TradeClose for a trade."""
    return TradeClose(
        trade_id=trade_id,
        timestamp=draw(st.datetimes(
            min_value=datetime(2020, 1, 2),
            max_value=datetime(2024, 1, 2)
        )),
        exit_price=draw(st.floats(min_value=100, max_value=100000, allow_nan=False)),
        profit_loss=draw(st.floats(min_value=-500, max_value=500, allow_nan=False)),
        exit_reason=draw(st.sampled_from(list(ExitReason)))
    )


class TestTradePersistenceCompleteness:
    """Tests for Property 23: Trade Persistence Completeness."""

    @given(trade_open=trade_open_strategy())
    @settings(max_examples=50)
    def test_trade_open_fields_persisted(self, trade_open):
        """
        **Feature: kinetic-empire, Property 23: Trade Persistence Completeness**
        
        *For any* trade, when opened: timestamp, pair, entry_price, stake_amount, 
        and regime SHALL be persisted.
        **Validates: Requirements 10.1**
        """
        # Create temp db for this test
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        
        try:
            temp_db = TradePersistence(path)
            
            # Save trade
            temp_db.save_trade_open(trade_open)
            
            # Retrieve trade
            trades = temp_db.get_trades_by_pair(trade_open.pair, closed_only=False)
            
            assert len(trades) == 1
            retrieved = trades[0]
            
            # Verify all required fields
            assert retrieved.id == trade_open.id
            assert retrieved.pair == trade_open.pair
            assert retrieved.entry_timestamp == trade_open.timestamp
            assert abs(retrieved.entry_price - trade_open.entry_price) < 1e-10
            assert abs(retrieved.stake_amount - trade_open.stake_amount) < 1e-10
            assert retrieved.regime == trade_open.regime
            assert abs(retrieved.stop_loss - trade_open.stop_loss) < 1e-10
        finally:
            try:
                os.unlink(path)
            except:
                pass

    def test_trade_close_fields_persisted(self, temp_db):
        """
        **Feature: kinetic-empire, Property 23: Trade Persistence Completeness**
        
        *For any* trade, when closed: exit_timestamp, exit_price, profit_loss, 
        and exit_reason SHALL be persisted.
        **Validates: Requirements 10.2**
        """
        # Create and save open trade
        trade_open = TradeOpen(
            id="test123",
            timestamp=datetime(2023, 1, 1),
            pair="BTC/USDT",
            entry_price=50000.0,
            stake_amount=100.0,
            regime=Regime.BULL,
            stop_loss=48000.0,
            amount=0.002
        )
        temp_db.save_trade_open(trade_open)
        
        # Close trade
        trade_close = TradeClose(
            trade_id="test123",
            timestamp=datetime(2023, 1, 2),
            exit_price=51000.0,
            profit_loss=20.0,
            exit_reason=ExitReason.TREND_BREAK
        )
        temp_db.save_trade_close(trade_close)
        
        # Retrieve trade
        trades = temp_db.get_trades_by_pair("BTC/USDT")
        
        assert len(trades) == 1
        retrieved = trades[0]
        
        # Verify close fields
        assert retrieved.exit_timestamp == trade_close.timestamp
        assert abs(retrieved.exit_price - trade_close.exit_price) < 1e-10
        assert abs(retrieved.profit_loss - trade_close.profit_loss) < 1e-10
        assert retrieved.exit_reason == trade_close.exit_reason


class TestTradeQueryFiltering:
    """Tests for Property 24: Trade Query Filtering."""

    def test_filter_by_pair(self, temp_db):
        """
        **Feature: kinetic-empire, Property 24: Trade Query Filtering**
        
        *For any* query by pair, returned trades SHALL match the filter criteria exactly.
        **Validates: Requirements 10.3**
        """
        # Create trades for different pairs
        for i, pair in enumerate(["BTC/USDT", "ETH/USDT", "SOL/USDT"]):
            trade = TradeOpen(
                id=f"trade_{i}",
                timestamp=datetime(2023, 1, 1) + timedelta(hours=i),
                pair=pair,
                entry_price=1000.0,
                stake_amount=100.0,
                regime=Regime.BULL,
                stop_loss=950.0,
                amount=0.1
            )
            temp_db.save_trade_open(trade)
        
        # Query for BTC/USDT
        btc_trades = temp_db.get_trades_by_pair("BTC/USDT", closed_only=False)
        
        assert len(btc_trades) == 1
        assert all(t.pair == "BTC/USDT" for t in btc_trades)

    def test_filter_by_date_range(self, temp_db):
        """Query by date range should return only trades in range."""
        # Create trades at different times
        for i in range(5):
            trade = TradeOpen(
                id=f"trade_{i}",
                timestamp=datetime(2023, 1, 1) + timedelta(days=i),
                pair="BTC/USDT",
                entry_price=1000.0,
                stake_amount=100.0,
                regime=Regime.BULL,
                stop_loss=950.0,
                amount=0.1
            )
            temp_db.save_trade_open(trade)
        
        # Query for middle 3 days
        start = datetime(2023, 1, 2)
        end = datetime(2023, 1, 4)
        
        trades = temp_db.get_trades_by_date_range(start, end)
        
        assert len(trades) == 3
        assert all(start <= t.entry_timestamp <= end for t in trades)

    def test_filter_by_outcome(self, temp_db):
        """Query by outcome should return only winning or losing trades."""
        # Create winning and losing trades
        for i in range(4):
            is_winner = i % 2 == 0
            profit = 50.0 if is_winner else -30.0
            
            trade_open = TradeOpen(
                id=f"trade_{i}",
                timestamp=datetime(2023, 1, 1) + timedelta(hours=i),
                pair="BTC/USDT",
                entry_price=1000.0,
                stake_amount=100.0,
                regime=Regime.BULL,
                stop_loss=950.0,
                amount=0.1
            )
            temp_db.save_trade_open(trade_open)
            
            trade_close = TradeClose(
                trade_id=f"trade_{i}",
                timestamp=datetime(2023, 1, 1) + timedelta(hours=i+1),
                exit_price=1000.0 + profit,
                profit_loss=profit,
                exit_reason=ExitReason.TREND_BREAK
            )
            temp_db.save_trade_close(trade_close)
        
        # Query winners
        winners = temp_db.get_trades_by_outcome(is_winner=True)
        assert len(winners) == 2
        assert all(t.is_winner for t in winners)
        
        # Query losers
        losers = temp_db.get_trades_by_outcome(is_winner=False)
        assert len(losers) == 2
        assert all(not t.is_winner for t in losers)

    def test_filter_by_pair_and_outcome(self, temp_db):
        """Combined filters should work correctly."""
        # Create trades for different pairs with different outcomes
        for pair in ["BTC/USDT", "ETH/USDT"]:
            for i in range(2):
                is_winner = i == 0
                profit = 50.0 if is_winner else -30.0
                
                trade_open = TradeOpen(
                    id=f"{pair}_{i}",
                    timestamp=datetime(2023, 1, 1) + timedelta(hours=i),
                    pair=pair,
                    entry_price=1000.0,
                    stake_amount=100.0,
                    regime=Regime.BULL,
                    stop_loss=950.0,
                    amount=0.1
                )
                temp_db.save_trade_open(trade_open)
                
                trade_close = TradeClose(
                    trade_id=f"{pair}_{i}",
                    timestamp=datetime(2023, 1, 1) + timedelta(hours=i+1),
                    exit_price=1000.0 + profit,
                    profit_loss=profit,
                    exit_reason=ExitReason.TREND_BREAK
                )
                temp_db.save_trade_close(trade_close)
        
        # Query BTC winners
        btc_winners = temp_db.get_trades_by_outcome(is_winner=True, pair="BTC/USDT")
        
        assert len(btc_winners) == 1
        assert btc_winners[0].pair == "BTC/USDT"
        assert btc_winners[0].is_winner

    def test_limit_parameter(self, temp_db):
        """Limit parameter should restrict result count."""
        # Create 10 trades
        for i in range(10):
            trade = TradeOpen(
                id=f"trade_{i}",
                timestamp=datetime(2023, 1, 1) + timedelta(hours=i),
                pair="BTC/USDT",
                entry_price=1000.0,
                stake_amount=100.0,
                regime=Regime.BULL,
                stop_loss=950.0,
                amount=0.1
            )
            temp_db.save_trade_open(trade)
        
        # Query with limit
        trades = temp_db.get_trades_by_pair("BTC/USDT", limit=5, closed_only=False)
        
        assert len(trades) == 5

    def test_closed_only_filter(self, temp_db):
        """closed_only parameter should filter open trades."""
        # Create open and closed trades
        for i in range(4):
            trade_open = TradeOpen(
                id=f"trade_{i}",
                timestamp=datetime(2023, 1, 1) + timedelta(hours=i),
                pair="BTC/USDT",
                entry_price=1000.0,
                stake_amount=100.0,
                regime=Regime.BULL,
                stop_loss=950.0,
                amount=0.1
            )
            temp_db.save_trade_open(trade_open)
            
            # Close only even trades
            if i % 2 == 0:
                trade_close = TradeClose(
                    trade_id=f"trade_{i}",
                    timestamp=datetime(2023, 1, 1) + timedelta(hours=i+1),
                    exit_price=1050.0,
                    profit_loss=50.0,
                    exit_reason=ExitReason.TREND_BREAK
                )
                temp_db.save_trade_close(trade_close)
        
        # Query closed only
        closed_trades = temp_db.get_trades_by_pair("BTC/USDT", closed_only=True)
        assert len(closed_trades) == 2
        assert all(t.is_closed for t in closed_trades)
        
        # Query all
        all_trades = temp_db.get_trades_by_pair("BTC/USDT", closed_only=False)
        assert len(all_trades) == 4


class TestDatabaseOperations:
    """Tests for database operations."""

    def test_delete_trade(self, temp_db):
        """Delete should remove trade from database."""
        trade = TradeOpen(
            id="test123",
            timestamp=datetime(2023, 1, 1),
            pair="BTC/USDT",
            entry_price=50000.0,
            stake_amount=100.0,
            regime=Regime.BULL,
            stop_loss=48000.0,
            amount=0.002
        )
        temp_db.save_trade_open(trade)
        
        # Verify exists
        trades = temp_db.get_trades_by_pair("BTC/USDT", closed_only=False)
        assert len(trades) == 1
        
        # Delete
        deleted = temp_db.delete_trade("test123")
        assert deleted is True
        
        # Verify deleted
        trades = temp_db.get_trades_by_pair("BTC/USDT", closed_only=False)
        assert len(trades) == 0

    def test_clear_all_trades(self, temp_db):
        """Clear should remove all trades."""
        # Create multiple trades
        for i in range(5):
            trade = TradeOpen(
                id=f"trade_{i}",
                timestamp=datetime(2023, 1, 1) + timedelta(hours=i),
                pair="BTC/USDT",
                entry_price=1000.0,
                stake_amount=100.0,
                regime=Regime.BULL,
                stop_loss=950.0,
                amount=0.1
            )
            temp_db.save_trade_open(trade)
        
        # Verify exists
        trades = temp_db.get_all_trades()
        assert len(trades) == 5
        
        # Clear
        temp_db.clear_all_trades()
        
        # Verify empty
        trades = temp_db.get_all_trades()
        assert len(trades) == 0
