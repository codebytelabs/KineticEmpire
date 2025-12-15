"""Data models for Kinetic Empire Alpha v2.0 multi-strategy system."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List
import json


class TrendStrength(Enum):
    """Multi-timeframe trend classification."""
    STRONG_UPTREND = "strong_uptrend"
    WEAK_UPTREND = "weak_uptrend"
    NEUTRAL = "neutral"
    WEAK_DOWNTREND = "weak_downtrend"
    STRONG_DOWNTREND = "strong_downtrend"
    NO_TRADE = "no_trade"


class TrailingMethod(Enum):
    """Trailing stop method selection."""
    ATR = "atr"
    SUPERTREND = "supertrend"
    CHANDELIER = "chandelier"
    PROFIT_LOCK = "profit_lock"


@dataclass
class PartialExit:
    """Record of a partial position exit."""
    r_level: float
    percentage: float
    exit_price: float
    exit_time: datetime
    profit: float

    def to_dict(self) -> dict:
        return {
            "r_level": self.r_level,
            "percentage": self.percentage,
            "exit_price": self.exit_price,
            "exit_time": self.exit_time.isoformat(),
            "profit": self.profit,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PartialExit":
        return cls(
            r_level=data["r_level"],
            percentage=data["percentage"],
            exit_price=data["exit_price"],
            exit_time=datetime.fromisoformat(data["exit_time"]),
            profit=data["profit"],
        )



@dataclass
class RFactorPosition:
    """Position with R-factor tracking for systematic profit management."""
    pair: str
    side: str  # LONG or SHORT
    entry_price: float
    stop_loss: float
    position_size: float
    original_size: float
    r_value: float = 0.0  # Dollar value of 1R
    current_r: float = 0.0  # Current profit in R multiples
    peak_r: float = 0.0  # Highest R achieved
    partial_exits: List[PartialExit] = field(default_factory=list)
    open_time: datetime = field(default_factory=datetime.now)
    strategy: str = ""

    def __post_init__(self):
        if self.r_value == 0.0:
            self.r_value = self._calculate_r_value()

    def _calculate_r_value(self) -> float:
        """Calculate R value (risk per unit)."""
        if self.side == "LONG":
            return abs(self.entry_price - self.stop_loss)
        return abs(self.stop_loss - self.entry_price)

    def update_current_r(self, current_price: float) -> float:
        """Update and return current R multiple."""
        if self.r_value == 0:
            return 0.0
        if self.side == "LONG":
            profit = current_price - self.entry_price
        else:
            profit = self.entry_price - current_price
        self.current_r = profit / self.r_value
        self.peak_r = max(self.peak_r, self.current_r)
        return self.current_r

    def is_risk_free(self) -> bool:
        """Check if position is risk-free (took profit at 1R+)."""
        return any(exit.r_level >= 1.0 for exit in self.partial_exits)

    def get_remaining_pct(self) -> float:
        """Get remaining position percentage after partial exits."""
        taken = sum(exit.percentage for exit in self.partial_exits)
        return max(0.0, 1.0 - taken)

    def to_dict(self) -> dict:
        return {
            "pair": self.pair,
            "side": self.side,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "position_size": self.position_size,
            "original_size": self.original_size,
            "r_value": self.r_value,
            "current_r": self.current_r,
            "peak_r": self.peak_r,
            "partial_exits": [e.to_dict() for e in self.partial_exits],
            "open_time": self.open_time.isoformat(),
            "strategy": self.strategy,
        }


@dataclass
class ArbitragePosition:
    """Delta-neutral arbitrage position for funding rate collection."""
    pair: str
    spot_entry_price: float
    futures_entry_price: float
    spot_size: float
    futures_size: float
    open_time: datetime
    funding_collected: float = 0.0
    last_funding_time: Optional[datetime] = None
    entry_funding_rate: float = 0.0

    @property
    def notional_value(self) -> float:
        """Total notional value of the position."""
        return self.spot_entry_price * self.spot_size

    @property
    def delta(self) -> float:
        """Calculate position delta (should be near 0 for neutral)."""
        spot_value = self.spot_entry_price * self.spot_size
        futures_value = self.futures_entry_price * self.futures_size
        if spot_value == 0:
            return 1.0
        return abs(spot_value - futures_value) / spot_value

    def is_delta_neutral(self, tolerance: float = 0.01) -> bool:
        """Check if position is delta-neutral within tolerance."""
        return self.delta <= tolerance

    def to_dict(self) -> dict:
        return {
            "pair": self.pair,
            "spot_entry_price": self.spot_entry_price,
            "futures_entry_price": self.futures_entry_price,
            "spot_size": self.spot_size,
            "futures_size": self.futures_size,
            "open_time": self.open_time.isoformat(),
            "funding_collected": self.funding_collected,
            "last_funding_time": self.last_funding_time.isoformat() if self.last_funding_time else None,
            "entry_funding_rate": self.entry_funding_rate,
        }



@dataclass
class Signal:
    """Trading signal from a strategy."""
    pair: str
    side: str  # LONG or SHORT
    strategy: str
    strength: TrendStrength
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    size_pct: float = 1.0  # Percentage of allocated capital
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Optional[dict] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "pair": self.pair,
            "side": self.side,
            "strategy": self.strategy,
            "strength": self.strength.value,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "size_pct": self.size_pct,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class GridLevel:
    """Single level in a grid trading setup."""
    price: float
    side: str  # BUY or SELL
    quantity: float = 0.0
    order_id: Optional[str] = None
    filled: bool = False
    fill_price: Optional[float] = None
    fill_time: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "price": self.price,
            "side": self.side,
            "quantity": self.quantity,
            "order_id": self.order_id,
            "filled": self.filled,
            "fill_price": self.fill_price,
            "fill_time": self.fill_time.isoformat() if self.fill_time else None,
        }


@dataclass
class GridState:
    """State of an active grid trading position."""
    pair: str
    center_price: float
    levels: List[GridLevel]
    allocated_capital: float
    atr_at_creation: float
    trend_at_creation: TrendStrength
    total_profit: float = 0.0
    completed_trades: int = 0
    active: bool = True
    created_at: datetime = field(default_factory=datetime.now)

    def get_active_orders(self) -> List[GridLevel]:
        """Get levels with active orders."""
        return [l for l in self.levels if l.order_id and not l.filled]

    def get_filled_levels(self) -> List[GridLevel]:
        """Get filled levels."""
        return [l for l in self.levels if l.filled]

    def profit_pct(self) -> float:
        """Calculate profit as percentage of allocated capital."""
        if self.allocated_capital == 0:
            return 0.0
        return (self.total_profit / self.allocated_capital) * 100

    def to_dict(self) -> dict:
        return {
            "pair": self.pair,
            "center_price": self.center_price,
            "levels": [l.to_dict() for l in self.levels],
            "allocated_capital": self.allocated_capital,
            "atr_at_creation": self.atr_at_creation,
            "trend_at_creation": self.trend_at_creation.value,
            "total_profit": self.total_profit,
            "completed_trades": self.completed_trades,
            "active": self.active,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class FundingData:
    """Funding rate data for a perpetual pair."""
    pair: str
    current_rate: float  # Per 8 hours
    annualized_rate: float
    next_funding_time: datetime
    avg_7d_rate: float = 0.0
    is_opportunity: bool = False
    last_updated: datetime = field(default_factory=datetime.now)

    @classmethod
    def from_rate(cls, pair: str, rate_8h: float, next_time: datetime,
                  min_rate: float = 0.0001) -> "FundingData":
        """Create FundingData from 8-hour rate."""
        annualized = rate_8h * 3 * 365  # 3 funding periods per day
        return cls(
            pair=pair,
            current_rate=rate_8h,
            annualized_rate=annualized,
            next_funding_time=next_time,
            is_opportunity=rate_8h >= min_rate,
        )

    def to_dict(self) -> dict:
        return {
            "pair": self.pair,
            "current_rate": self.current_rate,
            "annualized_rate": self.annualized_rate,
            "next_funding_time": self.next_funding_time.isoformat(),
            "avg_7d_rate": self.avg_7d_rate,
            "is_opportunity": self.is_opportunity,
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class StrategyPerformance:
    """Performance metrics for a strategy."""
    strategy_name: str
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    total_r_gained: float = 0.0
    max_drawdown: float = 0.0
    peak_equity: float = 0.0
    current_equity: float = 0.0
    daily_returns: List[float] = field(default_factory=list)

    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return self.winning_trades / self.total_trades

    @property
    def avg_r_multiple(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return self.total_r_gained / self.total_trades

    @property
    def sharpe_ratio(self) -> float:
        """Calculate Sharpe ratio from daily returns."""
        if len(self.daily_returns) < 2:
            return 0.0
        import statistics
        mean_return = statistics.mean(self.daily_returns)
        std_return = statistics.stdev(self.daily_returns)
        if std_return == 0:
            return 0.0
        # Annualized Sharpe (assuming daily returns)
        return (mean_return / std_return) * (365 ** 0.5)

    def to_dict(self) -> dict:
        return {
            "strategy_name": self.strategy_name,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "total_pnl": self.total_pnl,
            "avg_r_multiple": self.avg_r_multiple,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
        }
