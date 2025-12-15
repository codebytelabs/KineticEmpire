"""Fear & Greed Index Adjuster.

Adjusts position sizing and trailing stops based on market sentiment extremes.
"""

from typing import Optional

from .config import FearGreedConfig


class FearGreedAdjuster:
    """Adjusts trading parameters based on Fear & Greed Index.
    
    Adjustments at sentiment extremes:
    - Extreme Fear (< 25): Reduce position sizes by 30%
    - Extreme Greed (> 75): Tighten trailing stops to 1.0x ATR
    - Normal (25-75): No adjustment
    
    Gracefully handles unavailable F&G data (returns standard params).
    """
    
    def __init__(self, config: Optional[FearGreedConfig] = None):
        """Initialize Fear & Greed adjuster.
        
        Args:
            config: F&G configuration. Uses defaults if None.
        """
        self.config = config or FearGreedConfig()
    
    def should_adjust(self, fg_index: Optional[int]) -> bool:
        """Check if F&G index warrants adjustment.
        
        Args:
            fg_index: Fear & Greed index (0-100), or None if unavailable
            
        Returns:
            True if at sentiment extreme
        """
        if fg_index is None:
            return False
        
        return (
            fg_index < self.config.extreme_fear_threshold or
            fg_index > self.config.extreme_greed_threshold
        )
    
    def is_extreme_fear(self, fg_index: Optional[int]) -> bool:
        """Check if in extreme fear zone.
        
        Args:
            fg_index: Fear & Greed index
            
        Returns:
            True if F&G < 25
        """
        if fg_index is None:
            return False
        return fg_index < self.config.extreme_fear_threshold
    
    def is_extreme_greed(self, fg_index: Optional[int]) -> bool:
        """Check if in extreme greed zone.
        
        Args:
            fg_index: Fear & Greed index
            
        Returns:
            True if F&G > 75
        """
        if fg_index is None:
            return False
        return fg_index > self.config.extreme_greed_threshold
    
    def get_size_multiplier(self, fg_index: Optional[int]) -> float:
        """Get position size multiplier based on F&G.
        
        Args:
            fg_index: Fear & Greed index (0-100), or None
            
        Returns:
            Size multiplier (0.7 for extreme fear, 1.0 otherwise)
        """
        if fg_index is None:
            return 1.0
        
        if self.is_extreme_fear(fg_index):
            return self.config.fear_size_multiplier
        
        return 1.0
    
    def get_trail_multiplier(
        self,
        fg_index: Optional[int],
        base_mult: float = 1.5
    ) -> float:
        """Get trailing stop ATR multiplier based on F&G.
        
        Args:
            fg_index: Fear & Greed index (0-100), or None
            base_mult: Base ATR multiplier
            
        Returns:
            Adjusted ATR multiplier (1.0 for extreme greed, base otherwise)
        """
        if fg_index is None:
            return base_mult
        
        if self.is_extreme_greed(fg_index):
            return self.config.greed_trail_multiplier
        
        return base_mult
    
    def adjust_position_size(
        self,
        base_size: float,
        fg_index: Optional[int]
    ) -> float:
        """Adjust position size based on F&G.
        
        Args:
            base_size: Base position size
            fg_index: Fear & Greed index
            
        Returns:
            Adjusted position size
        """
        multiplier = self.get_size_multiplier(fg_index)
        return base_size * multiplier
    
    def get_sentiment_label(self, fg_index: Optional[int]) -> str:
        """Get human-readable sentiment label.
        
        Args:
            fg_index: Fear & Greed index
            
        Returns:
            Sentiment label string
        """
        if fg_index is None:
            return "unknown"
        
        if self.is_extreme_fear(fg_index):
            return "extreme_fear"
        elif self.is_extreme_greed(fg_index):
            return "extreme_greed"
        elif fg_index < 40:
            return "fear"
        elif fg_index > 60:
            return "greed"
        else:
            return "neutral"
