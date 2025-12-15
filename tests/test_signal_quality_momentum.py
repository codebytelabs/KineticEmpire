"""Property-based tests for MomentumValidator.

**Feature: signal-quality-fix, Property 5: Momentum Validation**
**Validates: Requirements 5.1, 5.2, 5.3**
"""

import pytest
from hypothesis import given, strategies as st, assume

from src.kinetic_empire.signal_quality.config import QualityGateConfig
from src.kinetic_empire.signal_quality.momentum_validator import MomentumValidator, OHLCV


def make_ohlcv(close: float, volume: float = 1000.0) -> OHLCV:
    """Helper to create OHLCV with just close price."""
    return OHLCV(open=close, high=close * 1.01, low=close * 0.99, close=close, volume=volume)


class TestMomentumValidatorProperties:
    """Property-based tests for momentum validation."""
    
    @given(
        start_price=st.floats(min_value=100, max_value=10000),
        drop_pct=st.floats(min_value=0.6, max_value=5.0)
    )
    def test_price_drop_rejects_long(self, start_price: float, drop_pct: float):
        """Property: Price drop >0.5% SHALL reject LONG signal.
        
        **Feature: signal-quality-fix, Property 5: Momentum Validation**
        **Validates: Requirements 5.1**
        """
        config = QualityGateConfig()
        validator = MomentumValidator(config)
        
        # Create candles with price drop
        end_price = start_price * (1 - drop_pct / 100)
        mid_price = (start_price + end_price) / 2
        ohlcv = [make_ohlcv(start_price), make_ohlcv(mid_price), make_ohlcv(end_price)]
        
        valid, reason = validator.validate("LONG", ohlcv, rsi_15m=50.0)
        
        assert valid is False, f"LONG should be rejected with {drop_pct}% drop"
        assert reason is not None
        assert "contradicts LONG" in reason
    
    @given(
        start_price=st.floats(min_value=100, max_value=10000),
        rise_pct=st.floats(min_value=0.6, max_value=5.0)
    )
    def test_price_rise_rejects_short(self, start_price: float, rise_pct: float):
        """Property: Price rise >0.5% SHALL reject SHORT signal.
        
        **Feature: signal-quality-fix, Property 5: Momentum Validation**
        **Validates: Requirements 5.1**
        """
        config = QualityGateConfig()
        validator = MomentumValidator(config)
        
        # Create candles with price rise
        end_price = start_price * (1 + rise_pct / 100)
        mid_price = (start_price + end_price) / 2
        ohlcv = [make_ohlcv(start_price), make_ohlcv(mid_price), make_ohlcv(end_price)]
        
        valid, reason = validator.validate("SHORT", ohlcv, rsi_15m=50.0)
        
        assert valid is False, f"SHORT should be rejected with {rise_pct}% rise"
        assert reason is not None
        assert "contradicts SHORT" in reason
    
    @given(rsi=st.floats(min_value=80.1, max_value=100.0))
    def test_overbought_rsi_rejects_long(self, rsi: float):
        """Property: RSI > 80 SHALL reject LONG signal (relaxed from 70).
        
        **Feature: signal-quality-fix, Property 5: Momentum Validation**
        **Validates: Requirements 5.2**
        """
        config = QualityGateConfig()
        validator = MomentumValidator(config)
        
        # Neutral price action
        ohlcv = [make_ohlcv(100), make_ohlcv(100), make_ohlcv(100)]
        
        valid, reason = validator.validate("LONG", ohlcv, rsi_15m=rsi)
        
        assert valid is False, f"LONG should be rejected with RSI {rsi}"
        assert reason is not None
        assert "overbought" in reason
    
    @given(rsi=st.floats(min_value=0.0, max_value=19.9))
    def test_oversold_rsi_rejects_short(self, rsi: float):
        """Property: RSI < 20 SHALL reject SHORT signal (relaxed from 30).
        
        **Feature: signal-quality-fix, Property 5: Momentum Validation**
        **Validates: Requirements 5.3**
        """
        config = QualityGateConfig()
        validator = MomentumValidator(config)
        
        # Neutral price action
        ohlcv = [make_ohlcv(100), make_ohlcv(100), make_ohlcv(100)]
        
        valid, reason = validator.validate("SHORT", ohlcv, rsi_15m=rsi)
        
        assert valid is False, f"SHORT should be rejected with RSI {rsi}"
        assert reason is not None
        assert "oversold" in reason


class TestMomentumValidatorEdgeCases:
    """Edge case tests for momentum validation."""
    
    def test_boundary_rsi_80_long_passes(self):
        """RSI exactly at 80 should pass for LONG (relaxed threshold)."""
        validator = MomentumValidator(QualityGateConfig())
        ohlcv = [make_ohlcv(100), make_ohlcv(100), make_ohlcv(100)]
        valid, _ = validator.validate("LONG", ohlcv, rsi_15m=80.0)
        assert valid is True
    
    def test_boundary_rsi_81_long_fails(self):
        """RSI at 81 should fail for LONG (above relaxed threshold)."""
        validator = MomentumValidator(QualityGateConfig())
        ohlcv = [make_ohlcv(100), make_ohlcv(100), make_ohlcv(100)]
        valid, _ = validator.validate("LONG", ohlcv, rsi_15m=81.0)
        assert valid is False
    
    def test_boundary_rsi_20_short_passes(self):
        """RSI exactly at 20 should pass for SHORT (relaxed threshold)."""
        validator = MomentumValidator(QualityGateConfig())
        ohlcv = [make_ohlcv(100), make_ohlcv(100), make_ohlcv(100)]
        valid, _ = validator.validate("SHORT", ohlcv, rsi_15m=20.0)
        assert valid is True
    
    def test_boundary_rsi_19_short_fails(self):
        """RSI at 19 should fail for SHORT (below relaxed threshold)."""
        validator = MomentumValidator(QualityGateConfig())
        ohlcv = [make_ohlcv(100), make_ohlcv(100), make_ohlcv(100)]
        valid, _ = validator.validate("SHORT", ohlcv, rsi_15m=19.0)
        assert valid is False
    
    def test_price_change_exactly_at_threshold(self):
        """Price change exactly at 0.5% should pass."""
        validator = MomentumValidator(QualityGateConfig())
        # 0.5% drop
        ohlcv = [make_ohlcv(100), make_ohlcv(99.75), make_ohlcv(99.5)]
        valid, _ = validator.validate("LONG", ohlcv, rsi_15m=50.0)
        assert valid is True  # Exactly at threshold, not exceeding
    
    def test_insufficient_candles(self):
        """With fewer than 3 candles, price check should be skipped."""
        validator = MomentumValidator(QualityGateConfig())
        ohlcv = [make_ohlcv(100), make_ohlcv(90)]  # Only 2 candles
        valid, _ = validator.validate("LONG", ohlcv, rsi_15m=50.0)
        assert valid is True  # Should pass since we can't check price change
