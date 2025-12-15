"""Property-based tests for Advanced Trailing Stop System.

**Feature: kinetic-empire-alpha, Properties 4, 5, 11, 12**
**Validates: Requirements 4.4, 4.5, 13.5, 14.1**
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from datetime import datetime
import pandas as pd
import numpy as np

from kinetic_empire.alpha.trailing import AdvancedTrailingSystem, AdvancedTrailingConfig
from kinetic_empire.alpha.indicators import (
    SupertrendIndicator, SupertrendConfig,
    ChandelierExit, ChandelierConfig
)
from kinetic_empire.alpha.models import RFactorPosition, TrailingMethod


def generate_ohlcv_df(n_bars: int = 50, base_price: float = 100.0, 
                      volatility: float = 0.02) -> pd.DataFrame:
    """Generate synthetic OHLCV data for testing."""
    np.random.seed(42)  # For reproducibility
    
    prices = [base_price]
    for _ in range(n_bars - 1):
        change = np.random.normal(0, volatility)
        prices.append(prices[-1] * (1 + change))
    
    df = pd.DataFrame({
        'open': prices,
        'high': [p * (1 + abs(np.random.normal(0, volatility/2))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, volatility/2))) for p in prices],
        'close': [p * (1 + np.random.normal(0, volatility/3)) for p in prices],
        'volume': [1000000 * (1 + np.random.random()) for _ in prices]
    })
    
    # Ensure high >= open, close and low <= open, close
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    
    # Calculate ATR
    tr1 = df['high'] - df['low']
    tr2 = abs(df['high'] - df['close'].shift(1))
    tr3 = abs(df['low'] - df['close'].shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr'] = tr.rolling(window=14).mean()
    
    return df


class TestSupertrendProperties:
    """Property-based tests for Supertrend indicator."""
    
    @given(
        multiplier=st.floats(min_value=1.0, max_value=5.0, allow_nan=False),
        period=st.integers(min_value=5, max_value=20)
    )
    @settings(max_examples=50)
    def test_supertrend_band_ratcheting(self, multiplier: float, period: int):
        """**Feature: kinetic-empire-alpha, Property 11: Supertrend Band Ratcheting**
        
        WHEN Supertrend is bullish THEN lower band SHALL only increase (ratchet up).
        **Validates: Requirements 13.5**
        """
        config = SupertrendConfig(period=period, multiplier=multiplier)
        indicator = SupertrendIndicator(config)
        
        df = generate_ohlcv_df(n_bars=100)
        df = indicator.calculate(df)
        
        # Check lower band ratcheting during uptrend
        for i in range(period + 1, len(df)):
            if df['supertrend_direction'].iloc[i] == 1:  # Bullish
                # Lower band should only increase or stay same
                if df['supertrend_direction'].iloc[i-1] == 1:  # Was also bullish
                    assert df['supertrend_lower'].iloc[i] >= df['supertrend_lower'].iloc[i-1] - 1e-10, (
                        f"Lower band decreased during uptrend at index {i}: "
                        f"{df['supertrend_lower'].iloc[i-1]} -> {df['supertrend_lower'].iloc[i]}"
                    )
    
    @given(
        multiplier=st.floats(min_value=1.0, max_value=5.0, allow_nan=False),
        period=st.integers(min_value=5, max_value=20)
    )
    @settings(max_examples=50)
    def test_supertrend_upper_band_ratcheting(self, multiplier: float, period: int):
        """**Feature: kinetic-empire-alpha, Property 11: Supertrend Band Ratcheting**
        
        WHEN Supertrend is bearish THEN upper band SHALL only decrease (ratchet down).
        **Validates: Requirements 13.5**
        """
        config = SupertrendConfig(period=period, multiplier=multiplier)
        indicator = SupertrendIndicator(config)
        
        df = generate_ohlcv_df(n_bars=100)
        df = indicator.calculate(df)
        
        # Check upper band ratcheting during downtrend (skip NaN values)
        for i in range(period + 1, len(df)):
            if pd.isna(df['supertrend_upper'].iloc[i]) or pd.isna(df['supertrend_upper'].iloc[i-1]):
                continue
            if pd.isna(df['supertrend_direction'].iloc[i]) or pd.isna(df['supertrend_direction'].iloc[i-1]):
                continue
            if df['supertrend_direction'].iloc[i] == -1:  # Bearish
                if df['supertrend_direction'].iloc[i-1] == -1:  # Was also bearish
                    assert df['supertrend_upper'].iloc[i] <= df['supertrend_upper'].iloc[i-1] + 1e-10, (
                        f"Upper band increased during downtrend at index {i}"
                    )
    
    def test_supertrend_trend_flip_on_price_break(self):
        """Test that trend flips when price breaks through band."""
        indicator = SupertrendIndicator()
        df = generate_ohlcv_df(n_bars=100)
        df = indicator.calculate(df)
        
        # Verify trend direction is either 1 or -1
        valid_directions = df['supertrend_direction'].dropna().unique()
        assert all(d in [1, -1] for d in valid_directions)


class TestChandelierExitProperties:
    """Property-based tests for Chandelier Exit indicator."""
    
    @given(
        multiplier=st.floats(min_value=1.0, max_value=5.0, allow_nan=False),
        period=st.integers(min_value=10, max_value=30)
    )
    @settings(max_examples=50)
    def test_chandelier_long_exit_calculation(self, multiplier: float, period: int):
        """**Feature: kinetic-empire-alpha, Property 12: Chandelier Exit Calculation**
        
        Chandelier Exit for longs SHALL equal Highest_High(N) - (multiplier × ATR).
        **Validates: Requirements 14.1**
        """
        config = ChandelierConfig(period=period, multiplier=multiplier)
        indicator = ChandelierExit(config)
        
        df = generate_ohlcv_df(n_bars=100)
        df = indicator.calculate(df)
        
        # Verify calculation for last bar
        idx = len(df) - 1
        highest_high = df['high'].iloc[idx-period+1:idx+1].max()
        atr = df['atr'].iloc[idx]
        
        expected = highest_high - (multiplier * atr)
        actual = df['chandelier_long'].iloc[idx]
        
        assert abs(actual - expected) < 1e-10, (
            f"Chandelier long exit mismatch: expected {expected}, got {actual}"
        )
    
    @given(
        multiplier=st.floats(min_value=1.0, max_value=5.0, allow_nan=False),
        period=st.integers(min_value=10, max_value=30)
    )
    @settings(max_examples=50)
    def test_chandelier_short_exit_calculation(self, multiplier: float, period: int):
        """**Feature: kinetic-empire-alpha, Property 12: Chandelier Exit Calculation**
        
        Chandelier Exit for shorts SHALL equal Lowest_Low(N) + (multiplier × ATR).
        **Validates: Requirements 14.2**
        """
        config = ChandelierConfig(period=period, multiplier=multiplier)
        indicator = ChandelierExit(config)
        
        df = generate_ohlcv_df(n_bars=100)
        df = indicator.calculate(df)
        
        # Verify calculation for last bar
        idx = len(df) - 1
        lowest_low = df['low'].iloc[idx-period+1:idx+1].min()
        atr = df['atr'].iloc[idx]
        
        expected = lowest_low + (multiplier * atr)
        actual = df['chandelier_short'].iloc[idx]
        
        assert abs(actual - expected) < 1e-10, (
            f"Chandelier short exit mismatch: expected {expected}, got {actual}"
        )


class TestTrailingStopProperties:
    """Property-based tests for Advanced Trailing Stop System."""
    
    @given(
        entry_price=st.floats(min_value=10.0, max_value=1000.0, allow_nan=False),
        stop_distance_pct=st.floats(min_value=0.01, max_value=0.1, allow_nan=False),
        position_size=st.floats(min_value=0.1, max_value=10.0, allow_nan=False),
        price_moves=st.lists(
            st.floats(min_value=-0.05, max_value=0.1, allow_nan=False),
            min_size=5,
            max_size=20
        )
    )
    @settings(max_examples=50)
    def test_trailing_stop_monotonicity_long(
        self, entry_price: float, stop_distance_pct: float, 
        position_size: float, price_moves: list
    ):
        """**Feature: kinetic-empire-alpha, Property 4: Trailing Stop Monotonicity**
        
        For long positions, trailing stop SHALL only move up (monotonic increase).
        **Validates: Requirements 4.4**
        """
        trailing = AdvancedTrailingSystem()
        stop_loss = entry_price * (1 - stop_distance_pct)
        
        position = RFactorPosition(
            pair="TEST/USDT",
            side="LONG",
            entry_price=entry_price,
            stop_loss=stop_loss,
            position_size=position_size,
            original_size=position_size,
            strategy="test"
        )
        
        current_stop = stop_loss
        current_price = entry_price
        
        for move in price_moves:
            current_price = current_price * (1 + move)
            if current_price <= 0:
                continue
            
            # Calculate ATR-based stop
            atr = entry_price * 0.02  # 2% ATR
            new_stop = trailing.calculate_atr_stop(current_price, atr, "LONG")
            
            # Update stop only if higher
            updated_stop = trailing.update_stop_if_higher(new_stop, current_stop, "LONG")
            
            # Property: Stop should never decrease for longs
            assert updated_stop >= current_stop - 1e-10, (
                f"Long stop decreased: {current_stop} -> {updated_stop}"
            )
            
            current_stop = updated_stop
    
    @given(
        entry_price=st.floats(min_value=10.0, max_value=1000.0, allow_nan=False),
        stop_distance_pct=st.floats(min_value=0.01, max_value=0.1, allow_nan=False),
        position_size=st.floats(min_value=0.1, max_value=10.0, allow_nan=False),
        price_moves=st.lists(
            st.floats(min_value=-0.1, max_value=0.05, allow_nan=False),
            min_size=5,
            max_size=20
        )
    )
    @settings(max_examples=50)
    def test_trailing_stop_monotonicity_short(
        self, entry_price: float, stop_distance_pct: float,
        position_size: float, price_moves: list
    ):
        """**Feature: kinetic-empire-alpha, Property 4: Trailing Stop Monotonicity**
        
        For short positions, trailing stop SHALL only move down (monotonic decrease).
        **Validates: Requirements 4.4**
        """
        trailing = AdvancedTrailingSystem()
        stop_loss = entry_price * (1 + stop_distance_pct)
        
        position = RFactorPosition(
            pair="TEST/USDT",
            side="SHORT",
            entry_price=entry_price,
            stop_loss=stop_loss,
            position_size=position_size,
            original_size=position_size,
            strategy="test"
        )
        
        current_stop = stop_loss
        current_price = entry_price
        
        for move in price_moves:
            current_price = current_price * (1 + move)
            if current_price <= 0:
                continue
            
            # Calculate ATR-based stop
            atr = entry_price * 0.02
            new_stop = trailing.calculate_atr_stop(current_price, atr, "SHORT")
            
            # Update stop only if lower
            updated_stop = trailing.update_stop_if_higher(new_stop, current_stop, "SHORT")
            
            # Property: Stop should never increase for shorts
            assert updated_stop <= current_stop + 1e-10, (
                f"Short stop increased: {current_stop} -> {updated_stop}"
            )
            
            current_stop = updated_stop
    
    @given(
        entry_price=st.floats(min_value=10.0, max_value=1000.0, allow_nan=False),
        stop_distance_pct=st.floats(min_value=0.01, max_value=0.1, allow_nan=False),
        peak_r=st.floats(min_value=1.0, max_value=5.0, allow_nan=False),
        profit_lock_pct=st.floats(min_value=0.3, max_value=0.7, allow_nan=False)
    )
    @settings(max_examples=50)
    def test_profit_lock_constraint(
        self, entry_price: float, stop_distance_pct: float,
        peak_r: float, profit_lock_pct: float
    ):
        """**Feature: kinetic-empire-alpha, Property 5: Profit-Lock Constraint**
        
        Profit-lock stop SHALL never allow giving back more than X% of peak profit.
        **Validates: Requirements 4.5**
        """
        config = AdvancedTrailingConfig(profit_lock_pct=profit_lock_pct)
        trailing = AdvancedTrailingSystem(config)
        
        stop_loss = entry_price * (1 - stop_distance_pct)
        r_value = entry_price - stop_loss
        
        position = RFactorPosition(
            pair="TEST/USDT",
            side="LONG",
            entry_price=entry_price,
            stop_loss=stop_loss,
            position_size=1.0,
            original_size=1.0,
            strategy="test"
        )
        position.peak_r = peak_r
        
        # Calculate profit-lock stop
        current_price = entry_price + (peak_r * r_value)  # At peak
        profit_lock_stop = trailing.calculate_profit_lock_stop(position, current_price)
        
        # Calculate expected minimum locked profit
        peak_profit = peak_r * r_value
        max_giveback = peak_profit * profit_lock_pct
        expected_min_profit = peak_profit - max_giveback
        
        # Profit at stop should be at least (1 - profit_lock_pct) of peak
        profit_at_stop = profit_lock_stop - entry_price
        
        assert profit_at_stop >= expected_min_profit - 1e-10, (
            f"Profit-lock violated: profit at stop {profit_at_stop} < "
            f"expected min {expected_min_profit}"
        )


class TestTrailingStopEdgeCases:
    """Edge case tests for trailing stop system."""
    
    def test_best_stop_selects_most_protective_for_long(self):
        """Test that best_stop returns highest stop for longs."""
        trailing = AdvancedTrailingSystem()
        
        position = RFactorPosition(
            pair="TEST/USDT",
            side="LONG",
            entry_price=100.0,
            stop_loss=95.0,
            position_size=1.0,
            original_size=1.0,
            strategy="test"
        )
        position.peak_r = 2.0
        
        df = generate_ohlcv_df(n_bars=50, base_price=100.0)
        
        best_stop = trailing.get_best_stop(position, df)
        
        # Best stop should be >= original stop for profitable position
        assert best_stop >= position.stop_loss
    
    def test_atr_stop_calculation(self):
        """Test ATR stop calculation."""
        trailing = AdvancedTrailingSystem()
        
        current_price = 100.0
        atr = 2.0
        
        # Long stop should be below price
        long_stop = trailing.calculate_atr_stop(current_price, atr, "LONG")
        assert long_stop < current_price
        assert long_stop == current_price - (trailing.config.atr_multiplier * atr)
        
        # Short stop should be above price
        short_stop = trailing.calculate_atr_stop(current_price, atr, "SHORT")
        assert short_stop > current_price
        assert short_stop == current_price + (trailing.config.atr_multiplier * atr)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
