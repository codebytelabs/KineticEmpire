# Requirements Document

## Introduction

This specification defines a set of high-confidence, low-risk optimizations to the Kinetic Empire trading bot. These improvements are designed to enhance profitability and risk management without breaking existing functionality. Each optimization has been carefully analyzed to ensure it adds value without overfitting or degrading current performance.

The improvements are prioritized by impact-to-effort ratio and grouped into three tiers:
- **Tier 1 (Critical):** Immediate profit protection and risk reduction
- **Tier 2 (High Value):** Entry/exit optimization for better win rate
- **Tier 3 (Enhancement):** Additional edge improvements

## Glossary

- **ATR (Average True Range):** Volatility indicator measuring price movement range
- **RSI (Relative Strength Index):** Momentum oscillator measuring overbought/oversold conditions
- **Kelly Criterion:** Mathematical formula for optimal position sizing based on win rate
- **Trailing Stop:** Dynamic stop loss that follows price movement to lock in profits
- **F&G Index:** Fear & Greed Index measuring market sentiment (0-100)
- **Half-Kelly:** Conservative position sizing using 50% of Kelly fraction
- **TP1/TP2:** Take Profit levels for partial position exits
- **Regime:** Market condition classification (BULL, BEAR, TRENDING, SIDEWAYS, CHOPPY)

## Requirements

### Requirement 1: Trailing Stop Standardization

**User Story:** As a trader, I want consistent trailing stop activation across all modules, so that I lock in profits earlier and reduce profit giveback.

#### Acceptance Criteria

1. WHEN a position reaches 1.5% unrealized profit THEN the Trading_System SHALL activate trailing stop protection
2. WHEN trailing stop is activated THEN the Trading_System SHALL trail at 1.5x ATR from peak price
3. WHEN profit exceeds 3% THEN the Trading_System SHALL tighten trailing to 1.0x ATR from peak price
4. WHEN trailing stop configuration is updated THEN the Trading_System SHALL apply changes to all modules (base, wave_rider, profitable_trading)

### Requirement 2: Partial Profit Taking (TP1/TP2)

**User Story:** As a trader, I want to take partial profits at predetermined levels, so that I secure gains while letting winners run.

#### Acceptance Criteria

1. WHEN position profit reaches 1.5x ATR THEN the Trading_System SHALL close 25% of position (TP1)
2. WHEN position profit reaches 2.5x ATR THEN the Trading_System SHALL close an additional 25% of position (TP2)
3. WHEN TP1 or TP2 triggers THEN the Trading_System SHALL log the partial exit with profit amount
4. WHEN remaining 50% position is active THEN the Trading_System SHALL manage it with trailing stop only

### Requirement 3: Half-Kelly Position Sizing

**User Story:** As a trader, I want more conservative position sizing, so that I reduce variance while maintaining edge.

#### Acceptance Criteria

1. WHEN calculating Kelly fraction THEN the Kelly_Sizer SHALL multiply result by 0.5 (Half-Kelly)
2. WHEN Half-Kelly result is below minimum stake THEN the Kelly_Sizer SHALL use minimum stake percentage
3. WHEN Half-Kelly result exceeds maximum stake THEN the Kelly_Sizer SHALL cap at maximum stake percentage
4. WHEN insufficient trade history exists THEN the Kelly_Sizer SHALL use conservative default stake

### Requirement 4: Volume-Tiered Position Sizing

**User Story:** As a trader, I want position sizes adjusted by volume confirmation strength, so that I allocate more capital to high-conviction setups.

#### Acceptance Criteria

1. WHEN volume ratio is 1.0-1.5x average THEN the Position_Sizer SHALL use standard position size (1.0x multiplier)
2. WHEN volume ratio is 1.5-2.5x average THEN the Position_Sizer SHALL increase position size by 10% (1.1x multiplier)
3. WHEN volume ratio exceeds 2.5x average THEN the Position_Sizer SHALL increase position size by 20% (1.2x multiplier)
4. WHEN volume ratio is below 1.0x average THEN the Position_Sizer SHALL reduce position size by 20% (0.8x multiplier)

### Requirement 5: Regime-Adaptive ATR Stop Loss

**User Story:** As a trader, I want stop loss distances adjusted by market regime, so that I avoid whipsaws in volatile markets and capture more profit in trending markets.

#### Acceptance Criteria

1. WHEN regime is BULL and TRENDING THEN the Stop_Loss_Manager SHALL use 1.5x ATR multiplier
2. WHEN regime is BULL and SIDEWAYS THEN the Stop_Loss_Manager SHALL use 2.0x ATR multiplier
3. WHEN regime is BEAR THEN the Stop_Loss_Manager SHALL use 2.5x ATR multiplier
4. WHEN regime changes THEN the Stop_Loss_Manager SHALL NOT modify existing position stops (only new positions)

### Requirement 6: RSI Zone Optimization

**User Story:** As a trader, I want optimized RSI entry zones by regime, so that I catch more quality pullback entries without chasing.

#### Acceptance Criteria

1. WHEN regime is BULL THEN the Entry_Generator SHALL accept RSI range 35-70 for entry
2. WHEN regime is BEAR THEN the Entry_Generator SHALL accept RSI range 45-60 for entry (conservative)
3. WHEN RSI is outside acceptable range THEN the Entry_Generator SHALL reject the entry signal
4. WHEN RSI zone configuration changes THEN the Entry_Generator SHALL apply to new signals only

### Requirement 7: Dynamic Blacklist Duration

**User Story:** As a trader, I want blacklist duration scaled by loss severity, so that small losses don't block good opportunities while large losses trigger appropriate cooldown.

#### Acceptance Criteria

1. WHEN stop loss triggers with loss less than 1% THEN the Blacklist_Manager SHALL blacklist symbol for 15 minutes
2. WHEN stop loss triggers with loss between 1-2% THEN the Blacklist_Manager SHALL blacklist symbol for 30 minutes
3. WHEN stop loss triggers with loss greater than 2% THEN the Blacklist_Manager SHALL blacklist symbol for 60 minutes
4. WHEN blacklist expires THEN the Blacklist_Manager SHALL allow new entries for that symbol

### Requirement 8: Fear & Greed Integration Enhancement

**User Story:** As a trader, I want position sizing and trailing stops adjusted by market sentiment extremes, so that I'm more cautious at market extremes.

#### Acceptance Criteria

1. WHEN Fear & Greed Index is below 25 (Extreme Fear) THEN the Position_Sizer SHALL reduce position sizes by 30%
2. WHEN Fear & Greed Index is above 75 (Extreme Greed) THEN the Trailing_Stop_Manager SHALL use tighter 1.0x ATR trail
3. WHEN Fear & Greed Index is between 25-75 THEN the Trading_System SHALL use standard parameters
4. WHEN Fear & Greed data is unavailable THEN the Trading_System SHALL use standard parameters (no adjustment)

### Requirement 9: Micro-Timeframe Alignment Bonus

**User Story:** As a trader, I want to reward high-quality setups where micro-timeframes align, so that I allocate more to the best opportunities.

#### Acceptance Criteria

1. WHEN 1M and 5M trends both align with signal direction THEN the Position_Sizer SHALL add 5% to position size
2. WHEN 1M and 5M trends both align with signal direction THEN the Stop_Loss_Manager SHALL reduce stop distance by 0.5x ATR
3. WHEN micro-timeframes contradict signal direction THEN the Signal_Quality_Gate SHALL reject the signal
4. WHEN micro-timeframe data is unavailable THEN the Trading_System SHALL use standard parameters

### Requirement 10: Entry Confirmation Delay

**User Story:** As a trader, I want a brief confirmation delay before entry, so that I avoid chasing price spikes.

#### Acceptance Criteria

1. WHEN entry signal is generated THEN the Entry_Confirmer SHALL wait 1 candle before execution
2. WHEN price moves more than 0.3% against signal during confirmation THEN the Entry_Confirmer SHALL cancel the entry
3. WHEN confirmation period completes without adverse movement THEN the Entry_Confirmer SHALL execute the entry
4. WHEN entry is cancelled due to adverse movement THEN the Entry_Confirmer SHALL log the cancellation reason
