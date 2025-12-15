"""Wave Rider Position Sizer.

Calculates position size and leverage based on signal strength:
- Tier 1 (2.0-3.0 volume ratio): 5% size, 3x leverage
- Tier 2 (3.0-5.0 volume ratio): 7% size, 5x leverage
- Tier 3 (5.0+ volume ratio): 10% size, 7x leverage
- Alignment bonus: +1x leverage if score=100 (max 10x)
- Loss protection: 50% size reduction after 2 consecutive losses
"""

from dataclasses import dataclass
from typing import Tuple, Optional
from .models import WaveRiderConfig


@dataclass
class PositionSizeResult:
    """Result of position size calculation."""
    size_pct: float  # Position size as percentage (0.05 = 5%)
    leverage: int  # Leverage multiplier
    size_usd: float  # Position size in USD
    tier: str  # "tier1", "tier2", "tier3"
    is_reduced: bool  # Whether size was reduced due to losses
    is_capped: bool  # Whether size was capped due to exposure limit


class WaveRiderPositionSizer:
    """Calculates position size and leverage based on signal strength.
    
    Property 8: Position Size and Leverage Tiers
    - If 2.0 <= volume_ratio < 3.0: size=5%, leverage=3x
    - If 3.0 <= volume_ratio < 5.0: size=7%, leverage=5x
    - If volume_ratio >= 5.0: size=10%, leverage=7x
    
    Property 9: Alignment Leverage Bonus
    - If alignment_score == 100: leverage += 1 (max 10x)
    
    Property 10: Loss Protection Size Reduction
    - If consecutive_losses > 2: size *= 0.5
    """
    
    # Volume ratio tiers: (min, max, size_pct, leverage)
    TIER_1 = (2.0, 3.0, 0.05, 3)   # Normal spike
    TIER_2 = (3.0, 5.0, 0.07, 5)   # Strong spike
    TIER_3 = (5.0, float('inf'), 0.10, 7)  # Extreme spike
    
    MAX_LEVERAGE = 10
    LOSS_PROTECTION_THRESHOLD = 2  # Reduce after 2 losses
    LOSS_PROTECTION_MULTIPLIER = 0.5  # 50% reduction
    
    def __init__(self, config: Optional[WaveRiderConfig] = None):
        """Initialize the position sizer.
        
        Args:
            config: Wave Rider configuration
        """
        self.config = config or WaveRiderConfig()
    
    def calculate(
        self,
        volume_ratio: float,
        alignment_score: int,
        consecutive_losses: int,
        available_capital: float,
        current_exposure: float,
    ) -> PositionSizeResult:
        """Calculate position size and leverage.
        
        Args:
            volume_ratio: Volume spike ratio
            alignment_score: MTF alignment score (40/70/100)
            consecutive_losses: Number of consecutive losses
            available_capital: Available capital in USD
            current_exposure: Current portfolio exposure (0.0-1.0)
        
        Returns:
            PositionSizeResult with size, leverage, and metadata
        """
        # Get base size and leverage from tier
        size_pct, leverage, tier = self._get_tier_params(volume_ratio)
        
        # Apply alignment bonus to leverage
        if alignment_score == 100:
            leverage = min(leverage + 1, self.MAX_LEVERAGE)
        
        # Apply loss protection
        is_reduced = False
        if consecutive_losses > self.LOSS_PROTECTION_THRESHOLD:
            size_pct *= self.LOSS_PROTECTION_MULTIPLIER
            is_reduced = True
        
        # Apply exposure cap
        is_capped = False
        max_new_exposure = self.config.max_exposure - current_exposure
        if max_new_exposure <= 0:
            # No room for new positions
            return PositionSizeResult(
                size_pct=0.0,
                leverage=0,
                size_usd=0.0,
                tier=tier,
                is_reduced=is_reduced,
                is_capped=True,
            )
        
        if size_pct > max_new_exposure:
            size_pct = max_new_exposure
            is_capped = True
        
        # Calculate USD size
        size_usd = available_capital * size_pct
        
        return PositionSizeResult(
            size_pct=size_pct,
            leverage=leverage,
            size_usd=size_usd,
            tier=tier,
            is_reduced=is_reduced,
            is_capped=is_capped,
        )
    
    def _get_tier_params(self, volume_ratio: float) -> Tuple[float, int, str]:
        """Get position parameters based on volume ratio tier.
        
        Args:
            volume_ratio: Volume spike ratio
        
        Returns:
            Tuple of (size_pct, leverage, tier_name)
        """
        if volume_ratio >= self.TIER_3[0]:
            return self.TIER_3[2], self.TIER_3[3], "tier3"
        elif volume_ratio >= self.TIER_2[0]:
            return self.TIER_2[2], self.TIER_2[3], "tier2"
        elif volume_ratio >= self.TIER_1[0]:
            return self.TIER_1[2], self.TIER_1[3], "tier1"
        else:
            # Below minimum threshold - shouldn't happen in normal flow
            return 0.0, 0, "none"
    
    def get_tier_for_ratio(self, volume_ratio: float) -> str:
        """Get tier name for a volume ratio.
        
        Args:
            volume_ratio: Volume spike ratio
        
        Returns:
            Tier name ("tier1", "tier2", "tier3", or "none")
        """
        _, _, tier = self._get_tier_params(volume_ratio)
        return tier
    
    def get_base_size_pct(self, volume_ratio: float) -> float:
        """Get base position size percentage for a volume ratio.
        
        Args:
            volume_ratio: Volume spike ratio
        
        Returns:
            Base position size as decimal (0.05 = 5%)
        """
        size_pct, _, _ = self._get_tier_params(volume_ratio)
        return size_pct
    
    def get_base_leverage(self, volume_ratio: float) -> int:
        """Get base leverage for a volume ratio.
        
        Args:
            volume_ratio: Volume spike ratio
        
        Returns:
            Base leverage multiplier
        """
        _, leverage, _ = self._get_tier_params(volume_ratio)
        return leverage
