# Kinetic Empire v3.0 - Complete Documentation

## Table of Contents
1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Architecture](#architecture)
4. [Core Modules](#core-modules)
5. [Configuration](#configuration)
6. [Trading Strategy](#trading-strategy)
7. [Risk Management](#risk-management)
8. [Technical Indicators](#technical-indicators)
9. [Enhanced TA System](#enhanced-ta-system)
10. [Running the Bot](#running-the-bot)
11. [Troubleshooting](#troubleshooting)

---

## Overview

Kinetic Empire v3.0 is a professional-grade automated cryptocurrency futures trading system designed for Binance Futures. It uses multi-timeframe technical analysis, dynamic leverage scaling, and comprehensive risk management to identify and execute high-probability trades.

### Key Features
- **Multi-Timeframe Analysis**: Analyzes 4H, 1H, and 15M timeframes for trend alignment
- **Dynamic Leverage**: 5x-20x leverage based on signal confidence (60-100 score)
- **Enhanced TA System**: 11+ technical indicators with market regime detection
- **Smart Position Management**: Partial take profits, trailing stops, emergency exits
- **Risk Controls**: Max positions, margin limits, daily loss limits, correlation limits
- **Dual Quote Support**: Monitors both USDT and USDC markets

### Performance Targets
- Win Rate: 55-65%
- Risk per Trade: 1-2% of equity
- Max Drawdown: 5% daily limit
- Leverage Range: 5x-20x based on confidence

---

## Quick Start

### Prerequisites
- Python 3.10+
- Binance Futures Demo Account (or live account)
- API keys with futures trading permissions

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd KineticEmpire

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .
```

### Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` with your credentials:
```env
# Binance API (Demo or Live)
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
BINANCE_TESTNET=true  # Set to false for live trading

# Optional: Telegram notifications
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### Running

```bash
# Demo mode (simulated data - safe for testing)
python run_v3_demo.py

# Live mode (real Binance Demo account)
python run_v3_live.py --capital 5000 --interval 60
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     KINETIC ENGINE v3.0                         │
│                    (Main Orchestrator)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐ │
│  │   SCANNER   │───▶│  ANALYZER   │───▶│  POSITION MANAGER   │ │
│  │  (60s loop) │    │ (on-demand) │    │     (5s loop)       │ │
│  └─────────────┘    └─────────────┘    └─────────────────────┘ │
│         │                  │                     │              │
│         ▼                  ▼                     ▼              │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                      DATA HUB                               ││
│  │  (Price Cache | OHLCV Cache | Account State | Positions)    ││
│  └─────────────────────────────────────────────────────────────┘│
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                   BINANCE FUTURES API                       ││
│  │            (REST + WebSocket for real-time)                 ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### Module Responsibilities

| Module | Responsibility | Frequency |
|--------|---------------|-----------|
| **KineticEngine** | Orchestrates all modules, manages lifecycle | Continuous |
| **MarketScanner** | Finds high-potential opportunities | Every 60s |
| **TAAnalyzer** | Multi-timeframe technical analysis | On-demand |
| **PositionManager** | Risk checks, sizing, exits | Every 5s |
| **DataHub** | Central data cache and state | Real-time |

---

## Core Modules

### 1. Market Scanner (`scanner/market_scanner.py`)

The scanner identifies trading opportunities by filtering the market for:

**Volume Filter**
- Requires volume > 1.5x the 20-period average
- High volume indicates institutional interest

**Momentum Filter**
- Requires |24h change| > 1%
- Filters out stagnant markets

**Ranking Algorithm**
```
Score = |momentum| × volume_ratio
```
Top opportunities are passed to the analyzer.

**Usage:**
```python
from src.kinetic_empire.v3.scanner.market_scanner import MarketScanner

scanner = MarketScanner(
    volume_threshold=1.5,
    momentum_threshold=1.0,
    max_opportunities=20,
)
opportunities = await scanner.scan(tickers)
```

### 2. Technical Analyzer (`analyzer/ta_analyzer.py`)

Performs multi-timeframe analysis using:

**Timeframes Analyzed:**
- 4H: Primary trend direction (25 points)
- 1H: Trend confirmation (20 points)
- 15M: Entry timing (15 points)

**Scoring System (100 points total):**
| Component | Weight | Description |
|-----------|--------|-------------|
| 4H EMA Trend | 25 | EMA(9) vs EMA(21) direction |
| 1H Alignment | 20 | Matches 4H trend |
| RSI Zone | 15 | 30-45 for LONG, 55-70 for SHORT |
| MACD Cross | 15 | MACD line vs signal line |
| Volume Spike | 10 | Volume ratio >= 1.5x |
| Price Action | 15 | 15M trend + MACD histogram |

**Signal Generation:**
```python
from src.kinetic_empire.v3.analyzer.ta_analyzer import TAAnalyzer

analyzer = TAAnalyzer(min_score=60, max_stop_loss_pct=3.0)
signal = await analyzer.analyze(symbol, price, ohlcv_4h, ohlcv_1h, ohlcv_15m)

if signal:
    print(f"{signal.symbol}: {signal.direction} @ {signal.entry_price}")
    print(f"Confidence: {signal.confidence}%")
    print(f"Stop Loss: {signal.stop_loss}")
    print(f"Take Profit: {signal.take_profit}")
```

### 3. Position Manager (`manager/position_manager.py`)

Handles the complete position lifecycle:

**Pre-Trade Risk Checks:**
1. Max positions (default: 12)
2. Margin usage (max 90%)
3. Daily loss limit (max 5%)
4. Correlated positions (max 3 per group)
5. No duplicate positions

**Dynamic Leverage:**
| Confidence | Leverage |
|------------|----------|
| 60-69 | 5x |
| 70-79 | 10x |
| 80-89 | 15x |
| 90-100 | 20x |

**Position Sizing:**
```
Risk Amount = Equity × Risk% × Confidence Multiplier
Position Size = Risk Amount / Stop Distance
```

**Exit Management:**
- **TP1**: Close 40% at +1.5% profit
- **TP2**: Close 30% at +2.5% profit
- **Trailing Stop**: Activates at +1.5%, follows 1% behind
- **Stop Loss**: -3% max (ATR-based)
- **Emergency**: -4% position or -5% portfolio

### 4. Data Hub (`core/data_hub.py`)

Central data management with:
- Price cache with TTL
- OHLCV data caching
- Account state tracking
- Position synchronization
- WebSocket connection management

---

## Configuration

### Main Configuration (`core/config.py`)

```python
from src.kinetic_empire.v3.core.config import V3Config

config = V3Config()

# Leverage settings
config.leverage.tiers = {
    60: 5,   # Score 60-69 -> 5x
    70: 10,  # Score 70-79 -> 10x
    80: 15,  # Score 80-89 -> 15x
    90: 20,  # Score 90-100 -> 20x
}

# Risk settings
config.risk.max_positions = 12
config.risk.max_margin_usage = 90.0
config.risk.max_daily_loss_pct = 5.0
config.risk.emergency_portfolio_loss_pct = 5.0

# Take profit settings
config.take_profit.partial_levels = [
    (1.5, 0.40),  # At +1.5%, close 40%
    (2.5, 0.30),  # At +2.5%, close 30%
]
config.take_profit.trailing_activation_pct = 1.5
```

### Watchlist Configuration

Default watchlist includes high-liquidity pairs:
```python
watchlist = [
    # USDT pairs - Top caps
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT",
    # USDT pairs - High volatility alts
    "AVAX/USDT", "DOGE/USDT", "XRP/USDT", "ADA/USDT",
    # USDT pairs - DeFi & Layer 1
    "MATIC/USDT", "DOT/USDT", "LINK/USDT", "ATOM/USDT",
    # USDC pairs
    "BTC/USDC", "ETH/USDC", "SOL/USDC",
]
```

### Correlation Groups

Positions in the same group count toward correlation limits:
```python
correlation_groups = {
    "layer1": ["SOL", "AVAX", "DOT", "ATOM", "SUI", "APT", "SEI"],
    "defi": ["LINK", "INJ", "ARB", "OP"],
    "meme": ["DOGE", "WIF"],
    "major": ["BTC", "ETH", "BNB"],
}
```

---

## Trading Strategy

### Entry Criteria

A valid LONG signal requires:
1. ✅ 4H EMA(9) > EMA(21) (uptrend)
2. ✅ 1H trend aligns with 4H
3. ✅ RSI between 30-45 (not overbought)
4. ✅ MACD line > signal line
5. ✅ Volume ratio >= 1.5x average
6. ✅ Confidence score >= 60

A valid SHORT signal requires:
1. ✅ 4H EMA(9) < EMA(21) (downtrend)
2. ✅ 1H trend aligns with 4H
3. ✅ RSI between 55-70 (not oversold)
4. ✅ MACD line < signal line
5. ✅ Volume ratio >= 1.5x average
6. ✅ Confidence score >= 60

### Exit Strategy

```
Entry ──────────────────────────────────────────────▶
         │
         │ -3% ──▶ STOP LOSS (full close)
         │
         │ +1.5% ──▶ TP1: Close 40%, activate trailing
         │
         │ +2.5% ──▶ TP2: Close 30%
         │
         │ +3.0% ──▶ Tighten trailing to 0.5%
         │
         │ Trailing hit ──▶ Close remaining 30%
         ▼
```

### Position Sizing Example

```
Account Equity: $10,000
Signal Confidence: 85 (HIGH)
Entry Price: $100
Stop Loss: $97 (3% distance)

Risk Multiplier (85 confidence): 1.5x
Risk Percentage: 1.0% × 1.5 = 1.5%
Risk Amount: $10,000 × 1.5% = $150
Stop Distance: 3%

Position Value: $150 / 3% = $5,000
Leverage: 15x (for 85 confidence)
Actual Margin Used: $5,000 / 15 = $333.33
```

---

## Risk Management

### Pre-Trade Checks

| Check | Limit | Action if Exceeded |
|-------|-------|-------------------|
| Max Positions | 12 | Reject new trades |
| Margin Usage | 90% | Reject new trades |
| Daily Loss | 5% | Pause trading |
| Correlated Positions | 3 per group | Reject new trades |
| Duplicate Position | 1 per symbol | Reject new trades |

### Emergency Controls

**Portfolio Emergency (-5% unrealized)**
- Closes ALL positions immediately
- Logs critical alert
- Pauses new trades

**Position Emergency (-4% single position)**
- Closes the specific position
- Continues monitoring others

### Cooldown System (Live Mode)

After a stop loss:
- 30-minute cooldown before re-entering same symbol
- Max 3 losses per symbol per day
- Prevents revenge trading

---

## Technical Indicators

### EMA (Exponential Moving Average)
```python
def calc_ema(data: List[float], period: int) -> float:
    multiplier = 2 / (period + 1)
    ema = sum(data[:period]) / period  # Start with SMA
    for price in data[period:]:
        ema = (price * multiplier) + (ema * (1 - multiplier))
    return ema
```

### RSI (Relative Strength Index)
- Period: 14
- Overbought: > 70
- Oversold: < 30
- Optimal LONG zone: 30-45
- Optimal SHORT zone: 55-70

### MACD (Moving Average Convergence Divergence)
- Fast EMA: 12
- Slow EMA: 26
- Signal: 9
- Bullish: MACD line > Signal line
- Bearish: MACD line < Signal line

### ATR (Average True Range)
- Period: 14
- Used for: Stop loss calculation, volatility detection
- Stop Loss = Entry ± (2 × ATR), capped at 3%

### Volume Ratio
```python
volume_ratio = recent_volume / average_volume
# > 1.5 = Volume spike (bullish confirmation)
# < 0.8 = Low volume (potential false move)
```

---

## Enhanced TA System

The Enhanced TA System provides advanced market context awareness.

### Components

1. **Trend Strength Calculator**
   - STRONG: EMA separation > 1%
   - MODERATE: EMA separation 0.3-1%
   - WEAK: EMA separation < 0.3%

2. **Market Regime Detector**
   - TRENDING: Strong aligned trends
   - SIDEWAYS: Price ranging within 2%
   - HIGH_VOLATILITY: ATR > 150% average
   - LOW_VOLATILITY: ATR < 50% average
   - CHOPPY: Frequent EMA crossings

3. **Trend Alignment Engine**
   - Weights: 4H (50%), 1H (30%), 15M (20%)
   - Alignment bonus: +25 points when all aligned
   - Conflict penalty: -15 points for misalignment

4. **Volume Confirmation**
   - Confirms price moves with volume
   - Detects false moves (big price, low volume)
   - Identifies declining volume patterns

5. **Support/Resistance Detection**
   - Identifies key price levels
   - Detects breakouts with volume
   - Adjusts confidence near S/R levels

6. **BTC Correlation Engine**
   - Adjusts altcoin signals based on BTC trend
   - Pauses altcoin signals during BTC volatility
   - +/- 20 points adjustment for correlation

### Confidence Scoring Weights

| Component | Weight |
|-----------|--------|
| Trend Alignment | 30% |
| Trend Strength | 20% |
| Volume Confirmation | 15% |
| Momentum | 15% |
| Support/Resistance | 10% |
| Market Regime | 10% |

### Signal Confidence Levels

| Level | Score Range | Leverage |
|-------|-------------|----------|
| HIGH | 80-100 | 15-20x |
| MEDIUM | 65-79 | 10x |
| LOW | < 65 | No signal |

---

## Running the Bot

### Demo Mode (Simulated Data)

```bash
python run_v3_demo.py
```

Features:
- Uses mock market data
- No real trades executed
- Fast cycles for testing (15s scan, 3s monitor)
- Full logging enabled

### Live Mode (Binance Demo Account)

```bash
python run_v3_live.py --capital 5000 --interval 60
```

Parameters:
- `--capital`: Starting capital (default: 5000)
- `--interval`: Scan interval in seconds (default: 60)

Features:
- Connects to real Binance Demo API
- Executes real trades on demo account
- 30s scan interval, 5s position monitoring
- Cooldown system after stop losses

### Command Line Options

```bash
# Run with custom settings
python run_v3_live.py \
    --capital 10000 \
    --interval 30 \
    --max-positions 8 \
    --leverage 10
```

### Monitoring

Logs are written to:
- Console (real-time)
- `logs/v3_live_YYYYMMDD_HHMMSS.log`

Log levels:
- DEBUG: All operations (very verbose)
- INFO: Trades, signals, important events
- WARNING: Stop losses, rejected signals
- ERROR: API errors, exceptions
- CRITICAL: Emergency exits

---

## Troubleshooting

### Common Issues

**"No opportunities found"**
- Market may be quiet (low volatility)
- Volume/momentum thresholds not met
- Try during active trading hours (US/EU sessions)

**"Signal rejected - Max positions reached"**
- Already at maximum position limit
- Wait for existing positions to close
- Or increase `max_positions` in config

**"Signal rejected - Margin usage exceeds limit"**
- Too much margin already in use
- Close some positions or reduce position sizes

**"Confidence too low for any leverage"**
- Signal score below 60
- Market conditions not favorable
- Wait for better setups

**API Connection Errors**
- Check API keys in `.env`
- Verify `BINANCE_TESTNET=true` for demo
- Check internet connection
- Binance may have rate limits

### Debug Mode

Enable verbose logging:
```python
import logging
logging.getLogger("src.kinetic_empire.v3").setLevel(logging.DEBUG)
```

### Testing

Run the test suite:
```bash
# All v3 tests
python -m pytest tests/test_v3_*.py -v

# Specific module
python -m pytest tests/test_v3_analyzer.py -v

# With coverage
python -m pytest tests/test_v3_*.py --cov=src/kinetic_empire/v3
```

---

## API Reference

### Signal Dataclass

```python
@dataclass
class Signal:
    symbol: str                    # e.g., "BTCUSDT"
    direction: Literal["LONG", "SHORT"]
    confidence: int                # 0-100
    entry_price: float
    stop_loss: float
    take_profit: float
    atr: float
    timeframe_alignment: bool
    indicators: Dict[str, Indicators]
    timestamp: datetime
```

### Position Dataclass

```python
@dataclass
class Position:
    symbol: str
    side: Literal["LONG", "SHORT"]
    entry_price: float
    size: float
    leverage: int
    stop_loss: float
    take_profit: float
    trailing_stop: Optional[float]
    trailing_activated: bool
    partial_exits: List[float]
    peak_pnl: float
    entry_time: datetime
    confidence: int
```

### EnhancedSignal Dataclass

```python
@dataclass
class EnhancedSignal:
    symbol: str
    direction: str
    confidence: int
    confidence_level: SignalConfidence
    entry_price: float
    stop_loss: float
    take_profit: float
    market_context: MarketContext
    component_scores: Dict[str, int]
```

---

## Disclaimer

⚠️ **IMPORTANT**: This software is for educational purposes only. Cryptocurrency trading involves substantial risk of loss. Past performance does not guarantee future results. Always:

1. Start with demo/testnet accounts
2. Never risk more than you can afford to lose
3. Understand the strategy before using real funds
4. Monitor the bot regularly
5. Have emergency stop procedures in place

The authors are not responsible for any financial losses incurred from using this software.

---

## License

MIT License - See LICENSE file for details.

---

## Support

For issues and feature requests, please open a GitHub issue.

Happy Trading! 🚀
