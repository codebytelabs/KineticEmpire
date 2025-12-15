"""Scanner module for dynamic pairlist filtering.

Implements the filter pipeline for selecting high-quality trading pairs
based on volume, spread, price, volatility, and performance criteria.
"""

import re
from dataclasses import dataclass, field
from typing import Optional

from kinetic_empire.models import PairData


@dataclass
class ScannerConfig:
    """Configuration for the scanner module."""
    blacklist_patterns: list[str] = field(default_factory=lambda: [
        r"BNB/.*", r".*DOWN/.*", r".*UP/.*", r"USDC/.*"
    ])
    refresh_interval: int = 1800  # 30 minutes
    max_pairs: int = 20
    min_volume_rank: int = 70
    max_spread: float = 0.005
    min_price: float = 0.001
    volatility_min: float = 0.02
    volatility_max: float = 0.50


def is_blacklisted(pair: str, patterns: list[re.Pattern]) -> bool:
    """Check if a pair matches any blacklist pattern.
    
    Args:
        pair: Trading pair symbol (e.g., "BTC/USDT")
        patterns: List of compiled regex patterns
        
    Returns:
        True if pair matches any blacklist pattern, False otherwise
    """
    return any(pattern.match(pair) for pattern in patterns)


def filter_by_spread(pairs: list[PairData], max_spread: float = 0.005) -> list[PairData]:
    """Filter pairs by maximum spread ratio.
    
    Args:
        pairs: List of pair data to filter
        max_spread: Maximum allowed spread ratio (default 0.5%)
        
    Returns:
        Pairs with spread_ratio <= max_spread
    """
    return [p for p in pairs if p.spread_ratio <= max_spread]


def filter_by_price(pairs: list[PairData], min_price: float = 0.001) -> list[PairData]:
    """Filter pairs by minimum price.
    
    Args:
        pairs: List of pair data to filter
        min_price: Minimum allowed price (default $0.001)
        
    Returns:
        Pairs with price >= min_price
    """
    return [p for p in pairs if p.price >= min_price]


def filter_by_volatility(
    pairs: list[PairData],
    min_vol: float = 0.02,
    max_vol: float = 0.50
) -> list[PairData]:
    """Filter pairs by volatility range.
    
    Args:
        pairs: List of pair data to filter
        min_vol: Minimum volatility (default 2%)
        max_vol: Maximum volatility (default 50%)
        
    Returns:
        Pairs with volatility in [min_vol, max_vol]
    """
    return [p for p in pairs if min_vol <= p.volatility <= max_vol]


def filter_by_performance(pairs: list[PairData], min_return: float = 0.0) -> list[PairData]:
    """Filter pairs by recent performance.
    
    Args:
        pairs: List of pair data to filter
        min_return: Minimum 60-minute return (default 0%)
        
    Returns:
        Pairs with return_60m > min_return
    """
    return [p for p in pairs if p.return_60m > min_return]



class ScannerModule:
    """Scanner module for filtering and selecting trading pairs.
    
    Implements a filter pipeline that:
    1. Removes blacklisted pairs (regex matching)
    2. Selects top pairs by quote volume
    3. Filters by spread ratio (<= 0.5%)
    4. Filters by minimum price (>= $0.001)
    5. Filters by volatility range (2% - 50%)
    6. Filters by recent performance (> 0% in 60 min)
    7. Sorts by volatility (descending) and limits to max_pairs
    """

    def __init__(self, config: Optional[ScannerConfig] = None):
        """Initialize scanner with configuration.
        
        Args:
            config: Scanner configuration. Uses defaults if None.
        """
        self.config = config or ScannerConfig()
        self._compiled_patterns: list[re.Pattern] = []
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile blacklist regex patterns."""
        self._compiled_patterns = [
            re.compile(p) for p in self.config.blacklist_patterns
        ]

    def is_blacklisted(self, pair: str) -> bool:
        """Check if a pair is blacklisted.
        
        Args:
            pair: Trading pair symbol
            
        Returns:
            True if pair matches any blacklist pattern
        """
        return is_blacklisted(pair, self._compiled_patterns)

    def apply_filters(self, pairs: list[PairData]) -> list[PairData]:
        """Apply the complete filter pipeline to pairs.
        
        Pipeline order:
        1. Remove blacklisted pairs
        2. Filter by spread
        3. Filter by price
        4. Filter by volatility
        5. Filter by performance
        
        Args:
            pairs: List of pair data to filter
            
        Returns:
            Filtered list of pairs passing all criteria
        """
        # Step 1: Remove blacklisted pairs
        filtered = [p for p in pairs if not self.is_blacklisted(p.symbol)]
        
        # Step 2: Filter by spread
        filtered = filter_by_spread(filtered, self.config.max_spread)
        
        # Step 3: Filter by price
        filtered = filter_by_price(filtered, self.config.min_price)
        
        # Step 4: Filter by volatility
        filtered = filter_by_volatility(
            filtered,
            self.config.volatility_min,
            self.config.volatility_max
        )
        
        # Step 5: Filter by performance
        filtered = filter_by_performance(filtered, min_return=0.0)
        
        return filtered

    def select_top_by_volume(
        self,
        pairs: list[PairData],
        limit: int = 70
    ) -> list[PairData]:
        """Select top pairs by quote volume.
        
        Args:
            pairs: List of pair data
            limit: Maximum number of pairs to return
            
        Returns:
            Top pairs sorted by quote_volume descending
        """
        sorted_pairs = sorted(pairs, key=lambda p: p.quote_volume, reverse=True)
        return sorted_pairs[:limit]

    def sort_by_volatility(self, pairs: list[PairData]) -> list[PairData]:
        """Sort pairs by volatility in descending order.
        
        Args:
            pairs: List of pair data
            
        Returns:
            Pairs sorted by volatility (high to low)
        """
        return sorted(pairs, key=lambda p: p.volatility, reverse=True)

    def scan(self, pairs: list[PairData]) -> list[str]:
        """Execute the complete scan pipeline.
        
        Pipeline:
        1. Select top 70 by volume
        2. Apply all filters (blacklist, spread, price, volatility, performance)
        3. Sort by volatility descending
        4. Return top max_pairs symbols
        
        Args:
            pairs: List of all available pair data from exchange
            
        Returns:
            List of top pair symbols (max 20 by default)
        """
        # Step 1: Select top by volume
        top_volume = self.select_top_by_volume(pairs, self.config.min_volume_rank)
        
        # Step 2: Apply filter pipeline
        filtered = self.apply_filters(top_volume)
        
        # Step 3: Sort by volatility
        sorted_pairs = self.sort_by_volatility(filtered)
        
        # Step 4: Limit to max_pairs and return symbols
        final_pairs = sorted_pairs[:self.config.max_pairs]
        
        return [p.symbol for p in final_pairs]

    def scan_with_data(self, pairs: list[PairData]) -> list[PairData]:
        """Execute scan pipeline and return full PairData objects.
        
        Same as scan() but returns PairData objects instead of symbols.
        
        Args:
            pairs: List of all available pair data from exchange
            
        Returns:
            List of top PairData objects (max 20 by default)
        """
        # Step 1: Select top by volume
        top_volume = self.select_top_by_volume(pairs, self.config.min_volume_rank)
        
        # Step 2: Apply filter pipeline
        filtered = self.apply_filters(top_volume)
        
        # Step 3: Sort by volatility
        sorted_pairs = self.sort_by_volatility(filtered)
        
        # Step 4: Limit to max_pairs
        return sorted_pairs[:self.config.max_pairs]
