"""Kinetic Empire Alpha Orchestrator - Coordinates all strategies.

Main entry point for the multi-strategy trading system.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd

from .models import Signal, TrendStrength, RFactorPosition
from .rfactor import RFactorCalculator
from .profit_taker import PartialProfitTaker, ProfitTakeConfig
from .trailing import AdvancedTrailingSystem, AdvancedTrailingConfig
from .funding_arbitrage import FundingArbitrageStrategy, ArbitrageConfig
from .wave_rider import WaveRiderStrategy, WaveRiderConfig
from .portfolio import PortfolioManager, PortfolioConfig
from .risk_manager import UnifiedRiskManager, RiskConfig
from ..risk.regime import RegimeClassifier # Import RegimeClassifier

logger = logging.getLogger(__name__)


@dataclass
class AlphaConfig:
    """Master configuration for Kinetic Empire Alpha."""
    portfolio: PortfolioConfig = None
    risk: RiskConfig = None
    arbitrage: ArbitrageConfig = None
    wave_rider: WaveRiderConfig = None
    profit_take: ProfitTakeConfig = None
    trailing: AdvancedTrailingConfig = None
    
    def __post_init__(self):
        self.portfolio = self.portfolio or PortfolioConfig()
        self.risk = self.risk or RiskConfig()
        self.arbitrage = self.arbitrage or ArbitrageConfig()
        self.wave_rider = self.wave_rider or WaveRiderConfig()
        self.profit_take = self.profit_take or ProfitTakeConfig()
        self.trailing = self.trailing or AdvancedTrailingConfig()


class KineticEmpireAlpha:
    """Main orchestrator for Kinetic Empire Alpha v2.0."""
    
    def __init__(self, config: Optional[AlphaConfig] = None,
                 initial_capital: float = 10000.0):
        self.config = config or AlphaConfig()
        
        # Initialize components
        self.portfolio = PortfolioManager(self.config.portfolio, initial_capital)
        self.risk_manager = UnifiedRiskManager(self.config.risk)
        self.rfactor = RFactorCalculator()
        self.profit_taker = PartialProfitTaker(self.config.profit_take)
        self.trailing = AdvancedTrailingSystem(self.config.trailing)
        self.regime_classifier = RegimeClassifier() # Initialize RegimeClassifier
        self.current_regime_info = {}
        
        # Initialize strategies
        self.funding_arb = FundingArbitrageStrategy(self.config.arbitrage)
        self.wave_rider = WaveRiderStrategy(self.config.wave_rider)
        
        # State
        self.positions: Dict[str, RFactorPosition] = {}
        self.pending_signals: List[Signal] = []
        self.running = False
        
        logger.info("Kinetic Empire Alpha v2.0 initialized")
        logger.info(f"Initial capital: ${initial_capital:,.2f}")
        logger.info(f"Allocations: {self.portfolio.allocations}")

    def update_regime(self, btc_close: float, btc_ema50: float) -> None:
        """Update market regime."""
        self.current_regime_info = self.regime_classifier.get_regime_info(btc_close, btc_ema50)
        regime = self.current_regime_info['regime']
        fg_index = self.current_regime_info.get('fear_greed_index')
        logger.info(f"📊 Regime Update: {regime.value} | FG: {fg_index} | Max Trades: {self.current_regime_info['max_trades']}")

    def process_funding_opportunities(self, funding_rates: Dict[str, float]) -> List[Signal]:
        """Process funding rate arbitrage opportunities."""
        signals = []
        
        if not self.risk_manager.can_trade():
            return signals
            
        # Arbitrage is usually regime-neutral, but we might want to check extreme volatility
        # For now, let it run delta-neutral
        
        opportunities = self.funding_arb.find_opportunities(funding_rates)
        capital = self.portfolio.get_strategy_capital('funding_arbitrage')
        
        for pair in opportunities[:self.config.arbitrage.max_positions]:
            if pair in self.funding_arb.positions:
                continue
            
            if not self.funding_arb.can_open_position():
                break
            
            # Create signal for arbitrage
            signal = Signal(
                pair=pair,
                side="ARBITRAGE",
                strategy="funding_arbitrage",
                strength=TrendStrength.NEUTRAL,
                size_pct=self.config.arbitrage.position_size_pct,
            )
            signals.append(signal)
            logger.info(f"Funding arbitrage opportunity: {pair} @ {funding_rates[pair]:.4%}")
        
        return signals
    
    def process_wave_rider(self, pair: str, 
                          timeframe_data: Dict[str, pd.DataFrame]) -> Optional[Signal]:
        """Process Wave Rider strategy for a pair."""
        if not self.risk_manager.can_trade():
            return None
        
        if pair in self.positions:
            return None
            
        # REGIME CHECK
        if self.current_regime_info:
             regime = self.current_regime_info.get('regime')
             max_trades = self.current_regime_info.get('max_trades', 20)
             
             # Check concurrent positions limit
             open_directional_positions = len([p for p in self.positions.values() if p.strategy == "wave_rider"])
             if open_directional_positions >= max_trades:
                 return None
        
        signal = self.wave_rider.generate_signal(pair, timeframe_data)
        if signal:
            # Further filtering: If weak regime, maybe ignore weak signals?
            # Implemented indirectly via max_trades, but we could add more logic
            logger.info(f"Wave Rider signal: {pair} {signal.side} ({signal.strength.value})")
        
        return signal
    
    def update_position(self, pair: str, current_price: float, 
                       df: pd.DataFrame) -> Dict:
        """Update position with current price and check for exits."""
        result = {
            "pair": pair,
            "action": None,
            "partial_exit": None,
            "new_stop": None,
        }
        
        position = self.positions.get(pair)
        if not position:
            return result
        
        # Update R-factor
        self.rfactor.update_position(pair, current_price)
        position = self.rfactor.get_position(pair)
        
        # Check for partial profit taking
        level = self.profit_taker.check_profit_levels(position)
        if level:
            result["action"] = "partial_exit"
            result["partial_exit"] = {
                "r_level": level.r_level,
                "percentage": level.percentage,
                "price": current_price,
            }
            logger.info(f"Partial exit {pair}: {level.percentage:.0%} at {level.r_level}R")
        
        # Update trailing stop
        if position.current_r >= 1.0:  # Only trail after 1R
            new_stop = self.trailing.get_best_stop(position, df)
            current_stop = position.stop_loss
            
            updated_stop = self.trailing.update_stop_if_higher(
                new_stop, current_stop, position.side
            )
            
            if updated_stop != current_stop:
                result["new_stop"] = updated_stop
                position.stop_loss = updated_stop
                logger.debug(f"Updated stop for {pair}: {current_stop:.2f} -> {updated_stop:.2f}")
        
        # Check for stop loss hit
        if position.side == "LONG" and current_price <= position.stop_loss:
            result["action"] = "stop_loss"
        elif position.side == "SHORT" and current_price >= position.stop_loss:
            result["action"] = "stop_loss"
        
        return result
    
    def close_position(self, pair: str, exit_price: float, reason: str) -> Optional[float]:
        """Close a position and record the trade."""
        position = self.positions.pop(pair, None)
        if not position:
            return None
        
        # Calculate P&L
        if position.side == "LONG":
            pnl = (exit_price - position.entry_price) * position.position_size
        else:
            pnl = (position.entry_price - exit_price) * position.position_size
        
        # Record trade
        self.portfolio.record_trade(position.strategy, pnl, position.current_r)
        self.risk_manager.update_pnl(pnl)
        
        # Cleanup
        self.rfactor.remove_position(pair)
        self.profit_taker.reset_position(pair)
        
        logger.info(f"Closed {pair}: {reason}, P&L: ${pnl:.2f}, R: {position.current_r:.2f}")
        
        return pnl
    
    def get_status(self) -> Dict:
        """Get current system status."""
        return {
            "running": self.running,
            "positions": len(self.positions),
            "arbitrage_positions": len(self.funding_arb.positions),
            "allocations": self.portfolio.allocations,
            "risk_status": self.risk_manager.get_status(),
            "performance": self.portfolio.get_performance_summary(),
            "regime": self.current_regime_info.get("regime", "UNKNOWN"),
        }
    
    def emergency_stop(self) -> None:
        """Emergency stop - close all positions."""
        logger.warning("EMERGENCY STOP TRIGGERED")
        self.running = False
        self.risk_manager.enter_emergency_mode()
