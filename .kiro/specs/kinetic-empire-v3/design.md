# Design Document: Kinetic Empire v3.0

## Overview

Kinetic Empire v3.0 is a professional-grade modular cryptocurrency futures trading system built on a three-pillar architecture: Market Scanner, Technical Analyzer, and Position Manager. The system is designed for Binance Futures with dynamic leverage scaling (2x-20x) based on signal confidence, multi-timeframe technical analysis, and comprehensive risk management.

The architecture prioritizes:
- **Modularity**: Each component is independent and testable
- **Low Latency**: Position monitoring every 5 seconds, WebSocket feeds
- **Risk Management**: Multiple layers of protection against losses
- **Profitability**: Confidence-based leverage and position sizing to maximize edge

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        KINETIC ENGINE                           │
│                     (Main Orchestrator)                         │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  MARKET SCANNER │  │   TA ANALYZER   │  │POSITION MANAGER │
│  (Discovery)    │  │  (Scoring)      │  │ (Execution)     │
│                 │  │                 │  │                 │
│ • Volume Filter │  │ • MTF Analysis  │  │ • Risk Checks   │
│ • Momentum      │  │ • EMA/RSI/MACD  │  │ • Dynamic Lev   │
│ • Hot Tickers   │  │ • ATR Stops     │  │ • Trailing SL   │
│                 │  │ • Scoring       │  │ • Partial TP    │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              ▼
              ┌───────────────────────────────┐
              │          DATA HUB             │
              │   (Shared State & Feeds)      │
              │                               │
              │ • WebSocket Price Feeds       │
              │ • OHLCV Cache                 │
              │ • Position State              │
              │ • Account Balance             │
              └───────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │      BINANCE FUTURES API      │
              └───────────────────────────────┘
```

## Components and Interfaces

### 1. Data Hub (core/data_hub.py)

Central data management with real-time feeds and shared state.

```python
class DataHub:
    """Manages all market data and shared state."""
    
    async def connect_websocket() -> None
    async def get_ticker(symbol: str) -> Ticker
    async def get_ohlcv(symbol: str, timeframe: str, limit: int) -> List[OHLCV]
    def get_account_balance() -> float
    def get_positions() -> Dict[str, Position]
    def update_position(symbol: str, position: Position) -> None
```

### 2. Market Scanner (scanner/market_scanner.py)

Discovers trading opportunities by filtering the market.

```python
class MarketScanner:
    """Scans market for high-potential opportunities."""
    
    async def scan() -> List[str]  # Returns hot ticker symbols
    def filter_by_volume(tickers: List[Ticker]) -> List[Ticker]
    def filter_by_momentum(tickers: List[Ticker]) -> List[Ticker]
    def rank_opportunities(tickers: List[Ticker]) -> List[str]
```

### 3. Technical Analyzer (analyzer/ta_analyzer.py)

Multi-timeframe analysis and signal generation.

```python
class TAAnalyzer:
    """Performs multi-timeframe technical analysis."""
    
    async def analyze(symbol: str) -> Signal
    def calculate_indicators(ohlcv: List[OHLCV]) -> Indicators
    def score_opportunity(indicators_4h, indicators_1h, indicators_15m) -> int
    def calculate_entry_exit(indicators: Indicators, direction: str) -> Tuple[float, float, float]

class Indicators:
    ema_9: float
    ema_21: float
    rsi: float
    macd_line: float
    macd_signal: float
    macd_histogram: float
    atr: float
    volume_ratio: float
```

### 4. Position Manager (manager/position_manager.py)

Handles all position lifecycle with risk management.

```python
class PositionManager:
    """Manages position lifecycle with dynamic leverage."""
    
    async def process_signal(signal: Signal) -> Optional[Trade]
    def check_risk_limits() -> Tuple[bool, str]
    def calculate_leverage(confidence: int, volatility: float) -> int
    def calculate_position_size(equity: float, risk_pct: float, entry: float, stop: float) -> float
    async def monitor_positions() -> None
    async def update_trailing_stops() -> None
    async def check_take_profits() -> None
    async def emergency_check() -> None
```

### 5. Signal Model (core/models.py)

```python
@dataclass
class Signal:
    symbol: str
    direction: Literal['LONG', 'SHORT']
    confidence: int  # 0-100
    entry_price: float
    stop_loss: float
    take_profit: float
    atr: float
    timeframe_alignment: bool
    indicators: Dict[str, Indicators]
    timestamp: datetime

@dataclass
class Position:
    symbol: str
    side: Literal['LONG', 'SHORT']
    entry_price: float
    size: float
    leverage: int
    stop_loss: float
    take_profit: float
    trailing_stop: Optional[float]
    partial_exits: List[float]  # Prices where partial exits occurred
    peak_pnl: float
    entry_time: datetime
```

## Data Models

### Scoring System

| Factor | Points | Long Condition | Short Condition |
|--------|--------|----------------|-----------------|
| 4H EMA Trend | 25 | EMA9 > EMA21 | EMA9 < EMA21 |
| 1H Trend Alignment | 20 | Same as 4H | Same as 4H |
| RSI Zone | 15 | 30-45 | 55-70 |
| MACD Cross | 15 | Bullish cross | Bearish cross |
| Volume Spike | 10 | >1.5x average | >1.5x average |
| Price Action | 15 | HH/HL pattern | LH/LL pattern |
| **Total** | **100** | | |

### Leverage Scaling

| Confidence Score | Base Leverage | High Volatility |
|-----------------|---------------|-----------------|
| 60-69 | 5x | 2x |
| 70-79 | 10x | 5x |
| 80-89 | 15x | 7x |
| 90-100 | 20x | 10x |

### Position Sizing

| Confidence Score | Risk % | Max Position |
|-----------------|--------|--------------|
| 60-69 | 1.0% | 20% equity |
| 70-79 | 1.0% | 20% equity |
| 80-89 | 1.5% | 25% equity |
| 90-100 | 2.0% | 25% equity |

### Take Profit Levels

| Level | Profit % | Action |
|-------|----------|--------|
| TP1 | +1.5% | Close 40% |
| TP2 | +2.5% | Close 30% |
| TP3 | +3.0%+ | Trail remaining 30% |

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Volume Filter Correctness
*For any* list of tickers with volume data, the Market_Scanner volume filter SHALL return only tickers where current volume exceeds 1.5x the 20-period average volume.
**Validates: Requirements 1.2**

### Property 2: Momentum Filter Correctness
*For any* list of tickers with price data, the Market_Scanner momentum filter SHALL return only tickers where absolute 24h price change exceeds 1%.
**Validates: Requirements 1.3**

### Property 3: EMA Calculation Correctness
*For any* valid OHLCV data series, the calculated EMA(9) and EMA(21) SHALL match the standard exponential moving average formula within 0.0001% tolerance.
**Validates: Requirements 2.2**

### Property 4: RSI Calculation Correctness
*For any* valid OHLCV data series with at least 15 candles, the calculated RSI(14) SHALL be between 0 and 100 inclusive.
**Validates: Requirements 2.2**

### Property 5: Scoring Consistency
*For any* set of indicator values, the total score SHALL equal the sum of individual component scores and SHALL be between 0 and 100.
**Validates: Requirements 2.3-2.10**

### Property 6: Stop Loss Bounds
*For any* generated Signal, the stop loss distance from entry SHALL not exceed 3% regardless of ATR value.
**Validates: Requirements 3.3**

### Property 7: Leverage Mapping Correctness
*For any* confidence score between 60-100, the calculated leverage SHALL match the defined mapping table exactly.
**Validates: Requirements 4.1-4.5**

### Property 8: Position Size Bounds
*For any* calculated position size, the notional value SHALL not exceed 25% of account equity.
**Validates: Requirements 5.5**

### Property 9: Partial Exit Sequence
*For any* position that reaches +2.5% profit, the system SHALL have already executed the +1.5% partial exit (40% close).
**Validates: Requirements 6.1, 6.2**

### Property 10: Risk Check Completeness
*For any* trade attempt, all five pre-trade risk checks SHALL be evaluated before execution.
**Validates: Requirements 7.1-7.5**

### Property 11: Emergency Exit Trigger
*For any* portfolio state where unrealized loss exceeds 5%, the system SHALL close all positions.
**Validates: Requirements 8.1**

## Error Handling

1. **API Errors**: Retry with exponential backoff (3 attempts, 1s/2s/4s delays)
2. **WebSocket Disconnect**: Auto-reconnect with position state preservation
3. **Order Rejection**: Log error, skip trade, continue monitoring
4. **Insufficient Margin**: Reduce position size by 50% and retry once
5. **Rate Limits**: Queue requests with 100ms minimum spacing

## Testing Strategy

### Unit Tests
- Indicator calculations (EMA, RSI, MACD, ATR)
- Scoring logic
- Leverage mapping
- Position sizing formulas

### Property-Based Tests (using Hypothesis)
- Volume/momentum filters with random ticker data
- Scoring bounds and consistency
- Stop loss/take profit calculations
- Leverage scaling correctness
- Position size bounds

### Integration Tests
- Scanner → Analyzer → Manager pipeline
- WebSocket connection handling
- Order execution flow

### Configuration
- Property tests: minimum 100 iterations per property
- Test framework: pytest with hypothesis
- Each property test tagged with: `**Feature: kinetic-empire-v3, Property {N}: {description}**`
