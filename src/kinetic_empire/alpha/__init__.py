"""Kinetic Empire Alpha v2.0 - Multi-Strategy Trading System.

A comprehensive multi-strategy cryptocurrency trading system combining:
- Funding Rate Arbitrage (40% allocation) - Delta-neutral income
- Wave Rider Strategy (30% allocation) - Multi-timeframe momentum
- Smart Grid Strategy (20% allocation) - Volatility-adjusted grids
- Reserve Fund (10% allocation) - Opportunity capital

Target Performance:
- Annual Return: 50-80%
- Maximum Drawdown: <15%
- Sharpe Ratio: 3-4
- Win Rate: 70-85%
"""

from .models import (
    TrendStrength,
    TrailingMethod,
    ArbitragePosition,
    RFactorPosition,
    PartialExit,
    Signal,
    GridLevel,
    GridState,
    FundingData,
    StrategyPerformance,
)

from .rfactor import RFactorCalculator
from .profit_taker import PartialProfitTaker, ProfitTakeConfig
from .trailing import AdvancedTrailingSystem, AdvancedTrailingConfig
from .indicators import SupertrendIndicator, ChandelierExit
from .funding_arbitrage import FundingArbitrageStrategy, FundingRateMonitor, ArbitrageConfig
from .wave_rider import WaveRiderStrategy, WaveRiderConfig
from .smart_grid import SmartGridStrategy, SmartGridConfig
from .pyramiding import PyramidingModule, PyramidConfig
from .portfolio import PortfolioManager, PortfolioConfig
from .risk_manager import UnifiedRiskManager, RiskConfig
from .analytics import PerformanceAnalytics, TradeRecord
from .orchestrator import KineticEmpireAlpha, AlphaConfig

__version__ = "2.0.0"

__all__ = [
    # Models
    "TrendStrength",
    "TrailingMethod",
    "ArbitragePosition",
    "RFactorPosition",
    "PartialExit",
    "Signal",
    "GridLevel",
    "GridState",
    "FundingData",
    "StrategyPerformance",
    "TradeRecord",
    # Core Components
    "RFactorCalculator",
    "PartialProfitTaker",
    "ProfitTakeConfig",
    "AdvancedTrailingSystem",
    "AdvancedTrailingConfig",
    "SupertrendIndicator",
    "ChandelierExit",
    # Strategies
    "FundingArbitrageStrategy",
    "FundingRateMonitor",
    "ArbitrageConfig",
    "WaveRiderStrategy",
    "WaveRiderConfig",
    "SmartGridStrategy",
    "SmartGridConfig",
    "PyramidingModule",
    "PyramidConfig",
    # Portfolio & Risk
    "PortfolioManager",
    "PortfolioConfig",
    "UnifiedRiskManager",
    "RiskConfig",
    # Analytics
    "PerformanceAnalytics",
    # Main Orchestrator
    "KineticEmpireAlpha",
    "AlphaConfig",
]
