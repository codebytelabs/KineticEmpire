"""Advanced Portfolio Management for Futures Grid Trading.

Implements Kelly Criterion, risk parity, correlation analysis,
and dynamic position sizing for optimal risk-adjusted returns.
"""
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from .client import BinanceFuturesClient
from .scanner import PairScore

logger = logging.getLogger(__name__)


@dataclass
class PositionSize:
    """Calculated position size for a pair."""
    symbol: str
    usdt_amount: float
    leverage: int
    quantity: float
    risk_amount: float
    kelly_fraction: float
    confidence_multiplier: float


@dataclass
class RiskMetrics:
    """Portfolio risk metrics."""
    total_exposure: float
    max_single_risk: float
    portfolio_var: float  # Value at Risk
    sharpe_ratio: float
    max_drawdown: float
    correlation_risk: float


class AdvancedPortfolioManager:
    """Advanced portfolio management with Kelly Criterion and risk optimization."""
    
    def __init__(self, client: BinanceFuturesClient):
        self.client = client
        
        # Risk parameters
        self.max_portfolio_risk = 0.15  # 15% max portfolio risk
        self.max_single_position_risk = 0.03  # 3% max single position risk
        self.max_leverage = 5  # Conservative max leverage
        self.min_leverage = 2  # Minimum leverage for efficiency
        
        # Kelly parameters
        self.kelly_multiplier = 0.25  # Use 25% of full Kelly (conservative)
        self.min_kelly_fraction = 0.01  # Minimum 1% allocation
        self.max_kelly_fraction = 0.20  # Maximum 20% allocation
        
        # Performance tracking
        self.historical_returns: Dict[str, List[float]] = {}
        self.win_rates: Dict[str, float] = {}
        self.avg_win_loss_ratio: Dict[str, float] = {}
    
    def calculate_kelly_fraction(self, pair_score: PairScore, 
                                historical_performance: Optional[Dict] = None) -> float:
        """Calculate Kelly Criterion fraction for optimal position sizing.
        
        Kelly Formula: f* = (bp - q) / b
        where:
        - b = odds (avg_win / avg_loss)
        - p = probability of winning
        - q = probability of losing (1-p)
        """
        # Use historical performance if available, otherwise estimate
        if historical_performance and pair_score.symbol in historical_performance:
            perf = historical_performance[pair_score.symbol]
            win_rate = perf.get('win_rate', 0.75)
            avg_win = perf.get('avg_win', 0.02)
            avg_loss = perf.get('avg_loss', 0.015)
        else:
            # Estimate based on pair characteristics
            base_win_rate = 0.75  # 75% base win rate for grid
            
            # Adjust based on volatility and range score
            vol_adjustment = max(0, 1 - (pair_score.atr_pct - 2.5) / 5)
            range_adjustment = pair_score.range_score / 100
            
            win_rate = base_win_rate * (0.7 + 0.3 * vol_adjustment * range_adjustment)
            win_rate = max(0.6, min(0.9, win_rate))
            
            # Estimate win/loss based on volatility
            grid_spacing = pair_score.atr_pct * 0.1
            avg_win = grid_spacing * 0.8
            avg_loss = grid_spacing * 1.2
        
        # Calculate Kelly fraction
        p = win_rate
        q = 1 - p
        b = avg_win / avg_loss if avg_loss > 0 else 1.5
        
        kelly_fraction = (b * p - q) / b
        
        # Apply safety multiplier and bounds
        kelly_fraction *= self.kelly_multiplier
        kelly_fraction = max(self.min_kelly_fraction, 
                           min(self.max_kelly_fraction, kelly_fraction))
        
        return kelly_fraction
    
    def calculate_optimal_leverage(self, pair_score: PairScore, 
                                 kelly_fraction: float) -> int:
        """Calculate optimal leverage based on volatility and Kelly fraction."""
        # Base leverage on volatility (inverse relationship)
        vol_based_leverage = max(2, min(5, 3.0 / max(pair_score.atr_pct, 0.5)))
        
        # Adjust based on Kelly fraction
        kelly_multiplier = 0.5 + (kelly_fraction / self.max_kelly_fraction) * 0.5
        optimal_leverage = vol_based_leverage * kelly_multiplier
        
        # Round to integer and apply bounds
        leverage = max(self.min_leverage, min(self.max_leverage, round(optimal_leverage)))
        
        return int(leverage)
    
    def calculate_position_sizes(self, pair_scores: List[PairScore], 
                               total_capital: float) -> List[PositionSize]:
        """Calculate optimal position sizes for all pairs."""
        logger.info(f"💰 Calculating position sizes for {len(pair_scores)} pairs")
        logger.info(f"   Total Capital: ${total_capital:,.2f}")
        
        position_sizes = []
        total_allocated = 0.0
        
        for pair_score in pair_scores:
            try:
                # Calculate Kelly fraction
                kelly_fraction = self.calculate_kelly_fraction(pair_score)
                
                # Calculate optimal leverage
                leverage = self.calculate_optimal_leverage(pair_score, kelly_fraction)
                
                # Base allocation from pair scanner
                base_allocation = pair_score.allocation_pct / 100
                
                # Combine Kelly and scanner allocation
                kelly_weight = 0.6
                final_allocation = (kelly_fraction * kelly_weight + 
                                  base_allocation * (1 - kelly_weight))
                
                # Apply confidence multiplier based on grade
                grade_multipliers = {'A+': 1.2, 'A': 1.1, 'A-': 1.0, 
                                   'B+': 0.9, 'B': 0.8, 'B-': 0.7,
                                   'C+': 0.6, 'C': 0.5, 'C-': 0.4}
                confidence_multiplier = grade_multipliers.get(pair_score.grade, 0.5)
                final_allocation *= confidence_multiplier
                
                # Calculate USDT amount
                usdt_amount = total_capital * final_allocation
                
                # Apply risk limits
                max_risk_amount = total_capital * self.max_single_position_risk
                risk_amount = usdt_amount / leverage
                
                if risk_amount > max_risk_amount:
                    usdt_amount = max_risk_amount * leverage
                    risk_amount = max_risk_amount
                
                # Calculate quantity
                current_price = pair_score.current_price
                quantity = (usdt_amount * leverage) / current_price
                
                position_size = PositionSize(
                    symbol=pair_score.symbol,
                    usdt_amount=usdt_amount,
                    leverage=leverage,
                    quantity=quantity,
                    risk_amount=risk_amount,
                    kelly_fraction=kelly_fraction,
                    confidence_multiplier=confidence_multiplier
                )
                
                position_sizes.append(position_size)
                total_allocated += usdt_amount
                
                logger.info(f"   {pair_score.symbol}: ${usdt_amount:,.0f} @ {leverage}x "
                           f"(Risk: ${risk_amount:,.0f}, Kelly: {kelly_fraction:.3f})")
                
            except Exception as e:
                logger.error(f"Error calculating position size for {pair_score.symbol}: {e}")
        
        logger.info(f"   Total Allocated: ${total_allocated:,.2f} ({total_allocated/total_capital:.1%})")
        
        return position_sizes
    
    def calculate_correlation_matrix(self, symbols: List[str], 
                                   lookback_days: int = 30) -> np.ndarray:
        """Calculate correlation matrix between pairs."""
        if len(symbols) <= 1:
            return np.array([[1.0]])
        
        # Fetch price data for all symbols
        price_data = {}
        for symbol in symbols:
            try:
                klines = self.client.get_klines(symbol, '4h', lookback_days * 6)
                df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['returns'] = df['close'].pct_change()
                price_data[symbol] = df['returns'].dropna()
            except Exception as e:
                logger.warning(f"Could not fetch data for {symbol}: {e}")
        
        if len(price_data) <= 1:
            return np.eye(len(symbols))
        
        # Create returns matrix
        min_length = min(len(data) for data in price_data.values())
        returns_matrix = np.array([data.tail(min_length).values for data in price_data.values()])
        
        # Calculate correlation matrix
        correlation_matrix = np.corrcoef(returns_matrix)
        
        return correlation_matrix
    
    def calculate_portfolio_risk(self, position_sizes: List[PositionSize],
                               correlation_matrix: np.ndarray) -> RiskMetrics:
        """Calculate comprehensive portfolio risk metrics."""
        if not position_sizes:
            return RiskMetrics(0, 0, 0, 0, 0, 0)
        
        # Total exposure
        total_exposure = sum(pos.usdt_amount for pos in position_sizes)
        
        # Max single position risk
        max_single_risk = max(pos.risk_amount for pos in position_sizes)
        
        # Portfolio VaR (simplified)
        risk_amounts = np.array([pos.risk_amount for pos in position_sizes])
        portfolio_var = np.sqrt(risk_amounts.T @ correlation_matrix @ risk_amounts)
        
        # Correlation risk (average correlation)
        n = len(correlation_matrix)
        if n > 1:
            correlation_risk = (correlation_matrix.sum() - n) / (n * (n - 1))
        else:
            correlation_risk = 0.0
        
        return RiskMetrics(
            total_exposure=total_exposure,
            max_single_risk=max_single_risk,
            portfolio_var=portfolio_var,
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            correlation_risk=correlation_risk
        )
    
    def get_portfolio_summary(self, position_sizes: List[PositionSize],
                            risk_metrics: RiskMetrics) -> Dict:
        """Get comprehensive portfolio summary."""
        total_capital = sum(pos.usdt_amount for pos in position_sizes)
        total_risk = sum(pos.risk_amount for pos in position_sizes)
        
        return {
            'total_positions': len(position_sizes),
            'total_capital_allocated': total_capital,
            'total_risk_amount': total_risk,
            'average_leverage': np.mean([pos.leverage for pos in position_sizes]) if position_sizes else 0,
            'max_single_risk_pct': (risk_metrics.max_single_risk / total_capital * 100) if total_capital > 0 else 0,
            'portfolio_risk_pct': (risk_metrics.portfolio_var / total_capital * 100) if total_capital > 0 else 0,
            'correlation_risk': risk_metrics.correlation_risk,
            'diversification_ratio': len(position_sizes) / max(1, risk_metrics.correlation_risk * 10),
        }
