"""130-Point Opportunity Scoring System.

Implements comprehensive multi-factor scoring for trading opportunities
based on DayTraderAI's proven approach.
"""

from dataclasses import dataclass
from typing import Dict, Optional

from .models import MarketRegime, OpportunityScore


@dataclass
class ScoringFeatures:
    """Input features for opportunity scoring."""
    # Technical indicators
    ema_diff_pct: float = 0.0      # EMA crossover freshness
    rsi: float = 50.0              # RSI value (0-100)
    macd_histogram: float = 0.0   # MACD histogram value
    vwap_distance_pct: float = 0.0  # Distance from VWAP as %
    
    # Momentum
    adx: float = 0.0              # ADX strength (0-100)
    plus_di: float = 0.0          # +DI value
    minus_di: float = 0.0         # -DI value
    price_momentum: float = 0.0   # Price rate of change %
    
    # Volume
    volume_ratio: float = 1.0     # Current/average volume ratio
    obv_trend: int = 0            # OBV trend: 1=up, 0=flat, -1=down
    
    # Volatility
    atr_pct: float = 0.0          # ATR as % of price
    
    # Market context
    regime: MarketRegime = MarketRegime.TRENDING
    fear_greed_index: int = 50    # Fear & Greed (0-100)
    
    # Growth potential
    momentum_strength: float = 0.0
    volume_surge: bool = False


class OpportunityScorer:
    """Calculates 130-point opportunity scores.
    
    Score breakdown:
    - Technical Setup: 0-40 points
    - Momentum: 0-25 points
    - Volume: 0-20 points
    - Volatility: 0-15 points
    - Regime: 0-10 points
    - Sentiment: 0-10 points
    - Growth Potential: 0-10 points
    Total: 0-130 points
    """

    # Score bounds
    MAX_TECHNICAL = 40
    MAX_MOMENTUM = 25
    MAX_VOLUME = 20
    MAX_VOLATILITY = 15
    MAX_REGIME = 10
    MAX_SENTIMENT = 10
    MAX_GROWTH = 10

    def score_technical(self, features: ScoringFeatures) -> int:
        """Calculate technical setup score (0-40 points).
        
        Components:
        - EMA crossover freshness (10 pts)
        - RSI zones (10 pts)
        - MACD histogram (10 pts)
        - VWAP proximity (10 pts)
        
        Validates: Requirement 4.1
        """
        score = 0
        
        # EMA crossover freshness (10 pts)
        ema_score = min(10, max(0, int(abs(features.ema_diff_pct) * 5)))
        score += ema_score
        
        # RSI zones (10 pts) - optimal is 30-70
        if 30 <= features.rsi <= 70:
            rsi_score = 10
        elif 20 <= features.rsi < 30 or 70 < features.rsi <= 80:
            rsi_score = 7
        elif 10 <= features.rsi < 20 or 80 < features.rsi <= 90:
            rsi_score = 4
        else:
            rsi_score = 0
        score += rsi_score
        
        # MACD histogram strength (10 pts)
        macd_score = min(10, max(0, int(abs(features.macd_histogram) * 100)))
        score += macd_score
        
        # VWAP proximity (10 pts) - closer is better
        vwap_dist = abs(features.vwap_distance_pct)
        if vwap_dist < 0.5:
            vwap_score = 10
        elif vwap_dist < 1.0:
            vwap_score = 8
        elif vwap_dist < 2.0:
            vwap_score = 5
        elif vwap_dist < 3.0:
            vwap_score = 2
        else:
            vwap_score = 0
        score += vwap_score
        
        return min(score, self.MAX_TECHNICAL)

    def score_momentum(self, features: ScoringFeatures) -> int:
        """Calculate momentum score (0-25 points).
        
        Components:
        - ADX strength (10 pts)
        - DI spread (8 pts)
        - Price momentum (7 pts)
        
        Validates: Requirement 4.2
        """
        score = 0
        
        # ADX strength (10 pts)
        if features.adx > 50:
            adx_score = 10
        elif features.adx > 35:
            adx_score = 8
        elif features.adx > 25:
            adx_score = 6
        elif features.adx > 20:
            adx_score = 3
        else:
            adx_score = 0
        score += adx_score
        
        # DI spread (8 pts)
        di_spread = abs(features.plus_di - features.minus_di)
        if di_spread > 20:
            di_score = 8
        elif di_spread > 15:
            di_score = 6
        elif di_spread > 10:
            di_score = 4
        elif di_spread > 5:
            di_score = 2
        else:
            di_score = 0
        score += di_score
        
        # Price momentum (7 pts)
        mom = abs(features.price_momentum)
        if mom > 5:
            mom_score = 7
        elif mom > 3:
            mom_score = 5
        elif mom > 2:
            mom_score = 3
        elif mom > 1:
            mom_score = 1
        else:
            mom_score = 0
        score += mom_score
        
        return min(score, self.MAX_MOMENTUM)

    def score_volume(self, features: ScoringFeatures) -> int:
        """Calculate volume score (0-20 points).
        
        Components:
        - Volume ratio (10 pts)
        - Volume surge (5 pts)
        - OBV confirmation (5 pts)
        
        Validates: Requirement 4.3
        """
        score = 0
        
        # Volume ratio (10 pts)
        ratio = features.volume_ratio
        if ratio > 3.0:
            vol_score = 10
        elif ratio > 2.0:
            vol_score = 8
        elif ratio > 1.5:
            vol_score = 6
        elif ratio > 1.2:
            vol_score = 4
        elif ratio > 1.0:
            vol_score = 2
        else:
            vol_score = 0
        score += vol_score
        
        # Volume surge (5 pts)
        if features.volume_surge:
            score += 5
        
        # OBV confirmation (5 pts)
        if features.obv_trend == 1:
            score += 5
        elif features.obv_trend == 0:
            score += 2
        
        return min(score, self.MAX_VOLUME)

    def score_volatility(self, features: ScoringFeatures) -> int:
        """Calculate volatility score (0-15 points).
        
        Based on ATR levels - moderate volatility is optimal.
        
        Validates: Requirement 4.4
        """
        atr = features.atr_pct
        
        # Optimal volatility range is 2-5%
        if 2.0 <= atr <= 5.0:
            return 15
        elif 1.5 <= atr < 2.0 or 5.0 < atr <= 7.0:
            return 12
        elif 1.0 <= atr < 1.5 or 7.0 < atr <= 10.0:
            return 8
        elif 0.5 <= atr < 1.0 or 10.0 < atr <= 15.0:
            return 4
        else:
            return 0

    def score_regime(self, regime: MarketRegime) -> int:
        """Calculate market regime score (0-10 points).
        
        Validates: Requirement 4.5
        """
        scores = {
            MarketRegime.TRENDING: 10,
            MarketRegime.LOW_VOLATILITY: 8,
            MarketRegime.HIGH_VOLATILITY: 5,
            MarketRegime.CHOPPY: 3,
            MarketRegime.BEAR: 2,
        }
        return scores.get(regime, 5)

    def score_sentiment(self, fear_greed: int) -> int:
        """Calculate crypto sentiment score (0-10 points).
        
        Based on Fear & Greed Index.
        
        Validates: Requirement 4.6
        """
        # Extreme fear (0-25) or extreme greed (75-100) are contrarian signals
        # Neutral (40-60) is optimal for trend following
        if 40 <= fear_greed <= 60:
            return 10
        elif 30 <= fear_greed < 40 or 60 < fear_greed <= 70:
            return 8
        elif 20 <= fear_greed < 30 or 70 < fear_greed <= 80:
            return 5
        elif fear_greed < 20:  # Extreme fear - contrarian long
            return 7
        else:  # Extreme greed - caution
            return 3

    def score_growth_potential(self, features: ScoringFeatures) -> int:
        """Calculate growth potential score (0-10 points).
        
        Based on volatility, momentum strength, and volume surge.
        
        Validates: Requirement 4.7
        """
        score = 0
        
        # Volatility component (3 pts)
        if 2.0 <= features.atr_pct <= 8.0:
            score += 3
        elif 1.0 <= features.atr_pct <= 10.0:
            score += 1
        
        # Momentum strength (4 pts)
        if features.momentum_strength > 5:
            score += 4
        elif features.momentum_strength > 3:
            score += 3
        elif features.momentum_strength > 1:
            score += 1
        
        # Volume surge (3 pts)
        if features.volume_surge:
            score += 3
        
        return min(score, self.MAX_GROWTH)

    def calculate_total(self, features: ScoringFeatures) -> OpportunityScore:
        """Calculate total opportunity score.
        
        Validates: Requirement 4.8
        """
        technical = self.score_technical(features)
        momentum = self.score_momentum(features)
        volume = self.score_volume(features)
        volatility = self.score_volatility(features)
        regime = self.score_regime(features.regime)
        sentiment = self.score_sentiment(features.fear_greed_index)
        growth = self.score_growth_potential(features)
        
        return OpportunityScore(
            technical_score=technical,
            momentum_score=momentum,
            volume_score=volume,
            volatility_score=volatility,
            regime_score=regime,
            sentiment_score=sentiment,
            growth_score=growth,
        )
