"""Property-based tests for MicroTimeframeAnalyzer.

**Feature: signal-quality-fix, Property 7: Micro-Timeframe Alignment**
**Validates: Requirements 7.2, 7.3**
"""

import pytest
from hypothesis import given, strategies as st

from src.kinetic_empire.signal_quality.config import QualityGateConfig
from src.kinetic_empire.signal_quality.micro_analyzer import MicroTimeframeAnalyzer
from src.kinetic_empire.signal_quality.momentum_validator import OHLCV


def make_trending_up_candles(count: int = 30, start_price: float = 100.0) -> list:
    """Create candles with clear uptrend."""
    candles = []
    price = start_price
    for i in range(count):
        price = price * 1.002  # 0.2% increase per candle
        candles.append(OHLCV(
            open=price * 0.999,
            high=price * 1.002,
            low=price * 0.998,
            close=price,
            volume=1000.0
        ))
    return candles


def make_trending_down_candles(count: int = 30, start_price: float = 100.0) -> list:
    """Create candles with clear downtrend."""
    candles = []
    price = start_price
    for i in range(count):
        price = price * 0.998  # 0.2% decrease per candle
        candles.append(OHLCV(
            open=price * 1.001,
            high=price * 1.002,
            low=price * 0.998,
            close=price,
            volume=1000.0
        ))
    return candles


def make_sideways_candles(count: int = 30, price: float = 100.0) -> list:
    """Create candles with sideways movement."""
    candles = []
    for i in range(count):
        candles.append(OHLCV(
            open=price,
            high=price * 1.001,
            low=price * 0.999,
            close=price,
            volume=1000.0
        ))
    return candles


class TestMicroAnalyzerProperties:
    """Property-based tests for micro-timeframe alignment."""
    
    def test_both_aligned_up_gives_bonus_for_long(self):
        """Property: Both 1M and 5M UP trends SHALL give +10 bonus for LONG.
        
        **Feature: signal-quality-fix, Property 7: Micro-Timeframe Alignment**
        **Validates: Requirements 7.2**
        """
        config = QualityGateConfig()
        analyzer = MicroTimeframeAnalyzer(config)
        
        ohlcv_1m = make_trending_up_candles()
        ohlcv_5m = make_trending_up_candles()
        
        result = analyzer.analyze(ohlcv_1m, ohlcv_5m, "LONG")
        
        assert result.micro_aligned is True
        assert result.micro_bonus == 10
        assert result.should_reject is False
    
    def test_both_aligned_down_gives_bonus_for_short(self):
        """Property: Both 1M and 5M DOWN trends SHALL give +10 bonus for SHORT.
        
        **Feature: signal-quality-fix, Property 7: Micro-Timeframe Alignment**
        **Validates: Requirements 7.2**
        """
        config = QualityGateConfig()
        analyzer = MicroTimeframeAnalyzer(config)
        
        ohlcv_1m = make_trending_down_candles()
        ohlcv_5m = make_trending_down_candles()
        
        result = analyzer.analyze(ohlcv_1m, ohlcv_5m, "SHORT")
        
        assert result.micro_aligned is True
        assert result.micro_bonus == 10
        assert result.should_reject is False
    
    def test_1m_contradicts_long_no_reject_with_relaxed_config(self):
        """Property: Only 1M DOWN (not both) SHALL NOT reject LONG with relaxed config.
        
        With require_both_micro_contradict=True (default), only one timeframe
        contradicting should NOT reject the signal.
        
        **Feature: signal-quality-fix, Property 7: Micro-Timeframe Alignment**
        **Validates: Requirements 7.3**
        """
        config = QualityGateConfig()  # Default has require_both_micro_contradict=True
        analyzer = MicroTimeframeAnalyzer(config)
        
        ohlcv_1m = make_trending_down_candles()  # Contradicts LONG
        ohlcv_5m = make_trending_up_candles()    # Supports LONG
        
        result = analyzer.analyze(ohlcv_1m, ohlcv_5m, "LONG")
        
        # With relaxed config, only one contradicting should NOT reject
        assert result.should_reject is False
        assert result.micro_bonus == 0  # No bonus since not fully aligned
    
    def test_both_contradict_long_rejects(self):
        """Property: BOTH 1M and 5M DOWN SHALL reject LONG signal.
        
        **Feature: signal-quality-fix, Property 7: Micro-Timeframe Alignment**
        **Validates: Requirements 7.3**
        """
        config = QualityGateConfig()
        analyzer = MicroTimeframeAnalyzer(config)
        
        ohlcv_1m = make_trending_down_candles()  # Contradicts LONG
        ohlcv_5m = make_trending_down_candles()  # Contradicts LONG
        
        result = analyzer.analyze(ohlcv_1m, ohlcv_5m, "LONG")
        
        assert result.should_reject is True
        assert result.micro_bonus == 0
    
    def test_both_contradict_short_rejects(self):
        """Property: BOTH 1M and 5M UP SHALL reject SHORT signal.
        
        **Feature: signal-quality-fix, Property 7: Micro-Timeframe Alignment**
        **Validates: Requirements 7.3**
        """
        config = QualityGateConfig()
        analyzer = MicroTimeframeAnalyzer(config)
        
        ohlcv_1m = make_trending_up_candles()  # Contradicts SHORT
        ohlcv_5m = make_trending_up_candles()  # Contradicts SHORT
        
        result = analyzer.analyze(ohlcv_1m, ohlcv_5m, "SHORT")
        
        assert result.should_reject is True
        assert result.micro_bonus == 0
    
    def test_strict_mode_single_contradict_rejects(self):
        """Property: With strict mode, single timeframe contradiction SHALL reject.
        
        **Feature: signal-quality-fix, Property 7: Micro-Timeframe Alignment**
        **Validates: Requirements 7.3**
        """
        config = QualityGateConfig(require_both_micro_contradict=False)  # Strict mode
        analyzer = MicroTimeframeAnalyzer(config)
        
        ohlcv_1m = make_trending_down_candles()  # Contradicts LONG
        ohlcv_5m = make_trending_up_candles()    # Supports LONG
        
        result = analyzer.analyze(ohlcv_1m, ohlcv_5m, "LONG")
        
        # With strict mode, single contradiction should reject
        assert result.should_reject is True
        assert result.micro_bonus == 0


class TestMicroAnalyzerEdgeCases:
    """Edge case tests for micro-timeframe analyzer."""
    
    def test_sideways_no_bonus_no_reject(self):
        """Sideways trends should not give bonus or reject."""
        analyzer = MicroTimeframeAnalyzer(QualityGateConfig())
        
        ohlcv_1m = make_sideways_candles()
        ohlcv_5m = make_sideways_candles()
        
        result = analyzer.analyze(ohlcv_1m, ohlcv_5m, "LONG")
        
        assert result.micro_aligned is False
        assert result.micro_bonus == 0
        assert result.should_reject is False
    
    def test_insufficient_data(self):
        """With insufficient data, should return sideways."""
        analyzer = MicroTimeframeAnalyzer(QualityGateConfig())
        
        # Only 10 candles (need 21 for EMA21)
        ohlcv_1m = make_trending_up_candles(count=10)
        ohlcv_5m = make_trending_up_candles(count=10)
        
        result = analyzer.analyze(ohlcv_1m, ohlcv_5m, "LONG")
        
        assert result.trend_1m == "SIDEWAYS"
        assert result.trend_5m == "SIDEWAYS"
    
    def test_case_insensitive_direction(self):
        """Direction should be case-insensitive."""
        analyzer = MicroTimeframeAnalyzer(QualityGateConfig())
        
        ohlcv_1m = make_trending_up_candles()
        ohlcv_5m = make_trending_up_candles()
        
        result_upper = analyzer.analyze(ohlcv_1m, ohlcv_5m, "LONG")
        result_lower = analyzer.analyze(ohlcv_1m, ohlcv_5m, "long")
        result_mixed = analyzer.analyze(ohlcv_1m, ohlcv_5m, "Long")
        
        assert result_upper.micro_aligned == result_lower.micro_aligned == result_mixed.micro_aligned
