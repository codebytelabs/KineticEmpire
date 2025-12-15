"""Tests for Wave Rider Signal Generator.

Includes property-based tests for:
- Property 6: Entry Rejection Conditions
- Property 7: Signal Direction Determination
"""

import pytest
from hypothesis import given, strategies as st, settings

from src.kinetic_empire.wave_rider.signal_generator import WaveRiderSignalGenerator
from src.kinetic_empire.wave_rider.models import (
    MoverData,
    MTFResult,
    TimeframeAnalysis,
    TrendDirection,
    SpikeClassification,
    WaveRiderConfig,
)


def make_mover(
    symbol: str = "BTCUSDT",
    price: float = 50000.0,
    volume_ratio: float = 3.0,
    momentum_score: float = 10.0,
    spike: SpikeClassification = SpikeClassification.STRONG,
) -> MoverData:
    """Create a MoverData for testing."""
    return MoverData(
        symbol=symbol,
        price=price,
        price_change_pct=3.0,
        volume_24h=100_000_000,
        volume_ratio=volume_ratio,
        momentum_score=momentum_score,
        spike_classification=spike,
    )


def make_mtf_result(
    alignment_score: int = 100,
    dominant: TrendDirection = TrendDirection.BULLISH,
    price_vs_vwap: str = "ABOVE",
    rsi_1m: float = 50.0,
) -> MTFResult:
    """Create an MTFResult for testing."""
    analyses = {
        "1m": TimeframeAnalysis("1m", 100, 99, rsi_1m, 99.5, dominant, 101),
        "5m": TimeframeAnalysis("5m", 100, 99, 55, 99.5, dominant, 101),
        "15m": TimeframeAnalysis("15m", 100, 99, 55, 99.5, dominant, 101),
    }
    return MTFResult(
        analyses=analyses,
        alignment_score=alignment_score,
        dominant_direction=dominant,
        price_vs_vwap=price_vs_vwap,
    )


class TestWaveRiderSignalGenerator:
    """Unit tests for WaveRiderSignalGenerator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = WaveRiderSignalGenerator()
    
    def test_valid_long_signal(self):
        """Test generating a valid LONG signal."""
        mover = make_mover(volume_ratio=3.5)
        mtf = make_mtf_result(
            alignment_score=100,
            dominant=TrendDirection.BULLISH,
            price_vs_vwap="ABOVE",
        )
        
        signal = self.generator.evaluate(
            mover=mover,
            mtf_result=mtf,
            is_blacklisted=False,
            current_exposure=0.0,
        )
        
        assert signal is not None
        assert signal.direction == "LONG"
        assert signal.symbol == "BTCUSDT"
    
    def test_valid_short_signal(self):
        """Test generating a valid SHORT signal."""
        mover = make_mover(volume_ratio=3.5)
        mtf = make_mtf_result(
            alignment_score=100,
            dominant=TrendDirection.BEARISH,
            price_vs_vwap="BELOW",
        )
        
        signal = self.generator.evaluate(
            mover=mover,
            mtf_result=mtf,
            is_blacklisted=False,
            current_exposure=0.0,
        )
        
        assert signal is not None
        assert signal.direction == "SHORT"
    
    def test_reject_low_volume_ratio(self):
        """Test rejection when volume ratio < 2.0."""
        mover = make_mover(volume_ratio=1.5)
        mtf = make_mtf_result()
        
        signal = self.generator.evaluate(
            mover=mover,
            mtf_result=mtf,
            is_blacklisted=False,
            current_exposure=0.0,
        )
        
        assert signal is None
    
    def test_reject_low_alignment(self):
        """Test rejection when alignment score < 70."""
        mover = make_mover(volume_ratio=3.0)
        mtf = make_mtf_result(alignment_score=40)
        
        signal = self.generator.evaluate(
            mover=mover,
            mtf_result=mtf,
            is_blacklisted=False,
            current_exposure=0.0,
        )
        
        assert signal is None
    
    def test_reject_rsi_oversold(self):
        """Test rejection when RSI < 25."""
        mover = make_mover(volume_ratio=3.0)
        mtf = make_mtf_result(rsi_1m=20.0)
        
        signal = self.generator.evaluate(
            mover=mover,
            mtf_result=mtf,
            is_blacklisted=False,
            current_exposure=0.0,
        )
        
        assert signal is None
    
    def test_reject_rsi_overbought(self):
        """Test rejection when RSI > 75."""
        mover = make_mover(volume_ratio=3.0)
        mtf = make_mtf_result(rsi_1m=80.0)
        
        signal = self.generator.evaluate(
            mover=mover,
            mtf_result=mtf,
            is_blacklisted=False,
            current_exposure=0.0,
        )
        
        assert signal is None
    
    def test_reject_blacklisted(self):
        """Test rejection when symbol is blacklisted."""
        mover = make_mover(volume_ratio=3.0)
        mtf = make_mtf_result()
        
        signal = self.generator.evaluate(
            mover=mover,
            mtf_result=mtf,
            is_blacklisted=True,
            current_exposure=0.0,
        )
        
        assert signal is None
    
    def test_reject_max_exposure(self):
        """Test rejection when at max exposure."""
        mover = make_mover(volume_ratio=3.0)
        mtf = make_mtf_result()
        
        signal = self.generator.evaluate(
            mover=mover,
            mtf_result=mtf,
            is_blacklisted=False,
            current_exposure=0.45,  # At max
        )
        
        assert signal is None
    
    def test_no_direction_when_mixed(self):
        """Test no signal when VWAP and trend don't align."""
        mover = make_mover(volume_ratio=3.0)
        mtf = make_mtf_result(
            dominant=TrendDirection.BULLISH,
            price_vs_vwap="BELOW",  # Mismatch
        )
        
        signal = self.generator.evaluate(
            mover=mover,
            mtf_result=mtf,
            is_blacklisted=False,
            current_exposure=0.0,
        )
        
        assert signal is None


class TestEntryRejectionProperty:
    """Property-based tests for Entry Rejection Conditions.
    
    Property 6: Entry Rejection Conditions
    Signal is rejected if:
    - volume_ratio < 2.0
    - alignment_score < 70
    - RSI < 25 or RSI > 75
    - symbol is blacklisted
    - current_exposure >= 45%
    
    Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5
    """
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = WaveRiderSignalGenerator()
    
    @given(st.floats(min_value=0.0, max_value=1.999, allow_nan=False, allow_infinity=False))
    def test_property_reject_low_volume_ratio(self, volume_ratio: float):
        """Property: volume_ratio < 2.0 => rejected."""
        result = self.generator.check_entry_conditions(
            volume_ratio=volume_ratio,
            alignment_score=100,
            rsi=50.0,
            is_blacklisted=False,
            current_exposure=0.0,
        )
        assert result is False
    
    @given(st.sampled_from([40]))
    def test_property_reject_low_alignment(self, alignment_score: int):
        """Property: alignment_score < 70 => rejected."""
        result = self.generator.check_entry_conditions(
            volume_ratio=3.0,
            alignment_score=alignment_score,
            rsi=50.0,
            is_blacklisted=False,
            current_exposure=0.0,
        )
        assert result is False
    
    @given(st.floats(min_value=0.0, max_value=24.9, allow_nan=False, allow_infinity=False))
    def test_property_reject_rsi_below_25(self, rsi: float):
        """Property: RSI < 25 => rejected."""
        result = self.generator.check_entry_conditions(
            volume_ratio=3.0,
            alignment_score=100,
            rsi=rsi,
            is_blacklisted=False,
            current_exposure=0.0,
        )
        assert result is False
    
    @given(st.floats(min_value=75.1, max_value=100.0, allow_nan=False, allow_infinity=False))
    def test_property_reject_rsi_above_75(self, rsi: float):
        """Property: RSI > 75 => rejected."""
        result = self.generator.check_entry_conditions(
            volume_ratio=3.0,
            alignment_score=100,
            rsi=rsi,
            is_blacklisted=False,
            current_exposure=0.0,
        )
        assert result is False
    
    def test_property_reject_blacklisted(self):
        """Property: blacklisted => rejected."""
        result = self.generator.check_entry_conditions(
            volume_ratio=3.0,
            alignment_score=100,
            rsi=50.0,
            is_blacklisted=True,
            current_exposure=0.0,
        )
        assert result is False
    
    @given(st.floats(min_value=0.45, max_value=1.0, allow_nan=False, allow_infinity=False))
    def test_property_reject_max_exposure(self, current_exposure: float):
        """Property: exposure >= 45% => rejected."""
        result = self.generator.check_entry_conditions(
            volume_ratio=3.0,
            alignment_score=100,
            rsi=50.0,
            is_blacklisted=False,
            current_exposure=current_exposure,
        )
        assert result is False
    
    @given(
        volume_ratio=st.floats(min_value=2.0, max_value=10.0, allow_nan=False, allow_infinity=False),
        alignment_score=st.sampled_from([70, 100]),
        rsi=st.floats(min_value=25.0, max_value=75.0, allow_nan=False, allow_infinity=False),
        current_exposure=st.floats(min_value=0.0, max_value=0.44, allow_nan=False, allow_infinity=False),
    )
    def test_property_accept_valid_conditions(
        self, volume_ratio: float, alignment_score: int, rsi: float, current_exposure: float
    ):
        """Property: All conditions met => accepted."""
        result = self.generator.check_entry_conditions(
            volume_ratio=volume_ratio,
            alignment_score=alignment_score,
            rsi=rsi,
            is_blacklisted=False,
            current_exposure=current_exposure,
        )
        assert result is True


class TestSignalDirectionProperty:
    """Property-based tests for Signal Direction Determination.
    
    Property 7: Signal Direction Determination
    - LONG: price > VWAP AND majority BULLISH
    - SHORT: price < VWAP AND majority BEARISH
    
    Validates: Requirements 4.6, 4.7
    """
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = WaveRiderSignalGenerator()
    
    def test_property_long_when_above_vwap_and_bullish(self):
        """Property: price > VWAP AND BULLISH => LONG."""
        mtf = make_mtf_result(
            dominant=TrendDirection.BULLISH,
            price_vs_vwap="ABOVE",
        )
        direction = self.generator._determine_direction(mtf)
        assert direction == "LONG"
    
    def test_property_short_when_below_vwap_and_bearish(self):
        """Property: price < VWAP AND BEARISH => SHORT."""
        mtf = make_mtf_result(
            dominant=TrendDirection.BEARISH,
            price_vs_vwap="BELOW",
        )
        direction = self.generator._determine_direction(mtf)
        assert direction == "SHORT"
    
    def test_property_no_direction_bullish_below_vwap(self):
        """Property: BULLISH but below VWAP => no direction."""
        mtf = make_mtf_result(
            dominant=TrendDirection.BULLISH,
            price_vs_vwap="BELOW",
        )
        direction = self.generator._determine_direction(mtf)
        assert direction is None
    
    def test_property_no_direction_bearish_above_vwap(self):
        """Property: BEARISH but above VWAP => no direction."""
        mtf = make_mtf_result(
            dominant=TrendDirection.BEARISH,
            price_vs_vwap="ABOVE",
        )
        direction = self.generator._determine_direction(mtf)
        assert direction is None
    
    def test_property_no_direction_neutral(self):
        """Property: NEUTRAL => no direction."""
        mtf = make_mtf_result(
            dominant=TrendDirection.NEUTRAL,
            price_vs_vwap="ABOVE",
        )
        direction = self.generator._determine_direction(mtf)
        assert direction is None
