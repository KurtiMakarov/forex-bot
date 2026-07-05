"""Economic Calendar - Simplified for stocks"""
from datetime import datetime, timedelta
from typing import Tuple
from utils.logger import setup_logger

logger = setup_logger('economic_calendar')

class EconomicCalendar:
    """For stocks, we check for earnings reports and major market events"""
    
    def __init__(self):
        self.events_cache = {}

    def is_high_impact_period(self, symbol: str, minutes_window: int = 60) -> Tuple[bool, str]:
        """Check if there's a high-impact event for the stock (earnings, etc.)"""
        # For now, return False - can be extended later with earnings API
        return False, ""

    def _fetch_events(self):
        logger.info("Fetching market events")
        return []