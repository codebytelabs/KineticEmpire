"""Orchestrator for Unified Trading System.

Main coordinator that manages multiple trading engines concurrently.
"""

import asyncio
import logging
import signal
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from .config import UnifiedConfig, EnvConfig, ConfigValidationError
from .capital_allocator import CapitalAllocator
from .risk_monitor import GlobalRiskMonitor
from .health_monitor import HealthMonitor, EngineStatus
from .base_engine import BaseEngine

logger = logging.getLogger(__name__)


@dataclass
class PortfolioStatus:
    """Combined portfolio status."""
    total_value_usd: float
    spot_value_usd: float
    futures_value_usd: float
    spot_pnl_usd: float
    futures_pnl_usd: float
    total_pnl_usd: float
    total_pnl_pct: float
    spot_positions: int
    futures_positions: int
    circuit_breaker_active: bool
    engines_status: Dict[str, str]


class Orchestrator:
    """Manages multiple trading engines concurrently.
    
    Coordinates engine lifecycle, monitors health and risk,
    and handles graceful shutdown.
    """
    
    def __init__(self, config: UnifiedConfig, env: EnvConfig):
        """Initialize orchestrator.
        
        Args:
            config: Unified configuration.
            env: Environment configuration.
        """
        self.config = config
        self.env = env
        self.engines: Dict[str, BaseEngine] = {}
        self._engine_tasks: Dict[str, asyncio.Task] = {}
        self.capital_allocator = CapitalAllocator(config)
        self.risk_monitor = GlobalRiskMonitor(config)
        self.health_monitor = HealthMonitor(config)
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._starting_balance: float = 0.0
        
        # Set up callbacks
        self.health_monitor.set_restart_callback(self._on_engine_restart_needed)
        self.risk_monitor.set_circuit_breaker_callback(self._on_circuit_breaker)
    
    def register_engine(self, engine: BaseEngine) -> None:
        """Register an engine with the orchestrator.
        
        Args:
            engine: Engine instance to register.
        """
        self.engines[engine.name] = engine
        self.health_monitor.register_engine(engine.name)
        engine.set_heartbeat_callback(self._on_heartbeat)
        logger.info(f"📝 Registered engine: {engine.name}")
    
    async def start(self) -> None:
        """Start all enabled engines."""
        self._running = True
        
        logger.info("=" * 70)
        logger.info("🚀 UNIFIED TRADING SYSTEM - STARTING")
        logger.info("=" * 70)
        
        # Log configuration
        logger.info(f"   📊 Spot Engine: {'ENABLED' if self.env.spot_enabled else 'DISABLED'}")
        logger.info(f"   📊 Futures Engine: {'ENABLED' if self.env.futures_enabled else 'DISABLED'}")
        logger.info(f"   💰 Spot Capital: {self.config.spot_capital_pct}%")
        logger.info(f"   💰 Futures Capital: {self.config.futures_capital_pct}%")
        logger.info(f"   🛡️ Daily Loss Limit: {self.config.global_daily_loss_limit_pct}%")
        logger.info(f"   🛡️ Max Drawdown: {self.config.global_max_drawdown_pct}%")
        logger.info("=" * 70)
        
        # Spawn enabled engines
        for name, engine in self.engines.items():
            if self._should_spawn_engine(name):
                await self._spawn_engine(engine)
            else:
                logger.info(f"   ⏭️ Skipping disabled engine: {name}")
        
        # Start monitoring loop
        monitor_task = asyncio.create_task(self._monitor_loop())
        
        # Wait for shutdown signal
        await self._shutdown_event.wait()
        
        # Cancel monitoring
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
        
        logger.info("🛑 Orchestrator stopped")
    
    async def stop(self) -> None:
        """Gracefully stop all engines."""
        logger.info("👋 Initiating graceful shutdown...")
        self._running = False
        
        # Signal all engines to stop
        for engine in self.engines.values():
            engine.request_shutdown()
        
        # Wait for engines to complete
        for name, task in self._engine_tasks.items():
            if not task.done():
                logger.info(f"   ⏳ Waiting for {name} to complete...")
                try:
                    await asyncio.wait_for(task, timeout=30.0)
                except asyncio.TimeoutError:
                    logger.warning(f"   ⚠️ {name} did not stop in time, cancelling...")
                    task.cancel()
                except asyncio.CancelledError:
                    pass
        
        # Log final status
        await self._log_final_status()
        
        # Signal shutdown complete
        self._shutdown_event.set()
    
    def _should_spawn_engine(self, engine_name: str) -> bool:
        """Check if engine should be spawned based on config.
        
        Args:
            engine_name: Name of the engine.
            
        Returns:
            True if engine should be spawned.
        """
        if engine_name == "spot":
            return self.env.spot_enabled and self.config.spot_enabled
        elif engine_name == "futures":
            return self.env.futures_enabled and self.config.futures_enabled
        return False
    
    async def _spawn_engine(self, engine: BaseEngine) -> None:
        """Spawn a single engine as async task.
        
        Args:
            engine: Engine to spawn.
        """
        logger.info(f"   🚀 Spawning engine: {engine.name}")
        self.health_monitor.record_start(engine.name)
        
        async def run_engine():
            try:
                await engine.start()
            except Exception as e:
                logger.error(f"❌ {engine.name} crashed: {e}")
                self.health_monitor.record_error(engine.name, str(e))
                # Attempt restart if allowed
                if self.health_monitor.can_restart(engine.name):
                    await self._restart_engine(engine)
            finally:
                self.health_monitor.record_stop(engine.name)
        
        task = asyncio.create_task(run_engine())
        self._engine_tasks[engine.name] = task
    
    async def _restart_engine(self, engine: BaseEngine) -> None:
        """Restart a crashed engine.
        
        Args:
            engine: Engine to restart.
        """
        if not self._running:
            return
        
        self.health_monitor.record_restart(engine.name)
        logger.info(f"🔄 Restarting engine: {engine.name}")
        
        # Wait a bit before restart
        await asyncio.sleep(5.0)
        
        if self._running:
            await self._spawn_engine(engine)
    
    async def _monitor_loop(self) -> None:
        """Main monitoring loop for health and risk."""
        while self._running:
            try:
                # Check engine health
                unhealthy = self.health_monitor.check_health()
                
                # Get current portfolio value
                total_value = await self._get_total_portfolio_value()
                
                # Set starting value if not set
                if self._starting_balance == 0 and total_value > 0:
                    self._starting_balance = total_value
                    self.risk_monitor.set_starting_value(total_value)
                
                # Update P&L from engines
                for name, engine in self.engines.items():
                    if engine.is_running:
                        pnl_usd, _ = await engine.get_total_pnl()
                        self.risk_monitor.update_pnl(name, pnl_usd)
                
                # Check risk limits
                if total_value > 0:
                    trigger_reason = self.risk_monitor.check_and_trigger(total_value)
                    if trigger_reason:
                        await self._handle_circuit_breaker(trigger_reason)
                
                # Log status periodically
                await self._log_status()
                
                await asyncio.sleep(10.0)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                await asyncio.sleep(5.0)
    
    async def _get_total_portfolio_value(self) -> float:
        """Get total portfolio value from all engines.
        
        Returns:
            Total portfolio value in USD.
        """
        total = 0.0
        for engine in self.engines.values():
            if engine.is_running:
                try:
                    status = await engine.get_status()
                    total += status.get("portfolio_value", 0.0)
                except Exception:
                    pass
        return total
    
    async def _handle_circuit_breaker(self, reason: str) -> None:
        """Handle circuit breaker trigger.
        
        Args:
            reason: Reason for circuit breaker.
        """
        logger.warning(f"🚨 CIRCUIT BREAKER: {reason}")
        
        # If max drawdown, close all positions
        if "drawdown" in reason.lower():
            logger.warning("📉 Max drawdown exceeded - closing all positions!")
            for engine in self.engines.values():
                if engine.is_running:
                    try:
                        await engine.close_all_positions()
                    except Exception as e:
                        logger.error(f"Failed to close positions for {engine.name}: {e}")
    
    def _on_heartbeat(self, engine_name: str) -> None:
        """Handle heartbeat from engine.
        
        Args:
            engine_name: Name of the engine.
        """
        self.health_monitor.record_heartbeat(engine_name)
    
    def _on_engine_restart_needed(self, engine_name: str) -> None:
        """Handle engine restart needed event.
        
        Args:
            engine_name: Name of the engine.
        """
        if engine_name in self.engines and self._running:
            asyncio.create_task(self._restart_engine(self.engines[engine_name]))
    
    def _on_circuit_breaker(self, reason: str) -> None:
        """Handle circuit breaker event.
        
        Args:
            reason: Reason for circuit breaker.
        """
        # Could send Telegram notification here
        pass
    
    async def _log_status(self) -> None:
        """Log current status."""
        status = await self.get_combined_status()
        
        logger.debug(
            f"📊 Portfolio: ${status.total_value_usd:.2f} | "
            f"P&L: ${status.total_pnl_usd:+.2f} ({status.total_pnl_pct:+.2f}%) | "
            f"Positions: Spot={status.spot_positions}, Futures={status.futures_positions}"
        )
    
    async def _log_final_status(self) -> None:
        """Log final portfolio state."""
        logger.info("=" * 70)
        logger.info("📊 FINAL PORTFOLIO STATUS")
        logger.info("=" * 70)
        
        for name, engine in self.engines.items():
            try:
                status = await engine.get_status()
                pnl_usd, pnl_pct = await engine.get_total_pnl()
                positions = await engine.get_positions_count()
                
                logger.info(f"   {name.upper()}:")
                logger.info(f"      Positions: {positions}")
                logger.info(f"      P&L: ${pnl_usd:+.2f} ({pnl_pct:+.2f}%)")
            except Exception as e:
                logger.info(f"   {name.upper()}: Unable to get status - {e}")
        
        logger.info("=" * 70)
    
    async def get_combined_status(self) -> PortfolioStatus:
        """Get combined portfolio status from all engines.
        
        Returns:
            PortfolioStatus with combined values.
        """
        spot_value = 0.0
        futures_value = 0.0
        spot_pnl = 0.0
        futures_pnl = 0.0
        spot_positions = 0
        futures_positions = 0
        
        for name, engine in self.engines.items():
            if engine.is_running:
                try:
                    pnl_usd, _ = await engine.get_total_pnl()
                    positions = await engine.get_positions_count()
                    status = await engine.get_status()
                    
                    if name == "spot":
                        spot_value = status.get("portfolio_value", 0.0)
                        spot_pnl = pnl_usd
                        spot_positions = positions
                    elif name == "futures":
                        futures_value = status.get("portfolio_value", 0.0)
                        futures_pnl = pnl_usd
                        futures_positions = positions
                except Exception:
                    pass
        
        total_value = spot_value + futures_value
        total_pnl = spot_pnl + futures_pnl
        total_pnl_pct = (total_pnl / self._starting_balance * 100) if self._starting_balance > 0 else 0.0
        
        return PortfolioStatus(
            total_value_usd=total_value,
            spot_value_usd=spot_value,
            futures_value_usd=futures_value,
            spot_pnl_usd=spot_pnl,
            futures_pnl_usd=futures_pnl,
            total_pnl_usd=total_pnl,
            total_pnl_pct=total_pnl_pct,
            spot_positions=spot_positions,
            futures_positions=futures_positions,
            circuit_breaker_active=not self.risk_monitor.can_open_new_trade(),
            engines_status=self.health_monitor.get_status_summary(),
        )
    
    def setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        def handle_signal(sig, frame):
            logger.info(f"👋 Received signal {sig}, initiating shutdown...")
            asyncio.create_task(self.stop())
        
        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)
