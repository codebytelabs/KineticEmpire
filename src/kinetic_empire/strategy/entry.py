"""Entry signal generation module.

Generates BUY signals based on multi-timeframe trend alignment,
momentum conditions, and regime-based trade limits.

Enhanced with RSI Zone Optimizer for regime-specific RSI bounds.
"""

from dataclasses import dataclass
from typing import Optional

from kinetic_empire.models import Regime
from kinetic_empire.optimizations import RSIZoneOptimizer
from kinetic_empire.optimizations.config import RSIZoneConfig


@dataclass
class EntryConfig:
    """Configuration for entry signal generation."""
    roc_threshold: float = 1.5  # ROC must be > 1.5%
    rsi_min: float = 45.0       # RSI must be > 45 (legacy, overridden by optimizer)
    rsi_max: float = 65.0       # RSI must be < 65 (legacy, overridden by optimizer)
    use_rsi_optimizer: bool = True  # Use regime-specific RSI zones


@dataclass
class MarketState:
    """Current market state for entry evaluation."""
    close_1h: float
    ema50_1h: float
    close_5m: float
    ema50_5m: float
    roc_12: float
    rsi_14: float
    volume: float
    mean_volume_24h: float


class EntrySignalGenerator:
    """Generates entry signals based on multi-timeframe conditions.
    
    Entry conditions (ALL must be true):
    1. 1H close > 1H EMA50 (macro trend confirmation)
    2. 5M close > 5M EMA50 (micro trend confirmation)
    3. ROC_12 > 1.5% (velocity threshold)
    4. 45 < RSI_14 < 65 (avoiding overbought/oversold)
    5. Volume > 24H mean volume
    6. Open trades < regime limit
    """

    def __init__(self, config: Optional[EntryConfig] = None):
        """Initialize entry signal generator.
        
        Args:
            config: Entry configuration. Uses defaults if None.
        """
        self.config = config or EntryConfig()
        
        # Initialize RSI zone optimizer if enabled
        if self.config.use_rsi_optimizer:
            self._rsi_optimizer = RSIZoneOptimizer()
        else:
            self._rsi_optimizer = None

    def check_macro_trend(self, close_1h: float, ema50_1h: float) -> bool:
        """Check if 1H close is above 1H EMA50.
        
        Args:
            close_1h: 1-hour close price
            ema50_1h: 1-hour EMA50 value
            
        Returns:
            True if close_1h > ema50_1h
        """
        return close_1h > ema50_1h

    def check_micro_trend(self, close_5m: float, ema50_5m: float) -> bool:
        """Check if 5M close is above 5M EMA50.
        
        Args:
            close_5m: 5-minute close price
            ema50_5m: 5-minute EMA50 value
            
        Returns:
            True if close_5m > ema50_5m
        """
        return close_5m > ema50_5m

    def check_momentum(self, roc: float, threshold: Optional[float] = None) -> bool:
        """Check if ROC exceeds threshold.
        
        Args:
            roc: Rate of Change value (percentage)
            threshold: Minimum ROC threshold (default from config)
            
        Returns:
            True if roc > threshold
        """
        threshold = threshold if threshold is not None else self.config.roc_threshold
        return roc > threshold

    def check_pullback(
        self,
        rsi: float,
        min_rsi: Optional[float] = None,
        max_rsi: Optional[float] = None,
        regime: Optional[Regime] = None
    ) -> bool:
        """Check if RSI is in the pullback zone.
        
        If RSI optimizer is enabled and regime is provided, uses regime-specific
        RSI bounds (BULL: 35-70, BEAR: 45-60).
        
        Args:
            rsi: RSI value
            min_rsi: Minimum RSI (default from config)
            max_rsi: Maximum RSI (default from config)
            regime: Market regime for optimizer (optional)
            
        Returns:
            True if RSI is in valid range
        """
        # Use optimizer if available and regime provided
        if self._rsi_optimizer is not None and regime is not None:
            return self._rsi_optimizer.is_valid_rsi(rsi, regime)
        
        min_rsi = min_rsi if min_rsi is not None else self.config.rsi_min
        max_rsi = max_rsi if max_rsi is not None else self.config.rsi_max
        return min_rsi < rsi < max_rsi

    def check_volume(self, volume: float, mean_volume_24h: float) -> bool:
        """Check if current volume exceeds 24H mean.
        
        Args:
            volume: Current volume
            mean_volume_24h: 24-hour mean volume
            
        Returns:
            True if volume > mean_volume_24h
        """
        return volume > mean_volume_24h

    def check_trade_limit(
        self,
        regime: Regime,
        open_trades: int,
        max_trades_bull: int = 20,
        max_trades_bear: int = 3
    ) -> bool:
        """Check if trade limit allows new trade.
        
        Args:
            regime: Current market regime
            open_trades: Number of currently open trades
            max_trades_bull: Max trades in BULL regime
            max_trades_bear: Max trades in BEAR regime
            
        Returns:
            True if open_trades < regime limit
        """
        max_trades = max_trades_bull if regime == Regime.BULL else max_trades_bear
        return open_trades < max_trades


    def check_entry_conditions(
        self,
        state: MarketState,
        regime: Regime,
        open_trades: int,
        max_trades_bull: int = 20,
        max_trades_bear: int = 3
    ) -> bool:
        """Check all entry conditions.
        
        ALL conditions must be true for a BUY signal:
        1. Macro trend: 1H close > 1H EMA50
        2. Micro trend: 5M close > 5M EMA50
        3. Momentum: ROC > 1.5%
        4. Pullback: RSI in regime-specific zone (BULL: 35-70, BEAR: 45-60)
        5. Volume: current > 24H mean
        6. Trade limit: open_trades < regime limit
        
        Args:
            state: Current market state
            regime: Current market regime
            open_trades: Number of currently open trades
            max_trades_bull: Max trades in BULL regime
            max_trades_bear: Max trades in BEAR regime
            
        Returns:
            True if ALL conditions are satisfied
        """
        return (
            self.check_macro_trend(state.close_1h, state.ema50_1h)
            and self.check_micro_trend(state.close_5m, state.ema50_5m)
            and self.check_momentum(state.roc_12)
            and self.check_pullback(state.rsi_14, regime=regime)
            and self.check_volume(state.volume, state.mean_volume_24h)
            and self.check_trade_limit(regime, open_trades, max_trades_bull, max_trades_bear)
        )

    def should_enter(
        self,
        state: MarketState,
        regime: Regime,
        open_trades: int
    ) -> bool:
        """Determine if a BUY signal should be generated.
        
        Convenience method that wraps check_entry_conditions.
        
        Args:
            state: Current market state
            regime: Current market regime
            open_trades: Number of currently open trades
            
        Returns:
            True if a BUY signal should be generated
        """
        return self.check_entry_conditions(state, regime, open_trades)

    def get_entry_analysis(
        self,
        state: MarketState,
        regime: Regime,
        open_trades: int
    ) -> dict:
        """Get detailed analysis of entry conditions.
        
        Args:
            state: Current market state
            regime: Current market regime
            open_trades: Number of currently open trades
            
        Returns:
            Dictionary with each condition's result
        """
        max_trades = 20 if regime == Regime.BULL else 3
        
        return {
            "macro_trend": self.check_macro_trend(state.close_1h, state.ema50_1h),
            "micro_trend": self.check_micro_trend(state.close_5m, state.ema50_5m),
            "momentum": self.check_momentum(state.roc_12),
            "pullback": self.check_pullback(state.rsi_14),
            "volume": self.check_volume(state.volume, state.mean_volume_24h),
            "trade_limit": self.check_trade_limit(regime, open_trades),
            "all_conditions_met": self.check_entry_conditions(state, regime, open_trades),
            "regime": regime,
            "open_trades": open_trades,
            "max_trades": max_trades,
        }
