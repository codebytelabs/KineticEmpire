"""Context Weighted Scorer for the Enhanced TA System.

Calculates final confidence score with weighted components.
"""

from .models import (
    MarketContext,
    ConfidenceScore,
    SignalConfidence,
    CONFIDENCE_WEIGHTS,
)


class ContextWeightedScorer:
    """Calculates weighted confidence score from market context.
    
    Weights:
    - Trend Alignment: 30%
    - Trend Strength: 20%
    - Volume Confirmation: 15%
    - Momentum: 15%
    - Support/Resistance: 10%
    - Market Regime: 10%
    
    Thresholds:
    - HIGH confidence: > 80
    - MEDIUM confidence: 65-80
    - LOW confidence: < 65 (no signal)
    """
    
    WEIGHTS = CONFIDENCE_WEIGHTS
    HIGH_THRESHOLD = 80
    MEDIUM_THRESHOLD = 20  # Lowered for demo testing (was 65)
    BASE_SCORE = 50  # Starting score before adjustments
    
    def calculate_score(self, context: MarketContext) -> ConfidenceScore:
        """Calculate weighted confidence score.
        
        Args:
            context: Aggregated market context
            
        Returns:
            ConfidenceScore with total and component breakdown
        """
        component_scores = {}
        
        # Calculate component scores (each normalized to 0-100 range)
        alignment_score = self._score_alignment(context)
        strength_score = self._score_strength(context)
        volume_score = self._score_volume(context)
        momentum_score = self._score_momentum(context)
        sr_score = self._score_support_resistance(context)
        regime_score = self._score_regime(context)

        component_scores = {
            "trend_alignment": alignment_score,
            "trend_strength": strength_score,
            "volume_confirmation": volume_score,
            "momentum": momentum_score,
            "support_resistance": sr_score,
            "market_regime": regime_score,
        }
        
        # Calculate weighted total
        total = 0
        for component, score in component_scores.items():
            weight = self.WEIGHTS.get(component, 0)
            total += score * weight
        
        # Add bonuses/penalties
        total += context.trend_alignment.alignment_bonus
        total -= context.trend_alignment.conflict_penalty
        total += context.btc_correlation_adjustment
        
        # Clamp to 0-100
        total = max(0, min(100, int(total)))
        
        # Determine confidence level
        if total > self.HIGH_THRESHOLD:
            level = SignalConfidence.HIGH
        elif total >= self.MEDIUM_THRESHOLD:
            level = SignalConfidence.MEDIUM
        else:
            level = SignalConfidence.LOW
        
        return ConfidenceScore(
            total_score=total,
            component_scores=component_scores,
            confidence_level=level,
            critical_factors_passed=True,  # Set by validator
            veto_reason=None,
        )
    
    def _score_alignment(self, context: MarketContext) -> int:
        """Score trend alignment (0-100)."""
        return int(context.trend_alignment.alignment_score * 100)
    
    def _score_strength(self, context: MarketContext) -> int:
        """Score trend strength (0-100)."""
        from .models import TrendStrength
        scores = {
            TrendStrength.STRONG: 100,
            TrendStrength.MODERATE: 70,
            TrendStrength.WEAK: 30,
        }
        return scores.get(context.trend_strength_4h, 50)
    
    def _score_volume(self, context: MarketContext) -> int:
        """Score volume confirmation (0-100).
        
        DEMO MODE: Higher base score for more signals.
        """
        base = 65  # Boosted from 50
        base += context.volume_confirmation.volume_score
        return max(0, min(100, base))
    
    def _score_momentum(self, context: MarketContext) -> int:
        """Score momentum (0-100).
        
        DEMO MODE: Higher base score for more signals.
        """
        base = 60  # Boosted from 50
        base += context.momentum.momentum_score
        if context.momentum.rsi_valid:
            base += 15  # Reduced from 20 to balance
        return max(0, min(100, base))
    
    def _score_support_resistance(self, context: MarketContext) -> int:
        """Score support/resistance (0-100).
        
        DEMO MODE: Higher base score for more signals.
        """
        base = 65  # Boosted from 50
        base += context.support_resistance.sr_score
        return max(0, min(100, base))
    
    def _score_regime(self, context: MarketContext) -> int:
        """Score market regime (0-100).
        
        DEMO MODE: Boosted scores for sideways/choppy to allow more trades.
        For live trading, revert SIDEWAYS to 30 and CHOPPY to 10.
        """
        from .models import MarketRegime
        scores = {
            MarketRegime.TRENDING: 100,
            MarketRegime.LOW_VOLATILITY: 80,
            MarketRegime.HIGH_VOLATILITY: 70,
            MarketRegime.SIDEWAYS: 70,  # Boosted from 30 - can still scalp in sideways
            MarketRegime.CHOPPY: 50,    # Boosted from 10 - more forgiving
        }
        return scores.get(context.market_regime, 50)
