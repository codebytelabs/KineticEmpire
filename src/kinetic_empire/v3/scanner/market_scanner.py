"""Market Scanner for Kinetic Empire v3.0.

Scans USDT/USDC markets for high-potential trading opportunities.
"""

import asyncio
import logging
from typing import List, Optional
from datetime import datetime

from src.kinetic_empire.v3.core.models import Ticker

logger = logging.getLogger(__name__)


class MarketScanner:
    """Scans market for high-potential trading opportunities.
    
    Filters markets by:
    - Volume spike (>1.5x 20-period average)
    - Price momentum (|24h change| > 1%)
    - Ranks by combined score
    """

    def __init__(
        self,
        volume_threshold: float = 1.5,
        momentum_threshold: float = 1.0,
        max_opportunities: int = 50,
        base_currencies: Optional[List[str]] = None,
        excluded_symbols: Optional[List[str]] = None,
    ):
        """Initialize scanner with configuration.
        
        Args:
            volume_threshold: Minimum volume ratio (current/average)
            momentum_threshold: Minimum |24h change| percentage
            max_opportunities: Maximum opportunities to return
            base_currencies: Quote currencies to scan (default: USDT, USDC)
            excluded_symbols: Symbols to exclude from scanning
        """
        self.volume_threshold = volume_threshold
        self.momentum_threshold = momentum_threshold
        self.max_opportunities = max_opportunities
        self.base_currencies = base_currencies or ["USDT", "USDC"]
        self.excluded_symbols = excluded_symbols or ["USDCUSDT", "BUSDUSDT"]
        
        self._last_scan_time: Optional[datetime] = None
        self._last_opportunities: List[str] = []

    def filter_by_volume(self, tickers: List[Ticker]) -> List[Ticker]:
        """Filter tickers by volume spike.
        
        Returns tickers where current volume > threshold × average volume.
        
        Args:
            tickers: List of ticker data
            
        Returns:
            Filtered list of tickers with volume spikes
        """
        filtered = []
        for ticker in tickers:
            # Calculate volume ratio
            if ticker.volume_24h > 0:
                # Use high_24h - low_24h as proxy for volatility if no avg available
                # In real implementation, this would use 20-period average
                volume_ratio = self._calculate_volume_ratio(ticker)
                if volume_ratio >= self.volume_threshold:
                    filtered.append(ticker)
        
        return filtered

    def filter_by_momentum(self, tickers: List[Ticker]) -> List[Ticker]:
        """Filter tickers by price momentum.
        
        Returns tickers where |24h change| > threshold.
        
        Args:
            tickers: List of ticker data
            
        Returns:
            Filtered list of tickers with sufficient momentum
        """
        filtered = []
        for ticker in tickers:
            if abs(ticker.change_24h) >= self.momentum_threshold:
                filtered.append(ticker)
        
        return filtered

    def rank_opportunities(self, tickers: List[Ticker]) -> List[str]:
        """Rank opportunities by combined score.
        
        Score = |momentum| × volume_ratio
        
        Args:
            tickers: List of filtered tickers
            
        Returns:
            List of symbols sorted by score (highest first)
        """
        scored = []
        for ticker in tickers:
            volume_ratio = self._calculate_volume_ratio(ticker)
            score = abs(ticker.change_24h) * volume_ratio
            scored.append((ticker.symbol, score))
        
        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        
        # Return top N symbols
        return [symbol for symbol, _ in scored[:self.max_opportunities]]

    def _calculate_volume_ratio(self, ticker: Ticker) -> float:
        """Calculate volume ratio for a ticker.
        
        In production, this would compare to 20-period average.
        For now, we use a simplified calculation.
        """
        # If ticker has volume data, use it directly
        # This is a placeholder - real implementation would fetch historical data
        if ticker.volume_24h > 0:
            # Assume average volume is roughly proportional to price range
            price_range = ticker.high_24h - ticker.low_24h
            if price_range > 0 and ticker.price > 0:
                volatility = price_range / ticker.price
                # Higher volatility with high volume = higher ratio
                return 1.0 + volatility * 10
        return 1.0

    def _is_valid_symbol(self, symbol: str) -> bool:
        """Check if symbol should be included in scan."""
        # Check if symbol ends with valid base currency
        valid_base = any(symbol.endswith(base) for base in self.base_currencies)
        
        # Check if symbol is excluded
        excluded = symbol in self.excluded_symbols
        
        return valid_base and not excluded

    async def scan(self, tickers: List[Ticker]) -> List[str]:
        """Perform full market scan.
        
        Args:
            tickers: List of all market tickers
            
        Returns:
            List of hot ticker symbols ranked by opportunity score
        """
        start_time = datetime.now()
        logger.debug(f"🔎 Scanner starting with {len(tickers)} tickers")
        
        # Filter to valid symbols
        valid_tickers = [t for t in tickers if self._is_valid_symbol(t.symbol)]
        logger.debug(f"   ✓ Valid symbols (USDT/USDC): {len(valid_tickers)}/{len(tickers)}")
        
        # Apply volume filter
        volume_filtered = self.filter_by_volume(valid_tickers)
        logger.debug(f"   ✓ Volume filter (>{self.volume_threshold}x avg): {len(volume_filtered)} passed")
        if volume_filtered:
            for t in volume_filtered[:3]:
                ratio = self._calculate_volume_ratio(t)
                logger.debug(f"      📊 {t.symbol}: vol_ratio={ratio:.2f}x")
        
        # Apply momentum filter
        momentum_filtered = self.filter_by_momentum(volume_filtered)
        logger.debug(f"   ✓ Momentum filter (>{self.momentum_threshold}%): {len(momentum_filtered)} passed")
        if momentum_filtered:
            for t in momentum_filtered[:3]:
                logger.debug(f"      📈 {t.symbol}: change={t.change_24h:+.2f}%")
        
        # Rank opportunities
        opportunities = self.rank_opportunities(momentum_filtered)
        logger.debug(f"   ✓ Ranked top {len(opportunities)} opportunities")
        
        # Update state
        self._last_scan_time = start_time
        self._last_opportunities = opportunities
        
        scan_duration = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"📡 Scan complete: {len(opportunities)} opportunities in {scan_duration:.3f}s"
        )
        
        if opportunities:
            logger.debug(f"   🎯 Top picks: {', '.join(opportunities[:5])}")
        
        return opportunities

    @property
    def last_scan_time(self) -> Optional[datetime]:
        """Get timestamp of last scan."""
        return self._last_scan_time

    @property
    def last_opportunities(self) -> List[str]:
        """Get results from last scan."""
        return self._last_opportunities.copy()
