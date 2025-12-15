"""Pytest configuration and shared fixtures."""

import pytest
from pathlib import Path
import tempfile
import json

from kinetic_empire.config import ConfigManager, Config


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory for config files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def valid_config_data():
    """Return valid configuration data."""
    return {
        "dry_run": True,
        "database_url": "sqlite:///data/trades.db",
        "exchange": {
            "name": "binance",
            "key": "test_api_key",
            "secret": "test_api_secret",
            "testnet": True,
            "rate_limit": 200,
            "enable_rate_limit": True,
        },
        "scanner": {
            "blacklist_patterns": ["BNB/.*", ".*DOWN/.*", ".*UP/.*", "USDC/.*"],
            "refresh_interval": 1800,
            "max_pairs": 20,
            "min_volume_rank": 70,
            "max_spread": 0.005,
            "min_price": 0.001,
            "volatility_min": 0.02,
            "volatility_max": 0.50,
        },
        "strategy": {
            "max_open_trades": 20,
            "max_open_trades_bear": 3,
            "stake_currency": "USDT",
            "tradable_balance_ratio": 0.99,
            "roc_threshold": 1.5,
            "rsi_min": 45.0,
            "rsi_max": 65.0,
            "ema_period": 50,
        },
        "risk": {
            "min_stake_pct": 0.5,
            "max_stake_pct": 5.0,
            "default_stake_pct": 1.0,
            "min_trades_for_kelly": 10,
            "lookback_trades": 20,
            "reward_risk_ratio": 2.0,
            "stop_loss_atr_mult": 2.0,
            "trailing_activation_pct": 2.5,
            "trailing_atr_mult": 1.5,
            "flash_crash_threshold_pct": 5.0,
            "flash_crash_window_hours": 1,
            "recovery_hours": 4,
        },
        "telegram": {
            "enabled": False,
            "token": "",
            "chat_id": "",
        },
    }


@pytest.fixture
def config_file(temp_config_dir, valid_config_data):
    """Create a temporary config file with valid data."""
    config_path = temp_config_dir / "config.json"
    with open(config_path, "w") as f:
        json.dump(valid_config_data, f)
    return config_path


@pytest.fixture
def config_manager(config_file):
    """Create a ConfigManager with valid config."""
    return ConfigManager(config_path=config_file)
