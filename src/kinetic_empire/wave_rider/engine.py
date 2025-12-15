"""Wave Rider Engine - Main Trading Loop.

Orchestrates all Wave Rider components:
- Scans market every 15 seconds
- Monitors positions every 5 seconds
- Executes signals and manages exits
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from .models import (
    OHLCV,
    MoverData,
    MTFResult,
    WaveRiderSignal,
    WaveRiderConfig,
)
from .volume_spike_detector import VolumeSpikeDetector
from .momentum_scanner import MomentumScanner
from .mtf_analyzer import MTFAnalyzer
from .position_sizer import WaveRiderPositionSizer
from .signal_generator import WaveRiderSignalGenerator
from .stop_calculator import WaveRiderStopCalculator
from .trailing_stop import WaveRiderTrailingStop
from .risk_manager import (
    WaveRiderCircuitBreaker,
    WaveRiderBlacklist,
    WaveRiderPositionLimit,
)

logger = logging.getLogger(__name__)


class WaveRiderEngine:
    """Main Wave Rider trading engine.
    
    Orchestrates scanning, signal generation, and position management.
    """
    
    def __init__(
        self,
        client: Any,  # BinanceFuturesClient
        config: Optional[WaveRiderConfig] = None,
        capital: float = 5000,
    ):
        """Initialize the Wave Rider engine.
        
        Args:
            client: Binance futures client
            config: Wave Rider configuration
            capital: Starting capital in USD
        """
        self.client = client
        self.config = config or WaveRiderConfig()
        self.capital = capital
        
        # Initialize components
        self.spike_detector = VolumeSpikeDetector()
        self.momentum_scanner = MomentumScanner(self.config)
        self.mtf_analyzer = MTFAnalyzer(self.config)
        self.position_sizer = WaveRiderPositionSizer(self.config)
        self.signal_generator = WaveRiderSignalGenerator(self.config)
        self.stop_calculator = WaveRiderStopCalculator(self.config)
        self.trailing_stop = WaveRiderTrailingStop(self.config)
        
        # Risk management
        self.circuit_breaker = WaveRiderCircuitBreaker(self.config)
        self.blacklist = WaveRiderBlacklist(self.config)
        self.position_limit = WaveRiderPositionLimit(self.config)
        
        # State
        self.running = False
        self.scan_count = 0
        self.monitor_count = 0
        self._position_entries: Dict[str, float] = {}  # symbol -> entry_price
        self._position_atrs: Dict[str, float] = {}  # symbol -> ATR
    
    async def start(self):
        """Start the Wave Rider trading loop."""
        self.running = True
        
        # Initialize circuit breaker
        try:
            balance = self.client.get_usdt_balance()
            self.circuit_breaker.initialize(balance)
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            self.circuit_breaker.initialize(self.capital)
        
        logger.info("=" * 70)
        logger.info("🌊 WAVE RIDER ENGINE - ACTIVE MOMENTUM SCALPING")
        logger.info("=" * 70)
        logger.info(f"   📊 Scan interval: {self.config.scan_interval}s")
        logger.info(f"   👁️ Monitor interval: {self.config.monitor_interval}s")
        logger.info(f"   📈 Max positions: {self.config.max_positions}")
        logger.info(f"   💰 Max exposure: {self.config.max_exposure:.0%}")
        logger.info(f"   🛑 Daily loss limit: {self.config.daily_loss_limit:.0%}")
        logger.info("=" * 70)
        
        # Main loop
        monitor_cycle = 0
        while self.running:
            try:
                monitor_cycle += 1
                
                # Monitor positions every cycle
                await self._monitor_positions()
                
                # Scan market every N cycles (scan_interval / monitor_interval)
                scan_ratio = self.config.scan_interval // self.config.monitor_interval
                if monitor_cycle % scan_ratio == 1:
                    await self._scan_cycle()
                
                await asyncio.sleep(self.config.monitor_interval)
                
            except KeyboardInterrupt:
                logger.info("👋 Stopping Wave Rider...")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(10)
        
        self.running = False
        logger.info("🛑 Wave Rider stopped")
    
    async def _scan_cycle(self):
        """Execute one market scan cycle."""
        self.scan_count += 1
        
        # Check circuit breaker
        if not self.circuit_breaker.can_trade():
            logger.warning("🚨 CIRCUIT BREAKER ACTIVE - No new trades")
            return
        
        # Check position limit
        if not self.position_limit.can_open_position():
            logger.debug(f"Max positions reached ({self.config.max_positions})")
            return
        
        try:
            # Get all tickers
            tickers = self.client.get_all_tickers()
            
            # Get top movers
            top_movers = self.momentum_scanner.get_top_movers(tickers)
            
            if not top_movers:
                logger.debug(f"━━━ SCAN #{self.scan_count} | No movers found ━━━")
                return
            
            # Log top 5 movers
            logger.info(f"━━━ SCAN #{self.scan_count} | Top movers: ━━━")
            for mover in top_movers[:5]:
                logger.info(
                    f"   🔥 {mover.symbol}: {mover.price_change_pct:+.2f}% | "
                    f"Vol: {mover.volume_ratio:.1f}x | Score: {mover.momentum_score:.1f}"
                )
            
            # Analyze and generate signals
            for mover in top_movers:
                if not self.position_limit.can_open_position():
                    break
                
                # Skip if already in position
                if mover.symbol in self._position_entries:
                    continue
                
                # Skip if blacklisted
                if self.blacklist.is_blacklisted(mover.symbol):
                    continue
                
                # Get OHLCV data for MTF analysis
                ohlcv_data = await self._get_ohlcv_data(mover.symbol)
                if not ohlcv_data:
                    continue
                
                # Run MTF analysis
                mtf_result = self.mtf_analyzer.analyze(mover.symbol, ohlcv_data)
                
                # Calculate current exposure
                current_exposure = self._calculate_exposure()
                
                # Generate signal
                signal = self.signal_generator.evaluate(
                    mover=mover,
                    mtf_result=mtf_result,
                    is_blacklisted=False,
                    current_exposure=current_exposure,
                    consecutive_losses=0,  # TODO: track per symbol
                    available_capital=self.capital,
                )
                
                if signal:
                    await self._execute_signal(signal, ohlcv_data)
                    
        except Exception as e:
            logger.error(f"Scan error: {e}")
    
    async def _monitor_positions(self):
        """Monitor and manage open positions."""
        self.monitor_count += 1
        
        try:
            positions = self.client.get_positions()
            
            if not positions:
                return
            
            for pos in positions:
                symbol = pos.symbol
                
                # Skip dust positions
                if pos.quantity * pos.mark_price < 5:
                    continue
                
                # Get entry price and ATR
                entry_price = self._position_entries.get(symbol, pos.entry_price)
                atr = self._position_atrs.get(symbol, pos.entry_price * 0.02)
                
                # Calculate profit
                direction = "LONG" if pos.side == "LONG" else "SHORT"
                
                # Update trailing stop
                update = self.trailing_stop.update(
                    symbol=symbol,
                    current_price=pos.mark_price,
                    entry_price=entry_price,
                    direction=direction,
                    atr_14=atr,
                )
                
                if update.should_close:
                    await self._close_position(
                        pos,
                        update.close_pct,
                        update.close_reason,
                    )
                    
        except Exception as e:
            logger.error(f"Monitor error: {e}")
    
    async def _execute_signal(self, signal: WaveRiderSignal, ohlcv_data: Dict[str, List[OHLCV]]):
        """Execute a trading signal."""
        try:
            # Calculate ATR for stop
            candles_15m = ohlcv_data.get("15m", [])
            atr = self._calculate_atr(candles_15m) if candles_15m else signal.entry_price * 0.02
            
            # Calculate stop loss
            stop_result = self.stop_calculator.calculate(
                entry_price=signal.entry_price,
                direction=signal.direction,
                atr_14=atr,
            )
            
            # Calculate position size in USD
            size_usd = self.capital * signal.position_size_pct
            
            # Calculate quantity
            quantity = size_usd / signal.entry_price
            
            # Set leverage
            self.client.set_leverage(signal.symbol, signal.leverage)
            
            # Place order
            side = "BUY" if signal.direction == "LONG" else "SELL"
            result = self.client.place_market_order(
                symbol=signal.symbol,
                side=side,
                quantity=quantity,
            )
            
            if result:
                # Track position
                self._position_entries[signal.symbol] = signal.entry_price
                self._position_atrs[signal.symbol] = atr
                self.position_limit.add_position(signal.symbol)
                
                logger.info(
                    f"✅ OPENED {signal.symbol} {signal.direction} | "
                    f"Size: ${size_usd:.2f} | Leverage: {signal.leverage}x | "
                    f"Stop: {stop_result.stop_pct:.1%}"
                )
                
        except Exception as e:
            logger.error(f"Failed to execute signal for {signal.symbol}: {e}")
    
    async def _close_position(self, pos: Any, close_pct: float, reason: str):
        """Close a position (full or partial)."""
        try:
            close_qty = pos.quantity * close_pct
            close_side = "SELL" if pos.side == "LONG" else "BUY"
            
            result = self.client.place_market_order(
                symbol=pos.symbol,
                side=close_side,
                quantity=close_qty,
                reduce_only=True,
            )
            
            if result:
                # Record PnL
                pnl = pos.unrealized_pnl * close_pct
                self.circuit_breaker.record_pnl(pnl)
                
                # Track win/loss
                if pnl < 0:
                    was_blacklisted = self.blacklist.record_loss(pos.symbol)
                    if was_blacklisted:
                        logger.warning(f"⛔ {pos.symbol}: Blacklisted after losses")
                else:
                    self.blacklist.record_win(pos.symbol)
                
                # Clean up if fully closed
                if close_pct >= 1.0:
                    self._position_entries.pop(pos.symbol, None)
                    self._position_atrs.pop(pos.symbol, None)
                    self.position_limit.remove_position(pos.symbol)
                    self.trailing_stop.remove_position(pos.symbol)
                
                logger.info(
                    f"{'💰' if pnl >= 0 else '🛑'} CLOSED {pos.symbol} ({reason}) | "
                    f"PnL: ${pnl:+.2f}"
                )
                
        except Exception as e:
            logger.error(f"Failed to close {pos.symbol}: {e}")
    
    async def _get_ohlcv_data(self, symbol: str) -> Optional[Dict[str, List[OHLCV]]]:
        """Get OHLCV data for all timeframes."""
        try:
            ohlcv_data = {}
            for tf in ["1m", "5m", "15m"]:
                candles = self.client.get_klines(symbol, tf, limit=50)
                ohlcv_data[tf] = [
                    OHLCV(
                        open=float(c[1]),
                        high=float(c[2]),
                        low=float(c[3]),
                        close=float(c[4]),
                        volume=float(c[5]),
                        timestamp=int(c[0]),
                    )
                    for c in candles
                ]
            return ohlcv_data
        except Exception as e:
            logger.debug(f"Failed to get OHLCV for {symbol}: {e}")
            return None
    
    def _calculate_atr(self, candles: List[OHLCV], period: int = 14) -> float:
        """Calculate ATR from candles."""
        if len(candles) < period + 1:
            return candles[-1].close * 0.02 if candles else 0.0
        
        trs = []
        for i in range(1, len(candles)):
            high = candles[i].high
            low = candles[i].low
            prev_close = candles[i - 1].close
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close),
            )
            trs.append(tr)
        
        return sum(trs[-period:]) / period
    
    def _calculate_exposure(self) -> float:
        """Calculate current portfolio exposure."""
        try:
            positions = self.client.get_positions()
            total_value = sum(
                pos.quantity * pos.mark_price
                for pos in positions
                if pos.quantity * pos.mark_price >= 5
            )
            return total_value / self.capital if self.capital > 0 else 0.0
        except:
            return 0.0
    
    def stop(self):
        """Stop the engine."""
        self.running = False
