"""Exit signal generation module.

Generates sell signals when trend conditions deteriorate or stops are hit.
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum

from kinetic_empire.models import Position, ExitReason


class ExitSignalType(Enum):
    """Type of exit signal."""
    NONE = "none"
    TREND_BREAK = "trend_break"
    STOP_LOSS = "stop_loss"


@dataclass
class ExitSignal:
    """Exit signal with reason."""
    should_exit: bool
    signal_type: ExitSignalType
    reason: Optional[ExitReason] = None

    @classmethod
    def no_exit(cls) -> "ExitSignal":
        """Create a no-exit signal."""
        return cls(should_exit=False, signal_type=ExitSignalType.NONE)

    @classmethod
    def trend_break_exit(cls) -> "ExitSignal":
        """Create a trend break exit signal."""
        return cls(
            should_exit=True,
            signal_type=ExitSignalType.TREND_BREAK,
            reason=ExitReason.TREND_BREAK
        )

    @classmethod
    def stop_loss_exit(cls) -> "ExitSignal":
        """Create a stop loss exit signal."""
        return cls(
            should_exit=True,
            signal_type=ExitSignalType.STOP_LOSS,
            reason=ExitReason.STOP_LOSS
        )


class ExitSignalGenerator:
    """Generates exit signals based on trend breaks and stop losses.
    
    Monitors open positions and generates sell signals when:
    - Price breaks below EMA50 with volume confirmation
    - Stop loss price is reached
    """

    def check_trend_break(
        self,
        close_5m: float,
        ema50_5m: float,
        volume: float,
        mean_volume: float
    ) -> bool:
        """Check for trend break with volume confirmation.
        
        Trend break occurs when:
        - Close < EMA50 (trend reversal)
        - Volume > Mean (confirmation)
        
        Args:
            close_5m: Current 5-minute close price
            ema50_5m: 5-minute EMA50 value
            volume: Current volume
            mean_volume: 24-hour mean volume
            
        Returns:
            True if trend break is confirmed
        """
        price_break = close_5m < ema50_5m
        volume_confirmation = volume > mean_volume
        
        return price_break and volume_confirmation

    def check_stop_loss(
        self,
        current_price: float,
        stop_price: float
    ) -> bool:
        """Check if stop loss is hit.
        
        Args:
            current_price: Current market price
            stop_price: Stop loss price
            
        Returns:
            True if current price <= stop price
        """
        return current_price <= stop_price

    def check_exit_conditions(
        self,
        position: Position,
        close_5m: float,
        ema50_5m: float,
        volume: float,
        mean_volume: float
    ) -> ExitSignal:
        """Check all exit conditions for a position.
        
        Args:
            position: Current position
            close_5m: Current 5-minute close price
            ema50_5m: 5-minute EMA50 value
            volume: Current volume
            mean_volume: 24-hour mean volume
            
        Returns:
            ExitSignal indicating whether to exit and why
        """
        # Check stop loss first (highest priority)
        if self.check_stop_loss(close_5m, position.stop_loss):
            return ExitSignal.stop_loss_exit()
        
        # Check trailing stop if active
        if position.trailing_stop_active and position.trailing_stop_level:
            if self.check_stop_loss(close_5m, position.trailing_stop_level):
                return ExitSignal(
                    should_exit=True,
                    signal_type=ExitSignalType.STOP_LOSS,
                    reason=ExitReason.TRAILING_STOP
                )
        
        # Check trend break
        if self.check_trend_break(close_5m, ema50_5m, volume, mean_volume):
            return ExitSignal.trend_break_exit()
        
        return ExitSignal.no_exit()

    def generate_exit_signal(
        self,
        position: Position,
        close_5m: float,
        ema50_5m: float,
        volume: float,
        mean_volume: float
    ) -> bool:
        """Generate exit signal for a position.
        
        Args:
            position: Current position
            close_5m: Current 5-minute close price
            ema50_5m: 5-minute EMA50 value
            volume: Current volume
            mean_volume: 24-hour mean volume
            
        Returns:
            True if position should be exited
        """
        signal = self.check_exit_conditions(
            position, close_5m, ema50_5m, volume, mean_volume
        )
        return signal.should_exit
