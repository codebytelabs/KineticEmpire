"""Unified Configuration System for Kinetic Empire Trading Bot.

Centralizes all strategy parameters in a single configuration dataclass.
API credentials and environment settings are loaded from .env file.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional

from dotenv import load_dotenv


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


@dataclass
class UnifiedConfig:
    """Master configuration for all trading engines.
    
    All strategy parameters are centralized here. This config is loaded
    from the root config.py file and can be modified without code changes.
    """
    
    # Global Settings
    global_daily_loss_limit_pct: float = 5.0
    global_max_drawdown_pct: float = 15.0
    global_circuit_breaker_cooldown_minutes: int = 60
    
    # Spot Engine Configuration
    spot_enabled: bool = True
    spot_capital_pct: float = 40.0
    spot_max_positions: int = 5
    spot_position_size_pct: float = 10.0
    spot_stop_loss_pct: float = 3.0
    spot_take_profit_pct: float = 6.0
    spot_watchlist: List[str] = field(default_factory=lambda: [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"
    ])
    spot_min_confidence: int = 60
    spot_scan_interval_seconds: int = 60
    
    # Futures Engine Configuration
    futures_enabled: bool = True
    futures_capital_pct: float = 100.0
    
    # Dynamic position limits (8-12 based on market regime) - aggressive
    futures_max_positions_min: int = 8   # Increased from 5 for aggressive deployment
    futures_max_positions_max: int = 12
    futures_max_positions: int = 10  # Default/starting value (increased)
    
    # Aggressive position sizing (use 90% of buying power)
    futures_capital_utilization_pct: float = 90.0
    futures_position_size_min_pct: float = 8.0
    futures_position_size_max_pct: float = 25.0  # Increased from 20% for aggressive sizing
    
    # Dynamic leverage per regime
    futures_leverage_min: int = 3
    futures_leverage_max: int = 15
    futures_leverage_trending: int = 12
    futures_leverage_sideways: int = 8
    futures_leverage_choppy: int = 5
    
    futures_regime_adx_trending: float = 25.0
    futures_regime_adx_sideways: float = 15.0
    futures_atr_stop_multiplier: float = 2.0
    futures_trailing_activation_pct: float = 2.0
    futures_watchlist: List[str] = field(default_factory=lambda: [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
        "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
        "MATICUSDT", "LTCUSDT", "ATOMUSDT", "NEARUSDT", "APTUSDT"
    ])
    futures_min_confidence: int = 60  # Legacy - use regime-aware thresholds
    futures_min_confidence_trending: int = 60   # Trending markets: 60+
    futures_min_confidence_sideways: int = 65   # Sideways/Choppy: 65+ (more selective)
    futures_scan_interval_seconds: int = 20
    futures_blacklist_duration_minutes: int = 30
    
    # Trading Optimizations (Tier 1 - Critical)
    trailing_activation_pct: float = 1.5  # Activate trailing at 1.5% profit
    trailing_normal_mult: float = 1.5     # Normal ATR multiplier
    trailing_tight_mult: float = 1.0      # Tight ATR multiplier at 3%+
    trailing_tight_threshold_pct: float = 3.0  # Profit % to tighten trail
    
    tp1_atr_mult: float = 1.5   # TP1 at 1.5x ATR profit
    tp1_close_pct: float = 0.25  # Close 25% at TP1
    tp2_atr_mult: float = 2.5   # TP2 at 2.5x ATR profit
    tp2_close_pct: float = 0.25  # Close 25% at TP2
    
    half_kelly_enabled: bool = True  # Use Half-Kelly for reduced variance
    
    # Trading Optimizations (Tier 2 - High Value)
    volume_tier_low_threshold: float = 1.0
    volume_tier_medium_threshold: float = 1.5
    volume_tier_high_threshold: float = 2.5
    volume_tier_low_mult: float = 0.8
    volume_tier_medium_mult: float = 1.1
    volume_tier_high_mult: float = 1.2
    
    regime_stop_bull_trending_mult: float = 1.5
    regime_stop_bull_sideways_mult: float = 2.0
    regime_stop_bear_mult: float = 2.5
    
    rsi_zone_bull_min: float = 35.0
    rsi_zone_bull_max: float = 70.0
    rsi_zone_bear_min: float = 45.0
    rsi_zone_bear_max: float = 60.0
    
    # Trading Optimizations (Tier 3 - Enhancement)
    blacklist_small_loss_threshold: float = 0.01  # 1%
    blacklist_medium_loss_threshold: float = 0.02  # 2%
    blacklist_small_duration: int = 15   # minutes
    blacklist_medium_duration: int = 30  # minutes
    blacklist_large_duration: int = 60   # minutes
    
    fg_extreme_fear_threshold: int = 25
    fg_extreme_greed_threshold: int = 75
    fg_fear_size_mult: float = 0.7
    fg_greed_trail_mult: float = 1.0
    fg_adjustment_enabled: bool = True
    
    micro_bonus_size: float = 0.05  # 5% position size increase
    micro_bonus_stop_reduction: float = 0.5  # 0.5x ATR reduction
    micro_bonus_enabled: bool = True
    
    entry_confirm_candles: int = 1
    entry_confirm_adverse_threshold: float = 0.003  # 0.3%
    entry_confirm_enabled: bool = True
    
    # Health Monitoring
    heartbeat_warning_seconds: int = 60
    heartbeat_restart_seconds: int = 300
    engine_restart_max_attempts: int = 3
    
    def validate(self) -> None:
        """Validate configuration values.
        
        Raises:
            ConfigValidationError: If validation fails.
        """
        errors = []
        
        # Validate capital allocation
        total_allocation = 0.0
        if self.spot_enabled:
            total_allocation += self.spot_capital_pct
        if self.futures_enabled:
            total_allocation += self.futures_capital_pct
        
        if total_allocation > 100.0:
            errors.append(
                f"Total capital allocation ({total_allocation}%) exceeds 100%. "
                f"spot_capital_pct={self.spot_capital_pct}, futures_capital_pct={self.futures_capital_pct}"
            )
        
        # Validate percentages are positive
        if self.spot_capital_pct < 0:
            errors.append("spot_capital_pct must be >= 0")
        if self.futures_capital_pct < 0:
            errors.append("futures_capital_pct must be >= 0")
        if self.global_daily_loss_limit_pct <= 0:
            errors.append("global_daily_loss_limit_pct must be > 0")
        if self.global_max_drawdown_pct <= 0:
            errors.append("global_max_drawdown_pct must be > 0")
        
        # Validate leverage bounds
        if self.futures_leverage_min < 1:
            errors.append("futures_leverage_min must be >= 1")
        if self.futures_leverage_max < self.futures_leverage_min:
            errors.append("futures_leverage_max must be >= futures_leverage_min")
        
        # Validate position counts
        if self.spot_max_positions < 1:
            errors.append("spot_max_positions must be >= 1")
        if self.futures_max_positions < 1:
            errors.append("futures_max_positions must be >= 1")
        
        # Validate timeouts
        if self.heartbeat_warning_seconds <= 0:
            errors.append("heartbeat_warning_seconds must be > 0")
        if self.heartbeat_restart_seconds <= self.heartbeat_warning_seconds:
            errors.append("heartbeat_restart_seconds must be > heartbeat_warning_seconds")
        
        if errors:
            raise ConfigValidationError("\n".join(errors))


@dataclass
class EnvConfig:
    """Environment configuration from .env file.
    
    Contains API credentials and environment-specific settings
    that should not be committed to version control.
    """
    binance_api_key: str = ""
    binance_api_secret: str = ""
    binance_testnet: bool = True
    spot_enabled: bool = True
    futures_enabled: bool = True
    telegram_enabled: bool = False
    telegram_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    
    def validate(self) -> None:
        """Validate environment configuration.
        
        Raises:
            ConfigValidationError: If required fields are missing.
        """
        errors = []
        
        if not self.binance_api_key:
            errors.append("BINANCE_API_KEY is required")
        if not self.binance_api_secret:
            errors.append("BINANCE_API_SECRET is required")
        
        if self.telegram_enabled:
            if not self.telegram_token:
                errors.append("TELEGRAM_TOKEN is required when telegram is enabled")
            if not self.telegram_chat_id:
                errors.append("TELEGRAM_CHAT_ID is required when telegram is enabled")
        
        if errors:
            raise ConfigValidationError("\n".join(errors))


def load_unified_config() -> UnifiedConfig:
    """Load unified configuration from root config.py if it exists.
    
    Returns:
        UnifiedConfig with values from config.py or defaults.
    """
    config = UnifiedConfig()
    
    # Try to import from root config.py
    try:
        import sys
        import importlib.util
        
        config_path = os.path.join(os.getcwd(), "config.py")
        if os.path.exists(config_path):
            spec = importlib.util.spec_from_file_location("root_config", config_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Override defaults with values from config.py
                if hasattr(module, "UNIFIED_CONFIG"):
                    cfg = module.UNIFIED_CONFIG
                    for key, value in cfg.items():
                        if hasattr(config, key):
                            setattr(config, key, value)
    except Exception:
        pass  # Use defaults if config.py doesn't exist or has errors
    
    return config


def load_env_config() -> EnvConfig:
    """Load environment configuration from .env file.
    
    Returns:
        EnvConfig with values from environment variables.
    """
    load_dotenv(override=True)
    
    def str_to_bool(value: Optional[str], default: bool = False) -> bool:
        if value is None:
            return default
        return value.lower() in ("true", "1", "yes", "on")
    
    return EnvConfig(
        binance_api_key=os.getenv("BINANCE_API_KEY", ""),
        binance_api_secret=os.getenv("BINANCE_API_SECRET", ""),
        binance_testnet=str_to_bool(os.getenv("BINANCE_TESTNET"), True),
        spot_enabled=str_to_bool(os.getenv("SPOT_ENABLED"), True),
        futures_enabled=str_to_bool(os.getenv("FUTURES_ENABLED"), True),
        telegram_enabled=str_to_bool(os.getenv("TELEGRAM_ENABLED"), False),
        telegram_token=os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID"),
    )
