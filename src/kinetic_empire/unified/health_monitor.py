"""Health Monitor for Unified Trading System.

Tracks engine health via heartbeats and manages restart logic.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Callable
import logging

from .config import UnifiedConfig

logger = logging.getLogger(__name__)


class EngineStatus(Enum):
    """Engine status enumeration."""
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    RESTARTING = "restarting"


@dataclass
class EngineHealth:
    """Health state for a single engine."""
    engine_name: str
    status: EngineStatus = EngineStatus.STOPPED
    last_heartbeat: Optional[datetime] = None
    restart_count: int = 0
    last_error: Optional[str] = None
    started_at: Optional[datetime] = None


class HealthMonitor:
    """Monitors engine health via heartbeats.
    
    Tracks last heartbeat timestamp for each engine and triggers
    warnings or restarts when thresholds are exceeded.
    """
    
    def __init__(self, config: UnifiedConfig):
        """Initialize health monitor.
        
        Args:
            config: Unified configuration with health thresholds.
        """
        self.config = config
        self._engine_health: Dict[str, EngineHealth] = {}
        self._on_warning: Optional[Callable[[str, str], None]] = None
        self._on_restart_needed: Optional[Callable[[str], None]] = None
    
    def register_engine(self, engine_name: str) -> None:
        """Register an engine for health monitoring.
        
        Args:
            engine_name: Name of the engine.
        """
        self._engine_health[engine_name] = EngineHealth(
            engine_name=engine_name,
            status=EngineStatus.STOPPED,
        )
    
    def record_heartbeat(self, engine_name: str) -> None:
        """Record heartbeat from engine.
        
        Args:
            engine_name: Name of the engine.
        """
        if engine_name not in self._engine_health:
            self.register_engine(engine_name)
        
        health = self._engine_health[engine_name]
        health.last_heartbeat = datetime.now()
        health.status = EngineStatus.RUNNING
    
    def record_start(self, engine_name: str) -> None:
        """Record engine start.
        
        Args:
            engine_name: Name of the engine.
        """
        if engine_name not in self._engine_health:
            self.register_engine(engine_name)
        
        health = self._engine_health[engine_name]
        health.status = EngineStatus.RUNNING
        health.started_at = datetime.now()
        health.last_heartbeat = datetime.now()
        health.last_error = None
    
    def record_stop(self, engine_name: str) -> None:
        """Record engine stop.
        
        Args:
            engine_name: Name of the engine.
        """
        if engine_name in self._engine_health:
            self._engine_health[engine_name].status = EngineStatus.STOPPED
    
    def record_error(self, engine_name: str, error: str) -> None:
        """Record engine error.
        
        Args:
            engine_name: Name of the engine.
            error: Error message.
        """
        if engine_name not in self._engine_health:
            self.register_engine(engine_name)
        
        health = self._engine_health[engine_name]
        health.status = EngineStatus.ERROR
        health.last_error = error
    
    def record_restart(self, engine_name: str) -> None:
        """Record restart attempt.
        
        Args:
            engine_name: Name of the engine.
        """
        if engine_name in self._engine_health:
            health = self._engine_health[engine_name]
            health.restart_count += 1
            health.status = EngineStatus.RESTARTING
    
    def check_health(self) -> List[str]:
        """Check all engines, return list of unhealthy ones.
        
        Returns:
            List of unhealthy engine names.
        """
        unhealthy = []
        now = datetime.now()
        
        for name, health in self._engine_health.items():
            if health.status == EngineStatus.STOPPED:
                continue
            
            if health.last_heartbeat is None:
                unhealthy.append(name)
                continue
            
            seconds_since_heartbeat = (now - health.last_heartbeat).total_seconds()
            
            # Check restart threshold
            if seconds_since_heartbeat >= self.config.heartbeat_restart_seconds:
                unhealthy.append(name)
                if self._on_restart_needed:
                    self._on_restart_needed(name)
                logger.error(
                    f"🚨 {name}: No heartbeat for {seconds_since_heartbeat:.0f}s - RESTART NEEDED"
                )
            # Check warning threshold
            elif seconds_since_heartbeat >= self.config.heartbeat_warning_seconds:
                if self._on_warning:
                    self._on_warning(name, f"No heartbeat for {seconds_since_heartbeat:.0f}s")
                logger.warning(
                    f"⚠️ {name}: No heartbeat for {seconds_since_heartbeat:.0f}s"
                )
        
        return unhealthy
    
    def should_restart(self, engine_name: str) -> bool:
        """Check if engine should be restarted.
        
        Args:
            engine_name: Name of the engine.
            
        Returns:
            True if engine should be restarted.
        """
        if engine_name not in self._engine_health:
            return False
        
        health = self._engine_health[engine_name]
        
        # Don't restart if max attempts exceeded
        if health.restart_count >= self.config.engine_restart_max_attempts:
            logger.error(
                f"🛑 {engine_name}: Max restart attempts ({health.restart_count}) exceeded"
            )
            return False
        
        # Check if heartbeat timeout exceeded
        if health.last_heartbeat is None:
            return health.status == EngineStatus.ERROR
        
        seconds_since_heartbeat = (datetime.now() - health.last_heartbeat).total_seconds()
        return seconds_since_heartbeat >= self.config.heartbeat_restart_seconds
    
    def can_restart(self, engine_name: str) -> bool:
        """Check if engine can be restarted (hasn't exceeded max attempts).
        
        Args:
            engine_name: Name of the engine.
            
        Returns:
            True if restart is allowed.
        """
        if engine_name not in self._engine_health:
            return True
        
        return self._engine_health[engine_name].restart_count < self.config.engine_restart_max_attempts
    
    def get_health(self, engine_name: str) -> Optional[EngineHealth]:
        """Get health state for an engine.
        
        Args:
            engine_name: Name of the engine.
            
        Returns:
            EngineHealth or None if not registered.
        """
        return self._engine_health.get(engine_name)
    
    def get_all_health(self) -> Dict[str, EngineHealth]:
        """Get health state for all engines.
        
        Returns:
            Dictionary of engine name to EngineHealth.
        """
        return self._engine_health.copy()
    
    def get_status_summary(self) -> Dict[str, str]:
        """Get status summary for all engines.
        
        Returns:
            Dictionary of engine name to status string.
        """
        return {
            name: health.status.value
            for name, health in self._engine_health.items()
        }
    
    def set_warning_callback(self, callback: Callable[[str, str], None]) -> None:
        """Set callback for warning events.
        
        Args:
            callback: Function(engine_name, message) to call on warnings.
        """
        self._on_warning = callback
    
    def set_restart_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for restart needed events.
        
        Args:
            callback: Function(engine_name) to call when restart is needed.
        """
        self._on_restart_needed = callback
