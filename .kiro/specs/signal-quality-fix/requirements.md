# Requirements Document

## Introduction

This feature addresses critical signal quality issues in the Cash Cow trading bot that are causing consistent losses. The bot is currently entering trades against the actual market direction, ignoring Enhanced TA confidence scores, and getting stopped out within seconds of entry. The goal is to implement proper signal filtering and direction validation to ensure trades align with actual market momentum.

## Glossary

- **Enhanced TA**: The multi-timeframe technical analysis system that provides confidence scores and market regime detection
- **Cash Cow Scorer**: The 130-point scoring system that evaluates trade opportunities
- **Signal Direction**: Whether to go LONG (buy) or SHORT (sell)
- **Enhanced Confidence**: The 0-100 confidence score from the Enhanced TA analyzer
- **Market Regime**: Current market state (TRENDING, CHOPPY, SIDEWAYS, etc.)
- **Trend Alignment**: Agreement between 4H, 1H, and 15M timeframe trends

## Requirements

### Requirement 1

**User Story:** As a trader, I want the bot to only take trades when Enhanced TA confidence is above a minimum threshold, so that I avoid low-probability setups.

#### Acceptance Criteria

1. WHEN the Enhanced TA confidence score is below 50 THEN the system SHALL reject the trade signal regardless of Cash Cow score
2. WHEN the Enhanced TA confidence score is between 50-70 THEN the system SHALL reduce position size by 50%
3. WHEN the Enhanced TA confidence score is above 70 THEN the system SHALL allow full position sizing

### Requirement 2

**User Story:** As a trader, I want the bot to respect the Enhanced TA's signal direction, so that I don't trade against the actual market momentum.

#### Acceptance Criteria

1. WHEN the Enhanced TA indicates a LONG direction THEN the system SHALL only open LONG positions for that symbol
2. WHEN the Enhanced TA indicates a SHORT direction THEN the system SHALL only open SHORT positions for that symbol
3. WHEN the Cash Cow scorer generates a direction that conflicts with Enhanced TA THEN the system SHALL use the Enhanced TA direction

### Requirement 3

**User Story:** As a trader, I want the bot to avoid trading symbols that have repeatedly failed, so that I don't keep losing on the same bad setups.

#### Acceptance Criteria

1. WHEN a symbol has 3 consecutive stop-losses within 1 hour THEN the system SHALL blacklist that symbol for 30 minutes
2. WHEN a symbol is blacklisted THEN the system SHALL skip scanning that symbol until the blacklist expires
3. WHEN the blacklist period expires THEN the system SHALL resume scanning the symbol normally

### Requirement 4

**User Story:** As a trader, I want wider stop losses in choppy market conditions, so that normal volatility doesn't trigger premature exits.

#### Acceptance Criteria

1. WHEN the market regime is CHOPPY THEN the system SHALL use a 5% stop loss instead of 3%
2. WHEN the market regime is SIDEWAYS THEN the system SHALL use a 4% stop loss instead of 3%
3. WHEN the market regime is TRENDING THEN the system SHALL use the standard 3% stop loss

### Requirement 5

**User Story:** As a trader, I want the bot to confirm trend continuation before entry, so that I don't enter at reversal points.

#### Acceptance Criteria

1. WHEN the 15M price change in the last 3 candles contradicts the signal direction by more than 0.5% THEN the system SHALL reject the signal
2. WHEN the 15M RSI is above 70 for a LONG signal THEN the system SHALL reject the signal as overbought
3. WHEN the 15M RSI is below 30 for a SHORT signal THEN the system SHALL reject the signal as oversold

### Requirement 6

**User Story:** As a trader, I want reduced leverage in unfavorable conditions, so that losses are minimized when signals are weaker.

#### Acceptance Criteria

1. WHEN the market regime is CHOPPY or SIDEWAYS THEN the system SHALL cap leverage at 10x regardless of confidence
2. WHEN Enhanced TA confidence is below 60 THEN the system SHALL cap leverage at 10x
3. WHEN both conditions are favorable (TRENDING regime AND confidence above 70) THEN the system SHALL allow up to 20x leverage

### Requirement 7

**User Story:** As a trader, I want multi-timeframe analysis including 1M and 5M charts, so that I can make more precise entry decisions.

#### Acceptance Criteria

1. WHEN analyzing a symbol THEN the system SHALL fetch and analyze 1M, 5M, 15M, 1H, and 4H timeframes
2. WHEN the 1M and 5M trends align with the signal direction THEN the system SHALL add a micro-trend bonus of 10 points
3. WHEN the 1M and 5M trends contradict the signal direction THEN the system SHALL reject the signal as poorly timed

### Requirement 8

**User Story:** As a trader, I want the bot to detect volume surges and breakouts, so that I can capitalize on momentum moves.

#### Acceptance Criteria

1. WHEN volume exceeds 200% of the 20-period average THEN the system SHALL flag a volume surge event
2. WHEN price breaks above resistance with volume surge THEN the system SHALL add a breakout bonus of 15 points
3. WHEN a breakout is detected THEN the system SHALL use tighter trailing stops to lock in profits
