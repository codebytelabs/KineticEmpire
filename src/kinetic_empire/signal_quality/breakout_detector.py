"""Breakout Detector for Signal Quality Gate.

Detects volume surges and price breakouts.
"""

import logging

from .config import QualityGateConfig
from .models import BreakoutResult


logger = logging.getLogger(__name__)


class BreakoutDetector:
    """Detects volume surges and price breakouts.
    
    Volume surge: Current volume > 200% of 20-period average
    Breakout: Price breaks above resistance with volume surge
    """
    
    def __init__(self, config: QualityGateConfig):
        """Initialize with configuration.
        
        Args:
            config: Quality gate configuration
        """
        self.config = config
    
    def detect(
        self,
        current_price: float,
        resistance_level: float,
        volume_ratio: float,
        direction: str = "LONG",
    ) -> BreakoutResult:
        """Detect volume surges and breakouts.
        
        Args:
            current_price: Current price
            resistance_level: Nearest resistance level
            volume_ratio: Current volume / 20-period average volume
            direction: Signal direction ("LONG" or "SHORT")
            
        Returns:
            BreakoutResult with detection flags and bonus
        """
        direction = direction.upper()
        
        # Check for volume surge (>200% of average)
        is_volume_surge = volume_ratio >= self.config.volume_surge_threshold
        
        # Check for breakout
        if direction == "LONG":
            # Bullish breakout: price above resistance with volume
            is_breakout = current_price > resistance_level and is_volume_surge
        else:
            # For SHORT, we'd check support breakdown
            # But typically breakout bonus applies to bullish breakouts
            is_breakout = False
        
        # Calculate bonus
        breakout_bonus = self.config.breakout_bonus if is_breakout else 0
        
        # Use tight trailing for breakout trades
        use_tight_trailing = is_breakout
        
        if is_volume_surge:
            logger.debug(f"Volume surge detected: {volume_ratio:.1f}x average")
        
        if is_breakout:
            logger.info(
                f"Breakout detected: price {current_price} > resistance {resistance_level} "
                f"with {volume_ratio:.1f}x volume"
            )
        
        return BreakoutResult(
            is_volume_surge=is_volume_surge,
            is_breakout=is_breakout,
            breakout_bonus=breakout_bonus,
            use_tight_trailing=use_tight_trailing,
        )
    
    def detect_support_breakdown(
        self,
        current_price: float,
        support_level: float,
        volume_ratio: float,
    ) -> BreakoutResult:
        """Detect support breakdown for SHORT signals.
        
        Args:
            current_price: Current price
            support_level: Nearest support level
            volume_ratio: Current volume / 20-period average volume
            
        Returns:
            BreakoutResult with detection flags and bonus
        """
        # Check for volume surge
        is_volume_surge = volume_ratio >= self.config.volume_surge_threshold
        
        # Check for breakdown (price below support with volume)
        is_breakdown = current_price < support_level and is_volume_surge
        
        # Calculate bonus
        breakout_bonus = self.config.breakout_bonus if is_breakdown else 0
        
        # Use tight trailing for breakdown trades
        use_tight_trailing = is_breakdown
        
        if is_breakdown:
            logger.info(
                f"Support breakdown detected: price {current_price} < support {support_level} "
                f"with {volume_ratio:.1f}x volume"
            )
        
        return BreakoutResult(
            is_volume_surge=is_volume_surge,
            is_breakout=is_breakdown,
            breakout_bonus=breakout_bonus,
            use_tight_trailing=use_tight_trailing,
        )
