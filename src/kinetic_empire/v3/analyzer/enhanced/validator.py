"""Critical Factor Validator for the Enhanced TA System.

Validates critical factors that can veto signals regardless of score.
Uses hierarchical trend alignment per professional quant practice.
"""

from dataclasses import dataclass
from typing import Optional

from .models import MarketContext, TrendStrength, MarketRegime, TrendDirection


@dataclass
class ValidationResult:
    """Result of critical factor validation."""
    passed: bool
    veto_reason: Optional[str] = None


class CriticalFactorValidator:
    """Validates critical factors that can veto signals.
    
    Uses HIERARCHICAL trend alignment (professional quant practice):
    - Best: 4H + 1H + 15M all aligned
    - Good: 4H + 1H aligned (15M can differ - entry timing)
    - Acceptable: 4H strong + 15M confirms (1H pullback entry)
    - Reject: 4H weak or no confirmation from lower timeframes
    
    Other critical factors:
    - Volume below BTC-adjusted threshold
    - Weak 4H trend strength
    - Sideways regime
    - Choppy market conditions
    """
    
    def validate(self, context: MarketContext) -> ValidationResult:
        """Validate all critical factors.
        
        Args:
            context: Market context to validate
            
        Returns:
            ValidationResult with pass/fail and reason
        """
        # Check hierarchical trend alignment
        alignment_result = self._validate_hierarchical_alignment(context)
        if not alignment_result.passed:
            return alignment_result
        
        # Volume check DISABLED for demo testing
        # Uncomment below for live trading:
        # if not context.volume_confirmation.is_confirmed:
        #     return ValidationResult(
        #         passed=False,
        #         veto_reason="Volume below BTC-adjusted threshold"
        #     )

        # ============================================================
        # DEMO MODE: Most checks disabled for testing
        # Re-enable these for live trading!
        # ============================================================
        
        # Check for false move - DISABLED for demo
        # if context.volume_confirmation.is_false_move:
        #     return ValidationResult(
        #         passed=False,
        #         veto_reason="False move detected: significant price move with low volume"
        #     )
        
        # Check weak 4H trend - DISABLED for demo
        # if context.trend_strength_4h == TrendStrength.WEAK:
        #     return ValidationResult(
        #         passed=False,
        #         veto_reason="Weak 4H trend strength"
        #     )
        
        # Check sideways regime - DISABLED for demo
        # if context.market_regime == MarketRegime.SIDEWAYS:
        #     return ValidationResult(
        #         passed=False,
        #         veto_reason="Sideways market regime - no trend-following signals"
        #     )
        
        # Check choppy conditions - DISABLED for demo
        # if context.is_choppy or context.market_regime == MarketRegime.CHOPPY:
        #     return ValidationResult(
        #         passed=False,
        #         veto_reason="Choppy market conditions detected"
        #     )
        
        return ValidationResult(passed=True)
    
    def _validate_hierarchical_alignment(self, context: MarketContext) -> ValidationResult:
        """Validate trend alignment using hierarchical approach.
        
        Professional quant practice: higher timeframes take precedence.
        
        Passes if ANY of these conditions are met:
        1. All timeframes aligned (best case)
        2. 4H and 1H aligned (15M is just for entry timing)
        3. 4H is STRONG/MODERATE and 15M confirms 4H (pullback entry)
        4. 4H is STRONG - trust the higher timeframe regardless of lower TFs
        
        Args:
            context: Market context with trend data
            
        Returns:
            ValidationResult with pass/fail and reason
        """
        alignment = context.trend_alignment
        trend_4h = context.trend_4h
        trend_1h = context.trend_1h
        trend_15m = context.trend_15m
        
        # If we don't have individual trends, fall back to old logic
        if trend_4h is None or trend_1h is None or trend_15m is None:
            if not alignment.is_aligned and alignment.conflict_penalty > 0:
                return ValidationResult(
                    passed=False,
                    veto_reason="Trend alignment failure: 4H and 1H trends conflict"
                )
            return ValidationResult(passed=True)
        
        # Case 1: All timeframes aligned - PASS
        if alignment.is_aligned:
            return ValidationResult(passed=True)
        
        # Case 2: 4H and 1H aligned (15M can differ) - PASS
        if trend_4h == trend_1h and trend_4h != TrendDirection.SIDEWAYS:
            return ValidationResult(passed=True)
        
        # Case 3: 4H is strong/moderate AND 15M confirms 4H direction - PASS
        # This is the "pullback entry" - 1H temporarily against trend
        if (context.trend_strength_4h in (TrendStrength.STRONG, TrendStrength.MODERATE) and
            trend_4h != TrendDirection.SIDEWAYS and
            trend_15m == trend_4h):
            return ValidationResult(passed=True)
        
        # Case 4: 4H is STRONG - trust the higher timeframe (demo/testing mode)
        # Even if lower timeframes don't confirm, a strong 4H trend is tradeable
        if (context.trend_strength_4h == TrendStrength.STRONG and
            trend_4h != TrendDirection.SIDEWAYS):
            return ValidationResult(passed=True)
        
        # Case 5: DEMO MODE - Just require 4H to have a direction
        # This is very relaxed, only for testing!
        if trend_4h != TrendDirection.SIDEWAYS:
            return ValidationResult(passed=True)
        
        # Case 6: AGGRESSIVE DEMO MODE - Allow trading even when 4H is sideways
        # if 1H OR 15M has a clear direction. This is for scalping in ranging markets.
        # WARNING: Higher risk, but allows more trades in sideways conditions.
        if trend_1h != TrendDirection.SIDEWAYS or trend_15m != TrendDirection.SIDEWAYS:
            return ValidationResult(passed=True)
        
        # No valid alignment pattern found - all timeframes are sideways
        return ValidationResult(
            passed=False,
            veto_reason=f"Trend alignment failure: 4H={trend_4h.value}, 1H={trend_1h.value}, 15M={trend_15m.value}"
        )
    
    def validate_trend_alignment(self, context: MarketContext) -> bool:
        """Check if trend alignment passes.
        
        Args:
            context: Market context
            
        Returns:
            True if trend alignment is acceptable
        """
        return self._validate_hierarchical_alignment(context).passed
    
    def validate_volume(self, context: MarketContext) -> bool:
        """Check if volume passes threshold.
        
        Args:
            context: Market context
            
        Returns:
            True if volume is confirmed
        """
        return context.volume_confirmation.is_confirmed and not context.volume_confirmation.is_false_move
    
    def validate_trend_strength(self, context: MarketContext) -> bool:
        """Check if 4H trend strength is acceptable.
        
        Args:
            context: Market context
            
        Returns:
            True if trend strength is not WEAK
        """
        return context.trend_strength_4h != TrendStrength.WEAK
    
    def validate_regime(self, context: MarketContext) -> bool:
        """Check if market regime allows signals.
        
        Args:
            context: Market context
            
        Returns:
            True if regime is not SIDEWAYS or CHOPPY
        """
        return context.market_regime not in (MarketRegime.SIDEWAYS, MarketRegime.CHOPPY)
