#!/usr/bin/env python3
"""Kinetic Empire Trading Bot - LIVE Binance Demo Trading.

The main trading bot combining all features:
- Cash Cow 130-point opportunity scoring
- Dynamic position sizing (5-15% of portfolio based on confidence)
- Dynamic leverage (10-20x based on confidence)
- Consecutive loss protection
- Circuit breaker (5% daily loss halt)
- Multi-timeframe alignment bonuses
- Scaled exits with trailing stops

Usage:
    python run_bot.py --capital 5000
"""

import asyncio
import logging
import os
import signal
import sys
from datetime import datetime
from typing import Dict, List, Optional

from dotenv import load_dotenv

load_dotenv(override=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.kinetic_empire.futures.client import BinanceFuturesClient, FuturesPosition
from src.kinetic_empire.v3.analyzer.enhanced import EnhancedTAAnalyzer, OHLCV as EnhancedOHLCV
from src.kinetic_empire.v3.core.models import Ticker, OHLCV, Signal

# Cash Cow components
from src.kinetic_empire.cash_cow.engine import CashCowEngine, TradeEvaluation
from src.kinetic_empire.cash_cow.scorer import ScoringFeatures
from src.kinetic_empire.cash_cow.models import MarketRegime, OpportunityScore
from src.kinetic_empire.cash_cow.config import CashCowConfig

# Signal Quality Gate
from src.kinetic_empire.signal_quality import (
    SignalQualityGate,
    QualityGateConfig,
    QualityGateResult,
    MarketRegime as SQMarketRegime,
    OHLCV as SQOHLCV,
)

# Profitable Trading Overhaul Components
from src.kinetic_empire.profitable_trading import (
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
from src.kinetic_empire.profitable_trading.direction_validator import OHLCV as PTOHLCV

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)-8s | %(name)-40s | %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"logs/kinetic_{datetime.now():%Y%m%d_%H%M%S}.log"),
    ],
)
logger = logging.getLogger(__name__)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)


class PositionState:
    """Track state for scaled exits and trailing stops."""
    def __init__(self, symbol: str, original_qty: float, entry_price: float, stop_loss_pct: float = -4.0):
        self.symbol = symbol
        self.original_qty = original_qty
        self.entry_price = entry_price
        self.stop_loss_pct = stop_loss_pct  # Dynamic stop from quality gate
        self.tp1_done = False
        self.tp2_done = False
        self.peak_pnl_pct = 0.0


class CashCowLiveEngine:
    """Cash Cow Engine with real Binance execution."""
    
    def __init__(self, client: BinanceFuturesClient, capital: float = 5000):
        self.client = client
        self.capital = capital
        self.enhanced_analyzer = EnhancedTAAnalyzer()
        
        # Initialize Cash Cow engine with AGGRESSIVE config
        config = CashCowConfig(
            base_risk_pct=5.0,           # 5% base risk - AGGRESSIVE
            max_position_pct=15.0,       # 15% max position
            high_confidence_threshold=85,
            medium_confidence_threshold=75,
            low_confidence_threshold=60,  # Lower threshold for more trades
            daily_loss_limit_pct=5.0,    # 5% daily loss circuit breaker
        )
        self.cash_cow = CashCowEngine(config)
        
        # Initialize Signal Quality Gate for improved signal filtering
        self.quality_gate = SignalQualityGate(QualityGateConfig())
        
        # Profitable Trading Overhaul Components
        self.regime_detector = RegimeDetector()
        self.direction_validator = DirectionValidator()
        self.position_sizer = ConfidencePositionSizer()
        self.leverage_calculator = RegimeLeverageCalculator()
        self.atr_stop_calculator = ATRStopCalculator()
        self.trailing_stop_manager = ATRTrailingStopManager()
        self.exposure_tracker = ExposureTracker(max_exposure_pct=0.45)
        self.entry_confirmer = EntryConfirmer()
        
        # Trading config - STRICTER thresholds per profitable-trading-overhaul spec
        self.max_positions = 3  # Reduced from 5 to focus on quality
        self.min_cash_cow_score = 75  # Raised from 65 to be more selective
        self.min_confidence = 50  # Minimum confidence per spec
        
        # DYNAMIC LEVERAGE based on regime and confidence (2x-10x per spec)
        self.leverage_tiers = {
            90: 10,   # High confidence in trending = 10x
            70: 7,    # Medium confidence = 7x
            50: 5,    # Low confidence = 5x
        }
        
        # Exit config - ATR-based stops per profitable-trading-overhaul spec
        self.tp1_pct = 1.5
        self.tp2_pct = 2.5
        self.stop_loss_pct = -3.0  # Default stop (ATR-based will override)
        self.trailing_activation_pct = 2.0  # Activate trailing at 2% profit
        self.trailing_distance = 1.5  # 1.5x ATR trailing (tightens to 1.0x at 5%)
        
        # State
        self.running = False
        self.trade_count = 0
        self.position_states: Dict[str, PositionState] = {}
        self.daily_pnl = 0.0
        self.starting_balance = 0.0

    async def start(self):
        """Start the Cash Cow live trading engine."""
        self.running = True
        logger.info("=" * 70)
        logger.info("🚀 KINETIC EMPIRE TRADING BOT - LIVE BINANCE DEMO")
        logger.info("=" * 70)
        
        try:
            balance = self.client.get_usdt_balance()
            self.starting_balance = balance
            positions = self.client.get_positions()
            
            logger.info(f"✅ Connected to Binance Demo Account")
            logger.info(f"   💰 Available Balance: ${balance:.2f}")
            logger.info(f"   📊 Open Positions: {len(positions)}")
            logger.info(f"   🎯 PROFITABLE TRADING OVERHAUL ACTIVE:")
            logger.info(f"      • STRICT regime enforcement (NO CHOPPY/SIDEWAYS trades)")
            logger.info(f"      • Dynamic position sizing: 5-15% based on confidence")
            logger.info(f"      • Adaptive leverage: 2x-10x based on regime")
            logger.info(f"      • ATR-based stops: 2.0x-3.0x ATR (1%-5% bounds)")
            logger.info(f"      • ATR trailing stops: activate at 2%, tighten at 5%")
            logger.info(f"      • Fast blacklist: 1 loss = 60-min ban")
            logger.info(f"      • Max exposure: 45% portfolio cap")
            
            for pos in positions:
                pnl_pct = self._calc_pnl_pct(pos)
                logger.info(f"      {pos.symbol}: {pos.side} @ ${pos.entry_price:.4f} | P&L: {pnl_pct:+.2f}%")
        except Exception as e:
            logger.error(f"❌ Failed to connect: {e}")
            return
        
        logger.info("=" * 70)
        logger.info("🔄 Starting trading loop... Press Ctrl+C to stop")
        logger.info("=" * 70)
        
        scan_cycle = 0
        monitor_cycle = 0
        
        while self.running:
            try:
                monitor_cycle += 1
                await self._monitor_positions(monitor_cycle)
                
                if monitor_cycle % 6 == 1:
                    scan_cycle += 1
                    await self._scan_and_trade(scan_cycle)
                
                await asyncio.sleep(5)
                
            except KeyboardInterrupt:
                logger.info("👋 Stopping Cash Cow...")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(10)
        
        self.running = False
        logger.info("🛑 Cash Cow stopped")

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
                if cycle % 6 == 0:
                    status = self.cash_cow.get_status()
                    logger.debug(f"━━━ MONITOR #{cycle} | No positions | Losses: {status['consecutive_losses']} | Can trade: {status['can_trade']} ━━━")
                return
            
            logger.debug(f"━━━ MONITOR CYCLE #{cycle} ({len(positions)} positions) ━━━")
            
            total_pnl = 0
            for pos in positions:
                pnl_pct = self._calc_pnl_pct(pos)
                total_pnl += pos.unrealized_pnl
                
                emoji = "📈" if pos.unrealized_pnl >= 0 else "📉"
                logger.debug(
                    f"   {emoji} {pos.symbol}: {pos.side} @ ${pos.entry_price:.4f} → ${pos.mark_price:.4f} | "
                    f"P&L: {pnl_pct:+.2f}% (${pos.unrealized_pnl:+.2f})"
                )
                
                await self._check_exit_conditions(pos, pnl_pct)
            
            # Update daily P&L for circuit breaker
            self.daily_pnl = total_pnl
            self.cash_cow.update_daily_pnl(self.daily_pnl, self.starting_balance)
            
            logger.debug(f"   💵 Total Unrealized P&L: ${total_pnl:+.2f}")
            
        except Exception as e:
            logger.error(f"Monitor error: {e}")

    async def _check_exit_conditions(self, pos: FuturesPosition, pnl_pct: float):
        """Check scaled exits and ATR-based trailing stops per profitable-trading-overhaul spec."""
        symbol = pos.symbol
        
        # DUST POSITION CLEANUP: If position is too small to trade, just ignore it
        notional = pos.quantity * pos.mark_price
        if notional < 5:
            if symbol in self.position_states:
                del self.position_states[symbol]
            self.trailing_stop_manager.remove_position(symbol)
            return
        
        if symbol not in self.position_states:
            # Get dynamic stop loss from quality gate if available
            gate_results = getattr(self, '_gate_results', {})
            gate_result = gate_results.get(symbol)
            dynamic_stop = -gate_result.stop_loss_pct if gate_result else self.stop_loss_pct
            
            self.position_states[symbol] = PositionState(
                symbol=symbol,
                original_qty=pos.quantity,
                entry_price=pos.entry_price,
                stop_loss_pct=dynamic_stop
            )
        state = self.position_states[symbol]
        
        if pnl_pct > state.peak_pnl_pct:
            state.peak_pnl_pct = pnl_pct
        
        # Get ATR for trailing stop calculation
        atr_data = getattr(self, '_atr_cache', {})
        atr_14 = atr_data.get(symbol, pos.entry_price * 0.02)  # Default 2% if no ATR
        
        # ATR-based trailing stop per profitable-trading-overhaul spec
        # Activates at 2% profit, trails at 1.5x ATR, tightens to 1.0x at 5%
        direction = "LONG" if pos.side == "LONG" else "SHORT"
        trailing_state, should_close = self.trailing_stop_manager.update(
            symbol=symbol,
            current_price=pos.mark_price,
            entry_price=pos.entry_price,
            direction=direction,
            atr_14=atr_14,
        )
        
        if should_close:
            logger.info(
                f"🔒 {symbol}: ATR TRAILING STOP at {pnl_pct:.2f}% "
                f"(peak: {trailing_state.peak_profit_pct:.2f}%, trail: {trailing_state.trail_multiplier}x ATR)"
            )
            await self._close_position(pos, "ATR_TRAILING_STOP", is_winner=True)
            return
        
        # Stop loss - use dynamic stop from quality gate
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
        if not state.tp1_done and pnl_pct >= self.tp1_pct:
            close_qty = round(state.original_qty * 0.25, self._get_qty_decimals(symbol))
            if close_qty > 0:
                logger.info(f"💰 {symbol}: TP1 HIT at {pnl_pct:.2f}% - Closing 25%")
                await self._partial_close(pos, close_qty, "TP1")
                state.tp1_done = True
            return
        
        # TP2: Close another 25% at +2.5%
        if state.tp1_done and not state.tp2_done and pnl_pct >= self.tp2_pct:
            close_qty = round(state.original_qty * 0.25, self._get_qty_decimals(symbol))
            if close_qty > 0:
                logger.info(f"💰 {symbol}: TP2 HIT at {pnl_pct:.2f}% - Closing 25%")
                await self._partial_close(pos, close_qty, "TP2")
                state.tp2_done = True
            return


    def _get_qty_decimals(self, symbol: str) -> int:
        """Get quantity decimal places for partial closes."""
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
            result = self.client.place_market_order(
                symbol=pos.symbol, side=close_side, quantity=quantity, reduce_only=True
            )
            logger.info(f"✅ Partial close {pos.symbol}: {reason} | Qty: {quantity}")
            return result
        except Exception as e:
            logger.error(f"Failed partial close {pos.symbol}: {e}")
            return None

    async def _close_position(self, pos: FuturesPosition, reason: str, is_winner: bool):
        """Close entire remaining position."""
        try:
            close_side = "SELL" if pos.side == "LONG" else "BUY"
            
            # Use actual position quantity from Binance
            quantity = pos.quantity
            
            # Check minimum notional ($5 on Binance)
            notional = quantity * pos.mark_price
            if notional < 5:
                logger.warning(f"⚠️ {pos.symbol}: Position notional ${notional:.2f} too small, skipping close")
                # Clean up state since position is negligible
                if pos.symbol in self.position_states:
                    del self.position_states[pos.symbol]
                return None
            
            logger.debug(f"   Closing {pos.symbol}: qty={quantity}, side={close_side}, notional=${notional:.2f}")
            
            result = self.client.place_market_order(
                symbol=pos.symbol, side=close_side, quantity=quantity, reduce_only=True
            )
            logger.info(f"✅ Closed {pos.symbol}: {reason} | P&L: ${pos.unrealized_pnl:+.2f}")
            
            # Record result for Cash Cow loss tracking
            self.cash_cow.record_trade_result(is_winner)
            
            # Record loss for blacklist tracking (only on stop-loss exits)
            if not is_winner:
                was_blacklisted = self.quality_gate.record_loss(pos.symbol)
                if was_blacklisted:
                    logger.warning(f"⛔ {pos.symbol}: Blacklisted after 1 loss (60-min ban)")
            
            # Clean up state
            if pos.symbol in self.position_states:
                del self.position_states[pos.symbol]
            self.trailing_stop_manager.remove_position(pos.symbol)
            self.exposure_tracker.remove_position(pos.symbol)
            
            return result
        except Exception as e:
            logger.error(f"Failed to close {pos.symbol} (qty={pos.quantity}): {e}")
            return None

    async def _scan_and_trade(self, cycle: int):
        """Scan market and open new positions using Cash Cow scoring."""
        logger.debug(f"━━━ CASH COW SCANNER #{cycle} ━━━")
        
        # Check circuit breaker
        if not self.cash_cow.circuit_breaker.can_enter_new_trade():
            logger.warning(f"   🚨 CIRCUIT BREAKER ACTIVE - No new trades!")
            return
        
        try:
            positions = self.client.get_positions()
            # Filter out dust positions (< $5 notional) - they don't count toward max
            active_positions = [p for p in positions if p.quantity * p.mark_price >= 5]
            position_symbols = {p.symbol for p in positions}  # Still track all symbols
            
            if len(active_positions) >= self.max_positions:
                logger.debug(f"   Max positions reached ({len(active_positions)}/{self.max_positions})")
                return
            
            balance = self.client.get_usdt_balance()
            logger.debug(f"   💰 Available: ${balance:.2f}")
            
            # Get Cash Cow status
            status = self.cash_cow.get_status()
            logger.debug(f"   🐄 Consecutive losses: {status['consecutive_losses']} | Protection: {status['loss_protection_multiplier']:.2f}x")
            
            symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", 
                      "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT"]
            
            # Get BTC data for correlation
            btc_ohlcv = await self._get_ohlcv("BTCUSDT")
            btc_indicators = self._calculate_indicators(btc_ohlcv.get("4h", [])) if btc_ohlcv else {}
            
            for symbol in symbols:
                if symbol in position_symbols:
                    continue
                
                # Check blacklist first
                if self.quality_gate.is_blacklisted(symbol):
                    logger.debug(f"   ⛔ {symbol}: Blacklisted - skipping")
                    continue
                
                try:
                    ohlcv_data = await self._get_ohlcv(symbol)
                    if not ohlcv_data:
                        continue
                    
                    # Get enhanced analysis
                    enhanced_signal, market_regime = await self._analyze_enhanced(
                        symbol, ohlcv_data, btc_indicators, symbol != "BTCUSDT"
                    )
                    
                    if not enhanced_signal:
                        continue
                    
                    # Calculate Cash Cow score
                    indicators = self._calculate_indicators(ohlcv_data.get("4h", []))
                    indicators_15m = self._calculate_indicators(ohlcv_data.get("15m", []))
                    cash_cow_score = self._calculate_cash_cow_score(
                        enhanced_signal, indicators, market_regime
                    )
                    
                    # Convert OHLCV for Signal Quality Gate
                    ohlcv_15m_sq = [SQOHLCV(o.open, o.high, o.low, o.close, o.volume) 
                                   for o in ohlcv_data.get("15m", [])]
                    ohlcv_1m_sq = [SQOHLCV(o.open, o.high, o.low, o.close, o.volume) 
                                  for o in ohlcv_data.get("1m", [])]
                    ohlcv_5m_sq = [SQOHLCV(o.open, o.high, o.low, o.close, o.volume) 
                                  for o in ohlcv_data.get("5m", [])]
                    
                    # Get support/resistance from enhanced signal
                    current_price = enhanced_signal.entry_price
                    resistance = enhanced_signal.market_context.support_resistance.nearest_resistance if enhanced_signal.market_context else current_price * 1.05
                    support = enhanced_signal.market_context.support_resistance.nearest_support if enhanced_signal.market_context else current_price * 0.95
                    volume_ratio = indicators_15m.get("volume_ratio", 1.0)
                    
                    # Convert regime for quality gate
                    sq_regime = self._convert_to_sq_regime(market_regime)
                    
                    # Run through Signal Quality Gate
                    gate_result = self.quality_gate.evaluate(
                        symbol=symbol,
                        enhanced_confidence=enhanced_signal.confidence,
                        enhanced_direction=enhanced_signal.direction,
                        cash_cow_direction=enhanced_signal.direction,  # Use same for now
                        ohlcv_15m=ohlcv_15m_sq,
                        rsi_15m=indicators_15m.get("rsi", 50),
                        regime=sq_regime,
                        ohlcv_1m=ohlcv_1m_sq,
                        ohlcv_5m=ohlcv_5m_sq,
                        current_price=current_price,
                        resistance_level=resistance,
                        support_level=support,
                        volume_ratio=volume_ratio,
                        cash_cow_score=cash_cow_score,  # Pass for high-quality bypass
                    )
                    
                    # Log the score with gate result
                    logger.info(
                        f"   🐄 {symbol}: Cash Cow={cash_cow_score} | Enhanced={enhanced_signal.confidence} | "
                        f"Gate={'✅ PASS' if gate_result.passed else '❌ FAIL'} | Regime={market_regime}"
                    )
                    
                    if not gate_result.passed:
                        logger.debug(f"   ❌ {symbol}: Quality Gate rejected - {gate_result.rejection_reason}")
                        continue
                    
                    # Add bonuses from quality gate
                    total_score = cash_cow_score + gate_result.micro_bonus + gate_result.breakout_bonus
                    
                    # Check if score meets threshold
                    if total_score >= self.min_cash_cow_score:
                        # Use new ConfidencePositionSizer per profitable-trading-overhaul spec
                        # Position size: 5-15% based on confidence
                        position_result = self.position_sizer.calculate(
                            confidence=enhanced_signal.confidence,
                            available_capital=balance,
                            current_exposure=self.exposure_tracker.get_current_exposure(),
                            max_exposure=0.45,  # 45% max per spec
                        )
                        
                        if position_result.is_rejected:
                            logger.debug(f"   ❌ {symbol}: Position rejected - {position_result.rejection_reason}")
                            continue
                        
                        # Use new RegimeLeverageCalculator per profitable-trading-overhaul spec
                        # Leverage: 2x-10x based on regime and confidence
                        pt_regime = self._convert_to_pt_regime(market_regime)
                        leverage = self.leverage_calculator.calculate(
                            regime=pt_regime,
                            confidence=enhanced_signal.confidence,
                            consecutive_losses=self.cash_cow.loss_tracker.consecutive_losses,
                        )
                        
                        # Calculate ATR-based stop loss per spec
                        atr_14 = indicators_15m.get("atr", current_price * 0.02)
                        stop_result = self.atr_stop_calculator.calculate(
                            entry_price=current_price,
                            direction=gate_result.direction,
                            atr_14=atr_14,
                            regime=pt_regime,
                        )
                        
                        # Cache ATR for trailing stop calculations
                        self._atr_cache = getattr(self, '_atr_cache', {})
                        self._atr_cache[symbol] = atr_14
                        
                        # Store gate result for exit management
                        self._gate_results = getattr(self, '_gate_results', {})
                        self._gate_results[symbol] = gate_result
                        
                        # Track exposure
                        self.exposure_tracker.add_position(symbol, position_result.size_pct)
                        
                        logger.info(
                            f"   ✨ {symbol}: SIGNAL {gate_result.direction} | "
                            f"Score={total_score} | Confidence={enhanced_signal.confidence} ({position_result.confidence_tier}) | "
                            f"Size={position_result.size_pct:.0%} (${position_result.size_usd:.2f}) | "
                            f"Leverage={leverage}x | Stop={stop_result.stop_pct:.1%} (ATR={stop_result.atr_multiplier}x)"
                        )
                        
                        # Update signal direction from quality gate
                        enhanced_signal.direction = gate_result.direction
                        
                        await self._execute_signal(enhanced_signal, position_result.size_usd, enhanced_signal.confidence, gate_result)
                        
                        balance = self.client.get_usdt_balance()
                        positions = self.client.get_positions()
                        position_symbols.add(symbol)
                        
                        if len(positions) >= self.max_positions:
                            break
                    
                except Exception as e:
                    logger.debug(f"   Error analyzing {symbol}: {e}")
            
        except Exception as e:
            logger.error(f"Scanner error: {e}")


    def _calculate_cash_cow_score(
        self, signal: Signal, indicators: Dict, market_regime: Optional[str]
    ) -> int:
        """Calculate Cash Cow 130-point score from signal and indicators."""
        score = 0
        
        # Technical (0-40 points)
        # EMA crossover freshness
        ema_9 = indicators.get("ema_9", 0)
        ema_21 = indicators.get("ema_21", 0)
        if ema_21 > 0:
            ema_diff = abs(ema_9 - ema_21) / ema_21 * 100
            score += min(10, int(ema_diff * 5))
        
        # RSI zones
        rsi = indicators.get("rsi", 50)
        if 30 <= rsi <= 70:
            score += 10
        elif 20 <= rsi <= 80:
            score += 7
        else:
            score += 3
        
        # MACD (simplified)
        score += 8  # Base MACD score
        
        # VWAP proximity (simplified)
        score += 7  # Base VWAP score
        
        # Momentum (0-25 points)
        # ADX strength
        adx = indicators.get("adx", 25)
        if adx > 40:
            score += 10
        elif adx > 30:
            score += 8
        elif adx > 20:
            score += 5
        else:
            score += 2
        
        # Price momentum
        momentum = indicators.get("momentum", 0)
        if abs(momentum) > 3:
            score += 8
        elif abs(momentum) > 1:
            score += 5
        else:
            score += 2
        
        # DI spread
        score += 5  # Base DI score
        
        # Volume (0-20 points)
        volume_ratio = indicators.get("volume_ratio", 1.0)
        if volume_ratio > 2.0:
            score += 15
        elif volume_ratio > 1.5:
            score += 12
        elif volume_ratio > 1.2:
            score += 8
        else:
            score += 5
        
        # Volatility (0-15 points)
        atr_pct = indicators.get("atr_pct", 2.0)
        if 2.0 <= atr_pct <= 5.0:
            score += 15
        elif 1.5 <= atr_pct <= 7.0:
            score += 10
        else:
            score += 5
        
        # Regime (0-10 points)
        regime_scores = {
            "TRENDING": 10,
            "LOW_VOLATILITY": 8,
            "HIGH_VOLATILITY": 5,
            "SIDEWAYS": 3,
            "CHOPPY": 2,
        }
        score += regime_scores.get(market_regime, 5)
        
        # Sentiment (0-10 points) - use signal confidence as proxy
        if signal.confidence >= 70:
            score += 10
        elif signal.confidence >= 60:
            score += 7
        elif signal.confidence >= 50:
            score += 5
        else:
            score += 3
        
        # Growth potential (0-10 points)
        if volume_ratio > 1.5 and abs(momentum) > 2:
            score += 10
        elif volume_ratio > 1.2 or abs(momentum) > 1:
            score += 6
        else:
            score += 3
        
        return min(130, score)

    def _convert_regime(self, regime_str: Optional[str]) -> MarketRegime:
        """Convert regime string to MarketRegime enum."""
        if not regime_str:
            return MarketRegime.TRENDING
        
        mapping = {
            "TRENDING": MarketRegime.TRENDING,
            "BEAR": MarketRegime.BEAR,
            "CHOPPY": MarketRegime.CHOPPY,
            "HIGH_VOLATILITY": MarketRegime.HIGH_VOLATILITY,
            "LOW_VOLATILITY": MarketRegime.LOW_VOLATILITY,
            "SIDEWAYS": MarketRegime.CHOPPY,
        }
        return mapping.get(regime_str.upper(), MarketRegime.TRENDING)
    
    def _convert_to_sq_regime(self, regime_str: Optional[str]) -> SQMarketRegime:
        """Convert regime string to Signal Quality MarketRegime enum."""
        if not regime_str:
            return SQMarketRegime.TRENDING
        
        mapping = {
            "TRENDING": SQMarketRegime.TRENDING,
            "CHOPPY": SQMarketRegime.CHOPPY,
            "HIGH_VOLATILITY": SQMarketRegime.HIGH_VOLATILITY,
            "LOW_VOLATILITY": SQMarketRegime.LOW_VOLATILITY,
            "SIDEWAYS": SQMarketRegime.SIDEWAYS,
        }
        return mapping.get(regime_str.upper(), SQMarketRegime.TRENDING)
    
    def _convert_to_pt_regime(self, regime_str: Optional[str]) -> PTMarketRegime:
        """Convert regime string to Profitable Trading MarketRegime enum."""
        if not regime_str:
            return PTMarketRegime.TRENDING
        
        mapping = {
            "TRENDING": PTMarketRegime.TRENDING,
            "CHOPPY": PTMarketRegime.CHOPPY,
            "HIGH_VOLATILITY": PTMarketRegime.CHOPPY,  # Treat high vol as choppy
            "LOW_VOLATILITY": PTMarketRegime.SIDEWAYS,  # Treat low vol as sideways
            "SIDEWAYS": PTMarketRegime.SIDEWAYS,
        }
        return mapping.get(regime_str.upper(), PTMarketRegime.TRENDING)

    async def _get_ohlcv(self, symbol: str) -> Optional[Dict[str, List[OHLCV]]]:
        """Get OHLCV data for multiple timeframes including 1M and 5M."""
        try:
            ohlcv_data = {}
            # Include 1M and 5M for micro-timeframe analysis
            for tf, interval in [("4h", "4h"), ("1h", "1h"), ("15m", "15m"), ("5m", "5m"), ("1m", "1m")]:
                klines = self.client.get_klines(symbol, interval, 50)
                ohlcv_data[tf] = [
                    OHLCV(timestamp=k[0], open=k[1], high=k[2], low=k[3], close=k[4], volume=k[5])
                    for k in klines
                ]
            return ohlcv_data
        except Exception as e:
            logger.debug(f"Failed to get OHLCV for {symbol}: {e}")
            return None

    async def _analyze_enhanced(
        self, symbol: str, ohlcv_data: Dict, btc_indicators: Dict, is_altcoin: bool
    ) -> tuple[Optional[any], Optional[str]]:
        """Analyze using enhanced TA analyzer.
        
        Returns the EnhancedSignal directly to preserve market_context for quality gate.
        """
        try:
            ohlcv_4h = [EnhancedOHLCV(o.open, o.high, o.low, o.close, o.volume) 
                       for o in ohlcv_data.get("4h", [])]
            ohlcv_1h = [EnhancedOHLCV(o.open, o.high, o.low, o.close, o.volume) 
                       for o in ohlcv_data.get("1h", [])]
            ohlcv_15m = [EnhancedOHLCV(o.open, o.high, o.low, o.close, o.volume) 
                        for o in ohlcv_data.get("15m", [])]
            
            indicators_4h = self._calculate_indicators(ohlcv_data.get("4h", []))
            indicators_1h = self._calculate_indicators(ohlcv_data.get("1h", []))
            indicators_15m = self._calculate_indicators(ohlcv_data.get("15m", []))
            
            enhanced_signal = self.enhanced_analyzer.analyze(
                symbol=symbol,
                ohlcv_4h=ohlcv_4h, ohlcv_1h=ohlcv_1h, ohlcv_15m=ohlcv_15m,
                indicators_4h=indicators_4h, indicators_1h=indicators_1h, indicators_15m=indicators_15m,
                btc_indicators_4h=btc_indicators, is_altcoin=is_altcoin,
            )
            
            market_regime = None
            if enhanced_signal and enhanced_signal.market_context:
                regime = enhanced_signal.market_context.market_regime
                market_regime = regime.value if hasattr(regime, 'value') else str(regime)
            
            # Return the EnhancedSignal directly to preserve market_context
            return enhanced_signal, market_regime
        except Exception as e:
            logger.debug(f"Enhanced analysis error for {symbol}: {e}")
            return None, None


    def _calculate_indicators(self, ohlcv: List[OHLCV]) -> Dict[str, float]:
        """Calculate technical indicators from OHLCV data."""
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
        
        def rsi(data, period=14):
            if len(data) < period + 1:
                return 50
            gains, losses = [], []
            for i in range(1, len(data)):
                change = data[i] - data[i-1]
                gains.append(max(0, change))
                losses.append(max(0, -change))
            avg_gain = sum(gains[-period:]) / period
            avg_loss = sum(losses[-period:]) / period
            if avg_loss == 0:
                return 100
            rs = avg_gain / avg_loss
            return 100 - (100 / (1 + rs))
        
        def atr(highs, lows, closes, period=14):
            if len(closes) < period + 1:
                return closes[-1] * 0.02 if closes else 0
            trs = []
            for i in range(1, len(closes)):
                tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
                trs.append(tr)
            return sum(trs[-period:]) / period
        
        def adx(highs, lows, closes, period=14):
            if len(closes) < period + 1:
                return 25
            # Simplified ADX calculation
            plus_dm, minus_dm = [], []
            for i in range(1, len(highs)):
                up = highs[i] - highs[i-1]
                down = lows[i-1] - lows[i]
                plus_dm.append(up if up > down and up > 0 else 0)
                minus_dm.append(down if down > up and down > 0 else 0)
            
            atr_val = atr(highs, lows, closes, period)
            if atr_val == 0:
                return 25
            
            plus_di = 100 * sum(plus_dm[-period:]) / (period * atr_val)
            minus_di = 100 * sum(minus_dm[-period:]) / (period * atr_val)
            
            if plus_di + minus_di == 0:
                return 25
            
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
            return dx
        
        ema_9 = ema(closes, 9)
        ema_21 = ema(closes, 21)
        atr_val = atr(highs, lows, closes)
        rsi_val = rsi(closes)
        adx_val = adx(highs, lows, closes)
        avg_volume = sum(volumes[-20:]) / min(20, len(volumes))
        current_volume = volumes[-1] if volumes else 0
        
        # Momentum (rate of change)
        momentum = 0
        if len(closes) >= 10 and closes[-10] > 0:
            momentum = ((closes[-1] - closes[-10]) / closes[-10]) * 100
        
        return {
            "ema_9": ema_9,
            "ema_21": ema_21,
            "rsi": rsi_val,
            "atr": atr_val,
            "atr_pct": (atr_val / closes[-1]) * 100 if closes[-1] > 0 else 0,
            "adx": adx_val,
            "momentum": momentum,
            "volume_ratio": current_volume / avg_volume if avg_volume > 0 else 1.0,
        }

    def _get_dynamic_leverage(self, confidence: int) -> int:
        """Get leverage based on confidence score - higher confidence = more leverage."""
        for threshold, leverage in sorted(self.leverage_tiers.items(), reverse=True):
            if confidence >= threshold:
                return leverage
        return 10  # Default

    async def _execute_signal(self, signal: Signal, position_size: float, confidence: int = 70, gate_result: QualityGateResult = None):
        """Execute a trading signal with Cash Cow sizing and dynamic leverage."""
        try:
            symbol = signal.symbol
            
            # Dynamic leverage based on confidence, capped by quality gate
            leverage = self._get_dynamic_leverage(confidence)
            if gate_result:
                leverage = min(leverage, gate_result.max_leverage)
            
            try:
                self.client.set_leverage(symbol, leverage)
                logger.info(f"   🔧 Set leverage to {leverage}x (confidence: {confidence})")
            except Exception as e:
                logger.warning(f"   ⚠️ Could not set leverage: {e}")
            
            # Calculate quantity from position size with dynamic leverage
            # position_size is already calculated by Cash Cow sizer (5-15% of portfolio)
            quantity = (position_size * leverage) / signal.entry_price
            qty_precision = self._get_qty_decimals(symbol)
            quantity = round(quantity, qty_precision)
            
            # Ensure minimum notional ($20 for meaningful trades)
            notional = quantity * signal.entry_price
            if notional < 20:
                quantity = round(20 / signal.entry_price, qty_precision)
                notional = quantity * signal.entry_price
            
            side = "BUY" if signal.direction == "LONG" else "SELL"
            
            # Use regime-based stop loss from quality gate
            stop_pct = gate_result.stop_loss_pct if gate_result else self.stop_loss_pct
            
            logger.info(f"🎯 Opening {signal.direction} on {symbol}")
            logger.info(f"   💰 Position: ${position_size:.2f} x {leverage}x = ${notional:.2f} notional")
            logger.info(f"   📊 Entry: ${signal.entry_price:.4f} | Qty: {quantity} | Stop: {stop_pct}%")
            if gate_result and gate_result.use_tight_trailing:
                logger.info(f"   🎯 BREAKOUT TRADE - Using tight trailing stops")
            
            result = self.client.place_market_order(symbol=symbol, side=side, quantity=quantity)
            
            self.trade_count += 1
            logger.info(f"🎉 CASH COW TRADE #{self.trade_count}: {symbol} {signal.direction} @ ${signal.entry_price:.4f}")
            
            return result
        except Exception as e:
            logger.error(f"Failed to execute signal: {e}")
            return None


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Kinetic Empire Cash Cow - Live Trading")
    parser.add_argument("--capital", type=float, default=5000, help="Starting capital")
    parser.add_argument("--interval", type=int, default=60, help="Scan interval in seconds")
    args = parser.parse_args()
    
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    
    if not api_key or not api_secret:
        logger.error("❌ Missing BINANCE_API_KEY or BINANCE_API_SECRET in .env")
        return
    
    logger.info(f"🔑 Using API key: {api_key[:8]}...{api_key[-4:]}")
    
    client = BinanceFuturesClient(
        api_key=api_key,
        api_secret=api_secret,
        testnet=True
    )
    
    engine = CashCowLiveEngine(client, capital=args.capital)
    
    # Handle shutdown
    def signal_handler(sig, frame):
        logger.info("👋 Shutdown signal received...")
        engine.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    await engine.start()


if __name__ == "__main__":
    asyncio.run(main())
