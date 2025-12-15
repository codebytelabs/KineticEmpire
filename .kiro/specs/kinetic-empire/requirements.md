# Requirements Document

## Introduction

Kinetic Empire is an automated high-frequency cryptocurrency trading system built on the Freqtrade framework. The system is designed to capitalize on high-velocity crypto assets while prioritizing capital preservation through regime-aware trading (adjusting exposure based on macro BTC trends) and self-optimizing position sizing (Kelly Criterion based on historical win rates). The bot targets a >60% win rate in bull regimes, <15% max drawdown, and >2.0 Sharpe ratio with 99.9% uptime.

## Glossary

- **Freqtrade**: Open-source Python trading bot framework for cryptocurrency trading
- **CCXT**: CryptoCurrency eXchange Trading Library - unified API for multiple exchanges
- **Regime Filter**: Market condition classifier based on BTC price relative to EMA50
- **Kelly Criterion**: Mathematical formula for optimal bet sizing based on win probability
- **ATR (Average True Range)**: Volatility indicator measuring price movement range
- **EMA (Exponential Moving Average)**: Trend-following indicator giving more weight to recent prices
- **ROC (Rate of Change)**: Momentum indicator measuring percentage price change
- **RSI (Relative Strength Index)**: Momentum oscillator measuring overbought/oversold conditions
- **Whitelist**: Dynamic list of tradeable asset pairs selected by the scanner
- **Drawdown**: Peak-to-trough decline in portfolio value
- **Sharpe Ratio**: Risk-adjusted return metric (return minus risk-free rate divided by volatility)
- **Trailing Stop**: Dynamic stop-loss that follows price movement to lock in profits

## Requirements

### Requirement 1: Dynamic Pairlist Scanner

**User Story:** As a trader, I want the system to automatically discover and filter high-quality trading pairs, so that I only trade assets with optimal volatility and liquidity characteristics.

#### Acceptance Criteria

1. WHEN the scanner refresh interval (30 minutes) elapses THEN the Scanner Module SHALL retrieve the top 70 coins by USDT quote volume from the exchange
2. WHEN filtering trading pairs THEN the Scanner Module SHALL exclude all blacklisted pairs (stablecoins, leverage tokens matching patterns BNB/.*, .*DOWN/.*, .*UP/.*, USDC/.*)
3. WHEN evaluating pair quality THEN the Scanner Module SHALL reject pairs with spread ratio exceeding 0.005 (0.5%)
4. WHEN evaluating pair quality THEN the Scanner Module SHALL reject pairs with price below $0.001
5. WHEN evaluating volatility THEN the Scanner Module SHALL accept pairs with volatility between 0.02 and 0.50
6. WHEN evaluating recent performance THEN the Scanner Module SHALL accept pairs with positive returns (>0%) in the last 60 minutes
7. WHEN the filter pipeline completes THEN the Scanner Module SHALL sort remaining pairs by volatility (high to low) and retain the top 20 pairs

### Requirement 2: Technical Indicator Calculation

**User Story:** As a trader, I want the system to calculate accurate technical indicators on multiple timeframes, so that trading signals are based on reliable market data.

#### Acceptance Criteria

1. WHEN processing market data THEN the Indicator Module SHALL calculate EMA_50 on both 5-minute and 1-hour timeframes
2. WHEN processing market data THEN the Indicator Module SHALL calculate ROC_12 (12-period Rate of Change) for momentum measurement
3. WHEN processing market data THEN the Indicator Module SHALL calculate RSI_14 (14-period Relative Strength Index)
4. WHEN processing market data THEN the Indicator Module SHALL calculate ATR_14 (14-period Average True Range) for volatility measurement
5. WHEN merging timeframe data THEN the Indicator Module SHALL align 1-hour and daily informative data with the 5-minute primary dataframe
6. WHEN indicator calculation completes THEN the Indicator Module SHALL store computed values in the dataframe for signal generation

### Requirement 3: Entry Signal Generation

**User Story:** As a trader, I want the system to generate buy signals based on multi-timeframe trend alignment and momentum conditions, so that entries occur during high-probability setups.

#### Acceptance Criteria

1. WHEN evaluating entry conditions THEN the Strategy Engine SHALL require 1-hour close price above 1-hour EMA_50 (macro trend confirmation)
2. WHEN evaluating entry conditions THEN the Strategy Engine SHALL require 5-minute close price above 5-minute EMA_50 (micro trend confirmation)
3. WHEN evaluating momentum THEN the Strategy Engine SHALL require ROC_12 greater than 1.5% (velocity threshold)
4. WHEN evaluating pullback conditions THEN the Strategy Engine SHALL require RSI_14 between 45 and 65 (avoiding overbought/oversold)
5. WHEN evaluating volume THEN the Strategy Engine SHALL require current volume exceeding the 24-hour mean volume
6. WHEN all entry conditions are satisfied THEN the Strategy Engine SHALL generate a BUY signal for the pair

### Requirement 4: Regime-Based Risk Management

**User Story:** As a trader, I want the system to adjust position limits based on Bitcoin market regime, so that exposure is reduced during bearish conditions.

#### Acceptance Criteria

1. WHEN determining market regime THEN the Risk Module SHALL classify regime as BULL when BTC/USDT daily close exceeds daily EMA_50
2. WHEN determining market regime THEN the Risk Module SHALL classify regime as BEAR when BTC/USDT daily close falls below daily EMA_50
3. WHILE regime is BULL THEN the Risk Module SHALL permit a maximum of 20 concurrent open trades
4. WHILE regime is BEAR THEN the Risk Module SHALL permit a maximum of 3 concurrent open trades
5. WHEN a new trade signal is generated THEN the Risk Module SHALL reject the signal if current open trades equal or exceed the regime-based limit

### Requirement 5: Kelly Criterion Position Sizing

**User Story:** As a trader, I want the system to dynamically size positions based on historical performance per asset, so that winning pairs receive larger allocations.

#### Acceptance Criteria

1. WHEN calculating stake amount THEN the Sizing Module SHALL query the last 20 closed trades for the specific pair
2. WHEN fewer than 10 closed trades exist for a pair THEN the Sizing Module SHALL apply a conservative default stake of 1% of available balance
3. WHEN 10 or more closed trades exist THEN the Sizing Module SHALL calculate win rate as (winning trades / total trades)
4. WHEN applying Kelly Criterion THEN the Sizing Module SHALL calculate stake percentage using formula: (win_rate - (1 - win_rate) / reward_risk_ratio)
5. WHEN stake percentage is calculated THEN the Sizing Module SHALL clamp the value between 0.5% minimum and 5.0% maximum of available balance

### Requirement 6: Dynamic Stop Loss Management

**User Story:** As a trader, I want the system to set volatility-adjusted stop losses, so that positions have appropriate risk protection based on current market conditions.

#### Acceptance Criteria

1. WHEN a new position is opened THEN the Stop Loss Module SHALL calculate initial stop loss as entry_price minus (2.0 multiplied by ATR_14)
2. WHEN stop loss is calculated THEN the Stop Loss Module SHALL place the stop loss order on the exchange (stoploss_on_exchange: true)
3. IF the exchange API becomes unavailable THEN the Stop Loss Module SHALL maintain the on-exchange stop loss order to protect the position

### Requirement 7: Trailing Stop Profit Protection

**User Story:** As a trader, I want the system to implement trailing stops on profitable positions, so that gains are protected while allowing winners to run.

#### Acceptance Criteria

1. WHEN unrealized profit exceeds 2.5% THEN the Trailing Stop Module SHALL activate trailing stop mode for the position
2. WHEN trailing stop is active THEN the Trailing Stop Module SHALL calculate new stop level as current_price minus (1.5 multiplied by ATR_14)
3. WHEN new trailing stop level exceeds previous stop level THEN the Trailing Stop Module SHALL update the stop order on the exchange
4. WHEN trailing stop level would decrease THEN the Trailing Stop Module SHALL maintain the existing higher stop level

### Requirement 8: Exit Signal Generation

**User Story:** As a trader, I want the system to generate sell signals when trend conditions deteriorate, so that positions are closed before significant losses occur.

#### Acceptance Criteria

1. WHEN monitoring open positions THEN the Exit Module SHALL check if 5-minute close falls below 5-minute EMA_50
2. WHEN price breaks below EMA_50 THEN the Exit Module SHALL confirm with volume exceeding 24-hour mean
3. WHEN trend break is confirmed with volume THEN the Exit Module SHALL generate a SELL signal (trend break exit)
4. WHEN hard stop loss price is reached THEN the Exit Module SHALL execute market sell order immediately

### Requirement 9: Exchange Integration

**User Story:** As a trader, I want the system to reliably communicate with Binance Futures API, so that orders are executed accurately and market data is current.

#### Acceptance Criteria

1. WHEN connecting to exchange THEN the Exchange Module SHALL authenticate using API key and secret from configuration
2. WHEN fetching market data THEN the Exchange Module SHALL enable rate limiting (200ms between requests) to avoid API bans
3. WHEN placing orders THEN the Exchange Module SHALL use limit orders for entry and exit, market orders for emergency exit and stop loss
4. WHEN order remains unfilled THEN the Exchange Module SHALL cancel entry orders after 10 minutes and exit orders after 30 minutes
5. IF exchange API returns 5xx errors for more than 5 minutes THEN the Exchange Module SHALL enter FailSafe mode and halt new signal processing

### Requirement 10: Trade Persistence and History

**User Story:** As a trader, I want the system to persist all trade data, so that historical performance can be analyzed and Kelly Criterion calculations are accurate.

#### Acceptance Criteria

1. WHEN a trade is opened THEN the Persistence Module SHALL store entry timestamp, pair, entry price, stake amount, and regime classification
2. WHEN a trade is closed THEN the Persistence Module SHALL store exit timestamp, exit price, profit/loss amount, and exit reason
3. WHEN querying trade history THEN the Persistence Module SHALL return trades filtered by pair, date range, or outcome
4. WHEN serializing trade data THEN the Persistence Module SHALL encode records using JSON format for storage

### Requirement 11: Telegram Notifications and Control

**User Story:** As a trader, I want to receive alerts and control the bot via Telegram, so that I can monitor performance and intervene remotely.

#### Acceptance Criteria

1. WHEN a trade is executed THEN the Notification Module SHALL send a Telegram message with pair, direction, price, and stake amount
2. WHEN the /status command is received THEN the Notification Module SHALL respond with current open trades and unrealized P&L
3. WHEN the /profit command is received THEN the Notification Module SHALL respond with daily realized profit/loss summary
4. WHEN the /stop command is received THEN the Control Module SHALL halt all new signal processing (emergency kill switch)

### Requirement 12: Configuration Management

**User Story:** As a trader, I want to configure bot parameters through a JSON file, so that strategy settings can be adjusted without code changes.

#### Acceptance Criteria

1. WHEN the bot starts THEN the Configuration Module SHALL load parameters from config.json file
2. WHEN parsing configuration THEN the Configuration Module SHALL validate all required fields are present (exchange credentials, stake currency, max trades)
3. IF configuration validation fails THEN the Configuration Module SHALL log specific error and prevent bot startup
4. WHEN configuration is loaded THEN the Configuration Module SHALL apply pair blacklist patterns to the scanner

### Requirement 13: Backtesting Support

**User Story:** As a trader, I want to backtest strategies on historical data, so that I can validate performance before live deployment.

#### Acceptance Criteria

1. WHEN backtesting mode is enabled THEN the Backtest Module SHALL load historical OHLCV data for specified date range
2. WHEN simulating trades THEN the Backtest Module SHALL apply realistic slippage and fee calculations
3. WHEN backtest completes THEN the Backtest Module SHALL generate performance report with win rate, Sharpe ratio, max drawdown, and total return
4. WHEN comparing strategies THEN the Backtest Module SHALL output trade-by-trade results for analysis

### Requirement 14: Flash Crash Protection

**User Story:** As a trader, I want the system to detect and respond to flash crashes, so that catastrophic losses are prevented during extreme volatility.

#### Acceptance Criteria

1. WHEN BTC price drops more than 5% within 1 hour THEN the Protection Module SHALL immediately reduce max trades to 3 regardless of current regime
2. WHEN flash crash is detected THEN the Protection Module SHALL halt all new BUY signal processing
3. WHEN market stabilizes (BTC above EMA_50 for 4 consecutive hours) THEN the Protection Module SHALL restore normal regime-based limits
