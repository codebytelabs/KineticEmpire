"""
Kinetic Empire - Automated High-Frequency Crypto Asset Management System

A regime-aware, self-optimizing cryptocurrency trading system built on Freqtrade.
"""

__version__ = "1.0.0"
__author__ = "Kinetic Empire Team"

# Use relative imports to avoid module resolution issues
from .models import (
    Regime,
    ExitReason,
    PairData,
    Trade,
    TradeOpen,
    TradeClose,
    Position,
)

__all__ = [
    "Regime",
    "ExitReason",
    "PairData",
    "Trade",
    "TradeOpen",
    "TradeClose",
    "Position",
]
