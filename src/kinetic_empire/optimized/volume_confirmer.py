"""Optimized volume confirmation with enhanced requirements."""

from .models import VolumeResult
from .config import OptimizedConfig, DEFAULT_CONFIG


class OptimizedVolumeConfirmer:
    """Confirms entries with enhanced volume requirements."""
    
    def __init__(self, config: OptimizedConfig = DEFAULT_CONFIG):
        self.config = config
    
    def confirm_volume(
        self,
        current_volume: float,
        average_volume: float
    ) -> VolumeResult:
        """Confirm volume for entry.
        
        Args:
            current_volume: Current period volume
            average_volume: Average volume over lookback period
            
        Returns:
            VolumeResult with confirmation status and adjustments
        """
        if current_volume < 0 or average_volume <= 0:
            raise ValueError("volumes must be positive")
        
        volume_ratio = current_volume / average_volume
        
        confidence_bonus = 0
        position_size_multiplier = 1.0
        is_spike = False
        
        # Check for volume spike
        if volume_ratio >= self.config.VOLUME_SPIKE_MULTIPLIER:
            is_spike = True
            confidence_bonus = self.config.VOLUME_SPIKE_BONUS
            confirmed = True
        elif volume_ratio >= self.config.VOLUME_REQUIRED_MULTIPLIER:
            confirmed = True
        else:
            # Low volume - reduce position size
            confirmed = False
            position_size_multiplier = 1.0 - self.config.VOLUME_LOW_REDUCTION
        
        return VolumeResult(
            confirmed=confirmed,
            position_size_multiplier=position_size_multiplier,
            confidence_bonus=confidence_bonus,
            is_spike=is_spike
        )
