"""Global Risk Monitor for Unified Trading System.

Monitors portfolio-wide risk limits including daily loss limits
and maximum drawdown protection.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable
import logging

from .config import UnifiedConfig

logger = logging.getLogger(__name__)


@dataclass
class RiskState:
    """Current risk state for the portfolio."""
    daily_pnl: float = 0.0
    daily_pnl_pct: float = 0.0
    peak_portfolio_value: float = 0.0
    current_drawdown_pct: float = 0.0
    circuit_breaker_active: bool = False
    circuit_breaker_reason: Optional[str] = None
    circuit_breaker_until: Optional[datetime] = None


class GlobalRiskMonitor:
    """Monitors portfolio-wide risk limits.
    
    Tracks combined daily P&L across all engines and triggers
    circuit breakers when limits are exceeded.
    """
    
    def __init__(self, config: UnifiedConfig):
        """Initialize risk monitor.
        
        Args:
            config: Unified configuration with risk limits.
        """
        self.config = config
        self._engine_pnl: Dict[str, float] = {}
        self._starting_portfolio_value: float = 0.0
        self._peak_portfolio_value: float = 0.0
        self._circuit_breaker_active: bool = False
        self._circuit_breaker_until: Optional[datetime] = None
        self._circuit_breaker_reason: Optional[str] = None
        self._last_reset_date: Optional[datetime] = None
        self._on_circuit_breaker: Optional[Callable[[str], None]] = None
    
    def set_starting_value(self, portfolio_value: float) -> None:
        """Set starting portfolio value for daily P&L calculation.
        
        Args:
            portfolio_value: Starting portfolio value in USD.
        """
        self._starting_portfolio_value = portfolio_value
        self._peak_portfolio_value = max(self._peak_portfolio_value, portfolio_value)
        self._last_reset_date = datetime.now().date()
    
    def update_pnl(self, engine_name: str, pnl: float) -> None:
        """Update P&L from an engine.
        
        Args:
            engine_name: Name of the engine.
            pnl: Current unrealized P&L in USD.
        """
        self._engine_pnl[engine_name] = pnl
    
    def get_combined_pnl(self) -> float:
        """Get combined P&L across all engines.
        
        Returns:
            Total P&L in USD.
        """
        return sum(self._engine_pnl.values())
    
    def get_daily_pnl_pct(self) -> float:
        """Get daily P&L as percentage of starting value.
        
        Returns:
            Daily P&L percentage.
        """
        if self._starting_portfolio_value <= 0:
            return 0.0
        return (self.get_combined_pnl() / self._starting_portfolio_value) * 100
    
    def check_daily_loss_limit(self, current_portfolio_value: float) -> bool:
        """Check if daily loss limit is exceeded.
        
        Args:
            current_portfolio_value: Current portfolio value in USD.
            
        Returns:
            True if daily loss limit is exceeded.
        """
        if self._starting_portfolio_value <= 0:
            return False
        
        daily_pnl_pct = self.get_daily_pnl_pct()
        return daily_pnl_pct <= -self.config.global_daily_loss_limit_pct
    
    def check_drawdown_limit(self, current_portfolio_value: float) -> bool:
        """Check if max drawdown limit is exceeded.
        
        Args:
            current_portfolio_value: Current portfolio value in USD.
            
        Returns:
            True if max drawdown is exceeded.
        """
        # Update peak
        self._peak_portfolio_value = max(self._peak_portfolio_value, current_portfolio_value)
        
        if self._peak_portfolio_value <= 0:
            return False
        
        drawdown_pct = ((self._peak_portfolio_value - current_portfolio_value) 
                        / self._peak_portfolio_value) * 100
        return drawdown_pct >= self.config.global_max_drawdown_pct
    
    def get_current_drawdown_pct(self, current_portfolio_value: float) -> float:
        """Get current drawdown percentage.
        
        Args:
            current_portfolio_value: Current portfolio value in USD.
            
        Returns:
            Current drawdown percentage.
        """
        if self._peak_portfolio_value <= 0:
            return 0.0
        return ((self._peak_portfolio_value - current_portfolio_value) 
                / self._peak_portfolio_value) * 100
    
    def can_open_new_trade(self) -> bool:
        """Check if new trades are allowed.
        
        Returns:
            True if new trades are allowed.
        """
        if not self._circuit_breaker_active:
            return True
        
        # Check if cooldown has expired
        if self._circuit_breaker_until and datetime.now() >= self._circuit_breaker_until:
            self._circuit_breaker_active = False
            self._circuit_breaker_reason = None
            self._circuit_breaker_until = None
            logger.info("Circuit breaker cooldown expired, trading resumed")
            return True
        
        return False
    
    def trigger_circuit_breaker(self, reason: str) -> None:
        """Activate circuit breaker.
        
        Args:
            reason: Reason for triggering circuit breaker.
        """
        self._circuit_breaker_active = True
        self._circuit_breaker_reason = reason
        self._circuit_breaker_until = (
            datetime.now() + 
            timedelta(minutes=self.config.global_circuit_breaker_cooldown_minutes)
        )
        
        logger.warning(
            f"🚨 CIRCUIT BREAKER TRIGGERED: {reason} | "
            f"Trading halted until {self._circuit_breaker_until}"
        )
        
        if self._on_circuit_breaker:
            self._on_circuit_breaker(reason)
    
    def check_and_trigger(self, current_portfolio_value: float) -> Optional[str]:
        """Check all risk limits and trigger circuit breaker if needed.
        
        Args:
            current_portfolio_value: Current portfolio value in USD.
            
        Returns:
            Reason for circuit breaker if triggered, None otherwise.
        """
        # Reset daily P&L at start of new day
        today = datetime.now().date()
        if self._last_reset_date and today > self._last_reset_date:
            self._engine_pnl.clear()
            self._starting_portfolio_value = current_portfolio_value
            self._last_reset_date = today
            logger.info(f"Daily P&L reset. New starting value: ${current_portfolio_value:.2f}")
        
        # Check daily loss limit
        if self.check_daily_loss_limit(current_portfolio_value):
            reason = f"Daily loss limit exceeded ({self.get_daily_pnl_pct():.2f}%)"
            self.trigger_circuit_breaker(reason)
            return reason
        
        # Check drawdown limit
        if self.check_drawdown_limit(current_portfolio_value):
            drawdown = self.get_current_drawdown_pct(current_portfolio_value)
            reason = f"Max drawdown exceeded ({drawdown:.2f}%)"
            self.trigger_circuit_breaker(reason)
            return reason
        
        return None
    
    def get_state(self) -> RiskState:
        """Get current risk state.
        
        Returns:
            Current RiskState.
        """
        return RiskState(
            daily_pnl=self.get_combined_pnl(),
            daily_pnl_pct=self.get_daily_pnl_pct(),
            peak_portfolio_value=self._peak_portfolio_value,
            current_drawdown_pct=0.0,  # Needs current value to calculate
            circuit_breaker_active=self._circuit_breaker_active,
            circuit_breaker_reason=self._circuit_breaker_reason,
            circuit_breaker_until=self._circuit_breaker_until,
        )
    
    def set_circuit_breaker_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for circuit breaker events.
        
        Args:
            callback: Function to call when circuit breaker triggers.
        """
        self._on_circuit_breaker = callback
