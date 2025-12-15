"""Volume-Tiered Position Sizer.

Adjusts position sizes based on volume confirmation strength.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .config import VolumeTierConfig


class VolumeTier(Enum):
    """Volume tier classification."""
    LOW = "low"        # < 1.0x average
    STANDARD = "standard"  # 1.0-1.5x average
    MEDIUM = "medium"  # 1.5-2.5x average
    HIGH = "high"      # > 2.5x average


class VolumeTieredSizer:
    """Adjusts position size based on volume confirmation.
    
    Volume tiers and multipliers:
    - LOW (< 1.0x): 0.8x position size (20% reduction)
    - STANDARD (1.0-1.5x): 1.0x position size
    - MEDIUM (1.5-2.5x): 1.1x position size (10% increase)
    - HIGH (> 2.5x): 1.2x position size (20% increase)
    """
    
    def __init__(self, config: Optional[VolumeTierConfig] = None):
        """Initialize volume-tiered sizer.
        
        Args:
            config: Volume tier configuration. Uses defaults if None.
        """
        self.config = config or VolumeTierConfig()
    
    def get_volume_tier(self, volume_ratio: float) -> VolumeTier:
        """Classify volume into tier.
        
        Args:
            volume_ratio: Current volume / average volume
            
        Returns:
            VolumeTier classification
        """
        if volume_ratio < self.config.low_threshold:
            return VolumeTier.LOW
        elif volume_ratio < self.config.medium_threshold:
            return VolumeTier.STANDARD
        elif volume_ratio < self.config.high_threshold:
            return VolumeTier.MEDIUM
        else:
            return VolumeTier.HIGH
    
    def get_volume_multiplier(self, volume_ratio: float) -> float:
        """Get position size multiplier based on volume ratio.
        
        Args:
            volume_ratio: Current volume / average volume
            
        Returns:
            Position size multiplier (0.8, 1.0, 1.1, or 1.2)
        """
        tier = self.get_volume_tier(volume_ratio)
        
        if tier == VolumeTier.LOW:
            return self.config.low_multiplier
        elif tier == VolumeTier.STANDARD:
            return self.config.standard_multiplier
        elif tier == VolumeTier.MEDIUM:
            return self.config.medium_multiplier
        else:  # HIGH
            return self.config.high_multiplier
    
    def adjust_position_size(
        self,
        base_size: float,
        volume_ratio: float
    ) -> float:
        """Adjust position size based on volume.
        
        Args:
            base_size: Base position size
            volume_ratio: Current volume / average volume
            
        Returns:
            Adjusted position size
        """
        multiplier = self.get_volume_multiplier(volume_ratio)
        return base_size * multiplier
    
    def calculate_volume_ratio(
        self,
        current_volume: float,
        average_volume: float
    ) -> float:
        """Calculate volume ratio.
        
        Args:
            current_volume: Current period volume
            average_volume: Average volume (e.g., 24h mean)
            
        Returns:
            Volume ratio (current / average)
        """
        if average_volume <= 0:
            return 1.0  # Default to standard if no average
        return current_volume / average_volume
