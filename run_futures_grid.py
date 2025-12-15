#!/usr/bin/env python3
"""Kinetic Empire Futures Grid Trading Bot.

High win-rate grid trading strategy for Binance Futures.
Profits from price oscillations within a defined range.
"""
import asyncio
import logging
import os
import signal
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from kinetic_empire.futures.client import BinanceFuturesClient
from kinetic_empire.futures.grid import FuturesGridBot, GridConfig, GridType

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("FuturesGrid")


def calculate_grid_range(client: BinanceFuturesClient, symbol: str) -> tuple:
    """Calculate optimal grid range based on recent price action.
    
    Uses support/resistance from recent highs and lows.
    """
    # Get 4-hour candles for range calculation
    klines = client.get_klines(symbol, '4h', 50)
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    # Calculate range based on recent price action
    recent_high = df['high'].tail(20).max()
    recent_low = df['low'].tail(20).min()
    current_price = df['close'].iloc[-1]
    
    # Calculate ATR for volatility
    df['tr'] = pd.concat([
        df['high'] - df['low'],
        abs(df['high'] - df['close'].shift()),
        abs(df['low'] - df['close'].shift())
    ], axis=1).max(axis=1)
    atr = df['tr'].tail(14).mean()
    
    # Set range: current price +/- 2 ATR (or use recent high/low)
    range_size = max(atr * 4, (recent_high - recent_low) * 0.8)
    
    upper_price = current_price + (range_size / 2)
    lower_price = current_price - (range_size / 2)
    
    # Round to nice numbers
    if current_price > 10000:  # BTC
        upper_price = round(upper_price / 100) * 100
        lower_price = round(lower_price / 100) * 100
    elif current_price > 100:  # ETH, etc
        upper_price = round(upper_price / 10) * 10
        lower_price = round(lower_price / 10) * 10
    else:
        upper_price = round(upper_price, 2)
        lower_price = round(lower_price, 2)
    
    return lower_price, upper_price, atr


async def run_grid_bot():
    """Main grid bot loop."""
    logger.info("🚀 Starting Kinetic Empire Futures Grid Bot")
    logger.info("=" * 60)
    
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
    
    # Initialize grid bot
    grid_bot = FuturesGridBot(client)
    
    # Configuration
    symbol = "BTCUSDT"
    investment = min(balance * 0.5, 2000)  # Use 50% of balance, max $2000
    leverage = 3
    grid_count = 10
    
    # Calculate optimal range
    logger.info(f"\n📊 Analyzing {symbol} for grid setup...")
    lower_price, upper_price, atr = calculate_grid_range(client, symbol)
    
    ticker = client.get_ticker(symbol)
    current_price = ticker['last']
    
    logger.info(f"   Current Price: ${current_price:.2f}")
    logger.info(f"   ATR (14): ${atr:.2f}")
    logger.info(f"   Grid Range: ${lower_price:.2f} - ${upper_price:.2f}")
    logger.info(f"   Investment: ${investment:.2f} @ {leverage}x leverage")
    
    # Create grid config
    config = GridConfig(
        symbol=symbol,
        upper_price=upper_price,
        lower_price=lower_price,
        grid_count=grid_count,
        grid_type=GridType.NEUTRAL,
        leverage=leverage,
        total_investment=investment,
        stop_loss_pct=0.15,  # 15% below range
        take_profit_pct=0.15  # 15% above range
    )
    
    # Setup grid
    logger.info(f"\n🔧 Setting up grid...")
    state = grid_bot.setup_grid(config)
    
    # Place initial orders
    logger.info(f"\n📝 Placing grid orders...")
    orders_placed = grid_bot.place_grid_orders(symbol)
    logger.info(f"   Placed {orders_placed} orders")
    
    # Main loop
    logger.info(f"\n🔄 Starting grid trading loop...")
    logger.info("   Press Ctrl+C to stop")
    logger.info("=" * 60)
    
    cycle = 0
    running = True
    
    while running:
        try:
            cycle += 1
            
            # Get current status
            ticker = client.get_ticker(symbol)
            current_price = ticker['last']
            position = client.get_position(symbol)
            
            # Check for filled orders
            filled = grid_bot.check_filled_orders(symbol)
            
            # Rebalance if orders were filled
            if filled:
                grid_bot.rebalance_grid(symbol, filled)
            
            # Check stop conditions
            should_stop, reason = grid_bot.check_stop_conditions(symbol)
            if should_stop:
                logger.warning(f"⚠️ Stop condition triggered: {reason}")
                grid_bot.close_grid(symbol, reason)
                running = False
                break
            
            # Get grid status
            status = grid_bot.get_grid_status(symbol)
            
            # Log status every 10 cycles
            if cycle % 10 == 0:
                pos_info = ""
                if position:
                    pos_info = f" | Position: {position.side} {position.quantity:.4f}"
                
                logger.info(
                    f"Cycle {cycle} | "
                    f"Price: ${current_price:.2f} | "
                    f"Trades: {status['completed_trades']} | "
                    f"Profit: ${status['total_profit']:.2f}"
                    f"{pos_info}"
                )
            
            # Wait before next cycle
            await asyncio.sleep(5)  # 5 second cycles for grid trading
            
        except KeyboardInterrupt:
            logger.info("\n👋 Stopping bot...")
            running = False
        except Exception as e:
            logger.error(f"Error in cycle: {e}")
            await asyncio.sleep(10)
    
    # Cleanup
    logger.info("\n📊 Final Summary:")
    status = grid_bot.get_grid_status(symbol)
    logger.info(f"   Total Profit: ${status.get('total_profit', 0):.2f}")
    logger.info(f"   Completed Trades: {status.get('completed_trades', 0)}")
    logger.info(f"   Win Rate: {status.get('win_rate', 0):.1f}%")
    
    # Close grid
    grid_bot.close_grid(symbol, "Bot stopped")


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    print("\n👋 Shutting down...")
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    asyncio.run(run_grid_bot())
