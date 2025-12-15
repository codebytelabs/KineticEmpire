"""Capital Allocator for Unified Trading System.

Manages capital distribution between trading engines based on configuration.
"""

from dataclasses import dataclass
from typing import Dict, Optional

from .config import UnifiedConfig, ConfigValidationError


@dataclass
class CapitalAllocation:
    """Capital allocation for a single engine."""
    engine_name: str
    allocated_pct: float
    allocated_usd: float
    current_exposure_usd: float
    available_usd: float


class CapitalAllocator:
    """Allocates portfolio capital between engines.
    
    Validates that total allocation doesn't exceed 100% and handles
    reallocation when engines are disabled.
    """
    
    def __init__(self, config: UnifiedConfig):
        """Initialize capital allocator.
        
        Args:
            config: Unified configuration with allocation percentages.
            
        Raises:
            ConfigValidationError: If total allocation exceeds 100%.
        """
        self.config = config
        self._exposure: Dict[str, float] = {}
        self._validate_allocation()
    
    def _validate_allocation(self) -> None:
        """Ensure total allocation <= 100%.
        
        Raises:
            ConfigValidationError: If validation fails.
        """
        total = 0.0
        if self.config.spot_enabled:
            total += self.config.spot_capital_pct
        if self.config.futures_enabled:
            total += self.config.futures_capital_pct
        
        if total > 100.0:
            raise ConfigValidationError(
                f"Total capital allocation ({total}%) exceeds 100%. "
                f"spot={self.config.spot_capital_pct}%, futures={self.config.futures_capital_pct}%"
            )
    
    def get_allocation(self, engine_name: str, total_portfolio: float) -> CapitalAllocation:
        """Get capital allocation for an engine.
        
        Args:
            engine_name: Name of the engine ("spot" or "futures").
            total_portfolio: Total portfolio value in USD.
            
        Returns:
            CapitalAllocation with calculated values.
        """
        # Get base allocation percentage
        if engine_name == "spot":
            base_pct = self.config.spot_capital_pct if self.config.spot_enabled else 0.0
        elif engine_name == "futures":
            base_pct = self.config.futures_capital_pct if self.config.futures_enabled else 0.0
        else:
            base_pct = 0.0
        
        # Handle reallocation when one engine is disabled
        effective_pct = self._get_effective_allocation(engine_name, base_pct)
        
        allocated_usd = total_portfolio * (effective_pct / 100.0)
        current_exposure = self._exposure.get(engine_name, 0.0)
        available = max(0.0, allocated_usd - current_exposure)
        
        return CapitalAllocation(
            engine_name=engine_name,
            allocated_pct=effective_pct,
            allocated_usd=allocated_usd,
            current_exposure_usd=current_exposure,
            available_usd=available,
        )
    
    def _get_effective_allocation(self, engine_name: str, base_pct: float) -> float:
        """Get effective allocation considering disabled engines.
        
        When one engine is disabled, its allocation becomes available
        to the other engine.
        
        Args:
            engine_name: Name of the engine.
            base_pct: Base allocation percentage from config.
            
        Returns:
            Effective allocation percentage.
        """
        if base_pct == 0.0:
            return 0.0
        
        # If only one engine is enabled, it gets 100%
        spot_enabled = self.config.spot_enabled
        futures_enabled = self.config.futures_enabled
        
        if engine_name == "spot" and spot_enabled and not futures_enabled:
            return 100.0
        if engine_name == "futures" and futures_enabled and not spot_enabled:
            return 100.0
        
        return base_pct
    
    def update_exposure(self, engine_name: str, exposure_usd: float) -> None:
        """Update current exposure for an engine.
        
        Args:
            engine_name: Name of the engine.
            exposure_usd: Current exposure in USD.
        """
        self._exposure[engine_name] = exposure_usd
    
    def get_total_exposure(self) -> float:
        """Get total exposure across all engines.
        
        Returns:
            Total exposure in USD.
        """
        return sum(self._exposure.values())
    
    def can_allocate(self, engine_name: str, amount_usd: float, total_portfolio: float) -> bool:
        """Check if an allocation is possible.
        
        Args:
            engine_name: Name of the engine.
            amount_usd: Amount to allocate in USD.
            total_portfolio: Total portfolio value in USD.
            
        Returns:
            True if allocation is possible.
        """
        allocation = self.get_allocation(engine_name, total_portfolio)
        return amount_usd <= allocation.available_usd
