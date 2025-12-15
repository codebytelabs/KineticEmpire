"""Property-based tests for Trading Optimizations.

Uses Hypothesis for property-based testing with minimum 100 iterations per property.
"""

import pytest
from datetime import datetime, timedelta
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from kinetic_empire.models import Regime
from kinetic_empire.optimizations import (
    TrailingOptimizer,
    PartialProfitTaker,
    HalfKellySizer,
    VolumeTieredSizer,
    VolumeTier,
    RegimeAdaptiveStops,
    RSIZoneOptimizer,
    DynamicBlacklistManager,
    FearGreedAdjuster,
    MicroAlignmentBonus,
    EntryConfirmationManager,
)
from kinetic_empire.optimizations.config import (
    TrailingOptConfig,
    PartialProfitConfig,
    VolumeTierConfig,
    RSIZoneConfig,
    RegimeStopConfig,
    BlacklistDurationConfig,
    FearGreedConfig,
    MicroBonusConfig,
    EntryConfirmConfig,
)


# =============================================================================
# Property 1: Trailing Stop Activation Threshold
# For any position with unrealized profit, trailing stop activates if and only
# if profit >= 1.5%
# Validates: Requirements 1.1
# =============================================================================

@settings(max_examples=100)
@given(profit_pct=st.floats(min_value=-0.5, max_value=0.5, allow_nan=False))
def test_property_1_trailing_activation_threshold(profit_pct: float):
    """Trailing stop activates if and only if profit >= 1.5%."""
    optimizer = TrailingOptimizer()
    
    should_activate = optimizer.should_activate(profit_pct)
    
    if profit_pct >= 0.015:
        assert should_activate, f"Should activate at {profit_pct*100:.2f}% profit"
    else:
        assert not should_activate, f"Should not activate at {profit_pct*100:.2f}% profit"


# =============================================================================
# Property 2: Trailing Stop Tightening
# For any active trailing stop, the trail multiplier is 1.5x ATR when profit < 3%,
# and 1.0x ATR when profit >= 3%
# Validates: Requirements 1.2, 1.3
# =============================================================================

@settings(max_examples=100)
@given(profit_pct=st.floats(min_value=0.0, max_value=0.2, allow_nan=False))
def test_property_2_trailing_tightening(profit_pct: float):
    """Trail multiplier is 1.5x when profit < 3%, 1.0x when profit >= 3%."""
    optimizer = TrailingOptimizer()
    
    multiplier = optimizer.get_trail_multiplier(profit_pct)
    
    if profit_pct >= 0.03:
        assert multiplier == 1.0, f"Should be 1.0x at {profit_pct*100:.2f}% profit"
    else:
        assert multiplier == 1.5, f"Should be 1.5x at {profit_pct*100:.2f}% profit"


# =============================================================================
# Property 3: Partial Profit Taking Levels
# For any position, TP1 triggers at 1.5x ATR profit (closing 25%), and TP2
# triggers at 2.5x ATR profit (closing additional 25%)
# Validates: Requirements 2.1, 2.2, 2.4
# =============================================================================

@settings(max_examples=100)
@given(
    entry_price=st.floats(min_value=10.0, max_value=10000.0, allow_nan=False),
    atr=st.floats(min_value=0.1, max_value=100.0, allow_nan=False),
    profit_mult=st.floats(min_value=0.0, max_value=5.0, allow_nan=False)
)
def test_property_3_partial_profit_levels(entry_price: float, atr: float, profit_mult: float):
    """TP1 at 1.5x ATR, TP2 at 2.5x ATR, each closing 25%."""
    taker = PartialProfitTaker()
    
    # Calculate current price based on profit multiple
    current_price = entry_price + (profit_mult * atr)
    
    # Test TP1 (neither done)
    result = taker.check_tp_levels(entry_price, current_price, atr, "long", False, False)
    
    # Use small epsilon for floating point boundary comparisons
    eps = 1e-9
    if profit_mult >= 2.5 + eps:
        # Should trigger TP2 (but TP1 not done, so TP1 first)
        assert result.tp_level == 1 or result.tp_level == 2
        assert result.close_pct == 0.25
    elif profit_mult >= 1.5 + eps:
        assert result.tp_level == 1
        assert result.close_pct == 0.25
    elif profit_mult <= 1.5 - eps:
        assert result.tp_level == 0
        assert result.close_pct == 0.0
    # else: boundary case, either result is acceptable
    
    # Test TP2 (TP1 already done)
    result2 = taker.check_tp_levels(entry_price, current_price, atr, "long", True, False)
    
    if profit_mult >= 2.5:
        assert result2.tp_level == 2
        assert result2.close_pct == 0.25
    else:
        assert result2.tp_level == 0


# =============================================================================
# Property 4: Half-Kelly Calculation
# For any win rate and reward/risk ratio, the Half-Kelly stake equals
# 0.5 * full Kelly fraction, clamped to [min_stake, max_stake]
# Validates: Requirements 3.1, 3.2, 3.3
# =============================================================================

@settings(max_examples=100)
@given(
    win_rate=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    rr_ratio=st.floats(min_value=0.1, max_value=5.0, allow_nan=False)
)
def test_property_4_half_kelly_calculation(win_rate: float, rr_ratio: float):
    """Half-Kelly equals 0.5 * full Kelly, clamped to bounds."""
    sizer = HalfKellySizer()
    
    full_kelly = sizer.calculate_full_kelly(win_rate, rr_ratio)
    half_kelly = sizer.calculate_half_kelly(win_rate, rr_ratio)
    
    # Half-Kelly should be exactly 0.5 * full Kelly
    assert abs(half_kelly - (full_kelly * 0.5)) < 1e-10
    
    # When converted to stake percentage and clamped
    stake_pct = half_kelly * 100
    clamped = sizer.clamp_stake(stake_pct)
    
    assert clamped >= 0.5  # min_stake_pct
    assert clamped <= 5.0  # max_stake_pct


# =============================================================================
# Property 5: Volume Tier Multiplier
# For any volume ratio, the position size multiplier is:
# 0.8x if ratio < 1.0, 1.0x if 1.0-1.5, 1.1x if 1.5-2.5, 1.2x if > 2.5
# Validates: Requirements 4.1, 4.2, 4.3, 4.4
# =============================================================================

@settings(max_examples=100)
@given(volume_ratio=st.floats(min_value=0.0, max_value=5.0, allow_nan=False))
def test_property_5_volume_tier_multiplier(volume_ratio: float):
    """Volume multiplier follows tier rules."""
    sizer = VolumeTieredSizer()
    
    multiplier = sizer.get_volume_multiplier(volume_ratio)
    tier = sizer.get_volume_tier(volume_ratio)
    
    if volume_ratio < 1.0:
        assert tier == VolumeTier.LOW
        assert multiplier == 0.8
    elif volume_ratio < 1.5:
        assert tier == VolumeTier.STANDARD
        assert multiplier == 1.0
    elif volume_ratio < 2.5:
        assert tier == VolumeTier.MEDIUM
        assert multiplier == 1.1
    else:
        assert tier == VolumeTier.HIGH
        assert multiplier == 1.2


# =============================================================================
# Property 6: Regime-Adaptive ATR Multiplier
# For any regime and trend combination, the ATR stop multiplier is:
# 1.5x for BULL+TRENDING, 2.0x for BULL+SIDEWAYS, 2.5x for BEAR
# Validates: Requirements 5.1, 5.2, 5.3
# =============================================================================

@settings(max_examples=100)
@given(
    regime=st.sampled_from([Regime.BULL, Regime.BEAR]),
    trend_type=st.sampled_from(["trending", "sideways"])
)
def test_property_6_regime_adaptive_atr_multiplier(regime: Regime, trend_type: str):
    """ATR multiplier follows regime/trend rules."""
    stops = RegimeAdaptiveStops()
    
    multiplier = stops.get_atr_multiplier(regime, trend_type)
    
    if regime == Regime.BEAR:
        assert multiplier == 2.5
    elif trend_type == "trending":
        assert multiplier == 1.5
    else:  # sideways
        assert multiplier == 2.0


# =============================================================================
# Property 7: Existing Stops Preservation
# For any existing position, when regime changes, the stop loss price remains
# unchanged
# Validates: Requirements 5.4
# =============================================================================

@settings(max_examples=100)
@given(
    existing_stop=st.floats(min_value=10.0, max_value=1000.0, allow_nan=False),
    new_stop=st.floats(min_value=10.0, max_value=1000.0, allow_nan=False)
)
def test_property_7_existing_stops_preservation(existing_stop: float, new_stop: float):
    """Existing stops only update if more favorable (tighter)."""
    stops = RegimeAdaptiveStops()
    
    # For long positions, only update if new stop is higher (tighter)
    should_update = stops.should_update_stop(existing_stop, new_stop, "long")
    
    if new_stop > existing_stop:
        assert should_update, "Should update to tighter stop"
    else:
        assert not should_update, "Should not widen stop"


# =============================================================================
# Property 8: RSI Zone Validation
# For any RSI value and regime, entry is valid if:
# BULL regime accepts RSI 35-70, BEAR regime accepts RSI 45-60
# Validates: Requirements 6.1, 6.2, 6.3
# =============================================================================

@settings(max_examples=100)
@given(
    rsi=st.floats(min_value=0.0, max_value=100.0, allow_nan=False),
    regime=st.sampled_from([Regime.BULL, Regime.BEAR])
)
def test_property_8_rsi_zone_validation(rsi: float, regime: Regime):
    """RSI validation follows regime-specific zones."""
    optimizer = RSIZoneOptimizer()
    
    is_valid = optimizer.is_valid_rsi(rsi, regime)
    min_rsi, max_rsi = optimizer.get_rsi_bounds(regime)
    
    if regime == Regime.BULL:
        assert min_rsi == 35.0
        assert max_rsi == 70.0
    else:  # BEAR
        assert min_rsi == 45.0
        assert max_rsi == 60.0
    
    if min_rsi <= rsi <= max_rsi:
        assert is_valid, f"RSI {rsi} should be valid for {regime}"
    else:
        assert not is_valid, f"RSI {rsi} should be invalid for {regime}"


# =============================================================================
# Property 9: Blacklist Duration by Loss Severity
# For any stop loss event, blacklist duration is:
# 15 min if loss < 1%, 30 min if 1-2%, 60 min if > 2%
# Validates: Requirements 7.1, 7.2, 7.3
# =============================================================================

@settings(max_examples=100)
@given(loss_pct=st.floats(min_value=0.0, max_value=0.1, allow_nan=False))
def test_property_9_blacklist_duration_by_loss(loss_pct: float):
    """Blacklist duration follows loss severity tiers."""
    manager = DynamicBlacklistManager()
    
    duration = manager.get_blacklist_duration(loss_pct)
    
    if loss_pct < 0.01:
        assert duration == 15
    elif loss_pct < 0.02:
        assert duration == 30
    else:
        assert duration == 60


# =============================================================================
# Property 10: Blacklist Expiration
# For any blacklisted symbol, after the duration expires, the symbol is no
# longer blacklisted
# Validates: Requirements 7.4
# =============================================================================

@settings(max_examples=100)
@given(
    loss_pct=st.floats(min_value=0.001, max_value=0.05, allow_nan=False),
    minutes_elapsed=st.integers(min_value=0, max_value=120)
)
def test_property_10_blacklist_expiration(loss_pct: float, minutes_elapsed: int):
    """Blacklist expires after duration."""
    manager = DynamicBlacklistManager()
    
    base_time = datetime(2024, 1, 1, 12, 0, 0)
    manager.record_loss("BTCUSDT", loss_pct, base_time)
    
    duration = manager.get_blacklist_duration(loss_pct)
    check_time = base_time + timedelta(minutes=minutes_elapsed)
    
    is_blacklisted = manager.is_blacklisted("BTCUSDT", check_time)
    
    if minutes_elapsed >= duration:
        assert not is_blacklisted, f"Should expire after {duration} minutes"
    else:
        assert is_blacklisted, f"Should still be blacklisted at {minutes_elapsed} minutes"


# =============================================================================
# Property 11: Fear & Greed Adjustments
# For any F&G index value, position size is reduced 30% if F&G < 25,
# trail is tightened to 1.0x if F&G > 75, standard otherwise
# Validates: Requirements 8.1, 8.2, 8.3
# =============================================================================

@settings(max_examples=100)
@given(fg_index=st.integers(min_value=0, max_value=100))
def test_property_11_fear_greed_adjustments(fg_index: int):
    """F&G adjustments follow sentiment rules."""
    adjuster = FearGreedAdjuster()
    
    size_mult = adjuster.get_size_multiplier(fg_index)
    trail_mult = adjuster.get_trail_multiplier(fg_index, base_mult=1.5)
    
    if fg_index < 25:
        assert size_mult == 0.7, "Should reduce size 30% in extreme fear"
        assert trail_mult == 1.5, "Trail unchanged in fear"
    elif fg_index > 75:
        assert size_mult == 1.0, "Size unchanged in greed"
        assert trail_mult == 1.0, "Should tighten trail in extreme greed"
    else:
        assert size_mult == 1.0, "Standard size in normal range"
        assert trail_mult == 1.5, "Standard trail in normal range"


# =============================================================================
# Property 12: F&G Fallback
# For any unavailable F&G data (None), the system uses standard parameters
# without adjustment
# Validates: Requirements 8.4
# =============================================================================

@settings(max_examples=100)
@given(base_mult=st.floats(min_value=0.5, max_value=3.0, allow_nan=False))
def test_property_12_fg_fallback(base_mult: float):
    """None F&G returns standard parameters."""
    adjuster = FearGreedAdjuster()
    
    size_mult = adjuster.get_size_multiplier(None)
    trail_mult = adjuster.get_trail_multiplier(None, base_mult=base_mult)
    
    assert size_mult == 1.0, "Should use standard size when F&G unavailable"
    assert trail_mult == base_mult, "Should use base trail when F&G unavailable"


# =============================================================================
# Property 13: Micro Alignment Bonus
# For any signal where 1M and 5M trends align with direction, position size
# increases by 5% and stop reduces by 0.5x ATR
# Validates: Requirements 9.1, 9.2
# =============================================================================

@settings(max_examples=100)
@given(
    trend=st.sampled_from(["up", "down"]),
    direction=st.sampled_from(["long", "short"])
)
def test_property_13_micro_alignment_bonus(trend: str, direction: str):
    """Aligned micro-timeframes provide bonuses."""
    bonus = MicroAlignmentBonus()
    
    # Both timeframes same trend
    is_aligned = bonus.check_alignment(trend, trend, direction)
    
    expected_aligned = (
        (trend == "up" and direction == "long") or
        (trend == "down" and direction == "short")
    )
    
    assert is_aligned == expected_aligned
    
    if is_aligned:
        assert bonus.get_size_bonus(True) == 0.05
        assert bonus.get_stop_reduction(True) == 0.5
    else:
        assert bonus.get_size_bonus(False) == 0.0
        assert bonus.get_stop_reduction(False) == 0.0


# =============================================================================
# Property 14: Micro Contradiction Rejection
# For any signal where micro-timeframes contradict signal direction, the signal
# is rejected
# Validates: Requirements 9.3
# =============================================================================

@settings(max_examples=100)
@given(direction=st.sampled_from(["long", "short"]))
def test_property_14_micro_contradiction_rejection(direction: str):
    """Contradicting micro-timeframes cause rejection."""
    bonus = MicroAlignmentBonus()
    
    # Set opposite trend
    opposite_trend = "down" if direction == "long" else "up"
    
    should_reject = bonus.should_reject(opposite_trend, opposite_trend, direction)
    
    assert should_reject, f"Should reject {direction} when both timeframes are {opposite_trend}"


# =============================================================================
# Property 15: Entry Confirmation Delay
# For any entry signal, execution waits 1 candle and cancels if price moves
# > 0.3% against signal direction
# Validates: Requirements 10.1, 10.2, 10.3
# =============================================================================

@settings(max_examples=100)
@given(
    signal_price=st.floats(min_value=100.0, max_value=10000.0, allow_nan=False),
    price_change_pct=st.floats(min_value=-0.01, max_value=0.01, allow_nan=False),
    direction=st.sampled_from(["long", "short"])
)
def test_property_15_entry_confirmation_delay(
    signal_price: float,
    price_change_pct: float,
    direction: str
):
    """Entry confirmation cancels on adverse movement > 0.3%."""
    manager = EntryConfirmationManager()
    
    manager.create_pending("BTCUSDT", direction, signal_price)
    
    current_price = signal_price * (1 + price_change_pct)
    
    # Check after 1 candle
    should_execute, reason = manager.check_confirmation("BTCUSDT", current_price, candles_elapsed=1)
    
    # Determine if movement is adverse
    if direction == "long":
        adverse = price_change_pct < -0.003
    else:
        adverse = price_change_pct > 0.003
    
    if adverse:
        assert not should_execute, f"Should cancel on adverse movement"
        assert "cancelled" in reason.lower()
    else:
        assert should_execute, f"Should execute after confirmation"
        assert "confirmed" in reason.lower()
