"""Technical indicator calculation module for Kinetic Empire."""

import pandas as pd
import numpy as np
from typing import Optional


class IndicatorCalculator:
    """Calculates technical indicators for trading signals."""

    def __init__(self, ema_period: int = 50, roc_period: int = 12, rsi_period: int = 14, atr_period: int = 14):
        """Initialize indicator calculator.
        
        Args:
            ema_period: Period for EMA calculation (default 50)
            roc_period: Period for ROC calculation (default 12)
            rsi_period: Period for RSI calculation (default 14)
            atr_period: Period for ATR calculation (default 14)
        """
        self.ema_period = ema_period
        self.roc_period = roc_period
        self.rsi_period = rsi_period
        self.atr_period = atr_period

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all indicators and add to dataframe.
        
        Args:
            df: DataFrame with OHLCV columns (open, high, low, close, volume)
            
        Returns:
            DataFrame with added indicator columns
        """
        df = df.copy()
        
        # EMA
        df["ema_50"] = self.calculate_ema(df["close"], self.ema_period)
        
        # ROC
        df["roc_12"] = self.calculate_roc(df["close"], self.roc_period)
        
        # RSI
        df["rsi_14"] = self.calculate_rsi(df["close"], self.rsi_period)
        
        # ATR
        df["atr_14"] = self.calculate_atr(df, self.atr_period)
        
        # Volume mean (24h = 288 5-minute candles)
        df["volume_mean_24h"] = df["volume"].rolling(window=288, min_periods=1).mean()
        
        return df

    def calculate_ema(self, series: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average.
        
        Args:
            series: Price series (typically close prices)
            period: EMA period
            
        Returns:
            Series with EMA values
        """
        return series.ewm(span=period, adjust=False).mean()

    def calculate_roc(self, series: pd.Series, period: int) -> pd.Series:
        """Calculate Rate of Change (momentum indicator).
        
        ROC = ((current - n_periods_ago) / n_periods_ago) * 100
        
        Args:
            series: Price series
            period: Lookback period
            
        Returns:
            Series with ROC values as percentages
        """
        return series.pct_change(periods=period) * 100

    def calculate_rsi(self, series: pd.Series, period: int) -> pd.Series:
        """Calculate Relative Strength Index.
        
        RSI = 100 - (100 / (1 + RS))
        where RS = Average Gain / Average Loss
        
        Args:
            series: Price series
            period: RSI period
            
        Returns:
            Series with RSI values (0-100)
        """
        delta = series.diff()
        
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        
        # Use exponential moving average for smoothing
        avg_gain = gain.ewm(span=period, adjust=False).mean()
        avg_loss = loss.ewm(span=period, adjust=False).mean()
        
        # Calculate RS, handling edge cases
        # When avg_loss is 0 (all gains), RSI should be 100
        # When avg_gain is 0 (all losses), RSI should be 0
        rsi = pd.Series(index=series.index, dtype=float)
        
        for i in range(len(series)):
            ag = avg_gain.iloc[i]
            al = avg_loss.iloc[i]
            
            if pd.isna(ag) or pd.isna(al):
                rsi.iloc[i] = np.nan
            elif al == 0:
                rsi.iloc[i] = 100.0 if ag > 0 else 50.0
            elif ag == 0:
                rsi.iloc[i] = 0.0
            else:
                rs = ag / al
                rsi.iloc[i] = 100 - (100 / (1 + rs))
        
        # Ensure bounds
        rsi = rsi.clip(0, 100)
        
        return rsi

    def calculate_atr(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Calculate Average True Range (volatility indicator).
        
        True Range = max(high - low, abs(high - prev_close), abs(low - prev_close))
        ATR = EMA of True Range
        
        Args:
            df: DataFrame with high, low, close columns
            period: ATR period
            
        Returns:
            Series with ATR values (always >= 0)
        """
        high = df["high"]
        low = df["low"]
        close = df["close"]
        prev_close = close.shift(1)
        
        # Calculate True Range components
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        
        # True Range is the maximum of the three
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # ATR is the EMA of True Range
        atr = true_range.ewm(span=period, adjust=False).mean()
        
        # Ensure non-negative
        return atr.clip(lower=0)

    def merge_informative(
        self,
        df_5m: pd.DataFrame,
        df_1h: Optional[pd.DataFrame] = None,
        df_daily: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """Merge higher timeframe data into 5-minute dataframe.
        
        Aligns 1h and daily data with 5m candles using forward fill.
        
        Args:
            df_5m: Primary 5-minute dataframe with datetime index
            df_1h: Optional 1-hour informative dataframe
            df_daily: Optional daily informative dataframe
            
        Returns:
            Merged dataframe with all timeframe data aligned
        """
        result = df_5m.copy()
        
        if df_1h is not None:
            # Calculate indicators for 1h timeframe
            df_1h = self.calculate_indicators(df_1h)
            
            # Rename columns with suffix
            df_1h_renamed = df_1h.add_suffix("_1h")
            
            # Merge using asof join (forward fill)
            if isinstance(result.index, pd.DatetimeIndex) and isinstance(df_1h_renamed.index, pd.DatetimeIndex):
                result = pd.merge_asof(
                    result.reset_index(),
                    df_1h_renamed.reset_index(),
                    left_on="index" if "index" in result.reset_index().columns else result.index.name,
                    right_on="index" if "index" in df_1h_renamed.reset_index().columns else df_1h_renamed.index.name,
                    direction="backward",
                    suffixes=("", "_1h_merge"),
                )
                result = result.set_index(result.columns[0])
            else:
                # Fallback: simple reindex with forward fill
                for col in ["close", "ema_50", "rsi_14", "roc_12", "atr_14", "volume"]:
                    if col in df_1h.columns:
                        result[f"{col}_1h"] = df_1h[col].reindex(result.index, method="ffill")

        if df_daily is not None:
            # Calculate indicators for daily timeframe
            df_daily = self.calculate_indicators(df_daily)
            
            # Rename columns with suffix
            df_daily_renamed = df_daily.add_suffix("_daily")
            
            # Merge using asof join (forward fill)
            if isinstance(result.index, pd.DatetimeIndex) and isinstance(df_daily_renamed.index, pd.DatetimeIndex):
                result = pd.merge_asof(
                    result.reset_index(),
                    df_daily_renamed.reset_index(),
                    left_on=result.index.name or "index",
                    right_on=df_daily_renamed.index.name or "index",
                    direction="backward",
                    suffixes=("", "_daily_merge"),
                )
                result = result.set_index(result.columns[0])
            else:
                # Fallback: simple reindex with forward fill
                for col in ["close", "ema_50"]:
                    if col in df_daily.columns:
                        result[f"{col}_daily"] = df_daily[col].reindex(result.index, method="ffill")

        return result

    def calculate_volatility(self, df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Calculate price volatility as standard deviation of returns.
        
        Args:
            df: DataFrame with close prices
            period: Lookback period for volatility calculation
            
        Returns:
            Series with volatility values
        """
        returns = df["close"].pct_change()
        return returns.rolling(window=period).std()

    def calculate_volume_mean(self, df: pd.DataFrame, period: int = 288) -> pd.Series:
        """Calculate rolling mean volume.
        
        Args:
            df: DataFrame with volume column
            period: Lookback period (default 288 = 24h of 5m candles)
            
        Returns:
            Series with mean volume values
        """
        return df["volume"].rolling(window=period, min_periods=1).mean()
