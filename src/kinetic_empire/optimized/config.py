"""Optimized configuration constants for Kinetic Empire v4."""

from dataclasses import dataclass


@dataclass(frozen=True)
class OptimizedConfig:
    """Research-backed optimized trading parameters."""
    
    # ATR Stop Loss Parameters
    ATR_BASE_MULTIPLIER: float = 2.5  # Up from 1.5
    ATR_HIGH_VOL_MULTIPLIER: float = 3.0
    ATR_LOW_VOL_MULTIPLIER: float = 2.0
    ATR_SIDEWAYS_MULTIPLIER: float = 2.0
    MAX_LOSS_PERCENT: float = 0.02  # 2% max loss per trade
    
    # Leverage Parameters
    LEVERAGE_HARD_CAP: int = 8  # Down from 20
    LEVERAGE_TIER_LOW: int = 3  # confidence < 70
    LEVERAGE_TIER_MID: int = 5  # confidence 70-79
    LEVERAGE_TIER_HIGH: int = 6  # confidence 80-89
    LEVERAGE_TIER_MAX: int = 8  # confidence 90-100
    LEVERAGE_REGIME_REDUCTION: float = 0.5  # 50% reduction for choppy/volatile
    
    # Position Sizing Parameters
    KELLY_FRACTION: float = 0.25  # Quarter Kelly
    KELLY_LOW_WINRATE_FRACTION: float = 0.15
    KELLY_LOW_WINRATE_THRESHOLD: float = 0.40
    MAX_POSITION_PERCENT: float = 0.25  # 25% max of capital
    
    # Trailing Stop Parameters
    TRAILING_BASE_ACTIVATION: float = 0.02  # 2% profit to activate
    TRAILING_STEP_SIZE: float = 0.003  # 0.3% step
    TRAILING_TRENDING_ACTIVATION: float = 0.025  # 2.5%
    TRAILING_SIDEWAYS_ACTIVATION: float = 0.015  # 1.5%
    
    # RSI Parameters
    RSI_OVERSOLD_THRESHOLD: int = 25  # Down from 30
    RSI_OVERBOUGHT_THRESHOLD: int = 75  # Up from 70
    RSI_DIVERGENCE_BONUS: int = 10
    
    # ADX Parameters
    ADX_TRENDING_THRESHOLD: int = 20  # Down from 25
    ADX_SIDEWAYS_THRESHOLD: int = 15
    ADX_STRONG_TREND_THRESHOLD: int = 30
    ADX_WEAK_TREND_REDUCTION: float = 0.30  # 30% position reduction
    ADX_STRONG_TREND_BONUS: int = 5
    
    # Volume Parameters
    VOLUME_REQUIRED_MULTIPLIER: float = 1.5  # Up from 1.2
    VOLUME_SPIKE_MULTIPLIER: float = 2.5
    VOLUME_LOW_REDUCTION: float = 0.40  # 40% position reduction
    VOLUME_SPIKE_BONUS: int = 10
    
    # Portfolio Risk Parameters
    MAX_POSITIONS: int = 8  # Down from 12
    MAX_MARGIN_USAGE: float = 0.80  # 80%
    DAILY_LOSS_LIMIT: float = 0.04  # 4%
    WEEKLY_LOSS_LIMIT: float = 0.08  # 8%
    MAX_CORRELATION: float = 0.70
    MAX_CORRELATED_POSITIONS: int = 2
    WEEKLY_LOSS_REDUCTION: float = 0.50  # 50% size reduction
    
    # Regime Detection Parameters
    REGIME_CONFIDENCE_THRESHOLD: float = 0.60  # 60% confidence required


# Default instance
DEFAULT_CONFIG = OptimizedConfig()
