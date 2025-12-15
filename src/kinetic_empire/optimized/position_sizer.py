"""Optimized position sizer using quarter-Kelly criterion."""

from .config import OptimizedConfig, DEFAULT_CONFIG


class OptimizedPositionSizer:
    """Implements quarter-Kelly position sizing."""
    
    def __init__(self, config: OptimizedConfig = DEFAULT_CONFIG):
        self.config = config
    
    def calculate_kelly(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float
    ) -> float:
        """Calculate raw Kelly criterion value.
        
        Kelly = W - (1-W)/R
        where W = win rate, R = avg_win/avg_loss
        
        Args:
            win_rate: Historical win rate (0-1)
            avg_win: Average winning trade amount
            avg_loss: Average losing trade amount (positive value)
            
        Returns:
            Raw Kelly value (can be negative)
        """
        if avg_loss <= 0:
            return 0.0
        
        if avg_win <= 0:
            return 0.0
        
        win_loss_ratio = avg_win / avg_loss
        kelly = win_rate - ((1 - win_rate) / win_loss_ratio)
        
        return kelly
    
    def get_kelly_fraction(self, win_rate: float) -> float:
        """Get Kelly fraction based on win rate.
        
        Args:
            win_rate: Historical win rate (0-1)
            
        Returns:
            Kelly fraction to use (0.25 or 0.15)
        """
        if win_rate < self.config.KELLY_LOW_WINRATE_THRESHOLD:
            return self.config.KELLY_LOW_WINRATE_FRACTION
        return self.config.KELLY_FRACTION
    
    def calculate_position_size(
        self,
        capital: float,
        win_rate: float,
        avg_win: float,
        avg_loss: float
    ) -> float:
        """Calculate position size using quarter-Kelly.
        
        Args:
            capital: Total available capital
            win_rate: Historical win rate (0-1)
            avg_win: Average winning trade amount
            avg_loss: Average losing trade amount (positive value)
            
        Returns:
            Position size in capital units, never negative, capped at 25%
        """
        if capital <= 0:
            return 0.0
        
        if win_rate < 0 or win_rate > 1:
            raise ValueError("win_rate must be between 0 and 1")
        
        # Calculate raw Kelly
        raw_kelly = self.calculate_kelly(win_rate, avg_win, avg_loss)
        
        # If Kelly is negative, don't trade
        if raw_kelly <= 0:
            return 0.0
        
        # Apply Kelly fraction based on win rate
        kelly_fraction = self.get_kelly_fraction(win_rate)
        adjusted_kelly = raw_kelly * kelly_fraction
        
        # Calculate position size
        position_size = capital * adjusted_kelly
        
        # Cap at maximum position percent
        max_position = capital * self.config.MAX_POSITION_PERCENT
        position_size = min(position_size, max_position)
        
        return position_size
