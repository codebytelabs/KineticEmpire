"""Signal Quality Gate Configuration.

Defines all configuration parameters for the Signal Quality Gate system.
"""

from dataclasses import dataclass


@dataclass
class QualityGateConfig:
    """Configuration for the Signal Quality Gate system.
    
    Attributes:
        min_confidence: Minimum confidence to accept signal (below = reject)
        medium_confidence: Threshold for medium tier (50-70 = 0.5x size)
        
        contradiction_threshold_pct: Max price change against signal direction
        overbought_rsi: RSI threshold for overbought (reject LONG above this)
        oversold_rsi: RSI threshold for oversold (reject SHORT below this)
        
        max_consecutive_losses: Losses before blacklisting symbol
        loss_window_minutes: Time window to count consecutive losses
        blacklist_duration_minutes: How long to blacklist a symbol
        
        trending_stop_pct: Stop loss % in trending markets
        sideways_stop_pct: Stop loss % in sideways markets
        choppy_stop_pct: Stop loss % in choppy markets
        
        max_leverage_favorable: Max leverage in favorable conditions
        max_leverage_unfavorable: Max leverage in unfavorable conditions
        favorable_confidence_threshold: Confidence needed for favorable leverage
        
        micro_alignment_bonus: Points added when 1M/5M align with signal
        
        volume_surge_threshold: Volume ratio to detect surge (2.0 = 200%)
        breakout_bonus: Points added for confirmed breakout
        
        disable_rsi_extreme_filter: Disable RSI overbought/oversold rejection
        require_both_micro_contradict: Require BOTH 1M and 5M to contradict (not just one)
    """
    # Confidence thresholds - RELAXED: lowered to allow more trades
    min_confidence: int = 40
    medium_confidence: int = 60
    
    # Momentum validation - RELAXED: wider RSI bands
    contradiction_threshold_pct: float = 0.5
    overbought_rsi: float = 80.0  # Was 70, now 80 - allow more LONG entries
    oversold_rsi: float = 20.0   # Was 30, now 20 - allow more SHORT entries
    
    # NEW: Option to completely disable RSI extreme filter
    # In strong trends, RSI can stay extreme for extended periods
    disable_rsi_extreme_filter: bool = False
    
    # Blacklist settings - AGGRESSIVE: blacklist after 1 loss, longer duration
    # Per profitable-trading-overhaul spec: faster blacklist trigger
    max_consecutive_losses: int = 1  # Blacklist after 1 loss (was 2)
    loss_window_minutes: int = 30    # 30-minute window (was 60)
    blacklist_duration_minutes: int = 60  # 60-minute blacklist (was 30)
    
    # Micro-timeframe requirement - RELAXED: only reject if BOTH contradict
    require_micro_alignment_unfavorable: bool = True
    require_both_micro_contradict: bool = True  # NEW: need both 1M AND 5M against signal
    
    # HIGH-QUALITY BYPASS: DISABLED - strict regime enforcement
    # No directional trades in CHOPPY/SIDEWAYS markets regardless of confidence
    high_quality_bypass_enabled: bool = False  # DISABLED per profitable-trading-overhaul spec
    high_quality_enhanced_threshold: int = 90  # Enhanced score >= this (unused when bypass disabled)
    high_quality_cash_cow_threshold: int = 80  # Cash Cow score >= this (unused when bypass disabled)
    high_quality_size_multiplier: float = 0.5  # Use smaller size for sideways trades (unused when bypass disabled)
    
    # Risk settings - stop loss percentages
    trending_stop_pct: float = 3.0
    sideways_stop_pct: float = 4.0
    choppy_stop_pct: float = 5.0
    
    # Leverage caps
    max_leverage_favorable: int = 20
    max_leverage_unfavorable: int = 10
    favorable_confidence_threshold: int = 70
    
    # Micro-timeframe settings
    micro_alignment_bonus: int = 10
    
    # Breakout settings
    volume_surge_threshold: float = 2.0
    breakout_bonus: int = 15


# Default configuration instance
DEFAULT_QUALITY_GATE_CONFIG = QualityGateConfig()
