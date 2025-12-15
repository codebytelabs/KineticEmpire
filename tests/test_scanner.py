"""Tests for scanner module.

**Feature: kinetic-empire, Property 1: Scanner Filter Pipeline Correctness**
**Feature: kinetic-empire, Property 2: Scanner Output Ordering and Limit**
**Feature: kinetic-empire, Property 27: Blacklist Pattern Application**
**Validates: Requirements 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 12.4**
"""

import re
import pytest
from hypothesis import given, strategies as st, settings, assume

from kinetic_empire.models import PairData
from kinetic_empire.scanner import (
    ScannerModule,
    ScannerConfig,
    is_blacklisted,
    filter_by_spread,
    filter_by_price,
    filter_by_volatility,
    filter_by_performance,
)


# Strategies for generating test data
@st.composite
def pair_data_strategy(draw):
    """Generate random PairData objects."""
    symbol = draw(st.text(
        alphabet=st.sampled_from("ABCDEFGHIJKLMNOPQRSTUVWXYZ/"),
        min_size=3,
        max_size=15
    ))
    # Ensure symbol has proper format
    if "/" not in symbol:
        symbol = symbol[:len(symbol)//2] + "/" + symbol[len(symbol)//2:]
    
    return PairData(
        symbol=symbol,
        quote_volume=draw(st.floats(min_value=0, max_value=1e12, allow_nan=False)),
        spread_ratio=draw(st.floats(min_value=0, max_value=0.1, allow_nan=False)),
        price=draw(st.floats(min_value=0, max_value=1e6, allow_nan=False)),
        volatility=draw(st.floats(min_value=0, max_value=1.0, allow_nan=False)),
        return_60m=draw(st.floats(min_value=-0.5, max_value=0.5, allow_nan=False)),
    )


@st.composite
def valid_pair_data_strategy(draw):
    """Generate PairData that passes all filters."""
    symbol = draw(st.text(
        alphabet=st.sampled_from("ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
        min_size=2,
        max_size=6
    ))
    symbol = symbol + "/USDT"
    
    return PairData(
        symbol=symbol,
        quote_volume=draw(st.floats(min_value=1000, max_value=1e12, allow_nan=False)),
        spread_ratio=draw(st.floats(min_value=0, max_value=0.004, allow_nan=False)),
        price=draw(st.floats(min_value=0.01, max_value=1e5, allow_nan=False)),
        volatility=draw(st.floats(min_value=0.03, max_value=0.45, allow_nan=False)),
        return_60m=draw(st.floats(min_value=0.001, max_value=0.3, allow_nan=False)),
    )



class TestScannerFilterPipelineCorrectness:
    """Property tests for scanner filter pipeline.
    
    **Feature: kinetic-empire, Property 1: Scanner Filter Pipeline Correctness**
    **Validates: Requirements 1.2, 1.3, 1.4, 1.5, 1.6**
    """

    @given(pairs=st.lists(pair_data_strategy(), min_size=0, max_size=100))
    @settings(max_examples=100)
    def test_filtered_pairs_pass_all_criteria(self, pairs: list[PairData]):
        """For any set of pairs, all filtered pairs SHALL pass all quality criteria."""
        scanner = ScannerModule()
        filtered = scanner.apply_filters(pairs)
        
        for pair in filtered:
            # Requirement 1.2: No blacklisted pairs
            assert not scanner.is_blacklisted(pair.symbol), \
                f"Blacklisted pair {pair.symbol} should not be in filtered results"
            
            # Requirement 1.3: spread_ratio <= 0.005
            assert pair.spread_ratio <= 0.005, \
                f"Pair {pair.symbol} has spread {pair.spread_ratio} > 0.005"
            
            # Requirement 1.4: price >= 0.001
            assert pair.price >= 0.001, \
                f"Pair {pair.symbol} has price {pair.price} < 0.001"
            
            # Requirement 1.5: volatility in [0.02, 0.50]
            assert 0.02 <= pair.volatility <= 0.50, \
                f"Pair {pair.symbol} has volatility {pair.volatility} outside [0.02, 0.50]"
            
            # Requirement 1.6: return_60m > 0
            assert pair.return_60m > 0, \
                f"Pair {pair.symbol} has return {pair.return_60m} <= 0"

    @given(pairs=st.lists(valid_pair_data_strategy(), min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_valid_pairs_pass_filters(self, pairs: list[PairData]):
        """For any valid pairs, they SHALL pass the filter pipeline."""
        scanner = ScannerModule()
        filtered = scanner.apply_filters(pairs)
        
        # All valid pairs should pass (unless blacklisted)
        for pair in pairs:
            if not scanner.is_blacklisted(pair.symbol):
                assert pair in filtered, \
                    f"Valid pair {pair.symbol} should be in filtered results"


class TestScannerOutputOrderingAndLimit:
    """Property tests for scanner output ordering and limit.
    
    **Feature: kinetic-empire, Property 2: Scanner Output Ordering and Limit**
    **Validates: Requirements 1.7**
    """

    @given(pairs=st.lists(valid_pair_data_strategy(), min_size=0, max_size=100))
    @settings(max_examples=100)
    def test_output_sorted_by_volatility_descending(self, pairs: list[PairData]):
        """For any filtered pairs, output SHALL be sorted by volatility descending."""
        scanner = ScannerModule()
        result = scanner.scan_with_data(pairs)
        
        # Check sorting
        for i in range(len(result) - 1):
            assert result[i].volatility >= result[i + 1].volatility, \
                f"Pairs not sorted by volatility: {result[i].volatility} < {result[i + 1].volatility}"

    @given(pairs=st.lists(valid_pair_data_strategy(), min_size=0, max_size=100))
    @settings(max_examples=100)
    def test_output_limited_to_max_pairs(self, pairs: list[PairData]):
        """For any input, output length SHALL be at most max_pairs (20)."""
        scanner = ScannerModule()
        result = scanner.scan(pairs)
        
        assert len(result) <= scanner.config.max_pairs, \
            f"Output has {len(result)} pairs, exceeds max {scanner.config.max_pairs}"

    @given(max_pairs=st.integers(min_value=1, max_value=50))
    @settings(max_examples=100)
    def test_output_respects_custom_max_pairs(self, max_pairs: int):
        """For any max_pairs config, output SHALL respect that limit."""
        config = ScannerConfig(max_pairs=max_pairs)
        scanner = ScannerModule(config)
        
        # Generate more pairs than max_pairs
        pairs = [
            PairData(
                symbol=f"TEST{i}/USDT",
                quote_volume=1000000 - i * 1000,
                spread_ratio=0.001,
                price=100.0,
                volatility=0.1 + i * 0.005,
                return_60m=0.01,
            )
            for i in range(max_pairs + 20)
        ]
        
        result = scanner.scan(pairs)
        assert len(result) <= max_pairs



class TestBlacklistPatternApplication:
    """Property tests for blacklist pattern application.
    
    **Feature: kinetic-empire, Property 27: Blacklist Pattern Application**
    **Validates: Requirements 12.4**
    """

    @given(st.sampled_from([
        "BNB/USDT", "BNB/BTC", "BNB/ETH",
        "BTCDOWN/USDT", "ETHDOWN/USDT", "BNBDOWN/USDT",
        "BTCUP/USDT", "ETHUP/USDT", "BNBUP/USDT",
        "USDC/USDT", "USDC/BTC",
    ]))
    @settings(max_examples=100)
    def test_default_blacklist_excludes_known_patterns(self, symbol: str):
        """For any default blacklisted symbol, scanner SHALL exclude it."""
        scanner = ScannerModule()
        assert scanner.is_blacklisted(symbol), \
            f"Symbol {symbol} should be blacklisted by default patterns"

    @given(st.sampled_from([
        "BTC/USDT", "ETH/USDT", "SOL/USDT", "DOGE/USDT",
        "XRP/USDT", "ADA/USDT", "DOT/USDT", "LINK/USDT",
    ]))
    @settings(max_examples=100)
    def test_valid_symbols_not_blacklisted(self, symbol: str):
        """For any valid trading symbol, scanner SHALL NOT exclude it."""
        scanner = ScannerModule()
        assert not scanner.is_blacklisted(symbol), \
            f"Symbol {symbol} should not be blacklisted"

    @given(
        pattern=st.sampled_from([r"^TEST.*", r".*PERP$", r".*BEAR.*"]),
        symbol=st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=3, max_size=8)
    )
    @settings(max_examples=100)
    def test_custom_blacklist_patterns_applied(self, pattern: str, symbol: str):
        """For any custom blacklist pattern, matching symbols SHALL be excluded."""
        config = ScannerConfig(blacklist_patterns=[pattern])
        scanner = ScannerModule(config)
        
        compiled = re.compile(pattern)
        test_symbol = symbol + "/USDT"
        
        if compiled.match(test_symbol):
            assert scanner.is_blacklisted(test_symbol), \
                f"Symbol {test_symbol} should match pattern {pattern}"

    def test_blacklisted_pairs_excluded_from_scan(self):
        """Blacklisted pairs SHALL be excluded from scan results."""
        scanner = ScannerModule()
        
        pairs = [
            PairData("BTC/USDT", 1e9, 0.001, 50000, 0.1, 0.05),
            PairData("BNB/USDT", 1e9, 0.001, 300, 0.15, 0.05),  # Blacklisted
            PairData("ETH/USDT", 1e9, 0.001, 3000, 0.12, 0.05),
            PairData("BTCDOWN/USDT", 1e9, 0.001, 10, 0.2, 0.05),  # Blacklisted
        ]
        
        result = scanner.scan(pairs)
        
        assert "BTC/USDT" in result
        assert "ETH/USDT" in result
        assert "BNB/USDT" not in result
        assert "BTCDOWN/USDT" not in result


class TestScannerEdgeCases:
    """Unit tests for scanner edge cases.
    
    **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7**
    """

    def test_empty_pair_list(self):
        """Empty pair list SHALL return empty result."""
        scanner = ScannerModule()
        result = scanner.scan([])
        assert result == []

    def test_all_pairs_filtered_out(self):
        """When all pairs fail filters, result SHALL be empty."""
        scanner = ScannerModule()
        
        # All pairs fail various filters
        pairs = [
            PairData("BTC/USDT", 1e9, 0.01, 50000, 0.1, 0.05),  # Spread too high
            PairData("ETH/USDT", 1e9, 0.001, 0.0001, 0.1, 0.05),  # Price too low
            PairData("SOL/USDT", 1e9, 0.001, 100, 0.01, 0.05),  # Volatility too low
            PairData("DOGE/USDT", 1e9, 0.001, 0.1, 0.1, -0.05),  # Negative return
        ]
        
        result = scanner.scan(pairs)
        assert result == []

    def test_exactly_max_pairs_remaining(self):
        """When exactly max_pairs pass filters, all SHALL be returned."""
        config = ScannerConfig(max_pairs=5)
        scanner = ScannerModule(config)
        
        pairs = [
            PairData(f"TEST{i}/USDT", 1e9 - i * 1e6, 0.001, 100, 0.1 + i * 0.01, 0.05)
            for i in range(5)
        ]
        
        result = scanner.scan(pairs)
        assert len(result) == 5

    def test_volume_selection_before_filters(self):
        """Top volume pairs SHALL be selected before applying filters."""
        config = ScannerConfig(min_volume_rank=3, max_pairs=2)
        scanner = ScannerModule(config)
        
        # High volume but fails filters
        pairs = [
            PairData("HIGH1/USDT", 1e12, 0.001, 100, 0.1, 0.05),  # Highest volume, valid
            PairData("HIGH2/USDT", 1e11, 0.001, 100, 0.1, 0.05),  # 2nd highest, valid
            PairData("HIGH3/USDT", 1e10, 0.001, 100, 0.1, 0.05),  # 3rd highest, valid
            PairData("LOW1/USDT", 1e6, 0.001, 100, 0.1, 0.05),   # Low volume, valid
        ]
        
        result = scanner.scan(pairs)
        
        # Only top 3 by volume are considered, then filtered and limited to 2
        assert len(result) <= 2
        assert "LOW1/USDT" not in result  # Should be excluded by volume rank

    def test_volatility_sorting_correct(self):
        """Pairs SHALL be sorted by volatility in descending order."""
        scanner = ScannerModule()
        
        pairs = [
            PairData("LOW/USDT", 1e9, 0.001, 100, 0.05, 0.01),
            PairData("HIGH/USDT", 1e9, 0.001, 100, 0.40, 0.01),
            PairData("MED/USDT", 1e9, 0.001, 100, 0.20, 0.01),
        ]
        
        result = scanner.scan(pairs)
        
        assert result[0] == "HIGH/USDT"
        assert result[1] == "MED/USDT"
        assert result[2] == "LOW/USDT"


class TestIndividualFilters:
    """Unit tests for individual filter functions."""

    def test_filter_by_spread_boundary(self):
        """Spread filter SHALL include pairs at exactly max_spread."""
        pairs = [
            PairData("EXACT/USDT", 1e9, 0.005, 100, 0.1, 0.01),  # Exactly at limit
            PairData("OVER/USDT", 1e9, 0.0051, 100, 0.1, 0.01),  # Just over
        ]
        
        result = filter_by_spread(pairs, max_spread=0.005)
        
        assert len(result) == 1
        assert result[0].symbol == "EXACT/USDT"

    def test_filter_by_price_boundary(self):
        """Price filter SHALL include pairs at exactly min_price."""
        pairs = [
            PairData("EXACT/USDT", 1e9, 0.001, 0.001, 0.1, 0.01),  # Exactly at limit
            PairData("UNDER/USDT", 1e9, 0.001, 0.0009, 0.1, 0.01),  # Just under
        ]
        
        result = filter_by_price(pairs, min_price=0.001)
        
        assert len(result) == 1
        assert result[0].symbol == "EXACT/USDT"

    def test_filter_by_volatility_boundaries(self):
        """Volatility filter SHALL include pairs at exactly min and max."""
        pairs = [
            PairData("MIN/USDT", 1e9, 0.001, 100, 0.02, 0.01),   # Exactly at min
            PairData("MAX/USDT", 1e9, 0.001, 100, 0.50, 0.01),   # Exactly at max
            PairData("UNDER/USDT", 1e9, 0.001, 100, 0.019, 0.01),  # Just under min
            PairData("OVER/USDT", 1e9, 0.001, 100, 0.501, 0.01),   # Just over max
        ]
        
        result = filter_by_volatility(pairs, min_vol=0.02, max_vol=0.50)
        
        assert len(result) == 2
        symbols = [p.symbol for p in result]
        assert "MIN/USDT" in symbols
        assert "MAX/USDT" in symbols

    def test_filter_by_performance_boundary(self):
        """Performance filter SHALL exclude pairs at exactly 0 return."""
        pairs = [
            PairData("ZERO/USDT", 1e9, 0.001, 100, 0.1, 0.0),    # Exactly 0
            PairData("POS/USDT", 1e9, 0.001, 100, 0.1, 0.001),   # Just positive
            PairData("NEG/USDT", 1e9, 0.001, 100, 0.1, -0.001),  # Just negative
        ]
        
        result = filter_by_performance(pairs, min_return=0.0)
        
        assert len(result) == 1
        assert result[0].symbol == "POS/USDT"

    def test_is_blacklisted_function(self):
        """is_blacklisted function SHALL correctly match patterns."""
        patterns = [re.compile(r"BNB/.*"), re.compile(r".*DOWN/.*")]
        
        assert is_blacklisted("BNB/USDT", patterns) is True
        assert is_blacklisted("BTCDOWN/USDT", patterns) is True
        assert is_blacklisted("BTC/USDT", patterns) is False
