"""Property-based tests for backtesting module.

Tests validate:
- Property 28: Backtest Fee and Slippage Application
- Property 29: Backtest Report Completeness
"""

from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings
import pytest

from kinetic_empire.backtest.engine import BacktestEngine, BacktestConfig, SimulatedTrade
from kinetic_empire.models import ExitReason


class TestBacktestFeeAndSlippage:
    """Tests for Property 28: Backtest Fee and Slippage Application."""

    @given(
        price=st.floats(min_value=100, max_value=100000, allow_nan=False),
        slippage_pct=st.floats(min_value=0.01, max_value=1.0, allow_nan=False)
    )
    @settings(max_examples=50)
    def test_slippage_applied_to_entry(self, price, slippage_pct):
        """
        **Feature: kinetic-empire, Property 28: Backtest Fee and Slippage Application**
        
        *For any* simulated trade in backtest mode, realistic slippage 
        calculations SHALL be applied to entry prices.
        **Validates: Requirements 13.2**
        """
        config = BacktestConfig(slippage_pct=slippage_pct)
        engine = BacktestEngine(config)
        
        adjusted_price, slippage = engine.apply_slippage(price, is_buy=True)
        
        # Buy slippage should increase price
        assert adjusted_price > price
        assert slippage > 0
        
        # Verify slippage amount
        expected_slippage = price * (slippage_pct / 100)
        assert abs(slippage - expected_slippage) < 0.01

    @given(
        price=st.floats(min_value=100, max_value=100000, allow_nan=False),
        slippage_pct=st.floats(min_value=0.01, max_value=1.0, allow_nan=False)
    )
    @settings(max_examples=50)
    def test_slippage_applied_to_exit(self, price, slippage_pct):
        """Slippage should be applied to exit prices."""
        config = BacktestConfig(slippage_pct=slippage_pct)
        engine = BacktestEngine(config)
        
        adjusted_price, slippage = engine.apply_slippage(price, is_buy=False)
        
        # Sell slippage should decrease price
        assert adjusted_price < price
        assert slippage > 0

    @given(
        amount=st.floats(min_value=0.01, max_value=10, allow_nan=False),
        price=st.floats(min_value=100, max_value=100000, allow_nan=False),
        fee_pct=st.floats(min_value=0.01, max_value=1.0, allow_nan=False)
    )
    @settings(max_examples=50)
    def test_fee_calculation(self, amount, price, fee_pct):
        """Fee should be calculated correctly."""
        config = BacktestConfig(fee_pct=fee_pct)
        engine = BacktestEngine(config)
        
        fee = engine.calculate_fee(amount, price)
        
        expected_fee = amount * price * (fee_pct / 100)
        assert abs(fee - expected_fee) < 0.01

    def test_entry_applies_slippage_and_fee(self):
        """Entry simulation should apply both slippage and fee."""
        config = BacktestConfig(
            initial_balance=10000.0,
            slippage_pct=0.1,
            fee_pct=0.1
        )
        engine = BacktestEngine(config)
        
        trade = engine.simulate_entry(
            trade_id="test1",
            pair="BTC/USDT",
            entry_time=datetime(2023, 1, 1),
            entry_price=50000.0,
            stake_amount=1000.0
        )
        
        # Slippage should be recorded
        assert trade.slippage_entry > 0
        
        # Fee should be recorded
        assert trade.fee_entry > 0
        
        # Entry price should be adjusted
        assert trade.entry_price > 50000.0

    def test_exit_applies_slippage_and_fee(self):
        """Exit simulation should apply both slippage and fee."""
        config = BacktestConfig(
            initial_balance=10000.0,
            slippage_pct=0.1,
            fee_pct=0.1
        )
        engine = BacktestEngine(config)
        
        # Create entry
        trade = engine.simulate_entry(
            trade_id="test1",
            pair="BTC/USDT",
            entry_time=datetime(2023, 1, 1),
            entry_price=50000.0,
            stake_amount=1000.0
        )
        
        # Simulate exit
        trade = engine.simulate_exit(
            trade=trade,
            exit_time=datetime(2023, 1, 2),
            exit_price=51000.0,
            exit_reason=ExitReason.TREND_BREAK
        )
        
        # Slippage should be recorded
        assert trade.slippage_exit > 0
        
        # Fee should be recorded
        assert trade.fee_exit > 0
        
        # Exit price should be adjusted (lower due to sell slippage)
        assert trade.exit_price < 51000.0


class TestBacktestReportCompleteness:
    """Tests for Property 29: Backtest Report Completeness."""

    def test_report_includes_all_metrics(self):
        """
        **Feature: kinetic-empire, Property 29: Backtest Report Completeness**
        
        *For any* completed backtest, the report SHALL include win_rate, 
        sharpe_ratio, max_drawdown, and total_return.
        **Validates: Requirements 13.3**
        """
        engine = BacktestEngine()
        
        # Simulate some trades
        for i in range(5):
            trade = engine.simulate_entry(
                trade_id=f"trade_{i}",
                pair="BTC/USDT",
                entry_time=datetime(2023, 1, 1) + timedelta(days=i),
                entry_price=50000.0,
                stake_amount=100.0
            )
            
            # Alternate wins and losses
            exit_price = 51000.0 if i % 2 == 0 else 49000.0
            engine.simulate_exit(
                trade=trade,
                exit_time=datetime(2023, 1, 1) + timedelta(days=i, hours=1),
                exit_price=exit_price,
                exit_reason=ExitReason.TREND_BREAK
            )
        
        report = engine.generate_report()
        
        # Verify all required metrics present
        assert report.total_trades == 5
        assert report.winning_trades >= 0
        assert report.losing_trades >= 0
        assert report.winning_trades + report.losing_trades == report.total_trades
        assert hasattr(report, 'win_rate')
        assert hasattr(report, 'sharpe_ratio')
        assert hasattr(report, 'max_drawdown_pct')
        assert hasattr(report, 'total_return_pct')

    def test_report_includes_trade_list(self):
        """Report should include trade-by-trade results."""
        engine = BacktestEngine()
        
        # Simulate trades
        for i in range(3):
            trade = engine.simulate_entry(
                trade_id=f"trade_{i}",
                pair="BTC/USDT",
                entry_time=datetime(2023, 1, 1) + timedelta(days=i),
                entry_price=50000.0,
                stake_amount=100.0
            )
            
            engine.simulate_exit(
                trade=trade,
                exit_time=datetime(2023, 1, 1) + timedelta(days=i, hours=1),
                exit_price=51000.0,
                exit_reason=ExitReason.TREND_BREAK
            )
        
        report = engine.generate_report()
        
        assert len(report.trades) == 3
        for trade in report.trades:
            assert trade.id is not None
            assert trade.pair == "BTC/USDT"
            assert trade.profit_loss is not None

    def test_empty_backtest_report(self):
        """Empty backtest should return valid report."""
        engine = BacktestEngine()
        
        report = engine.generate_report()
        
        assert report.total_trades == 0
        assert report.winning_trades == 0
        assert report.losing_trades == 0
        assert report.win_rate == 0.0
        assert report.sharpe_ratio == 0.0

    def test_win_rate_calculation(self):
        """Win rate should be calculated correctly."""
        engine = BacktestEngine()
        
        # 3 wins, 2 losses
        for i in range(5):
            trade = engine.simulate_entry(
                trade_id=f"trade_{i}",
                pair="BTC/USDT",
                entry_time=datetime(2023, 1, 1) + timedelta(days=i),
                entry_price=50000.0,
                stake_amount=100.0
            )
            
            exit_price = 51000.0 if i < 3 else 49000.0
            engine.simulate_exit(
                trade=trade,
                exit_time=datetime(2023, 1, 1) + timedelta(days=i, hours=1),
                exit_price=exit_price,
                exit_reason=ExitReason.TREND_BREAK
            )
        
        report = engine.generate_report()
        
        assert report.winning_trades == 3
        assert report.losing_trades == 2
        assert report.win_rate == 60.0  # 3/5 * 100


class TestBacktestEngine:
    """Tests for backtest engine operations."""

    def test_balance_tracking(self):
        """Balance should be tracked correctly."""
        config = BacktestConfig(initial_balance=10000.0)
        engine = BacktestEngine(config)
        
        assert engine.get_balance() == 10000.0
        
        # Entry reduces balance
        trade = engine.simulate_entry(
            trade_id="test1",
            pair="BTC/USDT",
            entry_time=datetime(2023, 1, 1),
            entry_price=50000.0,
            stake_amount=1000.0
        )
        
        assert engine.get_balance() == 9000.0

    def test_drawdown_tracking(self):
        """Max drawdown should be tracked."""
        engine = BacktestEngine()
        
        # Create losing trade
        trade = engine.simulate_entry(
            trade_id="test1",
            pair="BTC/USDT",
            entry_time=datetime(2023, 1, 1),
            entry_price=50000.0,
            stake_amount=1000.0
        )
        
        engine.simulate_exit(
            trade=trade,
            exit_time=datetime(2023, 1, 2),
            exit_price=45000.0,  # 10% loss
            exit_reason=ExitReason.STOP_LOSS
        )
        
        report = engine.generate_report()
        
        assert report.max_drawdown_pct > 0

    def test_reset(self):
        """Reset should clear all state."""
        engine = BacktestEngine()
        
        # Create trade
        trade = engine.simulate_entry(
            trade_id="test1",
            pair="BTC/USDT",
            entry_time=datetime(2023, 1, 1),
            entry_price=50000.0,
            stake_amount=1000.0
        )
        
        assert len(engine.get_trades()) == 1
        
        engine.reset()
        
        assert len(engine.get_trades()) == 0
        assert engine.get_balance() == engine.config.initial_balance
