"""Wave Rider Trailing Stop Manager.

Manages trailing stops with profit-based tightening:
- Activates at 1.0% profit
- Trails at 0.8x ATR initially
- Tightens to 0.5x ATR at 3%+ profit
- Handles TP1 (30% at 1.5%) and TP2 (30% at 2.5%)
"""

from dataclasses import dataclass
from typing import Dict, Tuple, Optional
from .models import TrailingState, WaveRiderConfig


@dataclass
class TrailingUpdate:
    """Result of trailing stop update."""
    state: TrailingState
    should_close: bool
    close_pct: float  # Percentage of position to close (0.0-1.0)
    close_reason: str  # "trailing", "tp1", "tp2", or ""


class WaveRiderTrailingStop:
    """Manages trailing stops with profit-based tightening.
    
    Property 13: Trailing Stop Activation
    Trailing stop activates when unrealized_profit >= 1.0%
    
    Property 14: Trailing Stop Tightening
    - Trail multiplier is 0.8x ATR when profit < 3%
    - Trail multiplier is 0.5x ATR when profit >= 3%
    """
    
    ACTIVATION_PROFIT = 0.01  # 1%
    INITIAL_TRAIL_MULT = 0.8
    TIGHT_TRAIL_MULT = 0.5
    TIGHT_THRESHOLD = 0.03  # 3%
    TP1_PROFIT = 0.015  # 1.5%
    TP1_CLOSE_PCT = 0.30
    TP2_PROFIT = 0.025  # 2.5%
    TP2_CLOSE_PCT = 0.30
    
    def __init__(self, config: Optional[WaveRiderConfig] = None):
        """Initialize the trailing stop manager.
        
        Args:
            config: Wave Rider configuration
        """
        self.config = config or WaveRiderConfig()
        self._states: Dict[str, TrailingState] = {}
        
        # Use config values
        self.activation_profit = self.config.trailing_activation_pct
        self.initial_trail_mult = self.config.initial_trail_multiplier
        self.tight_trail_mult = self.config.tight_trail_multiplier
        self.tight_threshold = self.config.tight_threshold_pct
        self.tp1_profit = self.config.tp1_profit_pct
        self.tp1_close_pct = self.config.tp1_close_pct
        self.tp2_profit = self.config.tp2_profit_pct
        self.tp2_close_pct = self.config.tp2_close_pct
    
    def update(
        self,
        symbol: str,
        current_price: float,
        entry_price: float,
        direction: str,
        atr_14: float,
    ) -> TrailingUpdate:
        """Update trailing stop state and check for exits.
        
        Args:
            symbol: Trading pair symbol
            current_price: Current market price
            entry_price: Position entry price
            direction: "LONG" or "SHORT"
            atr_14: 14-period ATR value
        
        Returns:
            TrailingUpdate with state and exit signals
        """
        # Get or create state
        if symbol not in self._states:
            self._states[symbol] = TrailingState()
        state = self._states[symbol]
        
        # Calculate current profit
        if direction == "LONG":
            profit_pct = (current_price - entry_price) / entry_price
        else:  # SHORT
            profit_pct = (entry_price - current_price) / entry_price
        
        # Check for TP1
        if not state.tp1_done and profit_pct >= self.tp1_profit:
            state.tp1_done = True
            return TrailingUpdate(
                state=state,
                should_close=True,
                close_pct=self.tp1_close_pct,
                close_reason="tp1",
            )
        
        # Check for TP2
        if state.tp1_done and not state.tp2_done and profit_pct >= self.tp2_profit:
            state.tp2_done = True
            return TrailingUpdate(
                state=state,
                should_close=True,
                close_pct=self.tp2_close_pct,
                close_reason="tp2",
            )
        
        # Check trailing stop activation
        if not state.is_active and profit_pct >= self.activation_profit:
            state.is_active = True
            state.peak_price = current_price
            state.peak_profit_pct = profit_pct
            state.trail_multiplier = self.initial_trail_mult
        
        # Update trailing stop if active
        if state.is_active:
            # Update peak
            if direction == "LONG" and current_price > state.peak_price:
                state.peak_price = current_price
                state.peak_profit_pct = profit_pct
            elif direction == "SHORT" and current_price < state.peak_price:
                state.peak_price = current_price
                state.peak_profit_pct = profit_pct
            
            # Tighten trail at 3%+ profit
            if state.peak_profit_pct >= self.tight_threshold:
                state.trail_multiplier = self.tight_trail_mult
            
            # Calculate trail stop price
            trail_distance = atr_14 * state.trail_multiplier
            
            if direction == "LONG":
                trail_stop = state.peak_price - trail_distance
                if current_price <= trail_stop:
                    return TrailingUpdate(
                        state=state,
                        should_close=True,
                        close_pct=1.0,  # Close remaining
                        close_reason="trailing",
                    )
            else:  # SHORT
                trail_stop = state.peak_price + trail_distance
                if current_price >= trail_stop:
                    return TrailingUpdate(
                        state=state,
                        should_close=True,
                        close_pct=1.0,
                        close_reason="trailing",
                    )
        
        return TrailingUpdate(
            state=state,
            should_close=False,
            close_pct=0.0,
            close_reason="",
        )
    
    def get_state(self, symbol: str) -> Optional[TrailingState]:
        """Get trailing state for a symbol."""
        return self._states.get(symbol)
    
    def remove_position(self, symbol: str) -> None:
        """Remove trailing state for a closed position."""
        if symbol in self._states:
            del self._states[symbol]
    
    def reset(self) -> None:
        """Reset all trailing states."""
        self._states.clear()
    
    def is_trailing_active(self, profit_pct: float) -> bool:
        """Check if trailing should be active at given profit.
        
        For testing Property 13.
        """
        return profit_pct >= self.activation_profit
    
    def get_trail_multiplier(self, profit_pct: float) -> float:
        """Get trail multiplier for given profit level.
        
        For testing Property 14.
        """
        if profit_pct >= self.tight_threshold:
            return self.tight_trail_mult
        return self.initial_trail_mult
