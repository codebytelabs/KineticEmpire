"""Data models for Profitable Trading Overhaul.

Defines enums and dataclasses for the trading system.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class MarketRegime(Enum):
    """Market regime classification based on ADX."""
    TRENDING = "trending"   # ADX > 25
    SIDEWAYS = "sideways"   # 15 <= ADX <= 25
    CHOPPY = "choppy"       # ADX < 15


class TrendDirection(Enum):
    """Trend direction based on price vs MA."""
    BULLISH = "bullish"   # Price > 50-MA
    BEARISH = "bearish"   # Price < 50-MA
    NEUTRAL = "neutral"   # At MA


@dataclass
class RegimeAnalysis:
    """Result of regime detection.
    
    Attributes:
        regime: Market regime classification
        trend_direction: Bullish/bearish based on price vs MA
        adx_value: Raw ADX value
        price_vs_ma: Percentage above/below 50-MA
    """
    regime: MarketRegime
    trend_direction: TrendDirection
    adx_value: float
    price_vs_ma: float  # % above/below MA


@dataclass
class PositionSizeResult:
    """Result of position size calculation.
    
    Attributes:
        size_pct: Position size as percentage of portfolio (5-15%)
        size_usd: Position size in USD
        confidence_tier: Classification of confidence level
        is_rejected: Whether the trade was rejected
        rejection_reason: Why rejected (if applicable)
    """
    size_pct: float
    size_usd: float
    confidence_tier: str
    is_rejected: bool = False
    rejection_reason: Optional[str] = None


@dataclass
class StopLossResult:
    """Result of ATR-based stop loss calculation.
    
    Attributes:
        stop_price: Absolute stop loss price
        stop_pct: Stop loss as percentage of entry
        atr_multiplier: Multiplier used (2.0, 2.5, or 3.0)
        atr_value: Raw ATR value used
    """
    stop_price: float
    stop_pct: float
    atr_multiplier: float
    atr_value: float


@dataclass
class RiskParameters:
    """Complete risk parameters for a trade.
    
    Attributes:
        position_size_pct: Position size as % of portfolio (5-15%)
        position_size_usd: Position size in USD
        leverage: Leverage multiplier (2-10)
        stop_loss_pct: Stop loss percentage
        stop_loss_price: Absolute stop loss price
        atr_value: ATR value used for calculations
    """
    position_size_pct: float
    position_size_usd: float
    leverage: int
    stop_loss_pct: float
    stop_loss_price: float
    atr_value: float


@dataclass
class TrailingState:
    """State of trailing stop for a position.
    
    Attributes:
        is_active: Whether trailing stop is active (profit >= 2%)
        peak_price: Highest price reached (for LONG) or lowest (for SHORT)
        peak_profit_pct: Peak profit percentage reached
        current_trail_distance: Current trail distance in price units
        trail_multiplier: ATR multiplier for trail (1.0 or 1.5)
    """
    is_active: bool
    peak_price: float
    peak_profit_pct: float
    current_trail_distance: float
    trail_multiplier: float = 1.5


@dataclass
class PendingEntry:
    """Pending entry awaiting confirmation.
    
    Attributes:
        symbol: Trading symbol
        direction: LONG or SHORT
        signal_price: Price when signal was generated
        signal_time: When signal was generated
        confirmation_candles: Number of candles to wait
        candles_elapsed: Candles elapsed since signal
    """
    symbol: str
    direction: str
    signal_price: float
    signal_time: datetime
    confirmation_candles: int = 2
    candles_elapsed: int = 0
