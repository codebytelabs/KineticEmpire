# Requirements Document

## Introduction

The Wave Rider Upgrade transforms the Kinetic Empire trading bot from a conservative trend-follower into an active momentum scalper. The current bot waits for perfect TRENDING market conditions (ADX > 25) and only scans 10 fixed symbols, resulting in very low trading activity. The Wave Rider system actively scans ALL futures pairs to find coins with volume spikes and momentum, enters both LONG and SHORT positions based on multi-timeframe analysis, and rides price waves with proper risk management.

## Glossary

- **Wave_Rider_System**: The upgraded trading bot that actively scans for momentum opportunities across all futures pairs
- **Momentum_Scanner**: Component that fetches all futures tickers and ranks them by momentum score
- **Volume_Spike**: A condition where current volume exceeds the 20-period average volume by a configurable multiplier (default 2x)
- **Momentum_Score**: A composite score calculated as volume_ratio × abs(price_change_pct) used to rank trading opportunities
- **MTF_Analyzer**: Multi-Timeframe Analyzer that evaluates trend alignment across 1m, 5m, and 15m timeframes
- **Timeframe_Alignment**: The degree to which multiple timeframes agree on trend direction (bullish/bearish)
- **Top_Movers**: The highest-ranked symbols by momentum score after filtering (default top 20)
- **Entry_Signal**: A trading signal generated when volume spike, momentum, and timeframe alignment criteria are met
- **VWAP**: Volume Weighted Average Price, used as a dynamic support/resistance level

## Requirements

### Requirement 1: Dynamic Symbol Discovery

**User Story:** As a trader, I want the bot to scan ALL available futures pairs instead of a fixed list, so that I can capture momentum opportunities on any coin that is moving.

#### Acceptance Criteria

1. WHEN the Momentum_Scanner runs THEN the Wave_Rider_System SHALL fetch ticker data for all USDT-margined futures pairs from Binance
2. WHEN ticker data is fetched THEN the Wave_Rider_System SHALL calculate volume_ratio as current_volume divided by 20-period average volume for each symbol
3. WHEN ticker data is fetched THEN the Wave_Rider_System SHALL calculate price_change_pct as the percentage price change over the last 5 minutes for each symbol
4. WHEN momentum scores are calculated THEN the Wave_Rider_System SHALL compute momentum_score as volume_ratio multiplied by absolute value of price_change_pct
5. WHEN ranking symbols THEN the Wave_Rider_System SHALL return the top 20 symbols sorted by momentum_score in descending order
6. WHEN filtering symbols THEN the Wave_Rider_System SHALL exclude symbols with 24h volume below 10 million USD

### Requirement 2: Volume Spike Detection

**User Story:** As a trader, I want the bot to detect volume spikes in real-time, so that I can enter positions when there is significant market interest.

#### Acceptance Criteria

1. WHEN calculating volume_ratio THEN the Wave_Rider_System SHALL use a rolling 20-period average as the baseline
2. WHEN volume_ratio exceeds 2.0 THEN the Wave_Rider_System SHALL flag the symbol as having a volume spike
3. WHEN volume_ratio exceeds 3.0 THEN the Wave_Rider_System SHALL classify the spike as "strong"
4. WHEN volume_ratio exceeds 5.0 THEN the Wave_Rider_System SHALL classify the spike as "extreme"
5. WHEN a volume spike is detected THEN the Wave_Rider_System SHALL log the spike classification and ratio value

### Requirement 3: Multi-Timeframe Analysis

**User Story:** As a trader, I want the bot to analyze multiple timeframes before entering a trade, so that I can ensure the momentum is confirmed across different time horizons.

#### Acceptance Criteria

1. WHEN analyzing a top mover THEN the MTF_Analyzer SHALL fetch OHLCV data for 1m, 5m, and 15m timeframes
2. WHEN analyzing each timeframe THEN the MTF_Analyzer SHALL calculate EMA_fast (9-period) and EMA_slow (21-period)
3. WHEN analyzing each timeframe THEN the MTF_Analyzer SHALL calculate RSI with 14-period lookback
4. WHEN analyzing each timeframe THEN the MTF_Analyzer SHALL determine trend direction as BULLISH if EMA_fast is greater than EMA_slow and price is above both EMAs
5. WHEN analyzing each timeframe THEN the MTF_Analyzer SHALL determine trend direction as BEARISH if EMA_fast is less than EMA_slow and price is below both EMAs
6. WHEN analyzing each timeframe THEN the MTF_Analyzer SHALL determine trend direction as NEUTRAL if neither bullish nor bearish conditions are met
7. WHEN calculating alignment score THEN the MTF_Analyzer SHALL assign 100 points if all 3 timeframes agree on direction
8. WHEN calculating alignment score THEN the MTF_Analyzer SHALL assign 70 points if 2 of 3 timeframes agree on direction
9. WHEN calculating alignment score THEN the MTF_Analyzer SHALL assign 40 points if only 1 timeframe shows direction

### Requirement 4: Entry Signal Generation

**User Story:** As a trader, I want the bot to generate entry signals based on volume spikes and timeframe alignment, so that I can enter high-probability momentum trades.

#### Acceptance Criteria

1. WHEN evaluating entry conditions THEN the Wave_Rider_System SHALL require volume_ratio of at least 2.0
2. WHEN evaluating entry conditions THEN the Wave_Rider_System SHALL require alignment_score of at least 70 (2/3 timeframes aligned)
3. WHEN evaluating entry conditions THEN the Wave_Rider_System SHALL require RSI between 25 and 75 on the 1m timeframe
4. WHEN evaluating entry conditions THEN the Wave_Rider_System SHALL check that the symbol is not blacklisted
5. WHEN evaluating entry conditions THEN the Wave_Rider_System SHALL check that total portfolio exposure is below 45%
6. WHEN generating a LONG signal THEN the Wave_Rider_System SHALL require price above VWAP and majority timeframes showing BULLISH
7. WHEN generating a SHORT signal THEN the Wave_Rider_System SHALL require price below VWAP and majority timeframes showing BEARISH
8. WHEN a signal is generated THEN the Wave_Rider_System SHALL calculate position size based on confidence tier (5-15% of portfolio)

### Requirement 5: Position Sizing and Leverage

**User Story:** As a trader, I want position sizes and leverage to scale with signal strength, so that I can maximize returns on high-conviction trades while limiting risk on weaker signals.

#### Acceptance Criteria

1. WHEN volume_ratio is between 2.0 and 3.0 THEN the Wave_Rider_System SHALL use 5% position size and 3x leverage
2. WHEN volume_ratio is between 3.0 and 5.0 THEN the Wave_Rider_System SHALL use 7% position size and 5x leverage
3. WHEN volume_ratio exceeds 5.0 THEN the Wave_Rider_System SHALL use 10% position size and 7x leverage
4. WHEN alignment_score is 100 THEN the Wave_Rider_System SHALL increase leverage by 1x (up to maximum 10x)
5. WHEN consecutive losses exceed 2 THEN the Wave_Rider_System SHALL reduce position size by 50%
6. WHEN total exposure would exceed 45% THEN the Wave_Rider_System SHALL reduce position size to fit within the limit

### Requirement 6: Stop Loss Management

**User Story:** As a trader, I want ATR-based stop losses that adapt to market volatility, so that I can protect capital while giving trades room to breathe.

#### Acceptance Criteria

1. WHEN opening a position THEN the Wave_Rider_System SHALL calculate initial stop loss at 1.5x ATR from entry price
2. WHEN ATR-based stop would be less than 0.5% THEN the Wave_Rider_System SHALL use 0.5% as minimum stop distance
3. WHEN ATR-based stop would exceed 3% THEN the Wave_Rider_System SHALL use 3% as maximum stop distance
4. WHEN a LONG position is opened THEN the Wave_Rider_System SHALL place stop loss below entry price
5. WHEN a SHORT position is opened THEN the Wave_Rider_System SHALL place stop loss above entry price
6. WHEN stop loss is hit THEN the Wave_Rider_System SHALL close the entire position and record a loss

### Requirement 7: Trailing Stop and Profit Locking

**User Story:** As a trader, I want trailing stops that lock in profits as the trade moves in my favor, so that I can ride winning trades while protecting gains.

#### Acceptance Criteria

1. WHEN unrealized profit reaches 1.0% THEN the Wave_Rider_System SHALL activate trailing stop mode
2. WHEN trailing stop is active THEN the Wave_Rider_System SHALL trail at 0.8x ATR from the peak price
3. WHEN unrealized profit reaches 1.5% THEN the Wave_Rider_System SHALL close 30% of the position (TP1)
4. WHEN unrealized profit reaches 2.5% THEN the Wave_Rider_System SHALL close another 30% of the position (TP2)
5. WHEN unrealized profit exceeds 3% THEN the Wave_Rider_System SHALL tighten trailing stop to 0.5x ATR
6. WHEN trailing stop is triggered THEN the Wave_Rider_System SHALL close remaining position and record profit

### Requirement 8: Scan Cycle Speed

**User Story:** As a trader, I want the bot to scan the market frequently, so that I can capture fast-moving momentum opportunities.

#### Acceptance Criteria

1. WHEN the bot is running THEN the Wave_Rider_System SHALL execute a full market scan every 15 seconds
2. WHEN monitoring open positions THEN the Wave_Rider_System SHALL check exit conditions every 5 seconds
3. WHEN API rate limits are approached THEN the Wave_Rider_System SHALL implement exponential backoff
4. WHEN a scan cycle takes longer than 15 seconds THEN the Wave_Rider_System SHALL log a warning and skip to the next cycle

### Requirement 9: Risk Management

**User Story:** As a trader, I want comprehensive risk controls to protect my capital, so that I can trade aggressively while limiting downside.

#### Acceptance Criteria

1. WHEN daily realized loss exceeds 3% of starting balance THEN the Wave_Rider_System SHALL halt all new trades for the day
2. WHEN a symbol has 2 consecutive losses THEN the Wave_Rider_System SHALL blacklist it for 30 minutes
3. WHEN total open positions reach 5 THEN the Wave_Rider_System SHALL stop opening new positions
4. WHEN a single position loss exceeds 2% of portfolio THEN the Wave_Rider_System SHALL force close the position
5. WHEN the bot restarts THEN the Wave_Rider_System SHALL load existing positions and resume monitoring

### Requirement 10: Logging and Monitoring

**User Story:** As a trader, I want detailed logging of all bot activities, so that I can monitor performance and debug issues.

#### Acceptance Criteria

1. WHEN a market scan completes THEN the Wave_Rider_System SHALL log the top 5 movers with their momentum scores
2. WHEN an entry signal is generated THEN the Wave_Rider_System SHALL log symbol, direction, volume_ratio, alignment_score, position_size, and leverage
3. WHEN a position is opened THEN the Wave_Rider_System SHALL log entry price, stop loss, and take profit levels
4. WHEN a position is closed THEN the Wave_Rider_System SHALL log exit price, PnL percentage, PnL USD, and exit reason
5. WHEN the circuit breaker activates THEN the Wave_Rider_System SHALL log the trigger reason and remaining cooldown time
