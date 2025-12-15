# Requirements Document

## Introduction

Kinetic Empire v3.0 is a professional-grade modular cryptocurrency futures trading system designed for consistent profitability on Binance Futures. The system employs a three-module architecture: Market Scanner (opportunity discovery), Technical Analyzer (multi-timeframe scoring), and Position Manager (risk-adjusted execution with dynamic leverage). The system targets high-probability trades with confidence-based position sizing and leverage scaling from 2x to 20x.

## Glossary

- **Market_Scanner**: Module that continuously monitors all tradeable pairs (USDT and USDC markets) to identify high-potential opportunities based on volume, momentum, and market structure
- **TA_Analyzer**: Technical Analysis module that performs multi-timeframe analysis using EMA, RSI, MACD, ATR, and volume indicators to score opportunities
- **Position_Manager**: Module responsible for position lifecycle including entry, stop loss, trailing stops, take profit, and dynamic leverage management
- **Signal**: A trading recommendation with direction (LONG/SHORT), entry price, stop loss, take profit, and confidence score
- **Confidence_Score**: A 0-100 score indicating signal strength based on multi-timeframe indicator alignment
- **Dynamic_Leverage**: Leverage that scales from 2x to 20x based on confidence score and market conditions
- **ATR**: Average True Range - volatility indicator used for dynamic stop loss calculation
- **MTF**: Multi-Timeframe Analysis - analyzing the same asset across 4H, 1H, 15M timeframes

## Requirements

### Requirement 1

**User Story:** As a trader, I want the system to automatically scan the market for high-potential trading opportunities, so that I can focus on the best setups without manual screening.

#### Acceptance Criteria

1. WHEN the Market_Scanner runs THEN the system SHALL fetch ticker data for all configured trading pairs (both USDT and USDC pairs) within 5 seconds
2. WHEN analyzing tickers THEN the Market_Scanner SHALL filter pairs by volume spike (greater than 1.5x 20-period average)
3. WHEN analyzing tickers THEN the Market_Scanner SHALL filter pairs by 24-hour price momentum (absolute change greater than 1%)
4. WHEN the Market_Scanner identifies hot tickers THEN the system SHALL pass them to the TA_Analyzer for detailed analysis
5. WHEN the Market_Scanner completes a scan cycle THEN the system SHALL log the number of opportunities found and their symbols

### Requirement 2

**User Story:** As a trader, I want multi-timeframe technical analysis on opportunities, so that I can trade with the trend across multiple timeframes.

#### Acceptance Criteria

1. WHEN the TA_Analyzer receives a ticker THEN the system SHALL fetch OHLCV data for 4H, 1H, and 15M timeframes
2. WHEN calculating indicators THEN the TA_Analyzer SHALL compute EMA(9), EMA(21), RSI(14), MACD(12,26,9), and ATR(14) for each timeframe
3. WHEN the 4H EMA(9) is above EMA(21) THEN the TA_Analyzer SHALL assign 25 points to the long score
4. WHEN the 4H EMA(9) is below EMA(21) THEN the TA_Analyzer SHALL assign 25 points to the short score
5. WHEN the 1H trend direction matches the 4H trend direction THEN the TA_Analyzer SHALL add 20 points to the directional score
6. WHEN RSI(14) is between 30-45 in an uptrend THEN the TA_Analyzer SHALL add 15 points for optimal long entry zone
7. WHEN RSI(14) is between 55-70 in a downtrend THEN the TA_Analyzer SHALL add 15 points for optimal short entry zone
8. WHEN MACD line crosses above signal line THEN the TA_Analyzer SHALL add 15 points to long score
9. WHEN MACD line crosses below signal line THEN the TA_Analyzer SHALL add 15 points to short score
10. WHEN recent volume exceeds 1.5x average volume THEN the TA_Analyzer SHALL add 10 points to the score
11. WHEN the TA_Analyzer completes analysis THEN the system SHALL output a Signal with direction, score, entry, stop_loss, and take_profit

### Requirement 3

**User Story:** As a trader, I want the system to calculate optimal stop loss and take profit levels based on market volatility, so that my risk is properly calibrated to current conditions.

#### Acceptance Criteria

1. WHEN generating a Signal THEN the TA_Analyzer SHALL calculate stop loss as entry price minus 2x ATR(14) for long positions
2. WHEN generating a Signal THEN the TA_Analyzer SHALL calculate stop loss as entry price plus 2x ATR(14) for short positions
3. WHEN the calculated stop loss exceeds 3% from entry THEN the system SHALL cap the stop loss at 3% distance
4. WHEN generating a Signal THEN the TA_Analyzer SHALL calculate take profit at 1.5x the risk distance (risk-reward 1:1.5)
5. WHEN generating a Signal THEN the TA_Analyzer SHALL include ATR value for trailing stop calculations

### Requirement 4

**User Story:** As a trader, I want dynamic leverage scaling based on signal confidence, so that I can maximize gains on high-confidence trades while protecting capital on lower-confidence setups.

#### Acceptance Criteria

1. WHEN a Signal has confidence score 60-69 THEN the Position_Manager SHALL use 5x leverage
2. WHEN a Signal has confidence score 70-79 THEN the Position_Manager SHALL use 10x leverage
3. WHEN a Signal has confidence score 80-89 THEN the Position_Manager SHALL use 15x leverage
4. WHEN a Signal has confidence score 90-100 THEN the Position_Manager SHALL use 20x leverage
5. WHEN a Signal has confidence score below 60 THEN the Position_Manager SHALL reject the trade
6. WHEN market volatility (ATR) is above 2x normal THEN the Position_Manager SHALL reduce leverage by 50%

### Requirement 5

**User Story:** As a trader, I want dynamic position sizing based on confidence and account risk, so that I risk more on better setups while maintaining overall portfolio safety.

#### Acceptance Criteria

1. WHEN calculating position size THEN the Position_Manager SHALL risk maximum 1% of account equity per trade at base level
2. WHEN a Signal has confidence score 80+ THEN the Position_Manager SHALL increase risk to 1.5% of account equity
3. WHEN a Signal has confidence score 90+ THEN the Position_Manager SHALL increase risk to 2% of account equity
4. WHEN calculating position size THEN the system SHALL use the formula: size = (equity × risk%) / (entry × stop_distance%)
5. WHEN the calculated position would exceed 25% of account equity THEN the system SHALL cap position size at 25%

### Requirement 6

**User Story:** As a trader, I want the system to manage positions with trailing stops and partial take profits, so that I can lock in gains while letting winners run.

#### Acceptance Criteria

1. WHEN a position reaches 1.5% profit THEN the Position_Manager SHALL close 40% of the position
2. WHEN a position reaches 2.5% profit THEN the Position_Manager SHALL close an additional 30% of the position
3. WHEN a position reaches 1.5% profit THEN the Position_Manager SHALL activate trailing stop at 1x ATR distance
4. WHEN trailing stop is active and profit increases THEN the Position_Manager SHALL move the stop to lock minimum 0.5% profit
5. WHEN a position reaches 3% profit THEN the Position_Manager SHALL tighten trailing stop to 0.5x ATR distance
6. WHEN trailing stop is triggered THEN the Position_Manager SHALL close remaining position and log the trade result

### Requirement 7

**User Story:** As a trader, I want pre-trade risk checks to prevent overexposure, so that no single trade or correlated group of trades can blow up my account.

#### Acceptance Criteria

1. WHEN attempting to open a new position THEN the Position_Manager SHALL verify total open positions is less than 12
2. WHEN attempting to open a new position THEN the Position_Manager SHALL verify margin usage is below 90%
3. WHEN attempting to open a new position THEN the Position_Manager SHALL verify daily realized loss is below 5% of starting equity
4. WHEN attempting to open a position in a correlated asset THEN the Position_Manager SHALL verify less than 3 correlated positions exist
5. IF any pre-trade check fails THEN the Position_Manager SHALL reject the trade and log the reason

### Requirement 8

**User Story:** As a trader, I want emergency risk controls to protect against catastrophic losses, so that the system can survive black swan events.

#### Acceptance Criteria

1. WHEN total portfolio unrealized loss exceeds 5% THEN the Position_Manager SHALL close all positions immediately
2. WHEN any single position loss exceeds 4% THEN the Position_Manager SHALL force close that position
3. WHEN margin usage exceeds 90% THEN the Position_Manager SHALL close the worst-performing position
4. WHEN daily loss limit is hit THEN the system SHALL pause trading until the next day
5. WHEN an emergency action is taken THEN the system SHALL send an alert notification

### Requirement 9

**User Story:** As a trader, I want the system to run with minimal latency, so that I can capture opportunities before they disappear.

#### Acceptance Criteria

1. WHEN the Position_Manager monitors positions THEN the system SHALL check all positions every 5 seconds
2. WHEN the Market_Scanner runs THEN the system SHALL complete a full scan within 10 seconds
3. WHEN a stop loss or take profit is triggered THEN the system SHALL execute the order within 1 second
4. WHEN fetching market data THEN the system SHALL use WebSocket connections for real-time price updates
5. WHEN multiple modules need to communicate THEN the system SHALL use async message passing with no blocking

### Requirement 10

**User Story:** As a trader, I want comprehensive logging and performance metrics, so that I can analyze and improve the system over time.

#### Acceptance Criteria

1. WHEN a trade is executed THEN the system SHALL log entry price, size, leverage, confidence score, and signal details
2. WHEN a trade is closed THEN the system SHALL log exit price, P&L percentage, P&L amount, and exit reason
3. WHEN the system runs THEN it SHALL track win rate, average win, average loss, and profit factor
4. WHEN requested THEN the system SHALL display current positions with real-time P&L
5. WHEN the system starts THEN it SHALL log configuration settings and initial account state
