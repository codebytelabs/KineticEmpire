"""Configuration management for Kinetic Empire v3.0."""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class LeverageConfig:
    """Dynamic leverage configuration based on confidence score."""

    # Confidence score -> base leverage mapping
    tiers: Dict[int, int] = field(
        default_factory=lambda: {
            60: 5,   # Score 60-69 -> 5x
            70: 10,  # Score 70-79 -> 10x
            80: 15,  # Score 80-89 -> 15x
            90: 20,  # Score 90-100 -> 20x
        }
    )
    # Reduce leverage by this factor in high volatility
    high_volatility_reduction: float = 0.5
    # ATR threshold for high volatility (2x normal)
    high_volatility_atr_multiplier: float = 2.0

    def get_leverage(self, confidence: int, is_high_volatility: bool = False) -> int:
        """Get leverage for given confidence score."""
        if confidence < 60:
            return 0  # No trade
        
        # Find appropriate tier
        leverage = 5  # Default minimum
        for threshold, lev in sorted(self.tiers.items()):
            if confidence >= threshold:
                leverage = lev
        
        # Reduce in high volatility
        if is_high_volatility:
            leverage = max(2, int(leverage * self.high_volatility_reduction))
        
        return leverage


@dataclass
class PositionSizingConfig:
    """Position sizing configuration."""

    # Base risk per trade as percentage of equity
    base_risk_pct: float = 1.0
    # Risk scaling by confidence
    confidence_risk_scaling: Dict[int, float] = field(
        default_factory=lambda: {
            60: 1.0,   # Score 60-69 -> 1.0% risk
            70: 1.0,   # Score 70-79 -> 1.0% risk
            80: 1.5,   # Score 80-89 -> 1.5% risk
            90: 2.0,   # Score 90-100 -> 2.0% risk
        }
    )
    # Maximum position size as percentage of equity
    max_position_pct: float = 25.0

    def get_risk_pct(self, confidence: int) -> float:
        """Get risk percentage for given confidence score."""
        risk = self.base_risk_pct
        for threshold, r in sorted(self.confidence_risk_scaling.items()):
            if confidence >= threshold:
                risk = r
        return risk


@dataclass
class RiskConfig:
    """Risk management configuration."""

    # Maximum number of open positions
    max_positions: int = 12
    # Maximum margin usage percentage
    max_margin_usage: float = 90.0
    # Maximum daily loss percentage (pause trading)
    max_daily_loss_pct: float = 5.0
    # Maximum correlated positions (e.g., similar alts)
    max_correlated_positions: int = 3
    # Emergency close threshold - portfolio loss
    emergency_portfolio_loss_pct: float = 5.0
    # Emergency close threshold - single position loss
    emergency_position_loss_pct: float = 4.0
    # Maximum stop loss distance percentage
    max_stop_loss_pct: float = 3.0


@dataclass
class TakeProfitConfig:
    """Take profit and trailing stop configuration."""

    # Partial take profit levels: (profit_pct, close_pct)
    partial_levels: List[tuple] = field(
        default_factory=lambda: [
            (1.5, 0.40),  # At +1.5%, close 40%
            (2.5, 0.30),  # At +2.5%, close 30%
        ]
    )
    # Trailing stop activation threshold
    trailing_activation_pct: float = 1.5
    # Initial trailing distance (ATR multiplier)
    trailing_atr_multiplier: float = 1.0
    # Tightened trailing distance at higher profit
    trailing_tight_atr_multiplier: float = 0.5
    # Profit level to tighten trailing
    trailing_tight_threshold_pct: float = 3.0
    # Minimum profit to lock once trailing activated
    trailing_min_lock_pct: float = 0.5


@dataclass
class ScannerConfig:
    """Market scanner configuration."""

    # Volume spike threshold (multiplier of 20-period average)
    volume_spike_threshold: float = 1.5
    # Minimum 24h momentum (absolute percentage)
    min_momentum_pct: float = 1.0
    # Scan interval in seconds
    scan_interval: int = 60
    # Maximum hot tickers to analyze per scan
    max_hot_tickers: int = 20


@dataclass
class AnalyzerConfig:
    """Technical analyzer configuration."""

    # Timeframes to analyze (in order of importance)
    timeframes: List[str] = field(default_factory=lambda: ["4h", "1h", "15m"])
    # EMA periods
    ema_fast: int = 9
    ema_slow: int = 21
    # RSI period
    rsi_period: int = 14
    # MACD settings
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    # ATR period
    atr_period: int = 14
    # Minimum EMA spread to confirm trend
    min_ema_spread_pct: float = 0.1
    # Minimum confidence score to generate signal
    min_confidence: int = 60
    # OHLCV candles to fetch per timeframe
    ohlcv_limit: int = 50


@dataclass
class V3Config:
    """Master configuration for Kinetic Empire v3.0."""

    leverage: LeverageConfig = field(default_factory=LeverageConfig)
    position_sizing: PositionSizingConfig = field(default_factory=PositionSizingConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    take_profit: TakeProfitConfig = field(default_factory=TakeProfitConfig)
    scanner: ScannerConfig = field(default_factory=ScannerConfig)
    analyzer: AnalyzerConfig = field(default_factory=AnalyzerConfig)

    # Trading pairs to monitor (USDT and USDC)
    watchlist: List[str] = field(
        default_factory=lambda: [
            # USDT pairs - Top caps
            "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT",
            # USDT pairs - High volatility alts
            "AVAX/USDT", "DOGE/USDT", "XRP/USDT", "ADA/USDT",
            # USDT pairs - DeFi & Layer 1
            "MATIC/USDT", "DOT/USDT", "LINK/USDT", "ATOM/USDT",
            # USDT pairs - More alts
            "WIF/USDT", "SUI/USDT", "APT/USDT", "ARB/USDT",
            "OP/USDT", "INJ/USDT", "TIA/USDT", "SEI/USDT",
            # USDC pairs - Top caps
            "BTC/USDC", "ETH/USDC", "SOL/USDC",
            # USDC pairs - Alts
            "AVAX/USDC", "LINK/USDC", "MATIC/USDC",
        ]
    )

    # Position monitoring interval in seconds
    monitor_interval: int = 5

    # Correlation groups (positions in same group count toward correlation limit)
    correlation_groups: Dict[str, List[str]] = field(
        default_factory=lambda: {
            "layer1": ["SOL", "AVAX", "DOT", "ATOM", "SUI", "APT", "SEI"],
            "defi": ["LINK", "INJ", "ARB", "OP"],
            "meme": ["DOGE", "WIF"],
            "major": ["BTC", "ETH", "BNB"],
        }
    )

    def get_correlation_group(self, symbol: str) -> str:
        """Get correlation group for a symbol."""
        base = symbol.split("/")[0]
        for group, symbols in self.correlation_groups.items():
            if base in symbols:
                return group
        return "other"
