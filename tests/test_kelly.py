"""Property-based tests for Kelly Criterion position sizing.

Tests validate:
- Property 10: Kelly Criterion Default for Insufficient History
- Property 11: Win Rate Calculation Correctness
- Property 12: Kelly Fraction Formula Correctness
- Property 13: Stake Clamping
"""

from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings
import pytest

from kinetic_empire.models import Trade, Regime, ExitReason
from kinetic_empire.risk.kelly import KellyCriterionSizer, SizingConfig


# Strategies for generating test data
@st.composite
def closed_trade_strategy(draw, pair: str = "BTC/USDT"):
    """Generate a closed trade with random profit/loss."""
    trade_id = draw(st.text(min_size=8, max_size=16, alphabet="abcdef0123456789"))
    entry_time = draw(st.datetimes(
        min_value=datetime(2020, 1, 1),
        max_value=datetime(2024, 1, 1)
    ))
    exit_time = entry_time + timedelta(hours=draw(st.integers(min_value=1, max_value=48)))
    entry_price = draw(st.floats(min_value=100, max_value=100000, allow_nan=False))
    exit_price = draw(st.floats(min_value=100, max_value=100000, allow_nan=False))
    stake = draw(st.floats(min_value=10, max_value=1000, allow_nan=False))
    profit_loss = draw(st.floats(min_value=-500, max_value=500, allow_nan=False))
    
    return Trade(
        id=trade_id,
        pair=pair,
        entry_timestamp=entry_time,
        entry_price=entry_price,
        stake_amount=stake,
        regime=draw(st.sampled_from(list(Regime))),
        stop_loss=entry_price * 0.95,
        exit_timestamp=exit_time,
        exit_price=exit_price,
        profit_loss=profit_loss,
        exit_reason=draw(st.sampled_from(list(ExitReason))),
    )


@st.composite
def trade_list_with_known_win_rate(draw, num_trades: int, num_winners: int, pair: str = "BTC/USDT"):
    """Generate a list of trades with exact number of winners."""
    trades = []
    for i in range(num_trades):
        is_winner = i < num_winners
        profit = draw(st.floats(min_value=1, max_value=500)) if is_winner else draw(st.floats(min_value=-500, max_value=-0.01))
        
        entry_time = datetime(2023, 1, 1) + timedelta(hours=i)
        exit_time = entry_time + timedelta(hours=1)
        
        trade = Trade(
            id=f"trade_{i}",
            pair=pair,
            entry_timestamp=entry_time,
            entry_price=1000.0,
            stake_amount=100.0,
            regime=Regime.BULL,
            stop_loss=950.0,
            exit_timestamp=exit_time,
            exit_price=1000.0 + profit,
            profit_loss=profit,
            exit_reason=ExitReason.TREND_BREAK,
        )
        trades.append(trade)
    
    return trades


class TestKellyWinRateCalculation:
    """Tests for Property 11: Win Rate Calculation Correctness."""

    @given(
        num_trades=st.integers(min_value=1, max_value=50),
        num_winners=st.integers(min_value=0, max_value=50)
    )
    @settings(max_examples=100)
    def test_win_rate_equals_winners_over_total(self, num_trades, num_winners):
        """
        **Feature: kinetic-empire, Property 11: Win Rate Calculation Correctness**
        
        *For any* list of trades, win_rate SHALL equal 
        (count of trades where profit > 0) / (total trade count).
        **Validates: Requirements 5.3**
        """
        # Ensure num_winners doesn't exceed num_trades
        num_winners = min(num_winners, num_trades)
        
        sizer = KellyCriterionSizer()
        
        # Create trades with exact number of winners
        trades = []
        for i in range(num_trades):
            is_winner = i < num_winners
            profit = 100.0 if is_winner else -50.0
            
            trade = Trade(
                id=f"trade_{i}",
                pair="BTC/USDT",
                entry_timestamp=datetime(2023, 1, 1) + timedelta(hours=i),
                entry_price=1000.0,
                stake_amount=100.0,
                regime=Regime.BULL,
                stop_loss=950.0,
                exit_timestamp=datetime(2023, 1, 1) + timedelta(hours=i+1),
                exit_price=1100.0 if is_winner else 950.0,
                profit_loss=profit,
                exit_reason=ExitReason.TREND_BREAK,
            )
            trades.append(trade)
        
        expected_win_rate = num_winners / num_trades
        actual_win_rate = sizer.calculate_win_rate(trades)
        
        assert abs(actual_win_rate - expected_win_rate) < 1e-10

    def test_win_rate_empty_trades(self):
        """Win rate should be 0 for empty trade list."""
        sizer = KellyCriterionSizer()
        assert sizer.calculate_win_rate([]) == 0.0


class TestKellyFractionFormula:
    """Tests for Property 12: Kelly Fraction Formula Correctness."""

    @given(
        win_rate=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        reward_risk_ratio=st.floats(min_value=0.1, max_value=10.0, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_kelly_fraction_formula(self, win_rate, reward_risk_ratio):
        """
        **Feature: kinetic-empire, Property 12: Kelly Fraction Formula Correctness**
        
        *For any* win_rate and reward_risk_ratio, kelly_fraction SHALL equal 
        0.5 * (win_rate - (1 - win_rate) / reward_risk_ratio) when Half-Kelly enabled.
        **Validates: Requirements 5.4**
        """
        sizer = KellyCriterionSizer()
        
        # With Half-Kelly enabled (default), result is 0.5 * full Kelly
        full_kelly = win_rate - (1 - win_rate) / reward_risk_ratio
        expected = full_kelly * 0.5  # Half-Kelly
        actual = sizer.calculate_kelly_fraction(win_rate, reward_risk_ratio)
        
        assert abs(actual - expected) < 1e-10
    
    @given(
        win_rate=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        reward_risk_ratio=st.floats(min_value=0.1, max_value=10.0, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_full_kelly_when_disabled(self, win_rate, reward_risk_ratio):
        """Full Kelly should be returned when Half-Kelly is disabled."""
        config = SizingConfig(use_half_kelly=False)
        sizer = KellyCriterionSizer(config)
        
        expected = win_rate - (1 - win_rate) / reward_risk_ratio
        actual = sizer.calculate_kelly_fraction(win_rate, reward_risk_ratio)
        
        assert abs(actual - expected) < 1e-10

    def test_kelly_fraction_zero_ratio(self):
        """Kelly fraction should be 0 when reward_risk_ratio is 0 or negative."""
        sizer = KellyCriterionSizer()
        # Zero ratio returns 0 (edge case protection)
        assert sizer.calculate_kelly_fraction(0.6, -1.0) == 0.0


class TestStakeClamping:
    """Tests for Property 13: Stake Clamping."""

    @given(stake_pct=st.floats(min_value=-100, max_value=100, allow_nan=False))
    @settings(max_examples=100)
    def test_stake_clamped_to_bounds(self, stake_pct):
        """
        **Feature: kinetic-empire, Property 13: Stake Clamping**
        
        *For any* calculated stake percentage, the final stake SHALL be 
        clamped to [0.5%, 5.0%].
        **Validates: Requirements 5.5**
        """
        sizer = KellyCriterionSizer()
        
        clamped = sizer.clamp_stake(stake_pct)
        
        assert clamped >= sizer.config.min_stake_pct
        assert clamped <= sizer.config.max_stake_pct

    @given(
        stake_pct=st.floats(min_value=0.5, max_value=5.0, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_stake_within_bounds_unchanged(self, stake_pct):
        """Stake within bounds should remain unchanged."""
        sizer = KellyCriterionSizer()
        
        clamped = sizer.clamp_stake(stake_pct)
        
        assert abs(clamped - stake_pct) < 1e-10


class TestKellyDefaultForInsufficientHistory:
    """Tests for Property 10: Kelly Criterion Default for Insufficient History."""

    @given(
        num_trades=st.integers(min_value=0, max_value=9),
        balance=st.floats(min_value=100, max_value=100000, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_default_stake_for_insufficient_history(self, num_trades, balance):
        """
        **Feature: kinetic-empire, Property 10: Kelly Criterion Default for Insufficient History**
        
        *For any* pair with fewer than 10 closed trades, stake percentage 
        SHALL be exactly 1.0%.
        **Validates: Requirements 5.2**
        """
        sizer = KellyCriterionSizer()
        
        # Create trades with insufficient history
        trades = []
        for i in range(num_trades):
            trade = Trade(
                id=f"trade_{i}",
                pair="ETH/USDT",
                entry_timestamp=datetime(2023, 1, 1) + timedelta(hours=i),
                entry_price=1000.0,
                stake_amount=100.0,
                regime=Regime.BULL,
                stop_loss=950.0,
                exit_timestamp=datetime(2023, 1, 1) + timedelta(hours=i+1),
                exit_price=1050.0,
                profit_loss=50.0,
                exit_reason=ExitReason.TREND_BREAK,
            )
            trades.append(trade)
        
        stake_pct = sizer.calculate_stake_percentage("ETH/USDT", trades)
        
        assert stake_pct == sizer.config.default_stake_pct  # 1.0%

    @given(
        num_trades=st.integers(min_value=10, max_value=30),
        balance=st.floats(min_value=100, max_value=100000, allow_nan=False)
    )
    @settings(max_examples=100)
    def test_kelly_used_for_sufficient_history(self, num_trades, balance):
        """With sufficient history, Kelly Criterion should be used."""
        sizer = KellyCriterionSizer()
        
        # Create trades with sufficient history (all winners for predictable result)
        trades = []
        for i in range(num_trades):
            trade = Trade(
                id=f"trade_{i}",
                pair="ETH/USDT",
                entry_timestamp=datetime(2023, 1, 1) + timedelta(hours=i),
                entry_price=1000.0,
                stake_amount=100.0,
                regime=Regime.BULL,
                stop_loss=950.0,
                exit_timestamp=datetime(2023, 1, 1) + timedelta(hours=i+1),
                exit_price=1050.0,
                profit_loss=50.0,
                exit_reason=ExitReason.TREND_BREAK,
            )
            trades.append(trade)
        
        stake_pct = sizer.calculate_stake_percentage("ETH/USDT", trades)
        
        # With 100% win rate and default 2.0 reward/risk:
        # kelly = 1.0 - (0.0 / 2.0) = 1.0 = 100%
        # Clamped to max 5.0%
        assert stake_pct == sizer.config.max_stake_pct


class TestCalculateStake:
    """Integration tests for calculate_stake method."""

    def test_stake_amount_calculation(self):
        """Stake amount should be balance * stake_pct / 100."""
        sizer = KellyCriterionSizer()
        balance = 10000.0
        
        # With no history, should use default 1%
        stake = sizer.calculate_stake("NEW/USDT", balance, [])
        
        expected = balance * (sizer.config.default_stake_pct / 100)
        assert abs(stake - expected) < 1e-10

    def test_pair_filtering(self):
        """Only trades for the specific pair should be considered."""
        sizer = KellyCriterionSizer()
        
        # Create trades for different pairs
        trades = []
        for i in range(15):
            trade = Trade(
                id=f"trade_{i}",
                pair="BTC/USDT" if i < 5 else "ETH/USDT",
                entry_timestamp=datetime(2023, 1, 1) + timedelta(hours=i),
                entry_price=1000.0,
                stake_amount=100.0,
                regime=Regime.BULL,
                stop_loss=950.0,
                exit_timestamp=datetime(2023, 1, 1) + timedelta(hours=i+1),
                exit_price=1050.0,
                profit_loss=50.0,
                exit_reason=ExitReason.TREND_BREAK,
            )
            trades.append(trade)
        
        # BTC/USDT has only 5 trades, should use default
        btc_stake_pct = sizer.calculate_stake_percentage("BTC/USDT", trades)
        assert btc_stake_pct == sizer.config.default_stake_pct
        
        # ETH/USDT has 10 trades, should use Kelly
        eth_stake_pct = sizer.calculate_stake_percentage("ETH/USDT", trades)
        assert eth_stake_pct != sizer.config.default_stake_pct
