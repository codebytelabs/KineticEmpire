"""Futures Engine for Unified Trading System.

Wraps the existing CashCowLiveEngine logic into the unified engine interface.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .config import UnifiedConfig
from .capital_allocator import CapitalAllocation
from .base_engine import BaseEngine

from ..futures.client import BinanceFuturesClient, FuturesPosition
from ..v3.analyzer.enhanced import EnhancedTAAnalyzer, OHLCV as EnhancedOHLCV
from ..v3.core.models import OHLCV, Signal
from ..cash_cow.engine import CashCowEngine
from ..cash_cow.config import CashCowConfig
from ..signal_quality import SignalQualityGate, QualityGateConfig, QualityGateResult
from ..signal_quality import MarketRegime as SQMarketRegime, OHLCV as SQOHLCV
from ..profitable_trading import (
    MarketRegime as PTMarketRegime,
    RegimeDetector,
    DirectionValidator,
    ConfidencePositionSizer,
    RegimeLeverageCalculator,
    ATRStopCalculator,
    ATRTrailingStopManager,
    ExposureTracker,
    EntryConfirmer,
)

logger = logging.getLogger(__name__)


class AggressivePositionSizer:
    """Aggressive position sizer that uses 90% of available capital.
    
    Position sizing based on confidence (regime-aware):
    - 90-100 confidence → 20% position
    - 80-89 confidence → 18% position
    - 70-79 confidence → 15% position
    - 60-69 confidence → 12% position
    
    Minimum confidence thresholds:
    - TRENDING: 60
    - SIDEWAYS/CHOPPY: 65 (more selective)
    """
    
    def __init__(self, config: 'UnifiedConfig'):
        self.config = config
        self.min_size_pct = config.futures_position_size_min_pct / 100
        self.max_size_pct = config.futures_position_size_max_pct / 100
        self.capital_utilization = config.futures_capital_utilization_pct / 100
    
    def _get_min_confidence(self, market_regime: str) -> int:
        """Get minimum confidence based on market regime."""
        regime_upper = market_regime.upper() if market_regime else "TRENDING"
        if regime_upper == "TRENDING":
            return getattr(self.config, 'futures_min_confidence_trending', 60)
        else:  # SIDEWAYS, CHOPPY
            return getattr(self.config, 'futures_min_confidence_sideways', 65)
    
    def calculate(
        self,
        confidence: int,
        available_capital: float,
        current_exposure: float = 0.0,
        max_exposure: float = 0.90,
        market_regime: str = "TRENDING",
    ):
        """Calculate aggressive position size with regime-aware confidence."""
        from ..profitable_trading.models import PositionSizeResult
        
        # Regime-aware minimum confidence
        min_confidence = self._get_min_confidence(market_regime)
        
        # Reject low confidence based on regime
        if confidence < min_confidence:
            return PositionSizeResult(
                size_pct=0.0,
                size_usd=0.0,
                confidence_tier="rejected",
                is_rejected=True,
                rejection_reason=f"Confidence {confidence} below minimum {min_confidence} for {market_regime} regime",
            )
        
        # Aggressive confidence-to-size mapping
        if confidence >= 90:
            size_pct = 0.20  # 20%
            tier = "excellent"
        elif confidence >= 80:
            size_pct = 0.18  # 18%
            tier = "high"
        elif confidence >= 70:
            size_pct = 0.15  # 15%
            tier = "good"
        else:  # 60-69
            size_pct = 0.12  # 12%
            tier = "medium"
        
        # Clamp to config bounds
        size_pct = max(self.min_size_pct, min(size_pct, self.max_size_pct))
        
        # Check exposure limit
        remaining_exposure = max_exposure - current_exposure
        if remaining_exposure <= 0.02:  # Less than 2% remaining
            return PositionSizeResult(
                size_pct=0.0,
                size_usd=0.0,
                confidence_tier=tier,
                is_rejected=True,
                rejection_reason=f"Exposure limit reached: {current_exposure:.1%}",
            )
        
        # Cap at remaining exposure
        actual_size_pct = min(size_pct, remaining_exposure)
        size_usd = available_capital * actual_size_pct
        
        return PositionSizeResult(
            size_pct=actual_size_pct,
            size_usd=size_usd,
            confidence_tier=tier,
        )


class PositionState:
    """Track state for scaled exits and trailing stops."""
    def __init__(self, symbol: str, original_qty: float, entry_price: float, stop_loss_pct: float = -4.0):
        self.symbol = symbol
        self.original_qty = original_qty
        self.entry_price = entry_price
        self.stop_loss_pct = stop_loss_pct
        self.tp1_done = False
        self.tp2_done = False
        self.peak_pnl_pct = 0.0


class FuturesEngine(BaseEngine):
    """Futures trading engine with leverage.
    
    Integrates with existing profitable trading components and
    Cash Cow scoring system.
    
    Features:
    - Dynamic position limits (5-12) based on market regime
    - Aggressive capital utilization (90% of buying power)
    - Dynamic leverage per regime (5x-15x)
    """
    
    def __init__(
        self,
        config: UnifiedConfig,
        allocation: CapitalAllocation,
        client: BinanceFuturesClient,
    ):
        """Initialize futures engine.
        
        Args:
            config: Unified configuration.
            allocation: Capital allocation for this engine.
            client: Binance futures client.
        """
        super().__init__("futures", config, allocation)
        self.client = client
        self.enhanced_analyzer = EnhancedTAAnalyzer()
        
        # Initialize Cash Cow engine
        cash_cow_config = CashCowConfig(
            base_risk_pct=config.futures_position_size_min_pct,
            max_position_pct=config.futures_position_size_max_pct,
            high_confidence_threshold=85,
            medium_confidence_threshold=75,
            low_confidence_threshold=config.futures_min_confidence,
            daily_loss_limit_pct=config.global_daily_loss_limit_pct,
        )
        self.cash_cow = CashCowEngine(cash_cow_config)
        
        # Signal Quality Gate
        self.quality_gate = SignalQualityGate(QualityGateConfig())
        
        # Profitable Trading Components
        self.regime_detector = RegimeDetector()
        self.direction_validator = DirectionValidator()
        self.position_sizer = AggressivePositionSizer(config)  # Use aggressive sizer
        self.leverage_calculator = RegimeLeverageCalculator()
        self.atr_stop_calculator = ATRStopCalculator()
        self.trailing_stop_manager = ATRTrailingStopManager()
        self.exposure_tracker = ExposureTracker(max_exposure_pct=config.futures_capital_utilization_pct / 100)
        self.entry_confirmer = EntryConfirmer()
        
        # State
        self.position_states: Dict[str, PositionState] = {}
        self._atr_cache: Dict[str, float] = {}
        self._gate_results: Dict[str, QualityGateResult] = {}
        self.daily_pnl = 0.0
        self.starting_balance = 0.0
        self.trade_count = 0
        
        # Dynamic position limit tracking
        self._current_max_positions = config.futures_max_positions
        self._market_regime = "UNKNOWN"
    
    async def start(self) -> None:
        """Start the futures trading loop."""
        self._running = True
        
        logger.info(f"🚀 {self.name.upper()} ENGINE STARTING")
        logger.info(f"   💰 Capital Allocation: {self.allocation.allocated_pct}%")
        logger.info(f"   📊 Dynamic Positions: {self.config.futures_max_positions_min}-{self.config.futures_max_positions_max}")
        logger.info(f"   🎯 Leverage Range: {self.config.futures_leverage_min}x - {self.config.futures_leverage_max}x")
        logger.info(f"   💪 Capital Utilization: {self.config.futures_capital_utilization_pct}%")
        logger.info(f"   📈 Position Size: {self.config.futures_position_size_min_pct}%-{self.config.futures_position_size_max_pct}%")
        
        try:
            # Get all balance types
            total_wallet = self.client.get_total_wallet_balance()
            available_balance = self.client.get_usdt_balance()
            margin_balance = self.client.get_total_margin_balance()
            
            self.starting_balance = total_wallet  # Use total wallet as starting point
            
            logger.info(f"   💰 Total Wallet: ${total_wallet:.2f}")
            logger.info(f"   💵 Available (Free): ${available_balance:.2f}")
            logger.info(f"   � MargFin Balance: ${margin_balance:.2f}")
            logger.info(f"   🎯 Target Utilization (90%): ${total_wallet * self.config.futures_capital_utilization_pct / 100:.2f}")
            
            # Check for existing positions and adopt them
            existing_positions = self.client.get_positions()
            active_positions = [p for p in existing_positions if p.quantity * p.mark_price >= 5]
            if active_positions:
                logger.info(f"   📋 Found {len(active_positions)} existing positions - will manage them:")
                total_margin = 0
                total_unrealized_pnl = 0
                for pos in active_positions:
                    margin = (pos.quantity * pos.entry_price) / pos.leverage if pos.leverage > 0 else 0
                    total_margin += margin
                    total_unrealized_pnl += pos.unrealized_pnl
                    pnl_pct = self._calc_pnl_pct(pos)
                    logger.info(f"      • {pos.symbol} {pos.side} | Entry: ${pos.entry_price:.4f} | P&L: ${pos.unrealized_pnl:+.2f} ({pnl_pct:+.2f}%)")
                    # Add to exposure tracker
                    exposure_pct = margin / total_wallet if total_wallet > 0 else 0
                    self.exposure_tracker.add_position(pos.symbol, exposure_pct)
                margin_used_pct = (total_margin / total_wallet * 100) if total_wallet > 0 else 0
                logger.info(f"   💼 Margin Used: ${total_margin:.2f} ({margin_used_pct:.1f}%)")
                logger.info(f"   📈 Unrealized P&L: ${total_unrealized_pnl:+.2f}")
            else:
                logger.info(f"   📋 No existing positions found - ready to trade!")
        except Exception as e:
            logger.error(f"❌ Failed to get balance: {e}")
            return
        
        scan_cycle = 0
        monitor_cycle = 0
        
        while self._running and not self.is_shutdown_requested():
            try:
                monitor_cycle += 1
                self.send_heartbeat()
                
                await self._monitor_positions(monitor_cycle)
                
                # Scan every 6th cycle (30 seconds)
                if monitor_cycle % 6 == 1:
                    scan_cycle += 1
                    await self._scan_and_trade(scan_cycle)
                
                await asyncio.sleep(self.config.futures_scan_interval_seconds / 6)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in futures loop: {e}")
                await asyncio.sleep(10)
        
        self._running = False
        logger.info(f"🛑 {self.name.upper()} ENGINE STOPPED")
    
    async def stop(self) -> None:
        """Stop the engine gracefully."""
        self._shutdown_requested = True
        
        # Wait for current operation to complete
        await self._wait_for_completion(timeout_seconds=30.0)
        
        self._running = False
        logger.info(f"✅ {self.name.upper()} engine stopped gracefully")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        try:
            # Use total margin balance (wallet + unrealized PnL) for accurate portfolio value
            # This prevents false drawdown triggers when positions are opened/closed
            margin_balance = self.client.get_total_margin_balance()
            positions = self.client.get_positions()
            
            return {
                "name": self.name,
                "running": self._running,
                "portfolio_value": margin_balance,  # Use margin balance, not available
                "positions_count": len(positions),
                "daily_pnl": self.daily_pnl,
                "trade_count": self.trade_count,
                "allocation_pct": self.allocation.allocated_pct,
            }
        except Exception as e:
            return {
                "name": self.name,
                "running": self._running,
                "error": str(e),
            }
    
    async def get_positions_count(self) -> int:
        """Get number of open positions."""
        try:
            positions = self.client.get_positions()
            return len([p for p in positions if p.quantity * p.mark_price >= 5])
        except Exception:
            return 0
    
    async def get_total_pnl(self) -> tuple[float, float]:
        """Get total P&L."""
        try:
            positions = self.client.get_positions()
            total_pnl = sum(p.unrealized_pnl for p in positions)
            pnl_pct = (total_pnl / self.starting_balance * 100) if self.starting_balance > 0 else 0.0
            return total_pnl, pnl_pct
        except Exception:
            return 0.0, 0.0
    
    async def close_all_positions(self) -> None:
        """Close all open positions due to circuit breaker.
        
        Note: Does NOT blacklist symbols since this is a risk management action,
        not a trading loss.
        """
        logger.warning(f"🚨 {self.name}: Closing all positions!")
        try:
            positions = self.client.get_positions()
            for pos in positions:
                # Use special circuit breaker close that doesn't blacklist
                await self._close_position_no_blacklist(pos, "CIRCUIT_BREAKER")
        except Exception as e:
            logger.error(f"Failed to close all positions: {e}")
    
    async def _close_position_no_blacklist(self, pos: FuturesPosition, reason: str):
        """Close position without blacklisting (for circuit breaker)."""
        try:
            close_side = "SELL" if pos.side == "LONG" else "BUY"
            quantity = pos.quantity
            notional = quantity * pos.mark_price
            
            if notional < 5:
                if pos.symbol in self.position_states:
                    del self.position_states[pos.symbol]
                return
            
            self.client.place_market_order(
                symbol=pos.symbol, side=close_side, quantity=quantity, reduce_only=True
            )
            logger.info(f"✅ Closed {pos.symbol}: {reason} | P&L: ${pos.unrealized_pnl:+.2f}")
            
            # Clean up state but DON'T blacklist
            if pos.symbol in self.position_states:
                del self.position_states[pos.symbol]
            self.trailing_stop_manager.remove_position(pos.symbol)
            self.exposure_tracker.remove_position(pos.symbol)
            
        except Exception as e:
            logger.error(f"Failed to close {pos.symbol}: {e}")
    
    def _calc_pnl_pct(self, pos: FuturesPosition) -> float:
        """Calculate leveraged P&L percentage."""
        position_value = pos.entry_price * pos.quantity
        margin_used = position_value / pos.leverage if pos.leverage > 0 else position_value
        return (pos.unrealized_pnl / margin_used) * 100 if margin_used > 0 else 0
    
    async def _monitor_positions(self, cycle: int):
        """Monitor and manage open positions."""
        try:
            positions = self.client.get_positions()
            
            if not positions:
                return
            
            total_pnl = 0
            for pos in positions:
                pnl_pct = self._calc_pnl_pct(pos)
                total_pnl += pos.unrealized_pnl
                await self._check_exit_conditions(pos, pnl_pct)
            
            self.daily_pnl = total_pnl
            self.cash_cow.update_daily_pnl(self.daily_pnl, self.starting_balance)
            
        except Exception as e:
            logger.error(f"Monitor error: {e}")
    
    async def _check_exit_conditions(self, pos: FuturesPosition, pnl_pct: float):
        """Check scaled exits and trailing stops."""
        symbol = pos.symbol
        
        # Skip dust positions
        notional = pos.quantity * pos.mark_price
        if notional < 5:
            if symbol in self.position_states:
                del self.position_states[symbol]
            self.trailing_stop_manager.remove_position(symbol)
            return
        
        if symbol not in self.position_states:
            gate_result = self._gate_results.get(symbol)
            dynamic_stop = -gate_result.stop_loss_pct if gate_result else -3.0
            self.position_states[symbol] = PositionState(
                symbol=symbol,
                original_qty=pos.quantity,
                entry_price=pos.entry_price,
                stop_loss_pct=dynamic_stop
            )
        
        state = self.position_states[symbol]
        if pnl_pct > state.peak_pnl_pct:
            state.peak_pnl_pct = pnl_pct
        
        # ATR trailing stop
        atr_14 = self._atr_cache.get(symbol, pos.entry_price * 0.02)
        direction = "LONG" if pos.side == "LONG" else "SHORT"
        trailing_state, should_close = self.trailing_stop_manager.update(
            symbol=symbol,
            current_price=pos.mark_price,
            entry_price=pos.entry_price,
            direction=direction,
            atr_14=atr_14,
        )
        
        if should_close:
            logger.info(f"🔒 {symbol}: ATR TRAILING STOP at {pnl_pct:.2f}%")
            await self._close_position(pos, "ATR_TRAILING_STOP", is_winner=True)
            return
        
        # Stop loss
        if not state.tp1_done and pnl_pct <= state.stop_loss_pct:
            logger.warning(f"🛑 {symbol}: STOP LOSS at {pnl_pct:.2f}%")
            await self._close_position(pos, "STOP_LOSS", is_winner=False)
            return
        
        # Breakeven stop after TP1
        if state.tp1_done and not state.tp2_done and pnl_pct <= 0:
            logger.warning(f"⚖️ {symbol}: BREAKEVEN STOP at {pnl_pct:.2f}%")
            await self._close_position(pos, "BREAKEVEN_STOP", is_winner=True)
            return
        
        # TP1: Close 25% at +1.5%
        if not state.tp1_done and pnl_pct >= 1.5:
            close_qty = round(state.original_qty * 0.25, self._get_qty_decimals(symbol))
            if close_qty > 0:
                logger.info(f"💰 {symbol}: TP1 HIT at {pnl_pct:.2f}%")
                await self._partial_close(pos, close_qty, "TP1")
                state.tp1_done = True
            return
        
        # TP2: Close another 25% at +2.5%
        if state.tp1_done and not state.tp2_done and pnl_pct >= 2.5:
            close_qty = round(state.original_qty * 0.25, self._get_qty_decimals(symbol))
            if close_qty > 0:
                logger.info(f"💰 {symbol}: TP2 HIT at {pnl_pct:.2f}%")
                await self._partial_close(pos, close_qty, "TP2")
                state.tp2_done = True
    
    def _get_qty_decimals(self, symbol: str) -> int:
        """Get quantity decimal places."""
        precision_map = {
            "BTCUSDT": 3, "ETHUSDT": 3, "BNBUSDT": 2, "SOLUSDT": 0,
            "XRPUSDT": 0, "ADAUSDT": 0, "DOGEUSDT": 0, "AVAXUSDT": 0,
            "DOTUSDT": 1, "LINKUSDT": 1,
        }
        return precision_map.get(symbol, 0)
    
    async def _partial_close(self, pos: FuturesPosition, quantity: float, reason: str):
        """Close a partial position."""
        try:
            close_side = "SELL" if pos.side == "LONG" else "BUY"
            self.client.place_market_order(
                symbol=pos.symbol, side=close_side, quantity=quantity, reduce_only=True
            )
            logger.info(f"✅ Partial close {pos.symbol}: {reason}")
        except Exception as e:
            logger.error(f"Failed partial close {pos.symbol}: {e}")
    
    async def _close_position(self, pos: FuturesPosition, reason: str, is_winner: bool):
        """Close entire position."""
        try:
            close_side = "SELL" if pos.side == "LONG" else "BUY"
            quantity = pos.quantity
            notional = quantity * pos.mark_price
            
            if notional < 5:
                if pos.symbol in self.position_states:
                    del self.position_states[pos.symbol]
                return
            
            self.client.place_market_order(
                symbol=pos.symbol, side=close_side, quantity=quantity, reduce_only=True
            )
            logger.info(f"✅ Closed {pos.symbol}: {reason} | P&L: ${pos.unrealized_pnl:+.2f}")
            
            self.cash_cow.record_trade_result(is_winner)
            
            if not is_winner:
                self.quality_gate.record_loss(pos.symbol)
            
            if pos.symbol in self.position_states:
                del self.position_states[pos.symbol]
            self.trailing_stop_manager.remove_position(pos.symbol)
            self.exposure_tracker.remove_position(pos.symbol)
            
        except Exception as e:
            logger.error(f"Failed to close {pos.symbol}: {e}")
    
    def _get_dynamic_max_positions(self, market_regime: str) -> int:
        """Get dynamic max positions based on market regime.
        
        Aggressive capital deployment:
        - TRENDING: 12 positions - maximum opportunities
        - SIDEWAYS: 10 positions - moderate
        - CHOPPY: 8 positions - still aggressive but cautious
        """
        if market_regime == "TRENDING":
            return 12  # Max positions in trending
        elif market_regime == "SIDEWAYS":
            return 10  # Medium positions in sideways
        else:  # CHOPPY or unknown
            return 8   # Min positions but still aggressive
    
    def _get_dynamic_leverage(self, market_regime: str, confidence: int) -> int:
        """Get dynamic leverage based on market regime and confidence.
        
        - TRENDING + high confidence: max leverage (12-15x)
        - SIDEWAYS: medium leverage (8x)
        - CHOPPY: low leverage (5x)
        """
        if market_regime == "TRENDING":
            base_leverage = self.config.futures_leverage_trending  # 12x
            # Boost for high confidence
            if confidence >= 80:
                return min(base_leverage + 3, self.config.futures_leverage_max)
            return base_leverage
        elif market_regime == "SIDEWAYS":
            return self.config.futures_leverage_sideways  # 8x
        else:  # CHOPPY
            return self.config.futures_leverage_choppy  # 5x
    
    async def _scan_and_trade(self, cycle: int):
        """Scan market and open new positions with dynamic limits."""
        if not self.cash_cow.circuit_breaker.can_enter_new_trade():
            return
        
        try:
            positions = self.client.get_positions()
            active_positions = [p for p in positions if p.quantity * p.mark_price >= 5]
            position_symbols = {p.symbol for p in active_positions}
            
            # Sync exposure tracker with actual positions (handles manual closes)
            total_wallet = self.client.get_total_wallet_balance()
            self.exposure_tracker.sync_with_positions(position_symbols, total_wallet, active_positions)
            
            # Get current balance and calculate target utilization
            balance = self.client.get_usdt_balance()
            target_utilization = balance * (self.config.futures_capital_utilization_pct / 100)
            
            # Calculate current margin used
            current_margin_used = sum(
                (p.quantity * p.entry_price) / p.leverage 
                for p in active_positions if p.leverage > 0
            )
            remaining_capital = target_utilization - current_margin_used
            
            # Use configured watchlist
            symbols = self.config.futures_watchlist
            
            # Track overall market regime for dynamic limits
            regime_votes = {"TRENDING": 0, "SIDEWAYS": 0, "CHOPPY": 0}
            
            for idx, symbol in enumerate(symbols):
                # Send heartbeat every 5 symbols to prevent timeout warnings
                if idx > 0 and idx % 5 == 0:
                    self.send_heartbeat()
                
                # Delay between symbols to avoid rate limiting (testnet is stricter)
                if idx > 0:
                    await asyncio.sleep(0.5)  # 500ms between symbols
                
                if symbol in position_symbols:
                    continue
                
                if self.quality_gate.is_blacklisted(symbol):
                    continue
                
                # Check dynamic position limit
                dynamic_max = self._get_dynamic_max_positions(self._market_regime)
                if len(active_positions) >= dynamic_max:
                    logger.debug(f"Max positions ({dynamic_max}) reached for {self._market_regime} regime")
                    break
                
                # Check if we have capital left
                if remaining_capital < 50:  # Less than $50 remaining
                    logger.debug(f"Capital utilization target reached: ${current_margin_used:.2f}/${target_utilization:.2f}")
                    break
                
                try:
                    ohlcv_data = await self._get_ohlcv(symbol)
                    if not ohlcv_data:
                        continue
                    
                    enhanced_signal, market_regime = await self._analyze_enhanced(symbol, ohlcv_data)
                    if not enhanced_signal:
                        continue
                    
                    # Track regime votes
                    if market_regime:
                        regime_key = market_regime.upper()
                        if regime_key in regime_votes:
                            regime_votes[regime_key] += 1
                    
                    # Calculate indicators
                    indicators_15m = self._calculate_indicators(ohlcv_data.get("15m", []))
                    
                    # Get regime string for confidence check
                    regime_str = market_regime.upper() if market_regime else "UNKNOWN"
                    
                    # Aggressive position sizing with regime-aware confidence
                    position_result = self.position_sizer.calculate(
                        confidence=enhanced_signal.confidence,
                        available_capital=balance,
                        current_exposure=self.exposure_tracker.get_current_exposure(),
                        max_exposure=self.config.futures_capital_utilization_pct / 100,  # 90%
                        market_regime=regime_str,
                    )
                    
                    if position_result.is_rejected:
                        continue
                    
                    # Dynamic leverage based on regime
                    leverage = self._get_dynamic_leverage(regime_str, enhanced_signal.confidence)
                    
                    # Clamp leverage to config bounds
                    leverage = max(self.config.futures_leverage_min, 
                                   min(leverage, self.config.futures_leverage_max))
                    
                    # ATR stop
                    atr_14 = indicators_15m.get("atr", enhanced_signal.entry_price * 0.02)
                    self._atr_cache[symbol] = atr_14
                    
                    self.exposure_tracker.add_position(symbol, position_result.size_pct)
                    
                    logger.info(
                        f"✨ {symbol}: SIGNAL {enhanced_signal.direction} | "
                        f"Confidence={enhanced_signal.confidence} | "
                        f"Size=${position_result.size_usd:.0f} ({position_result.size_pct:.0%}) | "
                        f"Leverage={leverage}x | Regime={regime_str}"
                    )
                    
                    await self._execute_signal(enhanced_signal, position_result.size_usd, leverage)
                    
                    # Update tracking
                    balance = self.client.get_usdt_balance()
                    positions = self.client.get_positions()
                    active_positions = [p for p in positions if p.quantity * p.mark_price >= 5]
                    position_symbols.add(symbol)
                    
                    # Recalculate remaining capital
                    current_margin_used = sum(
                        (p.quantity * p.entry_price) / p.leverage 
                        for p in active_positions if p.leverage > 0
                    )
                    remaining_capital = target_utilization - current_margin_used
                    
                except Exception as e:
                    logger.debug(f"Error analyzing {symbol}: {e}")
            
            # Update overall market regime based on votes
            if sum(regime_votes.values()) > 0:
                self._market_regime = max(regime_votes, key=regime_votes.get)
                self._current_max_positions = self._get_dynamic_max_positions(self._market_regime)
            
            # Log status every 5 cycles
            if cycle % 5 == 0:
                utilization_pct = (current_margin_used / target_utilization * 100) if target_utilization > 0 else 0
                logger.info(
                    f"📊 Status: {len(active_positions)}/{self._current_max_positions} positions | "
                    f"Margin: ${current_margin_used:.0f}/${target_utilization:.0f} ({utilization_pct:.0f}%) | "
                    f"Regime: {self._market_regime}"
                )
            
        except Exception as e:
            logger.error(f"Scanner error: {e}")
    
    async def _get_ohlcv(self, symbol: str) -> Optional[Dict[str, List[OHLCV]]]:
        """Get OHLCV data for multiple timeframes."""
        try:
            ohlcv_data = {}
            for tf, interval in [("4h", "4h"), ("1h", "1h"), ("15m", "15m"), ("5m", "5m"), ("1m", "1m")]:
                klines = self.client.get_klines(symbol, interval, 50)
                ohlcv_data[tf] = [
                    OHLCV(timestamp=k[0], open=k[1], high=k[2], low=k[3], close=k[4], volume=k[5])
                    for k in klines
                ]
            return ohlcv_data
        except Exception:
            return None
    
    async def _analyze_enhanced(self, symbol: str, ohlcv_data: Dict) -> tuple[Optional[Signal], Optional[str]]:
        """Analyze using enhanced TA analyzer."""
        try:
            ohlcv_4h = [EnhancedOHLCV(o.open, o.high, o.low, o.close, o.volume) for o in ohlcv_data.get("4h", [])]
            ohlcv_1h = [EnhancedOHLCV(o.open, o.high, o.low, o.close, o.volume) for o in ohlcv_data.get("1h", [])]
            ohlcv_15m = [EnhancedOHLCV(o.open, o.high, o.low, o.close, o.volume) for o in ohlcv_data.get("15m", [])]
            
            indicators_4h = self._calculate_indicators(ohlcv_data.get("4h", []))
            indicators_1h = self._calculate_indicators(ohlcv_data.get("1h", []))
            indicators_15m = self._calculate_indicators(ohlcv_data.get("15m", []))
            
            enhanced_signal = self.enhanced_analyzer.analyze(
                symbol=symbol,
                ohlcv_4h=ohlcv_4h, ohlcv_1h=ohlcv_1h, ohlcv_15m=ohlcv_15m,
                indicators_4h=indicators_4h, indicators_1h=indicators_1h, indicators_15m=indicators_15m,
                btc_indicators_4h={}, is_altcoin=symbol != "BTCUSDT",
            )
            
            market_regime = None
            if enhanced_signal and enhanced_signal.market_context:
                regime = enhanced_signal.market_context.market_regime
                market_regime = regime.value if hasattr(regime, 'value') else str(regime)
            
            return enhanced_signal, market_regime
        except Exception:
            return None, None
    
    def _calculate_indicators(self, ohlcv: List[OHLCV]) -> Dict[str, float]:
        """Calculate technical indicators."""
        if not ohlcv or len(ohlcv) < 21:
            return {}
        
        closes = [c.close for c in ohlcv]
        highs = [c.high for c in ohlcv]
        lows = [c.low for c in ohlcv]
        volumes = [c.volume for c in ohlcv]
        
        def ema(data, period):
            if len(data) < period:
                return data[-1] if data else 0
            multiplier = 2 / (period + 1)
            ema_val = sum(data[:period]) / period
            for price in data[period:]:
                ema_val = (price - ema_val) * multiplier + ema_val
            return ema_val
        
        def atr(highs, lows, closes, period=14):
            if len(closes) < period + 1:
                return closes[-1] * 0.02 if closes else 0
            trs = []
            for i in range(1, len(closes)):
                tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
                trs.append(tr)
            return sum(trs[-period:]) / period
        
        atr_val = atr(highs, lows, closes)
        avg_volume = sum(volumes[-20:]) / min(20, len(volumes))
        current_volume = volumes[-1] if volumes else 0
        
        return {
            "ema_9": ema(closes, 9),
            "ema_21": ema(closes, 21),
            "atr": atr_val,
            "atr_pct": (atr_val / closes[-1]) * 100 if closes[-1] > 0 else 0,
            "volume_ratio": current_volume / avg_volume if avg_volume > 0 else 1.0,
        }
    
    def _convert_to_pt_regime(self, regime_str: Optional[str]) -> PTMarketRegime:
        """Convert regime string to PTMarketRegime."""
        if not regime_str:
            return PTMarketRegime.TRENDING
        mapping = {
            "TRENDING": PTMarketRegime.TRENDING,
            "CHOPPY": PTMarketRegime.CHOPPY,
            "HIGH_VOLATILITY": PTMarketRegime.CHOPPY,
            "LOW_VOLATILITY": PTMarketRegime.SIDEWAYS,
            "SIDEWAYS": PTMarketRegime.SIDEWAYS,
        }
        return mapping.get(regime_str.upper(), PTMarketRegime.TRENDING)
    
    async def _execute_signal(self, signal: Signal, position_size: float, leverage: int):
        """Execute a trading signal."""
        try:
            symbol = signal.symbol
            
            try:
                self.client.set_leverage(symbol, leverage)
            except Exception:
                pass
            
            quantity = (position_size * leverage) / signal.entry_price
            qty_precision = self._get_qty_decimals(symbol)
            quantity = round(quantity, qty_precision)
            
            notional = quantity * signal.entry_price
            if notional < 20:
                quantity = round(20 / signal.entry_price, qty_precision)
            
            side = "BUY" if signal.direction == "LONG" else "SELL"
            
            self.client.place_market_order(symbol=symbol, side=side, quantity=quantity)
            
            self.trade_count += 1
            self._last_trade_time = datetime.now()
            logger.info(f"🎉 TRADE #{self.trade_count}: {symbol} {signal.direction} @ ${signal.entry_price:.4f}")
            
        except Exception as e:
            logger.error(f"Failed to execute signal: {e}")
