"""Wave Rider Data Models and Enums.

Contains all data structures for the Wave Rider momentum scalping system:
- SpikeClassification: Volume spike severity levels
- TrendDirection: Timeframe trend direction
- MoverData: Top mover information with momentum score
- TimeframeAnalysis: Single timeframe analysis result
- MTFResult: Multi-timeframe analysis result
- WaveRiderSignal: Entry signal with all parameters
- TrailingState: Trailing stop state tracking
- WaveRiderConfig: System configuration
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional


class SpikeClassification(Enum):
    """Volume spike classification based on volume ratio thresholds."""
    NONE = "none"        # volume_ratio < 2.0
    NORMAL = "normal"    # 2.0 <= volume_ratio < 3.0
    STRONG = "strong"    # 3.0 <= volume_ratio < 5.0
    EXTREME = "extreme"  # volume_ratio >= 5.0


class TrendDirection(Enum):
    """Trend direction for a single timeframe."""
    BULLISH = "BULLISH"   # EMA_fast > EMA_slow AND price > EMA_fast
    BEARISH = "BEARISH"   # EMA_fast < EMA_slow AND price < EMA_slow
    NEUTRAL = "NEUTRAL"   # Neither bullish nor bearish


@dataclass
class OHLCV:
    """OHLCV candlestick data."""
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: int = 0


@dataclass
class MoverData:
    """Top mover data with momentum scoring.
    
    Attributes:
        symbol: Trading pair symbol (e.g., "BTCUSDT")
        price: Current price
        price_change_pct: 5-minute price change percentage
        volume_24h: 24-hour trading volume in USD
        volume_ratio: Current volume / 20-period average volume
        momentum_score: volume_ratio * abs(price_change_pct)
        spike_classification: Volume spike severity level
    """
    symbol: str
    price: float
    price_change_pct: float
    volume_24h: float
    volume_ratio: float
    momentum_score: float
    spike_classification: SpikeClassification = SpikeClassification.NONE


@dataclass
class TimeframeAnalysis:
    """Analysis result for a single timeframe.
    
    Attributes:
        timeframe: Timeframe string ("1m", "5m", "15m")
        ema_fast: 9-period EMA value
        ema_slow: 21-period EMA value
        rsi: 14-period RSI value
        vwap: Volume Weighted Average Price
        trend_direction: Classified trend direction
        price: Current price on this timeframe
    """
    timeframe: str
    ema_fast: float
    ema_slow: float
    rsi: float
    vwap: float
    trend_direction: TrendDirection
    price: float


@dataclass
class MTFResult:
    """Multi-timeframe analysis result.
    
    Attributes:
        analyses: Dict of TimeframeAnalysis keyed by timeframe
        alignment_score: 40 (1 aligned), 70 (2 aligned), or 100 (3 aligned)
        dominant_direction: Most common non-NEUTRAL direction
        price_vs_vwap: "ABOVE" or "BELOW" relative to VWAP
    """
    analyses: Dict[str, TimeframeAnalysis]
    alignment_score: int
    dominant_direction: TrendDirection
    price_vs_vwap: str  # "ABOVE" or "BELOW"


@dataclass
class WaveRiderSignal:
    """Entry signal with all trading parameters.
    
    Attributes:
        symbol: Trading pair symbol
        direction: "LONG" or "SHORT"
        volume_ratio: Volume spike ratio
        spike_classification: Volume spike severity
        alignment_score: MTF alignment score (40/70/100)
        rsi_1m: RSI on 1-minute timeframe
        position_size_pct: Position size as percentage of portfolio
        leverage: Leverage multiplier
        stop_loss_pct: Stop loss percentage from entry
        confidence_score: Overall confidence 0-100
        entry_price: Suggested entry price
    """
    symbol: str
    direction: str  # "LONG" or "SHORT"
    volume_ratio: float
    spike_classification: SpikeClassification
    alignment_score: int
    rsi_1m: float
    position_size_pct: float
    leverage: int
    stop_loss_pct: float
    confidence_score: int
    entry_price: float = 0.0


@dataclass
class TrailingState:
    """Trailing stop state for position management.
    
    Attributes:
        is_active: Whether trailing stop is active (profit >= 1%)
        peak_price: Highest (LONG) or lowest (SHORT) price since entry
        peak_profit_pct: Maximum profit percentage reached
        trail_multiplier: ATR multiplier for trail (0.8 or 0.5)
        tp1_done: Whether TP1 (30% at 1.5%) has been executed
        tp2_done: Whether TP2 (30% at 2.5%) has been executed
    """
    is_active: bool = False
    peak_price: float = 0.0
    peak_profit_pct: float = 0.0
    trail_multiplier: float = 0.8  # 0.8 initially, 0.5 at 3%+ profit
    tp1_done: bool = False
    tp2_done: bool = False


@dataclass
class WaveRiderConfig:
    """Wave Rider system configuration.
    
    All configurable parameters for the Wave Rider trading system.
    """
    # Scan settings
    scan_interval: int = 15  # seconds between market scans
    monitor_interval: int = 5  # seconds between position checks
    top_movers_limit: int = 20  # number of top movers to analyze
    min_24h_volume: float = 10_000_000  # minimum 24h volume in USD
    
    # Position limits
    max_positions: int = 5
    max_exposure: float = 0.45  # 45% max portfolio exposure
    
    # Risk management
    daily_loss_limit: float = 0.03  # 3% daily loss halt
    max_consecutive_losses: int = 2  # losses before blacklist
    blacklist_duration_minutes: int = 30
    
    # Entry thresholds
    min_volume_ratio: float = 2.0  # minimum for entry
    min_alignment_score: int = 70  # 2/3 timeframes aligned
    rsi_min: int = 25
    rsi_max: int = 75
    
    # Stop loss bounds
    stop_atr_multiplier: float = 1.5
    min_stop_pct: float = 0.005  # 0.5%
    max_stop_pct: float = 0.03  # 3%
    
    # Trailing stop settings
    trailing_activation_pct: float = 0.01  # 1% profit to activate
    initial_trail_multiplier: float = 0.8  # 0.8x ATR
    tight_trail_multiplier: float = 0.5  # 0.5x ATR at 3%+
    tight_threshold_pct: float = 0.03  # 3% profit to tighten
    
    # Take profit settings
    tp1_profit_pct: float = 0.015  # 1.5%
    tp1_close_pct: float = 0.30  # close 30%
    tp2_profit_pct: float = 0.025  # 2.5%
    tp2_close_pct: float = 0.30  # close 30%
