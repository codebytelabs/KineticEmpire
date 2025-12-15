# Design Document

## Overview

This design document outlines the comprehensive overhaul of the Kinetic Empire trading bot to achieve consistent profitability. The overhaul focuses on five key areas:

1. **Regime-Based Trade Filtering** - Completely disable trading in CHOPPY/SIDEWAYS markets
2. **Dynamic Position Sizing** - Scale position size (5-15%) based on confidence score
3. **Adaptive Leverage** - Scale leverage (2x-10x) based on regime and confidence
4. **ATR-Based Risk Management** - Use volatility-normalized stops instead of fixed percentages
5. **Direction Validation** - Confirm price momentum matches signal before entry

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Signal Quality Gate v2                      │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   Regime     │  │  Direction   │  │    Blacklist         │  │
│  │  Detector    │──│  Validator   │──│    Manager           │  │
│  │  (ADX-based) │  │  (Momentum)  │  │  (1 loss = 60min)    │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│         │                 │                    │                │
│         ▼                 ▼                    ▼                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Confidence-Based Position Sizer             │   │
│  │         (5% @ 50-59, 7% @ 60-69, 10% @ 70-79,           │   │
│  │          12% @ 80-89, 15% @ 90-100)                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Regime-Based Leverage Calculator            │   │
│  │    TRENDING: 5x-10x | SIDEWAYS: 3x max | CHOPPY: 2x max │   │
│  └─────────────────────────────────────────────────────────┘   │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                ATR-Based Stop Calculator                 │   │
│  │    TRENDING: 2.0x ATR | SIDEWAYS: 2.5x ATR | CHOPPY: 3x │   │
│  └─────────────────────────────────────────────────────────┘   │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  Entry Confirmer                         │   │
│  │         (30-second delay, 0.5% adverse = cancel)         │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Position Manager                              │
│  ┌──────────────────┐  ┌──────────────────────────────────┐    │
│  │  Exposure Tracker │  │     ATR Trailing Stop Manager    │    │
│  │  (45% max total)  │  │  (Activate @ 2%, trail 1.5x ATR) │    │
│  └──────────────────┘  └──────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. RegimeDetector

Improved regime detection using ADX thresholds.

```python
class RegimeDetector:
    def detect(self, adx: float, price: float, ma_50: float) -> MarketRegime:
        """
        Detect market regime based on ADX and price/MA relationship.
        
        Args:
            adx: 14-period ADX value
            price: Current price
            ma_50: 50-period moving average
            
        Returns:
            MarketRegime enum (TRENDING, SIDEWAYS, CHOPPY)
        """
        
    def get_trend_direction(self, price: float, ma_50: float) -> str:
        """Return 'bullish' or 'bearish' based on price vs MA."""
```

### 2. DirectionValidator

Validates signal direction against recent price momentum.

```python
class DirectionValidator:
    def validate(
        self, 
        direction: str, 
        recent_candles: List[OHLCV],
        threshold_pct: float = 0.3
    ) -> Tuple[bool, str]:
        """
        Validate that price momentum supports signal direction.
        
        Args:
            direction: "LONG" or "SHORT"
            recent_candles: Last 5 candles
            threshold_pct: Max adverse movement allowed (0.3%)
            
        Returns:
            (is_valid, reason) tuple
        """
```

### 3. ConfidencePositionSizer

Calculates position size based on confidence score.

```python
@dataclass
class PositionSizeResult:
    size_pct: float  # 5-15%
    size_usd: float
    confidence_tier: str
    
class ConfidencePositionSizer:
    CONFIDENCE_TO_SIZE = {
        (90, 100): 0.15,  # 15%
        (80, 89): 0.12,   # 12%
        (70, 79): 0.10,   # 10%
        (60, 69): 0.07,   # 7%
        (50, 59): 0.05,   # 5%
    }
    
    def calculate(
        self,
        confidence: int,
        available_capital: float,
        current_exposure: float,
        max_exposure: float = 0.45
    ) -> Optional[PositionSizeResult]:
        """
        Calculate position size based on confidence.
        
        Returns None if confidence < 50 or exposure limit reached.
        """
```

### 4. RegimeLeverageCalculator

Calculates leverage based on regime and confidence.

```python
class RegimeLeverageCalculator:
    def calculate(
        self,
        regime: MarketRegime,
        confidence: int,
        consecutive_losses: int = 0
    ) -> int:
        """
        Calculate leverage based on regime and confidence.
        
        TRENDING + 90-100: 10x
        TRENDING + 70-89: 7x
        TRENDING + 50-69: 5x
        SIDEWAYS: 3x max
        CHOPPY: 2x max
        
        After 2+ losses: reduce by 50%
        """
```

### 5. ATRStopCalculator

Calculates stop loss based on ATR and regime.

```python
@dataclass
class StopLossResult:
    stop_price: float
    stop_pct: float
    atr_multiplier: float
    atr_value: float
    
class ATRStopCalculator:
    REGIME_MULTIPLIERS = {
        MarketRegime.TRENDING: 2.0,
        MarketRegime.SIDEWAYS: 2.5,
        MarketRegime.CHOPPY: 3.0,
    }
    
    def calculate(
        self,
        entry_price: float,
        direction: str,
        atr_14: float,
        regime: MarketRegime,
        min_stop_pct: float = 0.01,
        max_stop_pct: float = 0.05
    ) -> StopLossResult:
        """
        Calculate ATR-based stop loss with min/max bounds.
        """
```

### 6. ATRTrailingStopManager

Manages trailing stops using ATR.

```python
@dataclass
class TrailingState:
    is_active: bool
    peak_price: float
    peak_profit_pct: float
    current_trail_distance: float
    
class ATRTrailingStopManager:
    def update(
        self,
        current_price: float,
        entry_price: float,
        direction: str,
        atr_14: float,
        activation_threshold: float = 0.02,  # 2%
        normal_trail_mult: float = 1.5,
        tight_trail_mult: float = 1.0,
        tight_threshold: float = 0.05  # 5%
    ) -> Tuple[TrailingState, bool]:
        """
        Update trailing stop state.
        
        Returns (state, should_close) tuple.
        """
```

### 7. EntryConfirmer

Implements confirmation delay before entry.

```python
@dataclass
class PendingEntry:
    symbol: str
    direction: str
    signal_price: float
    signal_time: datetime
    confirmation_candles: int
    
class EntryConfirmer:
    def create_pending(
        self,
        symbol: str,
        direction: str,
        current_price: float,
        confirmation_candles: int = 2
    ) -> PendingEntry:
        """Create a pending entry awaiting confirmation."""
        
    def check_confirmation(
        self,
        pending: PendingEntry,
        current_price: float,
        candles_elapsed: int,
        adverse_threshold: float = 0.005  # 0.5%
    ) -> Tuple[bool, str]:
        """
        Check if pending entry should execute or cancel.
        
        Returns (should_execute, reason) tuple.
        """
```

### 8. ExposureTracker

Tracks total portfolio exposure.

```python
class ExposureTracker:
    def __init__(self, max_exposure_pct: float = 0.45):
        self.max_exposure_pct = max_exposure_pct
        self.positions: Dict[str, float] = {}
        
    def get_current_exposure(self) -> float:
        """Get total exposure as percentage of portfolio."""
        
    def get_available_exposure(self, portfolio_value: float) -> float:
        """Get remaining exposure available for new positions."""
        
    def can_open_position(self, size_pct: float) -> bool:
        """Check if new position would exceed exposure limit."""
        
    def add_position(self, symbol: str, size_pct: float) -> None:
        """Record new position."""
        
    def remove_position(self, symbol: str) -> None:
        """Remove closed position."""
```

## Data Models

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from datetime import datetime

class MarketRegime(Enum):
    TRENDING = "trending"
    SIDEWAYS = "sideways"
    CHOPPY = "choppy"

class TrendDirection(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"

@dataclass
class RegimeAnalysis:
    regime: MarketRegime
    trend_direction: TrendDirection
    adx_value: float
    price_vs_ma: float  # % above/below MA

@dataclass
class RiskParameters:
    position_size_pct: float  # 5-15%
    position_size_usd: float
    leverage: int  # 2-10
    stop_loss_pct: float
    stop_loss_price: float
    atr_value: float

@dataclass
class TradeSignal:
    symbol: str
    direction: str
    confidence: int
    regime: MarketRegime
    risk_params: RiskParameters
    pending_confirmation: bool
    confirmation_deadline: Optional[datetime]

@dataclass
class QualityGateResultV2:
    passed: bool
    rejection_reason: Optional[str]
    direction: str
    confidence_tier: str
    position_size_pct: float
    leverage: int
    stop_loss_pct: float
    stop_loss_price: float
    atr_value: float
    requires_confirmation: bool
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Regime-based trade rejection
*For any* trade signal with regime CHOPPY or SIDEWAYS, the Signal_Quality_Gate SHALL reject the signal regardless of confidence score.
**Validates: Requirements 1.1, 1.2**

### Property 2: Confidence-to-position-size mapping
*For any* confidence score, the Position_Sizer SHALL return the correct position size percentage according to the mapping: 90-100→15%, 80-89→12%, 70-79→10%, 60-69→7%, 50-59→5%, <50→reject.
**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6**

### Property 3: Portfolio exposure cap invariant
*For any* set of open positions, the total exposure SHALL never exceed 45% of portfolio value.
**Validates: Requirements 2.7, 8.1, 8.2, 8.3**

### Property 4: Regime-confidence-to-leverage mapping
*For any* combination of regime and confidence, the Leverage_Calculator SHALL return leverage according to: TRENDING+90-100→10x, TRENDING+70-89→7x, TRENDING+50-69→5x, SIDEWAYS→3x, CHOPPY→2x, and reduce by 50% after 2+ consecutive losses.
**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**

### Property 5: ATR stop loss calculation with bounds
*For any* entry price, ATR value, and regime, the stop loss SHALL be calculated as regime_multiplier × ATR, bounded between 1% and 5% of entry price.
**Validates: Requirements 4.2, 4.3, 4.4, 4.5, 4.6**

### Property 6: Direction validation against price momentum
*For any* LONG signal, if price has fallen more than 0.3% in last 5 candles, the signal SHALL be rejected. *For any* SHORT signal, if price has risen more than 0.3% in last 5 candles, the signal SHALL be rejected.
**Validates: Requirements 5.1, 5.2, 5.3**

### Property 7: Trailing stop activation and tightening
*For any* position, trailing stop SHALL activate when profit reaches 2%, trail at 1.5x ATR, and tighten to 1.0x ATR when profit exceeds 5%.
**Validates: Requirements 6.1, 6.2, 6.3**

### Property 8: Blacklist trigger and expiration
*For any* symbol experiencing a stop-loss, the symbol SHALL be blacklisted for 60 minutes, and SHALL be removed from blacklist after expiration.
**Validates: Requirements 7.1, 7.2, 7.3**

### Property 9: ADX-based regime detection
*For any* ADX value, the regime SHALL be classified as: ADX>25→TRENDING, 15≤ADX≤25→SIDEWAYS, ADX<15→CHOPPY.
**Validates: Requirements 9.1, 9.2, 9.3, 9.4**

### Property 10: Entry confirmation with cancellation
*For any* pending entry, if price moves more than 0.5% against signal direction during confirmation period, the entry SHALL be cancelled.
**Validates: Requirements 10.1, 10.2, 10.3, 10.4**

## Error Handling

1. **Missing ATR Data**: If ATR cannot be calculated, use fallback fixed stop of 3%
2. **Missing ADX Data**: If ADX cannot be calculated, default to CHOPPY regime (most conservative)
3. **API Failures**: Retry up to 3 times with exponential backoff, then skip signal
4. **Position Size Overflow**: If calculated size exceeds available exposure, reduce to available amount
5. **Leverage Calculation Edge Cases**: Always return minimum 2x leverage, never exceed 10x

## Testing Strategy

### Dual Testing Approach

This system requires both unit tests and property-based tests:

**Unit Tests**: Verify specific examples, edge cases, and integration points
**Property-Based Tests**: Verify universal properties hold across all valid inputs

### Property-Based Testing Framework

Use **Hypothesis** library for Python property-based testing.

Each property test should:
- Run minimum 100 iterations
- Use smart generators that constrain to valid input ranges
- Be tagged with the property number and requirements reference

### Test Categories

1. **Position Sizing Tests**
   - Property test: confidence-to-size mapping
   - Unit test: edge cases at tier boundaries (49, 50, 59, 60, etc.)

2. **Leverage Calculation Tests**
   - Property test: regime-confidence-leverage mapping
   - Unit test: loss reduction behavior

3. **ATR Stop Tests**
   - Property test: stop calculation with bounds
   - Unit test: min/max boundary enforcement

4. **Direction Validation Tests**
   - Property test: momentum contradiction detection
   - Unit test: edge cases at 0.3% threshold

5. **Regime Detection Tests**
   - Property test: ADX-to-regime mapping
   - Unit test: boundary values (14.9, 15, 25, 25.1)

6. **Exposure Tracking Tests**
   - Property test: exposure cap invariant
   - Unit test: position add/remove operations
