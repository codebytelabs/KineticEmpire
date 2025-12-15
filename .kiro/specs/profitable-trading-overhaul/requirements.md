# Requirements Document

## Introduction

This specification defines a comprehensive overhaul of the Kinetic Empire trading bot to transform it from a losing system into a profitable, risk-managed trading machine. The overhaul addresses critical issues identified in live trading: the HIGH-QUALITY BYPASS allowing trades in unfavorable regimes, fixed position sizing ignoring confidence levels, static leverage regardless of market conditions, and direction detection failures in choppy markets.

The system will implement dynamic position sizing (5-15% of portfolio), confidence-based leverage scaling (2x-10x), regime-aware trading restrictions, ATR-based stop losses, and improved direction validation to ensure trades only occur when conditions are truly favorable.

## Glossary

- **Regime**: Market condition classification (TRENDING, SIDEWAYS, CHOPPY)
- **ATR**: Average True Range - volatility indicator measuring price movement
- **Confidence Score**: Combined score from Enhanced TA (0-100) indicating signal strength
- **Position Size**: Percentage of portfolio allocated to a single trade (5-15%)
- **Leverage**: Multiplier applied to position (2x-10x)
- **Micro-Alignment**: Confirmation from 1M and 5M timeframes matching signal direction
- **Blacklist**: Temporary ban on trading a symbol after consecutive losses
- **Trailing Stop**: Dynamic stop loss that follows profitable price movement
- **Direction Validation**: Confirmation that actual price movement matches predicted direction

## Requirements

### Requirement 1: Disable High-Quality Bypass

**User Story:** As a trader, I want the system to strictly enforce regime-based trading restrictions, so that I avoid taking directional trades in unfavorable market conditions.

#### Acceptance Criteria

1. WHEN the market regime is CHOPPY THEN the Signal_Quality_Gate SHALL reject all directional trade signals regardless of confidence score
2. WHEN the market regime is SIDEWAYS THEN the Signal_Quality_Gate SHALL reject all directional trade signals regardless of confidence score
3. WHEN the high_quality_bypass_enabled configuration is set to False THEN the Signal_Quality_Gate SHALL not allow any bypass of regime restrictions
4. WHEN a signal is rejected due to unfavorable regime THEN the Signal_Quality_Gate SHALL log the rejection reason including the regime type

### Requirement 2: Dynamic Position Sizing Based on Confidence

**User Story:** As a trader, I want position sizes to scale with signal confidence, so that I risk more on high-conviction trades and less on uncertain ones.

#### Acceptance Criteria

1. WHEN confidence score is between 90-100 THEN the Position_Sizer SHALL calculate position size as 15% of available portfolio
2. WHEN confidence score is between 80-89 THEN the Position_Sizer SHALL calculate position size as 12% of available portfolio
3. WHEN confidence score is between 70-79 THEN the Position_Sizer SHALL calculate position size as 10% of available portfolio
4. WHEN confidence score is between 60-69 THEN the Position_Sizer SHALL calculate position size as 7% of available portfolio
5. WHEN confidence score is between 50-59 THEN the Position_Sizer SHALL calculate position size as 5% of available portfolio
6. WHEN confidence score is below 50 THEN the Position_Sizer SHALL reject the trade signal
7. WHEN calculating position size THEN the Position_Sizer SHALL ensure total portfolio exposure across all positions does not exceed 45%

### Requirement 3: Regime-Based Leverage Scaling

**User Story:** As a trader, I want leverage to automatically adjust based on market conditions and confidence, so that I use higher leverage only when conditions are favorable.

#### Acceptance Criteria

1. WHEN market regime is TRENDING and confidence is 90-100 THEN the Leverage_Calculator SHALL return maximum leverage of 10x
2. WHEN market regime is TRENDING and confidence is 70-89 THEN the Leverage_Calculator SHALL return leverage of 7x
3. WHEN market regime is TRENDING and confidence is 50-69 THEN the Leverage_Calculator SHALL return leverage of 5x
4. WHEN market regime is SIDEWAYS THEN the Leverage_Calculator SHALL return maximum leverage of 3x regardless of confidence
5. WHEN market regime is CHOPPY THEN the Leverage_Calculator SHALL return maximum leverage of 2x regardless of confidence
6. WHEN consecutive losses exceed 2 THEN the Leverage_Calculator SHALL reduce calculated leverage by 50%

### Requirement 4: ATR-Based Stop Loss Calculation

**User Story:** As a trader, I want stop losses calculated based on market volatility, so that stops are appropriately sized for current conditions rather than using fixed percentages.

#### Acceptance Criteria

1. WHEN calculating stop loss THEN the ATR_Stop_Calculator SHALL use the 14-period ATR from the 15-minute timeframe
2. WHEN market regime is TRENDING THEN the ATR_Stop_Calculator SHALL set stop loss at 2.0x ATR from entry price
3. WHEN market regime is SIDEWAYS THEN the ATR_Stop_Calculator SHALL set stop loss at 2.5x ATR from entry price
4. WHEN market regime is CHOPPY THEN the ATR_Stop_Calculator SHALL set stop loss at 3.0x ATR from entry price
5. WHEN ATR-based stop exceeds 5% of entry price THEN the ATR_Stop_Calculator SHALL cap the stop loss at 5%
6. WHEN ATR-based stop is less than 1% of entry price THEN the ATR_Stop_Calculator SHALL set minimum stop loss at 1%

### Requirement 5: Direction Validation with Price Momentum

**User Story:** As a trader, I want the system to validate predicted direction against actual recent price movement, so that I avoid entering trades where price is moving opposite to the signal.

#### Acceptance Criteria

1. WHEN a LONG signal is generated THEN the Direction_Validator SHALL confirm price has not fallen more than 0.3% in the last 5 candles
2. WHEN a SHORT signal is generated THEN the Direction_Validator SHALL confirm price has not risen more than 0.3% in the last 5 candles
3. WHEN price movement contradicts signal direction by more than 0.3% THEN the Direction_Validator SHALL reject the signal
4. WHEN direction validation fails THEN the Direction_Validator SHALL log the contradiction percentage and recent price movement

### Requirement 6: Improved Trailing Stop Logic

**User Story:** As a trader, I want trailing stops that protect profits without exiting too early, so that I capture larger moves in trending markets.

#### Acceptance Criteria

1. WHEN position profit reaches 2% THEN the Trailing_Stop_Manager SHALL activate trailing stop mode
2. WHEN trailing stop is active THEN the Trailing_Stop_Manager SHALL trail at 1.5x ATR from the peak profit price
3. WHEN trailing stop is active and profit exceeds 5% THEN the Trailing_Stop_Manager SHALL tighten trail to 1.0x ATR
4. WHEN trailing stop is triggered THEN the Trailing_Stop_Manager SHALL close the position and log peak profit vs exit profit

### Requirement 7: Faster Blacklist Trigger

**User Story:** As a trader, I want symbols blacklisted after fewer consecutive losses, so that I stop trading problematic symbols sooner.

#### Acceptance Criteria

1. WHEN a symbol experiences 1 stop-loss within 30 minutes THEN the Blacklist_Manager SHALL blacklist the symbol for 60 minutes
2. WHEN a blacklisted symbol's blacklist period expires THEN the Blacklist_Manager SHALL remove the symbol from the blacklist
3. WHEN attempting to trade a blacklisted symbol THEN the Signal_Quality_Gate SHALL reject the signal with reason "Symbol is blacklisted"

### Requirement 8: Maximum Portfolio Exposure Limit

**User Story:** As a trader, I want the system to limit total portfolio exposure, so that I never have too much capital at risk simultaneously.

#### Acceptance Criteria

1. WHEN total open position value exceeds 45% of portfolio THEN the Position_Manager SHALL reject new trade signals
2. WHEN calculating available capital for new trades THEN the Position_Manager SHALL subtract current exposure from the 45% limit
3. WHEN a position is closed THEN the Position_Manager SHALL recalculate available exposure immediately

### Requirement 9: Regime Detection Improvement

**User Story:** As a trader, I want more accurate regime detection, so that the system correctly identifies trending vs choppy markets.

#### Acceptance Criteria

1. WHEN ADX is above 25 and price is above 50-period MA THEN the Regime_Detector SHALL classify regime as TRENDING (bullish)
2. WHEN ADX is above 25 and price is below 50-period MA THEN the Regime_Detector SHALL classify regime as TRENDING (bearish)
3. WHEN ADX is between 15-25 THEN the Regime_Detector SHALL classify regime as SIDEWAYS
4. WHEN ADX is below 15 THEN the Regime_Detector SHALL classify regime as CHOPPY
5. WHEN regime changes THEN the Regime_Detector SHALL log the transition and new regime classification

### Requirement 10: Trade Entry Delay for Confirmation

**User Story:** As a trader, I want a brief delay before trade execution to confirm the signal, so that I avoid entering on false signals that quickly reverse.

#### Acceptance Criteria

1. WHEN a trade signal passes all quality gates THEN the Entry_Confirmer SHALL wait for 2 candle closes (30 seconds on 15s timeframe) before execution
2. WHILE waiting for confirmation THEN the Entry_Confirmer SHALL monitor if price moves more than 0.5% against the signal direction
3. IF price moves against signal during confirmation period THEN the Entry_Confirmer SHALL cancel the pending entry
4. WHEN confirmation period completes successfully THEN the Entry_Confirmer SHALL execute the trade at current market price
