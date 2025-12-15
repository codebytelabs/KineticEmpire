"""Tests for Telegram notification handler."""

from datetime import datetime
import pytest

from kinetic_empire.telegram.handler import (
    TelegramHandler, TelegramConfig, TradeNotification,
    StatusResponse, ProfitResponse, Command
)


class TestTradeNotifications:
    """Tests for trade notification formatting."""

    def test_buy_notification_format(self):
        """Buy notification should include all fields."""
        handler = TelegramHandler()
        
        notification = TradeNotification(
            pair="BTC/USDT",
            direction="BUY",
            price=50000.0,
            stake_amount=100.0,
            timestamp=datetime(2023, 1, 1, 12, 0, 0)
        )
        
        message = handler.format_trade_notification(notification)
        
        assert "🟢" in message
        assert "BTC/USDT" in message
        assert "BUY" in message
        assert "50,000.00" in message
        assert "100.00" in message

    def test_sell_notification_format(self):
        """Sell notification should use red emoji."""
        handler = TelegramHandler()
        
        notification = TradeNotification(
            pair="ETH/USDT",
            direction="SELL",
            price=3000.0,
            stake_amount=50.0
        )
        
        message = handler.format_trade_notification(notification)
        
        assert "🔴" in message
        assert "SELL" in message

    def test_send_notification_queues_message(self):
        """Sending notification should queue message."""
        handler = TelegramHandler()
        
        notification = TradeNotification(
            pair="BTC/USDT",
            direction="BUY",
            price=50000.0,
            stake_amount=100.0
        )
        
        result = handler.send_trade_notification(notification)
        
        assert result is True
        messages = handler.get_pending_messages()
        assert len(messages) == 1

    def test_disabled_handler_doesnt_send(self):
        """Disabled handler should not send notifications."""
        config = TelegramConfig(enabled=False)
        handler = TelegramHandler(config)
        
        notification = TradeNotification(
            pair="BTC/USDT",
            direction="BUY",
            price=50000.0,
            stake_amount=100.0
        )
        
        result = handler.send_trade_notification(notification)
        
        assert result is False
        assert len(handler.get_pending_messages()) == 0


class TestStatusCommand:
    """Tests for /status command."""

    def test_status_response_format(self):
        """Status response should include all fields."""
        handler = TelegramHandler()
        
        status = StatusResponse(
            open_trades=5,
            total_unrealized_pnl=250.0,
            regime="bull",
            max_trades=20,
            flash_crash_active=False
        )
        
        message = handler.format_status_response(status)
        
        assert "5/20" in message
        assert "250.00" in message
        assert "BULL" in message
        assert "Normal" in message

    def test_status_negative_pnl(self):
        """Negative P&L should show down emoji."""
        handler = TelegramHandler()
        
        status = StatusResponse(
            open_trades=3,
            total_unrealized_pnl=-100.0,
            regime="bear",
            max_trades=3,
            flash_crash_active=False
        )
        
        message = handler.format_status_response(status)
        
        assert "📉" in message

    def test_status_flash_crash_active(self):
        """Flash crash should show warning."""
        handler = TelegramHandler()
        
        status = StatusResponse(
            open_trades=2,
            total_unrealized_pnl=0.0,
            regime="bear",
            max_trades=3,
            flash_crash_active=True
        )
        
        message = handler.format_status_response(status)
        
        assert "ACTIVE" in message
        assert "⚠️" in message


class TestProfitCommand:
    """Tests for /profit command."""

    def test_profit_response_format(self):
        """Profit response should include all fields."""
        handler = TelegramHandler()
        
        profit = ProfitResponse(
            daily_realized_pnl=500.0,
            daily_trades=10,
            daily_win_rate=70.0,
            total_realized_pnl=5000.0
        )
        
        message = handler.format_profit_response(profit)
        
        assert "500.00" in message
        assert "10" in message
        assert "70.0%" in message
        assert "5,000.00" in message

    def test_profit_negative_daily(self):
        """Negative daily P&L should show down emoji."""
        handler = TelegramHandler()
        
        profit = ProfitResponse(
            daily_realized_pnl=-200.0,
            daily_trades=5,
            daily_win_rate=40.0,
            total_realized_pnl=1000.0
        )
        
        message = handler.format_profit_response(profit)
        
        assert "📉" in message


class TestStopCommand:
    """Tests for /stop command (kill switch)."""

    def test_stop_command_sets_flag(self):
        """Stop command should set stopped flag."""
        handler = TelegramHandler()
        
        assert handler.is_stopped() is False
        
        response = handler.handle_command("/stop")
        
        assert handler.is_stopped() is True
        assert "Emergency Stop" in response

    def test_stop_callback_called(self):
        """Stop command should call callback."""
        handler = TelegramHandler()
        callback_called = [False]
        
        def on_stop():
            callback_called[0] = True
        
        handler.set_stop_callback(on_stop)
        handler.handle_command("/stop")
        
        assert callback_called[0] is True

    def test_start_command_clears_stop(self):
        """Start command should clear stopped flag."""
        handler = TelegramHandler()
        
        handler.handle_command("/stop")
        assert handler.is_stopped() is True
        
        handler.handle_command("/start")
        assert handler.is_stopped() is False


class TestCommandHandling:
    """Tests for command parsing."""

    def test_handle_status_command(self):
        """Status command should return response."""
        handler = TelegramHandler()
        
        response = handler.handle_command("/status")
        
        assert response is not None
        assert "Status" in response

    def test_handle_profit_command(self):
        """Profit command should return response."""
        handler = TelegramHandler()
        
        response = handler.handle_command("/profit")
        
        assert response is not None
        assert "Profit" in response

    def test_handle_help_command(self):
        """Help command should return commands list."""
        handler = TelegramHandler()
        
        response = handler.handle_command("/help")
        
        assert "/status" in response
        assert "/profit" in response
        assert "/stop" in response

    def test_unknown_command_returns_none(self):
        """Unknown command should return None."""
        handler = TelegramHandler()
        
        response = handler.handle_command("/unknown")
        
        assert response is None

    def test_command_case_insensitive(self):
        """Commands should be case insensitive."""
        handler = TelegramHandler()
        
        response = handler.handle_command("/STATUS")
        
        assert response is not None
