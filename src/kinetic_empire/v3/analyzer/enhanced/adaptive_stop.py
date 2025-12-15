"""Adaptive Stop Calculator for the Enhanced TA System.

Calculates stop losses based on market regime and trend strength.
"""

from .models import MarketRegime, TrendStrength


class AdaptiveStopCalculator:
    """Calculates adaptive stop loss distances.
    
    Regime multipliers:
    - TRENDING: 1.5x ATR
    - HIGH_VOLATILITY: 2.5x ATR
    - LOW_VOLATILITY: 1.0x ATR
    
    Strength multipliers:
    - STRONG: 1.2x ATR
    - MODERATE: 1.5x ATR
    - WEAK: 2.0x ATR
    """
    
    REGIME_MULTIPLIERS = {
        MarketRegime.TRENDING: 1.5,
        MarketRegime.HIGH_VOLATILITY: 2.5,
        MarketRegime.LOW_VOLATILITY: 1.0,
        MarketRegime.SIDEWAYS: 1.5,
        MarketRegime.CHOPPY: 2.0,
    }
    
    STRENGTH_MULTIPLIERS = {
        TrendStrength.STRONG: 1.2,
        TrendStrength.MODERATE: 1.5,
        TrendStrength.WEAK: 2.0,
    }
    
    def calculate(
        self,
        atr: float,
        regime: MarketRegime,
        strength: TrendStrength,
    ) -> float:
        """Calculate adaptive stop loss distance.
        
        Args:
            atr: Current ATR value
            regime: Current market regime
            strength: Current trend strength
            
        Returns:
            Stop loss distance in price units
        """
        regime_mult = self.REGIME_MULTIPLIERS.get(regime, 1.5)
        strength_mult = self.STRENGTH_MULTIPLIERS.get(strength, 1.5)

        # Use the larger of the two multipliers for safety
        multiplier = max(regime_mult, strength_mult)
        
        return atr * multiplier
    
    def calculate_stop_price(
        self,
        entry_price: float,
        atr: float,
        regime: MarketRegime,
        strength: TrendStrength,
        direction: str,
    ) -> float:
        """Calculate stop loss price.
        
        Args:
            entry_price: Entry price
            atr: Current ATR value
            regime: Current market regime
            strength: Current trend strength
            direction: "LONG" or "SHORT"
            
        Returns:
            Stop loss price
        """
        stop_distance = self.calculate(atr, regime, strength)
        
        if direction == "LONG":
            return entry_price - stop_distance
        else:
            return entry_price + stop_distance
    
    def get_regime_multiplier(self, regime: MarketRegime) -> float:
        """Get stop loss multiplier for regime.
        
        Args:
            regime: Market regime
            
        Returns:
            ATR multiplier
        """
        return self.REGIME_MULTIPLIERS.get(regime, 1.5)
    
    def get_strength_multiplier(self, strength: TrendStrength) -> float:
        """Get stop loss multiplier for trend strength.
        
        Args:
            strength: Trend strength
            
        Returns:
            ATR multiplier
        """
        return self.STRENGTH_MULTIPLIERS.get(strength, 1.5)
