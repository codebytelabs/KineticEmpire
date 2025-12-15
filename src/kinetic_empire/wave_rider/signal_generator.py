"""Wave Rider Signal Generator.

Generates entry signals based on momentum and MTF analysis:
- Validates entry conditions (volume ratio, alignment, RSI, blacklist, exposure)
- Determines signal direction (LONG/SHORT based on VWAP and trend)
- Calculates position parameters
"""

from typing import Optional
from .models import (
    MoverData,
    MTFResult,
    WaveRiderSignal,
    SpikeClassification,
    TrendDirection,
    WaveRiderConfig,
)
from .position_sizer import WaveRiderPositionSizer


class WaveRiderSignalGenerator:
    """Generates entry signals based on momentum and MTF analysis.
    
    Property 6: Entry Rejection Conditions
    Signal is rejected if:
    - volume_ratio < 2.0
    - alignment_score < 70
    - RSI < 25 or RSI > 75
    - symbol is blacklisted
    - current_exposure >= 45%
    
    Property 7: Signal Direction Determination
    - LONG: price > VWAP AND majority timeframes BULLISH
    - SHORT: price < VWAP AND majority timeframes BEARISH
    """
    
    def __init__(self, config: Optional[WaveRiderConfig] = None):
        """Initialize the signal generator.
        
        Args:
            config: Wave Rider configuration
        """
        self.config = config or WaveRiderConfig()
        self.position_sizer = WaveRiderPositionSizer(config)
    
    def evaluate(
        self,
        mover: MoverData,
        mtf_result: MTFResult,
        is_blacklisted: bool,
        current_exposure: float,
        consecutive_losses: int = 0,
        available_capital: float = 10000,
    ) -> Optional[WaveRiderSignal]:
        """Evaluate entry conditions and generate signal if valid.
        
        Args:
            mover: Top mover data with momentum score
            mtf_result: Multi-timeframe analysis result
            is_blacklisted: Whether symbol is blacklisted
            current_exposure: Current portfolio exposure (0.0-1.0)
            consecutive_losses: Number of consecutive losses
            available_capital: Available capital in USD
        
        Returns:
            WaveRiderSignal if conditions met, None otherwise
        """
        # Check rejection conditions (Property 6)
        rejection = self._check_rejection_conditions(
            mover, mtf_result, is_blacklisted, current_exposure
        )
        if rejection:
            return None
        
        # Determine direction (Property 7)
        direction = self._determine_direction(mtf_result)
        if direction is None:
            return None
        
        # Get RSI from 1m timeframe
        rsi_1m = mtf_result.analyses.get("1m")
        rsi_value = rsi_1m.rsi if rsi_1m else 50.0
        
        # Calculate position parameters
        size_result = self.position_sizer.calculate(
            volume_ratio=mover.volume_ratio,
            alignment_score=mtf_result.alignment_score,
            consecutive_losses=consecutive_losses,
            available_capital=available_capital,
            current_exposure=current_exposure,
        )
        
        if size_result.size_pct <= 0:
            return None
        
        # Calculate confidence score
        confidence = self._calculate_confidence(mover, mtf_result)
        
        # Calculate stop loss percentage (will be refined by stop calculator)
        stop_loss_pct = self._estimate_stop_loss(mover.volume_ratio)
        
        return WaveRiderSignal(
            symbol=mover.symbol,
            direction=direction,
            volume_ratio=mover.volume_ratio,
            spike_classification=mover.spike_classification,
            alignment_score=mtf_result.alignment_score,
            rsi_1m=rsi_value,
            position_size_pct=size_result.size_pct,
            leverage=size_result.leverage,
            stop_loss_pct=stop_loss_pct,
            confidence_score=confidence,
            entry_price=mover.price,
        )
    
    def _check_rejection_conditions(
        self,
        mover: MoverData,
        mtf_result: MTFResult,
        is_blacklisted: bool,
        current_exposure: float,
    ) -> Optional[str]:
        """Check if entry should be rejected.
        
        Returns rejection reason or None if valid.
        """
        # Volume ratio check
        if mover.volume_ratio < self.config.min_volume_ratio:
            return f"volume_ratio {mover.volume_ratio:.2f} < {self.config.min_volume_ratio}"
        
        # Alignment score check
        if mtf_result.alignment_score < self.config.min_alignment_score:
            return f"alignment_score {mtf_result.alignment_score} < {self.config.min_alignment_score}"
        
        # RSI check (1m timeframe)
        rsi_1m = mtf_result.analyses.get("1m")
        if rsi_1m:
            if rsi_1m.rsi < self.config.rsi_min:
                return f"RSI {rsi_1m.rsi:.1f} < {self.config.rsi_min} (oversold)"
            if rsi_1m.rsi > self.config.rsi_max:
                return f"RSI {rsi_1m.rsi:.1f} > {self.config.rsi_max} (overbought)"
        
        # Blacklist check
        if is_blacklisted:
            return "symbol is blacklisted"
        
        # Exposure check
        if current_exposure >= self.config.max_exposure:
            return f"exposure {current_exposure:.1%} >= {self.config.max_exposure:.1%}"
        
        return None
    
    def _determine_direction(self, mtf_result: MTFResult) -> Optional[str]:
        """Determine signal direction based on VWAP and trend.
        
        Property 7:
        - LONG: price > VWAP AND majority BULLISH
        - SHORT: price < VWAP AND majority BEARISH
        
        Returns "LONG", "SHORT", or None if no clear direction.
        """
        # Check price vs VWAP
        price_above_vwap = mtf_result.price_vs_vwap == "ABOVE"
        
        # Check dominant direction
        dominant = mtf_result.dominant_direction
        
        if price_above_vwap and dominant == TrendDirection.BULLISH:
            return "LONG"
        elif not price_above_vwap and dominant == TrendDirection.BEARISH:
            return "SHORT"
        else:
            return None
    
    def _calculate_confidence(self, mover: MoverData, mtf_result: MTFResult) -> int:
        """Calculate confidence score 0-100.
        
        Based on:
        - Volume spike strength (0-40)
        - Alignment score (0-40)
        - Momentum score (0-20)
        """
        confidence = 0
        
        # Volume spike contribution (0-40)
        spike_scores = {
            SpikeClassification.NONE: 0,
            SpikeClassification.NORMAL: 20,
            SpikeClassification.STRONG: 30,
            SpikeClassification.EXTREME: 40,
        }
        confidence += spike_scores.get(mover.spike_classification, 0)
        
        # Alignment contribution (0-40)
        alignment_scores = {40: 10, 70: 25, 100: 40}
        confidence += alignment_scores.get(mtf_result.alignment_score, 10)
        
        # Momentum contribution (0-20)
        if mover.momentum_score >= 20:
            confidence += 20
        elif mover.momentum_score >= 10:
            confidence += 15
        elif mover.momentum_score >= 5:
            confidence += 10
        else:
            confidence += 5
        
        return min(100, confidence)
    
    def _estimate_stop_loss(self, volume_ratio: float) -> float:
        """Estimate stop loss percentage based on volume ratio.
        
        Higher volume = tighter stop (more conviction).
        """
        if volume_ratio >= 5.0:
            return 0.015  # 1.5%
        elif volume_ratio >= 3.0:
            return 0.02  # 2%
        else:
            return 0.025  # 2.5%
    
    def check_entry_conditions(
        self,
        volume_ratio: float,
        alignment_score: int,
        rsi: float,
        is_blacklisted: bool,
        current_exposure: float,
    ) -> bool:
        """Check if basic entry conditions are met.
        
        Simplified check for testing Property 6.
        """
        if volume_ratio < self.config.min_volume_ratio:
            return False
        if alignment_score < self.config.min_alignment_score:
            return False
        if rsi < self.config.rsi_min or rsi > self.config.rsi_max:
            return False
        if is_blacklisted:
            return False
        if current_exposure >= self.config.max_exposure:
            return False
        return True
