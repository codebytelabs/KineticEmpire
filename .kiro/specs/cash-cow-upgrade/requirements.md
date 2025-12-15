# Cash Cow Upgrade - Requirements Specification

## Introduction

The Cash Cow Upgrade transforms Kinetic Empire from a basic crypto trading bot into a sophisticated, adaptive trading system inspired by DayTraderAI's proven money-making architecture. This upgrade implements confidence-based position sizing, consecutive loss protection, enhanced multi-factor scoring, upside potential analysis, and regime-adaptive risk management to maximize profits while minimizing losses.

## Glossary

- **Confidence Score**: A 0-100 score indicating the quality of a trading opportunity based on multiple technical and market factors
- **Position Sizer**: Component that calculates trade size based on confidence score and risk parameters
- **Consecutive Loss Tracker**: Component that monitors losing streaks and reduces position sizes accordingly
- **Opportunity Scorer**: Component that evaluates trading opportunities using a 130-point multi-factor scoring system
- **Upside Analyzer**: Component that calculates room to run (distance to resistance) and risk/reward ratios
- **Regime Detector**: Component that identifies current market conditions (trending, choppy, bear, high volatility)
- **Circuit Breaker**: Safety mechanism that halts trading when daily loss limits are exceeded

## Requirements

### Requirement 1: Confidence-Based Position Sizing

**User Story:** As a trader, I want position sizes to scale with trade confidence, so that I maximize profits on high-conviction trades while limiting exposure on uncertain setups.

#### Acceptance Criteria

1. WHEN the Confidence Score exceeds 85 THEN the Position Sizer SHALL apply a 2.0x multiplier to the base position size
2. WHEN the Confidence Score is between 75 and 84 THEN the Position Sizer SHALL apply a 1.5x multiplier to the base position size
3. WHEN the Confidence Score is between 65 and 74 THEN the Position Sizer SHALL apply a 1.0x multiplier to the base position size
4. WHEN the Confidence Score is below 65 THEN the Position Sizer SHALL reject the trade and return a zero position size
5. WHEN calculating position size THEN the Position Sizer SHALL enforce a maximum position size of 10% of portfolio value

### Requirement 2: Consecutive Loss Protection

**User Story:** As a trader, I want automatic position size reduction during losing streaks, so that I protect capital and prevent revenge trading.

#### Acceptance Criteria

1. WHEN a trade results in a loss THEN the Consecutive Loss Tracker SHALL increment the loss counter by one
2. WHEN a trade results in a profit THEN the Consecutive Loss Tracker SHALL reset the loss counter to zero
3. WHEN the consecutive loss count reaches 3 THEN the Position Sizer SHALL apply a 0.5x reduction multiplier to all subsequent trades
4. WHEN the consecutive loss count reaches 5 THEN the Position Sizer SHALL apply a 0.25x reduction multiplier to all subsequent trades
5. WHEN a winning trade occurs after consecutive losses THEN the Consecutive Loss Tracker SHALL restore normal position sizing

### Requirement 3: Daily Loss Circuit Breaker

**User Story:** As a trader, I want automatic trading halt when daily losses exceed limits, so that I prevent catastrophic drawdowns.

#### Acceptance Criteria

1. WHEN daily realized losses exceed 2% of portfolio value THEN the Circuit Breaker SHALL halt all new trade entries
2. WHEN the Circuit Breaker is triggered THEN the System SHALL log the event with timestamp and loss amount
3. WHEN a new trading day begins THEN the Circuit Breaker SHALL reset and allow trading to resume
4. WHEN the Circuit Breaker is active THEN the System SHALL allow position exits but prevent new entries

### Requirement 4: Enhanced 130-Point Opportunity Scoring

**User Story:** As a trader, I want comprehensive multi-factor scoring of opportunities, so that I only trade the highest quality setups.

#### Acceptance Criteria

1. WHEN evaluating an opportunity THEN the Opportunity Scorer SHALL calculate a Technical Setup score from 0 to 40 points based on EMA crossover freshness, RSI zones, MACD histogram strength, and VWAP proximity
2. WHEN evaluating an opportunity THEN the Opportunity Scorer SHALL calculate a Momentum score from 0 to 25 points based on ADX strength, directional movement spread, and price momentum
3. WHEN evaluating an opportunity THEN the Opportunity Scorer SHALL calculate a Volume score from 0 to 20 points based on volume ratio, volume surge detection, and OBV confirmation
4. WHEN evaluating an opportunity THEN the Opportunity Scorer SHALL calculate a Volatility score from 0 to 15 points based on ATR levels
5. WHEN evaluating an opportunity THEN the Opportunity Scorer SHALL calculate a Market Regime score from 0 to 10 points based on current market conditions
6. WHEN evaluating an opportunity THEN the Opportunity Scorer SHALL calculate a Crypto Sentiment score from 0 to 10 points based on Fear and Greed Index
7. WHEN evaluating an opportunity THEN the Opportunity Scorer SHALL calculate a Growth Potential score from 0 to 10 points based on volatility, momentum strength, and volume surge
8. WHEN all component scores are calculated THEN the Opportunity Scorer SHALL sum them to produce a total score from 0 to 130

### Requirement 5: Upside Potential Analysis

**User Story:** As a trader, I want to know the room to run before entering trades, so that I avoid chasing extended moves with limited upside.

#### Acceptance Criteria

1. WHEN analyzing upside potential THEN the Upside Analyzer SHALL calculate distance to resistance as a percentage of current price
2. WHEN distance to resistance exceeds 5% THEN the Upside Analyzer SHALL assign 25 bonus points (excellent room)
3. WHEN distance to resistance is between 3% and 5% THEN the Upside Analyzer SHALL assign 20 bonus points (good room)
4. WHEN distance to resistance is between 1% and 3% THEN the Upside Analyzer SHALL assign 10 bonus points (limited room)
5. WHEN distance to resistance is below 1% THEN the Upside Analyzer SHALL assign 0 points and apply a 15-point penalty
6. WHEN analyzing upside potential THEN the Upside Analyzer SHALL calculate risk/reward ratio using distance to resistance and distance to support
7. WHEN risk/reward ratio exceeds 3:1 THEN the Upside Analyzer SHALL apply a 5-point bonus
8. WHEN risk/reward ratio exceeds 2:1 THEN the Upside Analyzer SHALL apply a 3-point bonus

### Requirement 6: Regime-Adaptive Position Sizing

**User Story:** As a trader, I want position sizes to adapt to market conditions, so that I reduce risk in difficult markets and maximize opportunity in favorable conditions.

#### Acceptance Criteria

1. WHEN the Regime Detector identifies a trending market THEN the Position Sizer SHALL apply a 1.0x regime multiplier
2. WHEN the Regime Detector identifies a bear market THEN the Position Sizer SHALL apply a 0.5x regime multiplier
3. WHEN the Regime Detector identifies a choppy market THEN the Position Sizer SHALL apply a 0.75x regime multiplier
4. WHEN the Regime Detector identifies high volatility THEN the Position Sizer SHALL apply a 0.85x regime multiplier
5. WHEN multiple regime conditions apply THEN the Position Sizer SHALL use the most conservative multiplier

### Requirement 7: Minimum Stop Distance Enforcement

**User Story:** As a trader, I want guaranteed minimum stop distances, so that I avoid being stopped out by normal market noise.

#### Acceptance Criteria

1. WHEN calculating stop loss THEN the System SHALL enforce a minimum stop distance of 1.5% from entry price
2. WHEN ATR-based stop is closer than 1.5% THEN the System SHALL use the 1.5% minimum instead
3. WHEN validating a trade THEN the System SHALL reject trades where the calculated stop distance is below the minimum

### Requirement 8: Dynamic Universe Scanning

**User Story:** As a trader, I want continuous scanning of all available crypto pairs, so that I always trade the best opportunities across the entire market.

#### Acceptance Criteria

1. WHEN scanning the market THEN the Scanner SHALL evaluate all USDT and USDC pairs with sufficient volume
2. WHEN ranking opportunities THEN the Scanner SHALL sort by the 130-point opportunity score
3. WHEN selecting trades THEN the Scanner SHALL return the top N opportunities that pass all filters
4. WHEN a higher-scored opportunity appears THEN the Scanner SHALL prioritize it over lower-scored existing positions

### Requirement 9: Multi-Timeframe Alignment

**User Story:** As a trader, I want confirmation across multiple timeframes, so that I trade with the larger trend and avoid counter-trend entries.

#### Acceptance Criteria

1. WHEN analyzing alignment THEN the System SHALL check trend direction on 5m, 15m, 1h, 4h, and daily timeframes
2. WHEN all timeframes align THEN the System SHALL apply a 10-point alignment bonus
3. WHEN 4 of 5 timeframes align THEN the System SHALL apply a 5-point alignment bonus
4. WHEN fewer than 3 timeframes align THEN the System SHALL apply a 10-point penalty
5. WHEN the daily timeframe conflicts with the trade direction THEN the System SHALL apply an additional 5-point penalty

### Requirement 10: Crypto-Specific Enhancements

**User Story:** As a crypto trader, I want crypto-specific indicators integrated into the scoring system, so that I capitalize on unique crypto market dynamics.

#### Acceptance Criteria

1. WHEN funding rate is extremely negative (below -0.1%) THEN the System SHALL apply a 5-point bonus for long trades
2. WHEN funding rate is extremely positive (above 0.1%) THEN the System SHALL apply a 5-point bonus for short trades
3. WHEN BTC correlation is high and BTC is volatile THEN the System SHALL reduce position size by 20%
4. WHEN the asset shows low BTC correlation THEN the System SHALL allow full position sizing
