"""Position Manager for Kinetic Empire v3.0.

Handles position lifecycle with dynamic leverage and risk management.
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date

from src.kinetic_empire.v3.core.models import Signal, Position, TradeResult

logger = logging.getLogger(__name__)


class PositionManager:
    """Manages position lifecycle with dynamic leverage and risk controls.
    
    Features:
    - Pre-trade risk checks
    - Dynamic leverage scaling (5x-20x)
    - Confidence-based position sizing
    - Trailing stops and partial take profits
    - Emergency controls
    """

    def __init__(
        self,
        max_positions: int = 12,
        max_margin_usage_pct: float = 90.0,
        daily_loss_limit_pct: float = 5.0,
        max_correlated_positions: int = 3,
        max_position_pct: float = 25.0,
        base_risk_pct: float = 1.0,
    ):
        """Initialize position manager.
        
        Args:
            max_positions: Maximum concurrent positions
            max_margin_usage_pct: Maximum margin usage percentage
            daily_loss_limit_pct: Daily loss limit percentage
            max_correlated_positions: Max positions in correlated assets
            max_position_pct: Max position size as % of equity
            base_risk_pct: Base risk per trade percentage
        """
        self.max_positions = max_positions
        self.max_margin_usage_pct = max_margin_usage_pct
        self.daily_loss_limit_pct = daily_loss_limit_pct
        self.max_correlated_positions = max_correlated_positions
        self.max_position_pct = max_position_pct
        self.base_risk_pct = base_risk_pct
        
        # Leverage tiers based on confidence
        self.leverage_tiers = {
            (60, 69): 5,
            (70, 79): 10,
            (80, 89): 15,
            (90, 100): 20,
        }
        
        # Risk scaling based on confidence
        self.risk_scaling = {
            (60, 79): 1.0,
            (80, 89): 1.5,
            (90, 100): 2.0,
        }
        
        # State
        self.positions: Dict[str, Position] = {}
        self.daily_pnl: float = 0.0
        self.daily_start_equity: float = 0.0
        self.current_date: date = date.today()
        self.trade_history: List[TradeResult] = []

    def check_risk_limits(
        self,
        equity: float,
        margin_used: float,
        margin_total: float,
        symbol: str,
    ) -> Tuple[bool, str]:
        """Check all pre-trade risk limits.
        
        Args:
            equity: Current account equity
            margin_used: Currently used margin
            margin_total: Total available margin
            symbol: Symbol to trade
            
        Returns:
            Tuple of (can_trade, reason)
        """
        # Reset daily tracking if new day
        if date.today() != self.current_date:
            logger.debug(f"   📅 New day detected - resetting daily P&L tracking")
            self.current_date = date.today()
            self.daily_pnl = 0.0
            self.daily_start_equity = equity
        
        # Check 1: Max positions
        logger.debug(f"   [1/5] Positions: {len(self.positions)}/{self.max_positions}")
        if len(self.positions) >= self.max_positions:
            return False, f"Max positions ({self.max_positions}) reached"
        
        # Check 2: Margin usage
        if margin_total > 0:
            margin_usage_pct = (margin_used / margin_total) * 100
            logger.debug(f"   [2/5] Margin usage: {margin_usage_pct:.1f}%/{self.max_margin_usage_pct}%")
            if margin_usage_pct >= self.max_margin_usage_pct:
                return False, f"Margin usage ({margin_usage_pct:.1f}%) exceeds limit ({self.max_margin_usage_pct}%)"
        else:
            logger.debug(f"   [2/5] Margin usage: N/A (no margin total)")
        
        # Check 3: Daily loss limit
        if self.daily_start_equity > 0:
            daily_loss_pct = (self.daily_pnl / self.daily_start_equity) * 100
            logger.debug(f"   [3/5] Daily P&L: {daily_loss_pct:+.2f}% (limit: -{self.daily_loss_limit_pct}%)")
            if daily_loss_pct <= -self.daily_loss_limit_pct:
                return False, f"Daily loss limit ({self.daily_loss_limit_pct}%) reached"
        else:
            logger.debug(f"   [3/5] Daily P&L: N/A (no start equity)")
        
        # Check 4: Correlated positions
        correlated_count = self._count_correlated_positions(symbol)
        logger.debug(f"   [4/5] Correlated positions for {symbol}: {correlated_count}/{self.max_correlated_positions}")
        if correlated_count >= self.max_correlated_positions:
            return False, f"Max correlated positions ({self.max_correlated_positions}) reached"
        
        # Check 5: Symbol not already in position
        already_in = symbol in self.positions
        logger.debug(f"   [5/5] Already in position: {already_in}")
        if already_in:
            return False, f"Already have position in {symbol}"
        
        return True, "All risk checks passed"

    def calculate_leverage(self, confidence: int, high_volatility: bool = False) -> int:
        """Calculate leverage based on confidence and volatility.
        
        Args:
            confidence: Signal confidence score (60-100)
            high_volatility: Whether market is in high volatility state
            
        Returns:
            Leverage multiplier (1-20)
        """
        # Reject low confidence
        if confidence < 60:
            return 0
        
        # Find leverage tier
        base_leverage = 5  # Default
        for (min_conf, max_conf), leverage in self.leverage_tiers.items():
            if min_conf <= confidence <= max_conf:
                base_leverage = leverage
                break
        
        # Reduce by 50% in high volatility
        if high_volatility:
            base_leverage = max(1, base_leverage // 2)
        
        return base_leverage

    def calculate_position_size(
        self,
        equity: float,
        confidence: int,
        entry_price: float,
        stop_loss: float,
    ) -> float:
        """Calculate position size based on risk parameters.
        
        Args:
            equity: Account equity
            confidence: Signal confidence score
            entry_price: Entry price
            stop_loss: Stop loss price
            
        Returns:
            Position size in base currency
        """
        # Get risk multiplier based on confidence
        risk_multiplier = 1.0
        for (min_conf, max_conf), multiplier in self.risk_scaling.items():
            if min_conf <= confidence <= max_conf:
                risk_multiplier = multiplier
                break
        
        # Calculate risk amount
        risk_pct = self.base_risk_pct * risk_multiplier
        risk_amount = equity * (risk_pct / 100)
        
        # Calculate stop distance
        stop_distance_pct = abs(entry_price - stop_loss) / entry_price * 100
        if stop_distance_pct == 0:
            return 0
        
        # Position size = risk_amount / stop_distance
        position_value = risk_amount / (stop_distance_pct / 100)
        
        # Cap at max position percentage
        max_position_value = equity * (self.max_position_pct / 100)
        position_value = min(position_value, max_position_value)
        
        # Convert to base currency size
        size = position_value / entry_price
        
        return size

    def _count_correlated_positions(self, symbol: str) -> int:
        """Count positions in correlated assets.
        
        Simple correlation: same base currency (e.g., BTC in BTCUSDT, BTCUSDC)
        """
        # Extract base currency (everything before USDT/USDC)
        base = symbol.replace("USDT", "").replace("USDC", "")
        
        count = 0
        for pos_symbol in self.positions:
            pos_base = pos_symbol.replace("USDT", "").replace("USDC", "")
            if pos_base == base:
                count += 1
        
        return count

    def add_position(self, position: Position) -> None:
        """Add a new position to tracking."""
        self.positions[position.symbol] = position
        logger.info(f"Added position: {position.symbol} {position.side} @ {position.entry_price}")

    def remove_position(self, symbol: str, pnl: float) -> Optional[Position]:
        """Remove a position and update daily P&L."""
        if symbol in self.positions:
            position = self.positions.pop(symbol)
            self.daily_pnl += pnl
            logger.info(f"Removed position: {symbol}, P&L: {pnl:.2f}")
            return position
        return None

    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position by symbol."""
        return self.positions.get(symbol)

    def get_all_positions(self) -> List[Position]:
        """Get all open positions."""
        return list(self.positions.values())

    # ==================== Execution Methods ====================

    async def process_signal(
        self,
        signal: Signal,
        equity: float,
        margin_used: float,
        margin_total: float,
        high_volatility: bool = False,
    ) -> Optional[Position]:
        """Process a trading signal and create position if valid.
        
        Args:
            signal: Trading signal to process
            equity: Current account equity
            margin_used: Currently used margin
            margin_total: Total available margin
            high_volatility: Whether market is in high volatility
            
        Returns:
            Position if created, None if rejected
        """
        logger.debug(f"🔄 Processing signal: {signal.symbol} {signal.direction}")
        logger.debug(f"   Signal details: conf={signal.confidence}, entry=${signal.entry_price:.4f}, sl=${signal.stop_loss:.4f}, tp=${signal.take_profit:.4f}")
        
        # Validate signal
        if not signal.validate():
            logger.warning(f"⚠️  {signal.symbol}: Invalid signal - validation failed")
            return None
        logger.debug(f"   ✓ Signal validated")
        
        # Check risk limits
        logger.debug(f"   🛡️  Checking risk limits...")
        can_trade, reason = self.check_risk_limits(
            equity, margin_used, margin_total, signal.symbol
        )
        if not can_trade:
            logger.info(f"⛔ {signal.symbol}: Trade rejected - {reason}")
            return None
        logger.debug(f"   ✓ Risk checks passed: {reason}")
        
        # Calculate leverage
        leverage = self.calculate_leverage(signal.confidence, high_volatility)
        logger.debug(f"   📐 Calculated leverage: {leverage}x (volatility_mode={high_volatility})")
        if leverage == 0:
            logger.info(f"⛔ {signal.symbol}: Confidence {signal.confidence} too low for any leverage")
            return None
        
        # Calculate position size
        size = self.calculate_position_size(
            equity, signal.confidence, signal.entry_price, signal.stop_loss
        )
        logger.debug(f"   📏 Calculated size: {size:.6f} (equity=${equity:.2f}, risk={self.base_risk_pct}%)")
        if size <= 0:
            logger.warning(f"⚠️  {signal.symbol}: Invalid position size calculated")
            return None
        
        # Create position
        position = Position(
            symbol=signal.symbol,
            side=signal.direction,
            entry_price=signal.entry_price,
            size=size,
            leverage=leverage,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            confidence=signal.confidence,
        )
        
        # Add to tracking
        self.add_position(position)
        
        position_value = size * signal.entry_price
        logger.info(
            f"✅ {signal.symbol}: POSITION OPENED - {signal.direction} "
            f"| Size: {size:.4f} (${position_value:.2f}) | Leverage: {leverage}x | Confidence: {signal.confidence}%"
        )
        logger.debug(f"   Entry: ${signal.entry_price:.4f} | SL: ${signal.stop_loss:.4f} | TP: ${signal.take_profit:.4f}")
        
        return position

    # ==================== Exit Management ====================

    def update_trailing_stops(self, current_prices: Dict[str, float]) -> List[str]:
        """Update trailing stops for all positions.
        
        Args:
            current_prices: Dict of symbol -> current price
            
        Returns:
            List of symbols where trailing stop was updated
        """
        updated = []
        
        for symbol, position in self.positions.items():
            if symbol not in current_prices:
                continue
            
            current_price = current_prices[symbol]
            pnl_pct = position.calc_pnl_pct(current_price)
            
            # Update peak P&L
            if pnl_pct > position.peak_pnl:
                position.peak_pnl = pnl_pct
            
            # Activate trailing stop at +1.5%
            if pnl_pct >= 1.5 and not position.trailing_activated:
                position.trailing_activated = True
                # Set trailing stop at 1x ATR distance (simplified: use 1% for now)
                if position.side == "LONG":
                    position.trailing_stop = current_price * 0.99
                else:
                    position.trailing_stop = current_price * 1.01
                updated.append(symbol)
                logger.info(f"{symbol}: Trailing stop activated at {position.trailing_stop:.2f}")
            
            # Tighten trailing stop at +3%
            elif pnl_pct >= 3.0 and position.trailing_activated:
                # Tighten to 0.5% distance
                if position.side == "LONG":
                    new_stop = current_price * 0.995
                    if position.trailing_stop is None or new_stop > position.trailing_stop:
                        position.trailing_stop = new_stop
                        updated.append(symbol)
                else:
                    new_stop = current_price * 1.005
                    if position.trailing_stop is None or new_stop < position.trailing_stop:
                        position.trailing_stop = new_stop
                        updated.append(symbol)
            
            # Move trailing stop to lock minimum 0.5% profit
            elif position.trailing_activated and position.trailing_stop is not None:
                min_profit_price = self._calculate_min_profit_price(position, 0.5)
                if position.side == "LONG":
                    if min_profit_price > position.trailing_stop:
                        position.trailing_stop = min_profit_price
                        updated.append(symbol)
                else:
                    if min_profit_price < position.trailing_stop:
                        position.trailing_stop = min_profit_price
                        updated.append(symbol)
        
        return updated

    def check_take_profits(self, current_prices: Dict[str, float]) -> List[Tuple[str, int, float]]:
        """Check and return positions that hit take profit levels.
        
        Args:
            current_prices: Dict of symbol -> current price
            
        Returns:
            List of (symbol, tp_level, close_percentage) tuples
        """
        tp_triggers = []
        
        for symbol, position in self.positions.items():
            if symbol not in current_prices:
                continue
            
            current_price = current_prices[symbol]
            pnl_pct = position.calc_pnl_pct(current_price)
            num_exits = len(position.partial_exits)
            
            # TP1: +1.5% -> close 40% (only if no exits yet)
            if pnl_pct >= 1.5 and num_exits == 0:
                position.partial_exits.append(current_price)
                tp_triggers.append((symbol, 1, 40.0))
                logger.info(f"{symbol}: TP1 hit at {pnl_pct:.2f}%, closing 40%")
            
            # TP2: +2.5% -> close 30% (only if TP1 already executed)
            elif pnl_pct >= 2.5 and num_exits == 1:
                position.partial_exits.append(current_price)
                tp_triggers.append((symbol, 2, 30.0))
                logger.info(f"{symbol}: TP2 hit at {pnl_pct:.2f}%, closing 30%")
        
        return tp_triggers

    def check_stop_losses(self, current_prices: Dict[str, float]) -> List[Tuple[str, str]]:
        """Check positions for stop loss or trailing stop triggers.
        
        Args:
            current_prices: Dict of symbol -> current price
            
        Returns:
            List of (symbol, exit_reason) tuples
        """
        triggers = []
        
        for symbol, position in self.positions.items():
            if symbol not in current_prices:
                continue
            
            current_price = current_prices[symbol]
            
            # Check trailing stop first
            if position.should_trailing_stop(current_price):
                triggers.append((symbol, "TRAILING_STOP"))
                logger.info(f"{symbol}: Trailing stop triggered at {current_price:.2f}")
            
            # Check regular stop loss
            elif position.should_stop_loss(current_price):
                triggers.append((symbol, "STOP_LOSS"))
                logger.info(f"{symbol}: Stop loss triggered at {current_price:.2f}")
        
        return triggers

    def emergency_check(
        self,
        equity: float,
        unrealized_pnl: float,
        current_prices: Dict[str, float],
    ) -> List[Tuple[str, str]]:
        """Check for emergency exit conditions.
        
        Args:
            equity: Current account equity
            unrealized_pnl: Total unrealized P&L
            current_prices: Dict of symbol -> current price
            
        Returns:
            List of (symbol, reason) tuples for positions to close
        """
        emergency_exits = []
        
        # Check portfolio-level emergency: -5% unrealized loss
        if equity > 0:
            portfolio_loss_pct = (unrealized_pnl / equity) * 100
            if portfolio_loss_pct <= -5.0:
                logger.critical(f"EMERGENCY: Portfolio loss {portfolio_loss_pct:.2f}% - closing all positions")
                for symbol in self.positions:
                    emergency_exits.append((symbol, "EMERGENCY_PORTFOLIO"))
                return emergency_exits
        
        # Check individual position emergency: -4% loss
        for symbol, position in self.positions.items():
            if symbol not in current_prices:
                continue
            
            current_price = current_prices[symbol]
            pnl_pct = position.calc_pnl_pct(current_price)
            
            if pnl_pct <= -4.0:
                logger.warning(f"{symbol}: Position loss {pnl_pct:.2f}% - emergency close")
                emergency_exits.append((symbol, "EMERGENCY_POSITION"))
        
        return emergency_exits

    def _calculate_min_profit_price(self, position: Position, min_profit_pct: float) -> float:
        """Calculate price that locks minimum profit percentage."""
        if position.side == "LONG":
            return position.entry_price * (1 + min_profit_pct / 100)
        else:
            return position.entry_price * (1 - min_profit_pct / 100)

    async def monitor_positions(self, current_prices: Dict[str, float], equity: float) -> Dict[str, List]:
        """Monitor all positions and return actions needed.
        
        Args:
            current_prices: Dict of symbol -> current price
            equity: Current account equity
            
        Returns:
            Dict with 'stop_losses', 'take_profits', 'trailing_updates', 'emergencies'
        """
        logger.debug(f"🔍 Monitoring {len(self.positions)} positions...")
        
        # Calculate unrealized P&L
        unrealized_pnl = 0.0
        for symbol, position in self.positions.items():
            if symbol in current_prices:
                pnl = position.calc_pnl_amount(current_prices[symbol])
                unrealized_pnl += pnl
        
        logger.debug(f"   💵 Total unrealized P&L: ${unrealized_pnl:+.2f}")
        
        # Check all conditions
        stop_losses = self.check_stop_losses(current_prices)
        if stop_losses:
            logger.debug(f"   🛑 Stop losses triggered: {len(stop_losses)}")
        
        take_profits = self.check_take_profits(current_prices)
        if take_profits:
            logger.debug(f"   💰 Take profits triggered: {len(take_profits)}")
        
        trailing_updates = self.update_trailing_stops(current_prices)
        if trailing_updates:
            logger.debug(f"   🔄 Trailing stops updated: {len(trailing_updates)}")
        
        emergencies = self.emergency_check(equity, unrealized_pnl, current_prices)
        if emergencies:
            logger.debug(f"   🚨 Emergency exits: {len(emergencies)}")
        
        return {
            "stop_losses": stop_losses,
            "take_profits": take_profits,
            "trailing_updates": trailing_updates,
            "emergencies": emergencies,
        }
