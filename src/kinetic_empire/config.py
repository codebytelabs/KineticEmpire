"""Configuration management module for Kinetic Empire."""

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


@dataclass
class ExchangeConfig:
    """Exchange connection configuration."""
    name: str = "binance"
    key: str = ""
    secret: str = ""
    testnet: bool = True
    rate_limit: int = 200
    enable_rate_limit: bool = True


@dataclass
class ScannerConfig:
    """Scanner module configuration."""
    blacklist_patterns: list[str] = field(default_factory=lambda: [
        r"BNB/.*", r".*DOWN/.*", r".*UP/.*", r"USDC/.*"
    ])
    refresh_interval: int = 1800  # 30 minutes
    max_pairs: int = 20
    min_volume_rank: int = 70
    max_spread: float = 0.005
    min_price: float = 0.001
    volatility_min: float = 0.02
    volatility_max: float = 0.50


@dataclass
class StrategyConfig:
    """Strategy parameters configuration."""
    max_open_trades: int = 20
    max_open_trades_bear: int = 3
    stake_currency: str = "USDT"
    tradable_balance_ratio: float = 0.99
    roc_threshold: float = 1.5
    rsi_min: float = 45.0
    rsi_max: float = 65.0
    ema_period: int = 50


@dataclass
class RiskConfig:
    """Risk management configuration."""
    min_stake_pct: float = 0.5
    max_stake_pct: float = 5.0
    default_stake_pct: float = 1.0
    min_trades_for_kelly: int = 10
    lookback_trades: int = 20
    reward_risk_ratio: float = 2.0
    stop_loss_atr_mult: float = 2.0
    trailing_activation_pct: float = 1.5  # Optimized from 2.5%
    trailing_atr_mult: float = 1.5
    flash_crash_threshold_pct: float = 5.0
    flash_crash_window_hours: int = 1
    recovery_hours: int = 4
    
    # Trading Optimizations
    half_kelly_enabled: bool = True  # Use Half-Kelly for reduced variance
    fg_adjustment_enabled: bool = True  # Fear & Greed adjustments
    micro_bonus_enabled: bool = True  # Micro-timeframe alignment bonus
    entry_confirm_enabled: bool = True  # Entry confirmation delay
    dynamic_blacklist_enabled: bool = True  # Loss-severity-based blacklist


@dataclass
class TelegramConfig:
    """Telegram bot configuration."""
    enabled: bool = False
    token: str = ""
    chat_id: str = ""


@dataclass
class Config:
    """Main configuration container."""
    exchange: ExchangeConfig = field(default_factory=ExchangeConfig)
    scanner: ScannerConfig = field(default_factory=ScannerConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    dry_run: bool = True
    database_url: str = "sqlite:///data/trades.db"


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


class ConfigManager:
    """Manages loading and validation of configuration."""

    REQUIRED_FIELDS = [
        "exchange.key",
        "exchange.secret",
        "strategy.stake_currency",
        "strategy.max_open_trades",
    ]

    def __init__(self, config_path: str | Path | None = None, load_env: bool = True):
        """Initialize configuration manager.
        
        Args:
            config_path: Path to config.json file. If None, uses default location.
            load_env: Whether to load .env file. Set to False for testing.
        """
        self.config_path = Path(config_path) if config_path else Path("config/config.json")
        self._config: Config | None = None
        self._load_env = load_env
        if load_env:
            load_dotenv()

    def load(self) -> Config:
        """Load configuration from file and environment variables.
        
        Returns:
            Loaded and validated Config object.
            
        Raises:
            ConfigValidationError: If required fields are missing or invalid.
        """
        config_data = self._load_json()
        self._config = self._parse_config(config_data)
        self._override_from_env()
        self._validate()
        return self._config

    def _load_json(self) -> dict[str, Any]:
        """Load JSON configuration file."""
        if not self.config_path.exists():
            return {}
        
        with open(self.config_path) as f:
            return json.load(f)

    def _parse_config(self, data: dict[str, Any]) -> Config:
        """Parse configuration dictionary into Config object."""
        exchange_data = data.get("exchange", {})
        scanner_data = data.get("scanner", {})
        strategy_data = data.get("strategy", {})
        risk_data = data.get("risk", {})
        telegram_data = data.get("telegram", {})

        return Config(
            exchange=ExchangeConfig(
                name=exchange_data.get("name", "binance"),
                key=exchange_data.get("key", ""),
                secret=exchange_data.get("secret", ""),
                testnet=exchange_data.get("testnet", True),
                rate_limit=exchange_data.get("rate_limit", 200),
                enable_rate_limit=exchange_data.get("enable_rate_limit", True),
            ),
            scanner=ScannerConfig(
                blacklist_patterns=scanner_data.get("blacklist_patterns", [
                    r"BNB/.*", r".*DOWN/.*", r".*UP/.*", r"USDC/.*"
                ]),
                refresh_interval=scanner_data.get("refresh_interval", 1800),
                max_pairs=scanner_data.get("max_pairs", 20),
                min_volume_rank=scanner_data.get("min_volume_rank", 70),
                max_spread=scanner_data.get("max_spread", 0.005),
                min_price=scanner_data.get("min_price", 0.001),
                volatility_min=scanner_data.get("volatility_min", 0.02),
                volatility_max=scanner_data.get("volatility_max", 0.50),
            ),
            strategy=StrategyConfig(
                max_open_trades=strategy_data.get("max_open_trades", 20),
                max_open_trades_bear=strategy_data.get("max_open_trades_bear", 3),
                stake_currency=strategy_data.get("stake_currency", "USDT"),
                tradable_balance_ratio=strategy_data.get("tradable_balance_ratio", 0.99),
                roc_threshold=strategy_data.get("roc_threshold", 1.5),
                rsi_min=strategy_data.get("rsi_min", 45.0),
                rsi_max=strategy_data.get("rsi_max", 65.0),
                ema_period=strategy_data.get("ema_period", 50),
            ),
            risk=RiskConfig(
                min_stake_pct=risk_data.get("min_stake_pct", 0.5),
                max_stake_pct=risk_data.get("max_stake_pct", 5.0),
                default_stake_pct=risk_data.get("default_stake_pct", 1.0),
                min_trades_for_kelly=risk_data.get("min_trades_for_kelly", 10),
                lookback_trades=risk_data.get("lookback_trades", 20),
                reward_risk_ratio=risk_data.get("reward_risk_ratio", 2.0),
                stop_loss_atr_mult=risk_data.get("stop_loss_atr_mult", 2.0),
                trailing_activation_pct=risk_data.get("trailing_activation_pct", 2.5),
                trailing_atr_mult=risk_data.get("trailing_atr_mult", 1.5),
                flash_crash_threshold_pct=risk_data.get("flash_crash_threshold_pct", 5.0),
                flash_crash_window_hours=risk_data.get("flash_crash_window_hours", 1),
                recovery_hours=risk_data.get("recovery_hours", 4),
            ),
            telegram=TelegramConfig(
                enabled=telegram_data.get("enabled", False),
                token=telegram_data.get("token", ""),
                chat_id=telegram_data.get("chat_id", ""),
            ),
            dry_run=data.get("dry_run", True),
            database_url=data.get("database_url", "sqlite:///data/trades.db"),
        )

    def _override_from_env(self) -> None:
        """Override configuration values from environment variables."""
        if not self._config:
            return
        
        # Skip env overrides if load_env is False (for testing)
        if not self._load_env:
            return

        # Exchange
        if key := os.getenv("BINANCE_API_KEY") or os.getenv("Binance_testnet_API_KEY"):
            self._config.exchange.key = key
        if secret := os.getenv("BINANCE_API_SECRET") or os.getenv("Binance_testnet_API_SECRET"):
            self._config.exchange.secret = secret
        if testnet := os.getenv("BINANCE_TESTNET"):
            self._config.exchange.testnet = testnet.lower() == "true"

        # Strategy
        if max_pos := os.getenv("MAX_POSITIONS"):
            self._config.strategy.max_open_trades = int(max_pos)

        # Risk
        if stop_mult := os.getenv("STOP_LOSS_ATR_MULT"):
            self._config.risk.stop_loss_atr_mult = float(stop_mult)
        if trail_thresh := os.getenv("TRAILING_STOPS_ACTIVATION_THRESHOLD"):
            self._config.risk.trailing_activation_pct = float(trail_thresh)
        if trail_mult := os.getenv("TRAILING_STOPS_ATR_MULTIPLIER"):
            self._config.risk.trailing_atr_mult = float(trail_mult)

        # Telegram
        if token := os.getenv("TELEGRAM_BOT_TOKEN"):
            self._config.telegram.token = token
            self._config.telegram.enabled = True
        if chat_id := os.getenv("TELEGRAM_CHAT_ID"):
            self._config.telegram.chat_id = chat_id

        # Database
        if db_url := os.getenv("DATABASE_URL"):
            self._config.database_url = db_url

    def _validate(self) -> None:
        """Validate configuration has all required fields.
        
        Raises:
            ConfigValidationError: If validation fails.
        """
        if not self._config:
            raise ConfigValidationError("Configuration not loaded")

        missing_fields = []

        # Check exchange credentials
        if not self._config.exchange.key:
            missing_fields.append("exchange.key")
        if not self._config.exchange.secret:
            missing_fields.append("exchange.secret")

        # Check strategy required fields
        if not self._config.strategy.stake_currency:
            missing_fields.append("strategy.stake_currency")
        if self._config.strategy.max_open_trades <= 0:
            missing_fields.append("strategy.max_open_trades (must be > 0)")

        if missing_fields:
            raise ConfigValidationError(
                f"Missing or invalid required configuration fields: {', '.join(missing_fields)}"
            )

        # Validate blacklist patterns are valid regex
        for pattern in self._config.scanner.blacklist_patterns:
            try:
                re.compile(pattern)
            except re.error as e:
                raise ConfigValidationError(
                    f"Invalid blacklist pattern '{pattern}': {e}"
                )

    def get_blacklist_patterns(self) -> list[re.Pattern]:
        """Get compiled blacklist regex patterns.
        
        Returns:
            List of compiled regex patterns.
        """
        if not self._config:
            return []
        return [re.compile(p) for p in self._config.scanner.blacklist_patterns]

    @property
    def config(self) -> Config:
        """Get loaded configuration."""
        if not self._config:
            raise ConfigValidationError("Configuration not loaded. Call load() first.")
        return self._config
