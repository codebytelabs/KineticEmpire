#!/usr/bin/env python3
"""Kinetic Empire ULTIMATE Futures Grid Trading Bot.

The most advanced grid trading system with:
1. Intelligent pair ranking (trend, volume, volatility, upside)
2. Dynamic position sizing based on quality score
3. Multi-pair grid management
4. Adaptive leverage based on market conditions
5. Risk management with daily limits and kill switches

Target: 80%+ win rate, <10% drawdown, maximum profit!
"""
import asyncio
import logging
import os
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from kinetic_empire.futures.client import BinanceFuturesClient
from kinetic_empire.futures.grid import FuturesGridBot, GridConfig, GridType, GridState
from kinetic_empire.futures.scanner import FuturesPairScanner, PairScore
from kinetic_empire.futures.portfolio import AdvancedPortfolioManager
from kinetic_empire.futures.analytics import PerformanceTracker, TradeResult

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("UltimateGrid")


class UltimateGridBot:
    """The Ultimate Multi-Pair Grid Trading Bot."""
    
    def __init__(self, client: BinanceFuturesClient):
        self.client = client
        self.scanner = FuturesPairScanner(client)
        self.grid_bot = FuturesGridBot(client)
        self.portfolio_manager = AdvancedPortfolioManager(client)
        self.performance_tracker = PerformanceTracker()
        
        # Configuration
        self.max_concurrent_grids = 5
        self.min_score_threshold = 55  # Minimum C+ grade
        self.max_allocation_pct = 0.80  # Max 80% of balance in grids
        
        # Risk management
        self.daily_loss_limit = 0.03  # 3% daily loss limit
        self.max_drawdown = 0.10      # 10% max drawdown
        self.starting_balance = 0.0
        self.peak_balance = 0.0
        self.daily_pnl = 0.0
        
        # State
        self.active_grids: Dict[str, GridState] = {}
        self.pair_scores: Dict[str, PairScore] = {}
        self.running = False
        
    async def initialize(self):
        """Initialize the bot."""
        logger.info("🚀 Initializing Ultimate Grid Bot...")
        
        # Get starting balance
        self.starting_balance = self.client.get_usdt_balance()
        self.peak_balance = self.starting_balance
        
        # Initialize performance tracker
        self.performance_tracker.set_initial_balance(self.starting_balance)
        
        logger.info(f"   Starting Balance: ${self.starting_balance:.2f}")
        
        # Scan and rank pairs
        await self.scan_pairs()
        
    async def scan_pairs(self):
        """Scan and rank all pairs."""
        logger.info("\n📊 Scanning and ranking pairs...")
        
        scores = self.scanner.scan_all_pairs()
        self.pair_scores = {s.symbol: s for s in scores}
        
        # Print rankings
        self.scanner.print_rankings(scores[:10])
        
        return scores
    
    def calculate_grid_range(self, score: PairScore) -> tuple:
        """Calculate optimal grid range for a pair."""
        # Use support/resistance from scanner
        support = score.support
        resistance = score.resistance
        current_price = score.current_price
        atr = score.atr
        
        # Adjust range based on ATR
        range_buffer = atr * 0.5
        
        lower_price = max(support - range_buffer, current_price * 0.92)
        upper_price = min(resistance + range_buffer, current_price * 1.08)
        
        # Round to appropriate precision
        if current_price > 10000:
            lower_price = round(lower_price / 100) * 100
            upper_price = round(upper_price / 100) * 100
        elif current_price > 100:
            lower_price = round(lower_price / 10) * 10
            upper_price = round(upper_price / 10) * 10
        elif current_price > 1:
            lower_price = round(lower_price, 2)
            upper_price = round(upper_price, 2)
        else:
            lower_price = round(lower_price, 4)
            upper_price = round(upper_price, 4)
        
        return lower_price, upper_price
    
    def calculate_investment(self, score: PairScore, available_balance: float) -> float:
        """Calculate investment amount based on Kelly Criterion and score."""
        # Get Kelly fraction from portfolio manager
        kelly_fraction = self.portfolio_manager.calculate_kelly_fraction(score)
        
        # Base allocation from score
        scanner_allocation = score.allocation_pct / 100
        
        # Combine Kelly and scanner allocation (60% Kelly, 40% scanner)
        combined_allocation = kelly_fraction * 0.6 + scanner_allocation * 0.4
        
        # Scale by available balance
        max_per_grid = available_balance * self.max_allocation_pct / self.max_concurrent_grids
        
        investment = min(
            available_balance * combined_allocation,
            max_per_grid,
            1000  # Cap at $1000 per grid for safety
        )
        
        logger.debug(f"   {score.symbol}: Kelly={kelly_fraction:.3f}, Scanner={scanner_allocation:.3f}, Combined={combined_allocation:.3f}")
        
        return max(investment, 50)  # Minimum $50
    
    async def setup_grid_for_pair(self, score: PairScore) -> bool:
        """Setup a grid for a specific pair."""
        symbol = score.symbol
        
        if symbol in self.active_grids:
            logger.info(f"   {symbol}: Already has active grid")
            return False
        
        if len(self.active_grids) >= self.max_concurrent_grids:
            logger.info(f"   {symbol}: Max concurrent grids reached")
            return False
        
        # Calculate parameters
        available_balance = self.client.get_usdt_balance()
        investment = self.calculate_investment(score, available_balance)
        lower_price, upper_price = self.calculate_grid_range(score)
        
        # Determine grid count based on range
        range_pct = (upper_price - lower_price) / score.current_price * 100
        grid_count = max(5, min(15, int(range_pct * 2)))
        
        # Map grid type
        grid_type_map = {
            'LONG': GridType.LONG,
            'SHORT': GridType.SHORT,
            'NEUTRAL': GridType.NEUTRAL
        }
        grid_type = grid_type_map.get(score.grid_type, GridType.NEUTRAL)
        
        logger.info(f"\n🔧 Setting up grid for {symbol}")
        logger.info(f"   Grade: {score.grade} (Score: {score.total_score:.1f})")
        logger.info(f"   Range: ${lower_price:.2f} - ${upper_price:.2f}")
        logger.info(f"   Investment: ${investment:.2f} @ {score.recommended_leverage}x")
        logger.info(f"   Grid Type: {score.grid_type}")
        
        # Create config
        config = GridConfig(
            symbol=symbol,
            upper_price=upper_price,
            lower_price=lower_price,
            grid_count=grid_count,
            grid_type=grid_type,
            leverage=score.recommended_leverage,
            total_investment=investment,
            stop_loss_pct=0.12,
            take_profit_pct=0.12
        )
        
        try:
            # Setup grid
            state = self.grid_bot.setup_grid(config)
            
            # Place orders
            orders_placed = self.grid_bot.place_grid_orders(symbol)
            
            if orders_placed > 0:
                self.active_grids[symbol] = state
                logger.info(f"   ✅ Placed {orders_placed} orders")
                return True
            else:
                logger.warning(f"   ⚠️ No orders placed")
                return False
                
        except Exception as e:
            logger.error(f"   ❌ Failed to setup grid: {e}")
            return False
    
    async def manage_grids(self):
        """Manage all active grids."""
        for symbol in list(self.active_grids.keys()):
            try:
                # Check for filled orders
                filled = self.grid_bot.check_filled_orders(symbol)
                
                # Rebalance if needed
                if filled:
                    self.grid_bot.rebalance_grid(symbol, filled)
                
                # Check stop conditions
                should_stop, reason = self.grid_bot.check_stop_conditions(symbol)
                if should_stop:
                    logger.warning(f"⚠️ {symbol}: Stop triggered - {reason}")
                    self.grid_bot.close_grid(symbol, reason)
                    del self.active_grids[symbol]
                    
            except Exception as e:
                logger.error(f"Error managing {symbol}: {e}")
    
    def check_risk_limits(self) -> bool:
        """Check if risk limits are breached.
        
        Returns:
            True if should continue, False if should stop
        """
        current_balance = self.client.get_usdt_balance()
        
        # Update peak balance
        if current_balance > self.peak_balance:
            self.peak_balance = current_balance
        
        # Calculate drawdown
        drawdown = (self.peak_balance - current_balance) / self.peak_balance
        
        # Calculate daily P&L
        daily_pnl_pct = (current_balance - self.starting_balance) / self.starting_balance
        
        # Check limits
        if drawdown > self.max_drawdown:
            logger.error(f"🚨 MAX DRAWDOWN BREACHED: {drawdown*100:.1f}%")
            return False
        
        if daily_pnl_pct < -self.daily_loss_limit:
            logger.error(f"🚨 DAILY LOSS LIMIT BREACHED: {daily_pnl_pct*100:.1f}%")
            return False
        
        return True
    
    def get_status_summary(self) -> dict:
        """Get current bot status."""
        current_balance = self.client.get_usdt_balance()
        
        total_profit = sum(
            self.grid_bot.grids[s].total_profit 
            for s in self.active_grids if s in self.grid_bot.grids
        )
        total_trades = sum(
            self.grid_bot.grids[s].completed_trades 
            for s in self.active_grids if s in self.grid_bot.grids
        )
        
        return {
            'balance': current_balance,
            'starting_balance': self.starting_balance,
            'pnl': current_balance - self.starting_balance,
            'pnl_pct': (current_balance - self.starting_balance) / self.starting_balance * 100,
            'active_grids': len(self.active_grids),
            'total_profit': total_profit,
            'total_trades': total_trades,
            'drawdown': (self.peak_balance - current_balance) / self.peak_balance * 100
        }
    
    async def run(self):
        """Main bot loop."""
        logger.info("\n" + "=" * 70)
        logger.info("🚀 ULTIMATE GRID BOT STARTING")
        logger.info("=" * 70)
        
        await self.initialize()
        
        self.running = True
        cycle = 0
        rescan_interval = 100  # Rescan pairs every 100 cycles (~8 minutes)
        
        while self.running:
            try:
                cycle += 1
                
                # Check risk limits
                if not self.check_risk_limits():
                    logger.error("Risk limits breached - shutting down")
                    break
                
                # Rescan pairs periodically
                if cycle % rescan_interval == 0:
                    await self.scan_pairs()
                
                # Setup new grids if we have capacity
                if len(self.active_grids) < self.max_concurrent_grids:
                    top_pairs = [
                        s for s in self.pair_scores.values()
                        if s.total_score >= self.min_score_threshold
                        and s.symbol not in self.active_grids
                    ]
                    top_pairs.sort(key=lambda x: x.total_score, reverse=True)
                    
                    for score in top_pairs[:2]:  # Add up to 2 new grids per cycle
                        if len(self.active_grids) < self.max_concurrent_grids:
                            await self.setup_grid_for_pair(score)
                
                # Manage existing grids
                await self.manage_grids()
                
                # Log status every 20 cycles
                if cycle % 20 == 0:
                    status = self.get_status_summary()
                    logger.info(
                        f"\n📊 Cycle {cycle} | "
                        f"Balance: ${status['balance']:.2f} | "
                        f"P&L: ${status['pnl']:.2f} ({status['pnl_pct']:.2f}%) | "
                        f"Grids: {status['active_grids']} | "
                        f"Trades: {status['total_trades']} | "
                        f"DD: {status['drawdown']:.2f}%"
                    )
                    
                    # Show active grids
                    for symbol in self.active_grids:
                        grid_status = self.grid_bot.get_grid_status(symbol)
                        logger.info(
                            f"   {symbol}: "
                            f"Trades={grid_status.get('completed_trades', 0)} | "
                            f"Profit=${grid_status.get('total_profit', 0):.2f}"
                        )
                
                # Wait before next cycle
                await asyncio.sleep(5)
                
            except KeyboardInterrupt:
                logger.info("\n👋 Stopping bot...")
                break
            except Exception as e:
                logger.error(f"Error in cycle: {e}")
                await asyncio.sleep(10)
        
        # Cleanup
        await self.shutdown()
    
    async def shutdown(self):
        """Graceful shutdown."""
        logger.info("\n🛑 Shutting down...")
        
        # Close all grids
        for symbol in list(self.active_grids.keys()):
            self.grid_bot.close_grid(symbol, "Bot shutdown")
        
        # Final summary
        status = self.get_status_summary()
        logger.info("\n" + "=" * 70)
        logger.info("📊 FINAL SUMMARY")
        logger.info("=" * 70)
        logger.info(f"   Starting Balance: ${status['starting_balance']:.2f}")
        logger.info(f"   Final Balance: ${status['balance']:.2f}")
        logger.info(f"   Total P&L: ${status['pnl']:.2f} ({status['pnl_pct']:.2f}%)")
        logger.info(f"   Total Trades: {status['total_trades']}")
        logger.info(f"   Max Drawdown: {status['drawdown']:.2f}%")
        logger.info("=" * 70)
        
        # Print detailed performance analytics
        self.performance_tracker.print_summary()


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    print("\n👋 Shutting down...")
    sys.exit(0)


async def main():
    """Main entry point."""
    logger.info("🏆 KINETIC EMPIRE ULTIMATE GRID BOT")
    logger.info("   Target: 80%+ Win Rate, <10% Drawdown")
    logger.info("=" * 70)
    
    # Get API keys
    api_key = os.getenv('Binance_testnet_API_KEY')
    api_secret = os.getenv('Binance_testnet_API_SECRET')
    
    if not api_key or not api_secret:
        logger.error("❌ API keys not found in .env")
        return
    
    # Initialize client
    client = BinanceFuturesClient(api_key, api_secret, testnet=True)
    
    # Test connection
    try:
        balance = client.get_usdt_balance()
        logger.info(f"✅ Connected to Binance Futures Testnet")
        logger.info(f"   Available Balance: ${balance:.2f}")
    except Exception as e:
        logger.error(f"❌ Failed to connect: {e}")
        return
    
    # Create and run bot
    bot = UltimateGridBot(client)
    await bot.run()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    asyncio.run(main())
