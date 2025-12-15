"""Advanced indicators for Kinetic Empire Alpha v2.0.

Includes Supertrend and Chandelier Exit for trailing stops.
"""

from dataclasses import dataclass
from typing import Optional, Tuple
import pandas as pd
from pandas import DataFrame, Series
import numpy as np


@dataclass
class SupertrendConfig:
    """Configuration for Supertrend indicator."""
    period: int = 10
    multiplier: float = 3.0


@dataclass
class ChandelierConfig:
    """Configuration for Chandelier Exit indicator."""
    period: int = 22
    multiplier: float = 3.0


class SupertrendIndicator:
    """Supertrend indicator for trend detection and trailing stops.
    
    Upper Band = HL2 + (multiplier × ATR)
    Lower Band = HL2 - (multiplier × ATR)
    """
    
    def __init__(self, config: Optional[SupertrendConfig] = None):
        self.config = config or SupertrendConfig()
    
    def calculate(self, df: DataFrame) -> DataFrame:
        """Calculate Supertrend indicator.
        
        Args:
            df: OHLCV DataFrame with 'high', 'low', 'close' columns
            
        Returns:
            DataFrame with supertrend columns added
        """
        df = df.copy()
        
        # Calculate ATR if not present
        if 'atr' not in df.columns:
            df['atr'] = self._calculate_atr(df, self.config.period)
        
        # HL2 (typical price)
        hl2 = (df['high'] + df['low']) / 2
        
        # Basic bands
        basic_upper = hl2 + (self.config.multiplier * df['atr'])
        basic_lower = hl2 - (self.config.multiplier * df['atr'])
        
        # Initialize final bands
        final_upper = basic_upper.copy()
        final_lower = basic_lower.copy()
        supertrend = pd.Series(index=df.index, dtype=float)
        direction = pd.Series(index=df.index, dtype=int)
        
        for i in range(1, len(df)):
            # Upper band: only decrease (ratchet down in downtrend)
            if basic_upper.iloc[i] < final_upper.iloc[i-1] or df['close'].iloc[i-1] > final_upper.iloc[i-1]:
                final_upper.iloc[i] = basic_upper.iloc[i]
            else:
                final_upper.iloc[i] = final_upper.iloc[i-1]
            
            # Lower band: only increase (ratchet up in uptrend)
            if basic_lower.iloc[i] > final_lower.iloc[i-1] or df['close'].iloc[i-1] < final_lower.iloc[i-1]:
                final_lower.iloc[i] = basic_lower.iloc[i]
            else:
                final_lower.iloc[i] = final_lower.iloc[i-1]

            
            # Determine trend direction
            if i == 1:
                direction.iloc[i] = 1 if df['close'].iloc[i] > final_upper.iloc[i] else -1
            else:
                prev_dir = direction.iloc[i-1]
                if prev_dir == -1 and df['close'].iloc[i] > final_upper.iloc[i-1]:
                    direction.iloc[i] = 1
                elif prev_dir == 1 and df['close'].iloc[i] < final_lower.iloc[i-1]:
                    direction.iloc[i] = -1
                else:
                    direction.iloc[i] = prev_dir
            
            # Set supertrend value based on direction
            if direction.iloc[i] == 1:
                supertrend.iloc[i] = final_lower.iloc[i]
            else:
                supertrend.iloc[i] = final_upper.iloc[i]
        
        df['supertrend'] = supertrend
        df['supertrend_direction'] = direction
        df['supertrend_upper'] = final_upper
        df['supertrend_lower'] = final_lower
        
        return df
    
    def get_stop(self, df: DataFrame, side: str) -> float:
        """Get current Supertrend stop level.
        
        Args:
            df: DataFrame with supertrend calculated
            side: LONG or SHORT
            
        Returns:
            Stop price
        """
        if 'supertrend' not in df.columns:
            df = self.calculate(df)
        return df['supertrend'].iloc[-1]
    
    def get_trend(self, df: DataFrame) -> str:
        """Get current trend direction.
        
        Args:
            df: DataFrame with supertrend calculated
            
        Returns:
            'BULLISH' or 'BEARISH'
        """
        if 'supertrend_direction' not in df.columns:
            df = self.calculate(df)
        return "BULLISH" if df['supertrend_direction'].iloc[-1] == 1 else "BEARISH"
    
    def _calculate_atr(self, df: DataFrame, period: int) -> Series:
        """Calculate ATR."""
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()


class ChandelierExit:
    """Chandelier Exit indicator for trailing stops.
    
    Long Exit = Highest High(N) - (multiplier × ATR)
    Short Exit = Lowest Low(N) + (multiplier × ATR)
    """
    
    def __init__(self, config: Optional[ChandelierConfig] = None):
        self.config = config or ChandelierConfig()
    
    def calculate(self, df: DataFrame) -> DataFrame:
        """Calculate Chandelier Exit levels.
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            DataFrame with chandelier columns added
        """
        df = df.copy()
        
        # Calculate ATR if not present
        if 'atr' not in df.columns:
            df['atr'] = self._calculate_atr(df, self.config.period)
        
        # Highest high and lowest low over period
        highest_high = df['high'].rolling(window=self.config.period).max()
        lowest_low = df['low'].rolling(window=self.config.period).min()
        
        # Chandelier exits
        df['chandelier_long'] = highest_high - (self.config.multiplier * df['atr'])
        df['chandelier_short'] = lowest_low + (self.config.multiplier * df['atr'])
        
        return df
    
    def get_long_exit(self, df: DataFrame) -> float:
        """Get Chandelier Exit for long positions."""
        if 'chandelier_long' not in df.columns:
            df = self.calculate(df)
        return df['chandelier_long'].iloc[-1]
    
    def get_short_exit(self, df: DataFrame) -> float:
        """Get Chandelier Exit for short positions."""
        if 'chandelier_short' not in df.columns:
            df = self.calculate(df)
        return df['chandelier_short'].iloc[-1]
    
    def get_exit(self, df: DataFrame, side: str) -> float:
        """Get Chandelier Exit for given side."""
        if side == "LONG":
            return self.get_long_exit(df)
        return self.get_short_exit(df)
    
    def _calculate_atr(self, df: DataFrame, period: int) -> Series:
        """Calculate ATR."""
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()
