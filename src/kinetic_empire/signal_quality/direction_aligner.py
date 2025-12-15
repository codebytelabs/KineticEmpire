"""Direction Aligner for Signal Quality Gate.

Ensures trade direction matches Enhanced TA signal, overriding Cash Cow if needed.
"""

import logging


logger = logging.getLogger(__name__)


class DirectionAligner:
    """Aligns trade direction with Enhanced TA signal.
    
    The Enhanced TA direction always takes precedence over Cash Cow direction.
    This prevents trading against actual market momentum.
    """
    
    def align(self, enhanced_direction: str, cash_cow_direction: str) -> str:
        """Align trade direction with Enhanced TA.
        
        Args:
            enhanced_direction: Direction from Enhanced TA ("LONG" or "SHORT")
            cash_cow_direction: Direction from Cash Cow scorer
            
        Returns:
            Final direction to use (always Enhanced TA direction)
        """
        # Normalize directions to uppercase
        enhanced = enhanced_direction.upper()
        cash_cow = cash_cow_direction.upper()
        
        # Log warning if directions conflict
        if enhanced != cash_cow:
            logger.warning(
                f"Direction conflict: Enhanced TA says {enhanced}, "
                f"Cash Cow says {cash_cow}. Using Enhanced TA direction."
            )
        
        # Always return Enhanced TA direction
        return enhanced
