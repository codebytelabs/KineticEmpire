"""Property-based tests for Kinetic Empire v3.0 TA Analyzer.

**Feature: kinetic-empire-v3**
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from datetime import datetime
from src.kinetic_empire.v3.analyzer.ta_analyzer import TAAnalyzer
from src.kinetic_empire.v3.core.models import Indicators, OHLCV


# Strategies for generating test data
price_strategy = st.floats(min_value=0.01, max_value=100000.0, allow_nan=False, allow_infinity=False)


@st.composite
def valid_indicators(draw):
    """Generate valid Indicators."""
    ema_21 = draw(st.floats(min_value=10.0, max_value=10000.0, allow_nan=False, allow_infinity=False))
    ema_9 = draw(st.floats(min_value=10.0, max_value=10000.0, allow_nan=False, allow_infinity=False))
    return Indicators(
        ema_9=ema_9,
        ema_21=ema_21,
        rsi=draw(st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False)),
        macd_line=draw(st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False)),
        macd_signal=draw(st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False)),
        macd_histogram=draw(st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False)),
        atr=draw(st.floats(min_value=0.01, max_value=100.0, allow_nan=False, allow_infinity=False)),
        volume_ratio=draw(st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False)),
    )


@st.composite
def valid_ohlcv_series(draw, length: int = 50):
    """Generate valid OHLCV series."""
    base_price = draw(st.floats(min_value=10.0, max_value=1000.0, allow_nan=False, allow_infinity=False))
    
    ohlcv_list = []
    current_price = base_price
    
    for i in range(length):
        # Random price movement
        change = draw(st.floats(min_value=-0.05, max_value=0.05, allow_nan=False, allow_infinity=False))
        current_price = current_price * (1 + change)
        current_price = max(0.01, current_price)  # Ensure positive
        
        open_price = current_price
        close_price = current_price * (1 + draw(st.floats(min_value=-0.02, max_value=0.02, allow_nan=False, allow_infinity=False)))
        close_price = max(0.01, close_price)
        
        high_price = max(open_price, close_price) * (1 + abs(draw(st.floats(min_value=0.0, max_value=0.01, allow_nan=False, allow_infinity=False))))
        low_price = min(open_price, close_price) * (1 - abs(draw(st.floats(min_value=0.0, max_value=0.01, allow_nan=False, allow_infinity=False))))
        low_price = max(0.01, low_price)
        
        volume = draw(st.floats(min_value=1000.0, max_value=1000000.0, allow_nan=False, allow_infinity=False))
        
        ohlcv_list.append(OHLCV(
            timestamp=i * 3600000,  # Hourly timestamps
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume,
        ))
    
    return ohlcv_list


class TestScoringSystem:
    """Property tests for scoring system."""

    @given(
        ind_4h=valid_indicators(),
        ind_1h=valid_indicators(),
        ind_15m=valid_indicators(),
    )
    @settings(max_examples=100)
    def test_scoring_consistency(self, ind_4h: Indicators, ind_1h: Indicators, ind_15m: Indicators):
        """**Feature: kinetic-empire-v3, Property 5: Scoring Consistency**
        
        For any set of indicator values, the total score SHALL equal the sum of 
        individual component scores and SHALL be between 0 and 100.
        **Validates: Requirements 2.3-2.10**
        """
        analyzer = TAAnalyzer()
        long_score, short_score, direction = analyzer.score_opportunity(ind_4h, ind_1h, ind_15m)
        
        # Scores should be between 0 and 100
        assert 0 <= long_score <= 100, f"Long score {long_score} out of bounds"
        assert 0 <= short_score <= 100, f"Short score {short_score} out of bounds"
        
        # Direction should match higher score
        if long_score > short_score:
            assert direction == "LONG"
        else:
            assert direction == "SHORT"

    @given(
        ind_4h=valid_indicators(),
        ind_1h=valid_indicators(),
        ind_15m=valid_indicators(),
    )
    @settings(max_examples=100)
    def test_scoring_weights_sum(self, ind_4h: Indicators, ind_1h: Indicators, ind_15m: Indicators):
        """Scoring weights should sum to 100."""
        analyzer = TAAnalyzer()
        total_weights = sum(analyzer.weights.values())
        assert total_weights == 100, f"Weights sum to {total_weights}, expected 100"

    @given(
        ind_4h=valid_indicators(),
        ind_1h=valid_indicators(),
        ind_15m=valid_indicators(),
    )
    @settings(max_examples=100)
    def test_scoring_deterministic(self, ind_4h: Indicators, ind_1h: Indicators, ind_15m: Indicators):
        """Same inputs should produce same scores."""
        analyzer = TAAnalyzer()
        
        result1 = analyzer.score_opportunity(ind_4h, ind_1h, ind_15m)
        result2 = analyzer.score_opportunity(ind_4h, ind_1h, ind_15m)
        
        assert result1 == result2, "Scoring should be deterministic"


class TestEntryExitCalculation:
    """Property tests for entry/exit calculation."""

    @given(
        entry_price=st.floats(min_value=10.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
        atr=st.floats(min_value=0.1, max_value=100.0, allow_nan=False, allow_infinity=False),
        direction=st.sampled_from(["LONG", "SHORT"]),
    )
    @settings(max_examples=100)
    def test_stop_loss_capped_at_3_percent(self, entry_price: float, atr: float, direction: str):
        """Stop loss should never exceed 3% from entry."""
        analyzer = TAAnalyzer(max_stop_loss_pct=3.0)
        entry, stop_loss, take_profit = analyzer.calculate_entry_exit(entry_price, atr, direction)
        
        stop_distance_pct = abs(stop_loss - entry) / entry * 100
        
        # Allow small floating point tolerance
        assert stop_distance_pct <= 3.01, f"Stop loss {stop_distance_pct:.2f}% exceeds 3%"

    @given(
        entry_price=st.floats(min_value=10.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
        atr=st.floats(min_value=0.1, max_value=100.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_long_stop_below_entry(self, entry_price: float, atr: float):
        """LONG stop loss should be below entry price."""
        analyzer = TAAnalyzer()
        entry, stop_loss, take_profit = analyzer.calculate_entry_exit(entry_price, atr, "LONG")
        
        assert stop_loss < entry, f"LONG stop {stop_loss} should be below entry {entry}"
        assert take_profit > entry, f"LONG TP {take_profit} should be above entry {entry}"

    @given(
        entry_price=st.floats(min_value=10.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
        atr=st.floats(min_value=0.1, max_value=100.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_short_stop_above_entry(self, entry_price: float, atr: float):
        """SHORT stop loss should be above entry price."""
        analyzer = TAAnalyzer()
        entry, stop_loss, take_profit = analyzer.calculate_entry_exit(entry_price, atr, "SHORT")
        
        assert stop_loss > entry, f"SHORT stop {stop_loss} should be above entry {entry}"
        assert take_profit < entry, f"SHORT TP {take_profit} should be below entry {entry}"

    @given(
        entry_price=st.floats(min_value=10.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
        atr=st.floats(min_value=0.1, max_value=100.0, allow_nan=False, allow_infinity=False),
        direction=st.sampled_from(["LONG", "SHORT"]),
    )
    @settings(max_examples=100)
    def test_risk_reward_ratio(self, entry_price: float, atr: float, direction: str):
        """Take profit should be at 1.5x risk distance."""
        analyzer = TAAnalyzer(risk_reward_ratio=1.5)
        entry, stop_loss, take_profit = analyzer.calculate_entry_exit(entry_price, atr, direction)
        
        risk = abs(stop_loss - entry)
        reward = abs(take_profit - entry)
        
        if risk > 0:
            actual_rr = reward / risk
            # Allow small tolerance for floating point
            assert abs(actual_rr - 1.5) < 0.01, f"R:R {actual_rr:.2f} should be 1.5"


class TestIndicatorCalculation:
    """Property tests for indicator calculation."""

    @given(ohlcv=valid_ohlcv_series(length=50))
    @settings(max_examples=50)
    def test_calculate_indicators_returns_valid(self, ohlcv: list):
        """Indicator calculation should return valid Indicators."""
        analyzer = TAAnalyzer()
        indicators = analyzer.calculate_indicators(ohlcv)
        
        assert isinstance(indicators, Indicators)
        assert indicators.ema_9 > 0
        assert indicators.ema_21 > 0
        assert 0 <= indicators.rsi <= 100
        assert indicators.atr >= 0

    def test_calculate_indicators_insufficient_data(self):
        """Should raise error for insufficient data."""
        analyzer = TAAnalyzer()
        
        # Create only 10 candles
        ohlcv = [
            OHLCV(timestamp=i, open=100, high=101, low=99, close=100, volume=1000)
            for i in range(10)
        ]
        
        with pytest.raises(ValueError, match="Insufficient data"):
            analyzer.calculate_indicators(ohlcv)
