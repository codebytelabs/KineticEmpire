"""Unified Trading System - Multi-engine trading platform.

This module provides the orchestration layer for running Spot and Futures
trading engines concurrently with centralized configuration and risk management.
"""

from .config import UnifiedConfig, EnvConfig, load_unified_config, load_env_config
from .capital_allocator import CapitalAllocator, CapitalAllocation
from .risk_monitor import GlobalRiskMonitor
from .health_monitor import HealthMonitor, EngineHealth, EngineStatus
from .base_engine import BaseEngine
from .orchestrator import Orchestrator

__all__ = [
    "UnifiedConfig",
    "EnvConfig",
    "load_unified_config",
    "load_env_config",
    "CapitalAllocator",
    "CapitalAllocation",
    "GlobalRiskMonitor",
    "HealthMonitor",
    "EngineHealth",
    "EngineStatus",
    "BaseEngine",
    "Orchestrator",
]
