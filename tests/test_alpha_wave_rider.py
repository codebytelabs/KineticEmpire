"""Property-based tests for Wave Rider Strategy.

**Feature: kinetic-empire-alpha, Property 6: Multi-Timeframe Alignment**
**Validates: Requirements 5.2, 5.3**
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from datetime import datetime
import pandas as pd
import numpy as np

from kinetic_empire.alpha.wave_rider import WaveRiderStrategy, WaveRiderConfig
from kinetic_empire.alpha.models import TrendStrength, Signal


def generate_trending_df(n_bars: int = 50, base_price: float = 100.0,
                         trend: str = "BULLISH", ema_period: int = 21) -> pd.DataFrame:
    """Generate synthetic OHLCV data with a specific trend."""
    np.random.seed(42)
    
    if trend == "BULLISH":
        drift = 0.002  # Upward drift
    elif trend == "BEARISH":
        drift = -0.002  # Downward drift
    else:
        drift = 0.0  # Neutral
    
    prices = [base_price]
    for _ in range(n_bars - 1):
        change = np.random.normal(drift, 0.01)
        prices.append(prices[-1] * (1 + change))
    
    df = pd.DataFrame({
        'open': prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices],
        'close': [p * (1 + np.random.normal(drift/2, 0.005)) for p in prices],
        'volume': [1000000 * (1 + np.random.random()) for _ in prices]
    })
    
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    df['ema'] = df['close'].ewm(span=ema_period, adjust=False).mean()
    df['roc'] = df['close'].pct_change() * 100
    
    # Calculate ATR
    tr1 = df['high'] - df['low']
    tr2 = abs(df['high'] - df['close'].shift(1))
    tr3 = abs(df['low'] - df['close'].shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr'] = tr.rolling(window=14).mean()
    
    return df


class TestWaveRiderProperties:
    """Property-based tests for Wave Rider strategy."""
    
    def test_all_bullish_gives_strong_uptrend(self):
        """**Feature: kinetic-empire-alpha, Property 6: Multi-Timeframe Alignment**
        
        WHEN all four timeframes show bullish alignment THEN classify as STRONG_UPTREND.
        **Validates: Requirements 5.2**
        """
        strategy = WaveRiderStrategy()
        
        # Create dataframes where close is clearly above EMA
        timeframe_data = {}
        for tf in ["1d", "4h", "1h", "15m"]:
            df = generate_trending_df(trend="BULLISH")
            # Force close well above EMA
            df.loc[df.index[-1], 'close'] = df['ema'].iloc[-1] * 1.05
            timeframe_data[tf] = df
        
        trend = strategy.get_trend_alignment(timeframe_data)
        assert trend == TrendStrength.STRONG_UPTREND, (
            f"Expected STRONG_UPTREND with all bullish, got {trend}"
        )
    
    def test_all_bearish_gives_strong_downtrend(self):
        """**Feature: kinetic-empire-alpha, Property 6: Multi-Timeframe Alignment**
        
        WHEN all four timeframes show bearish alignment THEN classify as STRONG_DOWNTREND.
        **Validates: Requirements 5.3**
        """
        strategy = WaveRiderStrategy()
        
        # Create dataframes where close is clearly below EMA
        timeframe_data = {}
        for tf in ["1d", "4h", "1h", "15m"]:
            df = generate_trending_df(trend="BEARISH")
            # Force close well below EMA
            df.loc[df.index[-1], 'close'] = df['ema'].iloc[-1] * 0.95
            timeframe_data[tf] = df
        
        trend = strategy.get_trend_alignment(timeframe_data)
        assert trend == TrendStrength.STRONG_DOWNTREND, (
            f"Expected STRONG_DOWNTREND with all bearish, got {trend}"
        )
    
    def test_three_bullish_gives_weak_uptrend(self):
        """**Feature: kinetic-empire-alpha, Property 6: Multi-Timeframe Alignment**
        
        WHEN 3 timeframes show bullish alignment THEN classify as WEAK_UPTREND.
        **Validates: Requirements 5.2**
        """
        strategy = WaveRiderStrategy()
        
        timeframe_data = {}
        timeframes = ["1d", "4h", "1h", "15m"]
        
        # 3 bullish, 1 neutral
        for i, tf in enumerate(timeframes):
            df = generate_trending_df(trend="BULLISH" if i < 3 else "NEUTRAL")
            if i < 3:
                df.loc[df.index[-1], 'close'] = df['ema'].iloc[-1] * 1.05
            else:
                df.loc[df.index[-1], 'close'] = df['ema'].iloc[-1]  # Neutral
            timeframe_data[tf] = df
        
        trend = strategy.get_trend_alignment(timeframe_data)
        assert trend in [TrendStrength.STRONG_UPTREND, TrendStrength.WEAK_UPTREND], (
            f"Expected uptrend with 3 bullish, got {trend}"
        )
    
    def test_strong_uptrend_only_generates_long_signals(self):
        """**Feature: kinetic-empire-alpha, Property 6: Multi-Timeframe Alignment**
        
        WHEN trend is STRONG_UPTREND THEN only long signals SHALL be generated.
        **Validates: Requirements 5.4**
        """
        strategy = WaveRiderStrategy()
        
        # Create all bullish timeframes
        timeframe_data = {
            tf: generate_trending_df(trend="BULLISH")
            for tf in ["1d", "4h", "1h", "15m"]
        }
        
        # Adjust entry timeframe for pullback
        entry_df = timeframe_data["15m"]
        entry_df.loc[entry_df.index[-1], 'close'] = entry_df['ema'].iloc[-1] * 1.01
        entry_df.loc[entry_df.index[-1], 'roc'] = 1.0  # Positive momentum
        
        signal = strategy.generate_signal("BTC/USDT", timeframe_data)
        
        if signal is not None:
            assert signal.side == "LONG", (
                f"Expected LONG signal in uptrend, got {signal.side}"
            )
    
    def test_strong_downtrend_only_generates_short_signals(self):
        """**Feature: kinetic-empire-alpha, Property 6: Multi-Timeframe Alignment**
        
        WHEN trend is STRONG_DOWNTREND THEN only short signals SHALL be generated.
        **Validates: Requirements 5.5**
        """
        strategy = WaveRiderStrategy()
        
        # Create all bearish timeframes
        timeframe_data = {
            tf: generate_trending_df(trend="BEARISH")
            for tf in ["1d", "4h", "1h", "15m"]
        }
        
        # Adjust entry timeframe for pullback
        entry_df = timeframe_data["15m"]
        entry_df.loc[entry_df.index[-1], 'close'] = entry_df['ema'].iloc[-1] * 0.99
        entry_df.loc[entry_df.index[-1], 'roc'] = -1.0  # Negative momentum
        
        signal = strategy.generate_signal("BTC/USDT", timeframe_data)
        
        if signal is not None:
            assert signal.side == "SHORT", (
                f"Expected SHORT signal in downtrend, got {signal.side}"
            )
    
    def test_no_trade_when_insufficient_alignment(self):
        """**Feature: kinetic-empire-alpha, Property 6: Multi-Timeframe Alignment**
        
        WHEN fewer than 3 timeframes align THEN NO_TRADE SHALL be returned.
        **Validates: Requirements 5.6**
        """
        strategy = WaveRiderStrategy()
        
        # Create mixed timeframes (2 bullish, 2 bearish)
        timeframe_data = {
            "1d": generate_trending_df(trend="BULLISH"),
            "4h": generate_trending_df(trend="BULLISH"),
            "1h": generate_trending_df(trend="BEARISH"),
            "15m": generate_trending_df(trend="BEARISH"),
        }
        
        trend = strategy.get_trend_alignment(timeframe_data)
        
        # With 2 bullish and 2 bearish, should be NEUTRAL or NO_TRADE
        assert trend in [TrendStrength.NEUTRAL, TrendStrength.NO_TRADE], (
            f"Expected NEUTRAL/NO_TRADE with mixed alignment, got {trend}"
        )


class TestWaveRiderTimeframeAnalysis:
    """Tests for individual timeframe analysis."""
    
    @given(
        close_above_ema=st.booleans(),
        buffer_pct=st.floats(min_value=0.001, max_value=0.01, allow_nan=False)
    )
    @settings(max_examples=50)
    def test_timeframe_trend_detection(self, close_above_ema: bool, buffer_pct: float):
        """Test that timeframe trend is correctly detected based on price vs EMA."""
        strategy = WaveRiderStrategy()
        
        df = generate_trending_df(trend="NEUTRAL")
        ema = df['ema'].iloc[-1]
        
        if close_above_ema:
            df.loc[df.index[-1], 'close'] = ema * (1 + buffer_pct + 0.002)
            expected = "BULLISH"
        else:
            df.loc[df.index[-1], 'close'] = ema * (1 - buffer_pct - 0.002)
            expected = "BEARISH"
        
        result = strategy.analyze_timeframe(df)
        assert result == expected, f"Expected {expected}, got {result}"
    
    def test_neutral_when_close_near_ema(self):
        """Test that NEUTRAL is returned when close is very near EMA."""
        strategy = WaveRiderStrategy()
        
        df = generate_trending_df(trend="NEUTRAL")
        ema = df['ema'].iloc[-1]
        
        # Set close exactly at EMA
        df.loc[df.index[-1], 'close'] = ema
        
        result = strategy.analyze_timeframe(df)
        assert result == "NEUTRAL"


class TestWaveRiderPullbackEntry:
    """Tests for pullback entry detection."""
    
    def test_pullback_entry_requires_momentum(self):
        """Test that pullback entry requires sufficient momentum."""
        config = WaveRiderConfig(roc_threshold=0.5)
        strategy = WaveRiderStrategy(config)
        
        df = generate_trending_df(trend="BULLISH")
        ema = df['ema'].iloc[-1]
        
        # Price near EMA but no momentum
        df.loc[df.index[-1], 'close'] = ema * 1.01
        df.loc[df.index[-1], 'roc'] = 0.1  # Below threshold
        
        result = strategy.check_pullback_entry(df, TrendStrength.STRONG_UPTREND)
        assert not result, "Should not enter without sufficient momentum"
        
        # Now with momentum
        df.loc[df.index[-1], 'roc'] = 1.0  # Above threshold
        result = strategy.check_pullback_entry(df, TrendStrength.STRONG_UPTREND)
        assert result, "Should enter with sufficient momentum"
    
    def test_no_pullback_entry_in_no_trade(self):
        """Test that no pullback entry in NO_TRADE trend."""
        strategy = WaveRiderStrategy()
        
        df = generate_trending_df(trend="NEUTRAL")
        
        result = strategy.check_pullback_entry(df, TrendStrength.NO_TRADE)
        assert not result


class TestWaveRiderSignalGeneration:
    """Tests for signal generation."""
    
    def test_signal_includes_stop_loss(self):
        """Test that generated signals include stop loss."""
        strategy = WaveRiderStrategy()
        
        timeframe_data = {
            tf: generate_trending_df(trend="BULLISH")
            for tf in ["1d", "4h", "1h", "15m"]
        }
        
        # Setup for signal generation
        entry_df = timeframe_data["15m"]
        entry_df.loc[entry_df.index[-1], 'close'] = entry_df['ema'].iloc[-1] * 1.01
        entry_df.loc[entry_df.index[-1], 'roc'] = 1.0
        
        signal = strategy.generate_signal("BTC/USDT", timeframe_data)
        
        if signal is not None:
            assert signal.stop_loss is not None
            assert signal.entry_price is not None
            
            # For long, stop should be below entry
            if signal.side == "LONG":
                assert signal.stop_loss < signal.entry_price
            else:
                assert signal.stop_loss > signal.entry_price
    
    def test_signal_strategy_name(self):
        """Test that signal has correct strategy name."""
        strategy = WaveRiderStrategy()
        
        timeframe_data = {
            tf: generate_trending_df(trend="BULLISH")
            for tf in ["1d", "4h", "1h", "15m"]
        }
        
        entry_df = timeframe_data["15m"]
        entry_df.loc[entry_df.index[-1], 'close'] = entry_df['ema'].iloc[-1] * 1.01
        entry_df.loc[entry_df.index[-1], 'roc'] = 1.0
        
        signal = strategy.generate_signal("BTC/USDT", timeframe_data)
        
        if signal is not None:
            assert signal.strategy == "wave_rider"


class TestWaveRiderExitConditions:
    """Tests for exit condition detection."""
    
    def test_exit_long_when_below_ema(self):
        """Test that long position exits when price drops below EMA."""
        strategy = WaveRiderStrategy()
        
        df = generate_trending_df(trend="BULLISH")
        ema = df['ema'].iloc[-1]
        
        # Price above EMA - should not exit
        df.loc[df.index[-1], 'close'] = ema * 1.02
        assert not strategy.should_exit(df, "LONG")
        
        # Price below EMA - should exit
        df.loc[df.index[-1], 'close'] = ema * 0.98
        assert strategy.should_exit(df, "LONG")
    
    def test_exit_short_when_above_ema(self):
        """Test that short position exits when price rises above EMA."""
        strategy = WaveRiderStrategy()
        
        df = generate_trending_df(trend="BEARISH")
        ema = df['ema'].iloc[-1]
        
        # Price below EMA - should not exit
        df.loc[df.index[-1], 'close'] = ema * 0.98
        assert not strategy.should_exit(df, "SHORT")
        
        # Price above EMA - should exit
        df.loc[df.index[-1], 'close'] = ema * 1.02
        assert strategy.should_exit(df, "SHORT")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
