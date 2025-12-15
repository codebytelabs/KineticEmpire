"""Backtesting engine for strategy validation.

Provides historical simulation with realistic slippage and fee calculations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import math

from kinetic_empire.models import Trade, BacktestResult, Regime, ExitReason


@dataclass
class BacktestConfig:
    """Configuration for backtesting."""
    initial_balance: float = 10000.0
    slippage_pct: float = 0.05  # 0.05% slippage
    fee_pct: float = 0.1        # 0.1% fee per trade
    risk_free_rate: float = 0.02  # 2% annual risk-free rate


@dataclass
class SimulatedTrade:
    """A simulated trade during backtest."""
    id: str
    pair: str
    entry_time: datetime
    entry_price: float
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    stake_amount: float = 0.0
    amount: float = 0.0
    slippage_entry: float = 0.0
    slippage_exit: float = 0.0
    fee_entry: float = 0.0
    fee_exit: float = 0.0
    profit_loss: Optional[float] = None
    exit_reason: Optional[ExitReason] = None


class BacktestEngine:
    """Engine for backtesting trading strategies.
    
    Features:
    - Historical OHLCV data simulation
    - Realistic slippage and fee calculations
    - Performance metrics calculation
    """
    
    def __init__(self, config: Optional[BacktestConfig] = None):
        """Initialize backtest engine.
        
        Args:
            config: Backtest configuration
        """
        self.config = config or BacktestConfig()
        self._trades: list[SimulatedTrade] = []
        self._balance = self.config.initial_balance
        self._peak_balance = self.config.initial_balance
        self._max_drawdown = 0.0
        self._daily_returns: list[float] = []
    
    def apply_slippage(self, price: float, is_buy: bool) -> tuple[float, float]:
        """Apply slippage to price.
        
        Args:
            price: Original price
            is_buy: True for buy orders (slippage increases price)
            
        Returns:
            Tuple of (adjusted_price, slippage_amount)
        """
        slippage_multiplier = 1 + (self.config.slippage_pct / 100)
        
        if is_buy:
            adjusted_price = price * slippage_multiplier
        else:
            adjusted_price = price / slippage_multiplier
        
        slippage_amount = abs(adjusted_price - price)
        return adjusted_price, slippage_amount
    
    def calculate_fee(self, amount: float, price: float) -> float:
        """Calculate trading fee.
        
        Args:
            amount: Trade amount
            price: Trade price
            
        Returns:
            Fee amount
        """
        trade_value = amount * price
        return trade_value * (self.config.fee_pct / 100)
    
    def simulate_entry(
        self,
        trade_id: str,
        pair: str,
        entry_time: datetime,
        entry_price: float,
        stake_amount: float
    ) -> SimulatedTrade:
        """Simulate trade entry with slippage and fees.
        
        Args:
            trade_id: Unique trade ID
            pair: Trading pair
            entry_time: Entry timestamp
            entry_price: Intended entry price
            stake_amount: Stake amount
            
        Returns:
            Simulated trade
        """
        # Apply slippage
        adjusted_price, slippage = self.apply_slippage(entry_price, is_buy=True)
        
        # Calculate amount after fees
        fee = self.calculate_fee(stake_amount / adjusted_price, adjusted_price)
        effective_stake = stake_amount - fee
        amount = effective_stake / adjusted_price
        
        trade = SimulatedTrade(
            id=trade_id,
            pair=pair,
            entry_time=entry_time,
            entry_price=adjusted_price,
            stake_amount=stake_amount,
            amount=amount,
            slippage_entry=slippage,
            fee_entry=fee
        )
        
        self._trades.append(trade)
        self._balance -= stake_amount
        
        return trade
    
    def simulate_exit(
        self,
        trade: SimulatedTrade,
        exit_time: datetime,
        exit_price: float,
        exit_reason: ExitReason
    ) -> SimulatedTrade:
        """Simulate trade exit with slippage and fees.
        
        Args:
            trade: Trade to close
            exit_time: Exit timestamp
            exit_price: Intended exit price
            exit_reason: Reason for exit
            
        Returns:
            Updated trade
        """
        # Apply slippage
        adjusted_price, slippage = self.apply_slippage(exit_price, is_buy=False)
        
        # Calculate exit value and fee
        exit_value = trade.amount * adjusted_price
        fee = self.calculate_fee(trade.amount, adjusted_price)
        net_exit_value = exit_value - fee
        
        # Calculate profit/loss
        profit_loss = net_exit_value - trade.stake_amount
        
        # Update trade
        trade.exit_time = exit_time
        trade.exit_price = adjusted_price
        trade.slippage_exit = slippage
        trade.fee_exit = fee
        trade.profit_loss = profit_loss
        trade.exit_reason = exit_reason
        
        # Update balance
        self._balance += net_exit_value
        
        # Track drawdown
        if self._balance > self._peak_balance:
            self._peak_balance = self._balance
        
        current_drawdown = (self._peak_balance - self._balance) / self._peak_balance
        if current_drawdown > self._max_drawdown:
            self._max_drawdown = current_drawdown
        
        return trade
    
    def calculate_sharpe_ratio(self, returns: list[float]) -> float:
        """Calculate Sharpe ratio from returns.
        
        Args:
            returns: List of period returns
            
        Returns:
            Sharpe ratio
        """
        if not returns or len(returns) < 2:
            return 0.0
        
        mean_return = sum(returns) / len(returns)
        
        # Calculate standard deviation
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        std_dev = math.sqrt(variance)
        
        if std_dev == 0:
            return 0.0
        
        # Annualize (assuming daily returns)
        daily_risk_free = self.config.risk_free_rate / 365
        excess_return = mean_return - daily_risk_free
        
        # Annualized Sharpe
        return (excess_return / std_dev) * math.sqrt(365)
    
    def generate_report(self) -> BacktestResult:
        """Generate backtest performance report.
        
        Returns:
            BacktestResult with all metrics
        """
        closed_trades = [t for t in self._trades if t.exit_time is not None]
        
        if not closed_trades:
            return BacktestResult(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                total_return_pct=0.0,
                max_drawdown_pct=0.0,
                sharpe_ratio=0.0,
                trades=[]
            )
        
        # Count wins/losses
        winning_trades = sum(1 for t in closed_trades if t.profit_loss > 0)
        losing_trades = len(closed_trades) - winning_trades
        
        # Calculate total return
        total_return_pct = (
            (self._balance - self.config.initial_balance) / 
            self.config.initial_balance * 100
        )
        
        # Calculate returns for Sharpe
        returns = []
        for trade in closed_trades:
            if trade.stake_amount > 0:
                trade_return = trade.profit_loss / trade.stake_amount
                returns.append(trade_return)
        
        sharpe = self.calculate_sharpe_ratio(returns)
        
        # Convert to Trade objects
        trade_objects = [
            Trade(
                id=t.id,
                pair=t.pair,
                entry_timestamp=t.entry_time,
                entry_price=t.entry_price,
                stake_amount=t.stake_amount,
                regime=Regime.BULL,  # Default
                stop_loss=0.0,
                amount=t.amount,
                exit_timestamp=t.exit_time,
                exit_price=t.exit_price,
                profit_loss=t.profit_loss,
                exit_reason=t.exit_reason
            )
            for t in closed_trades
        ]
        
        return BacktestResult(
            total_trades=len(closed_trades),
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            total_return_pct=total_return_pct,
            max_drawdown_pct=self._max_drawdown * 100,
            sharpe_ratio=sharpe,
            trades=trade_objects
        )
    
    def reset(self) -> None:
        """Reset backtest state."""
        self._trades = []
        self._balance = self.config.initial_balance
        self._peak_balance = self.config.initial_balance
        self._max_drawdown = 0.0
        self._daily_returns = []
    
    def get_balance(self) -> float:
        """Get current balance.
        
        Returns:
            Current balance
        """
        return self._balance
    
    def get_trades(self) -> list[SimulatedTrade]:
        """Get all simulated trades.
        
        Returns:
            List of trades
        """
        return self._trades.copy()
