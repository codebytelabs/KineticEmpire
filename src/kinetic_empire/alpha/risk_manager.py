"""Unified Risk Manager - Portfolio-level risk controls.

Enforces VaR limits, drawdown protection, position limits, and emergency stops.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
import statistics

from .models import RFactorPosition


@dataclass
class RiskConfig:
    """Configuration for risk management."""
    max_daily_var: float = 0.03  # 3% daily VaR limit
    max_drawdown: float = 0.15  # 15% max drawdown
    max_position_pct: float = 0.10  # 10% max single position
    max_strategy_correlation: float = 0.7
    daily_loss_limit: float = 0.05  # 5% daily loss triggers emergency
    cooldown_hours: int = 24


class UnifiedRiskManager:
    """Portfolio-level risk management."""
    
    def __init__(self, config: Optional[RiskConfig] = None):
        self.config = config or RiskConfig()
        self.peak_equity = 0.0
        self.daily_pnl = 0.0
        self.daily_start_equity = 0.0
        self.emergency_mode = False
        self.cooldown_until: Optional[datetime] = None
        self.last_reset = datetime.now()
    
    def reset_daily(self, current_equity: float) -> None:
        """Reset daily tracking."""
        self.daily_pnl = 0.0
        self.daily_start_equity = current_equity
        self.last_reset = datetime.now()
    
    def update_pnl(self, pnl: float) -> None:
        """Update daily P&L."""
        self.daily_pnl += pnl
    
    def calculate_drawdown(self, current_equity: float) -> float:
        """Calculate current drawdown from peak."""
        self.peak_equity = max(self.peak_equity, current_equity)
        if self.peak_equity == 0:
            return 0.0
        return (self.peak_equity - current_equity) / self.peak_equity
    
    def calculate_var(self, positions: List[RFactorPosition], 
                     confidence: float = 0.95) -> float:
        """Calculate simplified Value at Risk.
        
        Uses position R-values as risk measure.
        """
        if not positions:
            return 0.0
        
        total_risk = sum(p.r_value * p.position_size for p in positions)
        return total_risk

    
    def check_position_size(self, position_value: float, portfolio_value: float) -> bool:
        """Check if position size is within limits."""
        if portfolio_value == 0:
            return False
        return position_value / portfolio_value <= self.config.max_position_pct
    
    def check_var_limit(self, var: float, portfolio_value: float) -> bool:
        """Check if VaR is within daily limit."""
        if portfolio_value == 0:
            return False
        return var / portfolio_value <= self.config.max_daily_var
    
    def check_drawdown_limit(self, current_equity: float) -> bool:
        """Check if drawdown is within limit."""
        dd = self.calculate_drawdown(current_equity)
        if dd >= self.config.max_drawdown:
            self.enter_emergency_mode()
            return False
        return True
    
    def check_daily_loss(self, portfolio_value: float) -> bool:
        """Check if daily loss limit is breached."""
        if portfolio_value == 0:
            return False
        
        loss_pct = abs(self.daily_pnl) / portfolio_value if self.daily_pnl < 0 else 0
        if loss_pct >= self.config.daily_loss_limit:
            self.enter_emergency_mode()
            return False
        return True
    
    def enter_emergency_mode(self) -> None:
        """Enter emergency mode."""
        self.emergency_mode = True
        self.cooldown_until = datetime.now() + timedelta(hours=self.config.cooldown_hours)
    
    def exit_emergency_mode(self) -> None:
        """Exit emergency mode."""
        self.emergency_mode = False
        self.cooldown_until = None
    
    def can_trade(self) -> bool:
        """Check if trading is allowed."""
        if not self.emergency_mode:
            return True
        
        if self.cooldown_until and datetime.now() > self.cooldown_until:
            self.exit_emergency_mode()
            return True
        
        return False
    
    def validate_trade(self, position_value: float, portfolio_value: float,
                      current_var: float) -> Tuple[bool, str]:
        """Validate a trade against all risk rules.
        
        Returns:
            Tuple of (is_valid, reason)
        """
        if not self.can_trade():
            return False, "Emergency mode active"
        
        if not self.check_position_size(position_value, portfolio_value):
            return False, f"Position size {position_value/portfolio_value:.1%} exceeds limit {self.config.max_position_pct:.1%}"
        
        if not self.check_var_limit(current_var + position_value * 0.02, portfolio_value):
            return False, "VaR limit exceeded"
        
        if not self.check_daily_loss(portfolio_value):
            return False, "Daily loss limit exceeded"
        
        return True, "OK"
    
    def get_status(self) -> dict:
        """Get current risk status."""
        return {
            "emergency_mode": self.emergency_mode,
            "daily_pnl": self.daily_pnl,
            "peak_equity": self.peak_equity,
            "cooldown_until": self.cooldown_until.isoformat() if self.cooldown_until else None,
            "can_trade": self.can_trade(),
        }
