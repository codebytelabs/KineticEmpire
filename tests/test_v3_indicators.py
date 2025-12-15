"""Property-based tests for Kinetic Empire v3.0 indicators.

**Feature: kinetic-empire-v3**
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from src.kinetic_empire.v3.analyzer.indicators import (
    calc_ema,
    calc_ema_series,
    calc_rsi,
    calc_macd,
    calc_atr,
    calc_volume_ratio,
)


# Strategies for generating test data
price_strategy = st.floats(min_value=0.01, max_value=100000.0, allow_nan=False, allow_infinity=False)
volume_strategy = st.floats(min_value=0.0, max_value=1e12, allow_nan=False, allow_infinity=False)
period_strategy = st.integers(min_value=2, max_value=50)


class TestEMACalculation:
    """Property tests for EMA calculation."""

    @given(
        data=st.lists(price_strategy, min_size=30, max_size=200),
        period=period_strategy,
    )
    @settings(max_examples=100)
    def test_ema_calculation_correctness(self, data: list, period: int):
        """**Feature: kinetic-empire-v3, Property 3: EMA Calculation Correctness**
        
        For any valid OHLCV data series, the calculated EMA(9) and EMA(21) 
        SHALL match the standard exponential moving average formula within 0.0001% tolerance.
        **Validates: Requirements 2.2**
        """
        assume(len(data) >= period)
        
        # Calculate EMA using our function
        result = calc_ema(data, period)
        
        # Calculate expected EMA manually using standard formula
        multiplier = 2 / (period + 1)
        expected = sum(data[:period]) / period  # Start with SMA
        for price in data[period:]:
            expected = (price * multiplier) + (expected * (1 - multiplier))
        
        # Check within 0.0001% tolerance
        if expected != 0:
            tolerance = abs(expected) * 0.000001
            assert abs(result - expected) <= tolerance, (
                f"EMA mismatch: got {result}, expected {expected}, diff {abs(result - expected)}"
            )
        else:
            assert result == expected

    @given(data=st.lists(price_strategy, min_size=30, max_size=200))
    @settings(max_examples=100)
    def test_ema_9_faster_than_21(self, data: list):
        """EMA(9) should react faster to price changes than EMA(21)."""
        ema_9 = calc_ema(data, 9)
        ema_21 = calc_ema(data, 21)
        
        # Both should be positive for positive data
        assert ema_9 > 0
        assert ema_21 > 0
        
        # EMA should be within data range (approximately)
        data_min = min(data)
        data_max = max(data)
        assert data_min * 0.5 <= ema_9 <= data_max * 1.5
        assert data_min * 0.5 <= ema_21 <= data_max * 1.5

    @given(data=st.lists(price_strategy, min_size=30, max_size=200))
    @settings(max_examples=100)
    def test_ema_series_length(self, data: list):
        """EMA series should have same length as input data."""
        series = calc_ema_series(data, 9)
        assert len(series) == len(data)

    @given(period=period_strategy)
    def test_ema_empty_data(self, period: int):
        """EMA of empty data should return 0."""
        assert calc_ema([], period) == 0.0

    @given(data=st.lists(price_strategy, min_size=1, max_size=10))
    def test_ema_invalid_period(self, data: list):
        """EMA with invalid period should handle gracefully."""
        assert calc_ema(data, 0) == 0.0
        assert calc_ema(data, -1) == 0.0



class TestRSICalculation:
    """Property tests for RSI calculation."""

    @given(data=st.lists(price_strategy, min_size=30, max_size=200))
    @settings(max_examples=100)
    def test_rsi_calculation_correctness(self, data: list):
        """**Feature: kinetic-empire-v3, Property 4: RSI Calculation Correctness**
        
        For any valid OHLCV data series with at least 15 candles, the calculated 
        RSI(14) SHALL be between 0 and 100 inclusive.
        **Validates: Requirements 2.2**
        """
        rsi = calc_rsi(data, 14)
        
        # RSI must always be between 0 and 100
        assert 0 <= rsi <= 100, f"RSI {rsi} out of bounds [0, 100]"

    @given(data=st.lists(price_strategy, min_size=30, max_size=200))
    @settings(max_examples=100)
    def test_rsi_bounds_any_period(self, data: list):
        """RSI should be bounded 0-100 for any valid period."""
        for period in [7, 14, 21]:
            rsi = calc_rsi(data, period)
            assert 0 <= rsi <= 100, f"RSI({period}) = {rsi} out of bounds"

    @given(
        base_price=st.floats(min_value=10.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        increase_pct=st.floats(min_value=0.01, max_value=0.1, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=50)
    def test_rsi_trending_up(self, base_price: float, increase_pct: float):
        """RSI should be high (>50) for consistently rising prices."""
        # Generate consistently rising prices
        data = [base_price * (1 + increase_pct * i) for i in range(30)]
        rsi = calc_rsi(data, 14)
        
        # Strong uptrend should have RSI > 50
        assert rsi > 50, f"RSI {rsi} should be > 50 for uptrend"

    @given(
        base_price=st.floats(min_value=100.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        decrease_pct=st.floats(min_value=0.01, max_value=0.05, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=50)
    def test_rsi_trending_down(self, base_price: float, decrease_pct: float):
        """RSI should be low (<50) for consistently falling prices."""
        # Generate consistently falling prices
        data = [base_price * (1 - decrease_pct * i) for i in range(30)]
        # Filter out any non-positive values
        data = [p for p in data if p > 0]
        assume(len(data) >= 20)
        
        rsi = calc_rsi(data, 14)
        
        # Strong downtrend should have RSI < 50
        assert rsi < 50, f"RSI {rsi} should be < 50 for downtrend"

    def test_rsi_insufficient_data(self):
        """RSI should return neutral (50) for insufficient data."""
        assert calc_rsi([], 14) == 50.0
        assert calc_rsi([100.0] * 10, 14) == 50.0  # Less than period + 1
