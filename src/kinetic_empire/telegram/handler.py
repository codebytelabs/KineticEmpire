"""Telegram notification and control handler.

Provides trade notifications and bot control via Telegram commands.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Callable
from enum import Enum


class Command(Enum):
    """Telegram command types."""
    STATUS = "/status"
    PROFIT = "/profit"
    STOP = "/stop"
    START = "/start"
    HELP = "/help"


@dataclass
class TelegramConfig:
    """Configuration for Telegram integration."""
    bot_token: str = ""
    chat_id: str = ""
    enabled: bool = True


@dataclass
class TradeNotification:
    """Trade notification data."""
    pair: str
    direction: str  # "BUY" or "SELL"
    price: float
    stake_amount: float
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class StatusResponse:
    """Status command response data."""
    open_trades: int
    total_unrealized_pnl: float
    regime: str
    max_trades: int
    flash_crash_active: bool


@dataclass
class ProfitResponse:
    """Profit command response data."""
    daily_realized_pnl: float
    daily_trades: int
    daily_win_rate: float
    total_realized_pnl: float


class TelegramHandler:
    """Handles Telegram notifications and commands.
    
    Provides:
    - Trade execution notifications
    - /status command for open trades
    - /profit command for daily P&L
    - /stop command for emergency kill switch
    """
    
    def __init__(self, config: Optional[TelegramConfig] = None):
        """Initialize Telegram handler.
        
        Args:
            config: Telegram configuration
        """
        self.config = config or TelegramConfig()
        self._is_stopped = False
        self._message_queue: list[str] = []
        self._on_stop_callback: Optional[Callable] = None
    
    def format_trade_notification(self, notification: TradeNotification) -> str:
        """Format trade notification message.
        
        Args:
            notification: Trade notification data
            
        Returns:
            Formatted message string
        """
        emoji = "🟢" if notification.direction == "BUY" else "🔴"
        
        return (
            f"{emoji} Trade Executed\n"
            f"Pair: {notification.pair}\n"
            f"Direction: {notification.direction}\n"
            f"Price: ${notification.price:,.2f}\n"
            f"Stake: ${notification.stake_amount:,.2f}\n"
            f"Time: {notification.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        )
    
    def format_status_response(self, status: StatusResponse) -> str:
        """Format status command response.
        
        Args:
            status: Status data
            
        Returns:
            Formatted message string
        """
        pnl_emoji = "📈" if status.total_unrealized_pnl >= 0 else "📉"
        crash_status = "⚠️ ACTIVE" if status.flash_crash_active else "✅ Normal"
        
        return (
            f"📊 Bot Status\n"
            f"Open Trades: {status.open_trades}/{status.max_trades}\n"
            f"Unrealized P&L: {pnl_emoji} ${status.total_unrealized_pnl:,.2f}\n"
            f"Regime: {status.regime.upper()}\n"
            f"Flash Crash: {crash_status}"
        )
    
    def format_profit_response(self, profit: ProfitResponse) -> str:
        """Format profit command response.
        
        Args:
            profit: Profit data
            
        Returns:
            Formatted message string
        """
        daily_emoji = "📈" if profit.daily_realized_pnl >= 0 else "📉"
        total_emoji = "📈" if profit.total_realized_pnl >= 0 else "📉"
        
        return (
            f"💰 Profit Summary\n"
            f"Daily P&L: {daily_emoji} ${profit.daily_realized_pnl:,.2f}\n"
            f"Daily Trades: {profit.daily_trades}\n"
            f"Daily Win Rate: {profit.daily_win_rate:.1f}%\n"
            f"Total P&L: {total_emoji} ${profit.total_realized_pnl:,.2f}"
        )
    
    def send_trade_notification(self, notification: TradeNotification) -> bool:
        """Send trade execution notification.
        
        Args:
            notification: Trade notification data
            
        Returns:
            True if sent successfully
        """
        if not self.config.enabled:
            return False
        
        message = self.format_trade_notification(notification)
        self._message_queue.append(message)
        
        # In real implementation, would send via Telegram API
        return True
    
    def handle_command(self, command: str) -> Optional[str]:
        """Handle incoming Telegram command.
        
        Args:
            command: Command string
            
        Returns:
            Response message or None
        """
        command = command.strip().lower()
        
        if command == Command.STATUS.value:
            return self._handle_status()
        elif command == Command.PROFIT.value:
            return self._handle_profit()
        elif command == Command.STOP.value:
            return self._handle_stop()
        elif command == Command.START.value:
            return self._handle_start()
        elif command == Command.HELP.value:
            return self._handle_help()
        
        return None
    
    def _handle_status(self) -> str:
        """Handle /status command.
        
        Returns:
            Status response message
        """
        # In real implementation, would fetch actual data
        return "Status command received. Fetching data..."
    
    def _handle_profit(self) -> str:
        """Handle /profit command.
        
        Returns:
            Profit response message
        """
        # In real implementation, would fetch actual data
        return "Profit command received. Fetching data..."
    
    def _handle_stop(self) -> str:
        """Handle /stop command (emergency kill switch).
        
        Returns:
            Confirmation message
        """
        self._is_stopped = True
        
        if self._on_stop_callback:
            self._on_stop_callback()
        
        return "🛑 Emergency Stop Activated\nAll new signal processing halted."
    
    def _handle_start(self) -> str:
        """Handle /start command.
        
        Returns:
            Welcome message
        """
        self._is_stopped = False
        
        return (
            "🚀 Kinetic Empire Bot\n"
            "Commands:\n"
            "/status - View open trades\n"
            "/profit - View daily P&L\n"
            "/stop - Emergency stop\n"
            "/help - Show this message"
        )
    
    def _handle_help(self) -> str:
        """Handle /help command.
        
        Returns:
            Help message
        """
        return self._handle_start()
    
    def is_stopped(self) -> bool:
        """Check if bot is stopped via kill switch.
        
        Returns:
            True if stopped
        """
        return self._is_stopped
    
    def set_stop_callback(self, callback: Callable) -> None:
        """Set callback for stop command.
        
        Args:
            callback: Function to call on stop
        """
        self._on_stop_callback = callback
    
    def get_pending_messages(self) -> list[str]:
        """Get pending messages in queue.
        
        Returns:
            List of pending messages
        """
        messages = self._message_queue.copy()
        self._message_queue.clear()
        return messages
