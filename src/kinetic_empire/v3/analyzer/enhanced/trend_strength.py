"""Trend Strength Calculator for the Enhanced TA System.

Quantifies trend strength based on EMA separation percentage.
"""

from .models import TrendStrength


class TrendStrengthCalculator:
    """Calculates trend strength from EMA separation.
    
    Classification thresholds:
    - STRONG: EMA separation > 1%
    - MODERATE: EMA separation 0.3% - 1%
    - WEAK: EMA separation < 0.3%
    """
    
    # Threshold constants (as percentages)
    STRONG_THRESHOLD = 1.0    # > 1% = STRONG
    MODERATE_THRESHOLD = 0.3  # > 0.3% = MODERATE, else WEAK
    
    def calculate(self, ema_9: float, ema_21: float, price: float) -> TrendStrength:
        """Calculate trend strength from EMA separation percentage.
        
        Args:
            ema_9: 9-period EMA value
            ema_21: 21-period EMA value
            price: Current price for percentage calculation
            
        Returns:
            TrendStrength enum value (STRONG, MODERATE, or WEAK)
        """
        if price <= 0:
            return TrendStrength.WEAK
            
        separation_pct = abs(ema_9 - ema_21) / price * 100
        
        if separation_pct > self.STRONG_THRESHOLD:
            return TrendStrength.STRONG
        elif separation_pct > self.MODERATE_THRESHOLD:
            return TrendStrength.MODERATE
        else:
            return TrendStrength.WEAK
    
    def get_separation_percentage(self, ema_9: float, ema_21: float, price: float) -> float:
        """Get the raw EMA separation percentage.
        
        Args:
            ema_9: 9-period EMA value
            ema_21: 21-period EMA value
            price: Current price for percentage calculation
            
        Returns:
            Separation percentage (always positive)
        """
        if price <= 0:
            return 0.0
        return abs(ema_9 - ema_21) / price * 100
    
    def get_confidence_adjustment(self, strength: TrendStrength) -> int:
        """Get confidence score adjustment based on trend strength.
        
        Args:
            strength: The calculated trend strength
            
        Returns:
            Points to add/subtract from confidence score
        """
        if strength == TrendStrength.WEAK:
            return -20  # Reduce confidence by 20 points for weak trends
        elif strength == TrendStrength.STRONG:
            return 10   # Bonus for strong trends
        return 0  # No adjustment for moderate
