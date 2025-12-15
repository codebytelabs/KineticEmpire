"""Technical indicator calculations for Kinetic Empire v3.0.

All indicators are implemented from scratch for full control and testability.
"""

from typing import List, Tuple


def calc_ema(data: List[float], period: int) -> float:
    """Calculate Exponential Moving Average.
    
    Args:
        data: List of prices (oldest to newest)
        period: EMA period (e.g., 9, 21)
    
    Returns:
        Current EMA value
    """
    if not data or period <= 0:
        return 0.0
    
    if len(data) < period:
        # Not enough data, return SMA
        return sum(data) / len(data)
    
    # EMA multiplier
    multiplier = 2 / (period + 1)
    
    # Start with SMA of first 'period' values
    ema = sum(data[:period]) / period
    
    # Calculate EMA for remaining values
    for price in data[period:]:
        ema = (price * multiplier) + (ema * (1 - multiplier))
    
    return ema


def calc_ema_series(data: List[float], period: int) -> List[float]:
    """Calculate EMA series for all data points.
    
    Args:
        data: List of prices (oldest to newest)
        period: EMA period
    
    Returns:
        List of EMA values (same length as input)
    """
    if not data or period <= 0:
        return []
    
    result = []
    multiplier = 2 / (period + 1)
    
    for i, price in enumerate(data):
        if i < period - 1:
            # Not enough data yet, use SMA
            result.append(sum(data[: i + 1]) / (i + 1))
        elif i == period - 1:
            # First EMA is SMA
            result.append(sum(data[:period]) / period)
        else:
            # EMA calculation
            ema = (price * multiplier) + (result[-1] * (1 - multiplier))
            result.append(ema)
    
    return result


def calc_rsi(closes: List[float], period: int = 14) -> float:
    """Calculate Relative Strength Index.
    
    Args:
        closes: List of closing prices (oldest to newest)
        period: RSI period (default 14)
    
    Returns:
        RSI value between 0 and 100
    """
    if not closes or len(closes) < period + 1:
        return 50.0  # Neutral if not enough data
    
    # Calculate price changes
    gains = []
    losses = []
    
    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    
    # Use Wilder's smoothing method (exponential)
    if len(gains) < period:
        return 50.0
    
    # Initial averages (SMA)
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    # Smooth with Wilder's method
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calc_macd(
    closes: List[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> Tuple[float, float, float]:
    """Calculate MACD (Moving Average Convergence Divergence).
    
    Args:
        closes: List of closing prices (oldest to newest)
        fast: Fast EMA period (default 12)
        slow: Slow EMA period (default 26)
        signal: Signal line period (default 9)
    
    Returns:
        Tuple of (macd_line, signal_line, histogram)
    """
    if not closes or len(closes) < slow:
        return 0.0, 0.0, 0.0
    
    # Calculate fast and slow EMAs
    fast_ema = calc_ema_series(closes, fast)
    slow_ema = calc_ema_series(closes, slow)
    
    # MACD line = Fast EMA - Slow EMA
    macd_line_series = []
    for i in range(len(closes)):
        if i < slow - 1:
            macd_line_series.append(0)
        else:
            macd_line_series.append(fast_ema[i] - slow_ema[i])
    
    # Signal line = EMA of MACD line
    # Only use valid MACD values (after slow period)
    valid_macd = macd_line_series[slow - 1 :]
    if len(valid_macd) < signal:
        signal_line = sum(valid_macd) / len(valid_macd) if valid_macd else 0
    else:
        signal_line = calc_ema(valid_macd, signal)
    
    # Current values
    macd_line = macd_line_series[-1] if macd_line_series else 0
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram


def calc_atr(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 14,
) -> float:
    """Calculate Average True Range.
    
    Args:
        highs: List of high prices
        lows: List of low prices
        closes: List of closing prices
        period: ATR period (default 14)
    
    Returns:
        Current ATR value
    """
    if not highs or not lows or not closes:
        return 0.0
    
    if len(highs) != len(lows) or len(highs) != len(closes):
        return 0.0
    
    if len(highs) < 2:
        return highs[0] - lows[0] if highs else 0.0
    
    # Calculate True Range for each period
    true_ranges = []
    
    for i in range(1, len(highs)):
        # True Range = max of:
        # 1. Current High - Current Low
        # 2. |Current High - Previous Close|
        # 3. |Current Low - Previous Close|
        tr1 = highs[i] - lows[i]
        tr2 = abs(highs[i] - closes[i - 1])
        tr3 = abs(lows[i] - closes[i - 1])
        true_ranges.append(max(tr1, tr2, tr3))
    
    if len(true_ranges) < period:
        return sum(true_ranges) / len(true_ranges) if true_ranges else 0.0
    
    # Use Wilder's smoothing for ATR
    atr = sum(true_ranges[:period]) / period
    
    for i in range(period, len(true_ranges)):
        atr = (atr * (period - 1) + true_ranges[i]) / period
    
    return atr


def calc_volume_ratio(volumes: List[float], period: int = 20) -> float:
    """Calculate volume ratio (current vs average).
    
    Args:
        volumes: List of volume values (oldest to newest)
        period: Average period (default 20)
    
    Returns:
        Ratio of recent volume to average (e.g., 1.5 = 50% above average)
    """
    if not volumes or len(volumes) < 3:
        return 1.0
    
    # Recent volume (last 3 candles average)
    recent_vol = sum(volumes[-3:]) / 3
    
    # Average volume
    avg_period = min(period, len(volumes))
    avg_vol = sum(volumes[-avg_period:]) / avg_period
    
    if avg_vol == 0:
        return 1.0
    
    return recent_vol / avg_vol


def detect_price_action(
    highs: List[float],
    lows: List[float],
    lookback: int = 5,
) -> Tuple[bool, bool, bool, bool]:
    """Detect price action patterns (higher highs/lows, lower highs/lows).
    
    Args:
        highs: List of high prices
        lows: List of low prices
        lookback: Number of candles to compare
    
    Returns:
        Tuple of (higher_highs, higher_lows, lower_highs, lower_lows)
    """
    if len(highs) < lookback * 2 or len(lows) < lookback * 2:
        return False, False, False, False
    
    # Recent vs previous period
    recent_high = max(highs[-lookback:])
    prev_high = max(highs[-lookback * 2 : -lookback])
    recent_low = min(lows[-lookback:])
    prev_low = min(lows[-lookback * 2 : -lookback])
    
    higher_highs = recent_high > prev_high
    higher_lows = recent_low > prev_low
    lower_highs = recent_high < prev_high
    lower_lows = recent_low < prev_low
    
    return higher_highs, higher_lows, lower_highs, lower_lows
