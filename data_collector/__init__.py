"""Data collection modules"""

from .market_data import MarketDataCollector
from .news import NewsCollector
from .economic_calendar import EconomicCalendar

__all__ = ['MarketDataCollector', 'NewsCollector', 'EconomicCalendar']