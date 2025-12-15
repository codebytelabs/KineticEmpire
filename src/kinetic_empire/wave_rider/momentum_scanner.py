"""Momentum Scanner for Wave Rider.

Scans all futures pairs and ranks them by momentum score:
- Fetches all USDT-margined futures tickers
- Calculates volume ratio (current / 20-period average)
- Calculates momentum score (volume_ratio * abs(price_change_pct))
- Returns top N movers sorted by momentum score
"""

from typing import List, Dict, Optional, Protocol
from .models import MoverData, SpikeClassification, WaveRiderConfig
from .volume_spike_detector import VolumeSpikeDetector


class TickerData(Protocol):
    """Protocol for ticker data from exchange."""
    symbol: str
    last_price: float
    price_change_percent: float
    quote_volume: float  # 24h volume in quote currency (USDT)


class MomentumScanner:
    """Scans all futures pairs and ranks by momentum score.
    
    The momentum score is calculated as:
        momentum_score = volume_ratio * abs(price_change_pct)
    
    This captures both volume interest and price movement.
    """
    
    def __init__(
        self,
        config: Optional[WaveRiderConfig] = None,
        volume_history: Optional[Dict[str, List[float]]] = None,
    ):
        """Initialize the momentum scanner.
        
        Args:
            config: Wave Rider configuration
            volume_history: Optional pre-loaded volume history for testing
        """
        self.config = config or WaveRiderConfig()
        self.spike_detector = VolumeSpikeDetector()
        # Volume history: symbol -> list of last 20 volume readings
        self._volume_history: Dict[str, List[float]] = volume_history or {}
    
    def scan_all_futures(self, tickers: List[Dict]) -> List[MoverData]:
        """Fetch all USDT futures tickers and calculate momentum scores.
        
        Args:
            tickers: List of ticker dicts with keys:
                - symbol: str
                - lastPrice: float (or last_price)
                - priceChangePercent: float (or price_change_percent)
                - quoteVolume: float (or quote_volume) - 24h volume
                - volume: float - current period volume (optional)
        
        Returns:
            List of MoverData for all valid tickers
        """
        movers = []
        
        for ticker in tickers:
            # Extract data with flexible key names
            symbol = ticker.get("symbol", "")
            
            # Skip non-USDT pairs
            if not symbol.endswith("USDT"):
                continue
            
            price = float(ticker.get("lastPrice", ticker.get("last_price", 0)))
            price_change_pct = float(ticker.get("priceChangePercent", ticker.get("price_change_percent", 0)))
            volume_24h = float(ticker.get("quoteVolume", ticker.get("quote_volume", 0)))
            current_volume = float(ticker.get("volume", volume_24h / 24))  # Estimate if not provided
            
            # Skip invalid data
            if price <= 0 or volume_24h <= 0:
                continue
            
            # Calculate volume ratio
            volume_ratio = self.calculate_volume_ratio(symbol, current_volume)
            
            # Calculate momentum score
            momentum_score = self.calculate_momentum_score(volume_ratio, price_change_pct)
            
            # Classify spike
            _, spike_classification = self.spike_detector.detect_spike(volume_ratio)
            
            mover = MoverData(
                symbol=symbol,
                price=price,
                price_change_pct=price_change_pct,
                volume_24h=volume_24h,
                volume_ratio=volume_ratio,
                momentum_score=momentum_score,
                spike_classification=spike_classification,
            )
            movers.append(mover)
        
        return movers
    
    def get_top_movers(
        self,
        tickers: List[Dict],
        limit: Optional[int] = None,
    ) -> List[MoverData]:
        """Return top N symbols sorted by momentum_score descending.
        
        Property 2: Top Movers Sorting
        The list SHALL be sorted in descending order by momentum_score
        and contain at most the specified limit.
        
        Args:
            tickers: List of ticker dicts from exchange
            limit: Maximum number of movers to return (default from config)
        
        Returns:
            List of top MoverData sorted by momentum_score descending
        """
        limit = limit or self.config.top_movers_limit
        
        # Get all movers
        all_movers = self.scan_all_futures(tickers)
        
        # Filter by minimum 24h volume
        filtered = [
            m for m in all_movers
            if m.volume_24h >= self.config.min_24h_volume
        ]
        
        # Sort by momentum score descending
        sorted_movers = sorted(filtered, key=lambda m: m.momentum_score, reverse=True)
        
        # Return top N
        return sorted_movers[:limit]
    
    def calculate_volume_ratio(self, symbol: str, current_volume: float) -> float:
        """Calculate volume ratio vs 20-period average.
        
        Args:
            symbol: Trading pair symbol
            current_volume: Current period volume
        
        Returns:
            Volume ratio (current / 20-period average)
        """
        # Get or initialize volume history
        if symbol not in self._volume_history:
            self._volume_history[symbol] = []
        
        history = self._volume_history[symbol]
        
        # Add current volume to history
        history.append(current_volume)
        
        # Keep only last 20 periods
        if len(history) > 20:
            history.pop(0)
        
        # Calculate average (need at least 1 reading)
        if len(history) < 2:
            # Not enough history, assume ratio of 1.0
            return 1.0
        
        # Average of previous readings (excluding current)
        avg_volume = sum(history[:-1]) / len(history[:-1])
        
        if avg_volume <= 0:
            return 1.0
        
        return current_volume / avg_volume
    
    def calculate_momentum_score(self, volume_ratio: float, price_change_pct: float) -> float:
        """Calculate momentum score.
        
        Property 1: Momentum Score Calculation
        momentum_score = volume_ratio * abs(price_change_pct)
        
        Args:
            volume_ratio: Current volume / 20-period average
            price_change_pct: Price change percentage
        
        Returns:
            Momentum score
        """
        return volume_ratio * abs(price_change_pct)
    
    def update_volume_history(self, symbol: str, volume: float) -> None:
        """Update volume history for a symbol.
        
        Args:
            symbol: Trading pair symbol
            volume: Volume reading to add
        """
        if symbol not in self._volume_history:
            self._volume_history[symbol] = []
        
        self._volume_history[symbol].append(volume)
        
        # Keep only last 20
        if len(self._volume_history[symbol]) > 20:
            self._volume_history[symbol].pop(0)
    
    def clear_history(self) -> None:
        """Clear all volume history."""
        self._volume_history.clear()
