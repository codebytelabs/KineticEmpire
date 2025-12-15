"""Kinetic Empire Unified Trading System - Root Configuration.

All strategy parameters are centralized here. Modify this file to tune
the trading bot without changing any source code.

API credentials and environment settings should be in .env file.
"""

# =============================================================================
# UNIFIED CONFIGURATION
# =============================================================================
# This dictionary is loaded by the unified trading system.
# All values here override the defaults in UnifiedConfig.

UNIFIED_CONFIG = {
    # =========================================================================
    # GLOBAL SETTINGS
    # =========================================================================
    # Portfolio-wide risk limits that apply to all engines combined
    
    "global_daily_loss_limit_pct": 5.0,      # Halt all trading if daily loss exceeds this %
    "global_max_drawdown_pct": 15.0,         # Close all positions if drawdown exceeds this %
    "global_circuit_breaker_cooldown_minutes": 60,  # Cooldown after circuit breaker triggers
    
    # =========================================================================
    # SPOT ENGINE CONFIGURATION
    # =========================================================================
    # Settings for spot trading (no leverage, actual asset ownership)
    # NOTE: Spot disabled - focusing on futures only for now
    
    "spot_enabled": False,                   # Enable/disable spot engine
    "spot_capital_pct": 0.0,                 # % of portfolio allocated to spot (0% since disabled)
    "spot_max_positions": 5,                 # Maximum concurrent spot positions
    "spot_position_size_pct": 10.0,          # Position size as % of spot allocation
    "spot_stop_loss_pct": 3.0,               # Stop loss percentage
    "spot_take_profit_pct": 6.0,             # Take profit percentage
    "spot_watchlist": [                      # Symbols to trade on spot
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"
    ],
    "spot_min_confidence": 60,               # Minimum confidence score to enter
    "spot_scan_interval_seconds": 60,        # How often to scan for opportunities
    
    # =========================================================================
    # FUTURES ENGINE CONFIGURATION
    # =========================================================================
    # Settings for futures trading (with leverage)
    
    "futures_enabled": True,                 # Enable/disable futures engine
    "futures_capital_pct": 100.0,            # % of portfolio allocated to futures (100% since spot disabled)
    
    # DYNAMIC POSITION LIMITS (8-12 based on market regime) - AGGRESSIVE
    "futures_max_positions_min": 8,          # Minimum positions (choppy market) - increased from 5
    "futures_max_positions_max": 12,         # Maximum positions (trending market)
    "futures_max_positions": 10,             # Default/starting max positions - increased from 8
    
    # AGGRESSIVE POSITION SIZING (use 90% of buying power)
    "futures_capital_utilization_pct": 90.0, # Use 90% of available margin
    "futures_position_size_min_pct": 8.0,    # Minimum position size %
    "futures_position_size_max_pct": 25.0,   # Maximum position size % - increased from 20%
    
    # DYNAMIC LEVERAGE (adjusted per regime)
    "futures_leverage_min": 3,               # Minimum leverage (was 2)
    "futures_leverage_max": 15,              # Maximum leverage (was 10)
    "futures_leverage_trending": 12,         # Leverage in trending market
    "futures_leverage_sideways": 8,          # Leverage in sideways market
    "futures_leverage_choppy": 5,            # Leverage in choppy market
    
    "futures_regime_adx_trending": 25.0,     # ADX threshold for trending market
    "futures_regime_adx_sideways": 15.0,     # ADX threshold for sideways market
    "futures_atr_stop_multiplier": 2.0,      # ATR multiplier for stop loss
    "futures_trailing_activation_pct": 2.0,  # Profit % to activate trailing stop
    "futures_watchlist": [                   # Symbols to trade on futures
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
        "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
        "MATICUSDT", "LTCUSDT", "ATOMUSDT", "NEARUSDT", "APTUSDT"
    ],
    # REGIME-AWARE CONFIDENCE THRESHOLDS
    "futures_min_confidence": 60,            # Legacy - use regime-aware thresholds below
    "futures_min_confidence_trending": 60,   # Trending markets: 60+ confidence required
    "futures_min_confidence_sideways": 65,   # Sideways/Choppy: 65+ (more selective)
    "futures_scan_interval_seconds": 20,     # How often to scan for opportunities
    "futures_blacklist_duration_minutes": 30,  # How long to blacklist losing symbols
    
    # =========================================================================
    # HEALTH MONITORING
    # =========================================================================
    # Engine health and restart settings
    
    "heartbeat_warning_seconds": 60,         # Warn if no heartbeat for this long
    "heartbeat_restart_seconds": 300,        # Restart engine if no heartbeat for this long
    "engine_restart_max_attempts": 3,        # Max restart attempts before giving up
}
