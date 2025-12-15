"""Tests for configuration module.

**Feature: kinetic-empire, Property 26: Configuration Validation**
**Validates: Requirements 12.2, 12.3**
"""

import json
import pytest
from hypothesis import given, strategies as st, settings
from pathlib import Path
import tempfile

from kinetic_empire.config import ConfigManager, ConfigValidationError, Config


class TestConfigValidation:
    """Property-based tests for configuration validation."""

    # **Feature: kinetic-empire, Property 26: Configuration Validation**
    # **Validates: Requirements 12.2, 12.3**
    def test_config_validation_rejects_missing_key(self):
        """Configuration missing exchange key SHALL fail validation."""
        config_data = {
            "exchange": {"name": "binance", "key": "", "secret": "valid_secret"},
            "strategy": {"stake_currency": "USDT", "max_open_trades": 20},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            with open(config_path, "w") as f:
                json.dump(config_data, f)

            manager = ConfigManager(config_path=config_path, load_env=False)
            with pytest.raises(ConfigValidationError):
                manager.load()

    def test_config_validation_rejects_missing_secret(self):
        """Configuration missing exchange secret SHALL fail validation."""
        config_data = {
            "exchange": {"name": "binance", "key": "valid_key", "secret": ""},
            "strategy": {"stake_currency": "USDT", "max_open_trades": 20},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            with open(config_path, "w") as f:
                json.dump(config_data, f)

            manager = ConfigManager(config_path=config_path, load_env=False)
            with pytest.raises(ConfigValidationError):
                manager.load()

    def test_config_validation_rejects_invalid_max_trades(self):
        """Configuration with invalid max_open_trades SHALL fail validation."""
        config_data = {
            "exchange": {"name": "binance", "key": "valid_key", "secret": "valid_secret"},
            "strategy": {"stake_currency": "USDT", "max_open_trades": 0},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            with open(config_path, "w") as f:
                json.dump(config_data, f)

            manager = ConfigManager(config_path=config_path, load_env=False)
            with pytest.raises(ConfigValidationError):
                manager.load()

    @given(
        pattern=st.sampled_from([
            r"BNB/.*",
            r".*DOWN/.*",
            r".*UP/.*",
            r"USDC/.*",
            r"^TEST.*",
            r".*PERP$",
        ])
    )
    @settings(max_examples=100)
    def test_valid_blacklist_patterns_are_accepted(self, pattern: str):
        """For any valid regex pattern, configuration SHALL accept it."""
        config_data = {
            "exchange": {"key": "test_key", "secret": "test_secret"},
            "strategy": {"stake_currency": "USDT", "max_open_trades": 20},
            "scanner": {"blacklist_patterns": [pattern]},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            with open(config_path, "w") as f:
                json.dump(config_data, f)

            manager = ConfigManager(config_path=config_path)
            config = manager.load()
            
            assert pattern in config.scanner.blacklist_patterns

    def test_invalid_regex_pattern_raises_error(self):
        """Invalid regex patterns SHALL cause validation to fail."""
        config_data = {
            "exchange": {"key": "test_key", "secret": "test_secret"},
            "strategy": {"stake_currency": "USDT", "max_open_trades": 20},
            "scanner": {"blacklist_patterns": ["[invalid(regex"]},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            with open(config_path, "w") as f:
                json.dump(config_data, f)

            manager = ConfigManager(config_path=config_path)
            
            with pytest.raises(ConfigValidationError) as exc_info:
                manager.load()
            
            assert "Invalid blacklist pattern" in str(exc_info.value)


class TestConfigLoading:
    """Unit tests for configuration loading."""

    def test_load_valid_config(self, config_manager, monkeypatch):
        """Valid configuration SHALL load successfully."""
        # Clear env vars that might override config
        monkeypatch.delenv("BINANCE_API_KEY", raising=False)
        monkeypatch.delenv("BINANCE_API_SECRET", raising=False)
        monkeypatch.delenv("Binance_testnet_API_KEY", raising=False)
        monkeypatch.delenv("Binance_testnet_API_SECRET", raising=False)
        
        config = config_manager.load()
        
        assert isinstance(config, Config)
        assert config.exchange.key == "test_api_key"
        assert config.exchange.secret == "test_api_secret"
        assert config.strategy.stake_currency == "USDT"
        assert config.strategy.max_open_trades == 20

    def test_missing_config_file_uses_defaults(self, temp_config_dir, monkeypatch):
        """Missing config file SHALL fail validation due to missing credentials."""
        # Clear all env vars that might provide credentials (from .env or previous tests)
        monkeypatch.delenv("BINANCE_API_KEY", raising=False)
        monkeypatch.delenv("BINANCE_API_SECRET", raising=False)
        monkeypatch.delenv("Binance_testnet_API_KEY", raising=False)
        monkeypatch.delenv("Binance_testnet_API_SECRET", raising=False)
        
        config_path = temp_config_dir / "nonexistent.json"
        # Use load_env=False to prevent loading .env file credentials
        manager = ConfigManager(config_path=config_path, load_env=False)
        
        # Will fail validation due to missing credentials
        with pytest.raises(ConfigValidationError):
            manager.load()

    def test_blacklist_patterns_loaded(self, config_manager):
        """Blacklist patterns SHALL be loaded from config."""
        config = config_manager.load()
        patterns = config_manager.get_blacklist_patterns()
        
        assert len(patterns) == 4
        assert any(p.match("BNB/USDT") for p in patterns)
        assert any(p.match("BTCDOWN/USDT") for p in patterns)
        assert any(p.match("ETHUP/USDT") for p in patterns)
        assert any(p.match("USDC/USDT") for p in patterns)

    def test_config_not_loaded_raises_error(self, temp_config_dir):
        """Accessing config before load() SHALL raise error."""
        config_path = temp_config_dir / "config.json"
        manager = ConfigManager(config_path=config_path)
        
        with pytest.raises(ConfigValidationError) as exc_info:
            _ = manager.config
        
        assert "not loaded" in str(exc_info.value)

    def test_env_override_exchange_credentials(self, config_file, monkeypatch):
        """Environment variables SHALL override config file values."""
        monkeypatch.setenv("BINANCE_API_KEY", "env_api_key")
        monkeypatch.setenv("BINANCE_API_SECRET", "env_api_secret")
        
        manager = ConfigManager(config_path=config_file)
        config = manager.load()
        
        assert config.exchange.key == "env_api_key"
        assert config.exchange.secret == "env_api_secret"

    def test_default_values_applied(self, temp_config_dir):
        """Default values SHALL be applied for missing optional fields."""
        minimal_config = {
            "exchange": {"key": "key", "secret": "secret"},
            "strategy": {"stake_currency": "USDT", "max_open_trades": 10},
        }
        
        config_path = temp_config_dir / "config.json"
        with open(config_path, "w") as f:
            json.dump(minimal_config, f)
        
        manager = ConfigManager(config_path=config_path)
        config = manager.load()
        
        # Check defaults
        assert config.risk.min_stake_pct == 0.5
        assert config.risk.max_stake_pct == 5.0
        assert config.scanner.max_pairs == 20
        assert config.scanner.max_spread == 0.005
