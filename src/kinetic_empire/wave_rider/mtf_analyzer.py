"""Multi-Timeframe Analyzer for Wave Rider.

Analyzes trend direction across multiple timeframes (1m, 5m, 15m):
- Calculates EMA (9 and 21 period)
- Calculates RSI (14 period)
- Calculates VWAP
- Determines trend direction per timeframe
- Calculates alignment score (40/70/100)
"""

from typing import Dict, List, Optional
from .models import OHLCV, TimeframeAnalysis, MTFResult, TrendDirection, WaveRiderConfig


class MTFAnalyzer:
    """Multi-Timeframe Analyzer for trend alignment.
    
    Analyzes 1m, 5m, and 15m timeframes to determine:
    - Trend direction per timeframe (BULLISH/BEARISH/NEUTRAL)
    - Alignment score based on agreement
    - Dominant direction across timeframes
    """
    
    TIMEFRAMES = ["1m", "5m", "15m"]
    EMA_FAST_PERIOD = 9
    EMA_SLOW_PERIOD = 21
    RSI_PERIOD = 14
    
    def __init__(self, config: Optional[WaveRiderConfig] = None):
        """Initialize the MTF analyzer.
        
        Args:
            config: Wave Rider configuration
        """
        self.config = config or WaveRiderConfig()
    
    def analyze(self, symbol: str, ohlcv_data: Dict[str, List[OHLCV]]) -> MTFResult:
        """Perform multi-timeframe analysis.
        
        Args:
            symbol: Trading pair symbol
            ohlcv_data: Dict of OHLCV lists keyed by timeframe ("1m", "5m", "15m")
        
        Returns:
            MTFResult with all analyses and alignment score
        """
        analyses: Dict[str, TimeframeAnalysis] = {}
        
        for tf in self.TIMEFRAMES:
            candles = ohlcv_data.get(tf, [])
            if len(candles) < self.EMA_SLOW_PERIOD:
                # Not enough data, create neutral analysis
                analyses[tf] = TimeframeAnalysis(
                    timeframe=tf,
                    ema_fast=0.0,
                    ema_slow=0.0,
                    rsi=50.0,
                    vwap=0.0,
                    trend_direction=TrendDirection.NEUTRAL,
                    price=candles[-1].close if candles else 0.0,
                )
            else:
                analyses[tf] = self._analyze_timeframe(tf, candles)
        
        # Calculate alignment score
        alignment_score = self.calculate_alignment_score(analyses)
        
        # Determine dominant direction
        dominant_direction = self._get_dominant_direction(analyses)
        
        # Determine price vs VWAP (use 1m for most recent)
        price_vs_vwap = self._get_price_vs_vwap(analyses)
        
        return MTFResult(
            analyses=analyses,
            alignment_score=alignment_score,
            dominant_direction=dominant_direction,
            price_vs_vwap=price_vs_vwap,
        )
    
    def _analyze_timeframe(self, timeframe: str, candles: List[OHLCV]) -> TimeframeAnalysis:
        """Analyze a single timeframe.
        
        Args:
            timeframe: Timeframe string
            candles: List of OHLCV candles
        
        Returns:
            TimeframeAnalysis for this timeframe
        """
        closes = [c.close for c in candles]
        current_price = closes[-1]
        
        # Calculate EMAs
        ema_fast = self._calculate_ema(closes, self.EMA_FAST_PERIOD)
        ema_slow = self._calculate_ema(closes, self.EMA_SLOW_PERIOD)
        
        # Calculate RSI
        rsi = self._calculate_rsi(closes, self.RSI_PERIOD)
        
        # Calculate VWAP
        vwap = self._calculate_vwap(candles)
        
        # Determine trend direction
        trend_direction = self.determine_trend_direction(ema_fast, ema_slow, current_price)
        
        return TimeframeAnalysis(
            timeframe=timeframe,
            ema_fast=ema_fast,
            ema_slow=ema_slow,
            rsi=rsi,
            vwap=vwap,
            trend_direction=trend_direction,
            price=current_price,
        )
    
    def determine_trend_direction(
        self,
        ema_fast: float,
        ema_slow: float,
        price: float,
    ) -> TrendDirection:
        """Determine trend direction for a single timeframe.
        
        Property 4: Trend Direction Classification
        - BULLISH: EMA_fast > EMA_slow AND price > EMA_fast
        - BEARISH: EMA_fast < EMA_slow AND price < EMA_slow
        - NEUTRAL: otherwise
        
        Args:
            ema_fast: 9-period EMA
            ema_slow: 21-period EMA
            price: Current price
        
        Returns:
            TrendDirection enum value
        """
        if ema_fast > ema_slow and price > ema_fast:
            return TrendDirection.BULLISH
        elif ema_fast < ema_slow and price < ema_slow:
            return TrendDirection.BEARISH
        else:
            return TrendDirection.NEUTRAL
    
    def calculate_alignment_score(self, analyses: Dict[str, TimeframeAnalysis]) -> int:
        """Calculate alignment score based on trend agreement.
        
        Property 5: Alignment Score Calculation
        - 100 points if all 3 timeframes agree on direction (non-NEUTRAL)
        - 70 points if exactly 2 timeframes agree on direction (non-NEUTRAL)
        - 40 points otherwise
        
        Args:
            analyses: Dict of TimeframeAnalysis keyed by timeframe
        
        Returns:
            Alignment score (40, 70, or 100)
        """
        directions = [a.trend_direction for a in analyses.values()]
        
        # Count non-neutral directions
        bullish_count = sum(1 for d in directions if d == TrendDirection.BULLISH)
        bearish_count = sum(1 for d in directions if d == TrendDirection.BEARISH)
        
        # All 3 agree on same non-neutral direction
        if bullish_count == 3 or bearish_count == 3:
            return 100
        
        # 2 of 3 agree on same non-neutral direction
        if bullish_count == 2 or bearish_count == 2:
            return 70
        
        # Otherwise (mixed or all neutral)
        return 40
    
    def _get_dominant_direction(self, analyses: Dict[str, TimeframeAnalysis]) -> TrendDirection:
        """Get the dominant (most common) non-neutral direction.
        
        Args:
            analyses: Dict of TimeframeAnalysis
        
        Returns:
            Most common non-neutral direction, or NEUTRAL if tied/all neutral
        """
        directions = [a.trend_direction for a in analyses.values()]
        
        bullish_count = sum(1 for d in directions if d == TrendDirection.BULLISH)
        bearish_count = sum(1 for d in directions if d == TrendDirection.BEARISH)
        
        if bullish_count > bearish_count:
            return TrendDirection.BULLISH
        elif bearish_count > bullish_count:
            return TrendDirection.BEARISH
        else:
            return TrendDirection.NEUTRAL
    
    def _get_price_vs_vwap(self, analyses: Dict[str, TimeframeAnalysis]) -> str:
        """Determine if price is above or below VWAP.
        
        Uses the 1m timeframe for most recent data.
        
        Args:
            analyses: Dict of TimeframeAnalysis
        
        Returns:
            "ABOVE" or "BELOW"
        """
        # Use 1m for most recent price/VWAP
        analysis_1m = analyses.get("1m")
        if analysis_1m and analysis_1m.vwap > 0:
            return "ABOVE" if analysis_1m.price >= analysis_1m.vwap else "BELOW"
        return "ABOVE"  # Default
    
    def _calculate_ema(self, values: List[float], period: int) -> float:
        """Calculate Exponential Moving Average.
        
        Args:
            values: List of values (closes)
            period: EMA period
        
        Returns:
            EMA value
        """
        if len(values) < period:
            return values[-1] if values else 0.0
        
        multiplier = 2 / (period + 1)
        
        # Start with SMA for first period
        ema = sum(values[:period]) / period
        
        # Calculate EMA for remaining values
        for value in values[period:]:
            ema = (value - ema) * multiplier + ema
        
        return ema
    
    def _calculate_rsi(self, closes: List[float], period: int = 14) -> float:
        """Calculate Relative Strength Index.
        
        Args:
            closes: List of closing prices
            period: RSI period (default 14)
        
        Returns:
            RSI value (0-100)
        """
        if len(closes) < period + 1:
            return 50.0  # Neutral default
        
        # Calculate price changes
        changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        
        # Separate gains and losses
        gains = [max(0, c) for c in changes]
        losses = [abs(min(0, c)) for c in changes]
        
        # Calculate average gain/loss for first period
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        # Smooth for remaining periods
        for i in range(period, len(changes)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_vwap(self, candles: List[OHLCV]) -> float:
        """Calculate Volume Weighted Average Price.
        
        Args:
            candles: List of OHLCV candles
        
        Returns:
            VWAP value
        """
        if not candles:
            return 0.0
        
        total_volume = sum(c.volume for c in candles)
        if total_volume == 0:
            return candles[-1].close
        
        # Typical price = (high + low + close) / 3
        vwap_sum = sum(
            ((c.high + c.low + c.close) / 3) * c.volume
            for c in candles
        )
        
        return vwap_sum / total_volume
