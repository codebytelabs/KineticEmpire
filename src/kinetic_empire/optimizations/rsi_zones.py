"""RSI Zone Optimizer.

Implements regime-specific RSI entry zones for better entry quality.
"""

from dataclasses import dataclass
from typing import Optional, Tuple

from kinetic_empire.models import Regime
from .config import RSIZoneConfig


class RSIZoneOptimizer:
    """Optimizes RSI entry zones by market regime.
    
    RSI zones by regime:
    - BULL: 35-70 (wider range, catch pullbacks)
    - BEAR: 45-60 (conservative, avoid catching falling knives)
    """
    
    def __init__(self, config: Optional[RSIZoneConfig] = None):
        """Initialize RSI zone optimizer.
        
        Args:
            config: RSI zone configuration. Uses defaults if None.
        """
        self.config = config or RSIZoneConfig()
    
    def get_rsi_bounds(self, regime: Regime) -> Tuple[float, float]:
        """Get RSI bounds for regime.
        
        Args:
            regime: Current market regime
            
        Returns:
            Tuple of (min_rsi, max_rsi)
        """
        if regime == Regime.BULL:
            return (self.config.bull_min, self.config.bull_max)
        else:  # BEAR
            return (self.config.bear_min, self.config.bear_max)
    
    def is_valid_rsi(self, rsi: float, regime: Regime) -> bool:
        """Check if RSI is in valid entry zone for regime.
        
        Args:
            rsi: Current RSI value
            regime: Current market regime
            
        Returns:
            True if RSI is within acceptable range
        """
        min_rsi, max_rsi = self.get_rsi_bounds(regime)
        return min_rsi <= rsi <= max_rsi
    
    def get_rsi_quality(self, rsi: float, regime: Regime) -> float:
        """Get RSI quality score (0-1) based on position in zone.
        
        Higher score for RSI closer to optimal pullback level.
        
        Args:
            rsi: Current RSI value
            regime: Current market regime
            
        Returns:
            Quality score from 0.0 to 1.0
        """
        min_rsi, max_rsi = self.get_rsi_bounds(regime)
        
        if not self.is_valid_rsi(rsi, regime):
            return 0.0
        
        # Optimal RSI is in the lower half of the range (pullback)
        mid_point = (min_rsi + max_rsi) / 2
        
        if rsi <= mid_point:
            # Lower RSI = better pullback entry
            return 1.0 - ((rsi - min_rsi) / (mid_point - min_rsi)) * 0.5
        else:
            # Higher RSI = less ideal but still valid
            return 0.5 - ((rsi - mid_point) / (max_rsi - mid_point)) * 0.5
    
    def get_rejection_reason(self, rsi: float, regime: Regime) -> Optional[str]:
        """Get reason for RSI rejection if invalid.
        
        Args:
            rsi: Current RSI value
            regime: Current market regime
            
        Returns:
            Rejection reason string, or None if valid
        """
        min_rsi, max_rsi = self.get_rsi_bounds(regime)
        
        if rsi < min_rsi:
            return f"RSI {rsi:.1f} below {regime.value} minimum {min_rsi}"
        elif rsi > max_rsi:
            return f"RSI {rsi:.1f} above {regime.value} maximum {max_rsi}"
        
        return None
