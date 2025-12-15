"""Property-based tests for R-Factor Calculator.

**Feature: kinetic-empire-alpha, Property 2: R-Factor Calculation Correctness**
"""

import pytest
from hypothesis import given, strategies as st, assume
from datetime import datetime

from kinetic_empire.alpha.rfactor import RFactorCalculator, RFactorConfig
from kinetic_empire.alpha.models import RFactorPosition


class TestRFactorCalculator:
    """Tests for R-Factor Calculator."""
    
    @given(
        entry_price=st.floats(min_value=0.01, max_value=100000, allow_nan=False),
        stop_distance_pct=st.floats(min_value=0.001, max_value=0.5, allow_nan=False),
    )
    def test_r_value_calculation_long(self, entry_price: float, stop_distance_pct: float):
        """**Feature: kinetic-empire-alpha, Property 2: R-Factor Calculation Correctness**
        
        For any long position, R_value SHALL equal |entry_price - stop_loss|.
        **Validates: Requirements 2.1**
        """
        calc = RFactorCalculator()
        stop_loss = entry_price * (1 - stop_distance_pct)
        
        r_value = calc.calculate_r_value(entry_price, stop_loss, "LONG")
        
        expected = abs(entry_price - stop_loss)
        assert abs(r_value - expected) < 1e-10
        assert r_value > 0
    
    @given(
        entry_price=st.floats(min_value=0.01, max_value=100000, allow_nan=False),
        stop_distance_pct=st.floats(min_value=0.001, max_value=0.5, allow_nan=False),
    )
    def test_r_value_calculation_short(self, entry_price: float, stop_distance_pct: float):
        """**Feature: kinetic-empire-alpha, Property 2: R-Factor Calculation Correctness**
        
        For any short position, R_value SHALL equal |stop_loss - entry_price|.
        **Validates: Requirements 2.2**
        """
        calc = RFactorCalculator()
        stop_loss = entry_price * (1 + stop_distance_pct)
        
        r_value = calc.calculate_r_value(entry_price, stop_loss, "SHORT")
        
        expected = abs(stop_loss - entry_price)
        assert abs(r_value - expected) < 1e-10
        assert r_value > 0

    
    @given(
        entry_price=st.floats(min_value=10, max_value=10000, allow_nan=False),
        stop_distance_pct=st.floats(min_value=0.01, max_value=0.2, allow_nan=False),
        profit_pct=st.floats(min_value=-0.5, max_value=2.0, allow_nan=False),
    )
    def test_current_r_calculation_long(self, entry_price: float, 
                                        stop_distance_pct: float, profit_pct: float):
        """**Feature: kinetic-empire-alpha, Property 2: R-Factor Calculation Correctness**
        
        For any long position, current_r SHALL equal (current_profit / R_value).
        **Validates: Requirements 2.3**
        """
        calc = RFactorCalculator()
        stop_loss = entry_price * (1 - stop_distance_pct)
        current_price = entry_price * (1 + profit_pct)
        
        r_value = calc.calculate_r_value(entry_price, stop_loss, "LONG")
        current_r = calc.calculate_current_r(entry_price, current_price, r_value, "LONG")
        
        # Verify: current_r = profit / r_value
        profit = current_price - entry_price
        expected_r = profit / r_value
        
        assert abs(current_r - expected_r) < 1e-10
    
    @given(
        entry_price=st.floats(min_value=10, max_value=10000, allow_nan=False),
        stop_distance_pct=st.floats(min_value=0.01, max_value=0.2, allow_nan=False),
        profit_pct=st.floats(min_value=-0.5, max_value=2.0, allow_nan=False),
    )
    def test_current_r_calculation_short(self, entry_price: float,
                                         stop_distance_pct: float, profit_pct: float):
        """**Feature: kinetic-empire-alpha, Property 2: R-Factor Calculation Correctness**
        
        For any short position, current_r SHALL equal (current_profit / R_value).
        **Validates: Requirements 2.3**
        """
        calc = RFactorCalculator()
        stop_loss = entry_price * (1 + stop_distance_pct)
        current_price = entry_price * (1 - profit_pct)  # Profit when price goes down
        
        r_value = calc.calculate_r_value(entry_price, stop_loss, "SHORT")
        current_r = calc.calculate_current_r(entry_price, current_price, r_value, "SHORT")
        
        # Verify: current_r = profit / r_value (profit = entry - current for shorts)
        profit = entry_price - current_price
        expected_r = profit / r_value
        
        assert abs(current_r - expected_r) < 1e-10
    
    def test_position_becomes_risk_free_at_1r(self):
        """Test that position is marked risk-free after 1R partial exit."""
        calc = RFactorCalculator()
        
        position = calc.create_position(
            pair="BTC/USDT",
            side="LONG",
            entry_price=100.0,
            stop_loss=95.0,
            position_size=1.0,
            strategy="test"
        )
        
        assert not calc.is_risk_free("BTC/USDT")
        
        # Record partial exit at 1R
        calc.record_partial_exit(
            pair="BTC/USDT",
            r_level=1.0,
            percentage=0.25,
            exit_price=105.0,
            profit=1.25
        )
        
        assert calc.is_risk_free("BTC/USDT")
    
    def test_target_price_calculation(self):
        """Test target price calculation for R multiples."""
        calc = RFactorCalculator()
        
        entry = 100.0
        stop = 95.0  # 5% stop = 5 R value
        
        # 2R target for long
        target_2r = calc.calculate_target_price(entry, stop, "LONG", 2.0)
        assert target_2r == 110.0  # entry + 2 * R
        
        # 3R target for long
        target_3r = calc.calculate_target_price(entry, stop, "LONG", 3.0)
        assert target_3r == 115.0
        
        # 2R target for short
        entry_short = 100.0
        stop_short = 105.0
        target_2r_short = calc.calculate_target_price(entry_short, stop_short, "SHORT", 2.0)
        assert target_2r_short == 90.0  # entry - 2 * R


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
