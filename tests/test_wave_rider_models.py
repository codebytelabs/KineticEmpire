"""Unit tests for Wave Rider data models.

Tests dataclass creation, validation, and enum values.
"""

import pytest
from src.kinetic_empire.wave_rider.models import (
    SpikeClassification,
    TrendDirection,
    OHLCV,
    MoverData,
    TimeframeAnalysis,
    MTFResult,
    WaveRiderSignal,
    TrailingState,
    WaveRiderConfig,
)


class TestSpikeClassification:
    """Tests for SpikeClassification enum."""
    
    def test_enum_values(self):
        """Test all spike classification values exist."""
        assert SpikeClassification.NONE.value == "none"
        assert SpikeClassification.NORMAL.value == "normal"
        assert SpikeClassification.STRONG.value == "strong"
        assert SpikeClassification.EXTREME.value == "extreme"
    
    def test_enum_count(self):
        """Test correct number of classifications."""
        assert len(SpikeClassification) == 4


class TestTrendDirection:
    """Tests for TrendDirection enum."""
    
    def test_enum_values(self):
        """Test all trend direction values exist."""
        assert TrendDirection.BULLISH.value == "BULLISH"
        assert TrendDirection.BEARISH.value == "BEARISH"
        assert TrendDirection.NEUTRAL.value == "NEUTRAL"
    
    def test_enum_count(self):
        """Test correct number of directions."""
        assert len(TrendDirection) == 3


class TestOHLCV:
    """Tests for OHLCV dataclass."""
    
    def test_creation(self):
        """Test OHLCV creation with all fields."""
        ohlcv = OHLCV(
            open=100.0,
            high=105.0,
            low=99.0,
            close=103.0,
            volume=1000.0,
            timestamp=1234567890,
        )
        assert ohlcv.open == 100.0
        assert ohlcv.high == 105.0
        assert ohlcv.low == 99.0
        assert ohlcv.close == 103.0
        assert ohlcv.volume == 1000.0
        assert ohlcv.timestamp == 1234567890
    
    def test_default_timestamp(self):
        """Test OHLCV with default timestamp."""
        ohlcv = OHLCV(open=100.0, high=105.0, low=99.0, close=103.0, volume=1000.0)
        assert ohlcv.timestamp == 0


class TestMoverData:
    """Tests for MoverData dataclass."""
    
    def test_creation(self):
        """Test MoverData creation with all fields."""
        mover = MoverData(
            symbol="BTCUSDT",
            price=50000.0,
            price_change_pct=2.5,
            volume_24h=1_000_000_000,
            volume_ratio=3.5,
            momentum_score=8.75,
            spike_classification=SpikeClassification.STRONG,
        )
        assert mover.symbol == "BTCUSDT"
        assert mover.price == 50000.0
        assert mover.price_change_pct == 2.5
        assert mover.volume_24h == 1_000_000_000
        assert mover.volume_ratio == 3.5
        assert mover.momentum_score == 8.75
        assert mover.spike_classification == SpikeClassification.STRONG
    
    def test_default_spike_classification(self):
        """Test MoverData with default spike classification."""
        mover = MoverData(
            symbol="ETHUSDT",
            price=3000.0,
            price_change_pct=1.0,
            volume_24h=500_000_000,
            volume_ratio=1.5,
            momentum_score=1.5,
        )
        assert mover.spike_classification == SpikeClassification.NONE


class TestTimeframeAnalysis:
    """Tests for TimeframeAnalysis dataclass."""
    
    def test_creation(self):
        """Test TimeframeAnalysis creation."""
        analysis = TimeframeAnalysis(
            timeframe="5m",
            ema_fast=50100.0,
            ema_slow=50000.0,
            rsi=55.0,
            vwap=50050.0,
            trend_direction=TrendDirection.BULLISH,
            price=50150.0,
        )
        assert analysis.timeframe == "5m"
        assert analysis.ema_fast == 50100.0
        assert analysis.ema_slow == 50000.0
        assert analysis.rsi == 55.0
        assert analysis.vwap == 50050.0
        assert analysis.trend_direction == TrendDirection.BULLISH
        assert analysis.price == 50150.0


class TestMTFResult:
    """Tests for MTFResult dataclass."""
    
    def test_creation(self):
        """Test MTFResult creation."""
        analyses = {
            "1m": TimeframeAnalysis("1m", 100, 99, 55, 99.5, TrendDirection.BULLISH, 101),
            "5m": TimeframeAnalysis("5m", 100, 99, 60, 99.5, TrendDirection.BULLISH, 101),
            "15m": TimeframeAnalysis("15m", 99, 100, 45, 99.5, TrendDirection.BEARISH, 98),
        }
        result = MTFResult(
            analyses=analyses,
            alignment_score=70,
            dominant_direction=TrendDirection.BULLISH,
            price_vs_vwap="ABOVE",
        )
        assert len(result.analyses) == 3
        assert result.alignment_score == 70
        assert result.dominant_direction == TrendDirection.BULLISH
        assert result.price_vs_vwap == "ABOVE"


class TestWaveRiderSignal:
    """Tests for WaveRiderSignal dataclass."""
    
    def test_creation(self):
        """Test WaveRiderSignal creation."""
        signal = WaveRiderSignal(
            symbol="SOLUSDT",
            direction="LONG",
            volume_ratio=3.5,
            spike_classification=SpikeClassification.STRONG,
            alignment_score=100,
            rsi_1m=55.0,
            position_size_pct=0.07,
            leverage=5,
            stop_loss_pct=0.015,
            confidence_score=85,
            entry_price=150.0,
        )
        assert signal.symbol == "SOLUSDT"
        assert signal.direction == "LONG"
        assert signal.volume_ratio == 3.5
        assert signal.spike_classification == SpikeClassification.STRONG
        assert signal.alignment_score == 100
        assert signal.rsi_1m == 55.0
        assert signal.position_size_pct == 0.07
        assert signal.leverage == 5
        assert signal.stop_loss_pct == 0.015
        assert signal.confidence_score == 85
        assert signal.entry_price == 150.0
    
    def test_default_entry_price(self):
        """Test WaveRiderSignal with default entry price."""
        signal = WaveRiderSignal(
            symbol="BTCUSDT",
            direction="SHORT",
            volume_ratio=2.5,
            spike_classification=SpikeClassification.NORMAL,
            alignment_score=70,
            rsi_1m=65.0,
            position_size_pct=0.05,
            leverage=3,
            stop_loss_pct=0.02,
            confidence_score=70,
        )
        assert signal.entry_price == 0.0


class TestTrailingState:
    """Tests for TrailingState dataclass."""
    
    def test_default_values(self):
        """Test TrailingState default values."""
        state = TrailingState()
        assert state.is_active is False
        assert state.peak_price == 0.0
        assert state.peak_profit_pct == 0.0
        assert state.trail_multiplier == 0.8
        assert state.tp1_done is False
        assert state.tp2_done is False
    
    def test_custom_values(self):
        """Test TrailingState with custom values."""
        state = TrailingState(
            is_active=True,
            peak_price=51000.0,
            peak_profit_pct=3.5,
            trail_multiplier=0.5,
            tp1_done=True,
            tp2_done=True,
        )
        assert state.is_active is True
        assert state.peak_price == 51000.0
        assert state.peak_profit_pct == 3.5
        assert state.trail_multiplier == 0.5
        assert state.tp1_done is True
        assert state.tp2_done is True


class TestWaveRiderConfig:
    """Tests for WaveRiderConfig dataclass."""
    
    def test_default_values(self):
        """Test WaveRiderConfig default values."""
        config = WaveRiderConfig()
        
        # Scan settings
        assert config.scan_interval == 15
        assert config.monitor_interval == 5
        assert config.top_movers_limit == 20
        assert config.min_24h_volume == 10_000_000
        
        # Position limits
        assert config.max_positions == 5
        assert config.max_exposure == 0.45
        
        # Risk management
        assert config.daily_loss_limit == 0.03
        assert config.max_consecutive_losses == 2
        assert config.blacklist_duration_minutes == 30
        
        # Entry thresholds
        assert config.min_volume_ratio == 2.0
        assert config.min_alignment_score == 70
        assert config.rsi_min == 25
        assert config.rsi_max == 75
        
        # Stop loss bounds
        assert config.stop_atr_multiplier == 1.5
        assert config.min_stop_pct == 0.005
        assert config.max_stop_pct == 0.03
        
        # Trailing stop settings
        assert config.trailing_activation_pct == 0.01
        assert config.initial_trail_multiplier == 0.8
        assert config.tight_trail_multiplier == 0.5
        assert config.tight_threshold_pct == 0.03
        
        # Take profit settings
        assert config.tp1_profit_pct == 0.015
        assert config.tp1_close_pct == 0.30
        assert config.tp2_profit_pct == 0.025
        assert config.tp2_close_pct == 0.30
    
    def test_custom_values(self):
        """Test WaveRiderConfig with custom values."""
        config = WaveRiderConfig(
            scan_interval=10,
            max_positions=3,
            daily_loss_limit=0.05,
        )
        assert config.scan_interval == 10
        assert config.max_positions == 3
        assert config.daily_loss_limit == 0.05
        # Other values should still be defaults
        assert config.monitor_interval == 5
