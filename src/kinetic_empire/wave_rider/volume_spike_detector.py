"""Volume Spike Detector for Wave Rider.

Detects and classifies volume spikes based on volume ratio thresholds:
- NONE: volume_ratio < 2.0
- NORMAL: 2.0 <= volume_ratio < 3.0
- STRONG: 3.0 <= volume_ratio < 5.0
- EXTREME: volume_ratio >= 5.0
"""

from typing import Tuple
from .models import SpikeClassification


class VolumeSpikeDetector:
    """Detects and classifies volume spikes.
    
    Volume spikes indicate significant market interest and are a key
    entry trigger for the Wave Rider system.
    """
    
    # Threshold constants per spec
    SPIKE_THRESHOLD = 2.0      # Normal spike
    STRONG_THRESHOLD = 3.0     # Strong spike
    EXTREME_THRESHOLD = 5.0    # Extreme spike
    
    def detect_spike(self, volume_ratio: float) -> Tuple[bool, SpikeClassification]:
        """Detect if volume ratio indicates a spike and classify it.
        
        Args:
            volume_ratio: Current volume / 20-period average volume
            
        Returns:
            Tuple of (has_spike, classification)
            - has_spike: True if volume_ratio >= 2.0
            - classification: SpikeClassification enum value
        """
        classification = self.classify(volume_ratio)
        has_spike = classification != SpikeClassification.NONE
        return has_spike, classification
    
    def classify(self, volume_ratio: float) -> SpikeClassification:
        """Classify volume ratio into spike category.
        
        Property 3: Volume Spike Classification
        - "extreme" if volume_ratio >= 5.0
        - "strong" if volume_ratio >= 3.0 and < 5.0
        - "normal" if volume_ratio >= 2.0 and < 3.0
        - "none" if volume_ratio < 2.0
        
        Args:
            volume_ratio: Current volume / 20-period average volume
            
        Returns:
            SpikeClassification enum value
        """
        if volume_ratio >= self.EXTREME_THRESHOLD:
            return SpikeClassification.EXTREME
        elif volume_ratio >= self.STRONG_THRESHOLD:
            return SpikeClassification.STRONG
        elif volume_ratio >= self.SPIKE_THRESHOLD:
            return SpikeClassification.NORMAL
        else:
            return SpikeClassification.NONE
    
    def get_spike_strength(self, volume_ratio: float) -> int:
        """Get spike strength as a 0-100 score for composite scoring.
        
        Scoring:
        - NONE (< 2.0): 0
        - NORMAL (2.0-3.0): 25-50 (linear interpolation)
        - STRONG (3.0-5.0): 50-75 (linear interpolation)
        - EXTREME (>= 5.0): 75-100 (capped at 100)
        
        Args:
            volume_ratio: Current volume / 20-period average volume
            
        Returns:
            Spike strength score 0-100
        """
        if volume_ratio < self.SPIKE_THRESHOLD:
            return 0
        elif volume_ratio < self.STRONG_THRESHOLD:
            # Linear interpolation from 25 to 50 for ratio 2.0 to 3.0
            progress = (volume_ratio - self.SPIKE_THRESHOLD) / (self.STRONG_THRESHOLD - self.SPIKE_THRESHOLD)
            return int(25 + progress * 25)
        elif volume_ratio < self.EXTREME_THRESHOLD:
            # Linear interpolation from 50 to 75 for ratio 3.0 to 5.0
            progress = (volume_ratio - self.STRONG_THRESHOLD) / (self.EXTREME_THRESHOLD - self.STRONG_THRESHOLD)
            return int(50 + progress * 25)
        else:
            # 75-100 for extreme, capped at 100
            # Each additional 1.0 ratio above 5.0 adds 5 points
            extra = min(25, int((volume_ratio - self.EXTREME_THRESHOLD) * 5))
            return 75 + extra
