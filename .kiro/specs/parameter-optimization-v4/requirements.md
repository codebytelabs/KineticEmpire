# Requirements Document

## Introduction

This specification defines the research-backed parameter optimizations for Kinetic Empire v4.0. The goal is to significantly improve profitability while reducing risk through optimized trading parameters based on extensive research into crypto futures trading best practices.

## Glossary

- **ATR (Average True Range)**: A volatility indicator measuring the average range of price movement
- **Kelly Criterion**: A formula for optimal position sizing based on win rate and risk/reward
- **Trailing Stop**: A dynamic stop-loss that follows price movement to lock in profits
- **RSI (Relative Strength Index)**: A momentum oscillator measuring speed and change of price movements
- **ADX (Average Directional Index)**: An indicator measuring trend strength
- **Regime**: The current market condition (trending, sideways, choppy, volatile)
- **Leverage**: The multiplier applied to position size using borrowed capital
- **Drawdown**: The peak-to-trough decline in account value

## Requirements

### Requirement 1: ATR-Based Stop Loss Optimization

**User Story:** As a trader, I want wider ATR-based stops optimized for crypto volatility, so that I avoid premature stop-outs during normal price fluctuations.

#### Acceptance Criteria

1. WHEN the ATR_Stop_Calculator computes a stop loss THEN the system SHALL use a multiplier of 2.5x ATR instead of 1.5x
2. WHEN market regime is HIGH_VOLATILITY THEN the system SHALL increase the ATR multiplier to 3.0x
3. WHEN market regime is LOW_VOLATILITY THEN the system SHALL decrease the ATR multiplier to 2.0x
4. WHEN a stop loss is calculated THEN the system SHALL ensure the maximum loss does not exceed 2% of position value
5. IF the calculated stop would exceed 2% loss THEN the system SHALL reduce position size proportionally

### Requirement 2: Leverage Cap Enforcement

**User Story:** As a trader, I want a hard leverage cap to ensure survivable drawdowns, so that my account can recover from losing streaks.

#### Acceptance Criteria

1. WHEN the Leverage_Calculator computes leverage THEN the system SHALL enforce a hard cap of 8x maximum
2. WHEN confidence score is below 70 THEN the system SHALL limit leverage to 3x maximum
3. WHEN confidence score is 70-79 THEN the system SHALL limit leverage to 5x maximum
4. WHEN confidence score is 80-89 THEN the system SHALL limit leverage to 6x maximum
5. WHEN confidence score is 90-100 THEN the system SHALL allow up to 8x leverage
6. WHEN market regime is CHOPPY or HIGH_VOLATILITY THEN the system SHALL reduce maximum leverage by 50%

### Requirement 3: Quarter-Kelly Position Sizing

**User Story:** As a trader, I want conservative position sizing using quarter-Kelly, so that I reduce variance while maintaining growth potential.

#### Acceptance Criteria

1. WHEN the Position_Sizer calculates position size THEN the system SHALL use a Kelly fraction of 0.25
2. WHEN calculating Kelly criterion THEN the system SHALL use historical win rate and average win/loss ratio
3. WHEN Kelly calculation produces a negative value THEN the system SHALL return zero position size
4. WHEN Kelly calculation exceeds 25% of capital THEN the system SHALL cap at 25%
5. IF win rate is below 40% THEN the system SHALL reduce Kelly fraction to 0.15

### Requirement 4: Trailing Stop Optimization

**User Story:** As a trader, I want optimized trailing stops that let winners run while protecting gains, so that I capture more of each profitable move.

#### Acceptance Criteria

1. WHEN a position reaches 2.0% profit THEN the system SHALL activate trailing stop
2. WHEN trailing stop is active THEN the system SHALL use a 0.3% step size
3. WHEN price moves favorably THEN the system SHALL update trailing stop to lock in gains
4. WHEN market regime is TRENDING THEN the system SHALL increase activation threshold to 2.5%
5. WHEN market regime is SIDEWAYS THEN the system SHALL decrease activation threshold to 1.5%
6. IF trailing stop is triggered THEN the system SHALL close the position immediately

### Requirement 5: RSI Entry Threshold Optimization

**User Story:** As a trader, I want more extreme RSI thresholds for entries, so that I only enter on higher probability setups.

#### Acceptance Criteria

1. WHEN evaluating RSI for long entries THEN the system SHALL require RSI below 25 (oversold)
2. WHEN evaluating RSI for short entries THEN the system SHALL require RSI above 75 (overbought)
3. WHEN RSI is between 25 and 75 THEN the system SHALL require additional confirmation signals
4. WHEN RSI crosses the threshold THEN the system SHALL wait for confirmation candle before entry
5. IF RSI divergence is detected THEN the system SHALL increase signal confidence by 10 points

### Requirement 6: ADX Trend Threshold Optimization

**User Story:** As a trader, I want a lower ADX threshold to capture more crypto trends, so that I don't miss profitable opportunities.

#### Acceptance Criteria

1. WHEN evaluating trend strength THEN the system SHALL consider ADX above 20 as trending
2. WHEN ADX is below 15 THEN the system SHALL classify market as SIDEWAYS
3. WHEN ADX is between 15 and 20 THEN the system SHALL reduce position size by 30%
4. WHEN ADX is above 30 THEN the system SHALL increase confidence score by 5 points
5. IF ADX is rising THEN the system SHALL favor trend-following entries

### Requirement 7: Volume Confirmation Enhancement

**User Story:** As a trader, I want stronger volume confirmation to reduce fakeouts, so that I enter only on moves with institutional backing.

#### Acceptance Criteria

1. WHEN evaluating volume for entry THEN the system SHALL require 1.5x average volume
2. WHEN volume is below 1.5x average THEN the system SHALL reduce position size by 40%
3. WHEN volume spike exceeds 2.5x average THEN the system SHALL increase confidence by 10 points
4. WHEN volume is declining during a move THEN the system SHALL flag potential reversal
5. IF volume confirmation fails THEN the system SHALL require additional technical confirmation

### Requirement 8: Portfolio Risk Limits

**User Story:** As a trader, I want tighter portfolio risk limits, so that I protect my capital during adverse market conditions.

#### Acceptance Criteria

1. WHEN total open positions exceed 8 THEN the system SHALL reject new entries
2. WHEN total margin usage exceeds 80% THEN the system SHALL reject new entries
3. WHEN daily loss exceeds 4% THEN the system SHALL pause trading for 24 hours
4. WHEN correlation between positions exceeds 0.7 THEN the system SHALL limit to 2 correlated positions
5. IF emergency conditions are detected THEN the system SHALL close all positions immediately
6. WHEN weekly loss exceeds 8% THEN the system SHALL reduce position sizes by 50% for remainder of week

### Requirement 9: Regime-Adaptive Parameters

**User Story:** As a trader, I want parameters that automatically adapt to market regime, so that the system performs well in all conditions.

#### Acceptance Criteria

1. WHEN regime changes to TRENDING THEN the system SHALL increase trailing activation to 2.5%
2. WHEN regime changes to SIDEWAYS THEN the system SHALL tighten stops to 2.0x ATR
3. WHEN regime changes to CHOPPY THEN the system SHALL reduce leverage by 50%
4. WHEN regime changes to HIGH_VOLATILITY THEN the system SHALL widen stops to 3.0x ATR
5. WHEN regime is detected THEN the system SHALL log the regime change with timestamp
6. IF regime detection confidence is below 60% THEN the system SHALL use conservative defaults
