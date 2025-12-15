# Cash Cow Upgrade - Technical Design

## Overview

The Cash Cow Upgrade transforms Kinetic Empire into a sophisticated, adaptive trading system by implementing DayTraderAI's proven money-making architecture adapted for crypto markets. The system uses confidence-based position sizing, consecutive loss protection, enhanced multi-factor scoring, and regime-adaptive risk management.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CASH COW TRADING ENGINE                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │  OPPORTUNITY    │  │   POSITION      │  │     RISK        │         │
│  │    SCORER       │  │    SIZER        │  │   MANAGER       │         │
│  │                 │  │                 │  │                 │         │
│  │ • 130-pt Score  │  │ • Confidence    │  │ • Circuit Break │         │
│  │ • Upside Anal.  │  │ • Regime Adapt  │  │ • Loss Tracking │         │
│  │ • MTF Alignment │  │ • Loss Protect  │  │ • Stop Enforce  │         │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘         │
│           │                    │                    │                   │
│           └────────────────────┼────────────────────┘                   │
│                                │                                        │
│                    ┌───────────▼───────────┐                           │
│                    │   TRADE EXECUTOR      │                           │
│                    │                       │                           │
│                    │ • Entry Validation    │                           │
│                    │ • Position Management │                           │
│                    │ • Exit Handling       │                           │
│                    └───────────────────────┘                           │
└─────────────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. OpportunityScorer

Calculates a 130-point score for trading opportunities.

```python
@dataclass
class OpportunityScore:
    technical_score: int      # 0-40 points
    momentum_score: int       # 0-25 points
    volume_score: int         # 0-20 points
    volatility_score: int     # 0-15 points
    regime_score: int         # 0-10 points
    sentiment_score: int      # 0-10 points
    growth_score: int         # 0-10 points
    upside_score: int         # 0-25 points (bonus)
    alignment_bonus: int      # -10 to +10 points
    rr_bonus: int             # 0-5 points
    total_score: int          # 0-130+ points
    
class OpportunityScorer:
    def score_technical(self, features: Dict) -> int: ...
    def score_momentum(self, features: Dict) -> int: ...
    def score_volume(self, features: Dict) -> int: ...
    def score_volatility(self, features: Dict) -> int: ...
    def score_regime(self, regime: MarketRegime) -> int: ...
    def score_sentiment(self, fear_greed: int) -> int: ...
    def score_growth_potential(self, features: Dict) -> int: ...
    def calculate_total(self, features: Dict) -> OpportunityScore: ...
```

### 2. UpsideAnalyzer

Calculates room to run and risk/reward ratios.

```python
@dataclass
class UpsideAnalysis:
    distance_to_resistance_pct: float
    distance_to_support_pct: float
    risk_reward_ratio: float
    upside_quality: str  # "excellent", "good", "limited", "poor"
    upside_score: int    # 0-25 points
    rr_bonus: int        # 0-5 points
    penalty: int         # 0-15 points

class UpsideAnalyzer:
    def calculate_distance_to_resistance(self, price: float, resistance: float) -> float: ...
    def calculate_risk_reward(self, price: float, resistance: float, support: float) -> float: ...
    def analyze(self, price: float, resistance: float, support: float) -> UpsideAnalysis: ...
```

### 3. ConfidenceBasedSizer

Calculates position sizes based on confidence scores.

```python
@dataclass
class SizingResult:
    base_size: float
    confidence_multiplier: float
    regime_multiplier: float
    loss_protection_multiplier: float
    final_size: float
    rejection_reason: Optional[str]

class ConfidenceBasedSizer:
    def get_confidence_multiplier(self, confidence: int) -> float: ...
    def get_regime_multiplier(self, regime: MarketRegime) -> float: ...
    def get_loss_protection_multiplier(self, consecutive_losses: int) -> float: ...
    def calculate_size(
        self, 
        confidence: int, 
        regime: MarketRegime, 
        consecutive_losses: int,
        portfolio_value: float,
        base_risk_pct: float
    ) -> SizingResult: ...
```

### 4. ConsecutiveLossTracker

Tracks losing streaks and provides protection multipliers.

```python
class ConsecutiveLossTracker:
    consecutive_losses: int = 0
    
    def record_loss(self) -> None: ...
    def record_win(self) -> None: ...
    def get_protection_multiplier(self) -> float: ...
    def reset(self) -> None: ...
```

### 5. CircuitBreaker

Halts trading when daily losses exceed limits.

```python
class CircuitBreaker:
    daily_loss_limit_pct: float = 0.02  # 2%
    is_triggered: bool = False
    trigger_time: Optional[datetime] = None
    
    def check_and_trigger(self, daily_pnl: float, portfolio_value: float) -> bool: ...
    def reset_for_new_day(self) -> None: ...
    def can_enter_new_trade(self) -> bool: ...
    def can_exit_position(self) -> bool: ...
```

### 6. MultiTimeframeAligner

Checks trend alignment across multiple timeframes.

```python
@dataclass
class AlignmentResult:
    timeframes_checked: List[str]
    aligned_count: int
    daily_conflicts: bool
    alignment_bonus: int
    
class MultiTimeframeAligner:
    TIMEFRAMES = ["5m", "15m", "1h", "4h", "1d"]
    
    def get_trend_direction(self, symbol: str, timeframe: str) -> str: ...
    def check_alignment(self, symbol: str, trade_direction: str) -> AlignmentResult: ...
```

## Data Models

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict

class MarketRegime(Enum):
    TRENDING = "trending"
    BEAR = "bear"
    CHOPPY = "choppy"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"

class UpsideQuality(Enum):
    EXCELLENT = "excellent"  # >5% room
    GOOD = "good"            # 3-5% room
    LIMITED = "limited"      # 1-3% room
    POOR = "poor"            # <1% room

@dataclass
class TradingFeatures:
    # Price data
    price: float
    resistance: float
    support: float
    vwap: float
    
    # Technical indicators
    ema_9: float
    ema_21: float
    ema_diff_pct: float
    rsi: float
    macd_histogram: float
    adx: float
    plus_di: float
    minus_di: float
    
    # Volume
    volume_ratio: float
    obv_trend: int  # 1, 0, -1
    
    # Volatility
    atr: float
    atr_pct: float
    
    # Crypto-specific
    funding_rate: float
    btc_correlation: float
    fear_greed_index: int

@dataclass
class TradeDecision:
    symbol: str
    direction: str  # "long" or "short"
    confidence_score: int
    opportunity_score: OpportunityScore
    upside_analysis: UpsideAnalysis
    sizing_result: SizingResult
    should_trade: bool
    rejection_reasons: List[str]
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Confidence multiplier bounds
*For any* confidence score, the confidence multiplier returned by the Position Sizer SHALL be one of: 0.0 (rejected), 1.0, 1.5, or 2.0, and SHALL correspond to the correct confidence bracket.
**Validates: Requirements 1.1, 1.2, 1.3, 1.4**

### Property 2: Position size cap enforcement
*For any* calculated position size and portfolio value, the final position size SHALL NOT exceed 10% of portfolio value.
**Validates: Requirements 1.5**

### Property 3: Consecutive loss counter correctness
*For any* sequence of trade results, the consecutive loss counter SHALL equal the number of consecutive losses at the end of the sequence, and SHALL reset to zero after any win.
**Validates: Requirements 2.1, 2.2**

### Property 4: Loss protection multiplier correctness
*For any* consecutive loss count, the protection multiplier SHALL be 1.0 for 0-2 losses, 0.5 for 3-4 losses, and 0.25 for 5+ losses.
**Validates: Requirements 2.3, 2.4, 2.5**

### Property 5: Circuit breaker activation
*For any* daily P&L and portfolio value where daily loss exceeds 2%, the circuit breaker SHALL be triggered and new entries SHALL be blocked.
**Validates: Requirements 3.1, 3.4**

### Property 6: Circuit breaker reset
*For any* triggered circuit breaker, after a new trading day begins, the circuit breaker SHALL be reset and trading SHALL be allowed.
**Validates: Requirements 3.3**

### Property 7: Component score bounds
*For any* set of trading features, each component score SHALL be within its defined bounds: technical (0-40), momentum (0-25), volume (0-20), volatility (0-15), regime (0-10), sentiment (0-10), growth (0-10).
**Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7**

### Property 8: Total score summation
*For any* opportunity score, the total score SHALL equal the sum of all component scores plus bonuses minus penalties.
**Validates: Requirements 4.8**

### Property 9: Upside distance calculation
*For any* price and resistance level where resistance > price, the distance to resistance percentage SHALL equal ((resistance - price) / price) * 100.
**Validates: Requirements 5.1**

### Property 10: Upside score assignment
*For any* distance to resistance percentage, the upside score SHALL be: 25 for >5%, 20 for 3-5%, 10 for 1-3%, 0 with -15 penalty for <1%.
**Validates: Requirements 5.2, 5.3, 5.4, 5.5**

### Property 11: Risk/reward calculation
*For any* price, resistance, and support where support < price < resistance, the R/R ratio SHALL equal (resistance - price) / (price - support).
**Validates: Requirements 5.6**

### Property 12: R/R bonus assignment
*For any* R/R ratio, the bonus SHALL be: 5 for >3:1, 3 for >2:1, 0 otherwise.
**Validates: Requirements 5.7, 5.8**

### Property 13: Regime multiplier correctness
*For any* market regime, the regime multiplier SHALL be: 1.0 for trending, 0.5 for bear, 0.75 for choppy, 0.85 for high volatility.
**Validates: Requirements 6.1, 6.2, 6.3, 6.4**

### Property 14: Conservative multiplier selection
*For any* combination of regime conditions, the final regime multiplier SHALL be the minimum of all applicable multipliers.
**Validates: Requirements 6.5**

### Property 15: Minimum stop distance enforcement
*For any* calculated stop loss, the stop distance SHALL be at least 1.5% from entry price.
**Validates: Requirements 7.1, 7.2, 7.3**

### Property 16: Opportunity ranking correctness
*For any* list of opportunities with scores, the ranked list SHALL be sorted in descending order by total score.
**Validates: Requirements 8.2**

### Property 17: Alignment bonus correctness
*For any* set of timeframe alignments, the bonus SHALL be: +10 for 5/5 aligned, +5 for 4/5 aligned, -10 for <3/5 aligned, with additional -5 if daily conflicts.
**Validates: Requirements 9.2, 9.3, 9.4, 9.5**

### Property 18: Funding rate bonus correctness
*For any* funding rate and trade direction, the bonus SHALL be: +5 for long when funding < -0.1%, +5 for short when funding > 0.1%, 0 otherwise.
**Validates: Requirements 10.1, 10.2**

### Property 19: BTC correlation adjustment
*For any* BTC correlation and volatility, position size SHALL be reduced by 20% when correlation is high AND BTC is volatile.
**Validates: Requirements 10.3, 10.4**

## Error Handling

1. **Invalid Input Handling**: All scoring functions return 0 for invalid/missing inputs
2. **Division by Zero**: Protected in R/R calculations and percentage calculations
3. **Circuit Breaker Logging**: All triggers logged with timestamp and context
4. **Graceful Degradation**: If sentiment API fails, use neutral score (5/10)

## Testing Strategy

### Unit Testing
- Test each scoring component with known inputs
- Test edge cases (boundary values, zero values)
- Test error conditions

### Property-Based Testing
- Use Hypothesis library for Python
- Configure minimum 100 iterations per property
- Test all 19 correctness properties
- Tag each test with property reference

**Property-Based Testing Framework**: Hypothesis (Python)

Each property test MUST:
1. Run minimum 100 iterations
2. Include comment: `# **Feature: cash-cow-upgrade, Property {N}: {property_text}**`
3. Generate random valid inputs using Hypothesis strategies
4. Assert the property holds for all generated inputs
