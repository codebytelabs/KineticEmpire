# Wave Rider Upgrade - Design Document

## Overview

The Wave Rider Upgrade transforms the Kinetic Empire trading bot from a conservative trend-follower into an active momentum scalper. The system actively scans ALL futures pairs to find coins with volume spikes and momentum, enters both LONG and SHORT positions based on multi-timeframe analysis, and rides price waves with proper risk management.

### Key Differences from Current Bot

| Aspect | Current Bot | Wave Rider |
|--------|-------------|------------|
| Symbols | 10 fixed coins | ALL futures (~150+ pairs) |
| Scan speed | Every 30 seconds | Every 15 seconds |
| Entry trigger | Perfect TRENDING regime (ADX>25) | Volume spike + MTF alignment |
| Activity | Very low | High |
| Finding movers | Static list | Dynamic ranking by momentum |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Wave Rider Engine                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │  Momentum    │───▶│    MTF       │───▶│   Signal     │       │
│  │  Scanner     │    │  Analyzer    │    │  Generator   │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│         │                   │                   │                │
│         ▼                   ▼                   ▼                │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   Volume     │    │   Trend      │    │  Position    │       │
│  │   Spike      │    │  Direction   │    │   Sizer      │       │
│  │  Detector    │    │  Classifier  │    │              │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                     Position Manager                             │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │  ATR Stop    │    │  Trailing    │    │   Profit     │       │
│  │  Calculator  │    │    Stop      │    │   Locker     │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                     Risk Management                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   Circuit    │    │  Blacklist   │    │  Exposure    │       │
│  │   Breaker    │    │   Manager    │    │   Tracker    │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. MomentumScanner

Scans all futures pairs and ranks them by momentum score.

```python
@dataclass
class MoverData:
    symbol: str
    price: float
    price_change_pct: float  # 5-minute change
    volume_24h: float
    volume_ratio: float  # current / 20-period avg
    momentum_score: float  # volume_ratio * abs(price_change_pct)
    spike_classification: str  # "none", "normal", "strong", "extreme"

class MomentumScanner:
    def scan_all_futures(self) -> List[MoverData]:
        """Fetch all USDT futures tickers and calculate momentum scores."""
        
    def get_top_movers(self, limit: int = 20) -> List[MoverData]:
        """Return top N symbols sorted by momentum_score descending."""
        
    def calculate_volume_ratio(self, symbol: str, current_volume: float) -> float:
        """Calculate volume ratio vs 20-period average."""
```

### 2. VolumeSpikeDetector

Detects and classifies volume spikes.

```python
class VolumeSpikeDetector:
    SPIKE_THRESHOLD = 2.0      # Normal spike
    STRONG_THRESHOLD = 3.0     # Strong spike
    EXTREME_THRESHOLD = 5.0    # Extreme spike
    
    def detect_spike(self, volume_ratio: float) -> Tuple[bool, str]:
        """Returns (has_spike, classification)."""
        
    def get_spike_strength(self, volume_ratio: float) -> int:
        """Returns spike strength 0-100 for scoring."""
```

### 3. MTFAnalyzer (Multi-Timeframe Analyzer)

Analyzes trend direction across multiple timeframes.

```python
@dataclass
class TimeframeAnalysis:
    timeframe: str  # "1m", "5m", "15m"
    ema_fast: float  # 9-period EMA
    ema_slow: float  # 21-period EMA
    rsi: float
    vwap: float
    trend_direction: str  # "BULLISH", "BEARISH", "NEUTRAL"
    price: float

@dataclass
class MTFResult:
    analyses: Dict[str, TimeframeAnalysis]  # keyed by timeframe
    alignment_score: int  # 40, 70, or 100
    dominant_direction: str  # "BULLISH", "BEARISH", "NEUTRAL"
    price_vs_vwap: str  # "ABOVE", "BELOW"

class MTFAnalyzer:
    TIMEFRAMES = ["1m", "5m", "15m"]
    EMA_FAST_PERIOD = 9
    EMA_SLOW_PERIOD = 21
    RSI_PERIOD = 14
    
    def analyze(self, symbol: str, ohlcv_data: Dict[str, List[OHLCV]]) -> MTFResult:
        """Perform multi-timeframe analysis."""
        
    def calculate_alignment_score(self, analyses: Dict[str, TimeframeAnalysis]) -> int:
        """Calculate alignment score based on trend agreement."""
        
    def determine_trend_direction(self, ema_fast: float, ema_slow: float, price: float) -> str:
        """Determine trend direction for a single timeframe."""
```

### 4. WaveRiderSignalGenerator

Generates entry signals based on momentum and MTF analysis.

```python
@dataclass
class WaveRiderSignal:
    symbol: str
    direction: str  # "LONG" or "SHORT"
    volume_ratio: float
    spike_classification: str
    alignment_score: int
    rsi_1m: float
    position_size_pct: float
    leverage: int
    stop_loss_pct: float
    confidence_score: int  # 0-100

class WaveRiderSignalGenerator:
    MIN_VOLUME_RATIO = 2.0
    MIN_ALIGNMENT_SCORE = 70
    RSI_MIN = 25
    RSI_MAX = 75
    
    def evaluate(
        self,
        mover: MoverData,
        mtf_result: MTFResult,
        is_blacklisted: bool,
        current_exposure: float,
    ) -> Optional[WaveRiderSignal]:
        """Evaluate entry conditions and generate signal if valid."""
        
    def calculate_position_params(
        self,
        volume_ratio: float,
        alignment_score: int,
        consecutive_losses: int,
    ) -> Tuple[float, int]:
        """Calculate position size and leverage based on signal strength."""
```

### 5. WaveRiderPositionSizer

Calculates position size and leverage based on signal strength.

```python
class WaveRiderPositionSizer:
    # Volume ratio tiers
    TIER_1 = (2.0, 3.0, 0.05, 3)   # (min, max, size_pct, leverage)
    TIER_2 = (3.0, 5.0, 0.07, 5)
    TIER_3 = (5.0, float('inf'), 0.10, 7)
    
    def calculate(
        self,
        volume_ratio: float,
        alignment_score: int,
        consecutive_losses: int,
        available_capital: float,
        current_exposure: float,
    ) -> Tuple[float, int, float]:
        """Returns (size_pct, leverage, size_usd)."""
```

### 6. WaveRiderStopCalculator

Calculates ATR-based stop losses with bounds.

```python
class WaveRiderStopCalculator:
    ATR_MULTIPLIER = 1.5
    MIN_STOP_PCT = 0.005  # 0.5%
    MAX_STOP_PCT = 0.03   # 3%
    
    def calculate(
        self,
        entry_price: float,
        direction: str,
        atr_14: float,
    ) -> Tuple[float, float]:
        """Returns (stop_price, stop_pct)."""
```

### 7. WaveRiderTrailingStop

Manages trailing stops with profit-based tightening.

```python
@dataclass
class TrailingState:
    is_active: bool
    peak_price: float
    peak_profit_pct: float
    trail_multiplier: float  # 0.8 or 0.5
    tp1_done: bool
    tp2_done: bool

class WaveRiderTrailingStop:
    ACTIVATION_PROFIT = 0.01  # 1%
    INITIAL_TRAIL_MULT = 0.8
    TIGHT_TRAIL_MULT = 0.5
    TIGHT_THRESHOLD = 0.03  # 3%
    TP1_PROFIT = 0.015  # 1.5%
    TP1_CLOSE_PCT = 0.30
    TP2_PROFIT = 0.025  # 2.5%
    TP2_CLOSE_PCT = 0.30
    
    def update(
        self,
        symbol: str,
        current_price: float,
        entry_price: float,
        direction: str,
        atr_14: float,
    ) -> Tuple[TrailingState, bool, float]:
        """Returns (state, should_close, close_pct)."""
```

### 8. WaveRiderEngine

Main engine that orchestrates all components.

```python
class WaveRiderEngine:
    SCAN_INTERVAL = 15  # seconds
    MONITOR_INTERVAL = 5  # seconds
    MAX_POSITIONS = 5
    MAX_EXPOSURE = 0.45
    DAILY_LOSS_LIMIT = 0.03  # 3%
    
    async def start(self):
        """Start the Wave Rider trading loop."""
        
    async def scan_cycle(self):
        """Execute one market scan cycle."""
        
    async def monitor_positions(self):
        """Monitor and manage open positions."""
        
    async def execute_signal(self, signal: WaveRiderSignal):
        """Execute a trading signal."""
```

## Data Models

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict

class SpikeClassification(Enum):
    NONE = "none"
    NORMAL = "normal"
    STRONG = "strong"
    EXTREME = "extreme"

class TrendDirection(Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"

@dataclass
class OHLCV:
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: int

@dataclass
class WaveRiderConfig:
    scan_interval: int = 15
    monitor_interval: int = 5
    max_positions: int = 5
    max_exposure: float = 0.45
    daily_loss_limit: float = 0.03
    min_volume_ratio: float = 2.0
    min_alignment_score: int = 70
    rsi_min: int = 25
    rsi_max: int = 75
    min_24h_volume: float = 10_000_000
    top_movers_limit: int = 20
    blacklist_duration_minutes: int = 30
    max_consecutive_losses: int = 2
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Momentum Score Calculation
*For any* volume_ratio and price_change_pct, the momentum_score SHALL equal volume_ratio multiplied by the absolute value of price_change_pct.
**Validates: Requirements 1.4**

### Property 2: Top Movers Sorting
*For any* list of movers returned by get_top_movers(), the list SHALL be sorted in descending order by momentum_score and contain at most the specified limit.
**Validates: Requirements 1.5**

### Property 3: Volume Spike Classification
*For any* volume_ratio, the spike classification SHALL be:
- "extreme" if volume_ratio >= 5.0
- "strong" if volume_ratio >= 3.0 and < 5.0
- "normal" if volume_ratio >= 2.0 and < 3.0
- "none" if volume_ratio < 2.0
**Validates: Requirements 2.2, 2.3, 2.4**

### Property 4: Trend Direction Classification
*For any* EMA_fast, EMA_slow, and price:
- Direction is BULLISH if EMA_fast > EMA_slow AND price > EMA_fast
- Direction is BEARISH if EMA_fast < EMA_slow AND price < EMA_slow
- Direction is NEUTRAL otherwise
**Validates: Requirements 3.4, 3.5, 3.6**

### Property 5: Alignment Score Calculation
*For any* three timeframe directions:
- Score is 100 if all 3 directions are the same (non-NEUTRAL)
- Score is 70 if exactly 2 directions are the same (non-NEUTRAL)
- Score is 40 otherwise
**Validates: Requirements 3.7, 3.8, 3.9**

### Property 6: Entry Rejection Conditions
*For any* entry evaluation, the signal SHALL be rejected if:
- volume_ratio < 2.0, OR
- alignment_score < 70, OR
- RSI < 25 or RSI > 75, OR
- symbol is blacklisted, OR
- current_exposure >= 45%
**Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**

### Property 7: Signal Direction Determination
*For any* valid entry signal:
- Direction is LONG if price > VWAP AND majority timeframes are BULLISH
- Direction is SHORT if price < VWAP AND majority timeframes are BEARISH
**Validates: Requirements 4.6, 4.7**

### Property 8: Position Size and Leverage Tiers
*For any* volume_ratio:
- If 2.0 <= volume_ratio < 3.0: size=5%, leverage=3x
- If 3.0 <= volume_ratio < 5.0: size=7%, leverage=5x
- If volume_ratio >= 5.0: size=10%, leverage=7x
**Validates: Requirements 5.1, 5.2, 5.3**

### Property 9: Alignment Leverage Bonus
*For any* signal with alignment_score of 100, leverage SHALL be increased by 1x (up to maximum 10x).
**Validates: Requirements 5.4**

### Property 10: Loss Protection Size Reduction
*For any* position sizing calculation where consecutive_losses > 2, the position size SHALL be reduced by 50%.
**Validates: Requirements 5.5**

### Property 11: Stop Loss Bounds
*For any* calculated stop loss:
- stop_pct >= 0.5% (minimum)
- stop_pct <= 3.0% (maximum)
**Validates: Requirements 6.2, 6.3**

### Property 12: Stop Loss Direction
*For any* position:
- LONG positions have stop_price < entry_price
- SHORT positions have stop_price > entry_price
**Validates: Requirements 6.4, 6.5**

### Property 13: Trailing Stop Activation
*For any* position, trailing stop mode SHALL activate when unrealized_profit >= 1.0%.
**Validates: Requirements 7.1**

### Property 14: Trailing Stop Tightening
*For any* position with trailing stop active:
- Trail multiplier is 0.8x ATR when profit < 3%
- Trail multiplier is 0.5x ATR when profit >= 3%
**Validates: Requirements 7.2, 7.5**

### Property 15: Circuit Breaker Activation
*For any* trading session, new trades SHALL be halted when daily_realized_loss > 3% of starting_balance.
**Validates: Requirements 9.1**

### Property 16: Blacklist After Losses
*For any* symbol with 2 consecutive losses, the symbol SHALL be blacklisted for 30 minutes.
**Validates: Requirements 9.2**

### Property 17: Position Limit Enforcement
*For any* state where open_positions >= 5, new position opening SHALL be rejected.
**Validates: Requirements 9.3**

## Error Handling

1. **API Rate Limits**: Implement exponential backoff when rate limits are approached
2. **Network Errors**: Retry with backoff, log errors, continue with next symbol
3. **Invalid Data**: Skip symbols with missing or invalid OHLCV data
4. **Order Failures**: Log failure, remove from exposure tracker, alert user
5. **Position Sync**: On startup, sync with exchange positions before trading

## Testing Strategy

### Unit Tests
- Test each component in isolation with mock data
- Test edge cases (empty data, extreme values, boundary conditions)
- Test error handling paths

### Property-Based Tests
Using `hypothesis` library for Python:
- Generate random volume ratios and verify spike classification
- Generate random EMA/price combinations and verify trend direction
- Generate random timeframe directions and verify alignment scores
- Generate random entry conditions and verify rejection logic
- Generate random stop calculations and verify bounds

### Integration Tests
- Test full signal generation pipeline with mock exchange
- Test position management lifecycle
- Test circuit breaker and blacklist behavior
