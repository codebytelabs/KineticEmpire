"""Tests for Wave Rider Momentum Scanner.

Includes property-based tests for:
- Property 1: Momentum Score Calculation
- Property 2: Top Movers Sorting
"""

import pytest
from hypothesis import given, strategies as st, settings

from src.kinetic_empire.wave_rider.momentum_scanner import MomentumScanner
from src.kinetic_empire.wave_rider.models import MoverData, SpikeClassification, WaveRiderConfig


def make_ticker(
    symbol: str,
    price: float = 100.0,
    price_change_pct: float = 1.0,
    volume_24h: float = 50_000_000,
    volume: float = 2_000_000,
) -> dict:
    """Create a ticker dict for testing."""
    return {
        "symbol": symbol,
        "lastPrice": price,
        "priceChangePercent": price_change_pct,
        "quoteVolume": volume_24h,
        "volume": volume,
    }


class TestMomentumScanner:
    """Unit tests for MomentumScanner."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.scanner = MomentumScanner()
    
    def test_scan_empty_tickers(self):
        """Test scanning empty ticker list."""
        result = self.scanner.scan_all_futures([])
        assert result == []
    
    def test_scan_filters_non_usdt(self):
        """Test that non-USDT pairs are filtered out."""
        tickers = [
            make_ticker("BTCUSDT"),
            make_ticker("ETHBTC"),  # Should be filtered
            make_ticker("SOLBUSD"),  # Should be filtered
        ]
        result = self.scanner.scan_all_futures(tickers)
        assert len(result) == 1
        assert result[0].symbol == "BTCUSDT"
    
    def test_scan_filters_invalid_price(self):
        """Test that zero/negative prices are filtered."""
        tickers = [
            make_ticker("BTCUSDT", price=50000),
            make_ticker("ETHUSDT", price=0),  # Should be filtered
            make_ticker("SOLUSDT", price=-100),  # Should be filtered
        ]
        result = self.scanner.scan_all_futures(tickers)
        assert len(result) == 1
        assert result[0].symbol == "BTCUSDT"
    
    def test_scan_calculates_momentum_score(self):
        """Test momentum score calculation in scan."""
        # Pre-populate volume history for predictable ratio
        self.scanner._volume_history["BTCUSDT"] = [1000] * 19
        
        tickers = [make_ticker("BTCUSDT", price_change_pct=5.0, volume=2000)]
        result = self.scanner.scan_all_futures(tickers)
        
        assert len(result) == 1
        # volume_ratio = 2000 / 1000 = 2.0
        # momentum_score = 2.0 * 5.0 = 10.0
        assert result[0].volume_ratio == 2.0
        assert result[0].momentum_score == 10.0
    
    def test_get_top_movers_sorted_descending(self):
        """Test that top movers are sorted by momentum score descending."""
        # Pre-populate volume history
        for symbol in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]:
            self.scanner._volume_history[symbol] = [1000] * 19
        
        tickers = [
            make_ticker("BTCUSDT", price_change_pct=1.0, volume=2000),  # score = 2.0
            make_ticker("ETHUSDT", price_change_pct=5.0, volume=3000),  # score = 15.0
            make_ticker("SOLUSDT", price_change_pct=3.0, volume=2500),  # score = 7.5
        ]
        
        result = self.scanner.get_top_movers(tickers, limit=10)
        
        assert len(result) == 3
        assert result[0].symbol == "ETHUSDT"  # Highest score
        assert result[1].symbol == "SOLUSDT"
        assert result[2].symbol == "BTCUSDT"  # Lowest score
    
    def test_get_top_movers_respects_limit(self):
        """Test that top movers respects the limit parameter."""
        for i in range(10):
            symbol = f"COIN{i}USDT"
            self.scanner._volume_history[symbol] = [1000] * 19
        
        tickers = [
            make_ticker(f"COIN{i}USDT", price_change_pct=float(i + 1), volume=2000)
            for i in range(10)
        ]
        
        result = self.scanner.get_top_movers(tickers, limit=3)
        
        assert len(result) == 3
    
    def test_get_top_movers_filters_low_volume(self):
        """Test that low 24h volume pairs are filtered."""
        self.scanner._volume_history["BTCUSDT"] = [1000] * 19
        self.scanner._volume_history["LOWUSDT"] = [1000] * 19
        
        tickers = [
            make_ticker("BTCUSDT", volume_24h=50_000_000),  # Above threshold
            make_ticker("LOWUSDT", volume_24h=1_000_000),   # Below 10M threshold
        ]
        
        result = self.scanner.get_top_movers(tickers, limit=10)
        
        assert len(result) == 1
        assert result[0].symbol == "BTCUSDT"
    
    def test_volume_ratio_with_no_history(self):
        """Test volume ratio returns 1.0 with no history."""
        ratio = self.scanner.calculate_volume_ratio("NEWUSDT", 1000)
        assert ratio == 1.0
    
    def test_volume_ratio_with_history(self):
        """Test volume ratio calculation with history."""
        self.scanner._volume_history["BTCUSDT"] = [1000, 1000, 1000]
        ratio = self.scanner.calculate_volume_ratio("BTCUSDT", 2000)
        assert ratio == 2.0
    
    def test_volume_history_capped_at_20(self):
        """Test that volume history is capped at 20 entries."""
        for i in range(25):
            self.scanner.update_volume_history("BTCUSDT", float(i))
        
        assert len(self.scanner._volume_history["BTCUSDT"]) == 20


class TestMomentumScoreProperty:
    """Property-based tests for Momentum Score Calculation.
    
    Property 1: Momentum Score Calculation
    For any volume_ratio and price_change_pct, the momentum_score SHALL equal
    volume_ratio multiplied by the absolute value of price_change_pct.
    
    Validates: Requirements 1.4
    """
    
    def setup_method(self):
        """Set up test fixtures."""
        self.scanner = MomentumScanner()
    
    @given(
        volume_ratio=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        price_change_pct=st.floats(min_value=-50.0, max_value=50.0, allow_nan=False, allow_infinity=False),
    )
    def test_property_momentum_score_formula(self, volume_ratio: float, price_change_pct: float):
        """Property: momentum_score = volume_ratio * abs(price_change_pct)."""
        score = self.scanner.calculate_momentum_score(volume_ratio, price_change_pct)
        expected = volume_ratio * abs(price_change_pct)
        assert abs(score - expected) < 1e-10
    
    @given(
        volume_ratio=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        price_change_pct=st.floats(min_value=-50.0, max_value=50.0, allow_nan=False, allow_infinity=False),
    )
    def test_property_momentum_score_non_negative(self, volume_ratio: float, price_change_pct: float):
        """Property: momentum_score is always non-negative."""
        score = self.scanner.calculate_momentum_score(volume_ratio, price_change_pct)
        assert score >= 0
    
    @given(
        volume_ratio=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        price_change_pct=st.floats(min_value=0.0, max_value=50.0, allow_nan=False, allow_infinity=False),
    )
    def test_property_momentum_score_symmetric(self, volume_ratio: float, price_change_pct: float):
        """Property: momentum_score is same for positive and negative price change."""
        score_pos = self.scanner.calculate_momentum_score(volume_ratio, price_change_pct)
        score_neg = self.scanner.calculate_momentum_score(volume_ratio, -price_change_pct)
        assert abs(score_pos - score_neg) < 1e-10


class TestTopMoversProperty:
    """Property-based tests for Top Movers Sorting.
    
    Property 2: Top Movers Sorting
    For any list of movers returned by get_top_movers(), the list SHALL be
    sorted in descending order by momentum_score and contain at most the
    specified limit.
    
    Validates: Requirements 1.5
    """
    
    def setup_method(self):
        """Set up test fixtures."""
        # Use config with low volume threshold for testing
        config = WaveRiderConfig(min_24h_volume=0)
        self.scanner = MomentumScanner(config=config)
    
    @given(
        num_tickers=st.integers(min_value=0, max_value=50),
        limit=st.integers(min_value=1, max_value=20),
    )
    @settings(max_examples=50)
    def test_property_top_movers_limit(self, num_tickers: int, limit: int):
        """Property: result length <= limit."""
        # Pre-populate volume history
        for i in range(num_tickers):
            symbol = f"COIN{i}USDT"
            self.scanner._volume_history[symbol] = [1000] * 19
        
        tickers = [
            make_ticker(f"COIN{i}USDT", price_change_pct=float(i + 1), volume=2000)
            for i in range(num_tickers)
        ]
        
        result = self.scanner.get_top_movers(tickers, limit=limit)
        
        assert len(result) <= limit
    
    @given(
        num_tickers=st.integers(min_value=2, max_value=20),
    )
    @settings(max_examples=30)
    def test_property_top_movers_sorted_descending(self, num_tickers: int):
        """Property: result is sorted by momentum_score descending."""
        # Pre-populate volume history
        for i in range(num_tickers):
            symbol = f"COIN{i}USDT"
            self.scanner._volume_history[symbol] = [1000] * 19
        
        tickers = [
            make_ticker(f"COIN{i}USDT", price_change_pct=float(i + 1), volume=2000)
            for i in range(num_tickers)
        ]
        
        result = self.scanner.get_top_movers(tickers, limit=100)
        
        # Check sorted descending
        for i in range(len(result) - 1):
            assert result[i].momentum_score >= result[i + 1].momentum_score
    
    @given(
        num_tickers=st.integers(min_value=0, max_value=30),
        limit=st.integers(min_value=1, max_value=20),
    )
    @settings(max_examples=30)
    def test_property_top_movers_contains_highest_scores(self, num_tickers: int, limit: int):
        """Property: result contains the highest momentum scores."""
        # Pre-populate volume history
        for i in range(num_tickers):
            symbol = f"COIN{i}USDT"
            self.scanner._volume_history[symbol] = [1000] * 19
        
        tickers = [
            make_ticker(f"COIN{i}USDT", price_change_pct=float(i + 1), volume=2000)
            for i in range(num_tickers)
        ]
        
        result = self.scanner.get_top_movers(tickers, limit=limit)
        all_movers = self.scanner.scan_all_futures(tickers)
        
        if len(result) > 0 and len(all_movers) > len(result):
            # The minimum score in result should be >= max score not in result
            min_result_score = min(m.momentum_score for m in result)
            result_symbols = {m.symbol for m in result}
            non_result_scores = [m.momentum_score for m in all_movers if m.symbol not in result_symbols]
            
            if non_result_scores:
                max_non_result_score = max(non_result_scores)
                assert min_result_score >= max_non_result_score
