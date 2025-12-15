# Design Document: Trading Optimizations

## Overview

This design document outlines the implementation of 10 high-confidence, low-risk optimizations to the Kinetic Empire trading bot. The changes are designed to be backward-compatible and enhance existing functionality without breaking current behavior.

The optimizations target three key areas:
1. **Profit Protection:** Earlier trailing stop activation, partial profit taking, conservative sizing
2. **Entry/Exit Quality:** Volume-based sizing, regime-adaptive stops, optimized RSI zones
3. **Risk Management:** Dynamic blacklisting, sentiment integration, micro-timeframe bonuses

## Architecture

The optimizations integrate into the existing modular architecture:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Trading Optimizations Layer                   │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  Enhanced   │  │   Volume    │  │    Regime-Adaptive      │  │
│  │   Trailing  │  │   Tiered    │  │      Stop Loss          │  │
│  │    Stop     │  │   Sizer     │  │      Manager            │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  Partial    │  │  Half-Kelly │  │    Dynamic Blacklist    │  │
│  │  Profit     │  │   Sizer     │  │      Duration           │  │
│  │  Taker      │  │             │  │                         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │    RSI      │  │    F&G      │  │    Entry Confirmation   │  │
│  │   Zone      │  │  Adjuster   │  │       Delay             │  │
│  │  Optimizer  │  │             │  │                         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Existing Trading Modules                      │
│  (risk/, strategy/, signal_quality/, profitable_trading/, etc.) │
└─────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Enhanced Trailing Stop Manager

**Location:** `src/kinetic_empire/optimizations/trailing_optimizer.py`

```python
@dataclass
class TrailingOptConfig:
    activation_pct: float = 0.015  # 1.5% profit to activate
    normal_trail_mult: float = 1.5  # Normal ATR multiplier
    tight_trail_mult: float = 1.0   # Tight ATR multiplier at 3%+
    tight_threshold_pct: float = 0.03  # 3% profit to tighten

class TrailingOptimizer:
    def get_trail_multiplier(self, profit_pct: float) -> float
    def should_activate(self, profit_pct: float) -> bool
    def calculate_trail_stop(self, peak_price: float, atr: float, profit_pct: float) -> float
```

### 2. Partial Profit Taker

**Location:** `src/kinetic_empire/optimizations/profit_taker.py`

```python
@dataclass
class PartialProfitConfig:
    tp1_atr_mult: float = 1.5   # TP1 at 1.5x ATR profit
    tp1_close_pct: float = 0.25  # Close 25% at TP1
    tp2_atr_mult: float = 2.5   # TP2 at 2.5x ATR profit
    tp2_close_pct: float = 0.25  # Close 25% at TP2

class PartialProfitTaker:
    def check_tp_levels(self, entry: float, current: float, atr: float, direction: str) -> TPResult
    def get_close_percentage(self, tp_level: int) -> float
```

### 3. Half-Kelly Sizer

**Location:** `src/kinetic_empire/optimizations/half_kelly.py`

```python
class HalfKellySizer:
    def calculate_half_kelly(self, win_rate: float, rr_ratio: float) -> float
    def clamp_stake(self, stake_pct: float, min_pct: float, max_pct: float) -> float
    def get_stake_percentage(self, pair: str, trade_history: list) -> float
```

### 4. Volume Tiered Sizer

**Location:** `src/kinetic_empire/optimizations/volume_sizer.py`

```python
@dataclass
class VolumeTierConfig:
    low_threshold: float = 1.0
    medium_threshold: float = 1.5
    high_threshold: float = 2.5
    low_multiplier: float = 0.8
    standard_multiplier: float = 1.0
    medium_multiplier: float = 1.1
    high_multiplier: float = 1.2

class VolumeTieredSizer:
    def get_volume_multiplier(self, volume_ratio: float) -> float
    def adjust_position_size(self, base_size: float, volume_ratio: float) -> float
```

### 5. Regime-Adaptive Stop Manager

**Location:** `src/kinetic_empire/optimizations/regime_stops.py`

```python
class RegimeAdaptiveStops:
    def get_atr_multiplier(self, regime: Regime, trend_type: str) -> float
    def calculate_stop_loss(self, entry: float, atr: float, regime: Regime, trend: str) -> float
```

### 6. RSI Zone Optimizer

**Location:** `src/kinetic_empire/optimizations/rsi_zones.py`

```python
@dataclass
class RSIZoneConfig:
    bull_min: float = 35.0
    bull_max: float = 70.0
    bear_min: float = 45.0
    bear_max: float = 60.0

class RSIZoneOptimizer:
    def is_valid_rsi(self, rsi: float, regime: Regime) -> bool
    def get_rsi_bounds(self, regime: Regime) -> tuple[float, float]
```

### 7. Dynamic Blacklist Manager

**Location:** `src/kinetic_empire/optimizations/dynamic_blacklist.py`

```python
class DynamicBlacklistManager:
    def get_blacklist_duration(self, loss_pct: float) -> int  # minutes
    def record_loss(self, symbol: str, loss_pct: float, timestamp: datetime) -> None
    def is_blacklisted(self, symbol: str) -> bool
```

### 8. Fear & Greed Adjuster

**Location:** `src/kinetic_empire/optimizations/fg_adjuster.py`

```python
class FearGreedAdjuster:
    def get_size_multiplier(self, fg_index: int) -> float
    def get_trail_multiplier(self, fg_index: int, base_mult: float) -> float
    def should_adjust(self, fg_index: int) -> bool
```

### 9. Micro Alignment Bonus

**Location:** `src/kinetic_empire/optimizations/micro_bonus.py`

```python
class MicroAlignmentBonus:
    def check_alignment(self, trend_1m: str, trend_5m: str, signal_direction: str) -> bool
    def get_size_bonus(self, is_aligned: bool) -> float
    def get_stop_reduction(self, is_aligned: bool) -> float
```

### 10. Entry Confirmation Manager

**Location:** `src/kinetic_empire/optimizations/entry_confirm.py`

```python
@dataclass
class EntryConfirmConfig:
    confirmation_candles: int = 1
    adverse_threshold_pct: float = 0.003  # 0.3%

class EntryConfirmationManager:
    def create_pending(self, symbol: str, direction: str, price: float) -> PendingEntry
    def check_confirmation(self, symbol: str, current_price: float, candles: int) -> tuple[bool, str]
```

## Data Models

### TrailingState (Enhanced)

```python
@dataclass
class EnhancedTrailingState:
    is_active: bool = False
    peak_price: float = 0.0
    peak_profit_pct: float = 0.0
    trail_multiplier: float = 1.5
    tp1_done: bool = False
    tp2_done: bool = False
    remaining_pct: float = 1.0  # Remaining position percentage
```

### TPResult

```python
@dataclass
class TPResult:
    should_close: bool
    close_pct: float
    tp_level: int  # 0=none, 1=TP1, 2=TP2
    reason: str
```

### VolumeTier

```python
class VolumeTier(Enum):
    LOW = "low"        # < 1.0x
    STANDARD = "standard"  # 1.0-1.5x
    MEDIUM = "medium"  # 1.5-2.5x
    HIGH = "high"      # > 2.5x
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Trailing Stop Activation Threshold
*For any* position with unrealized profit, trailing stop activates if and only if profit >= 1.5%
**Validates: Requirements 1.1**

### Property 2: Trailing Stop Tightening
*For any* active trailing stop, the trail multiplier is 1.5x ATR when profit < 3%, and 1.0x ATR when profit >= 3%
**Validates: Requirements 1.2, 1.3**

### Property 3: Partial Profit Taking Levels
*For any* position, TP1 triggers at 1.5x ATR profit (closing 25%), and TP2 triggers at 2.5x ATR profit (closing additional 25%)
**Validates: Requirements 2.1, 2.2, 2.4**

### Property 4: Half-Kelly Calculation
*For any* win rate and reward/risk ratio, the Half-Kelly stake equals 0.5 * full Kelly fraction, clamped to [min_stake, max_stake]
**Validates: Requirements 3.1, 3.2, 3.3**

### Property 5: Volume Tier Multiplier
*For any* volume ratio, the position size multiplier is: 0.8x if ratio < 1.0, 1.0x if 1.0-1.5, 1.1x if 1.5-2.5, 1.2x if > 2.5
**Validates: Requirements 4.1, 4.2, 4.3, 4.4**

### Property 6: Regime-Adaptive ATR Multiplier
*For any* regime and trend combination, the ATR stop multiplier is: 1.5x for BULL+TRENDING, 2.0x for BULL+SIDEWAYS, 2.5x for BEAR
**Validates: Requirements 5.1, 5.2, 5.3**

### Property 7: Existing Stops Preservation
*For any* existing position, when regime changes, the stop loss price remains unchanged
**Validates: Requirements 5.4**

### Property 8: RSI Zone Validation
*For any* RSI value and regime, entry is valid if: BULL regime accepts RSI 35-70, BEAR regime accepts RSI 45-60
**Validates: Requirements 6.1, 6.2, 6.3**

### Property 9: Blacklist Duration by Loss Severity
*For any* stop loss event, blacklist duration is: 15 min if loss < 1%, 30 min if 1-2%, 60 min if > 2%
**Validates: Requirements 7.1, 7.2, 7.3**

### Property 10: Blacklist Expiration
*For any* blacklisted symbol, after the duration expires, the symbol is no longer blacklisted
**Validates: Requirements 7.4**

### Property 11: Fear & Greed Adjustments
*For any* F&G index value, position size is reduced 30% if F&G < 25, trail is tightened to 1.0x if F&G > 75, standard otherwise
**Validates: Requirements 8.1, 8.2, 8.3**

### Property 12: F&G Fallback
*For any* unavailable F&G data (None), the system uses standard parameters without adjustment
**Validates: Requirements 8.4**

### Property 13: Micro Alignment Bonus
*For any* signal where 1M and 5M trends align with direction, position size increases by 5% and stop reduces by 0.5x ATR
**Validates: Requirements 9.1, 9.2**

### Property 14: Micro Contradiction Rejection
*For any* signal where micro-timeframes contradict signal direction, the signal is rejected
**Validates: Requirements 9.3**

### Property 15: Entry Confirmation Delay
*For any* entry signal, execution waits 1 candle and cancels if price moves > 0.3% against signal direction
**Validates: Requirements 10.1, 10.2, 10.3**

## Error Handling

- **Missing Data:** All optimizers fall back to standard parameters when data is unavailable
- **Invalid Inputs:** Input validation with sensible defaults (e.g., negative ATR → use 0)
- **Division by Zero:** Protected in all percentage calculations
- **Configuration Errors:** Validation at startup with clear error messages

## Testing Strategy

### Property-Based Testing

The implementation uses **Hypothesis** for property-based testing. Each correctness property is implemented as a property-based test with minimum 100 iterations.

### Unit Tests

Unit tests cover:
- Edge cases (zero values, boundary conditions)
- Integration points between optimizers
- Configuration validation

### Test Structure

```
tests/
├── test_trading_optimizations.py  # Property-based tests
├── test_trailing_optimizer.py     # Unit tests for trailing
├── test_profit_taker.py           # Unit tests for TP1/TP2
├── test_half_kelly.py             # Unit tests for Kelly
├── test_volume_sizer.py           # Unit tests for volume tiers
├── test_regime_stops.py           # Unit tests for regime stops
├── test_rsi_zones.py              # Unit tests for RSI
├── test_dynamic_blacklist.py      # Unit tests for blacklist
├── test_fg_adjuster.py            # Unit tests for F&G
├── test_micro_bonus.py            # Unit tests for micro alignment
└── test_entry_confirm.py          # Unit tests for confirmation
```
