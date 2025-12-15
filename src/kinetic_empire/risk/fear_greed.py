"""Fear & Greed Index Fetcher.

Provides market sentiment analysis using the alternative.me Fear & Greed Index API.
Used to adjust trading aggression based on market emotion.
"""

import logging
import requests
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

@dataclass
class FearGreedData:
    """Fear & Greed Index Data."""
    value: int
    classification: str
    timestamp: datetime

class FearGreedFetcher:
    """Fetches Crypto Fear & Greed Index."""
    
    API_URL = "https://api.alternative.me/fng/"
    
    def fetch(self) -> Optional[FearGreedData]:
        """Fetch latest index value.
        
        Returns:
            FearGreedData or None if fetch fails
        """
        try:
            response = requests.get(self.API_URL, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'data' in data and len(data['data']) > 0:
                item = data['data'][0]
                value = int(item['value'])
                classification = item['value_classification']
                timestamp = datetime.fromtimestamp(int(item['timestamp']))
                
                logger.info(f"😨 Fear & Greed: {value} ({classification})")
                return FearGreedData(value, classification, timestamp)
                
            return None
            
        except Exception as e:
            logger.error(f"Failed to fetch Fear & Greed Index: {e}")
            return None
