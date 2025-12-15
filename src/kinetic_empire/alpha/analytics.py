"""Performance Analytics Module - Track and analyze trading performance.

Records trades and calculates metrics per strategy and overall portfolio.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import statistics
import csv
import io


@dataclass
class TradeRecord:
    """Record of a completed trade."""
    strategy: str
    pair: str
    side: str
    entry_price: float
    exit_price: float
    quantity: float
    entry_time: datetime
    exit_time: datetime
    pnl: float
    r_multiple: float
    exit_reason: str
    
    @property
    def hold_time_minutes(self) -> int:
        return int((self.exit_time - self.entry_time).total_seconds() / 60)
    
    @property
    def return_pct(self) -> float:
        if self.side == "LONG":
            return (self.exit_price - self.entry_price) / self.entry_price * 100
        return (self.entry_price - self.exit_price) / self.entry_price * 100
    
    def to_dict(self) -> dict:
        return {
            "strategy": self.strategy,
            "pair": self.pair,
            "side": self.side,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "quantity": self.quantity,
            "entry_time": self.entry_time.isoformat(),
            "exit_time": self.exit_time.isoformat(),
            "pnl": self.pnl,
            "r_multiple": self.r_multiple,
            "hold_time_minutes": self.hold_time_minutes,
            "return_pct": self.return_pct,
            "exit_reason": self.exit_reason,
        }


class PerformanceAnalytics:
    """Track and analyze trading performance."""
    
    def __init__(self):
        self.trades: List[TradeRecord] = []
        self.daily_pnl: Dict[str, Dict[str, float]] = {}  # date -> strategy -> pnl
    
    def record_trade(self, trade: TradeRecord) -> None:
        """Record a completed trade."""
        self.trades.append(trade)
        
        # Update daily P&L
        date_str = trade.exit_time.strftime("%Y-%m-%d")
        if date_str not in self.daily_pnl:
            self.daily_pnl[date_str] = {}
        
        strategy = trade.strategy
        if strategy not in self.daily_pnl[date_str]:
            self.daily_pnl[date_str][strategy] = 0.0
        
        self.daily_pnl[date_str][strategy] += trade.pnl
    
    def get_strategy_trades(self, strategy: str) -> List[TradeRecord]:
        """Get all trades for a strategy."""
        return [t for t in self.trades if t.strategy == strategy]
    
    def calculate_metrics(self, strategy: Optional[str] = None) -> dict:
        """Calculate performance metrics for a strategy or overall."""
        trades = self.get_strategy_trades(strategy) if strategy else self.trades
        
        if not trades:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "avg_r": 0.0,
                "total_pnl": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
            }
        
        winning = [t for t in trades if t.pnl > 0]
        
        return {
            "total_trades": len(trades),
            "winning_trades": len(winning),
            "losing_trades": len(trades) - len(winning),
            "win_rate": len(winning) / len(trades) * 100,
            "avg_r": statistics.mean([t.r_multiple for t in trades]),
            "total_pnl": sum(t.pnl for t in trades),
            "avg_pnl": statistics.mean([t.pnl for t in trades]),
            "best_trade": max(t.pnl for t in trades),
            "worst_trade": min(t.pnl for t in trades),
            "avg_hold_time_min": statistics.mean([t.hold_time_minutes for t in trades]),
            "sharpe_ratio": self._calculate_sharpe(trades),
            "max_drawdown": self._calculate_max_drawdown(trades),
        }
    
    def _calculate_sharpe(self, trades: List[TradeRecord]) -> float:
        """Calculate Sharpe ratio from trades."""
        if len(trades) < 2:
            return 0.0
        
        returns = [t.return_pct for t in trades]
        mean_return = statistics.mean(returns)
        std_return = statistics.stdev(returns)
        
        if std_return == 0:
            return 0.0
        
        # Annualized (assuming ~250 trading days)
        return (mean_return / std_return) * (250 ** 0.5)
    
    def _calculate_max_drawdown(self, trades: List[TradeRecord]) -> float:
        """Calculate maximum drawdown from trades."""
        if not trades:
            return 0.0
        
        cumulative = 0.0
        peak = 0.0
        max_dd = 0.0
        
        for trade in sorted(trades, key=lambda t: t.exit_time):
            cumulative += trade.pnl
            peak = max(peak, cumulative)
            dd = (peak - cumulative) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
        
        return max_dd * 100  # As percentage
    
    def get_daily_pnl(self, strategy: Optional[str] = None, 
                     days: int = 30) -> Dict[str, float]:
        """Get daily P&L for last N days."""
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff.strftime("%Y-%m-%d")
        
        result = {}
        for date_str, strategies in self.daily_pnl.items():
            if date_str >= cutoff_str:
                if strategy:
                    result[date_str] = strategies.get(strategy, 0.0)
                else:
                    result[date_str] = sum(strategies.values())
        
        return result
    
    def get_best_pairs(self, strategy: str, n: int = 5) -> List[tuple]:
        """Get best performing pairs for a strategy."""
        trades = self.get_strategy_trades(strategy)
        
        pair_pnl = {}
        for trade in trades:
            if trade.pair not in pair_pnl:
                pair_pnl[trade.pair] = 0.0
            pair_pnl[trade.pair] += trade.pnl
        
        sorted_pairs = sorted(pair_pnl.items(), key=lambda x: x[1], reverse=True)
        return sorted_pairs[:n]
    
    def get_worst_pairs(self, strategy: str, n: int = 5) -> List[tuple]:
        """Get worst performing pairs for a strategy."""
        trades = self.get_strategy_trades(strategy)
        
        pair_pnl = {}
        for trade in trades:
            if trade.pair not in pair_pnl:
                pair_pnl[trade.pair] = 0.0
            pair_pnl[trade.pair] += trade.pnl
        
        sorted_pairs = sorted(pair_pnl.items(), key=lambda x: x[1])
        return sorted_pairs[:n]
    
    def calculate_strategy_correlations(self) -> Dict[tuple, float]:
        """Calculate correlations between strategy returns."""
        strategies = list(set(t.strategy for t in self.trades))
        
        if len(strategies) < 2:
            return {}
        
        # Get daily returns per strategy
        strategy_returns = {s: [] for s in strategies}
        
        for date_str in sorted(self.daily_pnl.keys()):
            for strategy in strategies:
                pnl = self.daily_pnl[date_str].get(strategy, 0.0)
                strategy_returns[strategy].append(pnl)
        
        # Calculate correlations
        correlations = {}
        for i, s1 in enumerate(strategies):
            for s2 in strategies[i+1:]:
                r1 = strategy_returns[s1]
                r2 = strategy_returns[s2]
                
                if len(r1) >= 2 and len(r2) >= 2:
                    corr = self._pearson_correlation(r1, r2)
                    correlations[(s1, s2)] = corr
        
        return correlations
    
    def _pearson_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation coefficient."""
        n = min(len(x), len(y))
        if n < 2:
            return 0.0
        
        x = x[:n]
        y = y[:n]
        
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        
        numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        
        sum_sq_x = sum((xi - mean_x) ** 2 for xi in x)
        sum_sq_y = sum((yi - mean_y) ** 2 for yi in y)
        
        denominator = (sum_sq_x * sum_sq_y) ** 0.5
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    def export_to_csv(self) -> str:
        """Export trades to CSV format."""
        if not self.trades:
            return ""
        
        output = io.StringIO()
        fieldnames = [
            "strategy", "pair", "side", "entry_price", "exit_price",
            "quantity", "entry_time", "exit_time", "pnl", "r_multiple",
            "hold_time_minutes", "return_pct", "exit_reason"
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for trade in self.trades:
            writer.writerow(trade.to_dict())
        
        return output.getvalue()
