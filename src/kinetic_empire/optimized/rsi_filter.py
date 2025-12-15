"""Optimized RSI filter with enhanced thresholds."""

from .models import RSIResult
from .config import OptimizedConfig, DEFAULT_CONFIG


class OptimizedRSIFilter:
    """Filters entries based on optimized RSI thresholds."""
    
    def __init__(self, config: OptimizedConfig = DEFAULT_CONFIG):
        self.config = config
    
    def evaluate_entry(
        self,
        rsi: float,
        direction: str,
        has_divergence: bool = False
    ) -> RSIResult:
        """Evaluate RSI for entry signal.
        
        Args:
            rsi: Current RSI value (0-100)
            direction: 'long' or 'short'
            has_divergence: Whether RSI divergence is detected
            
        Returns:
            RSIResult with signal validity and confidence adjustments
        """
        if rsi < 0 or rsi > 100:
            raise ValueError("rsi must be between 0 and 100")
        
        if direction not in ('long', 'short'):
            raise ValueError("direction must be 'long' or 'short'")
        
        confidence_bonus = 0
        
        # Add divergence bonus if detected
        if has_divergence:
            confidence_bonus += self.config.RSI_DIVERGENCE_BONUS
        
        # Check thresholds based on direction
        if direction == 'long':
            if rsi < self.config.RSI_OVERSOLD_THRESHOLD:
                return RSIResult(
                    signal_valid=True,
                    requires_confirmation=False,
                    confidence_bonus=confidence_bonus,
                    reason=f"RSI {rsi:.1f} below oversold threshold {self.config.RSI_OVERSOLD_THRESHOLD}"
                )
            elif rsi < self.config.RSI_OVERBOUGHT_THRESHOLD:
                return RSIResult(
                    signal_valid=False,
                    requires_confirmation=True,
                    confidence_bonus=confidence_bonus,
                    reason=f"RSI {rsi:.1f} in neutral zone, requires confirmation"
                )
            else:
                return RSIResult(
                    signal_valid=False,
                    requires_confirmation=False,
                    confidence_bonus=confidence_bonus,
                    reason=f"RSI {rsi:.1f} overbought, invalid for long"
                )
        else:  # short
            if rsi > self.config.RSI_OVERBOUGHT_THRESHOLD:
                return RSIResult(
                    signal_valid=True,
                    requires_confirmation=False,
                    confidence_bonus=confidence_bonus,
                    reason=f"RSI {rsi:.1f} above overbought threshold {self.config.RSI_OVERBOUGHT_THRESHOLD}"
                )
            elif rsi > self.config.RSI_OVERSOLD_THRESHOLD:
                return RSIResult(
                    signal_valid=False,
                    requires_confirmation=True,
                    confidence_bonus=confidence_bonus,
                    reason=f"RSI {rsi:.1f} in neutral zone, requires confirmation"
                )
            else:
                return RSIResult(
                    signal_valid=False,
                    requires_confirmation=False,
                    confidence_bonus=confidence_bonus,
                    reason=f"RSI {rsi:.1f} oversold, invalid for short"
                )
