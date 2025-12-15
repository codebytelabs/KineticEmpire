"""Kinetic Engine v3.0 - Main Orchestrator.

Coordinates all modules for automated trading.
"""

import asyncio
import logging
from typing import Optional, List
from datetime import datetime

from src.kinetic_empire.v3.core.data_hub import DataHub
from src.kinetic_empire.v3.core.models import Signal, TradeResult
from src.kinetic_empire.v3.scanner.market_scanner import MarketScanner
from src.kinetic_empire.v3.analyzer.ta_analyzer import TAAnalyzer
from src.kinetic_empire.v3.manager.position_manager import PositionManager

logger = logging.getLogger(__name__)


class KineticEngine:
    """Main orchestrator for Kinetic Empire v3.0.
    
    Coordinates:
    - Market Scanner (every 60s)
    - TA Analyzer (on-demand)
    - Position Manager (every 5s)
    """

    def __init__(
        self,
        initial_capital: float = 10000.0,
        scan_interval: int = 60,
        monitor_interval: int = 5,
        max_opportunities: int = 10,
        live_trading: bool = False,
    ):
        """Initialize engine.
        
        Args:
            initial_capital: Starting capital
            scan_interval: Seconds between market scans
            monitor_interval: Seconds between position checks
            max_opportunities: Max opportunities to analyze per scan
            live_trading: Whether to execute real trades
        """
        self.initial_capital = initial_capital
        self.scan_interval = scan_interval
        self.monitor_interval = monitor_interval
        self.max_opportunities = max_opportunities
        self.live_trading = live_trading
        
        # Initialize modules
        self.data_hub = DataHub()
        self.scanner = MarketScanner(max_opportunities=max_opportunities)
        self.analyzer = TAAnalyzer()
        self.position_manager = PositionManager()
        
        # State
        self._running = False
        self._last_scan_time: Optional[datetime] = None
        self._trade_count = 0
        
        # Metrics
        self.metrics = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
        }

    async def start(self) -> None:
        """Start the trading engine."""
        logger.info("=" * 50)
        logger.info("🚀 Kinetic Empire v3.0 Starting")
        logger.info(f"💰 Initial Capital: ${self.initial_capital:,.2f}")
        logger.info(f"🔴 Live Trading: {self.live_trading}")
        logger.info(f"🔍 Scan Interval: {self.scan_interval}s")
        logger.info(f"👁️  Monitor Interval: {self.monitor_interval}s")
        logger.info(f"📊 Max Opportunities: {self.max_opportunities}")
        logger.info("=" * 50)
        
        self._running = True
        logger.debug("Engine state set to RUNNING")
        
        # Initialize account
        self.data_hub.update_account(
            balance=self.initial_capital,
            equity=self.initial_capital,
            margin_total=self.initial_capital,
        )
        logger.debug(f"Account initialized: balance=${self.initial_capital:,.2f}")
        
        logger.info("🔄 Starting scanner and monitor loops...")
        
        # Start main loops
        await asyncio.gather(
            self._scanner_loop(),
            self._monitor_loop(),
        )

    async def stop(self) -> None:
        """Stop the trading engine."""
        logger.info("Stopping Kinetic Empire v3.0...")
        self._running = False
        
        # Close all positions if live trading
        if self.live_trading:
            await self._close_all_positions("SHUTDOWN")
        
        # Log final metrics
        self._log_metrics()
        logger.info("Engine stopped")

    async def _scanner_loop(self) -> None:
        """Market scanner loop - runs every scan_interval seconds."""
        logger.debug("📡 Scanner loop started")
        cycle_count = 0
        while self._running:
            cycle_count += 1
            logger.debug(f"━━━ SCANNER CYCLE #{cycle_count} ━━━")
            try:
                await self._run_scan_cycle()
            except Exception as e:
                logger.error(f"❌ Scanner error: {e}", exc_info=True)
            
            logger.debug(f"💤 Scanner sleeping {self.scan_interval}s until next cycle...")
            await asyncio.sleep(self.scan_interval)

    async def _monitor_loop(self) -> None:
        """Position monitor loop - runs every monitor_interval seconds."""
        logger.debug("👁️  Monitor loop started")
        cycle_count = 0
        while self._running:
            cycle_count += 1
            try:
                positions_count = len(self.position_manager.positions)
                if positions_count > 0:
                    logger.debug(f"━━━ MONITOR CYCLE #{cycle_count} ({positions_count} positions) ━━━")
                await self._run_monitor_cycle()
            except Exception as e:
                logger.error(f"❌ Monitor error: {e}", exc_info=True)
            
            await asyncio.sleep(self.monitor_interval)

    async def _run_scan_cycle(self) -> None:
        """Run a single scan cycle."""
        from datetime import datetime
        start_time = datetime.now()
        logger.debug("🔍 Starting scan cycle...")
        
        # Get all tickers (in production, fetch from exchange)
        tickers = self.data_hub.get_all_tickers()
        logger.debug(f"📊 DataHub returned {len(tickers)} tickers")
        
        if not tickers:
            logger.debug("⚠️  No tickers available in DataHub - waiting for market data")
            return
        
        # Log ticker summary
        for t in tickers[:5]:  # Show first 5
            logger.debug(f"   📈 {t.symbol}: ${t.price:.4f} ({t.change_24h:+.2f}%)")
        if len(tickers) > 5:
            logger.debug(f"   ... and {len(tickers) - 5} more tickers")
        
        # Scan for opportunities
        logger.debug("🔎 Running market scanner...")
        opportunities = await self.scanner.scan(tickers)
        
        if not opportunities:
            logger.debug("😴 No opportunities found this cycle")
            return
        
        logger.info(f"🎯 Found {len(opportunities)} opportunities: {', '.join(opportunities[:5])}")
        
        # Analyze top opportunities
        logger.debug(f"📊 Analyzing top {min(len(opportunities), self.max_opportunities)} opportunities...")
        for i, symbol in enumerate(opportunities[:self.max_opportunities]):
            logger.debug(f"   [{i+1}] Analyzing {symbol}...")
            await self._analyze_and_trade(symbol)
        
        self._last_scan_time = datetime.now()
        duration = (self._last_scan_time - start_time).total_seconds()
        logger.debug(f"✅ Scan cycle complete in {duration:.2f}s")

    async def _analyze_and_trade(self, symbol: str) -> None:
        """Analyze symbol and potentially open trade."""
        logger.debug(f"      🔬 {symbol}: Fetching OHLCV data...")
        
        # Get OHLCV data
        ohlcv_4h = self.data_hub.get_ohlcv(symbol, "4h")
        ohlcv_1h = self.data_hub.get_ohlcv(symbol, "1h")
        ohlcv_15m = self.data_hub.get_ohlcv(symbol, "15m")
        
        logger.debug(f"      📊 {symbol}: 4h={len(ohlcv_4h) if ohlcv_4h else 0}, 1h={len(ohlcv_1h) if ohlcv_1h else 0}, 15m={len(ohlcv_15m) if ohlcv_15m else 0} candles")
        
        if not all([ohlcv_4h, ohlcv_1h, ohlcv_15m]):
            logger.debug(f"      ⚠️  {symbol}: Missing OHLCV data - skipping")
            return
        
        # Get current price
        current_price = self.data_hub.get_price(symbol)
        if not current_price:
            logger.debug(f"      ⚠️  {symbol}: No price data - skipping")
            return
        
        logger.debug(f"      💵 {symbol}: Current price ${current_price:.4f}")
        
        # Generate signal
        logger.debug(f"      🧠 {symbol}: Running TA analysis...")
        signal = await self.analyzer.analyze(
            symbol, current_price, ohlcv_4h, ohlcv_1h, ohlcv_15m
        )
        
        if not signal:
            logger.debug(f"      ❌ {symbol}: No signal generated")
            return
        
        logger.info(f"      ✨ {symbol}: SIGNAL {signal.direction} confidence={signal.confidence}%")
        logger.debug(f"         Entry: ${signal.entry_price:.4f}, SL: ${signal.stop_loss:.4f}, TP: ${signal.take_profit:.4f}")
        
        # Process signal
        account = self.data_hub.get_account()
        logger.debug(f"      💰 Account: equity=${account.equity:.2f}, margin_used=${account.margin_used:.2f}")
        
        position = await self.position_manager.process_signal(
            signal,
            equity=account.equity,
            margin_used=account.margin_used,
            margin_total=account.margin_total,
        )
        
        if position:
            self._trade_count += 1
            self.metrics["total_trades"] += 1
            logger.info(f"🎉 TRADE #{self._trade_count}: {symbol} {position.side} @ ${position.entry_price:.4f}")
            logger.info(f"   Size: {position.size:.4f}, Leverage: {position.leverage}x, Confidence: {position.confidence}%")
            
            # Sync positions to data hub
            self.data_hub.sync_positions(self.position_manager.positions)
            logger.debug(f"      📝 Position synced to DataHub")
        else:
            logger.debug(f"      ⛔ {symbol}: Signal rejected by position manager")

    async def _run_monitor_cycle(self) -> None:
        """Run a single position monitoring cycle."""
        positions = self.position_manager.get_all_positions()
        if not positions:
            return
        
        # Get current prices
        current_prices = self.data_hub.get_all_prices()
        account = self.data_hub.get_account()
        
        # Log position status
        for pos in positions:
            if pos.symbol in current_prices:
                price = current_prices[pos.symbol]
                pnl_pct = pos.calc_pnl_pct(price)
                pnl_amt = pos.calc_pnl_amount(price)
                logger.debug(
                    f"   📍 {pos.symbol}: {pos.side} @ ${pos.entry_price:.4f} → ${price:.4f} "
                    f"| P&L: {pnl_pct:+.2f}% (${pnl_amt:+.2f}) | Peak: {pos.peak_pnl:+.2f}%"
                )
        
        # Monitor positions
        actions = await self.position_manager.monitor_positions(
            current_prices, account.equity
        )
        
        # Handle stop losses
        for symbol, reason in actions.get("stop_losses", []):
            logger.warning(f"🛑 {symbol}: STOP LOSS triggered - {reason}")
            await self._close_position(symbol, reason)
        
        # Handle emergencies
        for symbol, reason in actions.get("emergencies", []):
            logger.critical(f"🚨 {symbol}: EMERGENCY EXIT - {reason}")
            await self._close_position(symbol, reason)
        
        # Handle take profits (partial closes)
        for symbol, level, pct in actions.get("take_profits", []):
            logger.info(f"💰 {symbol}: TP{level} hit - closing {pct}%")
            # In production, would execute partial close order
        
        # Log trailing stop updates
        for symbol in actions.get("trailing_updates", []):
            pos = self.position_manager.get_position(symbol)
            if pos and pos.trailing_stop:
                logger.debug(f"   🔄 {symbol}: Trailing stop updated to ${pos.trailing_stop:.4f}")

    async def _close_position(self, symbol: str, reason: str) -> None:
        """Close a position."""
        position = self.position_manager.get_position(symbol)
        if not position:
            return
        
        current_price = self.data_hub.get_price(symbol)
        if not current_price:
            return
        
        # Calculate P&L
        pnl_pct = position.calc_pnl_pct(current_price)
        pnl_amount = position.calc_pnl_amount(current_price)
        
        # Update metrics
        self.metrics["total_pnl"] += pnl_amount
        if pnl_amount > 0:
            self.metrics["winning_trades"] += 1
        else:
            self.metrics["losing_trades"] += 1
        
        # Calculate win rate
        total = self.metrics["winning_trades"] + self.metrics["losing_trades"]
        if total > 0:
            self.metrics["win_rate"] = self.metrics["winning_trades"] / total * 100
        
        # Remove position
        self.position_manager.remove_position(symbol, pnl_amount)
        
        # Create trade result
        trade_result = TradeResult(
            symbol=symbol,
            side=position.side,
            entry_price=position.entry_price,
            exit_price=current_price,
            size=position.size,
            leverage=position.leverage,
            pnl_pct=pnl_pct,
            pnl_amount=pnl_amount,
            exit_reason=reason,
            confidence=position.confidence,
            entry_time=position.entry_time,
        )
        
        self.position_manager.trade_history.append(trade_result)
        
        logger.info(
            f"Closed {symbol}: {reason} | P&L: {pnl_pct:+.2f}% (${pnl_amount:+.2f})"
        )
        
        # Sync positions
        self.data_hub.sync_positions(self.position_manager.positions)

    async def _close_all_positions(self, reason: str) -> None:
        """Close all open positions."""
        positions = list(self.position_manager.positions.keys())
        for symbol in positions:
            await self._close_position(symbol, reason)

    def _log_metrics(self) -> None:
        """Log current metrics."""
        logger.info("=" * 50)
        logger.info("Trading Metrics")
        logger.info(f"Total Trades: {self.metrics['total_trades']}")
        logger.info(f"Winning: {self.metrics['winning_trades']}")
        logger.info(f"Losing: {self.metrics['losing_trades']}")
        logger.info(f"Win Rate: {self.metrics['win_rate']:.1f}%")
        logger.info(f"Total P&L: ${self.metrics['total_pnl']:+,.2f}")
        logger.info("=" * 50)

    def get_status(self) -> dict:
        """Get current engine status."""
        return {
            "running": self._running,
            "live_trading": self.live_trading,
            "positions": len(self.position_manager.positions),
            "trade_count": self._trade_count,
            "last_scan": self._last_scan_time,
            "metrics": self.metrics.copy(),
        }
