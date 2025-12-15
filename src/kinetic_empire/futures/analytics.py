"""Advanced Analytics and Performance Tracking.

Tracks performance metrics, calculates Sharpe ratio, win rates,
and provides insights for optimization.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TradeResult:
    """Individual trade result."""
    symbol: str
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    pnl_pct: float
    duration_minutes: int
    trade_type: str  # "GRID_COMPLETE", "STOP_LOSS", "TAKE_PROFIT"


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics."""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    calmar_ratio: float = 0.0
    sortino_ratio: float = 0.0
    avg_trade_duration: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    recovery_factor: float = 0.0


class PerformanceTracker:
    """Advanced performance tracking and analytics."""
    
    def __init__(self, initial_balance: float = 0.0):
        self.trades: List[TradeResult] = []
        self.daily_pnl: Dict[str, float] = {}
        self.equity_curve: List[Tuple[datetime, float]] = []
        self.initial_balance = initial_balance
        self.peak_balance = initial_balance
        self.current_balance = initial_balance
    
    def set_initial_balance(self, balance: float):
        """Set initial balance for tracking."""
        self.initial_balance = balance
        self.peak_balance = balance
        self.current_balance = balance
        self.equity_curve = [(datetime.now(), balance)]
    
    def add_trade(self, trade: TradeResult):
        """Add a completed trade to tracking."""
        self.trades.append(trade)
        
        # Update balance
        self.current_balance += trade.pnl
        
        # Update daily P&L
        date_str = trade.exit_time.strftime('%Y-%m-%d')
        self.daily_pnl[date_str] = self.daily_pnl.get(date_str, 0) + trade.pnl
        
        # Update equity curve
        self.equity_curve.append((trade.exit_time, self.current_balance))
        
        # Update peak balance
        self.peak_balance = max(self.peak_balance, self.current_balance)
        
        logger.info(f"📈 Trade recorded: {trade.symbol} P&L: ${trade.pnl:.2f} ({trade.pnl_pct:.2f}%)")
    
    def calculate_metrics(self, lookback_days: Optional[int] = None) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics."""
        if not self.trades:
            return PerformanceMetrics()
        
        # Filter trades by lookback period
        trades = self.trades
        if lookback_days:
            cutoff_date = datetime.now() - timedelta(days=lookback_days)
            trades = [t for t in trades if t.exit_time >= cutoff_date]
        
        if not trades:
            return PerformanceMetrics()
        
        # Basic counts
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t.pnl > 0])
        losing_trades = len([t for t in trades if t.pnl <= 0])
        
        # Win rate
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # P&L metrics
        total_pnl = sum(t.pnl for t in trades)
        pnl_list = [t.pnl for t in trades]
        
        wins = [t.pnl for t in trades if t.pnl > 0]
        losses = [abs(t.pnl) for t in trades if t.pnl <= 0]
        
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0
        
        # Profit factor
        gross_profit = sum(wins) if wins else 0
        gross_loss = sum(losses) if losses else 1
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Sharpe ratio (annualized)
        if len(pnl_list) > 1:
            returns = np.array(pnl_list) / self.initial_balance if self.initial_balance > 0 else np.array(pnl_list)
            sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Max drawdown
        max_drawdown, max_drawdown_pct = self._calculate_max_drawdown()
        
        # Sortino ratio (only downside volatility)
        negative_returns = [r for r in pnl_list if r < 0]
        if negative_returns and self.initial_balance > 0:
            downside_std = np.std(negative_returns) / self.initial_balance
            sortino_ratio = (np.mean(pnl_list) / self.initial_balance) / downside_std * np.sqrt(252) if downside_std > 0 else 0
        else:
            sortino_ratio = 0
        
        # Calmar ratio
        annual_return = total_pnl / self.initial_balance if self.initial_balance > 0 else 0
        calmar_ratio = annual_return / max_drawdown_pct if max_drawdown_pct > 0 else 0
        
        # Trade duration
        durations = [t.duration_minutes for t in trades]
        avg_trade_duration = np.mean(durations) if durations else 0
        
        # Best/worst trades
        best_trade = max(pnl_list) if pnl_list else 0
        worst_trade = min(pnl_list) if pnl_list else 0
        
        # Consecutive wins/losses
        consecutive_wins, consecutive_losses = self._calculate_streaks(trades)
        
        # Recovery factor
        recovery_factor = total_pnl / max_drawdown if max_drawdown > 0 else 0
        
        # Total P&L percentage
        total_pnl_pct = (total_pnl / self.initial_balance * 100) if self.initial_balance > 0 else 0
        
        return PerformanceMetrics(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            max_drawdown_pct=max_drawdown_pct,
            calmar_ratio=calmar_ratio,
            sortino_ratio=sortino_ratio,
            avg_trade_duration=avg_trade_duration,
            best_trade=best_trade,
            worst_trade=worst_trade,
            consecutive_wins=consecutive_wins,
            consecutive_losses=consecutive_losses,
            recovery_factor=recovery_factor
        )
    
    def _calculate_max_drawdown(self) -> Tuple[float, float]:
        """Calculate maximum drawdown from equity curve."""
        if len(self.equity_curve) < 2:
            return 0.0, 0.0
        
        balances = [b for _, b in self.equity_curve]
        peak = balances[0]
        max_dd = 0.0
        max_dd_pct = 0.0
        
        for balance in balances:
            if balance > peak:
                peak = balance
            dd = peak - balance
            dd_pct = dd / peak if peak > 0 else 0
            
            if dd > max_dd:
                max_dd = dd
            if dd_pct > max_dd_pct:
                max_dd_pct = dd_pct
        
        return max_dd, max_dd_pct * 100
    
    def _calculate_streaks(self, trades: List[TradeResult]) -> Tuple[int, int]:
        """Calculate max consecutive wins and losses."""
        if not trades:
            return 0, 0
        
        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0
        
        for trade in trades:
            if trade.pnl > 0:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)
        
        return max_wins, max_losses
    
    def get_pair_performance(self, symbol: str) -> Dict:
        """Get performance metrics for a specific pair."""
        pair_trades = [t for t in self.trades if t.symbol == symbol]
        
        if not pair_trades:
            return {'symbol': symbol, 'trades': 0}
        
        wins = len([t for t in pair_trades if t.pnl > 0])
        total_pnl = sum(t.pnl for t in pair_trades)
        
        return {
            'symbol': symbol,
            'trades': len(pair_trades),
            'wins': wins,
            'win_rate': wins / len(pair_trades),
            'total_pnl': total_pnl,
            'avg_pnl': total_pnl / len(pair_trades),
            'best_trade': max(t.pnl for t in pair_trades),
            'worst_trade': min(t.pnl for t in pair_trades)
        }
    
    def get_daily_summary(self, date: Optional[str] = None) -> Dict:
        """Get daily performance summary."""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        daily_trades = [t for t in self.trades 
                       if t.exit_time.strftime('%Y-%m-%d') == date]
        
        if not daily_trades:
            return {'date': date, 'trades': 0, 'pnl': 0}
        
        return {
            'date': date,
            'trades': len(daily_trades),
            'wins': len([t for t in daily_trades if t.pnl > 0]),
            'pnl': sum(t.pnl for t in daily_trades),
            'win_rate': len([t for t in daily_trades if t.pnl > 0]) / len(daily_trades)
        }
    
    def print_summary(self):
        """Print formatted performance summary."""
        metrics = self.calculate_metrics()
        
        print("\n" + "=" * 60)
        print("📊 PERFORMANCE SUMMARY")
        print("=" * 60)
        print(f"Total Trades:      {metrics.total_trades}")
        print(f"Win Rate:          {metrics.win_rate:.1%}")
        print(f"Total P&L:         ${metrics.total_pnl:,.2f} ({metrics.total_pnl_pct:.2f}%)")
        print(f"Profit Factor:     {metrics.profit_factor:.2f}")
        print(f"Sharpe Ratio:      {metrics.sharpe_ratio:.2f}")
        print(f"Max Drawdown:      ${metrics.max_drawdown:,.2f} ({metrics.max_drawdown_pct:.2f}%)")
        print(f"Avg Win:           ${metrics.avg_win:,.2f}")
        print(f"Avg Loss:          ${metrics.avg_loss:,.2f}")
        print(f"Best Trade:        ${metrics.best_trade:,.2f}")
        print(f"Worst Trade:       ${metrics.worst_trade:,.2f}")
        print(f"Consecutive Wins:  {metrics.consecutive_wins}")
        print(f"Consecutive Losses:{metrics.consecutive_losses}")
        print("=" * 60)
