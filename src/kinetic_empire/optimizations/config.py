"""Configuration for Trading Optimizations.

Centralized configuration for all optimization modules.
"""

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class TrailingOptConfig:
    """Configuration for enhanced trailing stop management."""
    activation_pct: float = 0.015  # 1.5% profit to activate
    normal_trail_mult: float = 1.5  # Normal ATR multiplier
    tight_trail_mult: float = 1.0   # Tight ATR multiplier at 3%+
    tight_threshold_pct: float = 0.03  # 3% profit to tighten


@dataclass
class PartialProfitConfig:
    """Configuration for partial profit taking."""
    tp1_atr_mult: float = 1.5   # TP1 at 1.5x ATR profit
    tp1_close_pct: float = 0.25  # Close 25% at TP1
    tp2_atr_mult: float = 2.5   # TP2 at 2.5x ATR profit
    tp2_close_pct: float = 0.25  # Close 25% at TP2


@dataclass
class VolumeTierConfig:
    """Configuration for volume-tiered position sizing."""
    low_threshold: float = 1.0      # Below this = low volume
    medium_threshold: float = 1.5   # Below this = standard
    high_threshold: float = 2.5     # Above this = high volume
    low_multiplier: float = 0.8     # 20% reduction for low volume
    standard_multiplier: float = 1.0
    medium_multiplier: float = 1.1  # 10% increase for medium
    high_multiplier: float = 1.2    # 20% increase for high


@dataclass
class RSIZoneConfig:
    """Configuration for regime-specific RSI zones."""
    bull_min: float = 35.0
    bull_max: float = 70.0
    bear_min: float = 45.0
    bear_max: float = 60.0


@dataclass
class RegimeStopConfig:
    """Configuration for regime-adaptive stop losses."""
    bull_trending_mult: float = 1.5
    bull_sideways_mult: float = 2.0
    bear_mult: float = 2.5
    default_mult: float = 2.0


@dataclass
class BlacklistDurationConfig:
    """Configuration for dynamic blacklist durations."""
    small_loss_threshold: float = 0.01  # 1%
    medium_loss_threshold: float = 0.02  # 2%
    small_loss_duration: int = 15   # minutes
    medium_loss_duration: int = 30  # minutes
    large_loss_duration: int = 60   # minutes


@dataclass
class FearGreedConfig:
    """Configuration for Fear & Greed adjustments."""
    extreme_fear_threshold: int = 25
    extreme_greed_threshold: int = 75
    fear_size_multiplier: float = 0.7  # 30% reduction
    greed_trail_multiplier: float = 1.0  # Tighter trail


@dataclass
class MicroBonusConfig:
    """Configuration for micro-timeframe alignment bonus."""
    size_bonus: float = 0.05  # 5% position size increase
    stop_reduction: float = 0.5  # 0.5x ATR reduction


@dataclass
class EntryConfirmConfig:
    """Configuration for entry confirmation delay."""
    confirmation_candles: int = 1
    adverse_threshold_pct: float = 0.003  # 0.3%


@dataclass
class OptimizationsConfig:
    """Master configuration for all optimizations."""
    # Feature flags
    trailing_opt_enabled: bool = True
    partial_profit_enabled: bool = True
    half_kelly_enabled: bool = True
    volume_tier_enabled: bool = True
    regime_stops_enabled: bool = True
    rsi_zones_enabled: bool = True
    dynamic_blacklist_enabled: bool = True
    fg_adjustment_enabled: bool = True
    micro_bonus_enabled: bool = True
    entry_confirm_enabled: bool = True
    
    # Component configs
    trailing: TrailingOptConfig = field(default_factory=TrailingOptConfig)
    partial_profit: PartialProfitConfig = field(default_factory=PartialProfitConfig)
    volume_tier: VolumeTierConfig = field(default_factory=VolumeTierConfig)
    rsi_zones: RSIZoneConfig = field(default_factory=RSIZoneConfig)
    regime_stops: RegimeStopConfig = field(default_factory=RegimeStopConfig)
    blacklist_duration: BlacklistDurationConfig = field(default_factory=BlacklistDurationConfig)
    fear_greed: FearGreedConfig = field(default_factory=FearGreedConfig)
    micro_bonus: MicroBonusConfig = field(default_factory=MicroBonusConfig)
    entry_confirm: EntryConfirmConfig = field(default_factory=EntryConfirmConfig)
