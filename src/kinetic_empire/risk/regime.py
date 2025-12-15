"""Regime classification module for market condition detection.

Classifies market regime based on BTC price relative to EMA50 to determine
appropriate position limits and risk exposure.
"""

from typing import Optional
from kinetic_empire.models import Regime
from .fear_greed import FearGreedFetcher

class RegimeClassifier:
    """Classifies market regime based on BTC trend and Fear & Greed Index.
    
    The regime determines maximum concurrent trades:
    - BULL (BTC > EMA50): Max 20 trades
    - BEAR (BTC < EMA50): Max 3 trades
    
    Fear & Greed adjusts the aggression:
    - EXTREME FEAR (<20): Reduce limits, be conservative
    - GREED (>70): Increase exposure (smartly)
    """

    # Trade limits per regime
    BULL_MAX_TRADES = 20
    BEAR_MAX_TRADES = 3
    
    # Fear & Greed thresholds
    EXTREME_FEAR = 20
    FEAR = 40
    GREED = 60
    EXTREME_GREED = 80

    def __init__(self, btc_pair: str = "BTC/USDT", ema_period: int = 50):
        """Initialize regime classifier.
        
        Args:
            btc_pair: BTC trading pair for regime detection
            ema_period: EMA period for trend detection (default 50)
        """
        self.btc_pair = btc_pair
        self.ema_period = ema_period
        self.fg_fetcher = FearGreedFetcher()
        self.last_fg_index: Optional[int] = None

    def classify(self, btc_close: float, btc_ema50: float) -> Regime:
        """Classify market regime based on BTC price vs EMA50.
        
        Args:
            btc_close: Current BTC daily close price
            btc_ema50: BTC 50-period EMA value
            
        Returns:
            Regime.BULL if close > ema50, Regime.BEAR otherwise
        """
        # Fetch Fear & Greed occasionally (cached by logic if needed, but here simple fetch)
        fg_data = self.fg_fetcher.fetch()
        if fg_data:
            self.last_fg_index = fg_data.value
            
        if btc_close > btc_ema50:
            return Regime.BULL
        return Regime.BEAR

    def get_max_trades(self, regime: Regime) -> int:
        """Get maximum allowed concurrent trades for regime, adjusted by Fear & Greed.
        
        Args:
            regime: Current market regime
            
        Returns:
            Adjusted max trades
        """
        base_limit = self.BULL_MAX_TRADES if regime == Regime.BULL else self.BEAR_MAX_TRADES
        
        # Adjust based on Fear & Greed
        if self.last_fg_index is not None:
            if self.last_fg_index < self.EXTREME_FEAR:
                # Extreme Fear: Cut exposure in half
                return max(1, base_limit // 2)
            elif self.last_fg_index > self.EXTREME_GREED:
                # Extreme Greed: Caution against top-blowing? Or ride it?
                # DayTraderAI suggests "Adaptive Sizing", let's keep max trades high but maybe sizing handles risk.
                # For now, let's allow full allocation.
                pass
                
        return base_limit

    def can_open_trade(self, regime: Regime, open_trades: int) -> bool:
        """Check if a new trade can be opened given current regime.
        
        Args:
            regime: Current market regime
            open_trades: Number of currently open trades
            
        Returns:
            True if open_trades < max_trades for regime
        """
        max_trades = self.get_max_trades(regime)
        return open_trades < max_trades

    def get_regime_info(self, btc_close: float, btc_ema50: float) -> dict:
        """Get complete regime information.
        
        Args:
            btc_close: Current BTC daily close price
            btc_ema50: BTC 50-period EMA value
            
        Returns:
            Dictionary with regime, max_trades, and price info
        """
        regime = self.classify(btc_close, btc_ema50)
        return {
            "regime": regime,
            "max_trades": self.get_max_trades(regime),
            "btc_close": btc_close,
            "btc_ema50": btc_ema50,
            "price_above_ema": btc_close > btc_ema50,
            "fear_greed_index": self.last_fg_index
        }
