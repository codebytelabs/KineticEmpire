"""Tests for Wave Rider MTF Analyzer.

Includes property-based tests for:
- Property 4: Trend Direction Classification
- Property 5: Alignment Score Calculation
"""

import pytest
from hypothesis import given, strategies as st, settings

from src.kinetic_empire.wave_rider.mtf_analyzer import MTFAnalyzer
from src.kinetic_empire.wave_rider.models import (
    OHLCV,
    TimeframeAnalysis,
    TrendDirection,
    WaveRiderConfig,
)


def make_candles(closes: list, volume: float = 1000.0) -> list:
    """Create OHLCV candles from close prices."""
    candles = []
    for i, close in enumerate(closes):
        # Simple candle with close as reference
        candles.append(OHLCV(
            open=close * 0.999,
            high=close * 1.001,
            low=close * 0.998,
            close=close,
            volume=volume,
            timestamp=i * 60000,
        ))
    return candles


class TestMTFAnalyzer:
    """Unit tests for MTFAnalyzer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = MTFAnalyzer()
    
    def test_analyze_empty_data(self):
        """Test analysis with empty data returns neutral."""
        result = self.analyzer.analyze("BTCUSDT", {})
        
        assert result.alignment_score == 40
        assert result.dominant_direction == TrendDirection.NEUTRAL
    
    def test_analyze_insufficient_data(self):
        """Test analysis with insufficient data returns neutral."""
        ohlcv_data = {
            "1m": make_candles([100] * 5),  # Less than 21 candles
            "5m": make_candles([100] * 5),
            "15m": make_candles([100] * 5),
        }
        result = self.analyzer.analyze("BTCUSDT", ohlcv_data)
        
        # All should be neutral due to insufficient data
        for tf, analysis in result.analyses.items():
            assert analysis.trend_direction == TrendDirection.NEUTRAL
    
    def test_analyze_bullish_trend(self):
        """Test analysis detects bullish trend."""
        # Create uptrending data: prices increasing
        closes = [100 + i * 0.5 for i in range(30)]  # 100 to 114.5
        ohlcv_data = {
            "1m": make_candles(closes),
            "5m": make_candles(closes),
            "15m": make_candles(closes),
        }
        result = self.analyzer.analyze("BTCUSDT", ohlcv_data)
        
        # Should detect bullish on all timeframes
        assert result.alignment_score == 100
        assert result.dominant_direction == TrendDirection.BULLISH
    
    def test_analyze_bearish_trend(self):
        """Test analysis detects bearish trend."""
        # Create downtrending data: prices decreasing
        closes = [100 - i * 0.5 for i in range(30)]  # 100 to 85.5
        ohlcv_data = {
            "1m": make_candles(closes),
            "5m": make_candles(closes),
            "15m": make_candles(closes),
        }
        result = self.analyzer.analyze("BTCUSDT", ohlcv_data)
        
        # Should detect bearish on all timeframes
        assert result.alignment_score == 100
        assert result.dominant_direction == TrendDirection.BEARISH
    
    def test_analyze_mixed_trends(self):
        """Test analysis with mixed trends."""
        # 1m bullish, 5m bearish, 15m neutral
        bullish_closes = [100 + i * 0.5 for i in range(30)]
        bearish_closes = [100 - i * 0.5 for i in range(30)]
        flat_closes = [100] * 30
        
        ohlcv_data = {
            "1m": make_candles(bullish_closes),
            "5m": make_candles(bearish_closes),
            "15m": make_candles(flat_closes),
        }
        result = self.analyzer.analyze("BTCUSDT", ohlcv_data)
        
        # Mixed signals = 40 alignment
        assert result.alignment_score == 40
    
    def test_ema_calculation(self):
        """Test EMA calculation."""
        values = [100.0] * 20 + [110.0]  # Flat then spike
        ema = self.analyzer._calculate_ema(values, 9)
        
        # EMA should be between 100 and 110
        assert 100 < ema < 110
    
    def test_rsi_calculation_overbought(self):
        """Test RSI calculation for overbought condition."""
        # Strongly rising prices
        closes = [100 + i * 2 for i in range(20)]
        rsi = self.analyzer._calculate_rsi(closes, 14)
        
        # Should be high (overbought)
        assert rsi > 70
    
    def test_rsi_calculation_oversold(self):
        """Test RSI calculation for oversold condition."""
        # Strongly falling prices
        closes = [100 - i * 2 for i in range(20)]
        rsi = self.analyzer._calculate_rsi(closes, 14)
        
        # Should be low (oversold)
        assert rsi < 30
    
    def test_vwap_calculation(self):
        """Test VWAP calculation."""
        candles = [
            OHLCV(100, 102, 99, 101, 1000, 0),
            OHLCV(101, 103, 100, 102, 2000, 1),
        ]
        vwap = self.analyzer._calculate_vwap(candles)
        
        # VWAP should be weighted toward second candle (higher volume)
        # Typical price 1: (102+99+101)/3 = 100.67
        # Typical price 2: (103+100+102)/3 = 101.67
        # VWAP = (100.67*1000 + 101.67*2000) / 3000 = 101.33
        assert 101 < vwap < 102
    
    def test_price_vs_vwap_above(self):
        """Test price vs VWAP detection - above."""
        # Create data where price is above VWAP
        closes = [100 + i * 0.5 for i in range(30)]
        ohlcv_data = {"1m": make_candles(closes)}
        
        result = self.analyzer.analyze("BTCUSDT", ohlcv_data)
        # Price should be above VWAP in uptrend
        assert result.price_vs_vwap == "ABOVE"


class TestTrendDirectionProperty:
    """Property-based tests for Trend Direction Classification.
    
    Property 4: Trend Direction Classification
    For any EMA_fast, EMA_slow, and price:
    - Direction is BULLISH if EMA_fast > EMA_slow AND price > EMA_fast
    - Direction is BEARISH if EMA_fast < EMA_slow AND price < EMA_slow
    - Direction is NEUTRAL otherwise
    
    Validates: Requirements 3.4, 3.5, 3.6
    """
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = MTFAnalyzer()
    
    @given(
        ema_slow=st.floats(min_value=10.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        ema_fast_offset=st.floats(min_value=0.01, max_value=50.0, allow_nan=False, allow_infinity=False),
        price_offset=st.floats(min_value=0.01, max_value=50.0, allow_nan=False, allow_infinity=False),
    )
    def test_property_bullish_condition(self, ema_slow: float, ema_fast_offset: float, price_offset: float):
        """Property: BULLISH when EMA_fast > EMA_slow AND price > EMA_fast."""
        ema_fast = ema_slow + ema_fast_offset  # EMA_fast > EMA_slow
        price = ema_fast + price_offset  # price > EMA_fast
        
        direction = self.analyzer.determine_trend_direction(ema_fast, ema_slow, price)
        assert direction == TrendDirection.BULLISH
    
    @given(
        ema_slow=st.floats(min_value=50.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        ema_fast_offset=st.floats(min_value=0.01, max_value=50.0, allow_nan=False, allow_infinity=False),
        price_offset=st.floats(min_value=0.01, max_value=50.0, allow_nan=False, allow_infinity=False),
    )
    def test_property_bearish_condition(self, ema_slow: float, ema_fast_offset: float, price_offset: float):
        """Property: BEARISH when EMA_fast < EMA_slow AND price < EMA_slow."""
        ema_fast = ema_slow - ema_fast_offset  # EMA_fast < EMA_slow
        price = ema_slow - ema_fast_offset - price_offset  # price < EMA_slow
        
        direction = self.analyzer.determine_trend_direction(ema_fast, ema_slow, price)
        assert direction == TrendDirection.BEARISH
    
    @given(
        ema_slow=st.floats(min_value=50.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        ema_fast_offset=st.floats(min_value=0.01, max_value=50.0, allow_nan=False, allow_infinity=False),
    )
    def test_property_neutral_ema_fast_above_price_between(self, ema_slow: float, ema_fast_offset: float):
        """Property: NEUTRAL when EMA_fast > EMA_slow but price between them."""
        ema_fast = ema_slow + ema_fast_offset
        price = (ema_fast + ema_slow) / 2  # Price between EMAs
        
        direction = self.analyzer.determine_trend_direction(ema_fast, ema_slow, price)
        assert direction == TrendDirection.NEUTRAL
    
    @given(
        ema_slow=st.floats(min_value=50.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        ema_fast_offset=st.floats(min_value=0.01, max_value=50.0, allow_nan=False, allow_infinity=False),
        price_offset=st.floats(min_value=0.01, max_value=10.0, allow_nan=False, allow_infinity=False),
    )
    def test_property_neutral_ema_fast_below_price_above_slow(self, ema_slow: float, ema_fast_offset: float, price_offset: float):
        """Property: NEUTRAL when EMA_fast < EMA_slow but price > EMA_slow."""
        ema_fast = ema_slow - ema_fast_offset  # EMA_fast < EMA_slow
        price = ema_slow + price_offset  # price > EMA_slow (not bearish)
        
        direction = self.analyzer.determine_trend_direction(ema_fast, ema_slow, price)
        # Not bearish because price > EMA_slow, not bullish because EMA_fast < EMA_slow
        assert direction == TrendDirection.NEUTRAL


class TestAlignmentScoreProperty:
    """Property-based tests for Alignment Score Calculation.
    
    Property 5: Alignment Score Calculation
    For any three timeframe directions:
    - Score is 100 if all 3 directions are the same (non-NEUTRAL)
    - Score is 70 if exactly 2 directions are the same (non-NEUTRAL)
    - Score is 40 otherwise
    
    Validates: Requirements 3.7, 3.8, 3.9
    """
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = MTFAnalyzer()
    
    def _make_analyses(self, directions: list) -> dict:
        """Create analyses dict from list of directions."""
        timeframes = ["1m", "5m", "15m"]
        return {
            tf: TimeframeAnalysis(
                timeframe=tf,
                ema_fast=100.0,
                ema_slow=100.0,
                rsi=50.0,
                vwap=100.0,
                trend_direction=direction,
                price=100.0,
            )
            for tf, direction in zip(timeframes, directions)
        }
    
    def test_property_all_bullish_100(self):
        """Property: All 3 BULLISH = 100 score."""
        analyses = self._make_analyses([
            TrendDirection.BULLISH,
            TrendDirection.BULLISH,
            TrendDirection.BULLISH,
        ])
        score = self.analyzer.calculate_alignment_score(analyses)
        assert score == 100
    
    def test_property_all_bearish_100(self):
        """Property: All 3 BEARISH = 100 score."""
        analyses = self._make_analyses([
            TrendDirection.BEARISH,
            TrendDirection.BEARISH,
            TrendDirection.BEARISH,
        ])
        score = self.analyzer.calculate_alignment_score(analyses)
        assert score == 100
    
    def test_property_two_bullish_70(self):
        """Property: 2 BULLISH + 1 other = 70 score."""
        for other in [TrendDirection.BEARISH, TrendDirection.NEUTRAL]:
            analyses = self._make_analyses([
                TrendDirection.BULLISH,
                TrendDirection.BULLISH,
                other,
            ])
            score = self.analyzer.calculate_alignment_score(analyses)
            assert score == 70
    
    def test_property_two_bearish_70(self):
        """Property: 2 BEARISH + 1 other = 70 score."""
        for other in [TrendDirection.BULLISH, TrendDirection.NEUTRAL]:
            analyses = self._make_analyses([
                TrendDirection.BEARISH,
                TrendDirection.BEARISH,
                other,
            ])
            score = self.analyzer.calculate_alignment_score(analyses)
            assert score == 70
    
    def test_property_all_neutral_40(self):
        """Property: All 3 NEUTRAL = 40 score."""
        analyses = self._make_analyses([
            TrendDirection.NEUTRAL,
            TrendDirection.NEUTRAL,
            TrendDirection.NEUTRAL,
        ])
        score = self.analyzer.calculate_alignment_score(analyses)
        assert score == 40
    
    def test_property_mixed_40(self):
        """Property: 1 BULLISH + 1 BEARISH + 1 NEUTRAL = 40 score."""
        analyses = self._make_analyses([
            TrendDirection.BULLISH,
            TrendDirection.BEARISH,
            TrendDirection.NEUTRAL,
        ])
        score = self.analyzer.calculate_alignment_score(analyses)
        assert score == 40
    
    def test_property_one_each_40(self):
        """Property: 1 BULLISH + 1 BEARISH + 1 NEUTRAL = 40 score."""
        analyses = self._make_analyses([
            TrendDirection.BULLISH,
            TrendDirection.BEARISH,
            TrendDirection.NEUTRAL,
        ])
        score = self.analyzer.calculate_alignment_score(analyses)
        assert score == 40
    
    @given(st.sampled_from([TrendDirection.BULLISH, TrendDirection.BEARISH, TrendDirection.NEUTRAL]))
    @settings(max_examples=20)
    def test_property_score_in_valid_range(self, direction: TrendDirection):
        """Property: Score is always 40, 70, or 100."""
        # Generate random combination
        import random
        directions = [random.choice(list(TrendDirection)) for _ in range(3)]
        analyses = self._make_analyses(directions)
        
        score = self.analyzer.calculate_alignment_score(analyses)
        assert score in [40, 70, 100]
