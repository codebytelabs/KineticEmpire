"""Kinetic Empire v3.0 - Professional Modular Trading System.

Three-pillar architecture:
- Market Scanner: Opportunity discovery
- TA Analyzer: Multi-timeframe technical analysis
- Position Manager: Risk-adjusted execution with dynamic leverage
"""

from .core.models import Signal, Position, Ticker, OHLCV, Indicators
from .core.config import V3Config

__version__ = "3.0.0"
__all__ = ["Signal", "Position", "Ticker", "OHLCV", "Indicators", "V3Config"]
