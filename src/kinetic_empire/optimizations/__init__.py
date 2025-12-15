"""Trading Optimizations Module.

High-confidence, low-risk optimizations for the Kinetic Empire trading bot.
These improvements enhance profitability and risk management without breaking
existing functionality.

Tier 1 (Critical): Profit protection and risk reduction
- TrailingOptimizer: Earlier trailing stop activation (1.5% profit)
- PartialProfitTaker: TP1/TP2 partial exits
- HalfKellySizer: Conservative position sizing

Tier 2 (High Value): Entry/exit optimization
- VolumeTieredSizer: Volume-based position sizing
- RegimeAdaptiveStops: Regime-aware stop loss distances
- RSIZoneOptimizer: Regime-specific RSI entry zones

Tier 3 (Enhancement): Additional edge improvements
- DynamicBlacklistManager: Loss-severity-based blacklist duration
- FearGreedAdjuster: Sentiment-based adjustments
- MicroAlignmentBonus: Micro-timeframe alignment rewards
- EntryConfirmationManager: Entry confirmation delay
"""

from .config import (
    OptimizationsConfig,
    TrailingOptConfig,
    PartialProfitConfig,
    VolumeTierConfig,
    RSIZoneConfig,
    EntryConfirmConfig,
)
from .trailing_optimizer import TrailingOptimizer
from .profit_taker import PartialProfitTaker, TPResult
from .half_kelly import HalfKellySizer
from .volume_sizer import VolumeTieredSizer, VolumeTier
from .regime_stops import RegimeAdaptiveStops
from .rsi_zones import RSIZoneOptimizer
from .dynamic_blacklist import DynamicBlacklistManager
from .fg_adjuster import FearGreedAdjuster
from .micro_bonus import MicroAlignmentBonus
from .entry_confirm import EntryConfirmationManager, PendingEntry

__all__ = [
    # Config
    "OptimizationsConfig",
    "TrailingOptConfig",
    "PartialProfitConfig",
    "VolumeTierConfig",
    "RSIZoneConfig",
    "EntryConfirmConfig",
    # Tier 1
    "TrailingOptimizer",
    "PartialProfitTaker",
    "TPResult",
    "HalfKellySizer",
    # Tier 2
    "VolumeTieredSizer",
    "VolumeTier",
    "RegimeAdaptiveStops",
    "RSIZoneOptimizer",
    # Tier 3
    "DynamicBlacklistManager",
    "FearGreedAdjuster",
    "MicroAlignmentBonus",
    "EntryConfirmationManager",
    "PendingEntry",
]
