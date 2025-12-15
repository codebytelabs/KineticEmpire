"""Integration tests with real Binance testnet data.

These tests connect to Binance testnet to validate:
- Exchange connectivity
- Real market data fetching
- Indicator calculations on live data
- Scanner filtering with real pairs
- Regime classification with real BTC data
"""

import os
import pytest
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables (don't override existing)
load_dotenv(override=False)

# Skip if no API credentials
BINANCE_API_KEY = os.getenv("Binance_testnet_API_KEY", "")
BINANCE_API_SECRET = os.getenv("Binance_testnet_API_SECRET", "")
HAS_CREDENTIALS = bool(BINANCE_API_KEY and BINANCE_API_SECRET)

# Try to import ccxt
try:
    import ccxt
    HAS_CCXT = True
except ImportError:
    HAS_CCXT = False

import pandas as pd
from kinetic_empire.indicators.calculator import IndicatorCalculator
from kinetic_empire.risk.regime import RegimeClassifier
from kinetic_empire.models import Regime, PairData


@pytest.fixture
def binance_testnet():
    """Create Binance testnet connection."""
    if not HAS_CCXT:
        pytest.skip("ccxt not installed")
    if not HAS_CREDENTIALS:
        pytest.skip("Binance testnet credentials not available")
    
    exchange = ccxt.binance({
        'apiKey': BINANCE_API_KEY,
        'secret': BINANCE_API_SECRET,
        'sandbox': True,  # Use testnet
        'enableRateLimit': True,
        'options': {
            'defaultType': 'future',
            'adjustForTimeDifference': True,
        }
    })
    
    return exchange


@pytest.fixture
def binance_spot():
    """Create Binance spot connection (public data only)."""
    if not HAS_CCXT:
        pytest.skip("ccxt not installed")
    
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {
            'defaultType': 'spot',
        }
    })
    
    return exchange


class TestExchangeConnectivity:
    """Test real exchange connectivity."""

    @pytest.mark.skipif(not HAS_CCXT, reason="ccxt not installed")
    def test_fetch_btc_ticker(self, binance_spot):
        """Fetch real BTC/USDT ticker."""
        ticker = binance_spot.fetch_ticker('BTC/USDT')
        
        assert ticker is not None
        assert 'last' in ticker
        assert ticker['last'] > 0
        assert 'bid' in ticker
        assert 'ask' in ticker
        print(f"\nBTC/USDT Price: ${ticker['last']:,.2f}")

    @pytest.mark.skipif(not HAS_CCXT, reason="ccxt not installed")
    def test_fetch_ohlcv_data(self, binance_spot):
        """Fetch real OHLCV data for BTC."""
        ohlcv = binance_spot.fetch_ohlcv('BTC/USDT', '5m', limit=100)
        
        assert len(ohlcv) > 0
        assert len(ohlcv[0]) == 6  # timestamp, o, h, l, c, v
        
        # Convert to dataframe
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        assert len(df) == 100
        assert df['close'].iloc[-1] > 0
        print(f"\nFetched {len(df)} candles, latest close: ${df['close'].iloc[-1]:,.2f}")

    @pytest.mark.skipif(not HAS_CCXT, reason="ccxt not installed")
    def test_fetch_multiple_tickers(self, binance_spot):
        """Fetch tickers for multiple pairs."""
        symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
        
        for symbol in symbols:
            ticker = binance_spot.fetch_ticker(symbol)
            assert ticker['last'] > 0
            print(f"{symbol}: ${ticker['last']:,.4f}")


class TestIndicatorsWithRealData:
    """Test indicator calculations with real market data."""

    @pytest.mark.skipif(not HAS_CCXT, reason="ccxt not installed")
    def test_calculate_indicators_on_real_data(self, binance_spot):
        """Calculate all indicators on real BTC data."""
        # Fetch real data
        ohlcv = binance_spot.fetch_ohlcv('BTC/USDT', '5m', limit=200)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Calculate indicators
        calculator = IndicatorCalculator()
        result = calculator.calculate_indicators(df)
        
        # Verify indicators exist and are valid
        assert 'ema_50' in result.columns
        assert 'roc_12' in result.columns
        assert 'rsi_14' in result.columns
        assert 'atr_14' in result.columns
        
        # Check RSI bounds
        valid_rsi = result['rsi_14'].dropna()
        assert all(0 <= v <= 100 for v in valid_rsi)
        
        # Check ATR non-negative
        valid_atr = result['atr_14'].dropna()
        assert all(v >= 0 for v in valid_atr)
        
        # Print latest values
        latest = result.iloc[-1]
        print(f"\nBTC/USDT Indicators:")
        print(f"  Close: ${latest['close']:,.2f}")
        print(f"  EMA50: ${latest['ema_50']:,.2f}")
        print(f"  ROC12: {latest['roc_12']:.2f}%")
        print(f"  RSI14: {latest['rsi_14']:.2f}")
        print(f"  ATR14: ${latest['atr_14']:,.2f}")

    @pytest.mark.skipif(not HAS_CCXT, reason="ccxt not installed")
    def test_rsi_bounds_on_multiple_pairs(self, binance_spot):
        """Verify RSI stays in bounds for multiple real pairs."""
        calculator = IndicatorCalculator()
        pairs = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
        
        for pair in pairs:
            ohlcv = binance_spot.fetch_ohlcv(pair, '5m', limit=100)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            result = calculator.calculate_indicators(df)
            valid_rsi = result['rsi_14'].dropna()
            
            assert all(0 <= v <= 100 for v in valid_rsi), f"RSI out of bounds for {pair}"
            print(f"{pair} RSI: {valid_rsi.iloc[-1]:.2f}")


class TestRegimeWithRealData:
    """Test regime classification with real BTC data."""

    @pytest.mark.skipif(not HAS_CCXT, reason="ccxt not installed")
    def test_regime_classification_real_btc(self, binance_spot):
        """Classify current market regime using real BTC daily data."""
        # Fetch daily BTC data
        ohlcv = binance_spot.fetch_ohlcv('BTC/USDT', '1d', limit=60)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Calculate EMA50
        calculator = IndicatorCalculator()
        df['ema_50'] = calculator.calculate_ema(df['close'], 50)
        
        # Get latest values
        btc_close = df['close'].iloc[-1]
        btc_ema50 = df['ema_50'].iloc[-1]
        
        # Classify regime
        classifier = RegimeClassifier()
        regime = classifier.classify(btc_close, btc_ema50)
        max_trades = classifier.get_max_trades(regime)
        
        print(f"\nBTC Daily Analysis:")
        print(f"  Close: ${btc_close:,.2f}")
        print(f"  EMA50: ${btc_ema50:,.2f}")
        print(f"  Regime: {regime.value.upper()}")
        print(f"  Max Trades: {max_trades}")
        
        assert regime in [Regime.BULL, Regime.BEAR]
        assert max_trades in [3, 20]


class TestScannerWithRealData:
    """Test scanner filtering with real market data."""

    @pytest.mark.skipif(not HAS_CCXT, reason="ccxt not installed")
    def test_fetch_and_filter_real_pairs(self, binance_spot):
        """Fetch real market data and apply scanner filters."""
        # Fetch all tickers
        tickers = binance_spot.fetch_tickers()
        
        # Filter USDT pairs
        usdt_pairs = {k: v for k, v in tickers.items() if k.endswith('/USDT')}
        
        print(f"\nTotal USDT pairs: {len(usdt_pairs)}")
        
        # Apply basic filters
        filtered = []
        for symbol, ticker in list(usdt_pairs.items())[:50]:  # Limit for speed
            try:
                if ticker.get('last', 0) < 0.001:
                    continue
                if ticker.get('quoteVolume', 0) < 1000000:  # Min $1M volume
                    continue
                
                # Calculate spread
                bid = ticker.get('bid', 0)
                ask = ticker.get('ask', 0)
                if bid and ask:
                    spread = (ask - bid) / ask
                    if spread > 0.005:
                        continue
                
                filtered.append({
                    'symbol': symbol,
                    'price': ticker['last'],
                    'volume': ticker.get('quoteVolume', 0),
                    'spread': spread if bid and ask else 0
                })
            except:
                continue
        
        print(f"Filtered pairs: {len(filtered)}")
        
        # Sort by volume
        filtered.sort(key=lambda x: x['volume'], reverse=True)
        
        # Show top 10
        print("\nTop 10 by volume:")
        for p in filtered[:10]:
            print(f"  {p['symbol']}: ${p['price']:,.4f} (Vol: ${p['volume']/1e6:.1f}M)")
        
        assert len(filtered) > 0


class TestDatabasePersistence:
    """Test database operations with real data."""

    def test_save_and_retrieve_trade(self):
        """Test saving and retrieving a trade from SQLite."""
        import tempfile
        import os
        from kinetic_empire.persistence import TradePersistence
        from kinetic_empire.models import TradeOpen, TradeClose, Regime, ExitReason
        
        # Create temp database
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        
        try:
            db = TradePersistence(db_path)
            
            # Create and save trade
            trade_open = TradeOpen(
                id="integration_test_001",
                timestamp=datetime.now(),
                pair="BTC/USDT",
                entry_price=50000.0,
                stake_amount=100.0,
                regime=Regime.BULL,
                stop_loss=48000.0,
                amount=0.002
            )
            
            db.save_trade_open(trade_open)
            
            # Retrieve
            trades = db.get_trades_by_pair("BTC/USDT", closed_only=False)
            assert len(trades) == 1
            assert trades[0].id == "integration_test_001"
            assert trades[0].entry_price == 50000.0
            
            # Close trade
            trade_close = TradeClose(
                trade_id="integration_test_001",
                timestamp=datetime.now(),
                exit_price=51000.0,
                profit_loss=20.0,
                exit_reason=ExitReason.TREND_BREAK
            )
            
            db.save_trade_close(trade_close)
            
            # Verify closed
            trades = db.get_trades_by_pair("BTC/USDT", closed_only=True)
            assert len(trades) == 1
            assert trades[0].is_closed
            assert trades[0].profit_loss == 20.0
            
            print("\n✅ Database persistence working correctly")
            
        finally:
            os.unlink(db_path)


class TestFullStrategyFlow:
    """Test complete strategy flow with real data."""

    @pytest.mark.skipif(not HAS_CCXT, reason="ccxt not installed")
    def test_entry_signal_evaluation_real_data(self, binance_spot):
        """Evaluate entry signals on real market data."""
        from kinetic_empire.strategy.entry import EntrySignalGenerator
        from kinetic_empire.indicators.calculator import IndicatorCalculator
        
        calculator = IndicatorCalculator()
        entry_gen = EntrySignalGenerator()
        classifier = RegimeClassifier()
        
        # Get BTC daily for regime
        btc_daily = binance_spot.fetch_ohlcv('BTC/USDT', '1d', limit=60)
        btc_df = pd.DataFrame(btc_daily, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        btc_df['ema_50'] = calculator.calculate_ema(btc_df['close'], 50)
        
        regime = classifier.classify(btc_df['close'].iloc[-1], btc_df['ema_50'].iloc[-1])
        
        # Test multiple pairs
        pairs = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
        signals = []
        
        for pair in pairs:
            # Get 5m data
            ohlcv_5m = binance_spot.fetch_ohlcv(pair, '5m', limit=100)
            df_5m = pd.DataFrame(ohlcv_5m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df_5m = calculator.calculate_indicators(df_5m)
            
            # Get 1h data
            ohlcv_1h = binance_spot.fetch_ohlcv(pair, '1h', limit=60)
            df_1h = pd.DataFrame(ohlcv_1h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df_1h['ema_50'] = calculator.calculate_ema(df_1h['close'], 50)
            
            # Get latest values
            latest_5m = df_5m.iloc[-1]
            latest_1h = df_1h.iloc[-1]
            
            # Calculate 24h volume mean
            vol_mean = df_5m['volume'].tail(288).mean() if len(df_5m) >= 288 else df_5m['volume'].mean()
            
            # Check individual entry conditions
            macro = entry_gen.check_macro_trend(latest_1h['close'], latest_1h['ema_50'])
            micro = entry_gen.check_micro_trend(latest_5m['close'], latest_5m['ema_50'])
            momentum = entry_gen.check_momentum(latest_5m['roc_12'])
            pullback = entry_gen.check_pullback(latest_5m['rsi_14'])
            volume_ok = entry_gen.check_volume(latest_5m['volume'], vol_mean)
            trade_limit = entry_gen.check_trade_limit(regime, 0)
            
            # All conditions must be true
            should_enter = macro and micro and momentum and pullback and volume_ok and trade_limit
            
            signals.append({
                'pair': pair,
                'signal': should_enter,
                'conditions': {
                    'macro_trend': macro,
                    'micro_trend': micro,
                    'momentum': momentum,
                    'pullback': pullback,
                    'volume': volume_ok
                }
            })
        
        print(f"\nRegime: {regime.value.upper()}")
        print("\nEntry Signal Analysis:")
        for s in signals:
            status = "✅ BUY" if s['signal'] else "❌ NO"
            print(f"  {s['pair']}: {status}")
            conds = s['conditions']
            print(f"    Macro: {'✓' if conds['macro_trend'] else '✗'} | "
                  f"Micro: {'✓' if conds['micro_trend'] else '✗'} | "
                  f"ROC: {'✓' if conds['momentum'] else '✗'} | "
                  f"RSI: {'✓' if conds['pullback'] else '✗'} | "
                  f"Vol: {'✓' if conds['volume'] else '✗'}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
