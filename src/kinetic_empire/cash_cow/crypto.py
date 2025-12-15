"""Crypto-Specific Enhancement modules.

Implements funding rate analysis and BTC correlation adjustments
for crypto-specific trading optimizations.
"""

from dataclasses import dataclass
from typing import Optional


class FundingRateAnalyzer:
    """Analyzes funding rates for trading bonuses.
    
    From Requirements 10.1, 10.2:
    - Funding < -0.1%: +5 bonus for long trades
    - Funding > 0.1%: +5 bonus for short trades
    """

    EXTREME_NEGATIVE_THRESHOLD = -0.1  # -0.1%
    EXTREME_POSITIVE_THRESHOLD = 0.1   # 0.1%
    BONUS_POINTS = 5

    def get_funding_bonus(self, funding_rate: float, trade_direction: str) -> int:
        """Get bonus points based on funding rate and trade direction.
        
        Args:
            funding_rate: Current funding rate as percentage (e.g., -0.15 for -0.15%)
            trade_direction: "long" or "short"
            
        Returns:
            Bonus points: 5 for favorable funding, 0 otherwise
            
        Validates: Requirements 10.1, 10.2
        """
        direction = trade_direction.lower()
        
        # Extreme negative funding favors longs (shorts paying longs)
        if funding_rate < self.EXTREME_NEGATIVE_THRESHOLD and direction == "long":
            return self.BONUS_POINTS
        
        # Extreme positive funding favors shorts (longs paying shorts)
        if funding_rate > self.EXTREME_POSITIVE_THRESHOLD and direction == "short":
            return self.BONUS_POINTS
        
        return 0

    def is_funding_favorable(self, funding_rate: float, trade_direction: str) -> bool:
        """Check if funding rate is favorable for the trade direction.
        
        Args:
            funding_rate: Current funding rate as percentage
            trade_direction: "long" or "short"
            
        Returns:
            True if funding is favorable
        """
        return self.get_funding_bonus(funding_rate, trade_direction) > 0


@dataclass
class CorrelationConfig:
    """Configuration for BTC correlation adjustment."""
    high_correlation_threshold: float = 0.7  # Correlation > 0.7 is "high"
    btc_volatility_threshold: float = 3.0    # BTC volatility > 3% is "volatile"
    position_reduction_pct: float = 20.0     # Reduce position by 20%


class BTCCorrelationAdjuster:
    """Adjusts position sizes based on BTC correlation.
    
    From Requirements 10.3, 10.4:
    - High BTC correlation + volatile BTC: reduce position by 20%
    - Low BTC correlation: allow full position sizing
    """

    def __init__(self, config: Optional[CorrelationConfig] = None):
        """Initialize BTC correlation adjuster.
        
        Args:
            config: Correlation configuration
        """
        self.config = config or CorrelationConfig()

    def get_correlation_adjustment(
        self,
        btc_correlation: float,
        btc_volatility: float
    ) -> float:
        """Get position size adjustment based on BTC correlation.
        
        Args:
            btc_correlation: Correlation with BTC (-1 to 1)
            btc_volatility: BTC volatility as percentage
            
        Returns:
            Multiplier: 0.8 if high correlation + volatile BTC, 1.0 otherwise
            
        Validates: Requirements 10.3, 10.4
        """
        is_high_correlation = abs(btc_correlation) >= self.config.high_correlation_threshold
        is_btc_volatile = btc_volatility >= self.config.btc_volatility_threshold
        
        if is_high_correlation and is_btc_volatile:
            return 1.0 - (self.config.position_reduction_pct / 100)  # 0.8
        
        return 1.0  # Full position sizing

    def should_reduce_position(
        self,
        btc_correlation: float,
        btc_volatility: float
    ) -> bool:
        """Check if position should be reduced due to BTC correlation.
        
        Args:
            btc_correlation: Correlation with BTC
            btc_volatility: BTC volatility as percentage
            
        Returns:
            True if position should be reduced
        """
        return self.get_correlation_adjustment(btc_correlation, btc_volatility) < 1.0

    def calculate_adjusted_size(
        self,
        base_size: float,
        btc_correlation: float,
        btc_volatility: float
    ) -> float:
        """Calculate adjusted position size.
        
        Args:
            base_size: Base position size
            btc_correlation: Correlation with BTC
            btc_volatility: BTC volatility as percentage
            
        Returns:
            Adjusted position size
        """
        adjustment = self.get_correlation_adjustment(btc_correlation, btc_volatility)
        return base_size * adjustment
