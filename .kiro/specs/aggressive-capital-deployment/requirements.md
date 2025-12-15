# Requirements Document

## Introduction

This feature addresses the critical issue of underutilized capital in the Kinetic Empire trading bot. Currently, the bot is only using 17-34% of available margin despite configuration settings targeting 90% utilization. The root cause is a disconnect between the config values and hardcoded defaults in the profitable_trading module components. This upgrade will ensure the bot aggressively deploys capital according to user preferences, maximizing trading opportunities and potential returns.

## Glossary

- **Exposure_Tracker**: Component that tracks total portfolio exposure across all positions and enforces maximum exposure limits
- **Position_Sizer**: Component that calculates position sizes based on signal confidence scores
- **Capital_Utilization**: Percentage of available margin/buying power that should be deployed in positions
- **Confidence_Score**: A 0-100 rating indicating signal quality and trade conviction
- **Market_Regime**: Current market condition classification (TRENDING, SIDEWAYS, CHOPPY)
- **Margin**: Collateral required to open leveraged futures positions

## Requirements

### Requirement 1

**User Story:** As a trader, I want the bot to use 90% of my available capital, so that I can maximize my trading opportunities and potential returns.

#### Acceptance Criteria

1. WHEN the Exposure_Tracker initializes THEN the Exposure_Tracker SHALL use the configured `futures_capital_utilization_pct` value (90%) as the maximum exposure limit
2. WHEN the Position_Sizer calculates position sizes THEN the Position_Sizer SHALL respect the configured 90% capital utilization target
3. WHEN total exposure reaches 90% of available capital THEN the Exposure_Tracker SHALL prevent new position entries
4. WHEN a position is closed THEN the Exposure_Tracker SHALL immediately recalculate available exposure for new positions

### Requirement 2

**User Story:** As a trader, I want larger position sizes for all confidence levels, so that each trade has meaningful impact on my portfolio.

#### Acceptance Criteria

1. WHEN a signal has confidence 90-100 THEN the Position_Sizer SHALL allocate 20% position size
2. WHEN a signal has confidence 80-89 THEN the Position_Sizer SHALL allocate 18% position size
3. WHEN a signal has confidence 70-79 THEN the Position_Sizer SHALL allocate 15% position size
4. WHEN a signal has confidence 60-69 THEN the Position_Sizer SHALL allocate 12% position size

### Requirement 3

**User Story:** As a trader, I want more concurrent positions allowed, so that I can diversify across multiple opportunities.

#### Acceptance Criteria

1. WHEN market regime is TRENDING THEN the Futures_Engine SHALL allow up to 12 concurrent positions
2. WHEN market regime is SIDEWAYS THEN the Futures_Engine SHALL allow up to 10 concurrent positions
3. WHEN market regime is CHOPPY THEN the Futures_Engine SHALL allow up to 8 concurrent positions
4. WHEN position count reaches the regime-based limit THEN the Futures_Engine SHALL stop scanning for new entries

### Requirement 4

**User Story:** As a trader, I want regime-aware confidence thresholds, so that the bot is more selective in difficult market conditions.

#### Acceptance Criteria

1. WHEN market regime is TRENDING and signal confidence is 60 or higher THEN the Position_Sizer SHALL accept the signal
2. WHEN market regime is SIDEWAYS or CHOPPY and signal confidence is 65 or higher THEN the Position_Sizer SHALL accept the signal
3. WHEN the Position_Sizer rejects a signal THEN the Position_Sizer SHALL log the rejection reason with the regime-specific threshold

### Requirement 5

**User Story:** As a trader, I want the hardcoded defaults in the codebase to match my aggressive configuration, so that there are no hidden bottlenecks limiting capital deployment.

#### Acceptance Criteria

1. WHEN ExposureTracker is instantiated without parameters THEN the ExposureTracker SHALL default to 90% max exposure
2. WHEN ConfidencePositionSizer is instantiated THEN the ConfidencePositionSizer SHALL use the aggressive confidence-to-size mapping
3. WHEN the unified config specifies capital utilization THEN all components SHALL respect that configuration value
4. WHEN position size bounds are configured THEN the Position_Sizer SHALL clamp sizes to the configured min (8%) and max (25%) bounds
