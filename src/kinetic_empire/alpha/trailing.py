"""Advanced Trailing Stop System with multiple methods.

Supports ATR-based, Supertrend, Chandelier Exit, and Profit-lock trailing.
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum
import pandas as pd
from pandas import DataFrame

from .models import RFactorPosition, TrailingMethod
from .indicators import SupertrendIndicator, ChandelierExit, SupertrendConfig, ChandelierConfig


@dataclass
class AdvancedTrailingConfig:
    """Configuration for advanced trailing stop system."""
    method: TrailingMethod = TrailingMethod.SUPERTREND
    atr_multiplier: float = 2.0
    supertrend_period: int = 10
    supertrend_multiplier: float = 3.0
    chandelier_period: int = 22
    chandelier_multiplier: float = 3.0
    profit_lock_pct: float = 0.5  # Never give back more than 50% of peak


class AdvancedTrailingSystem:
    """Advanced trailing stop system with multiple methods."""
    
    def __init__(self, config: Optional[AdvancedTrailingConfig] = None):
        self.config = config or AdvancedTrailingConfig()
        self.supertrend = SupertrendIndicator(SupertrendConfig(
            period=self.config.supertrend_period,
            multiplier=self.config.supertrend_multiplier
        ))
        self.chandelier = ChandelierExit(ChandelierConfig(
            period=self.config.chandelier_period,
            multiplier=self.config.chandelier_multiplier
        ))
    
    def calculate_atr_stop(self, current_price: float, atr: float, side: str) -> float:
        """Calculate ATR-based trailing stop.
        
        Args:
            current_price: Current market price
            atr: Current ATR value
            side: LONG or SHORT
            
        Returns:
            Stop price
        """
        if side == "LONG":
            return current_price - (self.config.atr_multiplier * atr)
        return current_price + (self.config.atr_multiplier * atr)

    
    def calculate_supertrend_stop(self, df: DataFrame, side: str) -> float:
        """Calculate Supertrend-based trailing stop.
        
        Args:
            df: OHLCV DataFrame
            side: LONG or SHORT
            
        Returns:
            Stop price
        """
        df = self.supertrend.calculate(df)
        return self.supertrend.get_stop(df, side)
    
    def calculate_chandelier_stop(self, df: DataFrame, side: str) -> float:
        """Calculate Chandelier Exit trailing stop.
        
        Args:
            df: OHLCV DataFrame
            side: LONG or SHORT
            
        Returns:
            Stop price
        """
        df = self.chandelier.calculate(df)
        return self.chandelier.get_exit(df, side)
    
    def calculate_profit_lock_stop(self, position: RFactorPosition, 
                                   current_price: float) -> float:
        """Calculate profit-lock stop (never give back more than X% of peak).
        
        Args:
            position: Current position with R-factor tracking
            current_price: Current market price
            
        Returns:
            Stop price
        """
        if position.peak_r <= 0:
            return position.stop_loss
        
        # Calculate peak profit in price terms
        peak_profit_price = position.peak_r * position.r_value
        
        # Maximum giveback allowed
        max_giveback = peak_profit_price * self.config.profit_lock_pct
        
        # Calculate stop that locks in (1 - profit_lock_pct) of peak profit
        if position.side == "LONG":
            return position.entry_price + peak_profit_price - max_giveback
        return position.entry_price - peak_profit_price + max_giveback
    
    def get_trailing_stop(self, position: RFactorPosition, df: DataFrame,
                          method: Optional[TrailingMethod] = None) -> float:
        """Get trailing stop using specified method.
        
        Args:
            position: Current position
            df: OHLCV DataFrame
            method: Trailing method (uses config default if None)
            
        Returns:
            Stop price
        """
        method = method or self.config.method
        current_price = df['close'].iloc[-1]
        atr = df['atr'].iloc[-1] if 'atr' in df.columns else 0
        
        if method == TrailingMethod.ATR:
            return self.calculate_atr_stop(current_price, atr, position.side)
        elif method == TrailingMethod.SUPERTREND:
            return self.calculate_supertrend_stop(df, position.side)
        elif method == TrailingMethod.CHANDELIER:
            return self.calculate_chandelier_stop(df, position.side)
        elif method == TrailingMethod.PROFIT_LOCK:
            return self.calculate_profit_lock_stop(position, current_price)
        
        return position.stop_loss
    
    def get_best_stop(self, position: RFactorPosition, df: DataFrame) -> float:
        """Get the most protective stop from all methods.
        
        For longs: highest stop (closest to current price)
        For shorts: lowest stop (closest to current price)
        
        Args:
            position: Current position
            df: OHLCV DataFrame
            
        Returns:
            Best stop price
        """
        current_price = df['close'].iloc[-1]
        atr = df['atr'].iloc[-1] if 'atr' in df.columns else 0
        
        stops = []
        
        # ATR stop
        stops.append(self.calculate_atr_stop(current_price, atr, position.side))
        
        # Supertrend stop
        try:
            stops.append(self.calculate_supertrend_stop(df, position.side))
        except Exception:
            pass
        
        # Chandelier stop
        try:
            stops.append(self.calculate_chandelier_stop(df, position.side))
        except Exception:
            pass
        
        # Profit-lock stop
        stops.append(self.calculate_profit_lock_stop(position, current_price))
        
        # Filter out NaN values
        stops = [s for s in stops if pd.notna(s)]
        
        if not stops:
            return position.stop_loss
        
        # For longs, highest stop is most protective
        # For shorts, lowest stop is most protective
        if position.side == "LONG":
            return max(stops)
        return min(stops)
    
    def update_stop_if_higher(self, new_stop: float, current_stop: float,
                              side: str) -> float:
        """Update stop only if it's more protective (monotonic).
        
        Args:
            new_stop: Proposed new stop
            current_stop: Current stop
            side: LONG or SHORT
            
        Returns:
            Updated stop (never less protective)
        """
        if side == "LONG":
            return max(new_stop, current_stop)
        return min(new_stop, current_stop)
