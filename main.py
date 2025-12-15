#!/usr/bin/env python3
"""Kinetic Empire Unified Trading System - Main Entry Point.

Runs both Spot and Futures trading engines concurrently with centralized
configuration and risk management.

Usage:
    python main.py
    ./start_backend.sh
"""

import asyncio
import logging
import os
import signal
import sys
from datetime import datetime

from dotenv import load_dotenv

# Load environment variables first
load_dotenv(override=True)

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.kinetic_empire.unified import (
    UnifiedConfig,
    EnvConfig,
    load_unified_config,
    load_env_config,
    Orchestrator,
    CapitalAllocator,
)
from src.kinetic_empire.unified.futures_engine import FuturesEngine
from src.kinetic_empire.unified.spot_engine import SpotEngine
from src.kinetic_empire.unified.config import ConfigValidationError
from src.kinetic_empire.futures.client import BinanceFuturesClient

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)-8s | %(name)-40s | %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"logs/unified_{datetime.now():%Y%m%d_%H%M%S}.log"),
    ],
)
logger = logging.getLogger(__name__)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)


async def main():
    """Main entry point for unified trading system."""
    logger.info("=" * 70)
    logger.info("🚀 KINETIC EMPIRE - UNIFIED TRADING SYSTEM")
    logger.info("=" * 70)
    
    # Load configuration
    try:
        config = load_unified_config()
        config.validate()
        logger.info("✅ Configuration loaded and validated")
    except ConfigValidationError as e:
        logger.error(f"❌ Configuration error: {e}")
        return 1
    
    # Load environment
    try:
        env = load_env_config()
        env.validate()
        logger.info("✅ Environment configuration loaded")
    except ConfigValidationError as e:
        logger.error(f"❌ Environment error: {e}")
        return 1
    
    # Create orchestrator
    orchestrator = Orchestrator(config, env)
    
    # Create and register engines based on configuration
    capital_allocator = CapitalAllocator(config)
    
    # Get initial balance for allocation calculation
    try:
        futures_client = BinanceFuturesClient(
            api_key=env.binance_api_key,
            api_secret=env.binance_api_secret,
            testnet=env.binance_testnet,
        )
        # Use total margin balance (includes unrealized PnL) for accurate portfolio value
        initial_balance = futures_client.get_total_margin_balance()
        logger.info(f"💰 Initial Balance: ${initial_balance:.2f}")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Binance: {e}")
        return 1
    
    # Register Futures Engine
    if env.futures_enabled and config.futures_enabled:
        futures_allocation = capital_allocator.get_allocation("futures", initial_balance)
        futures_engine = FuturesEngine(
            config=config,
            allocation=futures_allocation,
            client=futures_client,
        )
        orchestrator.register_engine(futures_engine)
    
    # Register Spot Engine
    if env.spot_enabled and config.spot_enabled:
        spot_allocation = capital_allocator.get_allocation("spot", initial_balance)
        spot_engine = SpotEngine(
            config=config,
            allocation=spot_allocation,
            api_key=env.binance_api_key,
            api_secret=env.binance_api_secret,
            testnet=env.binance_testnet,
        )
        orchestrator.register_engine(spot_engine)
    
    # Setup signal handlers
    def signal_handler(sig, frame):
        logger.info(f"👋 Received signal {sig}, initiating shutdown...")
        asyncio.create_task(orchestrator.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start orchestrator
    try:
        await orchestrator.start()
    except Exception as e:
        logger.error(f"❌ Orchestrator error: {e}")
        return 1
    
    logger.info("👋 Unified Trading System shutdown complete")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
