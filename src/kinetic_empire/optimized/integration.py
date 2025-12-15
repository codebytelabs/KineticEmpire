"""Integration module for optimized parameters.

Provides drop-in replacements for existing components with optimized parameters.
"""

from typing import Optional, Dict, Any
from .models import MarketRegime
from .config import OptimizedConfig, DEFAULT_CONFIG
from .atr_stop import OptimizedATRStopCalculator
from .leverage import OptimizedLeverageCalculator
from .position_sizer import OptimizedPositionSizer
from .trailing_stop import OptimizedTrailingStop
from .rsi_filter import OptimizedRSIFilter
from .adx_filter import OptimizedADXFilter
from .volume_confirmer import OptimizedVolumeConfirmer
from .portfolio_risk import OptimizedPortfolioRiskGuard
from .parameter_adjuster import ParameterAdjuster


class OptimizedTradingSystem:
    """Unified interface for all optimized trading components.
    
    This class provides a single entry point for using all optimized
    parameters in the trading system.
    """
    
    def __init__(self, config: OptimizedConfig = DEFAULT_CONFIG):
        self.config = config
        self.adjuster = ParameterAdjuster(config)
        
        # Individual components (accessible for direct use)
        self.atr_stop = self.adjuster.atr_calculator
        self.leverage = self.adjuster.leverage_calculator
        self.position_sizer = self.adjuster.position_sizer
        self.trailing_stop = self.adjuster.trailing_stop
        self.rsi_filter = self.adjuster.rsi_filter
        self.adx_filter = self.adjuster.adx_filter
        self.volume_confirmer = self.adjuster.volume_confirmer
        self.portfolio_guard = self.adjuster.portfolio_guard
        
        # State tracking
        self._current_regime = MarketRegime.TRENDING
        self._regime_confidence = 1.0
    
    def set_regime(self, regime: MarketRegime, confidence: float = 1.0):
        """Update current market regime."""
        self._current_regime = regime
        self._regime_confidence = confidence
    
    def get_regime(self) -> MarketRegime:
        """Get current market regime."""
        return self._current_regime
    
    def evaluate_entry(
        self,
        rsi: float,
        adx: float,
        current_volume: float,
        average_volume: float,
        direction: str,
        has_rsi_divergence: bool = False
    ) -> Dict[str, Any]:
        """Evaluate entry conditions using all filters.
        
        Returns:
            Dict with:
            - valid: bool - whether entry is valid
            - confidence_bonus: int - total confidence bonus
            - position_multiplier: float - position size multiplier
            - reasons: list - reasons for rejection if invalid
        """
        reasons = []
        confidence_bonus = 0
        position_multiplier = 1.0
        
        # RSI filter
        rsi_result = self.rsi_filter.evaluate_entry(rsi, direction, has_rsi_divergence)
        if not rsi_result.signal_valid:
            if not rsi_result.requires_confirmation:
                reasons.append(rsi_result.reason)
            else:
                reasons.append(f"RSI requires confirmation: {rsi_result.reason}")
        confidence_bonus += rsi_result.confidence_bonus
        
        # ADX filter
        adx_result = self.adx_filter.evaluate_trend(adx)
        if not adx_result.is_trending:
            reasons.append(f"ADX {adx:.1f} indicates non-trending market")
        confidence_bonus += adx_result.confidence_bonus
        position_multiplier *= adx_result.position_size_multiplier
        
        # Volume confirmation
        volume_result = self.volume_confirmer.confirm_volume(current_volume, average_volume)
        if not volume_result.confirmed:
            reasons.append(f"Volume {current_volume/average_volume:.2f}x below 1.5x threshold")
        confidence_bonus += volume_result.confidence_bonus
        position_multiplier *= volume_result.position_size_multiplier
        
        # Entry is valid if RSI is valid (or requires confirmation) and volume is confirmed
        valid = rsi_result.signal_valid and volume_result.confirmed
        
        return {
            "valid": valid,
            "confidence_bonus": confidence_bonus,
            "position_multiplier": position_multiplier,
            "reasons": reasons,
            "rsi_result": rsi_result,
            "adx_result": adx_result,
            "volume_result": volume_result,
        }
    
    def calculate_position(
        self,
        capital: float,
        confidence: int,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        current_positions: int,
        margin_usage: float,
        daily_loss: float,
        weekly_loss: float = 0.0
    ) -> Dict[str, Any]:
        """Calculate position size with all risk checks.
        
        Returns:
            Dict with:
            - can_trade: bool
            - position_size: float
            - leverage: int
            - rejection_reason: str or None
        """
        # Portfolio risk check
        risk_result = self.portfolio_guard.can_open_position(
            current_positions=current_positions,
            margin_usage=margin_usage,
            daily_loss=daily_loss,
            weekly_loss=weekly_loss
        )
        
        if not risk_result.can_open:
            return {
                "can_trade": False,
                "position_size": 0.0,
                "leverage": 0,
                "rejection_reason": risk_result.reason,
            }
        
        # Calculate position size
        position_size = self.position_sizer.calculate_position_size(
            capital=capital,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss
        )
        
        # Apply risk multiplier
        position_size *= risk_result.position_size_multiplier
        
        # Calculate leverage
        leverage = self.leverage.calculate_leverage(confidence, self._current_regime)
        
        return {
            "can_trade": True,
            "position_size": position_size,
            "leverage": leverage,
            "rejection_reason": None,
            "risk_multiplier": risk_result.position_size_multiplier,
        }
    
    def calculate_stop_loss(
        self,
        entry_price: float,
        atr: float,
        direction: str,
        position_size: float
    ) -> Dict[str, Any]:
        """Calculate stop loss with regime adaptation.
        
        Returns:
            Dict with stop price and any position adjustments
        """
        result = self.atr_stop.calculate_stop(
            entry_price=entry_price,
            atr=atr,
            direction=direction,
            regime=self._current_regime,
            position_size=position_size
        )
        
        return {
            "stop_price": result.stop_price,
            "multiplier": result.multiplier_used,
            "adjusted_size": result.adjusted_position_size,
            "max_loss_exceeded": result.max_loss_exceeded,
            "distance_pct": result.distance_percent,
        }
    
    def should_trail(self, profit_pct: float) -> bool:
        """Check if trailing stop should activate."""
        return self.trailing_stop.should_activate(profit_pct, self._current_regime)
    
    def update_trailing_stop(
        self,
        current_price: float,
        current_stop: float,
        direction: str,
        highest_price: float = None,
        lowest_price: float = None
    ) -> float:
        """Update trailing stop level."""
        return self.trailing_stop.update_stop(
            current_price=current_price,
            current_stop=current_stop,
            direction=direction,
            highest_price=highest_price,
            lowest_price=lowest_price
        )


# Singleton instance for easy access
_default_system: Optional[OptimizedTradingSystem] = None


def get_optimized_system(config: OptimizedConfig = DEFAULT_CONFIG) -> OptimizedTradingSystem:
    """Get or create the default optimized trading system."""
    global _default_system
    if _default_system is None:
        _default_system = OptimizedTradingSystem(config)
    return _default_system


def reset_optimized_system():
    """Reset the default system (useful for testing)."""
    global _default_system
    _default_system = None
