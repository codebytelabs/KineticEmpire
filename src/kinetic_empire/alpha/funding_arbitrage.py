"""Funding Rate Arbitrage Strategy - Delta-neutral income from funding payments.

Opens long spot + short perpetual positions to collect funding rate payments
while maintaining zero directional exposure.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from .models import ArbitragePosition, FundingData


@dataclass
class ArbitrageConfig:
    """Configuration for funding rate arbitrage."""
    min_funding_rate: float = 0.0001  # 0.01% per 8h = ~10% annual
    exit_funding_rate: float = 0.00005  # 0.005% per 8h = ~5% annual
    max_positions: int = 5
    position_size_pct: float = 0.08  # 8% of allocation per position
    delta_tolerance: float = 0.01  # 1% delta tolerance


class FundingRateMonitor:
    """Monitors funding rates across perpetual pairs."""
    
    def __init__(self, min_rate: float = 0.0001):
        self.min_rate = min_rate
        self.funding_data: Dict[str, FundingData] = {}
        self.history: Dict[str, List[Tuple[datetime, float]]] = {}
    
    def update_funding_rate(self, pair: str, rate_8h: float, 
                           next_funding_time: datetime) -> FundingData:
        """Update funding rate for a pair."""
        data = FundingData.from_rate(pair, rate_8h, next_funding_time, self.min_rate)
        data.avg_7d_rate = self.calculate_7d_average(pair)
        self.funding_data[pair] = data
        
        # Store in history
        if pair not in self.history:
            self.history[pair] = []
        self.history[pair].append((datetime.now(), rate_8h))
        
        # Trim history to 7 days
        cutoff = datetime.now() - timedelta(days=7)
        self.history[pair] = [(t, r) for t, r in self.history[pair] if t > cutoff]
        
        return data
    
    def calculate_annualized_rate(self, rate_8h: float) -> float:
        """Convert 8-hour rate to annualized."""
        return rate_8h * 3 * 365
    
    def calculate_7d_average(self, pair: str) -> float:
        """Calculate 7-day average funding rate."""
        if pair not in self.history or not self.history[pair]:
            return 0.0
        rates = [r for _, r in self.history[pair]]
        return sum(rates) / len(rates)
    
    def get_opportunities(self) -> List[FundingData]:
        """Get pairs with funding rate above threshold."""
        return [fd for fd in self.funding_data.values() if fd.is_opportunity]
    
    def get_top_opportunities(self, n: int = 10) -> List[FundingData]:
        """Get top N pairs by funding rate."""
        sorted_data = sorted(
            self.funding_data.values(),
            key=lambda x: x.current_rate,
            reverse=True
        )
        return sorted_data[:n]
    
    def is_negative_funding(self, pair: str) -> bool:
        """Check if funding rate is negative (reverse arb opportunity)."""
        data = self.funding_data.get(pair)
        return data is not None and data.current_rate < 0



class FundingArbitrageStrategy:
    """Delta-neutral funding rate arbitrage strategy."""
    
    def __init__(self, config: Optional[ArbitrageConfig] = None):
        self.config = config or ArbitrageConfig()
        self.monitor = FundingRateMonitor(self.config.min_funding_rate)
        self.positions: Dict[str, ArbitragePosition] = {}
    
    def find_opportunities(self, funding_rates: Dict[str, float]) -> List[str]:
        """Find pairs with funding rate above threshold.
        
        Args:
            funding_rates: Dict of pair -> 8h funding rate
            
        Returns:
            List of pairs that are arbitrage opportunities
        """
        opportunities = []
        for pair, rate in funding_rates.items():
            if rate >= self.config.min_funding_rate:
                opportunities.append(pair)
        return sorted(opportunities, key=lambda p: funding_rates[p], reverse=True)
    
    def can_open_position(self) -> bool:
        """Check if we can open a new arbitrage position."""
        return len(self.positions) < self.config.max_positions
    
    def calculate_position_size(self, available_capital: float, 
                                spot_price: float) -> Tuple[float, float]:
        """Calculate position sizes for spot and futures.
        
        Args:
            available_capital: Available capital for this position
            spot_price: Current spot price
            
        Returns:
            Tuple of (spot_size, futures_size)
        """
        position_capital = available_capital * self.config.position_size_pct
        size = position_capital / spot_price
        return size, size  # Equal sizes for delta-neutral
    
    def open_arbitrage(self, pair: str, spot_price: float, futures_price: float,
                      spot_size: float, futures_size: float,
                      funding_rate: float) -> ArbitragePosition:
        """Open a delta-neutral arbitrage position.
        
        Args:
            pair: Trading pair
            spot_price: Spot entry price
            futures_price: Futures entry price
            spot_size: Spot position size
            futures_size: Futures position size
            funding_rate: Current funding rate
            
        Returns:
            ArbitragePosition
        """
        position = ArbitragePosition(
            pair=pair,
            spot_entry_price=spot_price,
            futures_entry_price=futures_price,
            spot_size=spot_size,
            futures_size=futures_size,
            open_time=datetime.now(),
            entry_funding_rate=funding_rate,
        )
        
        self.positions[pair] = position
        return position
    
    def check_exit_conditions(self, pair: str, current_funding: float) -> bool:
        """Check if arbitrage should be closed.
        
        Args:
            pair: Trading pair
            current_funding: Current funding rate
            
        Returns:
            True if should exit
        """
        if pair not in self.positions:
            return False
        
        # Exit if funding drops below threshold
        return current_funding < self.config.exit_funding_rate
    
    def close_arbitrage(self, pair: str, spot_exit_price: float,
                       futures_exit_price: float) -> Optional[float]:
        """Close arbitrage position and calculate profit.
        
        Args:
            pair: Trading pair
            spot_exit_price: Spot exit price
            futures_exit_price: Futures exit price
            
        Returns:
            Total profit or None if position not found
        """
        position = self.positions.pop(pair, None)
        if not position:
            return None
        
        # Spot P&L (long)
        spot_pnl = (spot_exit_price - position.spot_entry_price) * position.spot_size
        
        # Futures P&L (short)
        futures_pnl = (position.futures_entry_price - futures_exit_price) * position.futures_size
        
        # Total = spot + futures + collected funding
        total_pnl = spot_pnl + futures_pnl + position.funding_collected
        
        return total_pnl
    
    def record_funding_payment(self, pair: str, payment: float) -> None:
        """Record a funding payment received."""
        if pair in self.positions:
            self.positions[pair].funding_collected += payment
            self.positions[pair].last_funding_time = datetime.now()
    
    def get_position(self, pair: str) -> Optional[ArbitragePosition]:
        """Get arbitrage position by pair."""
        return self.positions.get(pair)
    
    def get_all_positions(self) -> List[ArbitragePosition]:
        """Get all active arbitrage positions."""
        return list(self.positions.values())
    
    def calculate_expected_daily_return(self, position: ArbitragePosition,
                                        current_rate: float) -> float:
        """Calculate expected daily return from funding.
        
        Args:
            position: Arbitrage position
            current_rate: Current 8h funding rate
            
        Returns:
            Expected daily return in quote currency
        """
        # 3 funding periods per day
        daily_rate = current_rate * 3
        return position.notional_value * daily_rate
