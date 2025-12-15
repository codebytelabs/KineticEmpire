# Kinetic Empire v3.0 - Quick Reference Card

## 🚀 Quick Start Commands

```bash
# Demo mode (safe testing)
python run_v3_demo.py

# Live mode (Binance Demo account)
python run_v3_live.py --capital 5000 --interval 60

# Run tests
python -m pytest tests/test_v3_*.py -v
```

## 📊 Signal Scoring (100 points)

| Component | Points | Criteria |
|-----------|--------|----------|
| 4H Trend | 25 | EMA(9) vs EMA(21) |
| 1H Alignment | 20 | Matches 4H direction |
| RSI Zone | 15 | LONG: 30-45, SHORT: 55-70 |
| MACD Cross | 15 | Line vs Signal |
| Volume | 10 | >= 1.5x average |
| Price Action | 15 | 15M trend + histogram |

## 📈 Leverage Tiers

| Confidence | Leverage | Risk % |
|------------|----------|--------|
| 60-69 | 5x | 1.0% |
| 70-79 | 10x | 1.0% |
| 80-89 | 15x | 1.5% |
| 90-100 | 20x | 2.0% |

## 🎯 Exit Strategy

```
Entry ─────────────────────────────────────▶
  │
  │ -3% ──▶ STOP LOSS (close all)
  │
  │ +1.5% ──▶ TP1: Close 40%, start trailing
  │
  │ +2.5% ──▶ TP2: Close 30%
  │
  │ +3.0% ──▶ Tighten trailing to 0.5%
  │
  │ Trail hit ──▶ Close remaining 30%
  ▼
```

## 🛡️ Risk Limits

| Limit | Default | Description |
|-------|---------|-------------|
| Max Positions | 12 | Concurrent open positions |
| Max Margin | 90% | Total margin usage |
| Daily Loss | 5% | Pause trading threshold |
| Correlated | 3 | Same asset group |
| Emergency | -4% | Single position loss |
| Portfolio | -5% | Total unrealized loss |

## 📉 Technical Indicators

| Indicator | Settings | Usage |
|-----------|----------|-------|
| EMA Fast | 9 | Trend direction |
| EMA Slow | 21 | Trend confirmation |
| RSI | 14 | Momentum zones |
| MACD | 12/26/9 | Crossover signals |
| ATR | 14 | Stop loss calculation |
| Volume | 20 | Spike detection |

## 🌡️ Market Regimes

| Regime | Condition | Action |
|--------|-----------|--------|
| TRENDING | Strong aligned trends | Trade normally |
| SIDEWAYS | 2% range for 20 candles | Avoid or reduce size |
| HIGH_VOL | ATR > 150% avg | Reduce leverage 50% |
| LOW_VOL | ATR < 50% avg | Trade normally |
| CHOPPY | Frequent EMA crosses | Skip signals |

## 📁 Key Files

```
src/kinetic_empire/v3/
├── engine.py              # Main orchestrator
├── core/
│   ├── config.py          # Configuration
│   ├── models.py          # Data models
│   └── data_hub.py        # Data management
├── scanner/
│   └── market_scanner.py  # Opportunity finder
├── analyzer/
│   ├── ta_analyzer.py     # Technical analysis
│   ├── indicators.py      # Indicator calculations
│   └── enhanced/          # Advanced TA system
└── manager/
    └── position_manager.py # Position lifecycle
```

## 🔧 Environment Variables

```env
# Required
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret
BINANCE_TESTNET=true

# Optional
TELEGRAM_BOT_TOKEN=bot_token
TELEGRAM_CHAT_ID=chat_id
```

## 📝 Log Levels

| Level | When to Use |
|-------|-------------|
| DEBUG | Development, troubleshooting |
| INFO | Normal operation |
| WARNING | Stop losses, rejections |
| ERROR | API failures |
| CRITICAL | Emergency exits |

## 🔍 Debugging

```python
# Enable debug logging
import logging
logging.getLogger("src.kinetic_empire.v3").setLevel(logging.DEBUG)

# Check cache stats
engine.data_hub.get_cache_stats()

# View position states
engine.position_manager.get_all_positions()

# Check engine status
engine.get_status()
```

## ⚡ Performance Tips

1. **Scan Interval**: 30-60s for live, 15s for demo
2. **Monitor Interval**: 3-5s for active management
3. **Max Opportunities**: 5-10 per scan cycle
4. **Cache TTL**: 60s for prices, 300s for OHLCV

## 🚨 Emergency Procedures

**Stop the bot:**
```bash
# Ctrl+C in terminal
# Or kill the process
```

**Close all positions manually:**
```python
await engine._close_all_positions("MANUAL_STOP")
```

**Check Binance directly:**
- Log into Binance Futures
- Review open positions
- Close manually if needed

---

*For full documentation, see [KINETIC_EMPIRE_V3_DOCUMENTATION.md](./KINETIC_EMPIRE_V3_DOCUMENTATION.md)*
