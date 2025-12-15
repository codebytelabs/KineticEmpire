"""Circuit breaker module for daily loss protection.

Halts trading when daily losses exceed configured limits
to prevent catastrophic drawdowns.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    daily_loss_limit_pct: float = 2.0  # 2% daily loss triggers halt


class CircuitBreaker:
    """Halts trading when daily losses exceed limits.
    
    From Requirements 3.1-3.4:
    - 2% daily loss triggers circuit breaker
    - New entries blocked when triggered
    - Exits still allowed
    - Resets at start of new trading day
    """

    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        """Initialize circuit breaker.
        
        Args:
            config: Circuit breaker configuration
        """
        self.config = config or CircuitBreakerConfig()
        self.is_triggered: bool = False
        self.trigger_time: Optional[datetime] = None
        self.trigger_loss_pct: Optional[float] = None
        self._last_reset_date: Optional[datetime] = None

    def check_and_trigger(self, daily_pnl: float, portfolio_value: float) -> bool:
        """Check if circuit breaker should trigger.
        
        Args:
            daily_pnl: Daily P&L (negative for losses)
            portfolio_value: Total portfolio value
            
        Returns:
            True if circuit breaker was triggered
            
        Validates: Requirement 3.1
        """
        if portfolio_value <= 0:
            return False
            
        loss_pct = abs(daily_pnl / portfolio_value) * 100 if daily_pnl < 0 else 0
        
        if loss_pct >= self.config.daily_loss_limit_pct:
            self.is_triggered = True
            self.trigger_time = datetime.now(timezone.utc)
            self.trigger_loss_pct = loss_pct
            return True
        
        return False

    def reset_for_new_day(self) -> None:
        """Reset circuit breaker for new trading day.
        
        Validates: Requirement 3.3
        """
        self.is_triggered = False
        self.trigger_time = None
        self.trigger_loss_pct = None
        self._last_reset_date = datetime.now(timezone.utc).date()

    def can_enter_new_trade(self) -> bool:
        """Check if new trade entries are allowed.
        
        Returns:
            False if circuit breaker is triggered
            
        Validates: Requirement 3.4
        """
        return not self.is_triggered

    def can_exit_position(self) -> bool:
        """Check if position exits are allowed.
        
        Returns:
            Always True - exits allowed even when triggered
            
        Validates: Requirement 3.4
        """
        return True

    def get_status(self) -> dict:
        """Get current circuit breaker status.
        
        Returns:
            Dictionary with status information
        """
        return {
            "is_triggered": self.is_triggered,
            "trigger_time": self.trigger_time.isoformat() if self.trigger_time else None,
            "trigger_loss_pct": self.trigger_loss_pct,
            "daily_loss_limit_pct": self.config.daily_loss_limit_pct,
            "can_enter": self.can_enter_new_trade(),
            "can_exit": self.can_exit_position(),
        }
