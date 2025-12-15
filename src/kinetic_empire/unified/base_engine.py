"""Base Engine for Unified Trading System.

Abstract base class for all trading engines (Spot, Futures, etc.).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, Optional
import asyncio
import logging

from .config import UnifiedConfig
from .capital_allocator import CapitalAllocation

logger = logging.getLogger(__name__)


@dataclass
class EngineState:
    """Current state of an engine."""
    name: str
    running: bool
    positions_count: int
    total_pnl_usd: float
    total_pnl_pct: float
    last_scan_time: Optional[datetime]
    last_trade_time: Optional[datetime]


class BaseEngine(ABC):
    """Abstract base class for trading engines.
    
    Provides common functionality for heartbeat sending, graceful shutdown,
    and status reporting. Concrete implementations must implement the
    trading loop logic.
    """
    
    def __init__(
        self,
        name: str,
        config: UnifiedConfig,
        allocation: CapitalAllocation,
    ):
        """Initialize base engine.
        
        Args:
            name: Engine name (e.g., "spot", "futures").
            config: Unified configuration.
            allocation: Capital allocation for this engine.
        """
        self.name = name
        self.config = config
        self.allocation = allocation
        self._running = False
        self._shutdown_requested = False
        self._heartbeat_callback: Optional[Callable[[str], None]] = None
        self._current_operation: Optional[str] = None
        self._last_scan_time: Optional[datetime] = None
        self._last_trade_time: Optional[datetime] = None
    
    @abstractmethod
    async def start(self) -> None:
        """Start the engine's trading loop.
        
        Must be implemented by concrete engines.
        """
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop the engine gracefully.
        
        Must be implemented by concrete engines.
        Should complete current operations before returning.
        """
        pass
    
    @abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        """Get engine status.
        
        Must be implemented by concrete engines.
        
        Returns:
            Dictionary with engine status information.
        """
        pass
    
    @abstractmethod
    async def get_positions_count(self) -> int:
        """Get number of open positions.
        
        Returns:
            Number of open positions.
        """
        pass
    
    @abstractmethod
    async def get_total_pnl(self) -> tuple[float, float]:
        """Get total P&L.
        
        Returns:
            Tuple of (pnl_usd, pnl_pct).
        """
        pass
    
    @abstractmethod
    async def close_all_positions(self) -> None:
        """Close all open positions.
        
        Called when circuit breaker triggers max drawdown.
        """
        pass
    
    def send_heartbeat(self) -> None:
        """Send heartbeat to orchestrator."""
        if self._heartbeat_callback:
            self._heartbeat_callback(self.name)
    
    def set_heartbeat_callback(self, callback: Callable[[str], None]) -> None:
        """Set heartbeat callback.
        
        Args:
            callback: Function to call with engine name.
        """
        self._heartbeat_callback = callback
    
    def request_shutdown(self) -> None:
        """Request graceful shutdown."""
        self._shutdown_requested = True
        logger.info(f"🛑 {self.name}: Shutdown requested")
    
    def is_shutdown_requested(self) -> bool:
        """Check if shutdown has been requested.
        
        Returns:
            True if shutdown was requested.
        """
        return self._shutdown_requested
    
    @property
    def is_running(self) -> bool:
        """Check if engine is running.
        
        Returns:
            True if engine is running.
        """
        return self._running
    
    def get_state(self) -> EngineState:
        """Get current engine state.
        
        Returns:
            EngineState with current values.
        """
        return EngineState(
            name=self.name,
            running=self._running,
            positions_count=0,  # Override in subclass
            total_pnl_usd=0.0,
            total_pnl_pct=0.0,
            last_scan_time=self._last_scan_time,
            last_trade_time=self._last_trade_time,
        )
    
    async def _run_with_heartbeat(self, coro, operation_name: str):
        """Run a coroutine while sending heartbeats.
        
        Args:
            coro: Coroutine to run.
            operation_name: Name of the operation for logging.
            
        Returns:
            Result of the coroutine.
        """
        self._current_operation = operation_name
        try:
            self.send_heartbeat()
            result = await coro
            self.send_heartbeat()
            return result
        finally:
            self._current_operation = None
    
    async def _wait_for_completion(self, timeout_seconds: float = 30.0) -> bool:
        """Wait for current operation to complete.
        
        Args:
            timeout_seconds: Maximum time to wait.
            
        Returns:
            True if completed within timeout.
        """
        start = datetime.now()
        while self._current_operation:
            if (datetime.now() - start).total_seconds() > timeout_seconds:
                logger.warning(
                    f"⚠️ {self.name}: Timeout waiting for {self._current_operation}"
                )
                return False
            await asyncio.sleep(0.1)
        return True
