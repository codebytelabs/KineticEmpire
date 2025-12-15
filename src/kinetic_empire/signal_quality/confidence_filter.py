"""Confidence Filter for Signal Quality Gate.

Filters signals based on Enhanced TA confidence thresholds.
"""

import logging
from typing import Tuple

from .config import QualityGateConfig
from .models import ConfidenceTier


logger = logging.getLogger(__name__)


class ConfidenceFilter:
    """Filters signals based on confidence score thresholds.
    
    Three-tier logic:
    - Below min_confidence (50): Rejected
    - Between min and medium (50-70): Medium tier, 0.5x position size
    - Above medium (70+): High tier, full position size
    """
    
    def __init__(self, config: QualityGateConfig):
        """Initialize with configuration.
        
        Args:
            config: Quality gate configuration
        """
        self.config = config
    
    def filter(self, confidence: int) -> Tuple[bool, ConfidenceTier, float]:
        """Filter signal based on confidence score.
        
        Args:
            confidence: Enhanced TA confidence score (0-100)
            
        Returns:
            Tuple of (passed, tier, size_multiplier):
            - passed: Whether signal passes confidence filter
            - tier: Confidence tier classification
            - size_multiplier: Position size multiplier (0.5 or 1.0)
        """
        if confidence < self.config.min_confidence:
            logger.debug(f"Confidence {confidence} below minimum {self.config.min_confidence}")
            return (False, ConfidenceTier.LOW, 0.0)
        
        if confidence < self.config.medium_confidence:
            logger.debug(f"Confidence {confidence} in medium tier (50-70), using 0.5x size")
            return (True, ConfidenceTier.MEDIUM, 0.5)
        
        logger.debug(f"Confidence {confidence} in high tier (70+), using full size")
        return (True, ConfidenceTier.HIGH, 1.0)
