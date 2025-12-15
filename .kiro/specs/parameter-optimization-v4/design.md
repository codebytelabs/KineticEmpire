# Design Document: Parameter Optimization v4

## Overview

This design document specifies the implementation of research-backed parameter optimizations for Kinetic Empire v4.0. The optimizations target eight key areas: ATR-based stops, leverage caps, Kelly position sizing, trailing stops, RSI thresholds, ADX thresholds, volume confirmation, and portfolio risk limits.

The goal is to achieve:
- 40-60% reduction in premature stop-outs
- Better Sharpe ratio through improved risk-adjusted returns
- Reduced drawdowns during volatile periods
- More sustainable equity curve

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  OPTIMIZED PARAMETER SYSTEM                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐     ┌─────────────────┐               │
│  │  Regime         │────▶│  Parameter      │               │
│  │  Detector       │     │  Adjuster       │               │
│  └─────────────────┘     └─────────────────┘               │
│           │                      │                          │
│           ▼                      ▼                          │
│  ┌─────────────────────────────────────────────────┐       │
│  │              OPTIMIZED CALCULATORS               │       │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐     │       │
│  │  │ ATR Stop  │ │ Leverage  │ │ Position  │     │       │
│  │  │Calculator │ │Calculator │ │  Sizer    │     │       │
│  │  └───────────┘ └───────────┘ └───────────┘     │       │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐     │       │
│  │  │ Trailing  │ │   RSI     │ │   ADX     │     │       │
│  │  │  Stop     │ │ Filter    │ │ Filter    │     │       │
│  │  └───────────┘ └───────────┘ └───────────┘     │       │
│  │  ┌───────────┐ ┌───────────┐                   │       │
│  │  │  Volume   │ │ Portfolio │                   │       │
│  │  │Confirmer  │ │Risk Guard │                   │       │
│  │  └───────────┘ └───────────┘                   │       │
│  └─────────────────────────────────────────────────┘       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. OptimizedATRStopCalculator

Calculates stop loss levels using regime-adaptive ATR multipliers.

```python
class OptimizedATRStopCalculator:
    BASE_MULTIPLIER = 2.5  # Up from 1.5
    HIGH_VOL_MULTIPLIER = 3.0
    LOW_VOL_MULTIPLIER = 2.0
    SIDEWAYS_MULTIPLIER = 2.0
    MAX_LOSS_PERCENT = 0.02  # 2% max loss
    
    def calculate_stop(
        self,
        entry_price: float,
        atr: float,
        direction: str,  # 'long' or 'short'
        regime: MarketRegime,
        position_size: float
    ) -> StopResult:
        """Calculate stop loss with regime-adaptive multiplier."""
        pass
    
    def get_multiplier(self, regime: MarketRegime) -> float:
        """Get ATR multiplier based on market regime."""
        pass
```

### 2. OptimizedLeverageCalculator

Calculates leverage with hard caps and regime adjustments.

```python
class OptimizedLeverageCalculator:
    HARD_CAP = 8  # Down from 20
    CONFIDENCE_TIERS = {
        (0, 70): 3,
        (70, 80): 5,
        (80, 90): 6,
        (90, 101): 8
    }
    REGIME_REDUCTION = 0.5  # 50% reduction for choppy/volatile
    
    def calculate_leverage(
        self,
        confidence: float,
        regime: MarketRegime
    ) -> int:
        """Calculate leverage based on confidence and regime."""
        pass
```

### 3. OptimizedPositionSizer

Implements quarter-Kelly position sizing.

```python
class OptimizedPositionSizer:
    KELLY_FRACTION = 0.25  # Quarter Kelly
    LOW_WINRATE_FRACTION = 0.15
    MAX_POSITION_PERCENT = 0.25  # 25% max
    LOW_WINRATE_THRESHOLD = 0.40
    
    def calculate_position_size(
        self,
        capital: float,
        win_rate: float,
        avg_win: float,
        avg_loss: float
    ) -> float:
        """Calculate position size using quarter-Kelly."""
        pass
    
    def calculate_kelly(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float
    ) -> float:
        """Calculate raw Kelly criterion value."""
        pass
```

### 4. OptimizedTrailingStop

Manages trailing stops with regime-adaptive parameters.

```python
class OptimizedTrailingStop:
    BASE_ACTIVATION = 0.02  # 2% profit to activate
    STEP_SIZE = 0.003  # 0.3% step
    TRENDING_ACTIVATION = 0.025  # 2.5%
    SIDEWAYS_ACTIVATION = 0.015  # 1.5%
    
    def should_activate(
        self,
        current_profit_pct: float,
        regime: MarketRegime
    ) -> bool:
        """Check if trailing stop should activate."""
        pass
    
    def update_stop(
        self,
        current_price: float,
        current_stop: float,
        direction: str
    ) -> float:
        """Update trailing stop level."""
        pass
```

### 5. OptimizedRSIFilter

Filters entries based on optimized RSI thresholds.

```python
class OptimizedRSIFilter:
    OVERSOLD_THRESHOLD = 25  # Down from 30
    OVERBOUGHT_THRESHOLD = 75  # Up from 70
    DIVERGENCE_BONUS = 10
    
    def evaluate_entry(
        self,
        rsi: float,
        direction: str,
        has_divergence: bool = False
    ) -> RSIResult:
        """Evaluate RSI for entry signal."""
        pass
```

### 6. OptimizedADXFilter

Evaluates trend strength with optimized thresholds.

```python
class OptimizedADXFilter:
    TRENDING_THRESHOLD = 20  # Down from 25
    SIDEWAYS_THRESHOLD = 15
    STRONG_TREND_THRESHOLD = 30
    WEAK_TREND_REDUCTION = 0.30  # 30% position reduction
    STRONG_TREND_BONUS = 5
    
    def evaluate_trend(self, adx: float) -> ADXResult:
        """Evaluate ADX for trend classification."""
        pass
```

### 7. OptimizedVolumeConfirmer

Confirms entries with enhanced volume requirements.

```python
class OptimizedVolumeConfirmer:
    REQUIRED_MULTIPLIER = 1.5  # Up from 1.2
    SPIKE_MULTIPLIER = 2.5
    LOW_VOLUME_REDUCTION = 0.40  # 40% position reduction
    SPIKE_BONUS = 10
    
    def confirm_volume(
        self,
        current_volume: float,
        average_volume: float
    ) -> VolumeResult:
        """Confirm volume for entry."""
        pass
```

### 8. OptimizedPortfolioRiskGuard

Enforces portfolio-level risk limits.

```python
class OptimizedPortfolioRiskGuard:
    MAX_POSITIONS = 8  # Down from 12
    MAX_MARGIN_USAGE = 0.80  # 80%
    DAILY_LOSS_LIMIT = 0.04  # 4%
    WEEKLY_LOSS_LIMIT = 0.08  # 8%
    MAX_CORRELATION = 0.70
    MAX_CORRELATED_POSITIONS = 2
    WEEKLY_LOSS_REDUCTION = 0.50  # 50% size reduction
    
    def can_open_position(
        self,
        current_positions: int,
        margin_usage: float,
        daily_loss: float,
        correlation_matrix: dict
    ) -> RiskCheckResult:
        """Check if new position can be opened."""
        pass
```

## Data Models

```python
from dataclasses import dataclass
from enum import Enum

class MarketRegime(Enum):
    TRENDING = "trending"
    SIDEWAYS = "sideways"
    CHOPPY = "choppy"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"

@dataclass
class StopResult:
    stop_price: float
    multiplier_used: float
    adjusted_position_size: float | None
    max_loss_exceeded: bool

@dataclass
class RSIResult:
    signal_valid: bool
    requires_confirmation: bool
    confidence_bonus: int
    reason: str

@dataclass
class ADXResult:
    regime: MarketRegime
    position_size_multiplier: float
    confidence_bonus: int
    is_trending: bool

@dataclass
class VolumeResult:
    confirmed: bool
    position_size_multiplier: float
    confidence_bonus: int
    is_spike: bool

@dataclass
class RiskCheckResult:
    can_open: bool
    reason: str | None
    position_size_multiplier: float
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: ATR Stop Multiplier Regime Adaptation
*For any* market regime and ATR value, the stop calculator SHALL return the correct multiplier: 3.0x for HIGH_VOLATILITY, 2.0x for LOW_VOLATILITY or SIDEWAYS, and 2.5x for TRENDING or CHOPPY.
**Validates: Requirements 1.1, 1.2, 1.3, 9.2, 9.4**

### Property 2: Maximum Loss Invariant
*For any* stop loss calculation, the resulting maximum loss SHALL NOT exceed 2% of position value. If it would exceed 2%, position size must be reduced proportionally.
**Validates: Requirements 1.4, 1.5**

### Property 3: Leverage Hard Cap Invariant
*For any* leverage calculation regardless of confidence or regime, the result SHALL NOT exceed 8x.
**Validates: Requirements 2.1**

### Property 4: Leverage Confidence Tiers
*For any* confidence score, the leverage SHALL be limited to: 3x for confidence < 70, 5x for 70-79, 6x for 80-89, and 8x for 90-100.
**Validates: Requirements 2.2, 2.3, 2.4, 2.5**

### Property 5: Leverage Regime Reduction
*For any* CHOPPY or HIGH_VOLATILITY regime, the maximum leverage SHALL be reduced by 50% from the confidence-based tier.
**Validates: Requirements 2.6, 9.3**

### Property 6: Kelly Fraction Consistency
*For any* position size calculation, the Kelly fraction used SHALL be 0.25 when win rate >= 40%, and 0.15 when win rate < 40%.
**Validates: Requirements 3.1, 3.5**

### Property 7: Kelly Non-Negative Output
*For any* Kelly calculation that produces a negative value, the position size SHALL be zero.
**Validates: Requirements 3.3**

### Property 8: Position Size Cap Invariant
*For any* position size calculation, the result SHALL NOT exceed 25% of capital.
**Validates: Requirements 3.4**

### Property 9: Trailing Stop Activation Threshold
*For any* position and regime, trailing stop SHALL activate at: 2.5% profit for TRENDING, 1.5% for SIDEWAYS, and 2.0% for other regimes.
**Validates: Requirements 4.1, 4.4, 4.5, 9.1**

### Property 10: Trailing Stop Monotonicity
*For any* active trailing stop, when price moves favorably, the stop level SHALL only move in the favorable direction (never retreat).
**Validates: Requirements 4.2, 4.3**

### Property 11: RSI Entry Thresholds
*For any* RSI value, long entries SHALL only be valid when RSI < 25, and short entries SHALL only be valid when RSI > 75.
**Validates: Requirements 5.1, 5.2**

### Property 12: RSI Confirmation Requirement
*For any* RSI value between 25 and 75, the system SHALL require additional confirmation signals.
**Validates: Requirements 5.3**

### Property 13: RSI Divergence Bonus
*For any* detected RSI divergence, the confidence score SHALL increase by exactly 10 points.
**Validates: Requirements 5.5**

### Property 14: ADX Trend Classification
*For any* ADX value, the market SHALL be classified as: SIDEWAYS when ADX < 15, weak trend when 15 <= ADX < 20, and TRENDING when ADX >= 20.
**Validates: Requirements 6.1, 6.2**

### Property 15: ADX Position Adjustment
*For any* ADX value between 15 and 20, position size SHALL be reduced by 30%. For ADX > 30, confidence SHALL increase by 5 points.
**Validates: Requirements 6.3, 6.4**

### Property 16: Volume Confirmation Threshold
*For any* entry evaluation, volume confirmation SHALL require current volume >= 1.5x average volume.
**Validates: Requirements 7.1**

### Property 17: Volume Position Adjustment
*For any* volume below 1.5x average, position size SHALL be reduced by 40%. For volume > 2.5x average, confidence SHALL increase by 10 points.
**Validates: Requirements 7.2, 7.3**

### Property 18: Portfolio Position Limit
*For any* portfolio state with 8 or more open positions, new entries SHALL be rejected.
**Validates: Requirements 8.1**

### Property 19: Portfolio Margin Limit
*For any* portfolio state with margin usage > 80%, new entries SHALL be rejected.
**Validates: Requirements 8.2**

### Property 20: Daily Loss Circuit Breaker
*For any* daily loss exceeding 4%, trading SHALL be paused for 24 hours.
**Validates: Requirements 8.3**

### Property 21: Correlation Position Limit
*For any* pair of positions with correlation > 0.7, the total count of such correlated positions SHALL NOT exceed 2.
**Validates: Requirements 8.4**

### Property 22: Weekly Loss Position Reduction
*For any* weekly loss exceeding 8%, position sizes SHALL be reduced by 50% for the remainder of the week.
**Validates: Requirements 8.6**

### Property 23: Regime Conservative Defaults
*For any* regime detection with confidence below 60%, the system SHALL use conservative default parameters.
**Validates: Requirements 9.6**

## Error Handling

1. **Invalid Inputs**: All calculators validate inputs and raise `ValueError` for invalid data
2. **Division by Zero**: Kelly calculator handles zero avg_loss by returning 0
3. **Negative Values**: Position sizer ensures non-negative outputs
4. **Missing Data**: Regime detector falls back to conservative defaults when data is insufficient
5. **API Errors**: Portfolio risk guard handles exchange API errors gracefully

## Testing Strategy

### Property-Based Testing with Hypothesis

The system uses Hypothesis for property-based testing to verify correctness properties across a wide range of inputs.

```python
from hypothesis import given, strategies as st

# Example property test structure
@given(
    atr=st.floats(min_value=0.001, max_value=1000),
    regime=st.sampled_from(list(MarketRegime))
)
def test_atr_multiplier_regime_adaptation(atr, regime):
    """Property 1: ATR multiplier adapts correctly to regime."""
    calculator = OptimizedATRStopCalculator()
    multiplier = calculator.get_multiplier(regime)
    
    if regime == MarketRegime.HIGH_VOLATILITY:
        assert multiplier == 3.0
    elif regime in (MarketRegime.LOW_VOLATILITY, MarketRegime.SIDEWAYS):
        assert multiplier == 2.0
    else:
        assert multiplier == 2.5
```

### Unit Tests

Unit tests cover specific examples and edge cases:
- Zero ATR handling
- Boundary confidence values (69, 70, 79, 80, 89, 90)
- Negative Kelly scenarios
- Maximum position scenarios

### Test Configuration

- Property tests: 100 iterations minimum per property
- Test framework: pytest with hypothesis
- Coverage target: 90%+ for all calculator modules
