"""Flash crash protection module.

Detects and responds to extreme market conditions to prevent catastrophic losses.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from kinetic_empire.models import PricePoint


@dataclass
class ProtectionConfig:
    """Configuration for flash crash protection."""
    crash_threshold_pct: float = 5.0  # Price drop % to trigger protection
    crash_window_hours: int = 1       # Time window for crash detection
    recovery_hours: int = 4           # Hours above EMA for recovery
    emergency_max_trades: int = 3     # Max trades during crash


class FlashCrashProtection:
    """Detects and responds to flash crashes.
    
    Monitors BTC price for rapid drops and reduces exposure during
    extreme volatility to protect capital.
    """

    def __init__(self, config: Optional[ProtectionConfig] = None):
        """Initialize flash crash protection.
        
        Args:
            config: Protection configuration. Uses defaults if None.
        """
        self.config = config or ProtectionConfig()
        self._crash_detected = False
        self._crash_detection_time: Optional[datetime] = None

    def detect_flash_crash(
        self,
        btc_prices: list[PricePoint],
        threshold_pct: Optional[float] = None,
        window_hours: Optional[int] = None
    ) -> bool:
        """Detect flash crash from price history.
        
        Flash crash occurs when BTC drops > threshold_pct within window_hours.
        
        Args:
            btc_prices: List of BTC price points (sorted by timestamp)
            threshold_pct: Drop threshold percentage (default from config)
            window_hours: Time window in hours (default from config)
            
        Returns:
            True if flash crash detected
        """
        if not btc_prices or len(btc_prices) < 2:
            return False
        
        threshold_pct = threshold_pct if threshold_pct is not None else self.config.crash_threshold_pct
        window_hours = window_hours if window_hours is not None else self.config.crash_window_hours
        
        # Get most recent price
        latest = btc_prices[-1]
        cutoff_time = latest.timestamp - timedelta(hours=window_hours)
        
        # Find highest price within window
        prices_in_window = [
            p for p in btc_prices
            if p.timestamp >= cutoff_time
        ]
        
        if not prices_in_window:
            return False
        
        highest_price = max(p.price for p in prices_in_window)
        current_price = latest.price
        
        # Calculate drop percentage
        if highest_price == 0:
            return False
        
        drop_pct = ((highest_price - current_price) / highest_price) * 100
        
        is_crash = drop_pct > threshold_pct
        
        if is_crash and not self._crash_detected:
            self._crash_detected = True
            self._crash_detection_time = latest.timestamp
        
        return is_crash

    def is_market_stable(
        self,
        btc_prices: list[PricePoint],
        btc_ema50: float,
        recovery_hours: Optional[int] = None
    ) -> bool:
        """Check if market has stabilized after crash.
        
        Market is stable when BTC > EMA50 for recovery_hours consecutive hours.
        
        Args:
            btc_prices: List of BTC price points (sorted by timestamp)
            btc_ema50: BTC EMA50 value
            recovery_hours: Required hours above EMA (default from config)
            
        Returns:
            True if market is stable
        """
        if not btc_prices:
            return False
        
        recovery_hours = recovery_hours if recovery_hours is not None else self.config.recovery_hours
        
        # Get most recent prices
        latest = btc_prices[-1]
        cutoff_time = latest.timestamp - timedelta(hours=recovery_hours)
        
        # Get prices in recovery window
        prices_in_window = [
            p for p in btc_prices
            if p.timestamp >= cutoff_time
        ]
        
        if len(prices_in_window) < recovery_hours:
            return False
        
        # Check if all prices in window are above EMA50
        all_above_ema = all(p.price > btc_ema50 for p in prices_in_window)
        
        if all_above_ema and self._crash_detected:
            self._crash_detected = False
            self._crash_detection_time = None
        
        return all_above_ema

    def get_emergency_max_trades(self) -> int:
        """Get maximum trades during flash crash.
        
        Returns:
            Emergency max trades (3)
        """
        return self.config.emergency_max_trades

    def is_crash_active(self) -> bool:
        """Check if crash protection is currently active.
        
        Returns:
            True if crash is detected and not recovered
        """
        return self._crash_detected

    def reset(self) -> None:
        """Reset crash detection state."""
        self._crash_detected = False
        self._crash_detection_time = None

    def get_max_trades(
        self,
        btc_prices: list[PricePoint],
        btc_ema50: float,
        normal_max_trades: int
    ) -> int:
        """Get max trades considering flash crash protection.
        
        Args:
            btc_prices: List of BTC price points
            btc_ema50: BTC EMA50 value
            normal_max_trades: Normal max trades from regime
            
        Returns:
            Max trades (emergency limit if crash, normal otherwise)
        """
        # Check for flash crash
        if self.detect_flash_crash(btc_prices):
            return self.get_emergency_max_trades()
        
        # Check if recovered
        if self.is_market_stable(btc_prices, btc_ema50):
            return normal_max_trades
        
        # If crash was detected but not yet recovered
        if self.is_crash_active():
            return self.get_emergency_max_trades()
        
        return normal_max_trades
