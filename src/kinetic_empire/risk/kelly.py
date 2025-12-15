"""Kelly Criterion position sizing module.

Implements dynamic position sizing based on historical performance per asset,
rewarding winning pairs with larger allocations while managing risk.

Enhanced with Half-Kelly option for reduced variance while maintaining edge.
"""

from dataclasses import dataclass
from typing import Optional

from kinetic_empire.models import Trade
from kinetic_empire.optimizations import HalfKellySizer
from kinetic_empire.optimizations.half_kelly import HalfKellyConfig


@dataclass
class SizingConfig:
    """Configuration for Kelly Criterion position sizing."""
    min_stake_pct: float = 0.5      # Minimum stake as % of balance
    max_stake_pct: float = 5.0      # Maximum stake as % of balance
    default_stake_pct: float = 1.0  # Default stake when insufficient history
    min_trades_for_kelly: int = 10  # Minimum trades to use Kelly
    lookback_trades: int = 20       # Number of trades to analyze
    reward_risk_ratio: float = 2.0  # Expected reward/risk ratio
    use_half_kelly: bool = True     # Use Half-Kelly for reduced variance


class KellyCriterionSizer:
    """Calculates optimal position size using Kelly Criterion.
    
    The Kelly Criterion formula:
    f* = (p * b - q) / b = p - q/b
    
    Where:
    - f* = fraction of bankroll to bet
    - p = probability of winning (win rate)
    - q = probability of losing (1 - p)
    - b = odds received on the bet (reward/risk ratio)
    
    Simplified: f* = win_rate - (1 - win_rate) / reward_risk_ratio
    """

    def __init__(self, config: Optional[SizingConfig] = None):
        """Initialize Kelly Criterion sizer.
        
        Args:
            config: Sizing configuration. Uses defaults if None.
        """
        self.config = config or SizingConfig()
        
        # Initialize Half-Kelly sizer if enabled
        if self.config.use_half_kelly:
            half_kelly_config = HalfKellyConfig(
                min_stake_pct=self.config.min_stake_pct,
                max_stake_pct=self.config.max_stake_pct,
                default_stake_pct=self.config.default_stake_pct,
                min_trades_for_kelly=self.config.min_trades_for_kelly,
                lookback_trades=self.config.lookback_trades,
                reward_risk_ratio=self.config.reward_risk_ratio,
                kelly_fraction=0.5  # Half-Kelly
            )
            self._half_kelly = HalfKellySizer(half_kelly_config)
        else:
            self._half_kelly = None

    def calculate_win_rate(self, trades: list[Trade]) -> float:
        """Calculate win rate from trade history.
        
        Args:
            trades: List of closed trades
            
        Returns:
            Win rate as decimal (0.0 to 1.0)
        """
        if not trades:
            return 0.0
        
        winning_trades = sum(1 for t in trades if t.is_winner)
        return winning_trades / len(trades)

    def calculate_kelly_fraction(
        self,
        win_rate: float,
        reward_risk_ratio: Optional[float] = None
    ) -> float:
        """Calculate Kelly fraction from win rate and reward/risk ratio.
        
        Formula: f* = win_rate - (1 - win_rate) / reward_risk_ratio
        
        If use_half_kelly is enabled, returns Half-Kelly (0.5 * full Kelly).
        
        Args:
            win_rate: Probability of winning (0.0 to 1.0)
            reward_risk_ratio: Expected reward/risk ratio
            
        Returns:
            Kelly fraction (can be negative if edge is negative)
        """
        rr_ratio = reward_risk_ratio or self.config.reward_risk_ratio
        
        if rr_ratio <= 0:
            return 0.0
        
        # Use Half-Kelly if enabled
        if self._half_kelly is not None:
            return self._half_kelly.calculate_half_kelly(win_rate, rr_ratio)
        
        loss_rate = 1 - win_rate
        return win_rate - (loss_rate / rr_ratio)

    def clamp_stake(
        self,
        stake_pct: float,
        min_pct: Optional[float] = None,
        max_pct: Optional[float] = None
    ) -> float:
        """Clamp stake percentage to configured bounds.
        
        Args:
            stake_pct: Calculated stake percentage
            min_pct: Minimum stake percentage (default from config)
            max_pct: Maximum stake percentage (default from config)
            
        Returns:
            Stake percentage clamped to [min_pct, max_pct]
        """
        min_pct = min_pct if min_pct is not None else self.config.min_stake_pct
        max_pct = max_pct if max_pct is not None else self.config.max_stake_pct
        
        return max(min_pct, min(stake_pct, max_pct))

    def get_pair_trades(
        self,
        pair: str,
        trade_history: list[Trade],
        limit: Optional[int] = None
    ) -> list[Trade]:
        """Get closed trades for a specific pair.
        
        Args:
            pair: Trading pair symbol
            trade_history: Full trade history
            limit: Maximum trades to return (default from config)
            
        Returns:
            List of closed trades for the pair, most recent first
        """
        limit = limit or self.config.lookback_trades
        
        # Filter for pair and closed trades
        pair_trades = [
            t for t in trade_history
            if t.pair == pair and t.is_closed
        ]
        
        # Sort by exit timestamp descending (most recent first)
        pair_trades.sort(
            key=lambda t: t.exit_timestamp or t.entry_timestamp,
            reverse=True
        )
        
        return pair_trades[:limit]

    def calculate_stake(
        self,
        pair: str,
        available_balance: float,
        trade_history: list[Trade]
    ) -> float:
        """Calculate stake amount using Kelly Criterion.
        
        If fewer than min_trades_for_kelly trades exist for the pair,
        uses the conservative default stake percentage.
        
        Args:
            pair: Trading pair symbol
            available_balance: Available balance in quote currency
            trade_history: Full trade history
            
        Returns:
            Stake amount in quote currency
        """
        # Get recent trades for this pair
        pair_trades = self.get_pair_trades(pair, trade_history)
        
        # Use default stake if insufficient history
        if len(pair_trades) < self.config.min_trades_for_kelly:
            stake_pct = self.config.default_stake_pct
        else:
            # Calculate Kelly fraction from win rate
            win_rate = self.calculate_win_rate(pair_trades)
            kelly_fraction = self.calculate_kelly_fraction(win_rate)
            
            # Convert to percentage and clamp
            stake_pct = kelly_fraction * 100
            stake_pct = self.clamp_stake(stake_pct)
        
        # Calculate actual stake amount
        return available_balance * (stake_pct / 100)

    def calculate_stake_percentage(
        self,
        pair: str,
        trade_history: list[Trade]
    ) -> float:
        """Calculate stake percentage using Kelly Criterion.
        
        Args:
            pair: Trading pair symbol
            trade_history: Full trade history
            
        Returns:
            Stake percentage (0.5 to 5.0)
        """
        pair_trades = self.get_pair_trades(pair, trade_history)
        
        if len(pair_trades) < self.config.min_trades_for_kelly:
            return self.config.default_stake_pct
        
        win_rate = self.calculate_win_rate(pair_trades)
        kelly_fraction = self.calculate_kelly_fraction(win_rate)
        stake_pct = kelly_fraction * 100
        
        return self.clamp_stake(stake_pct)

