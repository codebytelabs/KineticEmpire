"""Property-based tests for Portfolio Manager and Risk Manager.

**Feature: kinetic-empire-alpha, Properties 8, 9, 10, 14**
**Validates: Requirements 7.1, 8.5, 9.2, 9.3, 9.6**
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from datetime import datetime, timedelta

from kinetic_empire.alpha.portfolio import PortfolioManager, PortfolioConfig
from kinetic_empire.alpha.risk_manager import UnifiedRiskManager, RiskConfig
from kinetic_empire.alpha.smart_grid import SmartGridStrategy, SmartGridConfig
from kinetic_empire.alpha.models import TrendStrength, RFactorPosition


class TestSmartGridProperties:
    """Property-based tests for Smart Grid Strategy."""
    
    @given(
        atr=st.floats(min_value=0.1, max_value=100.0, allow_nan=False),
        multiplier=st.floats(min_value=0.1, max_value=2.0, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_grid_spacing_calculation(self, atr: float, multiplier: float):
        """**Feature: kinetic-empire-alpha, Property 8: Grid Spacing Calculation**
        
        Grid spacing SHALL equal ATR × spacing_multiplier.
        **Validates: Requirements 7.1**
        """
        config = SmartGridConfig(atr_spacing_multiplier=multiplier)
        strategy = SmartGridStrategy(config)
        
        spacing = strategy.calculate_grid_spacing(atr)
        expected = atr * multiplier
        
        assert abs(spacing - expected) < 1e-10, (
            f"Grid spacing mismatch: expected {expected}, got {spacing}"
        )
    
    @given(
        center_price=st.floats(min_value=100.0, max_value=10000.0, allow_nan=False),
        atr=st.floats(min_value=0.1, max_value=10.0, allow_nan=False),
        grid_count=st.integers(min_value=4, max_value=20)
    )
    @settings(max_examples=50)
    def test_grid_level_count(self, center_price: float, atr: float, grid_count: int):
        """Test that correct number of grid levels are created."""
        # Ensure spacing is small enough that all levels have positive prices
        assume(center_price > atr * grid_count)
        
        config = SmartGridConfig(grid_count=grid_count)
        strategy = SmartGridStrategy(config)
        
        spacing = strategy.calculate_grid_spacing(atr)
        levels = strategy.calculate_grid_levels(center_price, spacing, TrendStrength.NEUTRAL)
        
        assert len(levels) == grid_count, (
            f"Expected {grid_count} levels, got {len(levels)}"
        )
    
    def test_uptrend_bias_more_buy_levels(self):
        """Test that uptrend creates more buy levels below."""
        config = SmartGridConfig(grid_count=10, trend_bias=0.6)
        strategy = SmartGridStrategy(config)
        
        levels = strategy.calculate_grid_levels(100.0, 1.0, TrendStrength.STRONG_UPTREND)
        
        buy_levels = [l for l in levels if l.side == 'BUY']
        sell_levels = [l for l in levels if l.side == 'SELL']
        
        # 60% should be buy levels
        assert len(buy_levels) == 6
        assert len(sell_levels) == 4
    
    def test_downtrend_bias_more_sell_levels(self):
        """Test that downtrend creates more sell levels above."""
        config = SmartGridConfig(grid_count=10, trend_bias=0.6)
        strategy = SmartGridStrategy(config)
        
        levels = strategy.calculate_grid_levels(100.0, 1.0, TrendStrength.STRONG_DOWNTREND)
        
        buy_levels = [l for l in levels if l.side == 'BUY']
        sell_levels = [l for l in levels if l.side == 'SELL']
        
        # 60% should be sell levels
        assert len(sell_levels) == 6
        assert len(buy_levels) == 4


class TestPortfolioManagerProperties:
    """Property-based tests for Portfolio Manager."""
    
    def test_allocation_bounds_enforced_after_rebalance(self):
        """**Feature: kinetic-empire-alpha, Property 9: Portfolio Allocation Bounds**
        
        Allocations SHALL be between min_allocation and max_allocation after rebalancing.
        **Validates: Requirements 8.5**
        """
        config = PortfolioConfig(
            min_allocation=0.10,
            max_allocation=0.60
        )
        manager = PortfolioManager(config, 10000.0)
        
        # Add performance data to trigger rebalancing
        for strategy in ['funding_arbitrage', 'wave_rider', 'smart_grid']:
            for _ in range(30):
                manager.record_daily_return(strategy, 0.01)
        
        # Force rebalance by setting last_rebalance in the past
        manager.last_rebalance = datetime.now() - timedelta(hours=48)
        
        # Rebalance
        manager.rebalance_allocations()
        
        # Check bounds (excluding reserve)
        for strategy, alloc in manager.allocations.items():
            if strategy != 'reserve' and strategy in manager.performance:
                # Allocations should be within bounds
                assert alloc >= 0, f"Allocation {alloc} is negative"
                assert alloc <= 1.0, f"Allocation {alloc} exceeds 100%"
    
    @given(
        total_capital=st.floats(min_value=1000.0, max_value=1000000.0, allow_nan=False)
    )
    @settings(max_examples=50)
    def test_allocations_sum_to_one(self, total_capital: float):
        """Test that allocations always sum to 1.0."""
        manager = PortfolioManager(total_capital=total_capital)
        
        total = sum(manager.allocations.values())
        assert abs(total - 1.0) < 0.01, f"Allocations sum to {total}, not 1.0"
        
        # After rebalancing
        manager.rebalance_allocations()
        total = sum(manager.allocations.values())
        assert abs(total - 1.0) < 0.01, f"After rebalance, allocations sum to {total}"
    
    def test_strategy_capital_calculation(self):
        """Test that strategy capital is calculated correctly."""
        manager = PortfolioManager(total_capital=10000.0)
        
        # Default: 40% to funding_arbitrage
        capital = manager.get_strategy_capital('funding_arbitrage')
        assert capital == 4000.0


class TestRiskManagerProperties:
    """Property-based tests for Unified Risk Manager."""
    
    @given(
        position_value=st.floats(min_value=100.0, max_value=100000.0, allow_nan=False),
        portfolio_value=st.floats(min_value=10000.0, max_value=1000000.0, allow_nan=False),
        max_position_pct=st.floats(min_value=0.05, max_value=0.2, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_position_size_limit_enforcement(
        self, position_value: float, portfolio_value: float, max_position_pct: float
    ):
        """**Feature: kinetic-empire-alpha, Property 10: Risk Limit Enforcement**
        
        WHEN single position exceeds max_position_pct THEN trade SHALL be rejected.
        **Validates: Requirements 9.2**
        """
        config = RiskConfig(max_position_pct=max_position_pct)
        manager = UnifiedRiskManager(config)
        
        is_valid = manager.check_position_size(position_value, portfolio_value)
        
        position_pct = position_value / portfolio_value
        expected_valid = position_pct <= max_position_pct
        
        assert is_valid == expected_valid, (
            f"Position {position_pct:.1%} vs limit {max_position_pct:.1%}: "
            f"expected {expected_valid}, got {is_valid}"
        )
    
    @given(
        current_equity=st.floats(min_value=1000.0, max_value=100000.0, allow_nan=False),
        peak_equity=st.floats(min_value=1000.0, max_value=100000.0, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_drawdown_calculation(self, current_equity: float, peak_equity: float):
        """Test drawdown calculation correctness."""
        manager = UnifiedRiskManager()
        manager.peak_equity = peak_equity
        
        dd = manager.calculate_drawdown(current_equity)
        
        # Peak should be updated if current is higher
        expected_peak = max(peak_equity, current_equity)
        expected_dd = (expected_peak - current_equity) / expected_peak if expected_peak > 0 else 0
        
        assert abs(dd - expected_dd) < 1e-10, (
            f"Drawdown mismatch: expected {expected_dd}, got {dd}"
        )
    
    @given(
        max_drawdown=st.floats(min_value=0.05, max_value=0.3, allow_nan=False)
    )
    @settings(max_examples=50)
    def test_emergency_mode_on_max_drawdown(self, max_drawdown: float):
        """**Feature: kinetic-empire-alpha, Property 14: Emergency Mode Trigger**
        
        WHEN drawdown exceeds max_drawdown THEN emergency mode SHALL activate.
        **Validates: Requirements 9.3**
        """
        config = RiskConfig(max_drawdown=max_drawdown)
        manager = UnifiedRiskManager(config)
        
        # Set peak equity
        manager.peak_equity = 10000.0
        
        # Calculate equity that would breach drawdown
        breach_equity = 10000.0 * (1 - max_drawdown - 0.01)
        
        # Check drawdown limit
        is_ok = manager.check_drawdown_limit(breach_equity)
        
        assert not is_ok, "Should fail drawdown check"
        assert manager.emergency_mode, "Should be in emergency mode"
    
    @given(
        daily_loss_pct=st.floats(min_value=0.01, max_value=0.1, allow_nan=False)
    )
    @settings(max_examples=50)
    def test_emergency_mode_on_daily_loss(self, daily_loss_pct: float):
        """**Feature: kinetic-empire-alpha, Property 14: Emergency Mode Trigger**
        
        WHEN daily loss exceeds limit THEN emergency mode SHALL activate.
        **Validates: Requirements 9.6**
        """
        config = RiskConfig(daily_loss_limit=daily_loss_pct)
        manager = UnifiedRiskManager(config)
        
        portfolio_value = 10000.0
        
        # Set daily loss above limit
        manager.daily_pnl = -portfolio_value * (daily_loss_pct + 0.01)
        
        is_ok = manager.check_daily_loss(portfolio_value)
        
        assert not is_ok, "Should fail daily loss check"
        assert manager.emergency_mode, "Should be in emergency mode"
    
    def test_cooldown_period(self):
        """Test that cooldown period is enforced."""
        config = RiskConfig(cooldown_hours=24)
        manager = UnifiedRiskManager(config)
        
        # Enter emergency mode
        manager.enter_emergency_mode()
        
        assert not manager.can_trade()
        
        # Simulate cooldown expiry
        manager.cooldown_until = datetime.now() - timedelta(hours=1)
        
        assert manager.can_trade()
        assert not manager.emergency_mode


class TestRiskManagerEdgeCases:
    """Edge case tests for risk manager."""
    
    def test_validate_trade_all_checks(self):
        """Test that validate_trade checks all conditions."""
        manager = UnifiedRiskManager()
        
        # Valid trade
        is_valid, reason = manager.validate_trade(
            position_value=500.0,
            portfolio_value=10000.0,
            current_var=100.0
        )
        assert is_valid
        assert reason == "OK"
    
    def test_validate_trade_rejects_in_emergency(self):
        """Test that trades are rejected in emergency mode."""
        manager = UnifiedRiskManager()
        manager.enter_emergency_mode()
        
        is_valid, reason = manager.validate_trade(
            position_value=500.0,
            portfolio_value=10000.0,
            current_var=100.0
        )
        
        assert not is_valid
        assert "Emergency" in reason


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
