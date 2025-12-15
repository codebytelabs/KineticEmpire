"""Property-based tests for Kinetic Empire v3.0 Market Scanner.

**Feature: kinetic-empire-v3**
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from datetime import datetime
from src.kinetic_empire.v3.scanner.market_scanner import MarketScanner
from src.kinetic_empire.v3.core.models import Ticker


# Strategies for generating test data
price_strategy = st.floats(min_value=0.01, max_value=100000.0, allow_nan=False, allow_infinity=False)
volume_strategy = st.floats(min_value=1.0, max_value=1e12, allow_nan=False, allow_infinity=False)
change_strategy = st.floats(min_value=-50.0, max_value=50.0, allow_nan=False, allow_infinity=False)


@st.composite
def valid_ticker(draw, symbol: str = None):
    """Generate a valid Ticker."""
    if symbol is None:
        base = draw(st.sampled_from(["BTC", "ETH", "SOL", "DOGE", "XRP", "ADA"]))
        quote = draw(st.sampled_from(["USDT", "USDC"]))
        symbol = f"{base}{quote}"
    
    price = draw(price_strategy)
    change_24h = draw(change_strategy)
    volume_24h = draw(volume_strategy)
    
    # High/low should be consistent with price and change
    high_24h = price * (1 + abs(change_24h) / 100 + 0.01)
    low_24h = price * (1 - abs(change_24h) / 100 - 0.01)
    if low_24h <= 0:
        low_24h = price * 0.5
    
    return Ticker(
        symbol=symbol,
        price=price,
        change_24h=change_24h,
        volume_24h=volume_24h,
        high_24h=high_24h,
        low_24h=low_24h,
    )


@st.composite
def ticker_list(draw, min_size: int = 5, max_size: int = 50):
    """Generate a list of valid tickers."""
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "XRPUSDT", 
               "ADAUSDT", "BTCUSDC", "ETHUSDC", "BNBUSDT", "MATICUSDT"]
    
    num_tickers = draw(st.integers(min_value=min_size, max_value=max_size))
    tickers = []
    
    for i in range(num_tickers):
        symbol = symbols[i % len(symbols)]
        ticker = draw(valid_ticker(symbol=symbol))
        tickers.append(ticker)
    
    return tickers


class TestVolumeFilter:
    """Property tests for volume filter."""

    @given(tickers=ticker_list())
    @settings(max_examples=100)
    def test_volume_filter_correctness(self, tickers: list):
        """**Feature: kinetic-empire-v3, Property 1: Volume Filter Correctness**
        
        For any list of tickers with volume data, the Market_Scanner volume filter 
        SHALL return only tickers where current volume exceeds 1.5x the 20-period average volume.
        **Validates: Requirements 1.2**
        """
        scanner = MarketScanner(volume_threshold=1.5)
        filtered = scanner.filter_by_volume(tickers)
        
        # All filtered tickers should have volume ratio >= threshold
        for ticker in filtered:
            volume_ratio = scanner._calculate_volume_ratio(ticker)
            assert volume_ratio >= 1.5, (
                f"Ticker {ticker.symbol} has volume ratio {volume_ratio} < 1.5"
            )

    @given(tickers=ticker_list())
    @settings(max_examples=100)
    def test_volume_filter_subset(self, tickers: list):
        """Filtered tickers should be a subset of input tickers."""
        scanner = MarketScanner(volume_threshold=1.5)
        filtered = scanner.filter_by_volume(tickers)
        
        # All filtered tickers should be in original list
        original_symbols = {t.symbol for t in tickers}
        for ticker in filtered:
            assert ticker.symbol in original_symbols

    @given(
        threshold=st.floats(min_value=0.5, max_value=5.0, allow_nan=False, allow_infinity=False),
        tickers=ticker_list(),
    )
    @settings(max_examples=50)
    def test_volume_filter_threshold_monotonic(self, threshold: float, tickers: list):
        """Higher threshold should result in fewer or equal filtered tickers."""
        scanner_low = MarketScanner(volume_threshold=threshold)
        scanner_high = MarketScanner(volume_threshold=threshold + 0.5)
        
        filtered_low = scanner_low.filter_by_volume(tickers)
        filtered_high = scanner_high.filter_by_volume(tickers)
        
        assert len(filtered_high) <= len(filtered_low)


class TestMomentumFilter:
    """Property tests for momentum filter."""

    @given(tickers=ticker_list())
    @settings(max_examples=100)
    def test_momentum_filter_correctness(self, tickers: list):
        """**Feature: kinetic-empire-v3, Property 2: Momentum Filter Correctness**
        
        For any list of tickers with price data, the Market_Scanner momentum filter 
        SHALL return only tickers where absolute 24h price change exceeds 1%.
        **Validates: Requirements 1.3**
        """
        scanner = MarketScanner(momentum_threshold=1.0)
        filtered = scanner.filter_by_momentum(tickers)
        
        # All filtered tickers should have |change_24h| >= threshold
        for ticker in filtered:
            assert abs(ticker.change_24h) >= 1.0, (
                f"Ticker {ticker.symbol} has change {ticker.change_24h}% < 1%"
            )

    @given(tickers=ticker_list())
    @settings(max_examples=100)
    def test_momentum_filter_subset(self, tickers: list):
        """Filtered tickers should be a subset of input tickers."""
        scanner = MarketScanner(momentum_threshold=1.0)
        filtered = scanner.filter_by_momentum(tickers)
        
        original_symbols = {t.symbol for t in tickers}
        for ticker in filtered:
            assert ticker.symbol in original_symbols

    @given(
        threshold=st.floats(min_value=0.5, max_value=10.0, allow_nan=False, allow_infinity=False),
        tickers=ticker_list(),
    )
    @settings(max_examples=50)
    def test_momentum_filter_threshold_monotonic(self, threshold: float, tickers: list):
        """Higher threshold should result in fewer or equal filtered tickers."""
        scanner_low = MarketScanner(momentum_threshold=threshold)
        scanner_high = MarketScanner(momentum_threshold=threshold + 1.0)
        
        filtered_low = scanner_low.filter_by_momentum(tickers)
        filtered_high = scanner_high.filter_by_momentum(tickers)
        
        assert len(filtered_high) <= len(filtered_low)


class TestOpportunityRanking:
    """Property tests for opportunity ranking."""

    @given(tickers=ticker_list())
    @settings(max_examples=100)
    def test_ranking_returns_symbols(self, tickers: list):
        """Ranking should return list of symbol strings."""
        scanner = MarketScanner()
        ranked = scanner.rank_opportunities(tickers)
        
        assert isinstance(ranked, list)
        for symbol in ranked:
            assert isinstance(symbol, str)

    @given(tickers=ticker_list())
    @settings(max_examples=100)
    def test_ranking_respects_max_opportunities(self, tickers: list):
        """Ranking should not exceed max_opportunities."""
        max_opps = 10
        scanner = MarketScanner(max_opportunities=max_opps)
        ranked = scanner.rank_opportunities(tickers)
        
        assert len(ranked) <= max_opps

    @given(tickers=ticker_list(min_size=10, max_size=30))
    @settings(max_examples=50)
    def test_ranking_is_sorted_by_score(self, tickers: list):
        """Ranked opportunities should be sorted by score descending."""
        scanner = MarketScanner()
        
        # Deduplicate tickers by symbol (keep first occurrence)
        seen = set()
        unique_tickers = []
        for t in tickers:
            if t.symbol not in seen:
                seen.add(t.symbol)
                unique_tickers.append(t)
        
        ranked = scanner.rank_opportunities(unique_tickers)
        
        if len(ranked) < 2:
            return  # Nothing to compare
        
        # Calculate scores for ranked symbols
        ticker_map = {t.symbol: t for t in unique_tickers}
        scores = []
        for symbol in ranked:
            if symbol in ticker_map:
                ticker = ticker_map[symbol]
                volume_ratio = scanner._calculate_volume_ratio(ticker)
                score = abs(ticker.change_24h) * volume_ratio
                scores.append(score)
        
        # Verify descending order
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], f"Scores not sorted: {scores}"


class TestScannerIntegration:
    """Integration tests for full scan pipeline."""

    @given(tickers=ticker_list())
    @settings(max_examples=50)
    def test_scan_returns_valid_symbols(self, tickers: list):
        """Scan should return valid symbol strings."""
        import asyncio
        
        scanner = MarketScanner()
        opportunities = asyncio.run(scanner.scan(tickers))
        
        assert isinstance(opportunities, list)
        for symbol in opportunities:
            assert isinstance(symbol, str)
            assert len(symbol) > 0

    @given(tickers=ticker_list())
    @settings(max_examples=50)
    def test_scan_excludes_invalid_symbols(self, tickers: list):
        """Scan should exclude symbols not ending in USDT/USDC."""
        import asyncio
        
        scanner = MarketScanner(base_currencies=["USDT", "USDC"])
        opportunities = asyncio.run(scanner.scan(tickers))
        
        for symbol in opportunities:
            assert symbol.endswith("USDT") or symbol.endswith("USDC"), (
                f"Symbol {symbol} should end with USDT or USDC"
            )
