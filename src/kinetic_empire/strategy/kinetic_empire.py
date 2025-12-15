"""KineticEmpire Freqtrade Strategy.

A regime-aware, self-optimizing cryptocurrency trading strategy that implements:
- Multi-timeframe momentum analysis (5m, 1h, daily)
- Dynamic position sizing via Kelly Criterion
- ATR-based stop losses and trailing stops
- Flash crash protection
"""

from typing import Optional
import pandas as pd
from pandas import DataFrame

from kinetic_empire.indicators.calculator import IndicatorCalculator
from kinetic_empire.strategy.entry import EntrySignalGenerator, EntryConfig
from kinetic_empire.strategy.exit import ExitSignalGenerator
from kinetic_empire.risk.regime import RegimeClassifier
from kinetic_empire.risk.kelly import KellyCriterionSizer, SizingConfig
from kinetic_empire.risk.stoploss import StopLossManager, StopLossConfig
from kinetic_empire.risk.trailing import TrailingStopManager, TrailingConfig
from kinetic_empire.risk.protection import FlashCrashProtection, ProtectionConfig
from kinetic_empire.models import Regime, Trade, Position, PricePoint


class KineticEmpireStrategy:
    """Main strategy class integrating all components.
    
    This class can be used standalone or integrated with Freqtrade's IStrategy.
    """
    
    # Strategy parameters
    TIMEFRAME = "5m"
    INFORMATIVE_TIMEFRAMES = ["1h", "1d"]
    
    # Indicator periods
    EMA_PERIOD = 50
    ROC_PERIOD = 12
    RSI_PERIOD = 14
    ATR_PERIOD = 14
    
    def __init__(
        self,
        entry_config: Optional[EntryConfig] = None,
        sizing_config: Optional[SizingConfig] = None,
        stoploss_config: Optional[StopLossConfig] = None,
        trailing_config: Optional[TrailingConfig] = None,
        protection_config: Optional[ProtectionConfig] = None
    ):
        """Initialize strategy with all components.
        
        Args:
            entry_config: Entry signal configuration
            sizing_config: Position sizing configuration
            stoploss_config: Stop loss configuration
            trailing_config: Trailing stop configuration
            protection_config: Flash crash protection configuration
        """
        # Initialize components
        self.indicator_calc = IndicatorCalculator()
        self.entry_generator = EntrySignalGenerator(entry_config)
        self.exit_generator = ExitSignalGenerator()
        self.regime_classifier = RegimeClassifier()
        self.kelly_sizer = KellyCriterionSizer(sizing_config)
        self.stoploss_manager = StopLossManager(stoploss_config)
        self.trailing_manager = TrailingStopManager(trailing_config)
        self.flash_protection = FlashCrashProtection(protection_config)
        
        # State
        self._trade_history: list[Trade] = []
        self._btc_prices: list[PricePoint] = []
        self._current_regime = Regime.BEAR  # Conservative default
    
    def informative_pairs(self) -> list[tuple[str, str]]:
        """Return list of informative pairs needed.
        
        Returns:
            List of (pair, timeframe) tuples
        """
        return [
            ("BTC/USDT", "1d"),  # For regime classification
            ("BTC/USDT", "1h"),  # For flash crash detection
        ]
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Calculate all indicators on the dataframe.
        
        Args:
            dataframe: OHLCV dataframe
            metadata: Pair metadata
            
        Returns:
            Dataframe with indicators added
        """
        # Calculate primary indicators
        df = self.indicator_calc.calculate_indicators(
            dataframe,
            ema_period=self.EMA_PERIOD,
            roc_period=self.ROC_PERIOD,
            rsi_period=self.RSI_PERIOD,
            atr_period=self.ATR_PERIOD
        )
        
        # Calculate 24h volume mean
        df["volume_mean_24h"] = df["volume"].rolling(window=288).mean()  # 288 5m candles = 24h
        
        return df
    
    def populate_entry_trend(
        self,
        dataframe: DataFrame,
        metadata: dict,
        open_trades: int = 0
    ) -> DataFrame:
        """Populate entry signals.
        
        Args:
            dataframe: Dataframe with indicators
            metadata: Pair metadata
            open_trades: Current number of open trades
            
        Returns:
            Dataframe with entry signals
        """
        dataframe["enter_long"] = 0
        
        # Check flash crash protection
        if self.flash_protection.is_crash_active():
            return dataframe
        
        # Get max trades based on regime
        max_trades = self.regime_classifier.get_max_trades(self._current_regime)
        
        # Check if we can open more trades
        if open_trades >= max_trades:
            return dataframe
        
        # Generate entry signals
        for i in range(len(dataframe)):
            row = dataframe.iloc[i]
            
            # Skip if missing data
            if pd.isna(row.get("ema_50")) or pd.isna(row.get("roc_12")):
                continue
            
            # Check entry conditions
            should_enter = self.entry_generator.should_enter(
                close_1h=row.get("close_1h", row["close"]),
                ema50_1h=row.get("ema50_1h", row["ema_50"]),
                close_5m=row["close"],
                ema50_5m=row["ema_50"],
                roc=row["roc_12"],
                rsi=row["rsi_14"],
                volume=row["volume"],
                mean_volume_24h=row.get("volume_mean_24h", row["volume"]),
                regime=self._current_regime,
                open_trades=open_trades
            )
            
            if should_enter:
                dataframe.loc[dataframe.index[i], "enter_long"] = 1
        
        return dataframe
    
    def populate_exit_trend(
        self,
        dataframe: DataFrame,
        metadata: dict
    ) -> DataFrame:
        """Populate exit signals.
        
        Args:
            dataframe: Dataframe with indicators
            metadata: Pair metadata
            
        Returns:
            Dataframe with exit signals
        """
        dataframe["exit_long"] = 0
        
        for i in range(len(dataframe)):
            row = dataframe.iloc[i]
            
            # Skip if missing data
            if pd.isna(row.get("ema_50")):
                continue
            
            # Check trend break
            trend_break = self.exit_generator.check_trend_break(
                close_5m=row["close"],
                ema50_5m=row["ema_50"],
                volume=row["volume"],
                mean_volume=row.get("volume_mean_24h", row["volume"])
            )
            
            if trend_break:
                dataframe.loc[dataframe.index[i], "exit_long"] = 1
        
        return dataframe
    
    def custom_stake_amount(
        self,
        pair: str,
        available_balance: float
    ) -> float:
        """Calculate stake amount using Kelly Criterion.
        
        Args:
            pair: Trading pair
            available_balance: Available balance
            
        Returns:
            Stake amount
        """
        return self.kelly_sizer.calculate_stake(
            pair=pair,
            available_balance=available_balance,
            trade_history=self._trade_history
        )
    
    def custom_stoploss(
        self,
        pair: str,
        entry_price: float,
        current_price: float,
        current_profit: float,
        atr: float,
        current_stop: Optional[float] = None
    ) -> float:
        """Calculate dynamic stop loss.
        
        Uses ATR-based initial stop, then trailing stop when profitable.
        
        Args:
            pair: Trading pair
            entry_price: Entry price
            current_price: Current price
            current_profit: Current profit percentage
            atr: Current ATR value
            current_stop: Current stop loss price
            
        Returns:
            Stop loss price
        """
        # Calculate initial stop
        initial_stop = self.stoploss_manager.calculate_stop_loss(entry_price, atr)
        
        if current_stop is None:
            return initial_stop
        
        # Check if trailing should activate
        if self.trailing_manager.should_activate(current_profit * 100):
            # Calculate trailing stop
            trailing_stop = self.trailing_manager.calculate_trailing_stop(
                current_price, atr
            )
            
            # Only update if higher
            return self.trailing_manager.update_stop_if_higher(
                trailing_stop, current_stop
            )
        
        return current_stop
    
    def update_regime(self, btc_close: float, btc_ema50: float) -> Regime:
        """Update market regime based on BTC data.
        
        Args:
            btc_close: BTC daily close price
            btc_ema50: BTC daily EMA50
            
        Returns:
            Current regime
        """
        self._current_regime = self.regime_classifier.classify(btc_close, btc_ema50)
        return self._current_regime
    
    def check_flash_crash(self, btc_prices: list[PricePoint]) -> bool:
        """Check for flash crash conditions.
        
        Args:
            btc_prices: Recent BTC price history
            
        Returns:
            True if flash crash detected
        """
        self._btc_prices = btc_prices
        return self.flash_protection.detect_flash_crash(btc_prices)
    
    def get_max_trades(self) -> int:
        """Get current max trades based on regime and protection.
        
        Returns:
            Maximum allowed open trades
        """
        if self.flash_protection.is_crash_active():
            return self.flash_protection.get_emergency_max_trades()
        
        return self.regime_classifier.get_max_trades(self._current_regime)
    
    def add_trade_to_history(self, trade: Trade) -> None:
        """Add completed trade to history.
        
        Args:
            trade: Completed trade
        """
        self._trade_history.append(trade)
    
    def get_regime_info(self) -> dict:
        """Get current regime information.
        
        Returns:
            Dict with regime details
        """
        return {
            "regime": self._current_regime.value,
            "max_trades": self.get_max_trades(),
            "flash_crash_active": self.flash_protection.is_crash_active()
        }
