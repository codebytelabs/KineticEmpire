"""Volume Confirmation Analyzer for the Enhanced TA System.

Validates that price movements are supported by corresponding volume.
Uses BTC as market benchmark to dynamically adjust thresholds.
"""

from typing import List, Optional

from .models import VolumeConfirmation


class VolumeConfirmationAnalyzer:
    """Analyzes volume to confirm price movements.
    
    Uses BTC volume as market benchmark - if BTC volume is low,
    we expect all coins to have lower volume and adjust thresholds.
    
    Thresholds (base values, adjusted by BTC benchmark):
    - Minimum volume: 60% of average (adjusted by BTC ratio)
    - Volume spike: 150% of average (+15 points)
    - False move: significant price move + volume < 40%
    - Declining: 5 consecutive declining candles
    """
    
    BASE_MIN_VOLUME_RATIO = 0.60   # Base 60% threshold
    MIN_THRESHOLD_FLOOR = 0.30    # Never go below 30%
    SPIKE_VOLUME_RATIO = 1.50     # 150% of average
    FALSE_MOVE_RATIO = 0.40       # 40% of average
    DECLINING_CANDLES = 5         # Consecutive declining candles
    SPIKE_BONUS = 15              # Points for volume spike
    DECLINING_PENALTY = 10        # Points for declining volume
    
    def __init__(self):
        self._btc_volume_ratio: float = 1.0  # Default to 100%
    
    def set_btc_benchmark(self, btc_volume_ratio: float) -> None:
        """Set BTC volume ratio as market benchmark.
        
        Args:
            btc_volume_ratio: BTC's current volume / average volume
        """
        self._btc_volume_ratio = max(0.3, min(2.0, btc_volume_ratio))  # Clamp 0.3-2.0
    
    def get_adjusted_threshold(self) -> float:
        """Get the BTC-adjusted volume threshold.
        
        If BTC is at 70% of its average, we adjust threshold down proportionally.
        This accounts for market-wide low volume periods.
        
        Returns:
            Adjusted minimum volume ratio threshold
        """
        # Scale threshold by BTC's volume ratio
        # If BTC at 0.7x, threshold becomes 0.60 * 0.7 = 0.42
        adjusted = self.BASE_MIN_VOLUME_RATIO * self._btc_volume_ratio
        return max(self.MIN_THRESHOLD_FLOOR, adjusted)
    
    def analyze(
        self,
        volume_ratio: float,
        volume_history: List[float],
        price_change_pct: float,
        btc_volume_ratio: Optional[float] = None,
    ) -> VolumeConfirmation:
        """Analyze volume confirmation for price movement.
        
        Uses BTC volume as benchmark to dynamically adjust thresholds.
        If BTC volume is low, we expect all coins to have lower volume.
        
        Args:
            volume_ratio: Current volume / average volume
            volume_history: Recent volume values for trend detection
            price_change_pct: Percentage price change
            btc_volume_ratio: BTC's current volume ratio (benchmark)
            
        Returns:
            VolumeConfirmation with analysis results
        """
        # Update BTC benchmark if provided
        if btc_volume_ratio is not None:
            self.set_btc_benchmark(btc_volume_ratio)
        
        # Get BTC-adjusted threshold
        adjusted_threshold = self.get_adjusted_threshold()
        
        # Check minimum volume requirement against adjusted threshold
        is_confirmed = volume_ratio >= adjusted_threshold
        
        # Check for volume spike
        is_spike = volume_ratio >= self.SPIKE_VOLUME_RATIO

        # Check for false move (significant price move with low volume)
        is_false_move = (
            abs(price_change_pct) > 1.0 and  # Significant price move
            volume_ratio < self.FALSE_MOVE_RATIO
        )
        
        # Check for declining volume
        is_declining = self._is_declining(volume_history)
        
        # Calculate volume score
        volume_score = self._calculate_score(
            is_confirmed, is_spike, is_declining, is_false_move
        )
        
        return VolumeConfirmation(
            is_confirmed=is_confirmed,
            volume_score=volume_score,
            is_declining=is_declining,
            is_false_move=is_false_move,
        )
    
    def _is_declining(self, volume_history: List[float]) -> bool:
        """Check if volume is declining over consecutive candles.
        
        Args:
            volume_history: Recent volume values
            
        Returns:
            True if volume declining for DECLINING_CANDLES consecutive candles
        """
        if len(volume_history) < self.DECLINING_CANDLES:
            return False
        
        recent = volume_history[-self.DECLINING_CANDLES:]
        for i in range(1, len(recent)):
            if recent[i] >= recent[i - 1]:
                return False
        return True
    
    def _calculate_score(
        self,
        is_confirmed: bool,
        is_spike: bool,
        is_declining: bool,
        is_false_move: bool,
    ) -> int:
        """Calculate volume contribution to confidence score.
        
        Args:
            is_confirmed: Volume meets minimum threshold
            is_spike: Volume spike detected
            is_declining: Volume declining
            is_false_move: False move detected
            
        Returns:
            Points to add to confidence score
        """
        if is_false_move:
            return -30  # Strong penalty for false moves
        
        if not is_confirmed:
            return -20  # Penalty for low volume
        
        score = 0
        if is_spike:
            score += self.SPIKE_BONUS
        if is_declining:
            score -= self.DECLINING_PENALTY
        
        return score
    
    def should_reject_signal(self, confirmation: VolumeConfirmation) -> bool:
        """Check if signal should be rejected based on volume.
        
        Args:
            confirmation: Volume confirmation analysis
            
        Returns:
            True if signal should be rejected
        """
        return not confirmation.is_confirmed or confirmation.is_false_move
