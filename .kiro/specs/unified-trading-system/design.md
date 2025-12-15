# Design Document

## Overview

The Unified Trading System transforms Kinetic Empire into a multi-engine trading platform that runs Spot and Futures strategies concurrently. The architecture follows a hub-and-spoke model where a central Orchestrator manages independent trading engines, each running in its own async task.

Key design principles:
1. **Configuration Centralization** - All strategy parameters in `config.py`, secrets in `.env`
2. **Engine Isolation** - Each engine operates independently with its own event loop
3. **Shared Risk Management** - Portfolio-wide circuit breakers protect total capital
4. **Graceful Degradation** - One engine's failure doesn't affect the other

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           start_backend.sh                               │
│                    (Entry Point - Activates venv, runs main.py)          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              main.py                                     │
│                         (Orchestrator Entry)                             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
┌─────────────────────────────┐     ┌─────────────────────────────┐
│       ConfigManager         │     │       EnvManager            │
│  (Loads config.py values)   │     │  (Loads .env credentials)   │
└─────────────────────────────┘     └─────────────────────────────┘
                    │                               │
                    └───────────────┬───────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           Orchestrator                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐ │
│  │ Capital Allocator│  │ Risk Monitor    │  │ Health Monitor          │ │
│  │ (Split portfolio)│  │ (Global limits) │  │ (Heartbeat tracking)    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                    │                               │
        ┌───────────┴───────────┐       ┌──────────┴──────────┐
        ▼                       ▼       ▼                      ▼
┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐
│   Spot Engine     │   │  Futures Engine   │   │  (Future: Options)│
│   (AsyncIO Task)  │   │  (AsyncIO Task)   │   │                   │
├───────────────────┤   ├───────────────────┤   └───────────────────┘
│ • SpotClient      │   │ • FuturesClient   │
│ • SpotStrategy    │   │ • FuturesStrategy │
│ • SpotRiskMgr     │   │ • FuturesRiskMgr  │
│ • SpotPositionMgr │   │ • FuturesPosMgr   │
└───────────────────┘   └───────────────────┘
        │                       │
        └───────────┬───────────┘
                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         Binance API                                      │
│              (Spot API)              (Futures API)                       │
└─────────────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. UnifiedConfig (config.py)

Centralized configuration dataclass at project root.

```python
@dataclass
class UnifiedConfig:
    """Master configuration for all trading engines."""
    
    # Global Settings
    global_daily_loss_limit_pct: float = 5.0
    global_max_drawdown_pct: float = 15.0
    global_circuit_breaker_cooldown_minutes: int = 60
    
    # Spot Engine Configuration
    spot_enabled: bool = True
    spot_capital_pct: float = 40.0
    spot_max_positions: int = 5
    spot_position_size_pct: float = 10.0
    spot_stop_loss_pct: float = 3.0
    spot_take_profit_pct: float = 6.0
    spot_watchlist: List[str] = field(default_factory=lambda: [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"
    ])
    spot_min_confidence: int = 60
    spot_scan_interval_seconds: int = 60
    
    # Futures Engine Configuration
    futures_enabled: bool = True
    futures_capital_pct: float = 60.0
    futures_max_positions: int = 3
    futures_position_size_min_pct: float = 5.0
    futures_position_size_max_pct: float = 15.0
    futures_leverage_min: int = 2
    futures_leverage_max: int = 10
    futures_regime_adx_trending: float = 25.0
    futures_regime_adx_sideways: float = 15.0
    futures_atr_stop_multiplier: float = 2.0
    futures_trailing_activation_pct: float = 2.0
    futures_watchlist: List[str] = field(default_factory=lambda: [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"
    ])
    futures_min_confidence: int = 50
    futures_scan_interval_seconds: int = 30
    futures_blacklist_duration_minutes: int = 60
    
    # Health Monitoring
    heartbeat_warning_seconds: int = 60
    heartbeat_restart_seconds: int = 300
    engine_restart_max_attempts: int = 3
```

### 2. Orchestrator

Main coordinator that manages engine lifecycle.

```python
class Orchestrator:
    """Manages multiple trading engines concurrently."""
    
    def __init__(self, config: UnifiedConfig, env: EnvConfig):
        self.config = config
        self.env = env
        self.engines: Dict[str, BaseEngine] = {}
        self.capital_allocator = CapitalAllocator(config)
        self.risk_monitor = GlobalRiskMonitor(config)
        self.health_monitor = HealthMonitor(config)
        self._running = False
    
    async def start(self) -> None:
        """Start all enabled engines."""
        
    async def stop(self) -> None:
        """Gracefully stop all engines."""
        
    async def _spawn_engine(self, engine_type: str) -> None:
        """Spawn a single engine as async task."""
        
    async def _monitor_loop(self) -> None:
        """Main monitoring loop for health and risk."""
        
    def get_combined_status(self) -> Dict[str, Any]:
        """Get combined portfolio status from all engines."""
```

### 3. CapitalAllocator

Manages capital distribution between engines.

```python
@dataclass
class CapitalAllocation:
    engine_name: str
    allocated_pct: float
    allocated_usd: float
    current_exposure_usd: float
    available_usd: float

class CapitalAllocator:
    """Allocates portfolio capital between engines."""
    
    def __init__(self, config: UnifiedConfig):
        self.config = config
        self._validate_allocation()
    
    def _validate_allocation(self) -> None:
        """Ensure total allocation <= 100%."""
        
    def get_allocation(self, engine_name: str, total_portfolio: float) -> CapitalAllocation:
        """Get capital allocation for an engine."""
        
    def reallocate_disabled_capital(self) -> None:
        """Redistribute capital from disabled engines."""
```

### 4. GlobalRiskMonitor

Portfolio-wide risk management.

```python
class GlobalRiskMonitor:
    """Monitors portfolio-wide risk limits."""
    
    def __init__(self, config: UnifiedConfig):
        self.config = config
        self.daily_pnl: float = 0.0
        self.peak_portfolio_value: float = 0.0
        self.circuit_breaker_active: bool = False
        self.circuit_breaker_until: Optional[datetime] = None
    
    def update_pnl(self, engine_name: str, pnl: float) -> None:
        """Update P&L from an engine."""
        
    def check_daily_loss_limit(self, portfolio_value: float) -> bool:
        """Check if daily loss limit exceeded."""
        
    def check_drawdown_limit(self, portfolio_value: float) -> bool:
        """Check if max drawdown exceeded."""
        
    def can_open_new_trade(self) -> bool:
        """Check if new trades are allowed."""
        
    def trigger_circuit_breaker(self, reason: str) -> None:
        """Activate circuit breaker."""
```

### 5. HealthMonitor

Tracks engine health via heartbeats.

```python
@dataclass
class EngineHealth:
    engine_name: str
    status: str  # "running", "stopped", "error", "restarting"
    last_heartbeat: datetime
    restart_count: int
    last_error: Optional[str]

class HealthMonitor:
    """Monitors engine health via heartbeats."""
    
    def __init__(self, config: UnifiedConfig):
        self.config = config
        self.engine_health: Dict[str, EngineHealth] = {}
    
    def record_heartbeat(self, engine_name: str) -> None:
        """Record heartbeat from engine."""
        
    def check_health(self) -> List[str]:
        """Check all engines, return list of unhealthy ones."""
        
    def should_restart(self, engine_name: str) -> bool:
        """Check if engine should be restarted."""
        
    def record_restart(self, engine_name: str) -> None:
        """Record restart attempt."""
```

### 6. BaseEngine (Abstract)

Base class for all trading engines.

```python
class BaseEngine(ABC):
    """Abstract base class for trading engines."""
    
    def __init__(self, name: str, config: UnifiedConfig, allocation: CapitalAllocation):
        self.name = name
        self.config = config
        self.allocation = allocation
        self._running = False
        self._heartbeat_callback: Optional[Callable] = None
    
    @abstractmethod
    async def start(self) -> None:
        """Start the engine's trading loop."""
        
    @abstractmethod
    async def stop(self) -> None:
        """Stop the engine gracefully."""
        
    @abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        
    def send_heartbeat(self) -> None:
        """Send heartbeat to orchestrator."""
```

### 7. SpotEngine

Spot trading implementation.

```python
class SpotEngine(BaseEngine):
    """Spot trading engine."""
    
    def __init__(self, config: UnifiedConfig, allocation: CapitalAllocation, client: BinanceSpotClient):
        super().__init__("spot", config, allocation)
        self.client = client
        self.positions: Dict[str, SpotPosition] = {}
        
    async def _scan_loop(self) -> None:
        """Scan for spot trading opportunities."""
        
    async def _monitor_loop(self) -> None:
        """Monitor open spot positions."""
        
    async def _execute_buy(self, symbol: str, amount_usd: float) -> None:
        """Execute spot buy order."""
        
    async def _execute_sell(self, symbol: str, quantity: float) -> None:
        """Execute spot sell order."""
```

### 8. FuturesEngine

Futures trading implementation (existing run_bot.py logic).

```python
class FuturesEngine(BaseEngine):
    """Futures trading engine with leverage."""
    
    def __init__(self, config: UnifiedConfig, allocation: CapitalAllocation, client: BinanceFuturesClient):
        super().__init__("futures", config, allocation)
        self.client = client
        # Reuse existing profitable trading components
        self.regime_detector = RegimeDetector()
        self.position_sizer = ConfidencePositionSizer()
        self.leverage_calculator = RegimeLeverageCalculator()
        # ... other components
```

## Data Models

```python
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

class EngineType(Enum):
    SPOT = "spot"
    FUTURES = "futures"

class EngineStatus(Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    RESTARTING = "restarting"

@dataclass
class EnvConfig:
    """Environment configuration from .env."""
    binance_api_key: str
    binance_api_secret: str
    binance_testnet: bool = True
    spot_enabled: bool = True
    futures_enabled: bool = True
    telegram_enabled: bool = False
    telegram_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None

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
    engines_status: Dict[str, EngineStatus]
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Engine spawning based on configuration
*For any* configuration with spot_enabled and futures_enabled flags, the Orchestrator SHALL spawn exactly the engines that are enabled.
**Validates: Requirements 1.1, 1.3**

### Property 2: Configuration loading completeness
*For any* valid config.py file, the ConfigManager SHALL load all strategy parameters with correct types and values.
**Validates: Requirements 2.1, 2.2**

### Property 3: Missing config validation
*For any* configuration missing required fields, the ConfigManager SHALL raise an error identifying the missing field.
**Validates: Requirements 2.4, 3.4**

### Property 4: Engine fault isolation
*For any* error in one engine, the other engine SHALL continue operating without interruption.
**Validates: Requirements 4.2, 4.3**

### Property 5: Capital allocation validation
*For any* configuration where spot_capital_pct + futures_capital_pct > 100, the ConfigManager SHALL raise a validation error.
**Validates: Requirements 7.2**

### Property 6: Capital allocation correctness
*For any* valid capital allocation, each engine SHALL receive exactly its configured percentage of total portfolio.
**Validates: Requirements 7.1, 7.4**

### Property 7: Disabled engine capital reallocation
*For any* configuration with one engine disabled, the enabled engine SHALL have access to 100% of portfolio capital.
**Validates: Requirements 7.3**

### Property 8: Global daily loss limit enforcement
*For any* combined daily loss exceeding global_daily_loss_limit_pct, both engines SHALL halt new trades.
**Validates: Requirements 8.2**

### Property 9: Global drawdown protection
*For any* portfolio drawdown exceeding global_max_drawdown_pct, both engines SHALL close all positions.
**Validates: Requirements 8.3**

### Property 10: Heartbeat timeout detection
*For any* engine that hasn't sent a heartbeat for heartbeat_warning_seconds, the HealthMonitor SHALL flag it as unhealthy.
**Validates: Requirements 9.2, 9.3**

### Property 11: Graceful shutdown completion
*For any* shutdown signal, all engines SHALL complete current operations before the Orchestrator exits.
**Validates: Requirements 10.2**

## Error Handling

1. **Missing Config File**: Use default values, log warning
2. **Invalid Config Values**: Raise ConfigValidationError with field name
3. **Missing API Keys**: Raise error before starting any engine
4. **Engine Crash**: Log error, attempt restart up to max_attempts
5. **API Connection Failure**: Retry with exponential backoff, halt after 5 failures
6. **Capital Allocation Overflow**: Raise error, refuse to start
7. **Circuit Breaker Trigger**: Halt all new trades, log event, notify via Telegram

## Testing Strategy

### Dual Testing Approach

**Unit Tests**: Verify specific examples, edge cases, and integration points
**Property-Based Tests**: Verify universal properties hold across all valid inputs

### Property-Based Testing Framework

Use **Hypothesis** library for Python property-based testing.

Each property test should:
- Run minimum 100 iterations
- Use smart generators that constrain to valid input ranges
- Be tagged with the property number and requirements reference

### Test Categories

1. **Configuration Tests**
   - Property test: config loading completeness
   - Property test: missing config validation
   - Property test: capital allocation validation
   - Unit test: default values

2. **Orchestrator Tests**
   - Property test: engine spawning based on config
   - Property test: fault isolation
   - Unit test: startup/shutdown sequence

3. **Capital Allocation Tests**
   - Property test: allocation correctness
   - Property test: disabled engine reallocation
   - Unit test: edge cases (0%, 100%)

4. **Risk Management Tests**
   - Property test: daily loss limit enforcement
   - Property test: drawdown protection
   - Unit test: circuit breaker cooldown

5. **Health Monitoring Tests**
   - Property test: heartbeat timeout detection
   - Unit test: restart logic

6. **Shutdown Tests**
   - Property test: graceful completion
   - Unit test: signal handling

