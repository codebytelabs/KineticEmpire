"""Technical Analyzer for Kinetic Empire v3.0.

Multi-timeframe analysis and signal generation.
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from src.kinetic_empire.v3.core.models import OHLCV, Indicators, Signal
from src.kinetic_empire.v3.analyzer.indicators import (
    calc_ema,
    calc_rsi,
    calc_macd,
    calc_atr,
    calc_volume_ratio,
    detect_price_action,
)

logger = logging.getLogger(__name__)


class TAAnalyzer:
    """Multi-timeframe technical analyzer.
    
    Analyzes opportunities using:
    - EMA(9/21) trend detection
    - RSI(14) momentum
    - MACD(12,26,9) confirmation
    - ATR(14) volatility
    - Volume ratio analysis
    """

    def __init__(
        self,
        min_score: int = 60,
        max_stop_loss_pct: float = 3.0,
        risk_reward_ratio: float = 1.5,
    ):
        """Initialize analyzer.
        
        Args:
            min_score: Minimum confidence score to generate signal
            max_stop_loss_pct: Maximum stop loss distance (%)
            risk_reward_ratio: Target risk-reward ratio
        """
        self.min_score = min_score
        self.max_stop_loss_pct = max_stop_loss_pct
        self.risk_reward_ratio = risk_reward_ratio
        
        # Scoring weights (must sum to 100)
        self.weights = {
            "trend_4h": 25,
            "trend_1h": 20,
            "rsi_zone": 15,
            "macd_cross": 15,
            "volume_spike": 10,
            "price_action": 15,
        }

    def calculate_indicators(self, ohlcv: List[OHLCV]) -> Indicators:
        """Calculate all indicators for OHLCV data.
        
        Args:
            ohlcv: List of OHLCV candles (oldest first)
            
        Returns:
            Indicators dataclass with all calculated values
        """
        if len(ohlcv) < 30:
            raise ValueError(f"Insufficient data: need 30 candles, got {len(ohlcv)}")
        
        # Extract price arrays
        closes = [c.close for c in ohlcv]
        highs = [c.high for c in ohlcv]
        lows = [c.low for c in ohlcv]
        volumes = [c.volume for c in ohlcv]
        
        # Calculate indicators
        ema_9 = calc_ema(closes, 9)
        ema_21 = calc_ema(closes, 21)
        rsi = calc_rsi(closes, 14)
        macd_line, macd_signal, macd_histogram = calc_macd(closes, 12, 26, 9)
        atr = calc_atr(highs, lows, closes, 14)
        volume_ratio = calc_volume_ratio(volumes, 20)
        
        return Indicators(
            ema_9=ema_9,
            ema_21=ema_21,
            rsi=rsi,
            macd_line=macd_line,
            macd_signal=macd_signal,
            macd_histogram=macd_histogram,
            atr=atr,
            volume_ratio=volume_ratio,
        )

    def score_opportunity(
        self,
        ind_4h: Indicators,
        ind_1h: Indicators,
        ind_15m: Indicators,
    ) -> Tuple[int, int, str]:
        """Score opportunity based on multi-timeframe analysis.
        
        Args:
            ind_4h: 4-hour timeframe indicators
            ind_1h: 1-hour timeframe indicators
            ind_15m: 15-minute timeframe indicators
            
        Returns:
            Tuple of (long_score, short_score, direction)
        """
        long_score = 0
        short_score = 0
        
        # 4H EMA Trend (25 points)
        if ind_4h.ema_trend == "UP":
            long_score += self.weights["trend_4h"]
        else:
            short_score += self.weights["trend_4h"]
        
        # 1H Trend Alignment (20 points)
        if ind_4h.ema_trend == ind_1h.ema_trend:
            if ind_4h.ema_trend == "UP":
                long_score += self.weights["trend_1h"]
            else:
                short_score += self.weights["trend_1h"]
        
        # RSI Zone (15 points)
        # Long: RSI 30-45 (optimal buy zone)
        # Short: RSI 55-70 (optimal sell zone)
        if 30 <= ind_1h.rsi <= 45:
            long_score += self.weights["rsi_zone"]
        elif 55 <= ind_1h.rsi <= 70:
            short_score += self.weights["rsi_zone"]
        
        # MACD Cross (15 points)
        if ind_1h.macd_line > ind_1h.macd_signal:
            long_score += self.weights["macd_cross"]
        else:
            short_score += self.weights["macd_cross"]
        
        # Volume Spike (10 points)
        if ind_1h.volume_ratio >= 1.5:
            # Add to dominant direction
            if long_score > short_score:
                long_score += self.weights["volume_spike"]
            else:
                short_score += self.weights["volume_spike"]
        
        # Price Action (15 points) - based on 15m for entry timing
        # This is simplified - real implementation would use detect_price_action
        if ind_15m.ema_trend == "UP" and ind_15m.macd_histogram > 0:
            long_score += self.weights["price_action"]
        elif ind_15m.ema_trend == "DOWN" and ind_15m.macd_histogram < 0:
            short_score += self.weights["price_action"]
        
        # Determine direction
        if long_score > short_score:
            direction = "LONG"
            confidence = long_score
        else:
            direction = "SHORT"
            confidence = short_score
        
        return long_score, short_score, direction

    def calculate_entry_exit(
        self,
        entry_price: float,
        atr: float,
        direction: str,
    ) -> Tuple[float, float, float]:
        """Calculate entry, stop loss, and take profit levels.
        
        Args:
            entry_price: Current price for entry
            atr: ATR value for volatility-based stops
            direction: "LONG" or "SHORT"
            
        Returns:
            Tuple of (entry_price, stop_loss, take_profit)
        """
        # Stop loss = 2x ATR, capped at 3%
        stop_distance = min(2 * atr, entry_price * (self.max_stop_loss_pct / 100))
        
        if direction == "LONG":
            stop_loss = entry_price - stop_distance
            take_profit = entry_price + (stop_distance * self.risk_reward_ratio)
        else:  # SHORT
            stop_loss = entry_price + stop_distance
            take_profit = entry_price - (stop_distance * self.risk_reward_ratio)
        
        return entry_price, stop_loss, take_profit

    def generate_signal(
        self,
        symbol: str,
        current_price: float,
        ohlcv_4h: List[OHLCV],
        ohlcv_1h: List[OHLCV],
        ohlcv_15m: List[OHLCV],
    ) -> Optional[Signal]:
        """Generate trading signal from multi-timeframe analysis.
        
        Args:
            symbol: Trading pair symbol
            current_price: Current market price
            ohlcv_4h: 4-hour OHLCV data
            ohlcv_1h: 1-hour OHLCV data
            ohlcv_15m: 15-minute OHLCV data
            
        Returns:
            Signal if confidence >= min_score, None otherwise
        """
        try:
            logger.debug(f"         🧮 {symbol}: Calculating indicators...")
            
            # Calculate indicators for each timeframe
            ind_4h = self.calculate_indicators(ohlcv_4h)
            ind_1h = self.calculate_indicators(ohlcv_1h)
            ind_15m = self.calculate_indicators(ohlcv_15m)
            
            logger.debug(f"         📊 {symbol} 4H: EMA9={ind_4h.ema_9:.4f}, EMA21={ind_4h.ema_21:.4f}, RSI={ind_4h.rsi:.1f}, Trend={ind_4h.ema_trend}")
            logger.debug(f"         📊 {symbol} 1H: EMA9={ind_1h.ema_9:.4f}, EMA21={ind_1h.ema_21:.4f}, RSI={ind_1h.rsi:.1f}, Trend={ind_1h.ema_trend}")
            logger.debug(f"         📊 {symbol} 15M: EMA9={ind_15m.ema_9:.4f}, EMA21={ind_15m.ema_21:.4f}, RSI={ind_15m.rsi:.1f}, Trend={ind_15m.ema_trend}")
            
            # Score the opportunity
            long_score, short_score, direction = self.score_opportunity(
                ind_4h, ind_1h, ind_15m
            )
            
            confidence = max(long_score, short_score)
            
            logger.debug(f"         🎯 {symbol}: LONG={long_score}, SHORT={short_score} → {direction} (conf={confidence})")
            
            # Check minimum score
            if confidence < self.min_score:
                logger.debug(
                    f"         ❌ {symbol}: Score {confidence} < min {self.min_score} - NO SIGNAL"
                )
                return None
            
            # Calculate entry/exit levels
            entry_price, stop_loss, take_profit = self.calculate_entry_exit(
                current_price, ind_1h.atr, direction
            )
            
            logger.debug(f"         📐 {symbol}: Entry=${entry_price:.4f}, SL=${stop_loss:.4f}, TP=${take_profit:.4f}, ATR={ind_1h.atr:.4f}")
            
            # Check timeframe alignment
            timeframe_alignment = ind_4h.ema_trend == ind_1h.ema_trend
            logger.debug(f"         🔗 {symbol}: Timeframe alignment: {timeframe_alignment} (4H={ind_4h.ema_trend}, 1H={ind_1h.ema_trend})")
            
            # Create signal
            signal = Signal(
                symbol=symbol,
                direction=direction,
                confidence=confidence,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                atr=ind_1h.atr,
                timeframe_alignment=timeframe_alignment,
                indicators={
                    "4h": ind_4h,
                    "1h": ind_1h,
                    "15m": ind_15m,
                },
            )
            
            # Validate signal
            if not signal.validate():
                logger.warning(f"         ⚠️  {symbol}: Signal validation failed")
                return None
            
            logger.info(
                f"         ✅ {symbol}: SIGNAL GENERATED - {direction} @ ${entry_price:.4f} (conf={confidence}%)"
            )
            return signal
            
        except Exception as e:
            logger.error(f"         ❌ {symbol}: Error generating signal: {e}")
            return None

    async def analyze(
        self,
        symbol: str,
        current_price: float,
        ohlcv_4h: List[OHLCV],
        ohlcv_1h: List[OHLCV],
        ohlcv_15m: List[OHLCV],
    ) -> Optional[Signal]:
        """Async wrapper for signal generation.
        
        Args:
            symbol: Trading pair symbol
            current_price: Current market price
            ohlcv_4h: 4-hour OHLCV data
            ohlcv_1h: 1-hour OHLCV data
            ohlcv_15m: 15-minute OHLCV data
            
        Returns:
            Signal if valid opportunity found, None otherwise
        """
        return self.generate_signal(
            symbol, current_price, ohlcv_4h, ohlcv_1h, ohlcv_15m
        )
