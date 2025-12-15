"""Optimized portfolio risk guard with tighter limits."""

from typing import Dict, Optional
from datetime import datetime, timedelta
from .models import RiskCheckResult
from .config import OptimizedConfig, DEFAULT_CONFIG


class OptimizedPortfolioRiskGuard:
    """Enforces portfolio-level risk limits."""
    
    def __init__(self, config: OptimizedConfig = DEFAULT_CONFIG):
        self.config = config
        self._pause_until: Optional[datetime] = None
        self._weekly_loss_active: bool = False
    
    def is_paused(self) -> bool:
        """Check if trading is paused due to daily loss limit."""
        if self._pause_until is None:
            return False
        return datetime.now() < self._pause_until
    
    def set_pause(self, hours: int = 24):
        """Pause trading for specified hours."""
        self._pause_until = datetime.now() + timedelta(hours=hours)
    
    def clear_pause(self):
        """Clear trading pause."""
        self._pause_until = None
    
    def set_weekly_loss_active(self, active: bool):
        """Set weekly loss reduction status."""
        self._weekly_loss_active = active
    
    def can_open_position(
        self,
        current_positions: int,
        margin_usage: float,
        daily_loss: float,
        weekly_loss: float = 0.0,
        correlation_matrix: Optional[Dict[str, Dict[str, float]]] = None,
        new_symbol: Optional[str] = None
    ) -> RiskCheckResult:
        """Check if new position can be opened.
        
        Args:
            current_positions: Number of currently open positions
            margin_usage: Current margin usage as decimal (e.g., 0.5 for 50%)
            daily_loss: Daily loss as decimal (e.g., 0.03 for 3%)
            weekly_loss: Weekly loss as decimal
            correlation_matrix: Dict of symbol -> {symbol: correlation}
            new_symbol: Symbol of the new position to check correlation
            
        Returns:
            RiskCheckResult with decision and any adjustments
        """
        position_size_multiplier = 1.0
        
        # Check if trading is paused
        if self.is_paused():
            return RiskCheckResult(
                can_open=False,
                reason="Trading paused due to daily loss limit",
                position_size_multiplier=0.0,
                is_paused=True
            )
        
        # Check daily loss limit
        if daily_loss >= self.config.DAILY_LOSS_LIMIT:
            self.set_pause(24)
            return RiskCheckResult(
                can_open=False,
                reason=f"Daily loss {daily_loss:.1%} exceeds limit {self.config.DAILY_LOSS_LIMIT:.1%}",
                position_size_multiplier=0.0,
                is_paused=True
            )
        
        # Check weekly loss - apply reduction
        if weekly_loss >= self.config.WEEKLY_LOSS_LIMIT:
            self._weekly_loss_active = True
            position_size_multiplier *= self.config.WEEKLY_LOSS_REDUCTION
        
        # Check position limit
        if current_positions >= self.config.MAX_POSITIONS:
            return RiskCheckResult(
                can_open=False,
                reason=f"Position limit {self.config.MAX_POSITIONS} reached",
                position_size_multiplier=position_size_multiplier
            )
        
        # Check margin limit
        if margin_usage >= self.config.MAX_MARGIN_USAGE:
            return RiskCheckResult(
                can_open=False,
                reason=f"Margin usage {margin_usage:.1%} exceeds limit {self.config.MAX_MARGIN_USAGE:.1%}",
                position_size_multiplier=position_size_multiplier
            )
        
        # Check correlation limit
        if correlation_matrix and new_symbol:
            correlated_count = self._count_correlated_positions(
                correlation_matrix, new_symbol
            )
            if correlated_count >= self.config.MAX_CORRELATED_POSITIONS:
                return RiskCheckResult(
                    can_open=False,
                    reason=f"Correlated position limit {self.config.MAX_CORRELATED_POSITIONS} reached",
                    position_size_multiplier=position_size_multiplier
                )
        
        return RiskCheckResult(
            can_open=True,
            reason=None,
            position_size_multiplier=position_size_multiplier
        )
    
    def _count_correlated_positions(
        self,
        correlation_matrix: Dict[str, Dict[str, float]],
        new_symbol: str
    ) -> int:
        """Count positions highly correlated with new symbol."""
        if new_symbol not in correlation_matrix:
            return 0
        
        correlations = correlation_matrix[new_symbol]
        count = sum(
            1 for corr in correlations.values()
            if abs(corr) > self.config.MAX_CORRELATION
        )
        return count
