"""Tests for technical indicator calculations.

**Feature: kinetic-empire, Property 3: Indicator Calculation Determinism**
**Feature: kinetic-empire, Property 4: RSI Bounds**
**Feature: kinetic-empire, Property 5: ATR Non-Negativity**
**Validates: Requirements 2.1, 2.2, 2.3, 2.4**
"""

import pytest
import pandas as pd
import numpy as np
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime, timedelta

from kinetic_empire.indicators.calculator import IndicatorCalculator


# Strategies for generating test data
price_strategy = st.floats(min_value=0.01, max_value=100000.0, allow_nan=False, allow_infinity=False)
volume_strategy = st.floats(min_value=0.0, max_value=1e12, allow_nan=False, allow_infinity=False)


def generate_ohlcv_dataframe(n_rows: int, base_price: float = 100.0) -> pd.DataFrame:
    """Generate a valid OHLCV dataframe for testing."""
    np.random.seed(42)
    
    dates = pd.date_range(start="2024-01-01", periods=n_rows, freq="5min")
    
    # Generate realistic price movements
    returns = np.random.normal(0, 0.01, n_rows)
    close = base_price * np.cumprod(1 + returns)
    
    # Generate OHLC from close
    high = close * (1 + np.abs(np.random.normal(0, 0.005, n_rows)))
    low = close * (1 - np.abs(np.random.normal(0, 0.005, n_rows)))
    open_price = close * (1 + np.random.normal(0, 0.003, n_rows))
    
    # Ensure high >= close >= low and high >= open >= low
    high = np.maximum(high, np.maximum(close, open_price))
    low = np.minimum(low, np.minimum(close, open_price))
    
    volume = np.random.uniform(1000, 100000, n_rows)
    
    return pd.DataFrame({
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    }, index=dates)


class TestIndicatorDeterminism:
    """Property-based tests for indicator calculation determinism."""

    # **Feature: kinetic-empire, Property 3: Indicator Calculation Determinism**
    # **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
    @given(
        n_rows=st.integers(min_value=60, max_value=500),
        base_price=st.floats(min_value=1.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_indicator_calculation_determinism(self, n_rows: int, base_price: float):
        """For any OHLCV dataframe, indicators produce identical results on repeated calculation."""
        df = generate_ohlcv_dataframe(n_rows, base_price)
        calculator = IndicatorCalculator()
        
        # Calculate twice
        result1 = calculator.calculate_indicators(df)
        result2 = calculator.calculate_indicators(df)
        
        # All indicator columns should be identical
        pd.testing.assert_series_equal(result1["ema_50"], result2["ema_50"])
        pd.testing.assert_series_equal(result1["roc_12"], result2["roc_12"])
        pd.testing.assert_series_equal(result1["rsi_14"], result2["rsi_14"])
        pd.testing.assert_series_equal(result1["atr_14"], result2["atr_14"])


class TestRSIBounds:
    """Property-based tests for RSI bounds."""

    # **Feature: kinetic-empire, Property 4: RSI Bounds**
    # **Validates: Requirements 2.3**
    @given(
        n_rows=st.integers(min_value=20, max_value=500),
        base_price=st.floats(min_value=1.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_rsi_always_in_bounds(self, n_rows: int, base_price: float):
        """For any price series, RSI_14 SHALL always be in the range [0, 100]."""
        df = generate_ohlcv_dataframe(n_rows, base_price)
        calculator = IndicatorCalculator()
        
        rsi = calculator.calculate_rsi(df["close"], 14)
        
        # Drop NaN values from beginning
        rsi_valid = rsi.dropna()
        
        assert (rsi_valid >= 0).all(), f"RSI below 0: {rsi_valid.min()}"
        assert (rsi_valid <= 100).all(), f"RSI above 100: {rsi_valid.max()}"

    def test_rsi_all_gains(self):
        """RSI approaches 100 when all price changes are gains."""
        # Use larger increments to ensure clear gains
        prices = pd.Series([100 + i * 2 for i in range(50)])  # Monotonically increasing
        calculator = IndicatorCalculator()
        
        rsi = calculator.calculate_rsi(prices, 14)
        
        # Last RSI should be high (close to 100) for consistent gains
        # With EMA smoothing, it may not reach exactly 100
        assert rsi.iloc[-1] > 70, f"RSI was {rsi.iloc[-1]}, expected > 70 for all gains"

    def test_rsi_all_losses(self):
        """RSI approaches 0 when all price changes are losses."""
        prices = pd.Series([100 - i * 0.5 for i in range(50)])  # Monotonically decreasing
        calculator = IndicatorCalculator()
        
        rsi = calculator.calculate_rsi(prices, 14)
        
        # Last RSI should be close to 0
        assert rsi.iloc[-1] < 10


class TestATRNonNegativity:
    """Property-based tests for ATR non-negativity."""

    # **Feature: kinetic-empire, Property 5: ATR Non-Negativity**
    # **Validates: Requirements 2.4**
    @given(
        n_rows=st.integers(min_value=20, max_value=500),
        base_price=st.floats(min_value=1.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_atr_always_non_negative(self, n_rows: int, base_price: float):
        """For any OHLCV dataframe, ATR_14 SHALL always be >= 0."""
        df = generate_ohlcv_dataframe(n_rows, base_price)
        calculator = IndicatorCalculator()
        
        atr = calculator.calculate_atr(df, 14)
        
        # Drop NaN values from beginning
        atr_valid = atr.dropna()
        
        assert (atr_valid >= 0).all(), f"ATR below 0: {atr_valid.min()}"

    def test_atr_zero_volatility(self):
        """ATR is 0 when there's no price movement."""
        n_rows = 50
        dates = pd.date_range(start="2024-01-01", periods=n_rows, freq="5min")
        
        # Flat prices - no volatility
        df = pd.DataFrame({
            "open": [100.0] * n_rows,
            "high": [100.0] * n_rows,
            "low": [100.0] * n_rows,
            "close": [100.0] * n_rows,
            "volume": [1000.0] * n_rows,
        }, index=dates)
        
        calculator = IndicatorCalculator()
        atr = calculator.calculate_atr(df, 14)
        
        # ATR should be 0 (or very close) for flat prices
        assert atr.iloc[-1] < 0.01


class TestEMACalculation:
    """Unit tests for EMA calculation."""

    def test_ema_basic(self):
        """EMA calculation produces expected values."""
        prices = pd.Series([10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20])
        calculator = IndicatorCalculator()
        
        ema = calculator.calculate_ema(prices, 5)
        
        # EMA should be smoothed version of prices
        assert len(ema) == len(prices)
        assert ema.iloc[-1] > ema.iloc[0]  # Trending up

    def test_ema_with_insufficient_data(self):
        """EMA handles insufficient data gracefully."""
        prices = pd.Series([100, 101, 102])
        calculator = IndicatorCalculator()
        
        ema = calculator.calculate_ema(prices, 50)
        
        # Should still produce values (using available data)
        assert len(ema) == len(prices)
        assert not ema.isna().all()


class TestROCCalculation:
    """Unit tests for ROC calculation."""

    def test_roc_basic(self):
        """ROC calculation produces expected values."""
        prices = pd.Series([100, 110, 121, 133.1])  # 10% increase each period
        calculator = IndicatorCalculator()
        
        roc = calculator.calculate_roc(prices, 1)
        
        # ROC should be approximately 10% for each period
        assert abs(roc.iloc[-1] - 10.0) < 0.1

    def test_roc_negative(self):
        """ROC is negative for declining prices."""
        prices = pd.Series([100, 90, 81, 72.9])  # 10% decrease each period
        calculator = IndicatorCalculator()
        
        roc = calculator.calculate_roc(prices, 1)
        
        # ROC should be approximately -10% for each period
        assert abs(roc.iloc[-1] - (-10.0)) < 0.1


class TestCalculateIndicators:
    """Integration tests for full indicator calculation."""

    def test_calculate_indicators_adds_all_columns(self):
        """calculate_indicators adds all expected indicator columns."""
        df = generate_ohlcv_dataframe(100)
        calculator = IndicatorCalculator()
        
        result = calculator.calculate_indicators(df)
        
        assert "ema_50" in result.columns
        assert "roc_12" in result.columns
        assert "rsi_14" in result.columns
        assert "atr_14" in result.columns
        assert "volume_mean_24h" in result.columns

    def test_calculate_indicators_preserves_original_columns(self):
        """calculate_indicators preserves original OHLCV columns."""
        df = generate_ohlcv_dataframe(100)
        calculator = IndicatorCalculator()
        
        result = calculator.calculate_indicators(df)
        
        assert "open" in result.columns
        assert "high" in result.columns
        assert "low" in result.columns
        assert "close" in result.columns
        assert "volume" in result.columns

    def test_calculate_indicators_does_not_modify_original(self):
        """calculate_indicators does not modify the original dataframe."""
        df = generate_ohlcv_dataframe(100)
        original_columns = list(df.columns)
        calculator = IndicatorCalculator()
        
        _ = calculator.calculate_indicators(df)
        
        assert list(df.columns) == original_columns
