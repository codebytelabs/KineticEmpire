"""Core data models for Kinetic Empire v3.0."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Literal, Optional


@dataclass
class OHLCV:
    """OHLCV candle data."""

    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float

    @classmethod
    def from_list(cls, data: List) -> "OHLCV":
        """Create from Binance API format [timestamp, o, h, l, c, v]."""
        return cls(
            timestamp=data[0],
            open=float(data[1]),
            high=float(data[2]),
            low=float(data[3]),
            close=float(data[4]),
            volume=float(data[5]),
        )


@dataclass
class Indicators:
    """Technical indicators for a single timeframe."""

    ema_9: float
    ema_21: float
    rsi: float
    macd_line: float
    macd_signal: float
    macd_histogram: float
    atr: float
    volume_ratio: float  # Current volume / 20-period average

    @property
    def ema_trend(self) -> Literal["UP", "DOWN"]:
        """Determine trend direction from EMA crossover."""
        return "UP" if self.ema_9 > self.ema_21 else "DOWN"

    @property
    def ema_spread(self) -> float:
        """EMA spread as percentage."""
        if self.ema_21 == 0:
            return 0
        return (self.ema_9 - self.ema_21) / self.ema_21 * 100


@dataclass
class Ticker:
    """Market ticker data."""

    symbol: str
    price: float
    change_24h: float  # Percentage
    volume_24h: float
    high_24h: float
    low_24h: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Signal:
    """Trading signal with full analysis."""

    symbol: str
    direction: Literal["LONG", "SHORT"]
    confidence: int  # 0-100 score
    entry_price: float
    stop_loss: float
    take_profit: float
    atr: float
    timeframe_alignment: bool  # True if 4H and 1H trends match
    indicators: Dict[str, Indicators]  # Keyed by timeframe: "4h", "1h", "15m"
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def risk_distance(self) -> float:
        """Distance from entry to stop loss as percentage."""
        if self.entry_price == 0:
            return 0
        return abs(self.entry_price - self.stop_loss) / self.entry_price * 100

    @property
    def reward_distance(self) -> float:
        """Distance from entry to take profit as percentage."""
        if self.entry_price == 0:
            return 0
        return abs(self.take_profit - self.entry_price) / self.entry_price * 100

    @property
    def risk_reward_ratio(self) -> float:
        """Risk to reward ratio."""
        if self.risk_distance == 0:
            return 0
        return self.reward_distance / self.risk_distance

    def validate(self) -> bool:
        """Validate signal integrity."""
        # Stop loss must be capped at 3%
        if self.risk_distance > 3.0:
            return False
        # Confidence must be 60-100 for valid signal
        if not 60 <= self.confidence <= 100:
            return False
        # Direction must match stop/tp placement
        if self.direction == "LONG":
            if self.stop_loss >= self.entry_price or self.take_profit <= self.entry_price:
                return False
        else:  # SHORT
            if self.stop_loss <= self.entry_price or self.take_profit >= self.entry_price:
                return False
        return True


@dataclass
class Position:
    """Open position with tracking state."""

    symbol: str
    side: Literal["LONG", "SHORT"]
    entry_price: float
    size: float
    leverage: int
    stop_loss: float
    take_profit: float
    trailing_stop: Optional[float] = None
    trailing_activated: bool = False
    partial_exits: List[float] = field(default_factory=list)  # Prices where exits occurred
    peak_pnl: float = 0.0
    entry_time: datetime = field(default_factory=datetime.now)
    confidence: int = 0  # Original signal confidence

    @property
    def notional_value(self) -> float:
        """Total position value."""
        return self.entry_price * self.size

    def calc_pnl_pct(self, current_price: float) -> float:
        """Calculate current P&L percentage."""
        if self.entry_price == 0:
            return 0
        if self.side == "LONG":
            return (current_price - self.entry_price) / self.entry_price * 100
        else:  # SHORT
            return (self.entry_price - current_price) / self.entry_price * 100

    def calc_pnl_amount(self, current_price: float) -> float:
        """Calculate current P&L in quote currency."""
        pnl_pct = self.calc_pnl_pct(current_price)
        return self.notional_value * (pnl_pct / 100)

    def should_stop_loss(self, current_price: float) -> bool:
        """Check if stop loss should trigger."""
        if self.side == "LONG":
            return current_price <= self.stop_loss
        else:  # SHORT
            return current_price >= self.stop_loss

    def should_trailing_stop(self, current_price: float) -> bool:
        """Check if trailing stop should trigger."""
        if not self.trailing_activated or self.trailing_stop is None:
            return False
        if self.side == "LONG":
            return current_price <= self.trailing_stop
        else:  # SHORT
            return current_price >= self.trailing_stop

    def should_take_profit(self, current_price: float, level: int = 1) -> bool:
        """Check if take profit level should trigger.
        
        Level 1: +1.5% (close 40%)
        Level 2: +2.5% (close 30%)
        Level 3: +3.0% (trail remaining)
        """
        pnl_pct = self.calc_pnl_pct(current_price)
        thresholds = {1: 1.5, 2: 2.5, 3: 3.0}
        return pnl_pct >= thresholds.get(level, 1.5)


@dataclass
class TradeResult:
    """Completed trade result for logging."""

    symbol: str
    side: Literal["LONG", "SHORT"]
    entry_price: float
    exit_price: float
    size: float
    leverage: int
    pnl_pct: float
    pnl_amount: float
    exit_reason: str  # "STOP_LOSS", "TAKE_PROFIT", "TRAILING_STOP", "EMERGENCY"
    confidence: int
    entry_time: datetime
    exit_time: datetime = field(default_factory=datetime.now)
    duration_minutes: int = 0

    def __post_init__(self):
        if self.entry_time:
            delta = self.exit_time - self.entry_time
            self.duration_minutes = int(delta.total_seconds() / 60)
