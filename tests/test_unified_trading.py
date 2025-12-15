"""Property-based tests for Unified Trading System.

Tests the correctness properties defined in the design document using Hypothesis.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime, timedelta

from src.kinetic_empire.unified.config import (
    UnifiedConfig,
    EnvConfig,
    ConfigValidationError,
)
from src.kinetic_empire.unified.capital_allocator import CapitalAllocator, CapitalAllocation
from src.kinetic_empire.unified.risk_monitor import GlobalRiskMonitor
from src.kinetic_empire.unified.health_monitor import HealthMonitor, EngineStatus


# =============================================================================
# STRATEGIES
# =============================================================================

@st.composite
def valid_config(draw):
    """Generate valid UnifiedConfig with allocation <= 100%."""
    spot_enabled = draw(st.booleans())
    futures_enabled = draw(st.booleans())
    
    # Ensure at least one engine is enabled for meaningful tests
    if not spot_enabled and not futures_enabled:
        spot_enabled = True
    
    # Generate allocations that sum to <= 100%
    if spot_enabled and futures_enabled:
        spot_pct = draw(st.floats(min_value=0.0, max_value=100.0))
        futures_pct = draw(st.floats(min_value=0.0, max_value=100.0 - spot_pct))
    elif spot_enabled:
        spot_pct = draw(st.floats(min_value=0.0, max_value=100.0))
        futures_pct = 0.0
    else:
        spot_pct = 0.0
        futures_pct = draw(st.floats(min_value=0.0, max_value=100.0))
    
    return UnifiedConfig(
        spot_enabled=spot_enabled,
        futures_enabled=futures_enabled,
        spot_capital_pct=spot_pct,
        futures_capital_pct=futures_pct,
        global_daily_loss_limit_pct=draw(st.floats(min_value=0.1, max_value=50.0)),
        global_max_drawdown_pct=draw(st.floats(min_value=0.1, max_value=50.0)),
        futures_leverage_min=draw(st.integers(min_value=1, max_value=10)),
        futures_leverage_max=draw(st.integers(min_value=10, max_value=125)),
        heartbeat_warning_seconds=draw(st.integers(min_value=1, max_value=300)),
        heartbeat_restart_seconds=draw(st.integers(min_value=301, max_value=600)),
    )


@st.composite
def invalid_allocation_config(draw):
    """Generate config with allocation > 100%."""
    spot_pct = draw(st.floats(min_value=51.0, max_value=100.0))
    futures_pct = draw(st.floats(min_value=51.0, max_value=100.0))
    
    return UnifiedConfig(
        spot_enabled=True,
        futures_enabled=True,
        spot_capital_pct=spot_pct,
        futures_capital_pct=futures_pct,
    )


# =============================================================================
# PROPERTY 2: Configuration loading completeness
# **Validates: Requirements 2.1, 2.2**
# =============================================================================

class TestConfigLoadingCompleteness:
    """Property 2: Configuration loading completeness.
    
    *For any* valid config.py file, the ConfigManager SHALL load all strategy
    parameters with correct types and values.
    **Feature: unified-trading-system, Property 2: Configuration loading completeness**
    """
    
    @given(valid_config())
    @settings(max_examples=100)
    def test_all_spot_parameters_present(self, config: UnifiedConfig):
        """All spot_* parameters should be present and correctly typed."""
        assert isinstance(config.spot_enabled, bool)
        assert isinstance(config.spot_capital_pct, float)
        assert isinstance(config.spot_max_positions, int)
        assert isinstance(config.spot_position_size_pct, float)
        assert isinstance(config.spot_stop_loss_pct, float)
        assert isinstance(config.spot_take_profit_pct, float)
        assert isinstance(config.spot_watchlist, list)
        assert isinstance(config.spot_min_confidence, int)
        assert isinstance(config.spot_scan_interval_seconds, int)
    
    @given(valid_config())
    @settings(max_examples=100)
    def test_all_futures_parameters_present(self, config: UnifiedConfig):
        """All futures_* parameters should be present and correctly typed."""
        assert isinstance(config.futures_enabled, bool)
        assert isinstance(config.futures_capital_pct, float)
        assert isinstance(config.futures_max_positions, int)
        assert isinstance(config.futures_leverage_min, int)
        assert isinstance(config.futures_leverage_max, int)
        assert isinstance(config.futures_watchlist, list)
        assert isinstance(config.futures_min_confidence, int)
    
    @given(valid_config())
    @settings(max_examples=100)
    def test_all_global_parameters_present(self, config: UnifiedConfig):
        """All global_* parameters should be present and correctly typed."""
        assert isinstance(config.global_daily_loss_limit_pct, float)
        assert isinstance(config.global_max_drawdown_pct, float)
        assert isinstance(config.global_circuit_breaker_cooldown_minutes, int)


# =============================================================================
# PROPERTY 3: Missing config validation
# **Validates: Requirements 2.4, 3.4**
# =============================================================================

class TestMissingConfigValidation:
    """Property 3: Missing config validation.
    
    *For any* configuration missing required fields, the ConfigManager SHALL
    raise an error identifying the missing field.
    **Feature: unified-trading-system, Property 3: Missing config validation**
    """
    
    def test_missing_api_key_raises_error(self):
        """Missing API key should raise ConfigValidationError."""
        env = EnvConfig(
            binance_api_key="",
            binance_api_secret="valid_secret",
        )
        with pytest.raises(ConfigValidationError) as exc_info:
            env.validate()
        assert "BINANCE_API_KEY" in str(exc_info.value)
    
    def test_missing_api_secret_raises_error(self):
        """Missing API secret should raise ConfigValidationError."""
        env = EnvConfig(
            binance_api_key="valid_key",
            binance_api_secret="",
        )
        with pytest.raises(ConfigValidationError) as exc_info:
            env.validate()
        assert "BINANCE_API_SECRET" in str(exc_info.value)
    
    def test_telegram_enabled_without_token_raises_error(self):
        """Telegram enabled without token should raise error."""
        env = EnvConfig(
            binance_api_key="valid_key",
            binance_api_secret="valid_secret",
            telegram_enabled=True,
            telegram_token=None,
        )
        with pytest.raises(ConfigValidationError) as exc_info:
            env.validate()
        assert "TELEGRAM_TOKEN" in str(exc_info.value)


# =============================================================================
# PROPERTY 5: Capital allocation validation
# **Validates: Requirements 7.2**
# =============================================================================

class TestCapitalAllocationValidation:
    """Property 5: Capital allocation validation.
    
    *For any* configuration where spot_capital_pct + futures_capital_pct > 100,
    the ConfigManager SHALL raise a validation error.
    **Feature: unified-trading-system, Property 5: Capital allocation validation**
    """
    
    @given(invalid_allocation_config())
    @settings(max_examples=100)
    def test_allocation_over_100_raises_error(self, config: UnifiedConfig):
        """Total allocation > 100% should raise ConfigValidationError."""
        with pytest.raises(ConfigValidationError) as exc_info:
            CapitalAllocator(config)
        assert "100" in str(exc_info.value) or "exceeds" in str(exc_info.value).lower()
    
    @given(valid_config())
    @settings(max_examples=100)
    def test_valid_allocation_does_not_raise(self, config: UnifiedConfig):
        """Valid allocation <= 100% should not raise error."""
        # Should not raise
        allocator = CapitalAllocator(config)
        assert allocator is not None


# =============================================================================
# PROPERTY 6: Capital allocation correctness
# **Validates: Requirements 7.1, 7.4**
# =============================================================================

class TestCapitalAllocationCorrectness:
    """Property 6: Capital allocation correctness.
    
    *For any* valid capital allocation, each engine SHALL receive exactly its
    configured percentage of total portfolio.
    **Feature: unified-trading-system, Property 6: Capital allocation correctness**
    """
    
    @given(
        valid_config(),
        st.floats(min_value=100.0, max_value=1000000.0),
    )
    @settings(max_examples=100)
    def test_allocation_matches_configured_percentage(self, config: UnifiedConfig, portfolio: float):
        """Each engine should receive exactly its configured percentage."""
        allocator = CapitalAllocator(config)
        
        if config.spot_enabled and config.spot_capital_pct > 0:
            spot_alloc = allocator.get_allocation("spot", portfolio)
            # When both enabled, should match config
            if config.futures_enabled:
                expected_pct = config.spot_capital_pct
            else:
                # When only spot enabled, gets 100%
                expected_pct = 100.0
            assert abs(spot_alloc.allocated_pct - expected_pct) < 0.01
        
        if config.futures_enabled and config.futures_capital_pct > 0:
            futures_alloc = allocator.get_allocation("futures", portfolio)
            if config.spot_enabled:
                expected_pct = config.futures_capital_pct
            else:
                expected_pct = 100.0
            assert abs(futures_alloc.allocated_pct - expected_pct) < 0.01
    
    @given(
        valid_config(),
        st.floats(min_value=100.0, max_value=1000000.0),
    )
    @settings(max_examples=100)
    def test_allocated_usd_matches_percentage(self, config: UnifiedConfig, portfolio: float):
        """Allocated USD should match percentage of portfolio."""
        allocator = CapitalAllocator(config)
        
        if config.spot_enabled:
            spot_alloc = allocator.get_allocation("spot", portfolio)
            expected_usd = portfolio * (spot_alloc.allocated_pct / 100.0)
            assert abs(spot_alloc.allocated_usd - expected_usd) < 0.01


# =============================================================================
# PROPERTY 7: Disabled engine capital reallocation
# **Validates: Requirements 7.3**
# =============================================================================

class TestDisabledEngineReallocation:
    """Property 7: Disabled engine capital reallocation.
    
    *For any* configuration with one engine disabled, the enabled engine SHALL
    have access to 100% of portfolio capital.
    **Feature: unified-trading-system, Property 7: Disabled engine capital reallocation**
    """
    
    @given(st.floats(min_value=100.0, max_value=1000000.0))
    @settings(max_examples=100)
    def test_spot_only_gets_100_percent(self, portfolio: float):
        """When futures disabled, spot should get 100%."""
        config = UnifiedConfig(
            spot_enabled=True,
            futures_enabled=False,
            spot_capital_pct=40.0,  # Original allocation
            futures_capital_pct=60.0,
        )
        allocator = CapitalAllocator(config)
        
        spot_alloc = allocator.get_allocation("spot", portfolio)
        assert spot_alloc.allocated_pct == 100.0
        assert abs(spot_alloc.allocated_usd - portfolio) < 0.01
    
    @given(st.floats(min_value=100.0, max_value=1000000.0))
    @settings(max_examples=100)
    def test_futures_only_gets_100_percent(self, portfolio: float):
        """When spot disabled, futures should get 100%."""
        config = UnifiedConfig(
            spot_enabled=False,
            futures_enabled=True,
            spot_capital_pct=40.0,
            futures_capital_pct=60.0,
        )
        allocator = CapitalAllocator(config)
        
        futures_alloc = allocator.get_allocation("futures", portfolio)
        assert futures_alloc.allocated_pct == 100.0
        assert abs(futures_alloc.allocated_usd - portfolio) < 0.01


# =============================================================================
# PROPERTY 8: Global daily loss limit enforcement
# **Validates: Requirements 8.2**
# =============================================================================

class TestDailyLossLimitEnforcement:
    """Property 8: Global daily loss limit enforcement.
    
    *For any* combined daily loss exceeding global_daily_loss_limit_pct,
    both engines SHALL halt new trades.
    **Feature: unified-trading-system, Property 8: Global daily loss limit enforcement**
    """
    
    @given(
        st.floats(min_value=1.0, max_value=20.0),  # loss_limit_pct
        st.floats(min_value=1000.0, max_value=100000.0),  # starting_value
    )
    @settings(max_examples=100)
    def test_loss_exceeding_limit_triggers_halt(self, loss_limit_pct: float, starting_value: float):
        """Loss exceeding limit should trigger circuit breaker."""
        config = UnifiedConfig(global_daily_loss_limit_pct=loss_limit_pct)
        monitor = GlobalRiskMonitor(config)
        monitor.set_starting_value(starting_value)
        
        # Simulate loss exceeding limit
        loss_amount = starting_value * (loss_limit_pct / 100.0) * 1.1  # 10% over limit
        monitor.update_pnl("futures", -loss_amount)
        
        current_value = starting_value - loss_amount
        assert monitor.check_daily_loss_limit(current_value) is True
    
    @given(
        st.floats(min_value=1.0, max_value=20.0),
        st.floats(min_value=1000.0, max_value=100000.0),
    )
    @settings(max_examples=100)
    def test_loss_under_limit_allows_trading(self, loss_limit_pct: float, starting_value: float):
        """Loss under limit should allow trading."""
        config = UnifiedConfig(global_daily_loss_limit_pct=loss_limit_pct)
        monitor = GlobalRiskMonitor(config)
        monitor.set_starting_value(starting_value)
        
        # Simulate loss under limit
        loss_amount = starting_value * (loss_limit_pct / 100.0) * 0.5  # 50% of limit
        monitor.update_pnl("futures", -loss_amount)
        
        current_value = starting_value - loss_amount
        assert monitor.check_daily_loss_limit(current_value) is False


# =============================================================================
# PROPERTY 9: Global drawdown protection
# **Validates: Requirements 8.3**
# =============================================================================

class TestDrawdownProtection:
    """Property 9: Global drawdown protection.
    
    *For any* portfolio drawdown exceeding global_max_drawdown_pct,
    both engines SHALL close all positions.
    **Feature: unified-trading-system, Property 9: Global drawdown protection**
    """
    
    @given(
        st.floats(min_value=5.0, max_value=50.0),  # max_drawdown_pct
        st.floats(min_value=1000.0, max_value=100000.0),  # peak_value
    )
    @settings(max_examples=100)
    def test_drawdown_exceeding_limit_triggers_protection(self, max_drawdown_pct: float, peak_value: float):
        """Drawdown exceeding limit should trigger protection."""
        config = UnifiedConfig(global_max_drawdown_pct=max_drawdown_pct)
        monitor = GlobalRiskMonitor(config)
        
        # Set peak value
        monitor.set_starting_value(peak_value)
        monitor.check_drawdown_limit(peak_value)  # Update peak
        
        # Simulate drawdown exceeding limit
        current_value = peak_value * (1 - max_drawdown_pct / 100.0) * 0.9  # 10% over limit
        assert monitor.check_drawdown_limit(current_value) is True
    
    @given(
        st.floats(min_value=5.0, max_value=50.0),
        st.floats(min_value=1000.0, max_value=100000.0),
    )
    @settings(max_examples=100)
    def test_drawdown_under_limit_allows_trading(self, max_drawdown_pct: float, peak_value: float):
        """Drawdown under limit should allow trading."""
        config = UnifiedConfig(global_max_drawdown_pct=max_drawdown_pct)
        monitor = GlobalRiskMonitor(config)
        
        monitor.set_starting_value(peak_value)
        monitor.check_drawdown_limit(peak_value)
        
        # Simulate drawdown under limit
        current_value = peak_value * (1 - max_drawdown_pct / 100.0 * 0.5)  # 50% of limit
        assert monitor.check_drawdown_limit(current_value) is False


# =============================================================================
# PROPERTY 10: Heartbeat timeout detection
# **Validates: Requirements 9.2, 9.3**
# =============================================================================

class TestHeartbeatTimeoutDetection:
    """Property 10: Heartbeat timeout detection.
    
    *For any* engine that hasn't sent a heartbeat for heartbeat_warning_seconds,
    the HealthMonitor SHALL flag it as unhealthy.
    **Feature: unified-trading-system, Property 10: Heartbeat timeout detection**
    """
    
    @given(
        st.integers(min_value=10, max_value=120),  # warning_seconds
        st.integers(min_value=121, max_value=600),  # restart_seconds
    )
    @settings(max_examples=100)
    def test_timeout_exceeding_restart_threshold_flags_unhealthy(
        self, warning_seconds: int, restart_seconds: int
    ):
        """Engine exceeding restart threshold should be flagged unhealthy."""
        config = UnifiedConfig(
            heartbeat_warning_seconds=warning_seconds,
            heartbeat_restart_seconds=restart_seconds,
        )
        monitor = HealthMonitor(config)
        
        # Register and start engine
        monitor.register_engine("test_engine")
        monitor.record_start("test_engine")
        
        # Simulate old heartbeat
        health = monitor.get_health("test_engine")
        health.last_heartbeat = datetime.now() - timedelta(seconds=restart_seconds + 10)
        
        unhealthy = monitor.check_health()
        assert "test_engine" in unhealthy
    
    def test_recent_heartbeat_is_healthy(self):
        """Engine with recent heartbeat should be healthy."""
        config = UnifiedConfig(
            heartbeat_warning_seconds=60,
            heartbeat_restart_seconds=300,
        )
        monitor = HealthMonitor(config)
        
        monitor.register_engine("test_engine")
        monitor.record_start("test_engine")
        monitor.record_heartbeat("test_engine")  # Fresh heartbeat
        
        unhealthy = monitor.check_health()
        assert "test_engine" not in unhealthy


# =============================================================================
# UNIT TESTS
# =============================================================================

class TestUnifiedConfigDefaults:
    """Unit tests for UnifiedConfig default values."""
    
    def test_default_values(self):
        """Default config should have sensible values.
        
        Updated for aggressive-capital-deployment spec:
        - futures_max_positions_min: 8 (was 5)
        - futures_max_positions: 10 (was 8)
        - futures_position_size_max_pct: 25 (was 20)
        - futures_min_confidence_trending: 60
        - futures_min_confidence_sideways: 65
        """
        config = UnifiedConfig()
        
        assert config.spot_enabled is True
        assert config.futures_enabled is True
        # Updated for aggressive futures-only configuration
        assert config.futures_capital_pct == 100.0
        assert config.futures_max_positions_min == 8  # Aggressive: was 5
        assert config.futures_max_positions_max == 12
        assert config.futures_max_positions == 10  # Aggressive: was 8
        assert config.futures_position_size_max_pct == 25.0  # Aggressive: was 20
        assert config.futures_capital_utilization_pct == 90.0
        assert config.futures_min_confidence_trending == 60
        assert config.futures_min_confidence_sideways == 65
        assert config.global_daily_loss_limit_pct == 5.0
        assert config.global_max_drawdown_pct == 15.0
    
    def test_validation_passes_for_defaults(self):
        """Default config should pass validation when spot is disabled."""
        config = UnifiedConfig()
        # Disable spot to make 100% futures valid
        config.spot_enabled = False
        config.spot_capital_pct = 0.0
        config.validate()  # Should not raise


class TestHealthMonitorRestartLogic:
    """Unit tests for HealthMonitor restart logic."""
    
    def test_max_restart_attempts_respected(self):
        """Should not restart after max attempts exceeded."""
        config = UnifiedConfig(engine_restart_max_attempts=3)
        monitor = HealthMonitor(config)
        
        monitor.register_engine("test_engine")
        
        # Simulate 3 restarts
        for _ in range(3):
            monitor.record_restart("test_engine")
        
        assert monitor.can_restart("test_engine") is False
    
    def test_restart_allowed_under_max(self):
        """Should allow restart under max attempts."""
        config = UnifiedConfig(engine_restart_max_attempts=3)
        monitor = HealthMonitor(config)
        
        monitor.register_engine("test_engine")
        monitor.record_restart("test_engine")
        
        assert monitor.can_restart("test_engine") is True


class TestCircuitBreakerCooldown:
    """Unit tests for circuit breaker cooldown."""
    
    def test_circuit_breaker_blocks_trading(self):
        """Circuit breaker should block new trades."""
        config = UnifiedConfig(global_circuit_breaker_cooldown_minutes=60)
        monitor = GlobalRiskMonitor(config)
        
        monitor.trigger_circuit_breaker("Test reason")
        
        assert monitor.can_open_new_trade() is False
    
    def test_circuit_breaker_expires(self):
        """Circuit breaker should expire after cooldown."""
        config = UnifiedConfig(global_circuit_breaker_cooldown_minutes=60)
        monitor = GlobalRiskMonitor(config)
        
        monitor.trigger_circuit_breaker("Test reason")
        
        # Manually expire the circuit breaker
        monitor._circuit_breaker_until = datetime.now() - timedelta(minutes=1)
        
        assert monitor.can_open_new_trade() is True
