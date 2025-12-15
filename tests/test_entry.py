"""Tests for entry signal generation module.

**Feature: kinetic-empire, Property 6: Entry Signal Requires All Conditions**
**Feature: kinetic-empire, Property 9: Trade Limit Enforcement**
**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 4.5**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume

from kinetic_empire.models import Regime
from kinetic_empire.strategy import EntrySignalGenerator, EntryConfig, MarketState


# Strategies for generating test data
@st.composite
def market_state_strategy(draw):
    """Generate random MarketState objects."""
    return MarketState(
        close_1h=draw(st.floats(min_value=100, max_value=100000, allow_nan=False)),
        ema50_1h=draw(st.floats(min_value=100, max_value=100000, allow_nan=False)),
        close_5m=draw(st.floats(min_value=100, max_value=100000, allow_nan=False)),
        ema50_5m=draw(st.floats(min_value=100, max_value=100000, allow_nan=False)),
        roc_12=draw(st.floats(min_value=-10, max_value=20, allow_nan=False)),
        rsi_14=draw(st.floats(min_value=0, max_value=100, allow_nan=False)),
        volume=draw(st.floats(min_value=0, max_value=1e12, allow_nan=False)),
        mean_volume_24h=draw(st.floats(min_value=1, max_value=1e12, allow_nan=False)),
    )


@st.composite
def valid_entry_state_strategy(draw, regime: Regime = None):
    """Generate MarketState that passes all entry conditions.
    
    RSI zones by regime (with optimizer):
    - BULL: 35-70
    - BEAR: 45-60
    
    For compatibility with both regimes, use 46-59 range.
    """
    # Generate base values
    ema50_1h = draw(st.floats(min_value=1000, max_value=50000, allow_nan=False))
    ema50_5m = draw(st.floats(min_value=1000, max_value=50000, allow_nan=False))
    mean_volume = draw(st.floats(min_value=1000, max_value=1e9, allow_nan=False))
    
    return MarketState(
        close_1h=ema50_1h * 1.01,  # Above EMA
        ema50_1h=ema50_1h,
        close_5m=ema50_5m * 1.01,  # Above EMA
        ema50_5m=ema50_5m,
        roc_12=draw(st.floats(min_value=1.6, max_value=10, allow_nan=False)),  # > 1.5
        rsi_14=draw(st.floats(min_value=46, max_value=59, allow_nan=False)),  # Valid for both BULL (35-70) and BEAR (45-60)
        volume=mean_volume * 1.1,  # Above mean
        mean_volume_24h=mean_volume,
    )


class TestEntrySignalRequiresAllConditions:
    """Property tests for entry signal requiring all conditions.
    
    **Feature: kinetic-empire, Property 6: Entry Signal Requires All Conditions**
    **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**
    """

    @given(state=market_state_strategy(), regime=st.sampled_from([Regime.BULL, Regime.BEAR]))
    @settings(max_examples=100)
    def test_entry_signal_iff_all_conditions_met(self, state: MarketState, regime: Regime):
        """BUY signal SHALL be generated if and only if ALL conditions are true."""
        generator = EntrySignalGenerator()
        open_trades = 0  # Under limit for both regimes
        
        # Calculate expected result based on all conditions
        macro_ok = state.close_1h > state.ema50_1h
        micro_ok = state.close_5m > state.ema50_5m
        momentum_ok = state.roc_12 > 1.5
        
        # RSI zones are regime-specific with optimizer:
        # BULL: 35-70, BEAR: 45-60
        if regime == Regime.BULL:
            pullback_ok = 35 <= state.rsi_14 <= 70
        else:  # BEAR
            pullback_ok = 45 <= state.rsi_14 <= 60
        
        volume_ok = state.volume > state.mean_volume_24h
        
        expected = macro_ok and micro_ok and momentum_ok and pullback_ok and volume_ok
        
        result = generator.check_entry_conditions(state, regime, open_trades)
        
        assert result == expected, \
            f"Entry signal mismatch: expected {expected}, got {result}"

    @given(state=valid_entry_state_strategy())
    @settings(max_examples=100)
    def test_valid_state_generates_entry_signal(self, state: MarketState):
        """For any valid entry state, a BUY signal SHALL be generated."""
        generator = EntrySignalGenerator()
        
        # With 0 open trades, should always pass trade limit
        result = generator.check_entry_conditions(state, Regime.BULL, 0)
        
        assert result is True, \
            f"Valid state should generate entry signal"

    def test_macro_trend_failure_blocks_entry(self):
        """When macro trend fails, entry SHALL be blocked."""
        generator = EntrySignalGenerator()
        state = MarketState(
            close_1h=49000,  # Below EMA
            ema50_1h=50000,
            close_5m=51000,
            ema50_5m=50000,
            roc_12=2.0,
            rsi_14=55,
            volume=1e9,
            mean_volume_24h=5e8,
        )
        
        assert generator.check_entry_conditions(state, Regime.BULL, 0) is False

    def test_micro_trend_failure_blocks_entry(self):
        """When micro trend fails, entry SHALL be blocked."""
        generator = EntrySignalGenerator()
        state = MarketState(
            close_1h=51000,
            ema50_1h=50000,
            close_5m=49000,  # Below EMA
            ema50_5m=50000,
            roc_12=2.0,
            rsi_14=55,
            volume=1e9,
            mean_volume_24h=5e8,
        )
        
        assert generator.check_entry_conditions(state, Regime.BULL, 0) is False

    def test_momentum_failure_blocks_entry(self):
        """When momentum fails, entry SHALL be blocked."""
        generator = EntrySignalGenerator()
        state = MarketState(
            close_1h=51000,
            ema50_1h=50000,
            close_5m=51000,
            ema50_5m=50000,
            roc_12=1.0,  # Below threshold
            rsi_14=55,
            volume=1e9,
            mean_volume_24h=5e8,
        )
        
        assert generator.check_entry_conditions(state, Regime.BULL, 0) is False

    def test_pullback_failure_blocks_entry_overbought(self):
        """When RSI is overbought (above regime max), entry SHALL be blocked."""
        generator = EntrySignalGenerator()
        state = MarketState(
            close_1h=51000,
            ema50_1h=50000,
            close_5m=51000,
            ema50_5m=50000,
            roc_12=2.0,
            rsi_14=75,  # Above BULL max of 70
            volume=1e9,
            mean_volume_24h=5e8,
        )
        
        assert generator.check_entry_conditions(state, Regime.BULL, 0) is False

    def test_pullback_failure_blocks_entry_oversold(self):
        """When RSI is oversold (below regime min), entry SHALL be blocked."""
        generator = EntrySignalGenerator()
        state = MarketState(
            close_1h=51000,
            ema50_1h=50000,
            close_5m=51000,
            ema50_5m=50000,
            roc_12=2.0,
            rsi_14=30,  # Below BULL min of 35
            volume=1e9,
            mean_volume_24h=5e8,
        )
        
        assert generator.check_entry_conditions(state, Regime.BULL, 0) is False

    def test_volume_failure_blocks_entry(self):
        """When volume is below mean, entry SHALL be blocked."""
        generator = EntrySignalGenerator()
        state = MarketState(
            close_1h=51000,
            ema50_1h=50000,
            close_5m=51000,
            ema50_5m=50000,
            roc_12=2.0,
            rsi_14=55,
            volume=4e8,  # Below mean
            mean_volume_24h=5e8,
        )
        
        assert generator.check_entry_conditions(state, Regime.BULL, 0) is False



class TestTradeLimitEnforcement:
    """Property tests for trade limit enforcement.
    
    **Feature: kinetic-empire, Property 9: Trade Limit Enforcement**
    **Validates: Requirements 4.5**
    """

    @given(
        open_trades=st.integers(min_value=0, max_value=30),
        state=valid_entry_state_strategy()
    )
    @settings(max_examples=100)
    def test_bull_regime_trade_limit(self, open_trades: int, state: MarketState):
        """In BULL regime, trades SHALL be rejected when open_trades >= 20."""
        generator = EntrySignalGenerator()
        
        result = generator.check_entry_conditions(state, Regime.BULL, open_trades)
        
        if open_trades >= 20:
            assert result is False, \
                f"Should reject trade when open_trades ({open_trades}) >= 20"
        else:
            # All other conditions are valid, so should pass
            assert result is True, \
                f"Should allow trade when open_trades ({open_trades}) < 20"

    @given(
        open_trades=st.integers(min_value=0, max_value=10),
        state=valid_entry_state_strategy()
    )
    @settings(max_examples=100)
    def test_bear_regime_trade_limit(self, open_trades: int, state: MarketState):
        """In BEAR regime, trades SHALL be rejected when open_trades >= 3."""
        generator = EntrySignalGenerator()
        
        result = generator.check_entry_conditions(state, Regime.BEAR, open_trades)
        
        if open_trades >= 3:
            assert result is False, \
                f"Should reject trade when open_trades ({open_trades}) >= 3"
        else:
            # All other conditions are valid, so should pass
            assert result is True, \
                f"Should allow trade when open_trades ({open_trades}) < 3"

    def test_trade_limit_at_boundary_bull(self):
        """At exactly 20 trades in BULL, new trade SHALL be rejected."""
        generator = EntrySignalGenerator()
        state = MarketState(
            close_1h=51000, ema50_1h=50000,
            close_5m=51000, ema50_5m=50000,
            roc_12=2.0, rsi_14=55,
            volume=1e9, mean_volume_24h=5e8,
        )
        
        assert generator.check_entry_conditions(state, Regime.BULL, 19) is True
        assert generator.check_entry_conditions(state, Regime.BULL, 20) is False

    def test_trade_limit_at_boundary_bear(self):
        """At exactly 3 trades in BEAR, new trade SHALL be rejected."""
        generator = EntrySignalGenerator()
        state = MarketState(
            close_1h=51000, ema50_1h=50000,
            close_5m=51000, ema50_5m=50000,
            roc_12=2.0, rsi_14=55,
            volume=1e9, mean_volume_24h=5e8,
        )
        
        assert generator.check_entry_conditions(state, Regime.BEAR, 2) is True
        assert generator.check_entry_conditions(state, Regime.BEAR, 3) is False


class TestEntryEdgeCases:
    """Unit tests for entry signal edge cases."""

    def test_rsi_at_boundary_45(self):
        """RSI at exactly 45 SHALL NOT pass pullback check."""
        generator = EntrySignalGenerator()
        assert generator.check_pullback(45) is False

    def test_rsi_at_boundary_65(self):
        """RSI at exactly 65 SHALL NOT pass pullback check."""
        generator = EntrySignalGenerator()
        assert generator.check_pullback(65) is False

    def test_rsi_just_inside_range(self):
        """RSI just inside range SHALL pass pullback check."""
        generator = EntrySignalGenerator()
        assert generator.check_pullback(45.01) is True
        assert generator.check_pullback(64.99) is True

    def test_roc_at_boundary(self):
        """ROC at exactly 1.5 SHALL NOT pass momentum check."""
        generator = EntrySignalGenerator()
        assert generator.check_momentum(1.5) is False
        assert generator.check_momentum(1.51) is True

    def test_volume_at_boundary(self):
        """Volume at exactly mean SHALL NOT pass volume check."""
        generator = EntrySignalGenerator()
        assert generator.check_volume(1000, 1000) is False
        assert generator.check_volume(1001, 1000) is True

    def test_custom_config(self):
        """Custom config SHALL be respected."""
        config = EntryConfig(roc_threshold=2.0, rsi_min=40, rsi_max=70)
        generator = EntrySignalGenerator(config)
        
        assert generator.check_momentum(1.5) is False
        assert generator.check_momentum(2.1) is True
        assert generator.check_pullback(42) is True
        assert generator.check_pullback(68) is True

    def test_get_entry_analysis(self):
        """get_entry_analysis SHALL return complete analysis."""
        generator = EntrySignalGenerator()
        state = MarketState(
            close_1h=51000, ema50_1h=50000,
            close_5m=51000, ema50_5m=50000,
            roc_12=2.0, rsi_14=55,
            volume=1e9, mean_volume_24h=5e8,
        )
        
        analysis = generator.get_entry_analysis(state, Regime.BULL, 5)
        
        assert analysis["macro_trend"] is True
        assert analysis["micro_trend"] is True
        assert analysis["momentum"] is True
        assert analysis["pullback"] is True
        assert analysis["volume"] is True
        assert analysis["trade_limit"] is True
        assert analysis["all_conditions_met"] is True
        assert analysis["regime"] == Regime.BULL
        assert analysis["open_trades"] == 5
        assert analysis["max_trades"] == 20

    def test_should_enter_convenience_method(self):
        """should_enter SHALL be equivalent to check_entry_conditions."""
        generator = EntrySignalGenerator()
        state = MarketState(
            close_1h=51000, ema50_1h=50000,
            close_5m=51000, ema50_5m=50000,
            roc_12=2.0, rsi_14=55,
            volume=1e9, mean_volume_24h=5e8,
        )
        
        result1 = generator.should_enter(state, Regime.BULL, 0)
        result2 = generator.check_entry_conditions(state, Regime.BULL, 0)
        
        assert result1 == result2
