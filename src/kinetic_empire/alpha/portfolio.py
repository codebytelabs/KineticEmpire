"""Portfolio Manager - Dynamic allocation across strategies.

Manages capital allocation based on strategy performance (Sharpe ratio).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import statistics

from .models import StrategyPerformance


@dataclass
class PortfolioConfig:
    """Configuration for portfolio management."""
    initial_allocations: Dict[str, float] = field(default_factory=lambda: {
        'funding_arbitrage': 0.40,
        'wave_rider': 0.30,
        'smart_grid': 0.20,
        'reserve': 0.10
    })
    min_allocation: float = 0.10
    max_allocation: float = 0.60
    rebalance_threshold: float = 0.50  # Rebalance if Sharpe differs by 50%
    rebalance_amount: float = 0.05  # Move 5% allocation per rebalance
    rebalance_interval_hours: int = 24


class PortfolioManager:
    """Manages capital allocation across strategies."""
    
    def __init__(self, config: Optional[PortfolioConfig] = None, 
                 total_capital: float = 10000.0):
        self.config = config or PortfolioConfig()
        self.total_capital = total_capital
        self.allocations = self.config.initial_allocations.copy()
        self.performance: Dict[str, StrategyPerformance] = {}
        self.last_rebalance = datetime.now()
        
        # Initialize performance tracking
        for strategy in self.allocations:
            if strategy != 'reserve':
                self.performance[strategy] = StrategyPerformance(strategy_name=strategy)
    
    def get_strategy_capital(self, strategy_name: str) -> float:
        """Get capital allocated to a strategy."""
        return self.total_capital * self.allocations.get(strategy_name, 0)
    
    def get_allocation(self, strategy_name: str) -> float:
        """Get allocation percentage for a strategy."""
        return self.allocations.get(strategy_name, 0)
    
    def update_total_capital(self, new_capital: float) -> None:
        """Update total capital."""
        self.total_capital = new_capital
    
    def record_trade(self, strategy: str, pnl: float, r_multiple: float = 0) -> None:
        """Record a completed trade for a strategy."""
        if strategy not in self.performance:
            self.performance[strategy] = StrategyPerformance(strategy_name=strategy)
        
        perf = self.performance[strategy]
        perf.total_trades += 1
        perf.total_pnl += pnl
        perf.total_r_gained += r_multiple
        
        if pnl > 0:
            perf.winning_trades += 1
        else:
            perf.losing_trades += 1

    
    def record_daily_return(self, strategy: str, daily_return: float) -> None:
        """Record daily return for Sharpe calculation."""
        if strategy not in self.performance:
            self.performance[strategy] = StrategyPerformance(strategy_name=strategy)
        self.performance[strategy].daily_returns.append(daily_return)
    
    def calculate_strategy_sharpe(self, strategy: str, lookback_days: int = 30) -> float:
        """Calculate rolling Sharpe ratio for a strategy."""
        if strategy not in self.performance:
            return 0.0
        
        returns = self.performance[strategy].daily_returns[-lookback_days:]
        if len(returns) < 2:
            return 0.0
        
        mean_return = statistics.mean(returns)
        std_return = statistics.stdev(returns)
        
        if std_return == 0:
            return 0.0
        
        # Annualized Sharpe
        return (mean_return / std_return) * (365 ** 0.5)
    
    def should_rebalance(self) -> bool:
        """Check if allocations should be rebalanced."""
        # Check time since last rebalance
        hours_since = (datetime.now() - self.last_rebalance).total_seconds() / 3600
        if hours_since < self.config.rebalance_interval_hours:
            return False
        
        # Check if Sharpe ratios differ significantly
        sharpes = {s: self.calculate_strategy_sharpe(s) for s in self.performance}
        if not sharpes:
            return False
        
        avg_sharpe = sum(sharpes.values()) / len(sharpes)
        if avg_sharpe == 0:
            return False
        
        for sharpe in sharpes.values():
            if abs(sharpe - avg_sharpe) / abs(avg_sharpe) > self.config.rebalance_threshold:
                return True
        
        return False
    
    def rebalance_allocations(self) -> Dict[str, float]:
        """Adjust allocations based on strategy performance."""
        sharpes = {s: self.calculate_strategy_sharpe(s) for s in self.performance}
        if not sharpes:
            return self.allocations
        
        avg_sharpe = sum(sharpes.values()) / len(sharpes)
        if avg_sharpe == 0:
            return self.allocations
        
        new_allocations = self.allocations.copy()
        
        for strategy, sharpe in sharpes.items():
            if strategy == 'reserve':
                continue
            
            current = new_allocations.get(strategy, 0)
            
            if sharpe > avg_sharpe * 1.5:  # Outperforming
                new_alloc = min(current + self.config.rebalance_amount,
                               self.config.max_allocation)
                new_allocations[strategy] = new_alloc
            elif sharpe < avg_sharpe * 0.5:  # Underperforming
                new_alloc = max(current - self.config.rebalance_amount,
                               self.config.min_allocation)
                new_allocations[strategy] = new_alloc
        
        # Normalize to ensure sum = 1.0
        total = sum(new_allocations.values())
        if total > 0:
            new_allocations = {k: v/total for k, v in new_allocations.items()}
        
        self.allocations = new_allocations
        self.last_rebalance = datetime.now()
        
        return self.allocations
    
    def get_performance_summary(self) -> Dict[str, dict]:
        """Get performance summary for all strategies."""
        return {s: p.to_dict() for s, p in self.performance.items()}
    
    def reduce_allocations(self, reduction_pct: float = 0.25) -> None:
        """Reduce all allocations (for risk events)."""
        reserve_increase = 0.0
        for strategy in self.allocations:
            if strategy != 'reserve':
                reduction = self.allocations[strategy] * reduction_pct
                self.allocations[strategy] -= reduction
                reserve_increase += reduction
        
        self.allocations['reserve'] = self.allocations.get('reserve', 0) + reserve_increase
