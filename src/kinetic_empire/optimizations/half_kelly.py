"""Half-Kelly Position Sizer.

Implements conservative position sizing using 50% of Kelly fraction
to reduce variance while maintaining edge.
"""

from dataclasses import dataclass
from typing import Optional, List

from kinetic_empire.models import Trade


@dataclass
class HalfKellyConfig:
    """Configuration for Half-Kelly position sizing."""
    min_stake_pct: float = 0.5      # Minimum stake as % of balance
    max_stake_pct: float = 5.0      # Maximum stake as % of balance
    default_stake_pct: float = 1.0  # Default stake when insufficient history
    min_trades_for_kelly: int = 10  # Minimum trades to use Kelly
    lookback_trades: int = 20       # Number of trades to analyze
    reward_risk_ratio: float = 2.0  # Expected reward/risk ratio
    kelly_fraction: float = 0.5     # Use 50% of full Kelly


class HalfKellySizer:
    """Calculates position size using Half-Kelly criterion.
    
    Half-Kelly provides:
    - 75% of full Kelly's expected growth rate
    - 50% of full Kelly's variance
    - Better drawdown characteristics
    """
    
    def __init__(self, config: Optional[HalfKellyConfig] = None):
        """Initialize Half-Kelly sizer.
        
        Args:
            config: Sizing configuration. Uses defaults if None.
        """
        self.config = config or HalfKellyConfig()
    
    def calculate_full_kelly(
        self,
        win_rate: float,
        rr_ratio: Optional[float] = None
    ) -> float:
        """Calculate full Kelly fraction.
        
        Formula: f* = win_rate - (1 - win_rate) / rr_ratio
        
        Args:
            win_rate: Probability of winning (0.0 to 1.0)
            rr_ratio: Reward/risk ratio
            
        Returns:
            Full Kelly fraction (can be negative if no edge)
        """
        rr_ratio = rr_ratio or self.config.reward_risk_ratio
        
        if rr_ratio <= 0:
            return 0.0
        
        loss_rate = 1 - win_rate
        return win_rate - (loss_rate / rr_ratio)
    
    def calculate_half_kelly(
        self,
        win_rate: float,
        rr_ratio: Optional[float] = None
    ) -> float:
        """Calculate Half-Kelly fraction.
        
        Args:
            win_rate: Probability of winning (0.0 to 1.0)
            rr_ratio: Reward/risk ratio
            
        Returns:
            Half-Kelly fraction (0.5 * full Kelly)
        """
        full_kelly = self.calculate_full_kelly(win_rate, rr_ratio)
        return full_kelly * self.config.kelly_fraction
    
    def clamp_stake(
        self,
        stake_pct: float,
        min_pct: Optional[float] = None,
        max_pct: Optional[float] = None
    ) -> float:
        """Clamp stake percentage to configured bounds.
        
        Args:
            stake_pct: Calculated stake percentage
            min_pct: Minimum stake percentage
            max_pct: Maximum stake percentage
            
        Returns:
            Stake percentage clamped to [min_pct, max_pct]
        """
        min_pct = min_pct if min_pct is not None else self.config.min_stake_pct
        max_pct = max_pct if max_pct is not None else self.config.max_stake_pct
        
        return max(min_pct, min(stake_pct, max_pct))
    
    def calculate_win_rate(self, trades: List[Trade]) -> float:
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
    
    def get_pair_trades(
        self,
        pair: str,
        trade_history: List[Trade],
        limit: Optional[int] = None
    ) -> List[Trade]:
        """Get closed trades for a specific pair.
        
        Args:
            pair: Trading pair symbol
            trade_history: Full trade history
            limit: Maximum trades to return
            
        Returns:
            List of closed trades for the pair, most recent first
        """
        limit = limit or self.config.lookback_trades
        
        pair_trades = [
            t for t in trade_history
            if t.pair == pair and t.is_closed
        ]
        
        pair_trades.sort(
            key=lambda t: t.exit_timestamp or t.entry_timestamp,
            reverse=True
        )
        
        return pair_trades[:limit]
    
    def get_stake_percentage(
        self,
        pair: str,
        trade_history: List[Trade]
    ) -> float:
        """Calculate stake percentage using Half-Kelly.
        
        Args:
            pair: Trading pair symbol
            trade_history: Full trade history
            
        Returns:
            Stake percentage (clamped to bounds)
        """
        pair_trades = self.get_pair_trades(pair, trade_history)
        
        # Use default if insufficient history
        if len(pair_trades) < self.config.min_trades_for_kelly:
            return self.config.default_stake_pct
        
        win_rate = self.calculate_win_rate(pair_trades)
        half_kelly = self.calculate_half_kelly(win_rate)
        
        # Convert to percentage
        stake_pct = half_kelly * 100
        
        # Handle negative edge (no edge)
        if stake_pct <= 0:
            return self.config.min_stake_pct
        
        return self.clamp_stake(stake_pct)
    
    def calculate_stake(
        self,
        pair: str,
        available_balance: float,
        trade_history: List[Trade]
    ) -> float:
        """Calculate stake amount using Half-Kelly.
        
        Args:
            pair: Trading pair symbol
            available_balance: Available balance in quote currency
            trade_history: Full trade history
            
        Returns:
            Stake amount in quote currency
        """
        stake_pct = self.get_stake_percentage(pair, trade_history)
        return available_balance * (stake_pct / 100)
