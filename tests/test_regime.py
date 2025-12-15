"""Tests for regime classification module.

**Feature: kinetic-empire, Property 7: Regime Classification Determinism**
**Feature: kinetic-empire, Property 8: Regime Determines Max Trades**
**Validates: Requirements 4.1, 4.2, 4.3, 4.4**
"""

import pytest
from hypothesis import given, strategies as st, settings

from kinetic_empire.models import Regime
from kinetic_empire.risk import RegimeClassifier


class TestRegimeClassificationDeterminism:
    """Property tests for regime classification determinism.
    
    **Feature: kinetic-empire, Property 7: Regime Classification Determinism**
    **Validates: Requirements 4.1, 4.2**
    """

    @given(
        btc_close=st.floats(min_value=1000, max_value=200000, allow_nan=False),
        btc_ema50=st.floats(min_value=1000, max_value=200000, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_regime_classification_is_deterministic(
        self, btc_close: float, btc_ema50: float
    ):
        """For any BTC close and EMA50, classification SHALL be deterministic."""
        classifier = RegimeClassifier()
        
        # Call classify multiple times
        result1 = classifier.classify(btc_close, btc_ema50)
        result2 = classifier.classify(btc_close, btc_ema50)
        result3 = classifier.classify(btc_close, btc_ema50)
        
        # All results should be identical
        assert result1 == result2 == result3, \
            "Regime classification should be deterministic"

    @given(
        btc_close=st.floats(min_value=1000, max_value=200000, allow_nan=False),
        btc_ema50=st.floats(min_value=1000, max_value=200000, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_bull_when_close_above_ema(self, btc_close: float, btc_ema50: float):
        """Regime SHALL be BULL when close > ema50."""
        classifier = RegimeClassifier()
        
        if btc_close > btc_ema50:
            regime = classifier.classify(btc_close, btc_ema50)
            assert regime == Regime.BULL, \
                f"Expected BULL when close ({btc_close}) > ema50 ({btc_ema50})"

    @given(
        btc_close=st.floats(min_value=1000, max_value=200000, allow_nan=False),
        btc_ema50=st.floats(min_value=1000, max_value=200000, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_bear_when_close_at_or_below_ema(self, btc_close: float, btc_ema50: float):
        """Regime SHALL be BEAR when close <= ema50."""
        classifier = RegimeClassifier()
        
        if btc_close <= btc_ema50:
            regime = classifier.classify(btc_close, btc_ema50)
            assert regime == Regime.BEAR, \
                f"Expected BEAR when close ({btc_close}) <= ema50 ({btc_ema50})"


class TestRegimeDeterminesMaxTrades:
    """Property tests for regime determining max trades.
    
    **Feature: kinetic-empire, Property 8: Regime Determines Max Trades**
    **Validates: Requirements 4.3, 4.4**
    """

    @given(
        btc_close=st.floats(min_value=1000, max_value=200000, allow_nan=False),
        btc_ema50=st.floats(min_value=1000, max_value=200000, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_bull_regime_allows_20_trades(self, btc_close: float, btc_ema50: float):
        """For BULL regime, max_trades SHALL be exactly 20."""
        classifier = RegimeClassifier()
        
        if btc_close > btc_ema50:
            regime = classifier.classify(btc_close, btc_ema50)
            max_trades = classifier.get_max_trades(regime)
            assert max_trades == 20, \
                f"BULL regime should allow 20 trades, got {max_trades}"

    @given(
        btc_close=st.floats(min_value=1000, max_value=200000, allow_nan=False),
        btc_ema50=st.floats(min_value=1000, max_value=200000, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_bear_regime_allows_3_trades(self, btc_close: float, btc_ema50: float):
        """For BEAR regime, max_trades SHALL be exactly 3."""
        classifier = RegimeClassifier()
        
        if btc_close <= btc_ema50:
            regime = classifier.classify(btc_close, btc_ema50)
            max_trades = classifier.get_max_trades(regime)
            assert max_trades == 3, \
                f"BEAR regime should allow 3 trades, got {max_trades}"

    def test_max_trades_for_bull_enum(self):
        """get_max_trades(BULL) SHALL return exactly 20."""
        classifier = RegimeClassifier()
        assert classifier.get_max_trades(Regime.BULL) == 20

    def test_max_trades_for_bear_enum(self):
        """get_max_trades(BEAR) SHALL return exactly 3."""
        classifier = RegimeClassifier()
        assert classifier.get_max_trades(Regime.BEAR) == 3


class TestRegimeEdgeCases:
    """Unit tests for regime classification edge cases."""

    def test_exact_equality_is_bear(self):
        """When close == ema50, regime SHALL be BEAR."""
        classifier = RegimeClassifier()
        regime = classifier.classify(50000.0, 50000.0)
        assert regime == Regime.BEAR

    def test_very_small_difference_above(self):
        """Very small positive difference SHALL be BULL."""
        classifier = RegimeClassifier()
        regime = classifier.classify(50000.01, 50000.0)
        assert regime == Regime.BULL

    def test_very_small_difference_below(self):
        """Very small negative difference SHALL be BEAR."""
        classifier = RegimeClassifier()
        regime = classifier.classify(49999.99, 50000.0)
        assert regime == Regime.BEAR

    def test_can_open_trade_bull_under_limit(self):
        """In BULL with < 20 trades, can_open_trade SHALL return True."""
        classifier = RegimeClassifier()
        assert classifier.can_open_trade(Regime.BULL, 0) is True
        assert classifier.can_open_trade(Regime.BULL, 10) is True
        assert classifier.can_open_trade(Regime.BULL, 19) is True

    def test_can_open_trade_bull_at_limit(self):
        """In BULL with >= 20 trades, can_open_trade SHALL return False."""
        classifier = RegimeClassifier()
        assert classifier.can_open_trade(Regime.BULL, 20) is False
        assert classifier.can_open_trade(Regime.BULL, 25) is False

    def test_can_open_trade_bear_under_limit(self):
        """In BEAR with < 3 trades, can_open_trade SHALL return True."""
        classifier = RegimeClassifier()
        assert classifier.can_open_trade(Regime.BEAR, 0) is True
        assert classifier.can_open_trade(Regime.BEAR, 1) is True
        assert classifier.can_open_trade(Regime.BEAR, 2) is True

    def test_can_open_trade_bear_at_limit(self):
        """In BEAR with >= 3 trades, can_open_trade SHALL return False."""
        classifier = RegimeClassifier()
        assert classifier.can_open_trade(Regime.BEAR, 3) is False
        assert classifier.can_open_trade(Regime.BEAR, 5) is False

    def test_get_regime_info_bull(self):
        """get_regime_info SHALL return complete info for BULL."""
        classifier = RegimeClassifier()
        info = classifier.get_regime_info(55000.0, 50000.0)
        
        assert info["regime"] == Regime.BULL
        assert info["max_trades"] == 20
        assert info["btc_close"] == 55000.0
        assert info["btc_ema50"] == 50000.0
        assert info["price_above_ema"] is True

    def test_get_regime_info_bear(self):
        """get_regime_info SHALL return complete info for BEAR."""
        classifier = RegimeClassifier()
        info = classifier.get_regime_info(45000.0, 50000.0)
        
        assert info["regime"] == Regime.BEAR
        assert info["max_trades"] == 3
        assert info["btc_close"] == 45000.0
        assert info["btc_ema50"] == 50000.0
        assert info["price_above_ema"] is False

    def test_custom_btc_pair(self):
        """Classifier SHALL accept custom BTC pair."""
        classifier = RegimeClassifier(btc_pair="BTC/BUSD")
        assert classifier.btc_pair == "BTC/BUSD"

    def test_custom_ema_period(self):
        """Classifier SHALL accept custom EMA period."""
        classifier = RegimeClassifier(ema_period=200)
        assert classifier.ema_period == 200
