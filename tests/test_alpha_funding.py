"""Property-based tests for Funding Rate Arbitrage.

**Feature: kinetic-empire-alpha, Properties 1, 13**
**Validates: Requirements 1.4, 10.4**
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from datetime import datetime, timedelta

from kinetic_empire.alpha.funding_arbitrage import (
    FundingArbitrageStrategy, ArbitrageConfig,
    FundingRateMonitor
)
from kinetic_empire.alpha.models import ArbitragePosition, FundingData


class TestFundingRateMonitorProperties:
    """Property-based tests for Funding Rate Monitor."""
    
    @given(
        rate_8h=st.floats(min_value=-0.01, max_value=0.01, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_annualized_rate_calculation(self, rate_8h: float):
        """**Feature: kinetic-empire-alpha, Property 13: Funding Rate Annualization**
        
        Annualized rate SHALL equal rate_8h × 3 × 365.
        **Validates: Requirements 10.4**
        """
        monitor = FundingRateMonitor()
        
        annualized = monitor.calculate_annualized_rate(rate_8h)
        expected = rate_8h * 3 * 365
        
        assert abs(annualized - expected) < 1e-10, (
            f"Annualized rate mismatch: expected {expected}, got {annualized}"
        )
    
    @given(
        rate_8h=st.floats(min_value=0.0001, max_value=0.01, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_opportunity_detection_above_threshold(self, rate_8h: float):
        """**Feature: kinetic-empire-alpha, Property 13: Funding Rate Annualization**
        
        WHEN funding rate exceeds threshold THEN pair SHALL be flagged as opportunity.
        **Validates: Requirements 10.4**
        """
        min_rate = 0.0001  # 10% annualized
        monitor = FundingRateMonitor(min_rate=min_rate)
        
        # Update with rate above threshold
        data = monitor.update_funding_rate(
            "BTC/USDT", rate_8h, datetime.now() + timedelta(hours=8)
        )
        
        # Should be flagged as opportunity
        assert data.is_opportunity == (rate_8h >= min_rate), (
            f"Opportunity flag incorrect for rate {rate_8h}"
        )
    
    @given(
        rates=st.lists(
            st.floats(min_value=-0.001, max_value=0.01, allow_nan=False),
            min_size=1,
            max_size=20
        )
    )
    @settings(max_examples=50)
    def test_7d_average_calculation(self, rates: list):
        """Test 7-day average funding rate calculation."""
        monitor = FundingRateMonitor()
        
        # Add rates to history
        for rate in rates:
            monitor.update_funding_rate(
                "BTC/USDT", rate, datetime.now() + timedelta(hours=8)
            )
        
        avg = monitor.calculate_7d_average("BTC/USDT")
        expected_avg = sum(rates) / len(rates)
        
        assert abs(avg - expected_avg) < 1e-10, (
            f"7d average mismatch: expected {expected_avg}, got {avg}"
        )
    
    def test_top_opportunities_sorted_by_rate(self):
        """Test that top opportunities are sorted by funding rate."""
        monitor = FundingRateMonitor()
        
        # Add multiple pairs with different rates
        pairs_rates = [
            ("BTC/USDT", 0.0005),
            ("ETH/USDT", 0.001),
            ("SOL/USDT", 0.0002),
            ("DOGE/USDT", 0.0008),
        ]
        
        for pair, rate in pairs_rates:
            monitor.update_funding_rate(
                pair, rate, datetime.now() + timedelta(hours=8)
            )
        
        top = monitor.get_top_opportunities(n=3)
        
        # Should be sorted descending by rate
        for i in range(1, len(top)):
            assert top[i-1].current_rate >= top[i].current_rate


class TestFundingArbitrageProperties:
    """Property-based tests for Funding Arbitrage Strategy."""
    
    @given(
        base_price=st.floats(min_value=10.0, max_value=100000.0, allow_nan=False),
        price_diff_pct=st.floats(min_value=-0.005, max_value=0.005, allow_nan=False),  # ±0.5% diff
        size=st.floats(min_value=0.001, max_value=100.0, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_delta_neutrality_of_arbitrage_positions(
        self, base_price: float, price_diff_pct: float, size: float
    ):
        """**Feature: kinetic-empire-alpha, Property 1: Delta-Neutrality of Arbitrage Positions**
        
        For any arbitrage position, spot_size SHALL equal futures_size within 1% tolerance.
        **Validates: Requirements 1.4**
        """
        strategy = FundingArbitrageStrategy()
        
        # Spot and futures prices are typically very close (within 0.5%)
        spot_price = base_price
        futures_price = base_price * (1 + price_diff_pct)
        
        position = strategy.open_arbitrage(
            pair="BTC/USDT",
            spot_price=spot_price,
            futures_price=futures_price,
            spot_size=size,
            futures_size=size,
            funding_rate=0.0001
        )
        
        # Property: Position should be delta-neutral (sizes equal means delta ~= price diff)
        # With equal sizes and small price diff, delta should be small
        assert position.delta <= abs(price_diff_pct) + 0.001, (
            f"Position delta too high: {position.delta}"
        )
        
        # Property: Spot and futures sizes should be equal
        assert position.spot_size == position.futures_size, (
            f"Sizes not equal: spot={position.spot_size}, futures={position.futures_size}"
        )
    
    @given(
        available_capital=st.floats(min_value=1000.0, max_value=1000000.0, allow_nan=False),
        spot_price=st.floats(min_value=10.0, max_value=100000.0, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_position_size_calculation_equal_legs(
        self, available_capital: float, spot_price: float
    ):
        """**Feature: kinetic-empire-alpha, Property 1: Delta-Neutrality of Arbitrage Positions**
        
        Position size calculation SHALL produce equal spot and futures sizes.
        **Validates: Requirements 1.4**
        """
        strategy = FundingArbitrageStrategy()
        
        spot_size, futures_size = strategy.calculate_position_size(
            available_capital, spot_price
        )
        
        # Property: Sizes must be equal for delta-neutrality
        assert spot_size == futures_size, (
            f"Calculated sizes not equal: spot={spot_size}, futures={futures_size}"
        )
        
        # Property: Size should be based on position_size_pct
        expected_capital = available_capital * strategy.config.position_size_pct
        expected_size = expected_capital / spot_price
        
        assert abs(spot_size - expected_size) < 1e-10, (
            f"Size calculation incorrect: expected {expected_size}, got {spot_size}"
        )
    
    @given(
        funding_rates=st.dictionaries(
            keys=st.sampled_from(["BTC/USDT", "ETH/USDT", "SOL/USDT", "DOGE/USDT"]),
            values=st.floats(min_value=-0.001, max_value=0.01, allow_nan=False),
            min_size=1,
            max_size=4
        )
    )
    @settings(max_examples=50)
    def test_opportunity_finding_above_threshold(self, funding_rates: dict):
        """Test that opportunities are found only above threshold."""
        config = ArbitrageConfig(min_funding_rate=0.0001)
        strategy = FundingArbitrageStrategy(config)
        
        opportunities = strategy.find_opportunities(funding_rates)
        
        # All opportunities should have rate >= threshold
        for pair in opportunities:
            assert funding_rates[pair] >= config.min_funding_rate, (
                f"Pair {pair} with rate {funding_rates[pair]} below threshold"
            )
        
        # All pairs above threshold should be in opportunities
        for pair, rate in funding_rates.items():
            if rate >= config.min_funding_rate:
                assert pair in opportunities, (
                    f"Pair {pair} with rate {rate} not in opportunities"
                )
    
    @given(
        current_funding=st.floats(min_value=-0.001, max_value=0.01, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_exit_condition_below_threshold(self, current_funding: float):
        """Test that exit is triggered when funding drops below threshold."""
        config = ArbitrageConfig(exit_funding_rate=0.00005)
        strategy = FundingArbitrageStrategy(config)
        
        # Open a position
        strategy.open_arbitrage(
            pair="BTC/USDT",
            spot_price=50000.0,
            futures_price=50100.0,
            spot_size=1.0,
            futures_size=1.0,
            funding_rate=0.0001
        )
        
        should_exit = strategy.check_exit_conditions("BTC/USDT", current_funding)
        
        # Should exit if funding below threshold
        expected_exit = current_funding < config.exit_funding_rate
        assert should_exit == expected_exit, (
            f"Exit condition incorrect for funding {current_funding}"
        )


class TestArbitragePositionProperties:
    """Property-based tests for ArbitragePosition model."""
    
    @given(
        spot_price=st.floats(min_value=10.0, max_value=100000.0, allow_nan=False),
        futures_price=st.floats(min_value=10.0, max_value=100000.0, allow_nan=False),
        spot_size=st.floats(min_value=0.001, max_value=100.0, allow_nan=False),
        futures_size=st.floats(min_value=0.001, max_value=100.0, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_delta_calculation(
        self, spot_price: float, futures_price: float,
        spot_size: float, futures_size: float
    ):
        """Test delta calculation for arbitrage positions."""
        position = ArbitragePosition(
            pair="BTC/USDT",
            spot_entry_price=spot_price,
            futures_entry_price=futures_price,
            spot_size=spot_size,
            futures_size=futures_size,
            open_time=datetime.now()
        )
        
        # Calculate expected delta
        spot_value = spot_price * spot_size
        futures_value = futures_price * futures_size
        expected_delta = abs(spot_value - futures_value) / spot_value if spot_value > 0 else 1.0
        
        assert abs(position.delta - expected_delta) < 1e-10, (
            f"Delta mismatch: expected {expected_delta}, got {position.delta}"
        )
    
    @given(
        spot_price=st.floats(min_value=10.0, max_value=100000.0, allow_nan=False),
        size=st.floats(min_value=0.001, max_value=100.0, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_notional_value_calculation(self, spot_price: float, size: float):
        """Test notional value calculation."""
        position = ArbitragePosition(
            pair="BTC/USDT",
            spot_entry_price=spot_price,
            futures_entry_price=spot_price,
            spot_size=size,
            futures_size=size,
            open_time=datetime.now()
        )
        
        expected_notional = spot_price * size
        
        assert abs(position.notional_value - expected_notional) < 1e-10, (
            f"Notional mismatch: expected {expected_notional}, got {position.notional_value}"
        )


class TestFundingArbitrageEdgeCases:
    """Edge case tests for funding arbitrage."""
    
    def test_max_positions_limit(self):
        """Test that max positions limit is enforced."""
        config = ArbitrageConfig(max_positions=2)
        strategy = FundingArbitrageStrategy(config)
        
        # Open max positions
        for i in range(config.max_positions):
            strategy.open_arbitrage(
                pair=f"PAIR{i}/USDT",
                spot_price=100.0,
                futures_price=100.0,
                spot_size=1.0,
                futures_size=1.0,
                funding_rate=0.0001
            )
        
        # Should not be able to open more
        assert not strategy.can_open_position()
    
    def test_funding_payment_recording(self):
        """Test that funding payments are recorded correctly."""
        strategy = FundingArbitrageStrategy()
        
        strategy.open_arbitrage(
            pair="BTC/USDT",
            spot_price=50000.0,
            futures_price=50000.0,
            spot_size=1.0,
            futures_size=1.0,
            funding_rate=0.0001
        )
        
        # Record funding payments
        strategy.record_funding_payment("BTC/USDT", 50.0)
        strategy.record_funding_payment("BTC/USDT", 45.0)
        
        position = strategy.get_position("BTC/USDT")
        assert position.funding_collected == 95.0
    
    def test_close_arbitrage_pnl_calculation(self):
        """Test P&L calculation when closing arbitrage."""
        strategy = FundingArbitrageStrategy()
        
        strategy.open_arbitrage(
            pair="BTC/USDT",
            spot_price=50000.0,
            futures_price=50100.0,
            spot_size=1.0,
            futures_size=1.0,
            funding_rate=0.0001
        )
        
        # Record some funding
        strategy.record_funding_payment("BTC/USDT", 100.0)
        
        # Close at different prices
        pnl = strategy.close_arbitrage(
            "BTC/USDT",
            spot_exit_price=51000.0,  # Spot up 1000
            futures_exit_price=51050.0  # Futures up 950
        )
        
        # Spot P&L: (51000 - 50000) * 1 = 1000
        # Futures P&L: (50100 - 51050) * 1 = -950
        # Funding: 100
        # Total: 1000 - 950 + 100 = 150
        assert pnl == pytest.approx(150.0, abs=0.01)
    
    def test_negative_funding_detection(self):
        """Test detection of negative funding rates."""
        monitor = FundingRateMonitor()
        
        monitor.update_funding_rate(
            "BTC/USDT", -0.0001, datetime.now() + timedelta(hours=8)
        )
        
        assert monitor.is_negative_funding("BTC/USDT")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
