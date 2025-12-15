"""Upside Potential Analysis module.

Calculates room to run (distance to resistance) and risk/reward ratios
to avoid trades with limited upside potential.
"""

from dataclasses import dataclass

from .models import UpsideQuality, UpsideAnalysis


class UpsideAnalyzer:
    """Analyzes upside potential for trading opportunities.
    
    Scoring:
    - >5% room: 25 points (excellent)
    - 3-5% room: 20 points (good)
    - 1-3% room: 10 points (limited)
    - <1% room: 0 points with -15 penalty (poor)
    
    R/R Bonus:
    - >3:1 ratio: +5 points
    - >2:1 ratio: +3 points
    """

    def calculate_distance_to_resistance(self, price: float, resistance: float) -> float:
        """Calculate distance to resistance as percentage.
        
        Args:
            price: Current price
            resistance: Resistance level
            
        Returns:
            Distance as percentage of current price
            
        Validates: Requirement 5.1
        """
        if price <= 0:
            return 0.0
        if resistance <= price:
            return 0.0
        return ((resistance - price) / price) * 100

    def calculate_distance_to_support(self, price: float, support: float) -> float:
        """Calculate distance to support as percentage.
        
        Args:
            price: Current price
            support: Support level
            
        Returns:
            Distance as percentage of current price
        """
        if price <= 0:
            return 0.0
        if support >= price:
            return 0.0
        return ((price - support) / price) * 100

    def calculate_risk_reward(self, price: float, resistance: float, support: float) -> float:
        """Calculate risk/reward ratio.
        
        R/R = (resistance - price) / (price - support)
        
        Args:
            price: Current price
            resistance: Resistance level (target)
            support: Support level (stop)
            
        Returns:
            Risk/reward ratio, or 0 if invalid
            
        Validates: Requirement 5.6
        """
        if support >= price or resistance <= price:
            return 0.0
        
        reward = resistance - price
        risk = price - support
        
        if risk <= 0:
            return 0.0
        
        return reward / risk

    def get_upside_quality(self, distance_pct: float) -> UpsideQuality:
        """Classify upside quality based on distance to resistance.
        
        Args:
            distance_pct: Distance to resistance as percentage
            
        Returns:
            UpsideQuality enum value
        """
        if distance_pct > 5.0:
            return UpsideQuality.EXCELLENT
        elif distance_pct >= 3.0:
            return UpsideQuality.GOOD
        elif distance_pct >= 1.0:
            return UpsideQuality.LIMITED
        else:
            return UpsideQuality.POOR

    def get_upside_score(self, distance_pct: float) -> int:
        """Get upside score based on distance to resistance.
        
        Args:
            distance_pct: Distance to resistance as percentage
            
        Returns:
            Score: 25 for >5%, 20 for 3-5%, 10 for 1-3%, 0 for <1%
            
        Validates: Requirements 5.2, 5.3, 5.4, 5.5
        """
        if distance_pct > 5.0:
            return 25  # Excellent room
        elif distance_pct >= 3.0:
            return 20  # Good room
        elif distance_pct >= 1.0:
            return 10  # Limited room
        else:
            return 0   # Poor room

    def get_upside_penalty(self, distance_pct: float) -> int:
        """Get penalty for poor upside potential.
        
        Args:
            distance_pct: Distance to resistance as percentage
            
        Returns:
            Penalty: 15 for <1% room, 0 otherwise
            
        Validates: Requirement 5.5
        """
        if distance_pct < 1.0:
            return 15
        return 0

    def get_rr_bonus(self, rr_ratio: float) -> int:
        """Get bonus points for favorable risk/reward ratio.
        
        Args:
            rr_ratio: Risk/reward ratio
            
        Returns:
            Bonus: 5 for >3:1, 3 for >2:1, 0 otherwise
            
        Validates: Requirements 5.7, 5.8
        """
        if rr_ratio > 3.0:
            return 5
        elif rr_ratio > 2.0:
            return 3
        else:
            return 0

    def analyze(self, price: float, resistance: float, support: float) -> UpsideAnalysis:
        """Perform complete upside analysis.
        
        Args:
            price: Current price
            resistance: Resistance level
            support: Support level
            
        Returns:
            UpsideAnalysis with all metrics and scores
        """
        distance_to_resistance = self.calculate_distance_to_resistance(price, resistance)
        distance_to_support = self.calculate_distance_to_support(price, support)
        rr_ratio = self.calculate_risk_reward(price, resistance, support)
        
        quality = self.get_upside_quality(distance_to_resistance)
        upside_score = self.get_upside_score(distance_to_resistance)
        penalty = self.get_upside_penalty(distance_to_resistance)
        rr_bonus = self.get_rr_bonus(rr_ratio)
        
        return UpsideAnalysis(
            distance_to_resistance_pct=distance_to_resistance,
            distance_to_support_pct=distance_to_support,
            risk_reward_ratio=rr_ratio,
            upside_quality=quality,
            upside_score=upside_score,
            rr_bonus=rr_bonus,
            penalty=penalty,
        )
