"""Consecutive loss tracking module.

Tracks losing streaks and provides protection multipliers
to prevent drawdown spirals.
"""


class ConsecutiveLossTracker:
    """Tracks consecutive losses and provides protection multipliers.
    
    Protection multipliers (from Requirements 2.3-2.5):
    - 0-2 consecutive losses: 1.0x (no reduction)
    - 3-4 consecutive losses: 0.5x (50% reduction)
    - 5+ consecutive losses: 0.25x (75% reduction)
    
    Counter resets to zero on any winning trade.
    """

    def __init__(self):
        """Initialize loss tracker."""
        self.consecutive_losses: int = 0

    def record_loss(self) -> None:
        """Record a losing trade, incrementing the counter.
        
        Validates: Requirement 2.1
        """
        self.consecutive_losses += 1

    def record_win(self) -> None:
        """Record a winning trade, resetting the counter.
        
        Validates: Requirement 2.2
        """
        self.consecutive_losses = 0

    def get_protection_multiplier(self) -> float:
        """Get position size multiplier based on loss streak.
        
        Returns:
            1.0 for 0-2 losses, 0.5 for 3-4 losses, 0.25 for 5+ losses
            
        Validates: Requirements 2.3, 2.4, 2.5
        """
        if self.consecutive_losses >= 5:
            return 0.25
        elif self.consecutive_losses >= 3:
            return 0.5
        else:
            return 1.0

    def reset(self) -> None:
        """Reset the loss counter to zero."""
        self.consecutive_losses = 0

    @property
    def should_halt_trading(self) -> bool:
        """Check if trading should be halted due to excessive losses.
        
        Returns:
            True if 5+ consecutive losses (optional halt condition)
        """
        return self.consecutive_losses >= 5
