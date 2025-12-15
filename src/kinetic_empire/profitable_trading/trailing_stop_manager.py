"""ATR Trailing Stop Manager.

Implements trailing stops per profitable-trading-overhaul spec:
- Activate at 2% profit
- Trail at 1.5x ATR from peak
- Tighten to 1.0x ATR at 5% profit
"""

import logging
from typing import Tuple

from .models import TrailingState


logger = logging.getLogger(__name__)


class ATRTrailingStopManager:
    """Manages trailing stops using ATR.
    
    Per Requirements 6.1-6.4:
    - Activate when profit reaches 2%
    - Trail at 1.5x ATR from peak price
    - Tighten to 1.0x ATR when profit exceeds 5%
    """
    
    # Activation threshold
    ACTIVATION_THRESHOLD = 0.02  # 2%
    
    # Trail multipliers
    NORMAL_TRAIL_MULT = 1.5
    TIGHT_TRAIL_MULT = 1.0
    
    # Tightening threshold
    TIGHT_THRESHOLD = 0.05  # 5%
    
    def __init__(self):
        """Initialize trailing stop manager."""
        self._states: dict = {}  # symbol -> TrailingState
    
    def update(
        self,
        symbol: str,
        current_price: float,
        entry_price: float,
        direction: str,
        atr_14: float,
        activation_threshold: float = ACTIVATION_THRESHOLD,
        normal_trail_mult: float = NORMAL_TRAIL_MULT,
        tight_trail_mult: float = TIGHT_TRAIL_MULT,
        tight_threshold: float = TIGHT_THRESHOLD,
    ) -> Tuple[TrailingState, bool]:
        """Update trailing stop state.
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            entry_price: Position entry price
            direction: "LONG" or "SHORT"
            atr_14: 14-period ATR value
            activation_threshold: Profit % to activate (default 0.02)
            normal_trail_mult: Normal ATR multiplier (default 1.5)
            tight_trail_mult: Tight ATR multiplier (default 1.0)
            tight_threshold: Profit % to tighten (default 0.05)
            
        Returns:
            (TrailingState, should_close) tuple
        """
        # Calculate current profit
        if direction.upper() == "LONG":
            profit_pct = (current_price - entry_price) / entry_price
        else:
            profit_pct = (entry_price - current_price) / entry_price
        
        # Get or create state
        state = self._states.get(symbol)
        if state is None:
            state = TrailingState(
                is_active=False,
                peak_price=current_price,
                peak_profit_pct=profit_pct,
                current_trail_distance=0.0,
                trail_multiplier=normal_trail_mult,
            )
            self._states[symbol] = state
        
        # Check activation
        if not state.is_active and profit_pct >= activation_threshold:
            state.is_active = True
            logger.info(f"{symbol}: Trailing stop ACTIVATED at {profit_pct:.2%} profit")
        
        if not state.is_active:
            # Update peak tracking even when not active
            if direction.upper() == "LONG":
                if current_price > state.peak_price:
                    state.peak_price = current_price
                    state.peak_profit_pct = profit_pct
            else:
                if current_price < state.peak_price:
                    state.peak_price = current_price
                    state.peak_profit_pct = profit_pct
            return state, False
        
        # Update peak price
        if direction.upper() == "LONG":
            if current_price > state.peak_price:
                state.peak_price = current_price
                state.peak_profit_pct = profit_pct
        else:
            if current_price < state.peak_price:
                state.peak_price = current_price
                state.peak_profit_pct = profit_pct
        
        # Determine trail multiplier (tighten at 5%+)
        if state.peak_profit_pct >= tight_threshold:
            state.trail_multiplier = tight_trail_mult
        else:
            state.trail_multiplier = normal_trail_mult
        
        # Calculate trail distance
        state.current_trail_distance = atr_14 * state.trail_multiplier
        
        # Check if trailing stop triggered
        should_close = False
        if direction.upper() == "LONG":
            trail_stop_price = state.peak_price - state.current_trail_distance
            if current_price <= trail_stop_price:
                should_close = True
                logger.info(
                    f"{symbol}: TRAILING STOP triggered at {profit_pct:.2%} "
                    f"(peak: {state.peak_profit_pct:.2%})"
                )
        else:
            trail_stop_price = state.peak_price + state.current_trail_distance
            if current_price >= trail_stop_price:
                should_close = True
                logger.info(
                    f"{symbol}: TRAILING STOP triggered at {profit_pct:.2%} "
                    f"(peak: {state.peak_profit_pct:.2%})"
                )
        
        return state, should_close
    
    def remove_position(self, symbol: str) -> None:
        """Remove position from tracking."""
        if symbol in self._states:
            del self._states[symbol]
    
    def get_state(self, symbol: str) -> TrailingState:
        """Get current trailing state for symbol."""
        return self._states.get(symbol)
