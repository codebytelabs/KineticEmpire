"""Spot Engine for Unified Trading System.

Simple spot trading engine without leverage.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .config import UnifiedConfig
from .capital_allocator import CapitalAllocation
from .base_engine import BaseEngine

logger = logging.getLogger(__name__)


class SpotPosition:
    """Track a spot position."""
    def __init__(self, symbol: str, quantity: float, entry_price: float):
        self.symbol = symbol
        self.quantity = quantity
        self.entry_price = entry_price
        self.entry_time = datetime.now()


class SpotEngine(BaseEngine):
    """Spot trading engine without leverage.
    
    Simple momentum-based spot trading strategy.
    """
    
    def __init__(
        self,
        config: UnifiedConfig,
        allocation: CapitalAllocation,
        api_key: str,
        api_secret: str,
        testnet: bool = True,
    ):
        """Initialize spot engine.
        
        Args:
            config: Unified configuration.
            allocation: Capital allocation for this engine.
            api_key: Binance API key.
            api_secret: Binance API secret.
            testnet: Whether to use testnet.
        """
        super().__init__("spot", config, allocation)
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self._client = None
        self.positions: Dict[str, SpotPosition] = {}
        self.starting_balance = 0.0
        self.trade_count = 0
    
    async def start(self) -> None:
        """Start the spot trading loop."""
        self._running = True
        
        logger.info(f"🚀 {self.name.upper()} ENGINE STARTING")
        logger.info(f"   💰 Capital Allocation: {self.allocation.allocated_pct}%")
        logger.info(f"   📊 Max Positions: {self.config.spot_max_positions}")
        logger.info(f"   🎯 Stop Loss: {self.config.spot_stop_loss_pct}%")
        logger.info(f"   🎯 Take Profit: {self.config.spot_take_profit_pct}%")
        
        # Initialize client
        try:
            from binance.client import Client
            self._client = Client(
                self.api_key,
                self.api_secret,
                testnet=self.testnet,
            )
            account = self._client.get_account()
            for balance in account['balances']:
                if balance['asset'] == 'USDT':
                    self.starting_balance = float(balance['free'])
                    break
            logger.info(f"   💵 Available Balance: ${self.starting_balance:.2f}")
        except ImportError:
            logger.warning("⚠️ binance-python not installed, spot engine disabled")
            self._running = False
            return
        except Exception as e:
            logger.error(f"❌ Failed to initialize spot client: {e}")
            self._running = False
            return
        
        scan_cycle = 0
        
        while self._running and not self.is_shutdown_requested():
            try:
                self.send_heartbeat()
                scan_cycle += 1
                
                # Monitor positions
                await self._monitor_positions()
                
                # Scan for opportunities
                if scan_cycle % 6 == 1:  # Every minute
                    await self._scan_and_trade()
                
                await asyncio.sleep(self.config.spot_scan_interval_seconds / 6)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in spot loop: {e}")
                await asyncio.sleep(10)
        
        self._running = False
        logger.info(f"🛑 {self.name.upper()} ENGINE STOPPED")
    
    async def stop(self) -> None:
        """Stop the engine gracefully."""
        self._shutdown_requested = True
        await self._wait_for_completion(timeout_seconds=30.0)
        self._running = False
        logger.info(f"✅ {self.name.upper()} engine stopped gracefully")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        return {
            "name": self.name,
            "running": self._running,
            "portfolio_value": self.starting_balance,
            "positions_count": len(self.positions),
            "trade_count": self.trade_count,
            "allocation_pct": self.allocation.allocated_pct,
        }
    
    async def get_positions_count(self) -> int:
        """Get number of open positions."""
        return len(self.positions)
    
    async def get_total_pnl(self) -> tuple[float, float]:
        """Get total P&L."""
        total_pnl = 0.0
        for pos in self.positions.values():
            try:
                ticker = self._client.get_symbol_ticker(symbol=pos.symbol)
                current_price = float(ticker['price'])
                pnl = (current_price - pos.entry_price) * pos.quantity
                total_pnl += pnl
            except Exception:
                pass
        
        pnl_pct = (total_pnl / self.starting_balance * 100) if self.starting_balance > 0 else 0.0
        return total_pnl, pnl_pct
    
    async def close_all_positions(self) -> None:
        """Close all open positions."""
        logger.warning(f"🚨 {self.name}: Closing all positions!")
        for symbol in list(self.positions.keys()):
            await self._close_position(symbol, "CIRCUIT_BREAKER")
    
    async def _monitor_positions(self):
        """Monitor open positions for exits."""
        for symbol, pos in list(self.positions.items()):
            try:
                ticker = self._client.get_symbol_ticker(symbol=symbol)
                current_price = float(ticker['price'])
                pnl_pct = ((current_price - pos.entry_price) / pos.entry_price) * 100
                
                # Check stop loss
                if pnl_pct <= -self.config.spot_stop_loss_pct:
                    logger.warning(f"🛑 {symbol}: STOP LOSS at {pnl_pct:.2f}%")
                    await self._close_position(symbol, "STOP_LOSS")
                    continue
                
                # Check take profit
                if pnl_pct >= self.config.spot_take_profit_pct:
                    logger.info(f"💰 {symbol}: TAKE PROFIT at {pnl_pct:.2f}%")
                    await self._close_position(symbol, "TAKE_PROFIT")
                    continue
                
            except Exception as e:
                logger.error(f"Error monitoring {symbol}: {e}")
    
    async def _scan_and_trade(self):
        """Scan for trading opportunities."""
        if len(self.positions) >= self.config.spot_max_positions:
            return
        
        try:
            for symbol in self.config.spot_watchlist:
                if symbol in self.positions:
                    continue
                
                if len(self.positions) >= self.config.spot_max_positions:
                    break
                
                # Simple momentum check
                try:
                    klines = self._client.get_klines(symbol=symbol, interval='15m', limit=20)
                    closes = [float(k[4]) for k in klines]
                    
                    if len(closes) < 20:
                        continue
                    
                    # Simple EMA crossover
                    ema_9 = sum(closes[-9:]) / 9
                    ema_21 = sum(closes[-21:]) / 21
                    
                    # Bullish signal
                    if ema_9 > ema_21 * 1.001:  # 0.1% above
                        current_price = closes[-1]
                        position_size = self.starting_balance * (self.config.spot_position_size_pct / 100)
                        quantity = position_size / current_price
                        
                        # Round quantity
                        quantity = round(quantity, 5)
                        
                        if quantity * current_price >= 10:  # Min $10
                            await self._execute_buy(symbol, quantity, current_price)
                            
                except Exception as e:
                    logger.debug(f"Error analyzing {symbol}: {e}")
                    
        except Exception as e:
            logger.error(f"Scanner error: {e}")
    
    async def _execute_buy(self, symbol: str, quantity: float, price: float):
        """Execute spot buy order."""
        try:
            order = self._client.create_order(
                symbol=symbol,
                side='BUY',
                type='MARKET',
                quantity=quantity,
            )
            
            self.positions[symbol] = SpotPosition(
                symbol=symbol,
                quantity=quantity,
                entry_price=price,
            )
            
            self.trade_count += 1
            self._last_trade_time = datetime.now()
            logger.info(f"🎉 SPOT BUY: {symbol} | Qty: {quantity} @ ${price:.4f}")
            
        except Exception as e:
            logger.error(f"Failed to buy {symbol}: {e}")
    
    async def _close_position(self, symbol: str, reason: str):
        """Close a spot position."""
        if symbol not in self.positions:
            return
        
        pos = self.positions[symbol]
        
        try:
            order = self._client.create_order(
                symbol=symbol,
                side='SELL',
                type='MARKET',
                quantity=pos.quantity,
            )
            
            del self.positions[symbol]
            logger.info(f"✅ SPOT SELL: {symbol} | {reason}")
            
        except Exception as e:
            logger.error(f"Failed to sell {symbol}: {e}")
