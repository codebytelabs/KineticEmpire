"""Intelligent Futures Pair Scanner and Ranker.

Ranks trading pairs based on:
1. Range-bound score (best for grid trading)
2. Volume/liquidity score
3. Volatility score (ATR, BB width)
4. Trend strength (ADX - lower is better for grid)
5. Upside potential score

Allocates position sizes based on composite quality score.
"""
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .client import BinanceFuturesClient

logger = logging.getLogger(__name__)


@dataclass
class PairScore:
    """Comprehensive score for a trading pair."""
    symbol: str
    
    # Individual scores (0-100)
    range_score: float = 0.0      # How range-bound (higher = better for grid)
    volume_score: float = 0.0     # Liquidity score
    volatility_score: float = 0.0 # Optimal volatility (not too high/low)
    trend_score: float = 0.0      # Lower trend = better for grid
    upside_score: float = 0.0     # Potential for profit
    
    # Composite score
    total_score: float = 0.0
    grade: str = "F"
    
    # Recommended allocation
    allocation_pct: float = 0.0
    recommended_leverage: int = 1
    grid_type: str = "NEUTRAL"  # LONG, SHORT, or NEUTRAL
    
    # Market data
    current_price: float = 0.0
    atr: float = 0.0
    atr_pct: float = 0.0
    volume_24h: float = 0.0
    change_24h: float = 0.0
    
    # Range data
    support: float = 0.0
    resistance: float = 0.0
    range_pct: float = 0.0


class FuturesPairScanner:
    """Scans and ranks futures pairs for grid trading."""
    
    # Scoring weights
    WEIGHTS = {
        'range': 0.25,      # Range-bound is most important for grid
        'volume': 0.20,     # Need liquidity
        'volatility': 0.20, # Need some volatility but not too much
        'trend': 0.20,      # Lower trend strength = better
        'upside': 0.15      # Potential profit
    }
    
    # Grade thresholds
    GRADES = {
        90: 'A+', 85: 'A', 80: 'A-',
        75: 'B+', 70: 'B', 65: 'B-',
        60: 'C+', 55: 'C', 50: 'C-',
        40: 'D', 0: 'F'
    }
    
    def __init__(self, client: BinanceFuturesClient):
        self.client = client
        self.pair_scores: Dict[str, PairScore] = {}
        
    def get_tradeable_pairs(self) -> List[str]:
        """Get list of tradeable USDT perpetual pairs."""
        # Top futures pairs by volume
        top_pairs = [
            'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT',
            'DOGEUSDT', 'ADAUSDT', 'AVAXUSDT', 'DOTUSDT', 'LINKUSDT',
            'MATICUSDT', 'LTCUSDT', 'ATOMUSDT', 'UNIUSDT', 'APTUSDT',
            'ARBUSDT', 'OPUSDT', 'NEARUSDT', 'FILUSDT', 'INJUSDT'
        ]
        return top_pairs
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators for scoring."""
        # EMA
        df['ema_9'] = df['close'].ewm(span=9).mean()
        df['ema_21'] = df['close'].ewm(span=21).mean()
        df['ema_50'] = df['close'].ewm(span=50).mean()
        
        # ATR (Average True Range)
        df['tr'] = pd.concat([
            df['high'] - df['low'],
            abs(df['high'] - df['close'].shift()),
            abs(df['low'] - df['close'].shift())
        ], axis=1).max(axis=1)
        df['atr'] = df['tr'].rolling(14).mean()
        df['atr_pct'] = (df['atr'] / df['close']) * 100
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        df['bb_mid'] = df['close'].rolling(20).mean()
        df['bb_std'] = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_mid'] + (df['bb_std'] * 2)
        df['bb_lower'] = df['bb_mid'] - (df['bb_std'] * 2)
        df['bb_width'] = ((df['bb_upper'] - df['bb_lower']) / df['bb_mid']) * 100
        
        # ADX (Average Directional Index)
        df['plus_dm'] = np.where(
            (df['high'] - df['high'].shift()) > (df['low'].shift() - df['low']),
            np.maximum(df['high'] - df['high'].shift(), 0), 0
        )
        df['minus_dm'] = np.where(
            (df['low'].shift() - df['low']) > (df['high'] - df['high'].shift()),
            np.maximum(df['low'].shift() - df['low'], 0), 0
        )
        df['plus_di'] = 100 * (df['plus_dm'].rolling(14).mean() / df['atr'])
        df['minus_di'] = 100 * (df['minus_dm'].rolling(14).mean() / df['atr'])
        df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
        df['adx'] = df['dx'].rolling(14).mean()
        
        # Support/Resistance (recent highs/lows)
        df['support'] = df['low'].rolling(20).min()
        df['resistance'] = df['high'].rolling(20).max()
        df['range_pct'] = ((df['resistance'] - df['support']) / df['close']) * 100
        
        # Volume metrics
        df['volume_sma'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        return df
    
    def score_range_bound(self, df: pd.DataFrame) -> float:
        """Score how range-bound the pair is (higher = better for grid).
        
        Factors:
        - RSI oscillating between 30-70 (not stuck at extremes)
        - Price staying within Bollinger Bands
        - Low ADX (no strong trend)
        """
        latest = df.iloc[-1]
        
        # RSI score: Best when oscillating 30-70
        rsi = latest['rsi']
        if 40 <= rsi <= 60:
            rsi_score = 100  # Perfect middle
        elif 30 <= rsi <= 70:
            rsi_score = 80   # Good range
        else:
            rsi_score = max(0, 60 - abs(rsi - 50))  # Penalize extremes
        
        # ADX score: Lower = more range-bound
        adx = latest['adx'] if not pd.isna(latest['adx']) else 25
        if adx < 20:
            adx_score = 100  # Very range-bound
        elif adx < 25:
            adx_score = 80   # Moderately range-bound
        elif adx < 30:
            adx_score = 60   # Weak trend
        elif adx < 40:
            adx_score = 40   # Moderate trend
        else:
            adx_score = 20   # Strong trend (bad for grid)
        
        # BB width score: Moderate width is best
        bb_width = latest['bb_width']
        if 2 <= bb_width <= 5:
            bb_score = 100  # Optimal volatility
        elif 1 <= bb_width <= 8:
            bb_score = 70   # Acceptable
        else:
            bb_score = 40   # Too tight or too wide
        
        # Combine scores
        return (rsi_score * 0.3) + (adx_score * 0.5) + (bb_score * 0.2)
    
    def score_volume(self, df: pd.DataFrame, ticker: dict) -> float:
        """Score liquidity/volume (higher = better)."""
        volume_24h = ticker.get('volume', 0)
        
        # Volume tiers (in millions USD)
        if volume_24h > 1_000_000_000:  # >$1B
            return 100
        elif volume_24h > 500_000_000:  # >$500M
            return 90
        elif volume_24h > 100_000_000:  # >$100M
            return 80
        elif volume_24h > 50_000_000:   # >$50M
            return 70
        elif volume_24h > 10_000_000:   # >$10M
            return 60
        elif volume_24h > 1_000_000:    # >$1M
            return 40
        else:
            return 20
    
    def score_volatility(self, df: pd.DataFrame) -> float:
        """Score volatility (optimal range is best for grid).
        
        Too low = not enough profit per grid
        Too high = risk of liquidation
        """
        latest = df.iloc[-1]
        atr_pct = latest['atr_pct']
        
        # Optimal ATR% for grid trading: 1-4%
        if 1.5 <= atr_pct <= 3.0:
            return 100  # Perfect volatility
        elif 1.0 <= atr_pct <= 4.0:
            return 80   # Good volatility
        elif 0.5 <= atr_pct <= 5.0:
            return 60   # Acceptable
        elif atr_pct < 0.5:
            return 30   # Too low (boring)
        else:
            return 40   # Too high (risky)
    
    def score_trend(self, df: pd.DataFrame) -> float:
        """Score trend strength (lower trend = better for grid).
        
        Grid trading works best in sideways markets.
        """
        latest = df.iloc[-1]
        
        # EMA alignment score
        ema_9 = latest['ema_9']
        ema_21 = latest['ema_21']
        ema_50 = latest['ema_50']
        price = latest['close']
        
        # Check if EMAs are converging (sideways) or diverging (trending)
        ema_spread = abs(ema_9 - ema_50) / price * 100
        
        if ema_spread < 1:
            ema_score = 100  # EMAs very close = sideways
        elif ema_spread < 2:
            ema_score = 80
        elif ema_spread < 3:
            ema_score = 60
        elif ema_spread < 5:
            ema_score = 40
        else:
            ema_score = 20   # Strong trend
        
        # ADX component
        adx = latest['adx'] if not pd.isna(latest['adx']) else 25
        adx_score = max(0, 100 - (adx * 2))  # Lower ADX = higher score
        
        return (ema_score * 0.5) + (adx_score * 0.5)
    
    def score_upside(self, df: pd.DataFrame, ticker: dict) -> float:
        """Score upside potential.
        
        Factors:
        - Distance from support (closer = more upside)
        - Recent momentum
        - Funding rate (negative = potential squeeze)
        """
        latest = df.iloc[-1]
        price = latest['close']
        support = latest['support']
        resistance = latest['resistance']
        
        # Position in range (0 = at support, 100 = at resistance)
        if resistance > support:
            position_in_range = ((price - support) / (resistance - support)) * 100
        else:
            position_in_range = 50
        
        # Score: Better when closer to support (more upside)
        if position_in_range < 30:
            position_score = 100  # Near support = high upside
        elif position_in_range < 50:
            position_score = 80
        elif position_in_range < 70:
            position_score = 60
        else:
            position_score = 40   # Near resistance = limited upside
        
        # Momentum score (RSI)
        rsi = latest['rsi']
        if rsi < 35:
            momentum_score = 90  # Oversold = potential bounce
        elif rsi < 45:
            momentum_score = 70
        elif rsi < 55:
            momentum_score = 50
        elif rsi < 65:
            momentum_score = 40
        else:
            momentum_score = 30  # Overbought
        
        return (position_score * 0.6) + (momentum_score * 0.4)
    
    def calculate_allocation(self, score: float) -> Tuple[float, int]:
        """Calculate position allocation and leverage based on score.
        
        Returns:
            (allocation_pct, leverage)
        """
        if score >= 85:
            return 5.0, 3   # A grade: 5% allocation, 3x leverage
        elif score >= 75:
            return 4.0, 3   # B+ grade: 4% allocation, 3x leverage
        elif score >= 65:
            return 3.0, 2   # B grade: 3% allocation, 2x leverage
        elif score >= 55:
            return 2.0, 2   # C+ grade: 2% allocation, 2x leverage
        elif score >= 45:
            return 1.0, 2   # C grade: 1% allocation, 2x leverage
        else:
            return 0.0, 1   # Don't trade
    
    def determine_grid_type(self, df: pd.DataFrame) -> str:
        """Determine optimal grid type based on market conditions.
        
        Returns:
            'LONG' - Bullish bias
            'SHORT' - Bearish bias
            'NEUTRAL' - No bias (both directions)
        """
        latest = df.iloc[-1]
        
        # Check trend direction
        ema_9 = latest['ema_9']
        ema_21 = latest['ema_21']
        ema_50 = latest['ema_50']
        price = latest['close']
        rsi = latest['rsi']
        
        bullish_signals = 0
        bearish_signals = 0
        
        # EMA alignment
        if ema_9 > ema_21 > ema_50:
            bullish_signals += 2
        elif ema_9 < ema_21 < ema_50:
            bearish_signals += 2
        
        # Price vs EMA50
        if price > ema_50:
            bullish_signals += 1
        else:
            bearish_signals += 1
        
        # RSI
        if rsi < 40:
            bullish_signals += 1  # Oversold = potential bounce
        elif rsi > 60:
            bearish_signals += 1  # Overbought = potential drop
        
        # Determine type
        if bullish_signals >= 3 and bearish_signals <= 1:
            return 'LONG'
        elif bearish_signals >= 3 and bullish_signals <= 1:
            return 'SHORT'
        else:
            return 'NEUTRAL'
    
    def get_grade(self, score: float) -> str:
        """Convert score to letter grade."""
        for threshold, grade in sorted(self.GRADES.items(), reverse=True):
            if score >= threshold:
                return grade
        return 'F'
    
    def scan_pair(self, symbol: str) -> Optional[PairScore]:
        """Scan and score a single pair."""
        try:
            # Get market data
            klines = self.client.get_klines(symbol, '4h', 100)
            df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Calculate indicators
            df = self.calculate_indicators(df)
            
            # Get ticker
            ticker = self.client.get_ticker(symbol)
            
            # Calculate individual scores
            range_score = self.score_range_bound(df)
            volume_score = self.score_volume(df, ticker)
            volatility_score = self.score_volatility(df)
            trend_score = self.score_trend(df)
            upside_score = self.score_upside(df, ticker)
            
            # Calculate weighted total
            total_score = (
                range_score * self.WEIGHTS['range'] +
                volume_score * self.WEIGHTS['volume'] +
                volatility_score * self.WEIGHTS['volatility'] +
                trend_score * self.WEIGHTS['trend'] +
                upside_score * self.WEIGHTS['upside']
            )
            
            # Get allocation and leverage
            allocation_pct, leverage = self.calculate_allocation(total_score)
            
            # Determine grid type
            grid_type = self.determine_grid_type(df)
            
            # Get latest data
            latest = df.iloc[-1]
            
            # Create score object
            score = PairScore(
                symbol=symbol,
                range_score=range_score,
                volume_score=volume_score,
                volatility_score=volatility_score,
                trend_score=trend_score,
                upside_score=upside_score,
                total_score=total_score,
                grade=self.get_grade(total_score),
                allocation_pct=allocation_pct,
                recommended_leverage=leverage,
                grid_type=grid_type,
                current_price=latest['close'],
                atr=latest['atr'],
                atr_pct=latest['atr_pct'],
                volume_24h=ticker.get('volume', 0),
                change_24h=ticker.get('change_pct', 0),
                support=latest['support'],
                resistance=latest['resistance'],
                range_pct=latest['range_pct']
            )
            
            self.pair_scores[symbol] = score
            return score
            
        except Exception as e:
            logger.error(f"Error scanning {symbol}: {e}")
            return None
    
    def scan_all_pairs(self) -> List[PairScore]:
        """Scan all tradeable pairs and return ranked list."""
        pairs = self.get_tradeable_pairs()
        scores = []
        
        logger.info(f"Scanning {len(pairs)} pairs...")
        
        for symbol in pairs:
            score = self.scan_pair(symbol)
            if score and score.total_score >= 40:  # Minimum threshold
                scores.append(score)
        
        # Sort by total score (descending)
        scores.sort(key=lambda x: x.total_score, reverse=True)
        
        logger.info(f"Found {len(scores)} tradeable pairs")
        return scores
    
    def get_top_pairs(self, n: int = 5) -> List[PairScore]:
        """Get top N pairs by score."""
        all_scores = self.scan_all_pairs()
        return all_scores[:n]
    
    def print_rankings(self, scores: List[PairScore]):
        """Print formatted rankings table."""
        print("\n" + "=" * 100)
        print("🏆 PAIR RANKINGS FOR GRID TRADING")
        print("=" * 100)
        print(f"{'Rank':<5} {'Symbol':<12} {'Grade':<6} {'Score':<8} {'Range':<8} {'Vol':<8} {'Volat':<8} {'Trend':<8} {'Alloc':<8} {'Type':<10}")
        print("-" * 100)
        
        for i, s in enumerate(scores, 1):
            print(f"{i:<5} {s.symbol:<12} {s.grade:<6} {s.total_score:<8.1f} "
                  f"{s.range_score:<8.1f} {s.volume_score:<8.1f} {s.volatility_score:<8.1f} "
                  f"{s.trend_score:<8.1f} {s.allocation_pct:<8.1f}% {s.grid_type:<10}")
        
        print("=" * 100)
