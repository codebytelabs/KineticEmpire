"""Parameter adjuster that coordinates all optimized components."""

from dataclasses import dataclass
from typing import Optional
from .models import MarketRegime
from .config import OptimizedConfig, DEFAULT_CONFIG
from .atr_stop import OptimizedATRStopCalculator
from .leverage import OptimizedLeverageCalculator
from .position_sizer import OptimizedPositionSizer
from .trailing_stop import OptimizedTrailingStop
from .rsi_filter import OptimizedRSIFilter
from .adx_filter import OptimizedADXFilter
from .volume_confirmer import OptimizedVolumeConfirmer
from .portfolio_risk import OptimizedPortfolioRiskGuard


@dataclass
class AdjustedParameters:
    """Container for regime-adjusted parameters."""
    atr_multiplier: float
    max_leverage: int
    kelly_fraction: float
    trailing_activation: float
    trailing_step: float
    rsi_oversold: int
    rsi_overbought: int
    adx_threshold: int
    volume_multiplier: float
    max_positions: int
    max_margin: float
    regime: MarketRegime
    regime_confidence: float


class ParameterAdjuster:
    """Coordinates all optimized calculators with regime adaptation."""
    
    def __init__(self, config: OptimizedConfig = DEFAULT_CONFIG):
        self.config = config
        self.atr_calculator = OptimizedATRStopCalculator(config)
        self.leverage_calculator = OptimizedLeverageCalculator(config)
        self.position_sizer = OptimizedPositionSizer(config)
        self.trailing_stop = OptimizedTrailingStop(config)
        self.rsi_filter = OptimizedRSIFilter(config)
        self.adx_filter = OptimizedADXFilter(config)
        self.volume_confirmer = OptimizedVolumeConfirmer(config)
        self.portfolio_guard = OptimizedPortfolioRiskGuard(config)
    
    def get_adjusted_parameters(
        self,
        regime: MarketRegime,
        regime_confidence: float = 1.0
    ) -> AdjustedParameters:
        """Get all parameters adjusted for current regime.
        
        Args:
            regime: Current market regime
            regime_confidence: Confidence in regime detection (0-1)
            
        Returns:
            AdjustedParameters with all values adjusted for regime
        """
        # Use conservative defaults if regime confidence is low
        if regime_confidence < self.config.REGIME_CONFIDENCE_THRESHOLD:
            return self._get_conservative_defaults(regime_confidence)
        
        # Get regime-adjusted values
        atr_multiplier = self.atr_calculator.get_multiplier(regime)
        trailing_activation = self.trailing_stop.get_activation_threshold(regime)
        
        # Adjust leverage for regime
        base_leverage = self.config.LEVERAGE_HARD_CAP
        if regime in (MarketRegime.CHOPPY, MarketRegime.HIGH_VOLATILITY):
            base_leverage = int(base_leverage * self.config.LEVERAGE_REGIME_REDUCTION)
        
        return AdjustedParameters(
            atr_multiplier=atr_multiplier,
            max_leverage=base_leverage,
            kelly_fraction=self.config.KELLY_FRACTION,
            trailing_activation=trailing_activation,
            trailing_step=self.config.TRAILING_STEP_SIZE,
            rsi_oversold=self.config.RSI_OVERSOLD_THRESHOLD,
            rsi_overbought=self.config.RSI_OVERBOUGHT_THRESHOLD,
            adx_threshold=self.config.ADX_TRENDING_THRESHOLD,
            volume_multiplier=self.config.VOLUME_REQUIRED_MULTIPLIER,
            max_positions=self.config.MAX_POSITIONS,
            max_margin=self.config.MAX_MARGIN_USAGE,
            regime=regime,
            regime_confidence=regime_confidence
        )
    
    def _get_conservative_defaults(
        self,
        regime_confidence: float
    ) -> AdjustedParameters:
        """Get conservative default parameters for low-confidence regime.
        
        Uses the most conservative values across all regimes.
        """
        return AdjustedParameters(
            atr_multiplier=self.config.ATR_HIGH_VOL_MULTIPLIER,  # Widest stops
            max_leverage=self.config.LEVERAGE_TIER_LOW,  # Lowest leverage
            kelly_fraction=self.config.KELLY_LOW_WINRATE_FRACTION,  # Most conservative
            trailing_activation=self.config.TRAILING_SIDEWAYS_ACTIVATION,  # Tightest
            trailing_step=self.config.TRAILING_STEP_SIZE,
            rsi_oversold=self.config.RSI_OVERSOLD_THRESHOLD,
            rsi_overbought=self.config.RSI_OVERBOUGHT_THRESHOLD,
            adx_threshold=self.config.ADX_TRENDING_THRESHOLD,
            volume_multiplier=self.config.VOLUME_REQUIRED_MULTIPLIER,
            max_positions=self.config.MAX_POSITIONS // 2,  # Half positions
            max_margin=self.config.MAX_MARGIN_USAGE * 0.5,  # Half margin
            regime=MarketRegime.SIDEWAYS,  # Assume sideways
            regime_confidence=regime_confidence
        )
