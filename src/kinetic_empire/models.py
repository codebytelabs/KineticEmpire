"""Core data models for Kinetic Empire trading system."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional
import json


class Regime(Enum):
    """Market regime classification based on BTC trend."""
    BULL = "bull"
    BEAR = "bear"


class ExitReason(Enum):
    """Reason for closing a trade."""
    TREND_BREAK = "trend_break"
    STOP_LOSS = "stop_loss"
    TRAILING_STOP = "trailing_stop"
    MANUAL = "manual"
    FLASH_CRASH = "flash_crash"


@dataclass
class PairData:
    """Market data for a trading pair used in scanner filtering."""
    symbol: str
    quote_volume: float
    spread_ratio: float
    price: float
    volatility: float
    return_60m: float

    def passes_filters(
        self,
        max_spread: float = 0.005,
        min_price: float = 0.001,
        volatility_min: float = 0.02,
        volatility_max: float = 0.50,
    ) -> bool:
        """Check if pair passes all quality filters."""
        return (
            self.spread_ratio <= max_spread
            and self.price >= min_price
            and volatility_min <= self.volatility <= volatility_max
            and self.return_60m > 0
        )


@dataclass
class TradeOpen:
    """Data for an opened trade."""
    id: str
    timestamp: datetime
    pair: str
    entry_price: float
    stake_amount: float
    regime: Regime
    stop_loss: float
    amount: float = 0.0  # Quantity of base currency

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "pair": self.pair,
            "entry_price": self.entry_price,
            "stake_amount": self.stake_amount,
            "regime": self.regime.value,
            "stop_loss": self.stop_loss,
            "amount": self.amount,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TradeOpen":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            pair=data["pair"],
            entry_price=data["entry_price"],
            stake_amount=data["stake_amount"],
            regime=Regime(data["regime"]),
            stop_loss=data["stop_loss"],
            amount=data.get("amount", 0.0),
        )


@dataclass
class TradeClose:
    """Data for a closed trade."""
    trade_id: str
    timestamp: datetime
    exit_price: float
    profit_loss: float
    exit_reason: ExitReason

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "trade_id": self.trade_id,
            "timestamp": self.timestamp.isoformat(),
            "exit_price": self.exit_price,
            "profit_loss": self.profit_loss,
            "exit_reason": self.exit_reason.value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TradeClose":
        """Create from dictionary."""
        return cls(
            trade_id=data["trade_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            exit_price=data["exit_price"],
            profit_loss=data["profit_loss"],
            exit_reason=ExitReason(data["exit_reason"]),
        )


@dataclass
class Trade:
    """Complete trade record combining open and close data."""
    id: str
    pair: str
    entry_timestamp: datetime
    entry_price: float
    stake_amount: float
    regime: Regime
    stop_loss: float
    amount: float = 0.0
    exit_timestamp: Optional[datetime] = None
    exit_price: Optional[float] = None
    profit_loss: Optional[float] = None
    exit_reason: Optional[ExitReason] = None

    @property
    def is_closed(self) -> bool:
        """Check if trade is closed."""
        return self.exit_timestamp is not None

    @property
    def is_winner(self) -> Optional[bool]:
        """Check if trade was profitable. None if still open."""
        if self.profit_loss is None:
            return None
        return self.profit_loss > 0

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "pair": self.pair,
            "entry_timestamp": self.entry_timestamp.isoformat(),
            "entry_price": self.entry_price,
            "stake_amount": self.stake_amount,
            "regime": self.regime.value,
            "stop_loss": self.stop_loss,
            "amount": self.amount,
            "exit_timestamp": self.exit_timestamp.isoformat() if self.exit_timestamp else None,
            "exit_price": self.exit_price,
            "profit_loss": self.profit_loss,
            "exit_reason": self.exit_reason.value if self.exit_reason else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Trade":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            pair=data["pair"],
            entry_timestamp=datetime.fromisoformat(data["entry_timestamp"]),
            entry_price=data["entry_price"],
            stake_amount=data["stake_amount"],
            regime=Regime(data["regime"]),
            stop_loss=data["stop_loss"],
            amount=data.get("amount", 0.0),
            exit_timestamp=(
                datetime.fromisoformat(data["exit_timestamp"])
                if data.get("exit_timestamp")
                else None
            ),
            exit_price=data.get("exit_price"),
            profit_loss=data.get("profit_loss"),
            exit_reason=(
                ExitReason(data["exit_reason"]) if data.get("exit_reason") else None
            ),
        )

    def to_json(self) -> str:
        """Serialize trade to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "Trade":
        """Deserialize trade from JSON string."""
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def from_open(cls, trade_open: TradeOpen) -> "Trade":
        """Create Trade from TradeOpen."""
        return cls(
            id=trade_open.id,
            pair=trade_open.pair,
            entry_timestamp=trade_open.timestamp,
            entry_price=trade_open.entry_price,
            stake_amount=trade_open.stake_amount,
            regime=trade_open.regime,
            stop_loss=trade_open.stop_loss,
            amount=trade_open.amount,
        )

    def close(self, trade_close: TradeClose) -> "Trade":
        """Close the trade with exit data."""
        return Trade(
            id=self.id,
            pair=self.pair,
            entry_timestamp=self.entry_timestamp,
            entry_price=self.entry_price,
            stake_amount=self.stake_amount,
            regime=self.regime,
            stop_loss=self.stop_loss,
            amount=self.amount,
            exit_timestamp=trade_close.timestamp,
            exit_price=trade_close.exit_price,
            profit_loss=trade_close.profit_loss,
            exit_reason=trade_close.exit_reason,
        )


@dataclass
class Position:
    """Current open position state."""
    pair: str
    entry_price: float
    current_price: float
    amount: float
    stop_loss: float
    trailing_stop_active: bool = False
    trailing_stop_level: Optional[float] = None

    @property
    def unrealized_profit_pct(self) -> float:
        """Calculate unrealized profit percentage."""
        if self.entry_price == 0:
            return 0.0
        return ((self.current_price - self.entry_price) / self.entry_price) * 100

    @property
    def unrealized_profit(self) -> float:
        """Calculate unrealized profit in quote currency."""
        return (self.current_price - self.entry_price) * self.amount


@dataclass
class BacktestResult:
    """Results from a backtest run."""
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_return_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    trades: list[Trade] = field(default_factory=list)

    @property
    def win_rate(self) -> float:
        """Calculate win rate percentage."""
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100

    def to_dict(self) -> dict:
        """Convert to dictionary for reporting."""
        return {
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "total_return_pct": self.total_return_pct,
            "max_drawdown_pct": self.max_drawdown_pct,
            "sharpe_ratio": self.sharpe_ratio,
        }


@dataclass
class PricePoint:
    """A single price point with timestamp."""
    timestamp: datetime
    price: float

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "price": self.price,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PricePoint":
        """Create from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            price=data["price"],
        )
