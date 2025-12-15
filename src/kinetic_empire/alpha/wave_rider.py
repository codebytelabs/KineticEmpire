"""Wave Rider Strategy - Multi-timeframe trend following.

Captures extended trend moves using alignment across Daily, 4H, 1H, and 15m timeframes,
utilizing EMA 9/21 crossovers, RSI filters, and Volume confirmation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import pandas as pd
from pandas import DataFrame

from .models import TrendStrength, Signal


@dataclass
class WaveRiderConfig:
    """Configuration for Wave Rider strategy."""
    timeframes: List[str] = field(default_factory=lambda: ["1d", "4h", "1h", "15m"])
    entry_timeframe: str = "1h"  # Main timeframe for signals
    ema_fast: int = 9
    ema_slow: int = 21
    rsi_period: int = 14
    min_volume_ratio: float = 1.3
    
    # RSI Thresholds
    rsi_long_min: int = 40
    rsi_long_max: int = 65
    rsi_short_min: int = 35
    rsi_short_max: int = 60
    
    # Scoring
    min_score: int = 55


class WaveRiderStrategy:
    """Advanced trend following strategy."""
    
    def __init__(self, config: Optional[WaveRiderConfig] = None):
        self.config = config or WaveRiderConfig()
    
    def calculate_indicators(self, df: DataFrame) -> DataFrame:
        """Calculate technical indicators."""
        df = df.copy()
        
        # EMAs
        df['ema_fast'] = df['close'].ewm(span=self.config.ema_fast).mean()
        df['ema_slow'] = df['close'].ewm(span=self.config.ema_slow).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.config.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.config.rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(window=14).mean()
        
        return df

    def analyze_opportunity(self, pair: str, df: DataFrame) -> Tuple[int, int, List[str], List[str]]:
        """Score the opportunity for Long and Short."""
        if len(df) < 50:
            return 0, 0, [], []
            
        df = self.calculate_indicators(df)
        curr = df.iloc[-1]
        
        # 1. EMA Trend
        ema_fast = curr['ema_fast']
        ema_slow = curr['ema_slow']
        ema_trend = 'UP' if ema_fast > ema_slow else 'DOWN'
        ema_spread = (ema_fast - ema_slow) / ema_slow * 100
        
        # 2. RSI
        rsi = curr['rsi']
        
        # 3. Volume
        recent_vol = df['volume'].iloc[-3:].mean()
        avg_vol = df['volume'].iloc[-20:].mean()
        vol_ratio = recent_vol / avg_vol if avg_vol > 0 else 1.0
        
        # 4. Price Action
        recent_high = df['high'].iloc[-5:].max()
        prev_high = df['high'].iloc[-10:-5].max()
        recent_low = df['low'].iloc[-5:].min()
        prev_low = df['low'].iloc[-10:-5].min()
        
        hh = recent_high > prev_high
        hl = recent_low > prev_low
        lh = recent_high < prev_high
        ll = recent_low < prev_low
        
        dist_from_ema = (curr['close'] - ema_fast) / ema_fast * 100
        
        # --- SCORING ---
        long_score = 0
        short_score = 0
        long_reasons = []
        short_reasons = []
        
        # LONG Logic
        if ema_trend == 'UP' and ema_spread > 0.1:
            long_score += 30
            long_reasons.append(f"EMA↑{ema_spread:.1f}%")
            
            if self.config.rsi_long_min <= rsi <= self.config.rsi_long_max:
                long_score += 25
                long_reasons.append(f"RSI{rsi:.0f}")
            elif rsi < 40: # Oversold dip
                long_score += 35
                long_reasons.append(f"RSI↓{rsi:.0f}")
                
            if hh and hl:
                long_score += 20
                long_reasons.append("HH/HL")
                
            if -2 < dist_from_ema < 0.5: # Pullback
                long_score += 20
                long_reasons.append("pullback")
                
            if vol_ratio > self.config.min_volume_ratio:
                long_score += 10
                long_reasons.append(f"vol{vol_ratio:.1f}x")
        
        # SHORT Logic
        if ema_trend == 'DOWN' and abs(ema_spread) > 0.1:
            short_score += 30
            short_reasons.append(f"EMA↓{abs(ema_spread):.1f}%")
            
            if self.config.rsi_short_min <= rsi <= self.config.rsi_short_max:
                short_score += 25
                short_reasons.append(f"RSI{rsi:.0f}")
            elif rsi > 60: # Overbought rally
                short_score += 35
                short_reasons.append(f"RSI↑{rsi:.0f}")
                
            if lh and ll:
                short_score += 20
                short_reasons.append("LH/LL")
                
            if -0.5 < dist_from_ema < 2: # Rally to resistance
                short_score += 20
                short_reasons.append("rally")
                
            if vol_ratio > self.config.min_volume_ratio:
                short_score += 10
                short_reasons.append(f"vol{vol_ratio:.1f}x")
                
        return long_score, short_score, long_reasons, short_reasons

    def generate_signal(self, pair: str, timeframe_data: Dict[str, DataFrame]) -> Optional[Signal]:
        """Generate entry signal based on advanced scoring.
        
        Args:
            pair: Trading pair
            timeframe_data: Dict of timeframe -> DataFrame
            
        Returns:
            Signal or None
        """
        # Focus on entry timeframe (e.g., 1h)
        df = timeframe_data.get(self.config.entry_timeframe)
        if df is None:
            # Fallback to key
            keys = list(timeframe_data.keys())
            if not keys:
                return None
            df = timeframe_data[keys[0]]
            
        long_score, short_score, l_reasons, s_reasons = self.analyze_opportunity(pair, df)
        
        min_score = self.config.min_score
        
        signal_side = None
        strength = TrendStrength.NEUTRAL
        reasons = []
        score = 0
        
        if long_score >= min_score and long_score > short_score:
            signal_side = "LONG"
            score = long_score
            reasons = l_reasons
            strength = TrendStrength.STRONG_UPTREND if long_score > 75 else TrendStrength.WEAK_UPTREND
            
        elif short_score >= min_score and short_score > long_score:
            signal_side = "SHORT"
            score = short_score
            reasons = s_reasons
            strength = TrendStrength.STRONG_DOWNTREND if short_score > 75 else TrendStrength.WEAK_DOWNTREND
            
        if signal_side:
            # Calculate dynamic stop (2 ATR)
            curr = df.iloc[-1]
            atr = curr['atr'] if 'atr' in curr else (curr['close'] * 0.02) # Fallback
            
            stop_loss = curr['close'] - (2 * atr) if signal_side == "LONG" else curr['close'] + (2 * atr)
            
            # Construct human readable reason
            reason_str = f"{signal_side} ({score}): " + " ".join(reasons)
            
            return Signal(
                pair=pair,
                side=signal_side,
                strategy="wave_rider",
                strength=strength,
                entry_price=curr['close'],
                stop_loss=stop_loss,
                metadata={"score": score, "reasons": reasons, "desc": reason_str}
            )
            
        return None
