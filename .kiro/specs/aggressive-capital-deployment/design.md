# Design Document: Aggressive Capital Deployment

## Overview

This design addresses the capital underutilization issue where the trading bot uses only 17-34% of available margin despite configuration targeting 90%. The solution involves updating hardcoded defaults in the `profitable_trading` module components to respect configuration values and implementing more aggressive position sizing.

## Architecture

The changes affect three main components in the existing architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    UnifiedConfig                             │
│  futures_capital_utilization_pct: 90%                       │
│  futures_position_size_min_pct: 8%                          │
│  futures_position_size_max_pct: 25%                         │
│  futures_min_confidence: 35                                  │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ ExposureTracker │ │  PositionSizer  │ │  FuturesEngine  │
│ max: 45% → 90%  │ │ sizes: 5-15%    │ │ positions: 5-8  │
│                 │ │    → 8-25%      │ │    → 8-12       │
│                 │ │ min_conf: 50    │ │                 │
│                 │ │    → 35         │ │                 │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

## Components and Interfaces


### 1. ExposureTracker (exposure_tracker.py)

**Current Issue:** `DEFAULT_MAX_EXPOSURE = 0.45` ignores config

**Changes:**
- Update `DEFAULT_MAX_EXPOSURE` from `0.45` to `0.90`
- Ensure constructor accepts and uses config value

```python
class ExposureTracker:
    DEFAULT_MAX_EXPOSURE = 0.90  # Changed from 0.45
    
    def __init__(self, max_exposure_pct: float = DEFAULT_MAX_EXPOSURE):
        self.max_exposure_pct = max_exposure_pct
```

### 2. ConfidencePositionSizer (position_sizer.py)

**Current Issue:** Conservative sizing (5-15%) and high minimum confidence (50)

**Changes:**
- Update `CONFIDENCE_TO_SIZE` mapping for aggressive sizing
- Lower `MIN_CONFIDENCE` from 50 to 35
- Add new tier for confidence 35-44

```python
class ConfidencePositionSizer:
    CONFIDENCE_TO_SIZE = {
        (90, 100): 0.20,  # 20% (was 15%)
        (80, 89): 0.18,   # 18% (was 12%)
        (70, 79): 0.15,   # 15% (was 10%)
        (60, 69): 0.12,   # 12% (was 7%)
    }
    
    # Regime-aware minimum confidence
    MIN_CONFIDENCE_TRENDING = 60   # Trending markets: 60+
    MIN_CONFIDENCE_SIDEWAYS = 65   # Sideways/Choppy: 65+ (more selective)
```

### 3. UnifiedConfig (unified/config.py)

**Changes:**
- Update `futures_max_positions_min` from 5 to 8
- Update `futures_max_positions_max` from 12 to 12 (unchanged)
- Update `futures_position_size_max_pct` from 20 to 25

### 4. FuturesEngine (unified/futures_engine.py)

**Changes:**
- Update `_get_dynamic_max_positions()` to return higher limits:
  - TRENDING: 12 positions
  - SIDEWAYS: 10 positions  
  - CHOPPY: 8 positions

## Data Models

No new data models required. Existing models remain unchanged:

- `PositionSizeResult`: Contains size_pct, size_usd, confidence_tier, is_rejected, rejection_reason
- `ExposureTracker.positions`: Dict[str, float] mapping symbol to size_pct

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Exposure tracking invariant
*For any* sequence of add_position and remove_position operations on ExposureTracker, the available exposure SHALL equal max_exposure_pct minus the sum of all tracked position sizes.
**Validates: Requirements 1.3, 1.4**

### Property 2: Confidence-to-size mapping consistency
*For any* confidence score between 60 and 100, the Position_Sizer SHALL return a position size that matches the defined tier mapping (60-69→12%, 70-79→15%, 80-89→18%, 90-100→20%).
**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

### Property 3: Regime-aware confidence rejection
*For any* TRENDING regime and confidence below 60, OR *for any* SIDEWAYS/CHOPPY regime and confidence below 65, the Position_Sizer SHALL reject the signal with is_rejected=True.
**Validates: Requirements 4.1, 4.2**

### Property 4: Position size bounds clamping
*For any* calculated position size, the final size SHALL be clamped between the configured minimum (8%) and maximum (25%) bounds.
**Validates: Requirements 5.4**

### Property 5: Config propagation
*For any* ExposureTracker instantiated with a config value, the max_exposure_pct SHALL equal the provided config value.
**Validates: Requirements 1.1, 5.3**

## Error Handling

- **Exposure limit reached**: Return `PositionSizeResult` with `is_rejected=True` and descriptive `rejection_reason`
- **Low confidence**: Return `PositionSizeResult` with `is_rejected=True` and reason stating confidence below minimum
- **Invalid config values**: `UnifiedConfig.validate()` raises `ConfigValidationError` for invalid percentages

## Testing Strategy

### Property-Based Testing

Use **Hypothesis** library for Python property-based testing.

Each property test will:
1. Generate random inputs using Hypothesis strategies
2. Execute the component under test
3. Assert the property holds for all generated inputs
4. Run minimum 100 iterations per property

Property tests must be annotated with:
```python
# **Feature: aggressive-capital-deployment, Property N: <property_text>**
# **Validates: Requirements X.Y**
```

### Unit Tests

Unit tests will cover:
- Default initialization values match expected aggressive defaults
- Regime-based position limits return correct values (TRENDING=12, SIDEWAYS=10, CHOPPY=8)
- Edge cases: exactly at exposure limit, confidence at tier boundaries
